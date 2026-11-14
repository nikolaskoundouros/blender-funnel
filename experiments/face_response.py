"""P2 (notes/facial-mocap-plan.md): response matrix of the tracker on our own face.

Builds the curly-haired boy with the 52 Faceunits shape keys, renders a 240x240 front
close-up of the neutral face and of each unit alone at 1.0, runs tools/face_track.py (own
venv) on the frames, and for each unit records the rise of every channel over the neutral
frame. A unit counts as recognised when its own channel rises most.

Usage: python experiments/face_response.py [--no-render]
Writes experiments/results_face_response.json and runs/017-faceunits/matrix.png.
"""
import csv
import json
import os
import subprocess
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from recipes import accessories, camera, face_anim, human, lighting, looks, render, stage, world  # noqa: E402

SIZE = int(os.environ.get("SIZE", 240))
OUT = os.path.join(ROOT, "runs", "017-faceunits", "matrix_frames" + ("" if SIZE == 240 else f"_{SIZE}"))
S = looks.CURLY_BOY_SLIDERS
UNITS = [u for u in face_anim.ARKIT if u != "tongueOut"]   # MediaPipe has no tongueOut


def face_scene():
    """The boy with face keys, a front close-up camera and soft light. Returns root."""
    scene = stage.new_scene()
    root = human.build_human(scene, name="Boy", skin="young_caucasian_male", hair=None, eyes="green",
                             outfit=(), pose=None, **S)
    face_anim.add_faceunit_keys(root, **S)
    lm = accessories.face_landmarks(human.morphed_base(**S))
    target = bpy.data.objects.new("aim", None)
    scene.collection.objects.link(target)
    target.location = (0.0, float(lm["front_y"]), float(lm["eye_z"]) - 0.03)
    cam_loc = (0.0, float(lm["front_y"]) - 0.75, float(lm["eye_z"]) - 0.01)
    camera.camera_at(scene, cam_loc, target, lens=85)
    world.solid_world(scene, color=(0.35, 0.35, 0.37), strength=0.5)
    lighting.three_point(scene, target, cam_loc, key_power=60.0, distance=2.0, key_size=1.0)
    render.cycles_cpu(scene, width=SIZE, height=SIZE, samples=16)
    return scene, root


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    order = ["neutral"] + UNITS
    if "--no-render" not in sys.argv:
        scene, root = face_scene()
        for i, unit in enumerate(order):
            face_anim.set_units(root, {u: 0.0 for u in face_anim.ARKIT})
            if unit != "neutral":
                face_anim.set_units(root, {unit: 1.0})
            render.render_to(scene, os.path.join(OUT, f"{i:03d}_{unit}.png"))
    out_csv = os.path.join(OUT, "track.csv")
    subprocess.run([os.path.join(ROOT, ".venv-face", "bin", "python"), "-I",
                    os.path.join(ROOT, "tools", "face_track.py"), OUT, out_csv, "--fps", "1"], check=True,
                   stderr=subprocess.DEVNULL)
    rows = list(csv.DictReader(open(out_csv)))
    val = lambda r, c: float(r[c]) if r[c] else np.nan
    neutral = rows[0]
    res, hits, ranks = {}, 0, {}
    M = np.zeros((len(UNITS), len(UNITS)))
    for j, unit in enumerate(UNITS):
        r = rows[j + 1]
        if r["found"] != "1":
            res[unit] = {"found": False}
            continue
        rise = np.array([val(r, c) - val(neutral, c) for c in UNITS])
        M[j] = rise
        order_idx = np.argsort(-rise)
        rank = int(np.where(order_idx == j)[0][0]) + 1
        ranks[unit] = rank
        hits += rank == 1
        res[unit] = {"own_rise": round(float(rise[j]), 3), "rank": rank,
                     "top": [(UNITS[k], round(float(rise[k]), 3)) for k in order_idx[:3]],
                     "lip_gap": val(r, "lip_gap"), "eye_open_l": val(r, "eye_open_l"), "eye_open_r": val(r, "eye_open_r")}
    summary = {"units": len(UNITS), "recognised_rank1": hits, "rank_le3": sum(v <= 3 for v in ranks.values()),
               "neutral_scores_above_0.3": {c: round(val(neutral, c), 2) for c in UNITS if val(neutral, c) > 0.3}}
    print(json.dumps(summary, indent=1))
    json.dump({"summary": summary, "units": res, "size_px": SIZE, "blender": bpy.app.version_string},
              open(os.path.join(HERE, "results_face_response" + ("" if SIZE == 240 else f"_{SIZE}") + ".json"), "w"), indent=1)
    # Matrix image: rows = unit rendered, columns = channel rise (red up, blue down).
    from PIL import Image, ImageDraw
    cell, pad = 9, 130
    img = Image.new("RGB", (pad + cell * len(UNITS), pad + cell * len(UNITS)), (255, 255, 255))
    d = ImageDraw.Draw(img)
    for j in range(len(UNITS)):
        d.text((2, pad + j * cell - 2), UNITS[j][:20], fill=(0, 0, 0))
        for k in range(len(UNITS)):
            v = float(np.clip(M[j, k], -1, 1))
            col = (255, int(255 * (1 - v)), int(255 * (1 - v))) if v >= 0 else (int(255 * (1 + v)), int(255 * (1 + v)), 255)
            d.rectangle([pad + k * cell, pad + j * cell, pad + (k + 1) * cell - 1, pad + (j + 1) * cell - 1], fill=col)
    d.text((pad, 4), "rows: unit rendered at 1.0 / columns: tracker channel rise over neutral", fill=(0, 0, 0))
    img.save(os.path.join(ROOT, "runs", "017-faceunits", "matrix" + ("" if SIZE == 240 else f"_{SIZE}") + ".png"))
