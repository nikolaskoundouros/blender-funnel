"""Human characters with outfits, built from MakeHuman's public-domain (CC0) data.

This is our own reader for the MakeHuman file formats. It does not use the MPFB add-on's
code; it follows the format documentation in makehumancommunity/mpfb2 (docs/fileformats)
and every step is checked in experiments/verify_human.py.

How it works:
  1. One base mesh (19,158 vertices). The first 13,380 are the body; the rest are helper
     geometry that clothes, hair and joints attach to. Helpers are never rendered.
  2. Body shape = base mesh + a weighted sum of "targets" (per-vertex offsets). Gender,
     age, muscle, weight, height and ethnicity each select a few targets and weights.
  3. Every outfit, hairstyle, eye or eyebrow is a separate mesh whose vertices are each
     tied to three base-mesh vertices. Re-evaluating that tie on the morphed body fits
     the item to any body shape.
  4. Each item lists the body vertices it covers, so the skin underneath can be removed
     and does not poke through.

All maths here is in MakeHuman coordinates (Y up, decimetres). Conversion to Blender
(Z up, metres) happens once, in to_blender().
"""
import gzip
import json
import math
import os

import bpy
import numpy as np

ASSETS = os.environ.get(
    "FUNNEL_ASSETS",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets"))
DATA = os.path.join(ASSETS, "mpfb_data")
PACK = os.path.join(ASSETS, "system")
BODY_VERTS = 13380  # mesh_metadata/basemesh_vertex_groups.json: "body": [[0, 13379]]
SCALE = 0.1         # decimetres to metres


BINDINGS = {}  # filled by build_human for the most recently built character

# ------------------------------------------------------------------ file readers

def read_obj(path):
    """Minimal Wavefront OBJ reader: vertices, UVs, faces, per-face UV indices."""
    verts, uvs, faces, face_uvs = [], [], [], []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("v "):
                verts.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("vt "):
                uvs.append([float(x) for x in line.split()[1:3]])
            elif line.startswith("f "):
                vi, ti = [], []
                for token in line.split()[1:]:
                    parts = token.split("/")
                    vi.append(int(parts[0]) - 1)
                    ti.append(int(parts[1]) - 1 if len(parts) > 1 and parts[1] else -1)
                faces.append(tuple(vi))
                face_uvs.append(tuple(ti))
    return np.array(verts), np.array(uvs), faces, face_uvs


def read_target(path):
    """A target file: one line per moved vertex, "index dx dy dz" in MakeHuman axes."""
    opener = gzip.open if path.endswith(".gz") else open
    idx, off = [], []
    with opener(path, "rt") as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split()
            idx.append(int(parts[0]))
            off.append([float(parts[1]), float(parts[2]), float(parts[3])])
    return np.array(idx, dtype=int), np.array(off, dtype=float).reshape(-1, 3)  # some targets are empty


def read_mhmat(path):
    """Material file: "key value" lines. Texture paths are relative to the file."""
    out = {"dir": os.path.dirname(path)}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) >= 2 and not line.startswith("#"):
                out.setdefault(parts[0], " ".join(parts[1:]))
    return out


