"""P4/P5 (notes/facial-mocap-plan.md): drive our character from a tracked face and check.

Reads a CSV from tools/face_track.py, keys the curly-haired boy's Faceunits shape keys from
it (recipes/face_anim.py: neutral = each channel's 5th percentile, gains, One-Euro
smoothing), renders 240x240 front close-ups, tracks the renders with the same tool, and
compares source and render on landmark-only measures (lip gap, eye openings), which do not
depend on the blendshape model: Pearson r, best lag, amplitude ratio (p95 - p5).

Usage: python experiments/face_drive.py SOURCE.csv RUN_DIR [--frames N] [--gains JSON]
           [--source-frames DIR]   (to build side-by-side sheets)
Writes RUN_DIR/render/, RUN_DIR/render.csv, RUN_DIR/check.json.
"""
import argparse
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
sys.path.insert(0, HERE)
from recipes import face_anim, render  # noqa: E402
from face_response import face_scene  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("source")
ap.add_argument("run_dir")
ap.add_argument("--frames", type=int, default=0)
ap.add_argument("--gains", default="{}")
ap.add_argument("--source-frames", default="")
ap.add_argument("--no-render", action="store_true")
ap.add_argument("--no-topup", action="store_true")
ap.add_argument("--head", action="store_true", help="also drive head rotation (skeleton, relaxed pose)")
ap.add_argument("--refine", default="", help="previous run dir: correct jawOpen by its lip-gap error")
a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
os.makedirs(os.path.join(a.run_dir, "render"), exist_ok=True)

times, chans = face_anim.read_curves(a.source)
n = a.frames or len(times)
times = times[:n]
chans = {k: v[:n] for k, v in chans.items()}
rate = 1.0 / float(np.median(np.diff(times)))
neutral = {u: float(np.nanpercentile(chans[u], 5)) for u in face_anim.ARKIT if u in chans and not np.all(np.isnan(chans[u]))}
gains = json.loads(a.gains)
values = face_anim.prepare(chans, rate, neutral=neutral, gain=gains)
TOPUP = "--no-topup" not in sys.argv
if TOPUP:
    resp = json.load(open(os.path.join(HERE, "results_face_response.json")))
    lip_per_unit = {u: v["lip_gap"] for u, v in resp["landmark_rise_per_unit"].items()}
    src_lip = face_anim.zero_phase(np.nan_to_num(chans["lip_gap"]), rate)
    jc = json.load(open(os.path.join(HERE, "results_face_jaw_curve.json")))
    values = face_anim.lip_top_up(values, src_lip, lip_per_unit, resp["neutral_landmarks"]["lip_gap"],
                                  jaw_curve=(jc["jawOpen"], jc["lip_gap_alone"]))

if a.refine:
    # One feedback pass: frame by frame, move jawOpen along the measured jaw curve by the
    # previous render's lip-gap error. Lip gap is then fitted, not an independent check.
    prev = np.load(os.path.join(a.refine, "keys.npz"))
    _, prev_got = face_anim.read_curves(os.path.join(a.refine, "render.csv"))
    jc = json.load(open(os.path.join(HERE, "results_face_jaw_curve.json")))
    lv, lp = np.array(jc["jawOpen"]), np.maximum.accumulate(np.array(jc["lip_gap_alone"]))
    jaw_prev = prev["jawOpen"][:n]
    lip_at_prev = np.interp(jaw_prev, lv, lp)
    err = np.nan_to_num(face_anim.zero_phase(np.nan_to_num(chans["lip_gap"]), rate) - prev_got["lip_gap"][:n])
    values["jawOpen"] = np.clip(np.interp(lip_at_prev + err, lp, lv), 0.0, 1.0)
np.savez(os.path.join(a.run_dir, "keys.npz"), **values)

if not a.no_render:
    scene, root = face_scene(pose="relaxed" if a.head else None)
    head = None
    if a.head:
        head = {k: face_anim.zero_phase(np.nan_to_num(chans["head_" + k] - np.nanmedian(chans["head_" + k])), rate)
                for k in ("yaw", "pitch", "roll")}
        axes = json.load(open(os.path.join(HERE, "results_face_head_axes.json")))["tracker_per_bone_degree"]
    last = face_anim.apply_curves(root, values, frame_start=1, head=head,
                                  tracker_per_bone=axes if a.head else None)
    scene.frame_start, scene.frame_end = 1, last
    for f in range(1, last + 1):
        scene.frame_set(f)
        render.render_to(scene, os.path.join(a.run_dir, "render", f"{f:04d}.png"))

