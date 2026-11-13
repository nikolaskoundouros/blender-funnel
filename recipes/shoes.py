"""Trainers built by code, in the order a shoemaker works (see the shoe tools surveyed in
sources/log.md, pass 8): the last (the foot shape plus room), the upper over it, the sole
from the footprint, then panels, eyelets and laces.

All pieces are made around the morphed body's own feet, so they fit any body. The sole adds
height under the foot: lift the character by `SOLE_BELOW` so the sole stands on the floor.
"""
import bmesh
import bpy
import numpy as np

from . import garments, human

SOLE_BELOW = 0.018      # sole thickness under the foot (metres)


def footprint(base_verts, side="L", contact=0.014, grow=0.011, points=48):
    """Outline of one foot's sole, from the foot vertices nearest the ground: a smooth closed
    loop (x, y) around them, `grow` metres larger all round."""
    vb = human.to_blender(base_verts)[:human.BODY_VERTS]
    part = garments._body_coordinates()["part"][:human.BODY_VERTS]
    sign = 1.0 if side == "L" else -1.0
    foot = (part == "foot") & (vb[:, 0] * sign > 0)
    fv = vb[foot]
    low = fv[fv[:, 2] < fv[:, 2].min() + contact][:, :2]
    centre = low.mean(axis=0)
    # radial outline: furthest point in each direction, then smoothed and grown
    ang = np.arctan2(low[:, 1] - centre[1], low[:, 0] - centre[0])
    bins = np.linspace(-np.pi, np.pi, points + 1)
    r = np.zeros(points)
    for k in range(points):
        m = (ang >= bins[k]) & (ang < bins[k + 1])
        r[k] = np.linalg.norm(low[m] - centre, axis=1).max() if m.any() else np.nan
    good = ~np.isnan(r)
    idx = np.arange(points)
    r = np.interp(idx, idx[good], r[good], period=points)
    for _ in range(3):                                         # smooth the outline
        r = 0.25 * np.roll(r, 1) + 0.5 * r + 0.25 * np.roll(r, -1)
    mid = 0.5 * (bins[:-1] + bins[1:])
    out = centre + (r + grow)[:, None] * np.stack([np.cos(mid), np.sin(mid)], axis=1)
    return out, {"length": float(np.ptp(fv[:, 1])), "width": float(np.ptp(fv[:, 0])),
                 "ground": float(fv[:, 2].min())}


def sole(scene, base_verts, side="L", name=None, material=None, below=SOLE_BELOW, up=0.017,
         toe_spring=0.006, parent=None):
    """A midsole: the footprint outline extruded from `below` under the foot to `up` above
    the ground line, so it wraps the bottom edge of the upper; the toe curves up."""
    out, info = footprint(base_verts, side)
    ground = info["ground"]
    bm = bmesh.new()
    bottom = [bm.verts.new((x, y, ground - below)) for x, y in out]
    face = bm.faces.new(bottom)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    top = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in top:
        v.co.z = ground + up
    # toe spring: the front quarter of the sole rises
    ys = np.array([p[1] for p in out])
    front, back = ys.min(), ys.max()
    for v in bm.verts:
        t = np.clip((front + 0.25 * (back - front) - v.co.y) / (0.25 * (back - front)), 0.0, 1.0)
        v.co.z += toe_spring * t ** 2
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name or f"sole.{side}")
    bm.to_mesh(me); bm.free()
    obj = bpy.data.objects.new(me.name, me)
    scene.collection.objects.link(obj)
    if material is not None:
        me.materials.append(material)
    me.shade_smooth()
    # Rounded edges only (step 1 also had a subdivision, which made the many-sided caps wavy)
    bev = obj.modifiers.new("Rounded edges", "BEVEL"); bev.width = 0.0035; bev.segments = 4
    bev.limit_method = "ANGLE"
    if parent is not None:
        obj.parent = parent
    return obj, info


def upper_spec(name="upper", top_at=1.95, ease=0.006, material=None, smooth_shell=12):
    """The upper as a garment spec (garments.boots): the foot shape with room, cut below the
    ankle. Pass it in build_human's outfit."""
    return garments.boots(name=name, top_at=top_at, ease=ease, thickness=0.003, material=material,
                          smooth_shell=smooth_shell)


def foot_frames(base_verts):
    """Per foot: centre line x, toe tip y, heel y, ankle height (Blender coordinates)."""
    out = {}
    for side in ("L", "R"):
        pts, info = footprint(base_verts, side, grow=0.0)
        out[side] = {"x": float(pts[:, 0].mean()), "toe": float(pts[:, 1].min()), "heel": float(pts[:, 1].max())}
    return out


