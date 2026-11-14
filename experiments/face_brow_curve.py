"""Brow height on our character as a function of a brow raise (browInnerUp, browOuterUpLeft
and browOuterUpRight at the same value, up to 3), measured by tools/face_track.py on
240x240 renders as brow height above the eye corners / face width. Driving brows from this landmark measure was
abandoned (its noise on our renders matched the source's brow motion, notes F13); the
renders set the cap of 2 (a forehead ridge shows from about 2.5).
Writes experiments/results_face_brow_curve.json and runs/017-faceunits/brow_levels.png."""
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

OUT = os.path.join(ROOT, "runs", "017-faceunits", "matrix_frames_brow")
os.makedirs(OUT, exist_ok=True)
levels = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
scene, root = face_scene()
for k, s in enumerate(levels):
    face_anim.set_units(root, {u: 0.0 for u in face_anim.ARKIT})
    face_anim.set_units(root, {"browInnerUp": s, "browOuterUpLeft": s, "browOuterUpRight": s})
    render.render_to(scene, os.path.join(OUT, f"{k:03d}.png"))
csv_path = os.path.join(OUT, "track.csv")
subprocess.run([os.path.join(ROOT, ".venv-face", "bin", "python"), "-I", os.path.join(ROOT, "tools", "face_track.py"),
                OUT, csv_path, "--fps", "1"], check=True, stderr=subprocess.DEVNULL)
_, got = face_anim.read_curves(csv_path)
res = {"levels": levels, "brow_l": got["brow_l"].round(4).tolist(), "brow_r": got["brow_r"].round(4).tolist(),
       "tracker_browInnerUp": got["browInnerUp"].round(3).tolist(),
       "tracker_browOuterUpLeft": got["browOuterUpLeft"].round(3).tolist()}
print(json.dumps(res))
json.dump(res, open(os.path.join(HERE, "results_face_brow_curve.json"), "w"), indent=1)
from PIL import Image, ImageDraw  # noqa: E402
ims = [Image.open(os.path.join(OUT, f"{k:03d}.png")).convert("RGB").crop((40, 20, 200, 120)) for k in range(len(levels))]
sheet = Image.new("RGB", (160 * len(ims), 122), (20, 20, 20))
for k, im in enumerate(ims):
    sheet.paste(im, (160 * k, 22))
    ImageDraw.Draw(sheet).text((160 * k + 4, 5), f"brows {levels[k]}", fill=(235, 235, 235))
sheet.save(os.path.join(ROOT, "runs", "017-faceunits", "brow_levels.png"))
