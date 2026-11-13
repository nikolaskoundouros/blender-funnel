"""Garments made from scratch: no downloaded clothing assets.

How it works. The base mesh carries two invisible helper shells that morph and bend with
the body: a skin-tight "tights" shell (2,650 quads over torso, arms, legs and feet, about
5 mm off the skin) and a skirt-shaped shell from waist to ankle. A garment is a cut-out of
those shells:

  1. Every base vertex gets a body coordinate: which part it belongs to (torso, arm, leg,
     neck, hand, foot), how far along the limb it is (0 at shoulder or hip, 1 at elbow or
     knee, 2 at wrist or ankle), or how high up the torso (0 at hip joint, 1 at neck base).
  2. A garment is a rule over those coordinates, e.g. a T-shirt is "torso between hem and
     collar, plus arms up to 0.55". The rule is a number per vertex: positive inside the
     garment, negative outside, zero exactly on its edge.
  3. Shell faces fully inside are kept. Faces that straddle the edge are kept too, with
     their outside corners slid along the mesh edge to where the number crosses zero. That
     gives a clean hem line instead of a staircase of faces. (The first version simply
     dropped straddling faces; hems, collars and armholes came out jagged.)
  4. Every garment vertex is tied to one or two base vertices, pushed out along its normal
     by an "ease". So the garment fits any body shape, takes its skin weights from the
     body, and bends with the skeleton with no extra work.
  5. Solidify gives the cloth thickness and real hems; subdivision smooths it.
  6. Skin under the garment (the same rule, pulled in slightly) is removed.

Not done here: draping. These garments follow the body; they do not hang or fold.
"""
import numpy as np

import bpy

from . import human, materials, rig

TIGHTS = (15328, 18001)   # mesh_metadata/basemesh_vertex_groups.json: helper-tights
SKIRT = (18002, 18721)    # helper-skirt

_COORDS = None
FAR = 9.0


def _body_coordinates():
    """Per base vertex: part, torso height h, arm coordinate, leg coordinate, skirt height k.

    arm and leg coordinates run 0 at shoulder/hip, 1 at elbow/knee, 2 at wrist/ankle, and
    beyond 2 on hands and feet. They are also defined on the torso (as the projection onto
    the upper limb, mostly negative there) so armholes and leg openings cut cleanly.
    """
    global _COORDS
    if _COORDS is not None:
        return _COORDS
    bones = rig.read_rig("default")
    names = list(bones.keys())
    table = rig._weight_matrix("default", names)
    vb = human.to_blender(human.base_mesh()[0])
    joint = lambda bone: np.array(rig._position(bones[bone]["head"], vb))

    def part_of(bone):
        b = bone.split(".")[0]
        if b in ("upperarm01", "upperarm02", "lowerarm01", "lowerarm02"):
            return "arm"
        if b in ("upperleg01", "upperleg02", "lowerleg01", "lowerleg02"):
            return "leg"
        if b == "wrist" or b.startswith(("finger", "metacarpal")):
            return "hand"
        if b == "foot" or b.startswith("toe"):
            return "foot"
        if b.startswith(("spine", "breast", "clavicle", "shoulder", "pelvis")) or b == "root":
            return "torso"
        return "neck"  # neck, head and face bones

    dominant = table.argmax(axis=1)
    dom_name = np.array([names[d].split(".")[0] for d in dominant])
    part = np.array([part_of(names[d]) for d in dominant])
    left = vb[:, 0] >= 0
    coords = {}
    for limb, (a, b, c), ends, lower in (("arm", ("upperarm01", "lowerarm01", "wrist"), ("arm", "hand"), "lowerarm"),
                                         ("leg", ("upperleg01", "lowerleg01", "foot"), ("leg", "foot"), "lowerleg")):
        out = np.zeros(len(vb))
        for sd, mask in (("L", left), ("R", ~left)):
            p0, p1, p2 = joint(f"{a}.{sd}"), joint(f"{b}.{sd}"), joint(f"{c}.{sd}")
            t1 = (vb - p0) @ (p1 - p0) / np.dot(p1 - p0, p1 - p0)
            t2 = (vb - p1) @ (p2 - p1) / np.dot(p2 - p1, p2 - p1)
            on_lower = np.char.startswith(dom_name, lower) | (part == ends[1])
            value = np.where(on_lower, 1.0 + np.maximum(t2, 0.0), np.minimum(t1, 1.0))
            out[mask] = value[mask]
        coords[limb] = out
    z_hip, z_neck = joint("upperleg01.L")[2], joint("neck01")[2]
    zs = vb[SKIRT[0]:SKIRT[1] + 1, 2]
    _COORDS = {"part": part, "vb": vb, "eye": joint("eye.L"),
               "h": (vb[:, 2] - z_hip) / (z_neck - z_hip),
               "arm": coords["arm"], "leg": coords["leg"],
               "k": (zs.max() - vb[:, 2]) / (zs.max() - zs.min())}
    return _COORDS