def read_mhclo(path):
    """Fitted-item file: scale references, one binding per item vertex, covered body vertices."""
    info = {"dir": os.path.dirname(path), "scale": {}, "delete": set(), "material": None}
    tri, weight, offset = [], [], []
    section = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            parts = raw.split()
            if not parts:
                section = None  # a blank line ends the current block
                continue
            key = parts[0]
            if key == "#":
                continue
            if key == "material":  # may legally appear inside the vertex block
                info["material"] = parts[1]
                continue
            if key.startswith("vertexboneweights"):
                continue
            if section == "verts" and _is_number(key):
                if len(parts) == 1:  # exact match to one base vertex
                    v = int(parts[0])
                    tri.append((v, v, v)); weight.append((1.0, 0.0, 0.0)); offset.append((0.0, 0.0, 0.0))
                else:
                    tri.append(tuple(int(p) for p in parts[0:3]))
                    weight.append(tuple(float(p) for p in parts[3:6]))
                    offset.append(tuple(float(p) for p in parts[6:9]))
                continue
            if section == "delete" and _is_number(key):
                i = 0
                while i < len(parts):
                    if i + 2 < len(parts) and parts[i + 1] == "-":
                        info["delete"].update(range(int(parts[i]), int(parts[i + 2]) + 1))
                        i += 3
                    else:
                        info["delete"].add(int(parts[i]))
                        i += 1
                continue
            section = None
            if key == "verts" and len(parts) > 1:
                section = "verts"
            elif key == "delete_verts":
                section = "delete"
            elif key in ("x_scale", "y_scale", "z_scale"):
                info["scale"][key[0]] = (int(parts[1]), int(parts[2]), float(parts[3]))
            elif key in ("name", "obj_file"):
                info[key] = parts[1]
    info["tri"] = np.array(tri, dtype=int)
    info["weight"] = np.array(weight)
    info["offset"] = np.array(offset)
    return info


def _is_number(text):
    try:
        float(text)
        return True
    except ValueError:
        return False


# ------------------------------------------------------------------ body shape

_MACRO = None
_BASE = None


def base_mesh():
    """The unmorphed base mesh, read once: (verts, uvs, faces, face_uvs)."""
    global _BASE
    if _BASE is None:
        _BASE = read_obj(os.path.join(DATA, "3dobjs", "base.obj"))
    return _BASE


def _component_weights(name, value):
    """Split one 0..1 slider into its two neighbouring named extremes."""
    global _MACRO
    if _MACRO is None:
        with open(os.path.join(DATA, "targets", "macrodetails", "macro.json")) as fh:
            _MACRO = json.load(fh)["macrotargets"]
    for part in _MACRO[name]["parts"]:
        if part["lowest"] <= value <= part["highest"]:
            t = (value - part["lowest"]) / (part["highest"] - part["lowest"])
            return {part["low"]: 1.0 - t, part["high"]: t}
    return {}


def macro_targets(gender=0.5, age=0.5, muscle=0.5, weight=0.5, height=0.5, proportions=0.5,
                  cupsize=0.5, firmness=0.5, african=1 / 3, asian=1 / 3, caucasian=1 / 3):
    """Translate body sliders into a list of (target file, weight).

    Each slider is 0..1. gender: 0 female, 1 male. age: 0 baby, 0.19 child, 0.5 young
    adult, 1 old. A target's weight is the product of the weights of its name parts.
    """
    c = {k: _component_weights(k, v) for k, v in dict(
        gender=gender, age=age, muscle=muscle, weight=weight, height=height,
        proportions=proportions, cupsize=cupsize, firmness=firmness).items()}
    total = african + asian + caucasian
    race = {"african": african / total, "asian": asian / total, "caucasian": caucasian / total}
    macro = os.path.join(DATA, "targets", "macrodetails")
    out = []

    def add(folder, names_and_weights, prefix=""):
        combos = [("", 1.0)]
        for group in names_and_weights:
            combos = [(f"{n}-{label}" if n else label, w * gw)
                      for n, w in combos for label, gw in group.items() if label and gw > 1e-6]
        for name, w in combos:
            path = os.path.join(folder, f"{prefix}{name}.target.gz")
            if os.path.exists(path):  # e.g. "average" breast targets do not exist: no change
                out.append((path, w))

    add(macro, [race, c["gender"], c["age"]])
    add(macro, [c["gender"], c["age"], c["muscle"], c["weight"]], prefix="universal-")
    add(os.path.join(macro, "height"), [c["gender"], c["age"], c["muscle"], c["weight"], c["height"]])
    add(os.path.join(macro, "proportions"),
        [c["gender"], c["age"], c["muscle"], c["weight"], c["proportions"]])
    add(os.path.join(DATA, "targets", "breast"),
        [c["gender"], c["age"], c["muscle"], c["weight"], c["cupsize"], c["firmness"]])
    return out


