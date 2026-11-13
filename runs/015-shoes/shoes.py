"""Run 015: trainers built by code (recipes/shoes.py) for the curly-haired boy.

Usage: python runs/015-shoes/shoes.py [width height samples]
Environment: TOP_AT, EASE, SMOOTH (upper), OUT.
"""
import json
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from recipes import camera, color, human, lighting, looks, materials, render, shoes, stage, world  # noqa: E402

W, H, SAMPLES = (int(a) for a in sys.argv[1:4]) if len(sys.argv) > 3 else (480, 360, 16)
env = lambda k, d: type(d)(os.environ.get(k, d))
S = looks.CURLY_BOY_SLIDERS
YELLOW = (0.72, 0.36, 0.010)    # reference: yellow-orange canvas, white sole
WHITE = (0.80, 0.80, 0.78)

scene = stage.new_scene()
base_verts = human.morphed_base(**S)
started = time.time()
canvas = materials.fabric(YELLOW, name="Upper", thread=0.0007, on="garment", sheen=0.2)
upper = shoes.upper_spec(top_at=env("TOP_AT", 1.95), ease=env("EASE", 0.006), material=canvas,
                         smooth_shell=env("SMOOTH", 12))
# panels in the upper's own colour, shown by their seams (the reference has no white toe cap)
shoes.add_panels(canvas, shoes.foot_frames(base_verts), toe_cap=YELLOW, heel=YELLOW, eyestay=YELLOW,
                 seam=(0.30, 0.13, 0.01))
boy = human.build_human(scene, name="Boy", skin="young_caucasian_male", hair=None, eyes="green",
                        outfit=(upper,), **S)
materials.soften_skin(boy.data.materials[0])
rubber = materials.plain("Midsole", WHITE, 0.55)
info = {}
for side in ("L", "R"):
    _, info = shoes.sole(scene, base_verts, side, material=rubber, parent=boy)
upper_obj = next(o for o in boy.children if o.name == "Boy_upper")
lace_count = shoes.laces(scene, upper_obj, shoes.foot_frames(base_verts), parent=boy,
                         lace_material=materials.plain("Lace", (0.85, 0.85, 0.82), 0.7),
                         eyelet_material=materials.plain("Eyelet", (0.75, 0.75, 0.72), 0.3))
boy.location.z = shoes.SOLE_BELOW            # stand on the soles
build_seconds = round(time.time() - started, 1)

world.sky_world(scene, sun_elevation_deg=40.0, sun_rotation_deg=220.0, strength=0.006)
target = stage.empty_at(scene, "Feet", (0.0, -0.05, 0.05))
lighting.three_point(scene, target, (-0.6, -1.2, 0.3), key_power=env("KEY", 25.0), fill_ratio=0.35, rim_ratio=1.0,
                     distance=1.5, key_size=0.8)
bpy.ops.mesh.primitive_plane_add(size=20)
bpy.context.object.data.materials.append(materials.plain("Floor", (0.12, 0.025, 0.025), 0.95))
color.set_view(scene, "AgX", look="Medium High Contrast")
render.cycles_cpu(scene, width=W, height=H, samples=SAMPLES)
from PIL import Image  # noqa: E402
tiles = []
for label, eye in (("front", (-0.35, -0.75, 0.30)), ("side", (0.85, -0.10, 0.18))):
    for o in [o for o in scene.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(o, do_unlink=True)
    aim = stage.empty_at(scene, f"Aim_{label}", (0.08 if label == "side" else 0.0, -0.05, 0.05))
    camera.camera_at(scene, eye, aim, lens=70.0)
    path = os.path.join(HERE, f"shoes_{label}.png")
    render.render_to(scene, path)
    tiles.append(Image.open(path).convert("RGB"))
sheet = Image.new("RGB", (W * len(tiles), H))
for i, t in enumerate(tiles):
    sheet.paste(t, (W * i, 0))
sheet.save(os.environ.get("OUT") or os.path.join(HERE, "shoes.png"))
print("STATS " + json.dumps({"build_seconds": build_seconds, "render_seconds": round(time.time() - started - build_seconds), "laces": lace_count, **info}))
