"""Lip sync from audio: drive the boy's Visemes 01 shape keys from tools/voice_track.py.

Renders 240x240 close-ups, muxes the audio into RUN_DIR/talk.mp4, and, when a video track
of the same speech is given (tools/face_track.py on the speaker's video), compares our
render's landmark lip gap with the real speaker's: Pearson r, best lag, amplitude ratio.

Usage: python experiments/voice_drive.py VOICE.csv AUDIO RUN_DIR [--start S]
           [--gain G] [--truth VIDEO_TRACK.csv] [--blinks]
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from recipes import face_anim, looks, render  # noqa: E402
from face_response import face_scene  # noqa: E402
from face_metrics import compare  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("voice")
ap.add_argument("audio")
ap.add_argument("run_dir")
ap.add_argument("--start", type=float, default=0.0)
ap.add_argument("--gain", type=float, default=1.0)
ap.add_argument("--truth", default="")
ap.add_argument("--blinks", action="store_true")
ap.add_argument("--no-render", action="store_true")
a = ap.parse_args()
os.makedirs(os.path.join(a.run_dir, "render"), exist_ok=True)

times, chans = face_anim.read_curves(a.voice)
n = len(times)
fps = 1.0 / float(np.median(np.diff(times)))
values = {v: np.clip(chans[v] * a.gain, 0.0, 2.0) for v in face_anim.VISEMES}   # keys allow up to 3
values["mouthPucker"] = np.zeros(n)                      # carries the rest offset (REST_OFFSET)
if a.blinks:
    # Idle blinks: every 2 to 5 s, 150 ms closing and opening (no source for them in audio).
    rng = np.random.default_rng(1)
    blink = np.zeros(n)
    t = rng.uniform(0.5, 2.0)
    while t < n / fps:
        c = int(t * fps)
        for k, w in zip(range(c - 2, c + 3), (0.4, 0.9, 1.0, 0.8, 0.3)):
            if 0 <= k < n:
                blink[k] = max(blink[k], w)
        t += rng.uniform(2.0, 5.0)
    values["eyeBlinkLeft"] = values["eyeBlinkRight"] = blink

if not a.no_render:
    scene, root = face_scene()
    face_anim.add_faceunit_keys(root, units=face_anim.VISEMES, **looks.CURLY_BOY_SLIDERS)
    last = face_anim.apply_curves(root, values, frame_start=1)
    scene.frame_start, scene.frame_end = 1, last
    for f in range(1, last + 1):
        scene.frame_set(f)
        render.render_to(scene, os.path.join(a.run_dir, "render", f"{f:04d}.png"))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", os.path.join(a.run_dir, "render", "%04d.png"),
                    "-ss", str(a.start), "-t", str(n / fps), "-i", a.audio, "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-c:a", "aac", "-shortest",
                    os.path.join(a.run_dir, "talk.mp4")], check=True)

check = {"frames": n, "fps": round(fps, 3), "gain": a.gain, "blinks": a.blinks}
if a.truth:
    out_csv = os.path.join(a.run_dir, "render.csv")
    subprocess.run([os.path.join(ROOT, ".venv-face", "bin", "python"), "-I", os.path.join(ROOT, "tools", "face_track.py"),
                    os.path.join(a.run_dir, "render"), out_csv, "--fps", str(fps)], check=True, stderr=subprocess.DEVNULL)
    _, got = face_anim.read_curves(out_csv)
    _, truth = face_anim.read_curves(a.truth)
    m = min(n, len(truth["lip_gap"]), len(got["lip_gap"]))
    check["lip_gap_vs_real_video"] = compare(truth["lip_gap"][:m], got["lip_gap"][:m], max_lag=8)
    check["loudness_vs_real_lip_gap"] = compare(truth["lip_gap"][:m], chans["loudness"][:m], max_lag=8)
    print(json.dumps(check, indent=1))
json.dump(check, open(os.path.join(a.run_dir, "check.json"), "w"), indent=1)