EXPRESSION_UNITS = os.path.join(DATA, "targets", "expression", "units")
# Faceunits 01 (CC0): 52 ARKit-named targets for this base mesh, one file each, no ethnicity
# split. Fetched by tools/fetch_assets.sh; see notes/facial-mocap-plan.md.
FACEUNITS = os.path.join(os.path.dirname(DATA), "faceunits01", "targets", "faceunits")
# Visemes 01 (CC0): 22 Microsoft-style viseme targets, named by the sounds they cover.
VISEMES = os.path.join(os.path.dirname(DATA), "visemes01", "targets", "visemes")


def morphed_base(expression=None, sculpt=None, **sliders):
    """Base-mesh vertex positions (MakeHuman axes) for the given sliders, feet on the ground.

    expression: optional {unit name: weight 0..1} using MakeHuman's facial expression
    units, e.g. {"mouth-corner-puller": 0.8, "mouth-open": 0.3}. Names are the files in
    targets/expression/units/<ethnicity>/ without ".target.gz"; ARKit names such as
    {"jawOpen": 1.0} use the Faceunits 01 pack, viseme names such as {"p_b_m_21": 1.0} the
    Visemes 01 pack. The ethnicity folder is
    blended by the same african/asian/caucasian sliders as the body."""
    verts = base_mesh()[0].copy()
    for path, w in macro_targets(**sliders):
        idx, off = read_target(path)
        verts[idx] += w * off
    if sculpt:
        # code-sculpted shape edits (recipes/sculpt.py), applied to the identity before
        # any expression, with the feet put back on the ground first
        from . import sculpt as sculpt_mod
        verts[:, 1] -= verts[:BODY_VERTS, 1].min()
        verts = sculpt_mod.apply(verts, sculpt)
    if expression:
        race = {k: sliders.get(k, 1 / 3) for k in ("african", "asian", "caucasian")}
        total = sum(race.values()) or 1.0
        for unit, amount in expression.items():
            extra = [os.path.join(d, f"{unit}.target") for d in (FACEUNITS, VISEMES)]
            extra = [x for x in extra if os.path.exists(x)]
            if unit[:1].islower() and extra:
                idx, off = read_target(extra[0])                 # ARKit name or viseme
                verts[idx] += amount * off
                continue
            for folder, share in race.items():
                if share <= 0:
                    continue
                path = os.path.join(EXPRESSION_UNITS, folder, f"{unit}.target.gz")
                if not os.path.exists(path):
                    raise FileNotFoundError(f"no expression unit {unit!r}; see {EXPRESSION_UNITS}")
                idx, off = read_target(path)
                verts[idx] += amount * share / total * off
    verts[:, 1] -= verts[:BODY_VERTS, 1].min()
    return verts


# ------------------------------------------------------------------ fitting

def fit(item, base_verts):
    """Positions of a fitted item's vertices on a given body.

    position = sum of three base vertices x weights + offset x per-axis scale, where the
    scale is the body's current size between two reference vertices divided by the size
    recorded when the item was made.
    """
    scale = np.ones(3)
    for axis, key in enumerate("xyz"):
        if key in item["scale"]:
            a, b, recorded = item["scale"][key]
            scale[axis] = abs(base_verts[b, axis] - base_verts[a, axis]) / recorded
    corners = base_verts[item["tri"]]                       # (n, 3 corners, 3 axes)
    return (corners * item["weight"][:, :, None]).sum(axis=1) + item["offset"] * scale


# ------------------------------------------------------------------ Blender objects

def to_blender(verts_mh):
    """MakeHuman (x, y up, z front) decimetres -> Blender (x, y back, z up) metres."""
    return np.stack([verts_mh[:, 0], -verts_mh[:, 2], verts_mh[:, 1]], axis=1) * SCALE


