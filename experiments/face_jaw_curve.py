"""Lip gap on our character as a function of jawOpen (alone, and with mouthUpperUp L+R at
0.4), measured by tools/face_track.py on 240x240 renders. Used to invert the jaw top-up
(recipes/face_anim.lip_top_up). Writes experiments/results_face_jaw_curve.json."""
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from recipes import face_anim, render  # noqa: E402
from face_response import face_scene  # noqa: E402

OUT = os.path.join(ROOT, "runs", "017-faceunits", "matrix_frames_jaw")
os.makedirs(OUT, exist_ok=True)
levels = [round(x, 2) for x in np.linspace(0, 1, 11)]
scene, root = face_scene()
k = 0
for upper in (0.0, 0.4):
    for j in levels:
        face_anim.set_units(root, {u: 0.0 for u in face_anim.ARKIT})
        face_anim.set_units(root, {"jawOpen": j, "mouthUpperUpLeft": upper, "mouthUpperUpRight": upper})
        render.render_to(scene, os.path.join(OUT, f"{k:03d}.png"))
        k += 1
csv_path = os.path.join(OUT, "track.csv")
subprocess.run([os.path.join(ROOT, ".venv-face", "bin", "python"), "-I", os.path.join(ROOT, "tools", "face_track.py"),
                OUT, csv_path, "--fps", "1"], check=True, stderr=subprocess.DEVNULL)
_, got = face_anim.read_curves(csv_path)
res = {"jawOpen": levels, "lip_gap_alone": [round(float(x), 4) for x in got["lip_gap"][:11]],
       "lip_gap_with_upperUp_0.4": [round(float(x), 4) for x in got["lip_gap"][11:22]],
       "tracker_jawOpen_alone": [round(float(x), 3) for x in got["jawOpen"][:11]]}
print(json.dumps(res, indent=1))
json.dump(res, open(os.path.join(HERE, "results_face_jaw_curve.json"), "w"), indent=1)
