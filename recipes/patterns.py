"""Garments from real sewing patterns.

Reads the pattern file format of GarmentCode (Korosteleva and Sorkine-Hornung, ETH Zurich,
MIT licence): flat panels with outlines in centimetres, curved edges, a 3D placement for
each panel round the body, and a list of stitches joining pairs of edges. This is our own
reader, written from the format; it does not run GarmentCode's code.

What it does:
  1. Each panel edge is sampled into points. Two edges that are stitched together get the
     same number of points so they can be joined one to one.
  2. The panel interior is filled with triangles of even size (cloth simulates best on
     small, similar triangles).
  3. The panel is stood up in 3D where the pattern says it goes, in Blender's axes.
  4. Every stitch becomes loose edges between matching points. Blender's cloth solver
     treats loose edges as sewing springs that pull the panels together.
"""
import json
import math

import bpy
import numpy as np
from mathutils import geometry as geo


def load(path):
    with open(path) as fh:
        spec = json.load(fh)
    return spec["pattern"], spec.get("properties", {})


def _rotation(euler_deg):
    """Rotation matrix for XYZ Euler angles in degrees, composed as Rz * Ry * Rx."""
    x, y, z = (math.radians(a) for a in euler_deg)
    rx = np.array([[1, 0, 0], [0, math.cos(x), -math.sin(x)], [0, math.sin(x), math.cos(x)]])
    ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    rz = np.array([[math.cos(z), -math.sin(z), 0], [math.sin(z), math.cos(z), 0], [0, 0, 1]])
    return rz @ ry @ rx


def _control(start, end, rel):
    """A control point given relative to an edge: along it, and square to it."""
    edge = end - start
    return start + rel[0] * edge + rel[1] * np.array([-edge[1], edge[0]])


def edge_points(vertices, edge, segments):
    """Points along one panel edge, both ends included."""
    a, b = (np.array(vertices[i], dtype=float) for i in edge["endpoints"])
    t = np.linspace(0.0, 1.0, segments + 1)[:, None]
    curve = edge.get("curvature")
    if not curve:
        return a + t * (b - a)
    kind = "quadratic" if isinstance(curve, list) else curve["type"]
    params = curve if isinstance(curve, list) else curve["params"]
    if kind == "quadratic":
        c = _control(a, b, params[0] if not isinstance(curve, list) else params)
        return (1 - t) ** 2 * a + 2 * (1 - t) * t * c + t ** 2 * b
    if kind == "cubic":
        c1, c2 = _control(a, b, params[0]), _control(a, b, params[1])
        return (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t ** 2 * c2 + t ** 3 * b
    if kind == "circle":   # not exercised by the shirt pattern; side convention unverified
        radius, large, right = params
        chord = b - a
        half = np.linalg.norm(chord) / 2.0
        h = math.sqrt(max(radius ** 2 - half ** 2, 0.0))
        perp = np.array([-chord[1], chord[0]]) / (2.0 * half)
        centre = (a + b) / 2.0 + perp * h * (1.0 if bool(right) != bool(large) else -1.0)
        a0 = math.atan2(*(a - centre)[::-1])
        a1 = math.atan2(*(b - centre)[::-1])
        sweep = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        if large:
            sweep = sweep - math.copysign(2 * math.pi, sweep)
        ang = a0 + t[:, 0] * sweep
        return centre + radius * np.stack([np.cos(ang), np.sin(ang)], axis=1)
    raise ValueError(f"unknown edge curvature {kind!r}")


def _inside(points, polygon):
    x, y = points[:, 0], points[:, 1]
    inside = np.zeros(len(points), dtype=bool)
    for (x0, y0), (x1, y1) in zip(polygon, np.roll(polygon, -1, axis=0)):
        cross = ((y0 > y) != (y1 > y)) & (x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-12) + x0)
        inside ^= cross
    return inside