def _mesh_object(scene, name, verts_mh, faces, uvs, face_uvs):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(to_blender(verts_mh).tolist(), [], faces)
    if len(uvs) and face_uvs and all(i >= 0 for f in face_uvs for i in f):
        layer = mesh.uv_layers.new(name="UVMap")
        flat = np.array([uvs[i] for f in face_uvs for i in f]).ravel()
        layer.data.foreach_set("uv", flat)
    mesh.update()
    mesh.shade_smooth()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    return obj


def material_from_mhmat(path, name=None):
    """Principled material from a MakeHuman material file (colour texture, alpha, normal map)."""
    info = read_mhmat(path)
    mat = bpy.data.materials.new(name or info.get("name", "material"))
    if mat.node_tree is None:
        mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.6
    if "diffuseColor" in info:
        r, g, b = (float(x) for x in info["diffuseColor"].split()[:3])
        bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    tex_path = info.get("diffuseTexture")
    if tex_path:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(os.path.join(info["dir"], tex_path), check_existing=True)
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        if info.get("transparent", "False") == "True":  # hair cards, lashes, brows
            links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    normal_path = info.get("normalmapTexture")
    if normal_path and os.path.exists(os.path.join(info["dir"], normal_path)):
        ntex = nodes.new("ShaderNodeTexImage")
        ntex.image = bpy.data.images.load(os.path.join(info["dir"], normal_path), check_existing=True)
        ntex.image.colorspace_settings.name = "Non-Color"
        nmap = nodes.new("ShaderNodeNormalMap")
        links.new(ntex.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def find_asset(kind, name):
    """Path to an item's .mhclo (or a skin's .mhmat) in the asset pack."""
    ext = ".mhmat" if kind == "skins" else ".mhclo"
    path = os.path.join(PACK, kind, name, name + ext)
    if not os.path.exists(path):
        have = sorted(os.listdir(os.path.join(PACK, kind)))
        raise FileNotFoundError(f"no {kind} asset {name!r}; available: {have}")
    return path


def add_item(scene, base_verts, kind, name, material_path=None, parent=None):
    """Fit one asset (clothes, hair, eyes, ...) to the body and add it to the scene.

    Returns (object, parsed item). The item's "delete" set lists covered body vertices
    and its "tri"/"weight" arrays tie each vertex to the base mesh.
    """
    item = read_mhclo(find_asset(kind, name))
    _, uvs, faces, face_uvs = read_obj(os.path.join(item["dir"], item["obj_file"]))
    obj = _mesh_object(scene, name, fit(item, base_verts), faces, uvs, face_uvs)
    mat_file = material_path or (os.path.join(item["dir"], item["material"]) if item["material"] else None)
    if mat_file and os.path.exists(mat_file):
        obj.data.materials.append(material_from_mhmat(mat_file, name))
    if parent is not None:
        obj.parent = parent
    return obj, item


def build_human(scene, name="Human", skin="young_caucasian_female", outfit=(), hair=None,
                eyes="brown", eyebrows="eyebrow001", eyelashes="eyelashes01", teeth=True, tongue=True,
                location=(0.0, 0.0, 0.0), facing_deg=0.0, pose=None, rig_name="default",
                collider=False, expression=None, sculpt=None, **sliders):
    """A complete standing character: body, skin, face details, hair and outfit.

    outfit: names from assets/system/clothes, e.g. ("female_casualsuit01", "shoes01").
    pose: None keeps the modelling pose (arms out). A name from rig.POSES, or a list of
    pose steps (see rig.apply_pose), adds a skeleton and poses the character.
    rig_name: "default" (163 bones, with face and fingers), "game_engine" (53) or
    "mixamo" (52, Mixamo bone names). Named poses in rig.POSES are for "default".
    collider: also make "<name>_collider", a complete copy of the body that follows the
    skeleton but is invisible in renders. Cloth needs it: the visible body has holes
    where skin under garments was removed, and cloth falls straight through them.
    facing_deg: turn about the vertical axis; 0 faces the -Y direction.
    sliders: see macro_targets(). Returns the root object (the skeleton if posed, else the
    body); everything else is parented to it.
    """
    base_verts = morphed_base(expression=expression, sculpt=sculpt, **sliders)
    _, uvs, faces, face_uvs = base_mesh()

    covered = set()
    # Outfit entries are asset names, or garment specs made by recipes/garments.py.
    pending = [("clothes", n, None) for n in outfit if isinstance(n, str)]
    generated = [g for g in outfit if not isinstance(g, str)]
    if hair:
        pending.append(("hair", hair, None))
    if eyes:
        pending.append(("eyes", "low-poly", os.path.join(PACK, "eyes", "materials", eyes + ".mhmat")))
    if eyebrows:
        pending.append(("eyebrows", eyebrows, None))
    if eyelashes:
        pending.append(("eyelashes", eyelashes, None))
    if teeth:
        pending.append(("teeth", "teeth_base", None))
    if tongue:
        # MakeHuman tongue01 (CC0 system assets). Without it an open mouth showed a black
        # void behind the teeth (runs/019-voice-lipsync, 14 Nov 2026).
        pending.append(("tongue", "tongue01", None))

    # Body: only body faces, minus any face fully covered by an item.
    items = [(k, n, m, read_mhclo(find_asset(k, n))) for k, n, m in pending]
    for _, _, _, item in items:
        covered |= item["delete"]
    for garment in generated:
        covered |= garment["delete"]
    keep = [i for i, f in enumerate(faces)
            if all(v < BODY_VERTS for v in f) and not all(v in covered for v in f)]
    body = _mesh_object(scene, name, base_verts[:BODY_VERTS], [faces[i] for i in keep],
                        uvs, [face_uvs[i] for i in keep])
    body.data.materials.append(material_from_mhmat(find_asset("skins", skin), f"{name}_skin"))
    fitted = []
    for kind, item_name, mat in pending:
        obj, item = add_item(scene, base_verts, kind, item_name, mat, parent=body)
        obj.name = f"{name}_{item_name}"
        fitted.append((obj, item))

    if collider:
        whole = [i for i, f in enumerate(faces) if all(v < BODY_VERTS for v in f)]
        shape = _mesh_object(scene, f"{name}_collider", base_verts[:BODY_VERTS],
                             [faces[i] for i in whole], uvs, [face_uvs[i] for i in whole])
        shape.parent = body
        for flag in ("visible_camera", "visible_diffuse", "visible_glossy",
                     "visible_transmission", "visible_volume_scatter", "visible_shadow"):
            setattr(shape, flag, False)
        every = np.arange(BODY_VERTS)
        fitted.append((shape, {"tri": np.stack([every, every, every], axis=1),
                               "weight": np.tile(np.array([1.0, 0.0, 0.0]), (BODY_VERTS, 1)),
                               "delete": set()}))

    if generated:
        from . import garments  # imported here: garments.py imports this module
        for garment in generated:
            fitted.append(garments.build(scene, base_verts, garment, f"{name}_{garment['name']}",
                                         parent=body))
            fitted.extend(garments.build_extras(scene, base_verts, garment, f"{name}_{garment['name']}",
                                                parent=body))

    root = body
    if pose is not None:
        from . import rig  # imported here: rig.py imports this module
        root = rig.attach(scene, name, base_verts, body, fitted, rig_name=rig_name)
        rig.apply_pose(root, pose)
    root.location = location
    root.rotation_euler = (0.0, 0.0, math.radians(facing_deg))
    # Kept for later steps such as cloth pinning: {object name: binding to the base mesh}.
    BINDINGS.clear()
    BINDINGS.update({obj.name: item for obj, item in fitted})
    root["funnel_height_m"] = float(base_verts[:BODY_VERTS, 1].max() * SCALE)
    return root