def add_panels(mat, frames, toe_cap=(0.80, 0.80, 0.78), heel=(0.80, 0.80, 0.78), eyestay=(0.42, 0.22, 0.02),
               toe_len=0.045, heel_len=0.040, heel_top=0.055, stay_half=0.016, stay_from=0.06, stay_to=0.12,
               seam=(0.25, 0.14, 0.03)):
    """Colour the upper's panels from object position: toe cap over the front `toe_len` metres,
    heel counter over the back `heel_len` up to `heel_top`, eyestay as a band `stay_half` either
    side of the foot's centre line from `stay_from` to `stay_to` behind the toe, each edged with
    a thin darker seam line."""
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    tc = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ"); links.new(tc.outputs["Object"], sep.inputs[0])
    fx = abs(frames["L"]["x"]); toe = frames["L"]["toe"]; heel_y = frames["L"]["heel"]

    def math(op, a, b=None):
        n = nodes.new("ShaderNodeMath"); n.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                links.new(v, n.inputs[i])
        return n.outputs[0]

    ax = math("ABSOLUTE", sep.outputs["X"])
    lx = math("ABSOLUTE", math("SUBTRACT", ax, fx))                   # distance from the foot's centre line
    y, z = sep.outputs["Y"], sep.outputs["Z"]
    base = next((l.from_socket for l in links if l.to_socket == bsdf.inputs["Base Color"]), None)
    col = nodes.new("ShaderNodeMix"); col.data_type = "RGBA"
    if base is not None:
        links.new(base, col.inputs["A"])
    else:
        col.inputs["A"].default_value = bsdf.inputs["Base Color"].default_value
    current = col.inputs["A"]
    out = None

    def layer(mask, rgb, prev):
        m = nodes.new("ShaderNodeMix"); m.data_type = "RGBA"
        links.new(mask, m.inputs["Factor"]); links.new(prev, m.inputs["A"])
        m.inputs["B"].default_value = tuple(rgb) + (1.0,)
        return m.outputs["Result"]

    prev = base if base is not None else None
    if prev is None:
        rgb = nodes.new("ShaderNodeRGB"); rgb.outputs[0].default_value = bsdf.inputs["Base Color"].default_value
        prev = rgb.outputs[0]
    # curved panel lines (straight lines looked boxy, step 2): the toe cap's edge arcs forward
    # toward the sides, the heel counter's front edge slants back as it rises
    toe_d = math("SUBTRACT", math("SUBTRACT", toe + toe_len, math("MULTIPLY", math("MULTIPLY", lx, lx), 14.0)), y)
    heel_d = math("MINIMUM", math("SUBTRACT", math("SUBTRACT", y, heel_y - heel_len), math("MULTIPLY", z, 0.45)),
                  math("SUBTRACT", heel_top, z))
    stay_d = math("MINIMUM", math("SUBTRACT", stay_half, lx),
                  math("MINIMUM", math("SUBTRACT", y, toe + stay_from), math("SUBTRACT", toe + stay_to, y)))
    for d, rgb in ((toe_d, toe_cap), (heel_d, heel), (stay_d, eyestay)):
        prev = layer(math("GREATER_THAN", d, 0.0), rgb, prev)
        seam_line = math("LESS_THAN", math("ABSOLUTE", math("SUBTRACT", d, 0.0025)), 0.0007)
        prev = layer(seam_line, seam, prev)
    links.new(prev, bsdf.inputs["Base Color"])
    return mat


def collar_spec(name="collar", material=None, ease=0.010):
    """Padded ring round the ankle opening (garments.band on the leg)."""
    return garments.band(name=name, limb="leg", start=1.925, end=1.955, ease=ease, thickness=0.006,
                         material=material)


def laces(scene, upper_obj, frames, rows=5, start=0.062, end=0.118, spread=0.011, radius=0.0015,
          lace_material=None, eyelet_material=None, parent=None):
    """Eyelets in two rows along each foot's instep and a criss-cross lace through them,
    ray-cast onto the upper so they sit on its surface; a small bow at the top."""
    from . import straps
    bvh = straps.surface([upper_obj])
    made = 0
    for side, fr in frames.items():
        fx, toe = fr["x"], fr["toe"]
        holes = []
        for k in range(rows):
            y = toe + start + (end - start) * k / (rows - 1)
            row = []
            for sx in (-1.0, 1.0):
                p, n = straps.hit(bvh, (fx + sx * spread * (1.0 + 0.15 * k / rows), y, 0.4), (0.0, 0.0, -1.0))
                row.append((np.array(p), np.array(n)) if p is not None else None)
            holes.append(row)
        for k, row in enumerate(holes):
            for j, h in enumerate(row):
                if h is None:
                    continue
                straps.disc(scene, f"eyelet.{side}.{k}.{j}", h[0] + h[1] * 0.0006, h[1], 0.0026, 0.0012,
                            material=eyelet_material, bevel=0.0006, parent=parent)
        lift = lambda h, extra=0.0: h[0] + h[1] * (0.0022 + extra)
        segs = [(holes[0][0], holes[0][1])]                    # straight bar at the toe end
        for k in range(rows - 1):
            segs += [(holes[k][0], holes[k + 1][1]), (holes[k][1], holes[k + 1][0])]
        for i, (a, b) in enumerate(segs):
            if a is None or b is None:
                continue
            mid = 0.5 * (lift(a) + lift(b)) + 0.5 * (a[1] + b[1]) * 0.0015
            straps.tube(scene, f"lace.{side}.{i}", [lift(a), mid, lift(b)], radius, material=lace_material,
                        parent=parent)
            made += 1
        top = holes[-1]
        if top[0] is not None and top[1] is not None:
            c = 0.5 * (lift(top[0], 0.002) + lift(top[1], 0.002))
            up = 0.5 * (top[0][1] + top[1][1])
            for sx in (-1.0, 1.0):                             # two loops and two loose ends
                loop = [c, c + np.array([sx * 0.012, -0.004, 0.0]) + up * 0.004,
                        c + np.array([sx * 0.016, 0.004, 0.0]) + up * 0.002, c]
                straps.tube(scene, f"bow.{side}.{sx}", loop, radius, material=lace_material, parent=parent)
                tail = [c, c + np.array([sx * 0.006, 0.010, -0.004]), c + np.array([sx * 0.010, 0.018, -0.014])]
                straps.tube(scene, f"lace_end.{side}.{sx}", tail, radius, material=lace_material, parent=parent)
    return made