def _garment(name, shell, field, ease, thickness, material, skin_margin=0.07, soften=0):
    covered = set(np.nonzero(field[:human.BODY_VERTS] > skin_margin)[0].tolist()) if skin_margin else set()
    return {"name": name, "shell": shell, "field": field, "ease": ease, "thickness": thickness,
            "material": material, "delete": covered, "soften": soften}


# ------------------------------------------------------------------ catalogue

def top(name="top", sleeve=0.55, hem=-0.10, collar=0.96, ease=0.008, thickness=0.0025,
        material=None, soften=0):
    """Shirt-like garment. sleeve: 0 sleeveless, 0.55 short, 1.95 long. hem: bottom edge
    relative to the hip joint (negative is lower). collar: 0.9 wide neck, 0.99 high."""
    c = _body_coordinates()
    limb = np.isin(c["part"], ("arm", "hand"))
    armhole = sleeve if sleeve > 0 else -0.10
    field = np.minimum(c["h"] - hem, collar - c["h"])
    if sleeve <= 0:
        field = np.minimum(field, armhole - c["arm"])
    field = np.where(limb, armhole - c["arm"], field)
    # soften: smoothing passes that melt the body's shape out of a thick outer garment
    return _garment(name, TIGHTS, field, ease, thickness,
                    material or materials.fabric((0.85, 0.85, 0.82), on="garment"), soften=soften)


def trousers(name="trousers", length=1.93, waist=0.20, ease=0.008, thickness=0.003,
             material=None):
    """length: 0.5 shorts, 1.0 knee, 1.93 ankle. waist: waistband height above the hip
    joint as a fraction of hip-to-neck."""
    c = _body_coordinates()
    field = waist - c["h"]
    field = np.where(np.isin(c["part"], ("leg", "foot")), np.minimum(field, length - c["leg"]), field)
    field = np.where(np.isin(c["part"], ("arm", "hand")), -FAR, field)
    return _garment(name, TIGHTS, field, ease, thickness, material or materials.denim())


def boots(name="boots", top_at=1.55, ease=0.007, thickness=0.004, material=None):
    """Soft boot or sock from the foot up to a point on the shin (1.0 knee, 2.0 ankle).
    No separate sole or heel."""
    c = _body_coordinates()
    field = np.where(np.isin(c["part"], ("leg", "foot")), c["leg"] - top_at, -FAR)
    return _garment(name, TIGHTS, field, ease, thickness,
                    material or materials.plain("Boot leather", (0.06, 0.05, 0.05), 0.45))


def skirt(name="skirt", length=0.55, ease=0.004, thickness=0.003, material=None):
    """length: fraction of waist-to-ankle. 0.35 mini, 0.55 knee, 0.95 full."""
    c = _body_coordinates()
    return _garment(name, SKIRT, length - c["k"], ease, thickness,
                    material or materials.fabric((0.25, 0.27, 0.32), on="garment"), skin_margin=None)


def collar(name="collar", low=0.88, high=1.06, ease=0.022, thickness=0.02, material=None):
    """A thick rolled collar lying on the shoulders round the neck: the base for fur trim."""
    c = _body_coordinates()
    field = np.minimum(c["h"] - low, high - c["h"])
    field = np.where(np.isin(c["part"], ("torso", "neck")), field, -FAR)
    return _garment(name, TIGHTS, field, ease, thickness,
                    material or materials.plain("Collar base", (0.78, 0.72, 0.6), 0.9),
                    skin_margin=None, soften=4)


def helmet(name="helmet", ease=0.006, thickness=0.004, material=None):
    """Close-fitting leather flying helmet: crown, back and sides of the head down past
    the ears, leaving the face open. Cut from the head's own surface, then smoothed so
    the ears do not show through."""
    c = _body_coordinates()
    vb, eye = c["vb"], c["eye"]
    crown = (vb[:, 2] - (eye[2] + 0.024)) / 0.03
    back = np.minimum((vb[:, 1] - (eye[1] + 0.085)) / 0.03, (vb[:, 2] - (eye[2] - 0.085)) / 0.03)
    field = np.maximum(crown, back)
    on_head = (c["part"] == "neck") & (vb[:, 2] > eye[2] - 0.12)
    field = np.where(on_head, field, -FAR)
    return _garment(name, (0, human.BODY_VERTS - 1), field, ease, thickness,
                    material or materials.leather("Helmet leather", (0.10, 0.075, 0.055)),
                    skin_margin=0.3, soften=12)


