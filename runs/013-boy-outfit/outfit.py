"""Run 013: the curly-haired boy's body and outfit.

Reference: "My Mom Cracked The Dinosaur" (owner-supplied clip, kept out of git): a loose
off-white crew-neck T-shirt with a small chest print, loose track pants with a stripe down
the outside of each leg, yellow trainers with white soles. Owner's change: blue track pants
with a red stripe instead of green with yellow.

Usage: python runs/013-boy-outfit/outfit.py [width height samples]
Environment: VIEWS (full,front_upper,back), OUT, HAIR=0 to skip the hair for speed.
"""
import json
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from recipes import (accessories, camera, cloth, color, garments, human, lighting, looks, materials,  # noqa: E402
                     prints, render, sculpt, stage, world)
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402
import numpy as np  # noqa: E402

W, H, SAMPLES = (int(a) for a in sys.argv[1:4]) if len(sys.argv) > 3 else (432, 640, 32)
env = lambda k, d: type(d)(os.environ.get(k, d))
S = looks.CURLY_BOY_SLIDERS
SMOOTH = 30

# Colours (scene-linear). Reference measured (linear, displayed): green pants 0.006/0.085/0.03,
# yellow 0.54/0.33/0.05, all matte (highlight ratio 1.13). Pants recoloured on request.
TEE = (0.74, 0.74, 0.70)
PANTS = (0.012, 0.035, 0.17)        # royal blue, about as bright as the reference green
STRIPE = (0.55, 0.025, 0.02)        # red
SHOE = (0.62, 0.38, 0.04)           # yellow

scene = stage.new_scene()
base_verts = human.morphed_base(**S)
# Track pants: loose straight legs gathered at the ankle; child-sized version of run 009's cut.
CUT = {"thigh": 0.088, "knee": 0.074, "ankle": 0.062, "folds": 0.005}
baggy = garments.baggy_ease(outer=0.012, inner=0.008, waist=0.010, ankle=0.006)
jersey = lambda name, rgb: materials.fabric(rgb, name=name, thread=0.0008, on="garment", sheen=0.25)
pants = garments.trousers(name="pants", length=1.93, waist=env("WAIST", 0.0), ease=baggy, smooth_shell=SMOOTH, thickness=0.003, cut=CUT,
                          material=jersey("Pants", PANTS))
# Out past the trousers' 3 mm thickness (at +1.2 mm it was hidden inside them).
stripe = garments.leg_patch("stripe", s=(0.02, 1.92), theta=(84, 96), ease=baggy + 0.0035, thickness=0.0008,
                            material=jersey("Stripe", STRIPE), smooth_shell=SMOOTH, cut=CUT, corner=0.002,
                            step=0.004)
# Loose untucked tee: short sleeves to just above the elbow, hem below the hip.
tee = garments.top(name="tee", sleeve=0.85, collar=0.965, hem=env("HEM", -0.03 if env("DRAPE", 1) else 0.0), ease=garments.tee_ease(hem=env("HEM_EASE", 0.06)) if env("DRAPE", 1) else 0.012, thickness=0.003,
                   smooth_shell=SMOOTH, material=jersey("Tee", TEE))

started = time.time()
from recipes import rig as _rig  # noqa: E402
ARM = env("ARM", 0.2)    # how far the arms hang out from the sides (0.2 is rig.POSES["relaxed"])
pose = looks.head_pose(*looks.CURLY_BOY_HEAD) + _rig._arm("L", (ARM, 0.0, -1.0), (ARM * 0.5, -0.2, -1.0)) \
    + _rig._arm("R", (ARM, 0.0, -1.0), (ARM * 0.5, -0.2, -1.0))
if env("NOPOSE", 0):
    pose = []
if env("NORIG", 0):
    pose = None
