"""Do MakeHuman's Faceunits 01 targets (CC0, ARKit names) work on our characters?

For each unit: build the curly-haired boy with that unit at full weight (static, through
human.morphed_base), record how many vertices move and how far, and render a 240x240
front close-up. A contact sheet goes to runs/017-faceunits/units.png.

Usage: python experiments/verify_faceunits.py [unit ...]
Writes experiments/results_faceunits.json.
"""
import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from recipes import accessories, camera, human, lighting, looks, render, stage, world  # noqa: E402

UNITS = sys.argv[1:] or ["neutral", "jawOpen", "eyeBlinkLeft", "mouthSmileLeft", "browInnerUp", "mouthPucker"]
OUT = os.path.join(ROOT, "runs", "017-faceunits")
os.makedirs(OUT, exist_ok=True)
S = looks.CURLY_BOY_SLIDERS
neutral = human.morphed_base(**S)
results = {}
for unit in UNITS:
    expr = None if unit == "neutral" else {unit: 1.0}
    verts = human.morphed_base(expression=expr, **S)
    d = np.linalg.norm(verts - neutral, axis=1) * 100 * human.SCALE  # MakeHuman units -> cm
    results[unit] = {"moved_vertices": int((d > 0.01).sum()),
                     "moved_helpers": int((d[human.BODY_VERTS:] > 0.01).sum()),
                     "max_cm": round(float(d.max()), 2), "left_minus_right_cm": None}
    if expr:
        vb = human.to_blender(verts)
        moved = d > 0.01
        # Character faces -Y; its left is +X. Mean displacement on each side of the face.
        results[unit]["left_minus_right_cm"] = round(float(d[moved & (vb[:, 0] > 0.005)].sum()
                                                           - d[moved & (vb[:, 0] < -0.005)].sum()) / max(moved.sum(), 1), 3)
    scene = stage.new_scene()
    human.build_human(scene, name="Boy", skin="young_caucasian_male", hair=None, eyes="green",
                      outfit=(), pose=None, expression=expr, **S)
    lm = accessories.face_landmarks(neutral)
    target = bpy.data.objects.new("aim", None)
    scene.collection.objects.link(target)
    target.location = (0.0, float(lm["front_y"]), float(lm["eye_z"]) - 0.03)
    cam_loc = (0.0, float(lm["front_y"]) - 0.75, float(lm["eye_z"]) - 0.01)
    camera.camera_at(scene, cam_loc, target, lens=85)
    world.solid_world(scene, color=(0.35, 0.35, 0.37), strength=0.5)
    lighting.three_point(scene, target, cam_loc, key_power=60.0, distance=2.0, key_size=1.0)
    render.cycles_cpu(scene, width=240, height=240, samples=16)
    render.render_to(scene, os.path.join(OUT, f"{unit}.png"))
    print(unit, results[unit])

path = os.path.join(HERE, "results_faceunits.json")
old = json.load(open(path)) if os.path.exists(path) else {}
old.update(results)
old["blender"] = bpy.app.version_string
json.dump(old, open(path, "w"), indent=1)

from PIL import Image, ImageDraw  # noqa: E402
ims = [(u, Image.open(os.path.join(OUT, f"{u}.png")).convert("RGB")) for u in UNITS]
cols = 3
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 240, rows * 262), (20, 20, 20))
draw = ImageDraw.Draw(sheet)
for i, (u, im) in enumerate(ims):
    x, y = (i % cols) * 240, (i // cols) * 262
    sheet.paste(im, (x, y + 22))
    draw.text((x + 6, y + 5), u, fill=(235, 235, 235))
sheet.save(os.path.join(OUT, "units.png"))
