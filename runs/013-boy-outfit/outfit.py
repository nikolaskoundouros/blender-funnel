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
                     render, stage, world)
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
pants = garments.trousers(name="pants", length=1.93, waist=env("WAIST", 0.14), ease=baggy, smooth_shell=SMOOTH, thickness=0.003, cut=CUT,
                          material=jersey("Pants", PANTS))
# Out past the trousers' 3 mm thickness (at +1.2 mm it was hidden inside them).
stripe = garments.leg_patch("stripe", s=(0.02, 1.92), theta=(84, 96), ease=baggy + 0.0035, thickness=0.0008,
                            material=jersey("Stripe", STRIPE), smooth_shell=SMOOTH, cut=CUT, corner=0.002,
                            step=0.004)
# Loose untucked tee: short sleeves to just above the elbow, hem below the hip.
tee = garments.top(name="tee", sleeve=0.85, collar=0.965, hem=env("HEM", 0.0), ease=env("TEE_EASE", 0.03 if env("DRAPE", 0) else 0.012), thickness=0.003,
                   smooth_shell=SMOOTH, material=jersey("Tee", TEE))

started = time.time()
pose = looks.head_pose(*looks.CURLY_BOY_HEAD) + list(__import__("recipes.rig", fromlist=["POSES"]).POSES["relaxed"])
boy = human.build_human(scene, name="Boy", skin="young_caucasian_male", hair=None, eyes="green",
                        outfit=(pants, stripe, tee, "shoes05"), pose=pose, collider=bool(env("DRAPE", 0)), **S)
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

sim_seconds = 0
if env("DRAPE", 0):
    # Route B (playbook): a roomy shell draped as cotton. A stiff shell gave square, padded
    # shoulders (steps 1 and 2). Pin the yoke and the tops of the sleeves; the rest hangs.
    tee_obj = next(o for o in boy.children_recursive if o.name == "Boy_tee")
    binding = human.BINDINGS[tee_obj.name]
    h = garments.coordinate(binding, "h")
    on_arm = np.isin(garments.part(binding), ("arm", "hand"))
    arm = garments.coordinate(binding, "arm")
    pin = np.where(on_arm, np.clip((0.20 - arm) / 0.14, 0.0, 1.0), np.clip((h - 0.86) / 0.06, 0.0, 1.0))
    cloth.make_collider(next(o for o in boy.children_recursive if o.name == "Boy_collider"))
    cloth.make_collider(next(o for o in boy.children_recursive if o.name == "Boy_pants"), thickness=0.009)
    cloth.add_cloth(tee_obj, pin_weights=pin, fabric="cotton", spare=env("SPARE", 0.03), sewing_force=40.0)
    t0 = time.time()
    cloth.simulate(scene, env("FRAMES", 45))
    sim_seconds = round(time.time() - t0)
info = {"sim_seconds": sim_seconds}
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
