"""Run 011: a short, combed-back, salt-and-pepper haircut from guides plus children.

Usage: python runs/011-hair/hair.py [width height samples]   (renders front and side views)
Environment: GUIDES, CHILDREN, CLUMP, FRIZZ to try settings; OUT for the output file.
"""
import json
import os
import sys
import time

import bpy
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from recipes import accessories, camera, color, garments, haircut, human, materials, render, stage, world  # noqa: E402

W, H, SAMPLES = (int(a) for a in sys.argv[1:4]) if len(sys.argv) > 3 else (400, 400, 32)
SLIDERS = dict(gender=1.0, age=0.7, muscle=0.6, weight=0.5, height=0.5, caucasian=1, african=0, asian=0)
env = lambda k, d: type(d)(os.environ.get(k, d))

scene = stage.new_scene()
base_verts = human.morphed_base(**SLIDERS)
pilot = human.build_human(scene, name="Pilot", skin="old_caucasian_male", hair=None, eyes="brown",
                          outfit=(garments.top(name="shirt", sleeve=0.4, collar=1.0, hem=0.0, ease=0.004,
                                               material=materials.fabric((0.8, 0.8, 0.78), on="garment")),),
                          **SLIDERS)
body = pilot          # no pose: the body object is the root
materials.soften_skin(body.data.materials[0])
obj, info = haircut.haircut(scene, base_verts, guides=env("GUIDES", 400), children=env("CHILDREN", 60000),
                            clump=env("CLUMP", 0.55), frizz=env("FRIZZ", 0.0016), parent=pilot)
print("HAIR " + json.dumps(info))

lm = accessories.face_landmarks(base_verts)
world.sky_world(scene, sun_elevation_deg=40.0, sun_rotation_deg=220.0, strength=0.035)
scene.cycles_curves.shape = "THICK"
color.set_view(scene, "AgX", look="Medium High Contrast")
render.cycles_cpu(scene, width=W, height=H, samples=SAMPLES)
aim = stage.empty_at(scene, "Aim", (0.0, lm["front_y"] + 0.09, lm["eye_z"] + 0.02))
tiles = []
started = time.time()
for label, eye in (("front", (-0.25, -0.75, lm["eye_z"] + 0.10)), ("side", (0.75, -0.05, lm["eye_z"] + 0.12))):
    for o in [o for o in scene.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(o, do_unlink=True)
    camera.camera_at(scene, eye, aim, lens=85.0)
    path = os.path.join(HERE, f"hair_{label}.png")
    render.render_to(scene, path)
    tiles.append(Image.open(path).convert("RGB"))
sheet = Image.new("RGB", (W * 2, H))
for i, t in enumerate(tiles):
    sheet.paste(t, (W * i, 0))
out = os.environ.get("OUT") or os.path.join(HERE, "hair.png")
sheet.save(out)
print("STATS " + json.dumps({"render_seconds": round(time.time() - started), **info}))