# The tee: a ready-made, modelled T-shirt (MakeHuman's male_casualsuit06, CC0; its jeans
# are removed) loosened by sculpting the clothing layer only (owner's suggestion, after
# draping a generated shell kept riding up, steps 3 to 10).
TEE_MODE = os.environ.get("TEE", "asset")
EDITS = [sculpt.clothes(sculpt.inflate("belly", 0.20, env("LOOSE_BELLY", 0.03))),
         sculpt.clothes(sculpt.inflate("chest", 0.17, env("LOOSE_CHEST", 0.016))),
         sculpt.clothes(sculpt.inflate("shoulder.L", 0.09, env("LOOSE_SLEEVE", 0.008), mirror=True))]
if TEE_MODE == "asset":
    outfit, edits = (pants, stripe, "male_casualsuit06", "shoes05"), EDITS
else:
    outfit, edits = (pants, stripe, tee, "shoes05"), None
boy = human.build_human(scene, name="Boy", skin="young_caucasian_male", hair=None, eyes="green",
                        outfit=outfit, pose=pose, collider=bool(env("DRAPE", 1)) and TEE_MODE != "asset",
                        sculpt=edits, **S)
if TEE_MODE == "asset":
    import bmesh  # noqa: E402
    tee_obj = next(o for o in boy.children_recursive if o.name == "Boy_male_casualsuit06")
    tee_obj.name = "Boy_tee"
    bm = bmesh.new(); bm.from_mesh(tee_obj.data); bm.verts.ensure_lookup_table()
    seen, pieces = set(), []
    for v0 in bm.verts:
        if v0.index in seen:
            continue
        stack, piece = [v0], []
        seen.add(v0.index)
        while stack:
            v = stack.pop(); piece.append(v)
            for e in v.link_edges:
                o = e.other_vert(v)
                if o.index not in seen:
                    seen.add(o.index); stack.append(o)
        pieces.append(piece)
    jeans = min(pieces, key=lambda pc: sum(v.co.z for v in pc) / len(pc))
    bmesh.ops.delete(bm, geom=jeans, context="VERTS")
    bm.to_mesh(tee_obj.data); bm.free()
    # plain off-white: drop the logo texture, keep the modelled fold detail (normal map)
    tmat = tee_obj.data.materials[0]
    tb = next(n for n in tmat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for l in [l for l in tmat.node_tree.links if l.to_socket == tb.inputs["Base Color"]]:
        tmat.node_tree.links.remove(l)
    tb.inputs["Base Color"].default_value = TEE + (1.0,)
    tb.inputs["Roughness"].default_value = 0.85
body = looks.body_of(boy, "Boy")
looks.freckled_skin(body, base_verts)
looks.odd_eyes(boy, "Boy")

# Trainers: tint the white shoe asset yellow above the sole (object height over 2.5 cm).
shoes = next(o for o in boy.children_recursive if o.name == "Boy_shoes05")
smat = shoes.data.materials[0]
nodes, links = smat.node_tree.nodes, smat.node_tree.links
bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
src = next(l.from_socket for l in links if l.to_socket == bsdf.inputs["Base Color"])
geo = nodes.new("ShaderNodeNewGeometry")
sep = nodes.new("ShaderNodeSeparateXYZ"); links.new(geo.outputs["Position"], sep.inputs[0])
upper = nodes.new("ShaderNodeMath"); upper.operation = "GREATER_THAN"
links.new(sep.outputs["Z"], upper.inputs[0]); upper.inputs[1].default_value = env("SOLE", 0.025)
tint = nodes.new("ShaderNodeMix"); tint.data_type = "RGBA"; tint.blend_type = "MULTIPLY"
links.new(upper.outputs[0], tint.inputs["Factor"]); links.new(src, tint.inputs["A"])
tint.inputs["B"].default_value = (SHOE[0] * 1.3, SHOE[1] * 1.3, SHOE[2] * 1.3, 1.0)
links.new(tint.outputs["Result"], bsdf.inputs["Base Color"])

# Chest print on his left chest, following the cloth (see recipes/prints.py).
tee_obj = next(o for o in boy.children_recursive if o.name == "Boy_tee")
marks = sculpt.landmarks(human.to_blender(base_verts))
tco = [v.co for v in tee_obj.data.vertices]
want = Vector((0.065, 0.0, float(marks["chest"][2]) + env("PRINT_UP", 0.11)))
cands = [c for c in tco if abs(c.x - want.x) < 0.012 and abs(c.z - want.z) < 0.012]
centre = min(cands, key=lambda c: c.y) if cands else min(tco, key=lambda c: (c - want).length)
uv0, inv, fit_err, used = prints.fit_uv_frame(tee_obj, np.array(centre), radius=0.06)
badge = prints.graphic_image(prints.sunrise_badge, name="Badge")
prints.apply(tee_obj.data.materials[0], badge, uv0, inv, width=env("PRINT_W", 0.085))
print_info = {"print_uv_fit_error": round(fit_err, 5), "print_fit_vertices": used}
sim_seconds = 0
if env("DRAPE", 1) and TEE_MODE != "asset":
    # Route B (playbook): a roomy shell draped as cotton. A stiff shell gave square, padded
    # shoulders (steps 1 and 2). Pin the yoke and the tops of the sleeves; the rest hangs.
    tee_obj = next(o for o in boy.children_recursive if o.name == "Boy_tee")
    binding = human.BINDINGS[tee_obj.name]
    h = garments.coordinate(binding, "h")
    on_arm = np.isin(garments.part(binding), ("arm", "hand"))
    arm = garments.coordinate(binding, "arm")
    pin = np.where(on_arm, np.clip((0.20 - arm) / 0.14, 0.0, 1.0), np.clip((h - env("PIN_H", 0.80)) / 0.06, 0.0, 1.0))
    # Start the shirt clear of the trousers. Where the trousers flare at the hips the
    # shell began inside them, and cloth that starts inside a collider stays trapped
    # (step 3: trousers showing through) or is shoved up (step 4: a crop top).
    pants_obj = next(o for o in boy.children_recursive if o.name == "Boy_pants")
    pv = [Vector(v.co) for v in pants_obj.data.vertices]
    tree = BVHTree.FromPolygons(pv, [tuple(f.vertices) for f in pants_obj.data.polygons])
    clear = env("CLEAR", 0.010)
    pushed = 0
    for v in tee_obj.data.vertices:
        hit = tree.find_nearest(v.co)
        if hit[0] is None:
            continue
        q, n = hit[0], hit[1]
        outward = Vector((n.x, n.y, 0.0)).normalized() if abs(n.z) < 0.95 else n
        if outward.dot(Vector((v.co.x, v.co.y, 0.0))) < 0:
            outward = -outward
        depth = (v.co - q).dot(outward)
        if depth < clear:
            v.co = v.co + outward * (clear - depth)
            pushed += 1
    tee_obj.data.update()
    # ...and clear of the body by more than the collision gap (6 mm collider + 6 mm cloth):
    # smoothing the shell pulled parts of it within that gap, and the push-out shortened
    # the shirt (hem crept up 3 cm).
    col_obj = next(o for o in boy.children_recursive if o.name == "Boy_collider")
    cv = [Vector(v.co) for v in col_obj.data.vertices]
    ctree = BVHTree.FromPolygons(cv, [tuple(f.vertices) for f in col_obj.data.polygons])
    for v in tee_obj.data.vertices:
        q, n, _, dist = ctree.find_nearest(v.co)
        side = 1.0 if (v.co - q).dot(n) >= 0 else -1.0
        if env("BODY_CLEAR", 0.015) > 0 and side * dist < env("BODY_CLEAR", 0.015):
            v.co = q + n * env("BODY_CLEAR", 0.015)
            pushed += 1
    tee_obj.data.update()
    cloth.make_collider(col_obj)
    if not env("NOPANTS", 0):
        cloth.make_collider(pants_obj, thickness=0.004)
    # Start in the rest pose (the pose the shirt was made in) and move into the pose.
    from recipes import rig  # noqa: E402
    pose_frames = rig.animate_into_pose(boy, frame_end=env("POSE_FRAMES", 20)) if boy.type == "ARMATURE" else 20
    cloth.add_cloth(tee_obj, pin_weights=pin if env("PIN", 1) else None, fabric=os.environ.get("FABRIC", "jersey"), spare=env("SPARE", 0.02), sewing_force=40.0)
    t0 = time.time()
    total = pose_frames + env("FRAMES", 20)
    if env("DIAG", 0):
        from recipes import hair as _h  # noqa: E402
        scene.frame_start, scene.frame_end = 1, total
        for m in (m for o in scene.objects for m in o.modifiers if m.type == "CLOTH"):
            m.point_cache.frame_start, m.point_cache.frame_end = 1, total
        for f in range(1, total + 1):
            scene.frame_set(f)
            if f % 2 == 0 or f == 1:
                tv = np.array(_h.evaluated_mesh(tee_obj)[0]); pv_ = np.array(_h.evaluated_mesh(pants_obj)[0])
                print("DIAG frame", f, "tee hem z", round(float(np.percentile(tv[:, 2], 1)), 3), "tee top z",
                      round(float(tv[:, 2].max()), 3), "pants top z", round(float(pv_[:, 2].max()), 3))
    else:
        cloth.simulate(scene, total)
    sim_seconds = round(time.time() - t0)
info = {**print_info, "sim_seconds": sim_seconds, "tee_points_pushed": pushed if (env("DRAPE", 1) and TEE_MODE != "asset") else 0}
if env("HAIR", 1):
    _, hinfo = looks.orange_curls(scene, base_verts, armature=boy, children=env("CHILDREN", 150000))
    info.update(hinfo)
build_seconds = round(time.time() - started, 1)

# Museum-like warm soft light, as in run 012, on a dark red carpet floor.
lm = accessories.face_landmarks(base_verts)
world.sky_world(scene, sun_elevation_deg=40.0, sun_rotation_deg=220.0, strength=0.006)
target = stage.empty_at(scene, "Body", (0.0, 0.0, 0.85))
lighting.three_point(scene, target, (-0.6, -3.5, 1.2), key_power=env("KEY", 260.0), fill_ratio=0.35,
                     rim_ratio=1.2, distance=3.5, key_size=1.8)
bpy.ops.mesh.primitive_plane_add(size=40)
bpy.context.object.data.materials.append(materials.plain("Carpet", (0.12, 0.025, 0.025), 0.95))
scene.cycles_curves.shape = "THICK"
color.set_view(scene, "AgX", look="Medium High Contrast")
render.cycles_cpu(scene, width=W, height=H, samples=SAMPLES)

top = lm["top_z"]
views = {"full": ((-0.9, -3.2, 1.0), (0.0, 0.0, top * 0.52), 50.0),
         "back": ((0.7, 3.2, 1.1), (0.0, 0.0, top * 0.52), 50.0),
         "side": ((-3.3, -0.4, 1.0), (0.0, 0.0, top * 0.52), 50.0),
         "upper": ((-0.45, -1.6, top * 0.80), (0.0, 0.0, top * 0.74), 60.0)}
names = os.environ.get("VIEWS", "full,side,back,upper").split(",")
from PIL import Image  # noqa: E402
tiles = []
for label in names:
    for o in [o for o in scene.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(o, do_unlink=True)
    eye, at, lens = views[label]
    aim = stage.empty_at(scene, f"Aim_{label}", at)
    camera.camera_at(scene, eye, aim, lens=lens)
    path = os.path.join(HERE, f"outfit_{label}.png")
    render.render_to(scene, path)
    tiles.append(Image.open(path).convert("RGB"))
sheet = Image.new("RGB", (W * len(tiles), H))
for i, t in enumerate(tiles):
    sheet.paste(t, (W * i, 0))
out = os.environ.get("OUT") or os.path.join(HERE, "outfit.png")
sheet.save(out)
print("STATS " + json.dumps({"build_seconds": build_seconds, "render_seconds": round(time.time() - started - build_seconds), **info}))
