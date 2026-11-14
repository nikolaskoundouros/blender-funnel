"""Our character's resting mouth reads as puckered to MediaPipe (P2: neutral mouthPucker
0.53), which showed up as pucker "overshoot" when driven (run 018). Render the neutral
face with mouthPucker at 0, -0.2, ... -0.8 (shape key below zero) and read the tracker,
to pick a rest offset. Writes experiments/results_face_rest_offset.json and
runs/017-faceunits/pucker_rest.png."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from recipes import face_anim, render  # noqa: E402
from face_response import face_scene  # noqa: E402

OUT = os.path.join(ROOT, "runs", "017-faceunits", "matrix_frames_rest")
os.makedirs(OUT, exist_ok=True)
levels = [0.0, -0.2, -0.4, -0.6, -0.8]
scene, root = face_scene()
for obj in face_anim.keyable_objects(root):
    if obj.data.shape_keys and "mouthPucker" in obj.data.shape_keys.key_blocks:
        obj.data.shape_keys.key_blocks["mouthPucker"].slider_min = -1.0
for k, v in enumerate(levels):
    face_anim.set_units(root, {u: 0.0 for u in face_anim.ARKIT})
    face_anim.set_units(root, {"mouthPucker": v})
    render.render_to(scene, os.path.join(OUT, f"{k:03d}.png"))
csv_path = os.path.join(OUT, "track.csv")
subprocess.run([os.path.join(ROOT, ".venv-face", "bin", "python"), "-I", os.path.join(ROOT, "tools", "face_track.py"),
                OUT, csv_path, "--fps", "1"], check=True, stderr=subprocess.DEVNULL)
_, got = face_anim.read_curves(csv_path)
res = {"mouthPucker_key": levels, **{c: got[c].round(3).tolist() for c in
       ("mouthPucker", "mouthFunnel", "mouthStretchLeft", "mouthSmileLeft", "lip_gap")}}
print(json.dumps(res))
json.dump(res, open(os.path.join(HERE, "results_face_rest_offset.json"), "w"), indent=1)
from PIL import Image, ImageDraw  # noqa: E402
ims = [Image.open(os.path.join(OUT, f"{k:03d}.png")).convert("RGB").crop((60, 110, 180, 190)) for k in range(len(levels))]
sheet = Image.new("RGB", (120 * len(ims), 102), (20, 20, 20))
for k, im in enumerate(ims):
    sheet.paste(im.resize((120, 80)), (120 * k, 22))
    ImageDraw.Draw(sheet).text((120 * k + 4, 5), f"pucker {levels[k]}", fill=(235, 235, 235))
sheet.save(os.path.join(ROOT, "runs", "017-faceunits", "pucker_rest.png"))
