"""Each Visemes 01 shape alone at 1.0 on our character: lip gap and mouth width (face widths,
tools/face_track.py), against how far real speakers open (95th percentile of lip gap while
talking: 0.136 to 0.160 on the Wikitongues clips). Gives each viseme a ceiling so no shape
opens past a real speaker. Writes experiments/results_viseme_response.json and
runs/019-voice-lipsync/visemes.png."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from recipes import face_anim, looks, render  # noqa: E402
from face_response import face_scene  # noqa: E402

OUT = os.path.join(ROOT, "runs", "017-faceunits", "matrix_frames_visemes")
os.makedirs(OUT, exist_ok=True)
scene, root = face_scene()
face_anim.add_faceunit_keys(root, units=face_anim.VISEMES, **looks.CURLY_BOY_SLIDERS)
order = ["rest"] + face_anim.VISEMES
for k, v in enumerate(order):
    face_anim.set_units(root, {u: 0.0 for u in face_anim.ARKIT + face_anim.VISEMES})
    face_anim.set_units(root, {"mouthPucker": face_anim.REST_OFFSET["mouthPucker"]})
    if v != "rest":
        face_anim.set_units(root, {v: 1.0})
    render.render_to(scene, os.path.join(OUT, f"{k:03d}.png"))
csv_path = os.path.join(OUT, "track.csv")
subprocess.run([os.path.join(ROOT, ".venv-face", "bin", "python"), "-I", os.path.join(ROOT, "tools", "face_track.py"),
                OUT, csv_path, "--fps", "1"], check=True, stderr=subprocess.DEVNULL)
_, got = face_anim.read_curves(csv_path)
REAL_P95 = 0.136
res = {"real_lip_gap_p95": REAL_P95, "visemes": {}}
for k, v in enumerate(order):
    lip, width = float(got["lip_gap"][k]), float(got["mouth_width"][k])
    res["visemes"][v] = {"lip_gap": round(lip, 4), "mouth_width": round(width, 4)}
rest_lip = res["visemes"]["rest"]["lip_gap"]
for v in face_anim.VISEMES:
    lip = res["visemes"][v]["lip_gap"]
    # Lip gap roughly linear in the key above rest: ceiling where it reaches the real p95.
    res["visemes"][v]["ceiling"] = round(min(1.0, (REAL_P95 - rest_lip) / max(lip - rest_lip, 1e-6)), 3)
print(json.dumps(res, indent=1))
json.dump(res, open(os.path.join(HERE, "results_viseme_response.json"), "w"), indent=1)
from PIL import Image, ImageDraw  # noqa: E402
cols = 6
sheet = Image.new("RGB", (cols * 120, ((len(order) + cols - 1) // cols) * 112), (20, 20, 20))
for k, v in enumerate(order):
    im = Image.open(os.path.join(OUT, f"{k:03d}.png")).convert("RGB").crop((60, 110, 180, 200))
    x, y = (k % cols) * 120, (k // cols) * 112
    sheet.paste(im, (x, y + 20))
    ImageDraw.Draw(sheet).text((x + 3, y + 4), f"{v} {res['visemes'][v]['lip_gap']:.2f}", fill=(235, 235, 235))
sheet.save(os.path.join(ROOT, "runs", "019-voice-lipsync", "visemes.png"))