def build(scene, pattern, name="garment", spacing=1.8, to_metres=0.01, offset=(0.0, 0.0, 0.0),
          keep_stitch=None, edit=None, material=None):
    """Make one mesh object from a pattern: meshed panels plus sewing edges.

    spacing: target triangle edge in centimetres. edit(panel_name, panel): optional hook to
    alter a panel's 2D vertices before meshing (e.g. lengthen a sleeve).
    keep_stitch(panel_a, edge_a, panel_b, edge_b, fraction): optional; return False to
    leave a matched pair of points unsewn (fraction runs 0 to 1 along the first edge).
    Returns (object, info) where info lists each vertex's panel.
    """
    panels = json.loads(json.dumps(pattern["panels"]))  # work on a copy
    if edit:
        for pname, panel in panels.items():
            edit(pname, panel)
    stitches = pattern["stitches"]

    # 1. How many segments each edge gets: stitched partners must agree.
    length = {}
    for pname, panel in panels.items():
        for i, edge in enumerate(panel["edges"]):
            pts = edge_points(panel["vertices"], edge, 40)
            length[(pname, i)] = float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
    segments = {key: max(2, round(value / spacing)) for key, value in length.items()}
    for a, b in stitches:
        ka, kb = (a["panel"], a["edge"]), (b["panel"], b["edge"])
        segments[ka] = segments[kb] = max(2, round(max(length[ka], length[kb]) / spacing))

    verts3d, faces, uvs, owner = [], [], [], []
    edge_verts = {}                     # (panel, edge) -> global vertex indices along it
    for pname, panel in panels.items():
        # 2. Boundary loop, then interior grid points, then constrained triangulation.
        loop, edge_slices = [], {}
        for i, edge in enumerate(panel["edges"]):
            pts = edge_points(panel["vertices"], edge, segments[(pname, i)])
            edge_slices[i] = (len(loop), len(pts))
            loop.extend(pts[:-1])
        loop = np.array(loop)
        lo, hi = loop.min(axis=0), loop.max(axis=0)
        gx = np.arange(lo[0] + spacing * 0.5, hi[0], spacing)
        gy = np.arange(lo[1] + spacing * 0.5, hi[1], spacing * 0.866)
        grid = np.array([(x + (spacing * 0.5 if j % 2 else 0.0), y) for j, y in enumerate(gy) for x in gx])
        grid = grid[_inside(grid, loop)]
        far = np.array([np.min(np.linalg.norm(loop - g, axis=1)) > spacing * 0.6 for g in grid])
        points = np.concatenate([loop, grid[far]]) if len(grid) else loop
        n = len(loop)
        constraint = [(i, (i + 1) % n) for i in range(n)]
        out_v, _, out_f, orig, _, _ = geo.delaunay_2d_cdt([tuple(p) for p in points], constraint, [], 1, 1e-6)
        out_v = np.array([tuple(v) for v in out_v])
        where = {src: i for i, sources in enumerate(orig) for src in sources}
        tris = [f for f in out_f if len(f) == 3 and _inside(out_v[list(f)].mean(axis=0)[None, :], loop)[0]]

        # 3. Stand the panel up where the pattern places it, converted to Blender axes
        # (pattern: x left, y up, z front, centimetres; Blender: x left, y back, z up).
        rot, shift = _rotation(panel["rotation"]), np.array(panel["translation"], dtype=float)
        placed = np.concatenate([out_v, np.zeros((len(out_v), 1))], axis=1) @ rot.T + shift
        blender = np.stack([placed[:, 0], -placed[:, 2], placed[:, 1]], axis=1) * to_metres + np.array(offset)
        normal = rot @ np.array([0.0, 0.0, 1.0])
        normal = np.array([normal[0], -normal[2], normal[1]])
        centre = blender.mean(axis=0)
        outward = np.dot(normal[:2], centre[:2] - np.array(offset[:2])) >= 0   # away from the body's axis
        base = len(verts3d)
        verts3d.extend(blender.tolist())
        owner.extend([pname] * len(blender))
        for f in tris:
            f = f if outward else f[::-1]
            faces.append(tuple(base + i for i in f))
            uvs.extend((out_v[i] * to_metres).tolist() for i in f)
        for i, (start, count) in edge_slices.items():
            edge_verts[(pname, i)] = [base + where[(start + k) % n] for k in range(count)]

    # 4. Stitches: pair points along the two edges, in whichever direction lines up in 3D.
    v = np.array(verts3d)
    sewing = set()
    for a, b in stitches:
        ia, ib = edge_verts[(a["panel"], a["edge"])], edge_verts[(b["panel"], b["edge"])]
        same = np.linalg.norm(v[ia] - v[ib], axis=1).sum()
        flipped = np.linalg.norm(v[ia] - v[ib[::-1]], axis=1).sum()
        if flipped < same:
            ib = ib[::-1]
        for k, (p, q) in enumerate(zip(ia, ib)):
            if p != q and (keep_stitch is None or keep_stitch(a["panel"], a["edge"], b["panel"], b["edge"], k / (len(ia) - 1))):
                sewing.add((min(p, q), max(p, q)))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts3d, sorted(sewing), faces)
    mesh.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array(uvs).ravel())
    mesh.update()
    mesh.shade_smooth()
    if material is not None:
        mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    return obj, {"owner": owner, "panels": list(panels), "sewing_edges": len(sewing),
                 "triangles": len(faces), "vertices": len(verts3d)}
