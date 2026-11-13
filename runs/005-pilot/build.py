"""Run 005: a hero close-up in the style of the owner's reference (aviator portrait).

Everything is generated: body, leather jacket, shearling collar with real fur strands,
flying helmet, goggles, moustache. No downloaded clothing or hair assets are used except
the eyebrow and eyelash cards and the skin texture.

Usage: python runs/005-pilot/build.py [width height samples]
"""
import json
import math
import os
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from recipes import (accessories, camera, color, garments, hair, human, lighting,  # noqa: E402
                     materials, render, stage, world)
from tools.image_stats import stats  # noqa: E402

W, H, SAMPLES = (int(a) for a in sys.argv[1:4]) if len(sys.argv) > 3 else (864, 1080, 160)
SLIDERS = dict(gender=1.0, age=0.55, muscle=0.6, weight=0.55, height=0.5,
               caucasian=1, african=0, asian=0)

scene = stage.new_scene()
jacket_leather = materials.leather("Jacket leather", (0.032, 0.017, 0.010), on="garment", wear=0.3, grain=0.0014)
# Leather colours are scene-linear: 0.10 rendered as pale taupe (v1). Dark brown is about 0.03.
pilot = human.build_human(
    scene, name="Pilot", skin="middleage_caucasian_male", hair=None, eyes="brown",
    # First test: 2 cm of ease left every muscle showing and the jacket read as bare skin.
    outfit=(garments.top(name="jacket", sleeve=1.95, collar=0.93, hem=-0.12, ease=0.04,
                         thickness=0.006, material=jacket_leather, soften=10),
            garments.collar(low=0.84, high=1.08, ease=0.045, thickness=0.028),
            garments.helmet(material=materials.leather("Helmet leather", (0.022, 0.015, 0.011), wear=0.3, grain=0.0014)),
            garments.trousers(material=materials.fabric((0.30, 0.27, 0.20), on="garment"))),
    pose="relaxed", **SLIDERS)
body = next(c for c in pilot.children if c.name == "Pilot")
materials.soften_skin(body.data.materials[0])

base_verts = human.morphed_base(**SLIDERS)
lm = accessories.face_landmarks(base_verts)
accessories.goggles(scene, base_verts, parent=pilot, clearance=0.008)

# Shearling: woolly cream strands all over the collar.
collar_obj = next(c for c in pilot.children if c.name.endswith("_collar"))
cv, cf = hair.evaluated_mesh(collar_obj)
roots, normals = hair.sample_surface(cv, cf, 70000, seed=1)
wool = materials.hair_fibre("Wool", (0.72, 0.62, 0.44), roughness=0.8)
hair.grow(scene, "Collar fur", roots, normals, length=0.022, radius=0.00035, material=wool,
          comb=(0.0, 0.0, -0.15), curl=0.75, steps=6, seed=2)

# Moustache: strands on the upper lip, combed out to each side.
vb = human.to_blender(base_verts)
all_faces = human.base_mesh()[2]
nose, lip = lm["nose"], lm["lip"]
lip_faces = []
for f in all_faces:
    if all(v < human.BODY_VERTS for v in f):
        c = vb[list(f)].mean(axis=0)
        if abs(c[0]) < 0.034 and lip[2] - 0.004 < c[2] < nose[2] - 0.004 and c[1] < nose[1] + 0.03:
            lip_faces.append(f)
mr, mn = hair.sample_surface(vb, lip_faces, 2600, seed=3)
side = np.sign(mr[:, 0])[:, None]
comb = np.concatenate([side * 1.1, np.full((len(mr), 1), -0.15), np.full((len(mr), 1), -0.45)], axis=1)
length = 0.012 + 0.016 * np.abs(mr[:, 0]) / 0.034
hair.grow(scene, "Moustache", mr, mn, length=length, radius=0.00011,
          material=materials.hair_fibre("Moustache", (0.045, 0.03, 0.02), roughness=0.35),
          comb=comb, curl=0.12, steps=6, seed=4)

# Shot: portrait close-up, long lens, shallow focus on the eyes.
focus = stage.empty_at(scene, "Focus", (0.0, lm["front_y"] + 0.02, lm["eye_z"]))
aim = stage.empty_at(scene, "Aim", (0.0, -0.06, lm["eye_z"] - 0.075))
cam_at = (0.36, -1.08, lm["eye_z"] - 0.06)   # first test stood 1.6 m back: too wide
stage.backdrop(scene, cam_at, (0.0, 0.0, 0.0), color=(0.30, 0.33, 0.36))
lighting.three_point(scene, aim, cam_at, key_power=85.0, fill_ratio=0.2, rim_ratio=2.2,
                     distance=2.4, key_size=1.1)
world.solid_world(scene, (0.6, 0.72, 0.9), 0.08)
cam = camera.camera_at(scene, cam_at, aim, lens=85.0)
camera.depth_of_field(cam, focus, fstop=2.0)
color.set_view(scene, "AgX", look="Medium High Contrast")
render.cycles_cpu(scene, width=W, height=H, samples=SAMPLES)
scene.cycles_curves.shape = "THICK" if W >= 800 else "RIBBONS"

started = time.time()
out = render.render_to(scene, os.path.join(HERE, "pilot.png" if W >= 800 else "pilot_test.png"))
report = {"blender": bpy.app.version_string, "size": [W, H], "samples": SAMPLES,
          "render_seconds": round(time.time() - started), "image": stats(out),
          "strands": {"collar": 70000, "moustache": 2600}}
with open(os.path.join(HERE, "stats.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("STATS " + json.dumps(report))
