"""Whole characters for scenes: body, face, hair, outfit and face animation keys.

Built from the looks and outfit routes chosen in earlier runs, so a scene places
characters with one call each. Each function adds the face keys (Faceunits and visemes)
right after building: human.BINDINGS only holds the most recently built character.

Characters for the "My Mom Cracked The Dinosaur" two-character test (run 020):
  curly_boy: the boy of runs 012-015 (route E tee, track pants with stripe, yellow shoes).
  mom: PLACEHOLDER until the reference clip is available again; generic adult woman.
"""
import bmesh
import numpy as np
from mathutils import Vector

from . import face_anim, garments, human, looks, materials, prints, sculpt

TEE = (0.74, 0.74, 0.70)
PANTS = (0.012, 0.035, 0.17)        # royal blue (owner's change from the reference green)
STRIPE = (0.55, 0.025, 0.02)        # red
SHOE = (0.62, 0.38, 0.04)           # yellow
MOM_SLIDERS = dict(gender=0.0, age=0.6, muscle=0.45, weight=0.5, height=0.5,
                   caucasian=1, african=0, asian=0)   # about 38 years (age 0.5 = 25, 1.0 = 90)


def _face_keys(root, **sliders):
    face_anim.add_faceunit_keys(root, **sliders)
    face_anim.add_faceunit_keys(root, units=face_anim.VISEMES, **sliders)
    face_anim.set_units(root, face_anim.REST_OFFSET)


def curly_boy(scene, name="Boy", location=(0.0, 0.0, 0.0), facing_deg=0.0, pose="relaxed",
              hair_children=150000, face_keys=True):
    """The curly-haired boy, as finished in run 013 (route E) plus run 012's hair.
    Returns (root, base_verts)."""
    S = looks.CURLY_BOY_SLIDERS
    base_verts = human.morphed_base(**S)
    cut = {"thigh": 0.088, "knee": 0.074, "ankle": 0.062, "folds": 0.005}
    baggy = garments.baggy_ease(outer=0.012, inner=0.008, waist=0.010, ankle=0.006)
    jersey = lambda n, rgb: materials.fabric(rgb, name=n, thread=0.0008, on="garment", sheen=0.25)
    pants = garments.trousers(name="pants", length=1.93, waist=0.0, ease=baggy, smooth_shell=30, thickness=0.003,
                              cut=cut, material=jersey(f"{name}_Pants", PANTS))
    stripe = garments.leg_patch("stripe", s=(0.02, 1.92), theta=(84, 96), ease=baggy + 0.0035, thickness=0.0008,
                                material=jersey(f"{name}_Stripe", STRIPE), smooth_shell=30, cut=cut, corner=0.002,
                                step=0.004)
    edits = [sculpt.clothes(sculpt.inflate("belly", 0.20, 0.03)),
             sculpt.clothes(sculpt.inflate("chest", 0.17, 0.016)),
             sculpt.clothes(sculpt.inflate("shoulder.L", 0.09, 0.008, mirror=True))]
    head = looks.head_pose(*looks.CURLY_BOY_HEAD) if pose == "relaxed" else []
    from . import rig
    pose_steps = (rig.POSES["relaxed"] + head) if pose == "relaxed" else pose
    root = human.build_human(scene, name=name, skin="young_caucasian_male", hair=None, eyes="green",
                             outfit=(pants, stripe, "male_casualsuit06", "shoes05"), pose=pose_steps,
                             sculpt=edits, location=location, facing_deg=facing_deg, **S)
    kids = {o.name: o for o in root.children_recursive}
    tee = kids[f"{name}_male_casualsuit06"]
    tee.name = f"{name}_tee"
    _drop_lowest_piece(tee)                       # the asset's jeans
    tb = next(n for n in tee.data.materials[0].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for l in [l for l in tee.data.materials[0].node_tree.links if l.to_socket == tb.inputs["Base Color"]]:
        tee.data.materials[0].node_tree.links.remove(l)
    tb.inputs["Base Color"].default_value = TEE + (1.0,)
    tb.inputs["Roughness"].default_value = 0.85
    body = looks.body_of(root, name)
    looks.freckled_skin(body, base_verts)
    looks.odd_eyes(root, name)
    _tint_shoes(kids[f"{name}_shoes05"], SHOE)
    marks = sculpt.landmarks(human.to_blender(base_verts))
    want = Vector((0.065, 0.0, float(marks["chest"][2]) + 0.11))
    tco = [v.co for v in tee.data.vertices]
    cands = [c for c in tco if abs(c.x - want.x) < 0.02 and abs(c.z - want.z) < 0.02 and c.y < 0]
    centre = min(cands, key=lambda c: c.y) if cands else min(tco, key=lambda c: (c - want).length)
    uv0, inv, _, _ = prints.fit_uv_frame(tee, np.array(centre), radius=0.06)
    prints.apply(tee.data.materials[0], prints.graphic_image(prints.sunrise_badge, name=f"{name}_Badge"), uv0, inv,
                 width=0.085)
    if face_keys:
        _face_keys(root, **S)
    if hair_children:
        looks.orange_curls(scene, base_verts, armature=root if root.type == "ARMATURE" else None,
                           parent=root, children=hair_children)
    return root, base_verts


def mom(scene, name="Mom", location=(0.0, 0.0, 0.0), facing_deg=0.0, pose="relaxed", face_keys=True):
    """PLACEHOLDER mother: an adult woman in MakeHuman's CC0 casual outfit and long hair.
    To be matched to the reference clip once it is available. Returns (root, base_verts)."""
    from . import rig
    base_verts = human.morphed_base(**MOM_SLIDERS)
    root = human.build_human(scene, name=name, skin="young_caucasian_female", hair="long01", eyes="brown",
                             outfit=("female_casualsuit02", "shoes01"),
                             pose=rig.POSES["relaxed"] if pose == "relaxed" else pose,
                             location=location, facing_deg=facing_deg, **MOM_SLIDERS)
    if face_keys:
        _face_keys(root, **MOM_SLIDERS)
    return root, base_verts


def _drop_lowest_piece(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    seen, pieces = set(), []
    for v0 in bm.verts:
        if v0.index in seen:
            continue
        stack, piece = [v0], []
        seen.add(v0.index)
        while stack:
            v = stack.pop()
            piece.append(v)
            for e in v.link_edges:
                o = e.other_vert(v)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
        pieces.append(piece)
    low = min(pieces, key=lambda pc: sum(v.co.z for v in pc) / len(pc))
    bmesh.ops.delete(bm, geom=low, context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()


def _tint_shoes(shoes, rgb, sole=0.025):
    """Multiply the shoe colour above the sole (object height over `sole`), as run 013."""
    mat = shoes.data.materials[0]
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    src = next(l.from_socket for l in links if l.to_socket == bsdf.inputs["Base Color"])
    geo = nodes.new("ShaderNodeNewGeometry")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(geo.outputs["Position"], sep.inputs[0])
    upper = nodes.new("ShaderNodeMath")
    upper.operation = "GREATER_THAN"
    links.new(sep.outputs["Z"], upper.inputs[0])
    upper.inputs[1].default_value = sole
    tint = nodes.new("ShaderNodeMix")
    tint.data_type, tint.blend_type = "RGBA", "MULTIPLY"
    links.new(upper.outputs[0], tint.inputs["Factor"])
    links.new(src, tint.inputs["A"])
    tint.inputs["B"].default_value = (rgb[0] * 1.3, rgb[1] * 1.3, rgb[2] * 1.3, 1.0)
    links.new(tint.outputs["Result"], bsdf.inputs["Base Color"])