out_csv = os.path.join(a.run_dir, "render.csv")
subprocess.run([os.path.join(ROOT, ".venv-face", "bin", "python"), "-I", os.path.join(ROOT, "tools", "face_track.py"),
                os.path.join(a.run_dir, "render"), out_csv, "--fps", str(rate)], check=True, stderr=subprocess.DEVNULL)
_, got = face_anim.read_curves(out_csv)


def compare(x, y, max_lag=6):
    m = ~np.isnan(x) & ~np.isnan(y)
    x, y = x[m], y[m]
    best = (-2.0, 0)
    for lag in range(-max_lag, max_lag + 1):
        xs, ys = (x[:len(x) - lag], y[lag:]) if lag >= 0 else (x[-lag:], y[:len(y) + lag])
        r = float(np.corrcoef(xs, ys)[0, 1])
        best = max(best, (r, lag))
    amp = lambda z: float(np.percentile(z, 95) - np.percentile(z, 5))
    return {"r_lag0": round(float(np.corrcoef(x, y)[0, 1]), 3), "r_best": round(best[0], 3), "lag_frames": best[1],
            "amplitude_ratio_render_over_source": round(amp(y) / max(amp(x), 1e-9), 3)}


check = {"frames": n, "rate": round(rate, 3), "gains": gains, "lip_top_up": TOPUP, "refined_from": a.refine, "smoothing": "one-euro forward+backward",
         "found_in_render": int(np.sum(got["found"] == 1)),
         "lip_gap": compare(chans["lip_gap"], got["lip_gap"][:n]),
         "eye_open_l": compare(chans["eye_open_l"], got["eye_open_l"][:n]),
         "eye_open_r": compare(chans["eye_open_r"], got["eye_open_r"][:n]),
         "head": {k: compare(chans["head_" + k], got["head_" + k][:n]) for k in ("yaw", "pitch", "roll")},
         "blendshapes": {u: compare(chans[u], got[u][:n]) for u in
                         ("eyeBlinkLeft", "eyeBlinkRight", "mouthSmileLeft", "mouthSmileRight",
                          "mouthUpperUpLeft", "mouthLowerDownLeft", "browInnerUp", "mouthPucker")}}
print(json.dumps({k: check[k] for k in ("found_in_render", "lip_gap", "eye_open_l", "eye_open_r")}, indent=1))
json.dump(check, open(os.path.join(a.run_dir, "check.json"), "w"), indent=1)

if a.source_frames:
    # Side-by-side contact sheet: source frame | our render, every k-th frame.
    from PIL import Image, ImageDraw
    src = sorted(os.listdir(a.source_frames))
    picks = np.linspace(0, n - 1, 8).astype(int)
    tiles = []
    for i in picks:
        s = Image.open(os.path.join(a.source_frames, src[i])).convert("RGB")
        s = s.resize((round(s.width * 240 / s.height), 240))
        cx = int(s.width * float(os.environ.get("CROP_X", 0.5)))
        s = s.crop((cx - 120, 0, cx + 120, 240))
        r = Image.open(os.path.join(a.run_dir, "render", f"{i + 1:04d}.png")).convert("RGB")
        tile = Image.new("RGB", (480, 262), (20, 20, 20))
        tile.paste(s, (0, 22)); tile.paste(r, (240, 22))
        ImageDraw.Draw(tile).text((6, 5), f"frame {i + 1}  lip gap src {chans['lip_gap'][i]:.3f}  ours {got['lip_gap'][i]:.3f}",
                                  fill=(235, 235, 235))
        tiles.append(tile)
    sheet = Image.new("RGB", (960, 262 * 4), (20, 20, 20))
    for k, t in enumerate(tiles):
        sheet.paste(t, ((k % 2) * 480, (k // 2) * 262))
    sheet.save(os.path.join(a.run_dir, "side_by_side.png"))