# ------------------------------------------------------------------ building

def _cut(garment):
    """Faces and vertex bindings of a garment, with straddling faces trimmed to the edge.

    Returns (faces as tuples of garment-vertex indices, tri[n,3], weight[n,3],
    per-face base vertex tuples for UV lookup, per-face per-corner slide info).
    """
    lo, hi = garment["shell"]
    field = garment["field"]
    shell_faces = [f for f in human.base_mesh()[2] if all(lo <= v <= hi for v in f)]
    inside = field > 0
    # For each outside vertex, the inside neighbour (along a mesh edge) it slides toward:
    # the one with the steepest change, i.e. the edge most square to the garment's edge.
    slide = {}
    for f in shell_faces:
        for i, v in enumerate(f):
            for w in (f[i - 1], f[(i + 1) % len(f)]):
                if not inside[v] and inside[w]:
                    if v not in slide or field[w] - field[v] > field[slide[v]] - field[v]:
                        slide[v] = w
    index, tri, weight, faces, sources = {}, [], [], [], []

    def vertex(v):
        if v not in index:
            index[v] = len(tri)
            if inside[v]:
                tri.append((v, v, v)); weight.append((1.0, 0.0, 0.0))
            else:
                w = slide[v]
                t = float(np.clip(field[w] / (field[w] - field[v]), 0.05, 1.0))
                tri.append((w, v, v)); weight.append((1.0 - t, t, 0.0))
        return index[v]

    for f in shell_faces:
        n_in = sum(inside[v] for v in f)
        if n_in == len(f) or (n_in >= 1 and all(inside[v] or v in slide for v in f)):
            faces.append(tuple(vertex(v) for v in f))
            sources.append(f)
    return faces, np.array(tri, dtype=int), np.array(weight), sources


def _vertex_normals(verts, faces):
    normals = np.zeros_like(verts)
    for f in faces:
        n = np.cross(verts[f[1]] - verts[f[0]], verts[f[2]] - verts[f[0]])
        for v in f:
            normals[v] += n
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    return normals / np.maximum(length, 1e-12)


def build(scene, base_verts, garment, name, parent=None):
    """Create the garment object on a given (morphed) body. Returns (object, binding)."""
    all_bl = human.to_blender(base_verts)
    _, uvs, all_faces, all_face_uvs = human.base_mesh()
    uv_of = {f: fu for f, fu in zip(all_faces, all_face_uvs)}
    faces, tri, weight, sources = _cut(garment)
    verts = (all_bl[tri] * weight[:, :, None]).sum(axis=1)
    verts = verts + garment["ease"] * _vertex_normals(verts, faces)

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts.tolist(), [], faces)
    # UVs: a slid corner takes the UV part-way along the same edge, when that edge is in
    # this face; otherwise it keeps its own UV (a small stretch at the hem).
    flat = []
    for face, src in zip(faces, sources):
        for corner, (gv, bv) in enumerate(zip(face, src)):
            uv = uvs[uv_of[src][corner]]
            w0 = tri[gv][0]
            if weight[gv][1] > 0 and w0 in src:
                uv_in = uvs[uv_of[src][src.index(w0)]]
                uv = uv_in + weight[gv][1] * (uv - uv_in)
            flat.extend(uv)
    mesh.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array(flat))
    mesh.update()
    mesh.shade_smooth()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    mesh.materials.append(garment["material"])
    if garment.get("soften"):
        relax = obj.modifiers.new("Soften", "SMOOTH")
        relax.factor = 0.7
        relax.iterations = garment["soften"]
    solid = obj.modifiers.new("Thickness", "SOLIDIFY")
    solid.thickness = garment["thickness"]
    solid.offset = 1.0  # grow outward, so the inner face stays clear of the skin
    smooth = obj.modifiers.new("Subdivision", "SUBSURF")
    smooth.levels, smooth.render_levels = 1, 2
    if parent is not None:
        obj.parent = parent
    return obj, {"tri": tri, "weight": weight, "delete": garment["delete"]}
