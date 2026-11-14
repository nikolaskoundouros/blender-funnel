"""Face video -> per-frame ARKit blendshapes, head angles and landmark measures (CSV).

Runs MediaPipe Face Landmarker (Apache-2.0) in its own environment, not inside Blender:
    uv venv -p 3.13 .venv-face && uv pip install -p .venv-face/bin/python mediapipe==1.2.3
    apt install libegl1 libgles2            # MediaPipe links them even on the CPU path
Model: assets/models/face_landmarker.task (tools/fetch_assets.sh).

Usage:
    .venv-face/bin/python -I tools/face_track.py VIDEO_OR_FRAME_DIR out.csv [--fps 24] [--max-seconds 30]
A directory is read as sorted PNG/JPG frames at --fps. Columns: frame, time_s, found, the 52
ARKit names (tongueOut is empty: MediaPipe does not report it), head_yaw/pitch/roll in
degrees from the face transform, lip_gap (inner-lip gap / face width), eye_open_l/r
(lid gap / face width, subject's left/right) and brow_l/r (brow height above the eye corners /
face width). The last five come from landmarks only, so they check the blendshape scores
independently.
"""
import argparse
import csv
import math
import os
import sys

import cv2
import mediapipe as mp
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(ROOT, "assets", "models", "face_landmarker.task")
ARKIT = ["browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight",
         "cheekPuff", "cheekSquintLeft", "cheekSquintRight", "eyeBlinkLeft", "eyeBlinkRight",
         "eyeLookDownLeft", "eyeLookDownRight", "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft",
         "eyeLookOutRight", "eyeLookUpLeft", "eyeLookUpRight", "eyeSquintLeft", "eyeSquintRight",
         "eyeWideLeft", "eyeWideRight", "jawForward", "jawLeft", "jawOpen", "jawRight", "mouthClose",
         "mouthDimpleLeft", "mouthDimpleRight", "mouthFrownLeft", "mouthFrownRight", "mouthFunnel",
         "mouthLeft", "mouthLowerDownLeft", "mouthLowerDownRight", "mouthPressLeft", "mouthPressRight",
         "mouthPucker", "mouthRight", "mouthRollLower", "mouthRollUpper", "mouthShrugLower",
         "mouthShrugUpper", "mouthSmileLeft", "mouthSmileRight", "mouthStretchLeft", "mouthStretchRight",
         "mouthUpperUpLeft", "mouthUpperUpRight", "noseSneerLeft", "noseSneerRight", "tongueOut"]
EXTRA = ["head_yaw", "head_pitch", "head_roll", "lip_gap", "eye_open_l", "eye_open_r", "brow_l", "brow_r"]
# Face Mesh landmark indices (canonical face model): inner lips 13/14, cheeks 234/454,
# lids of the subject's left eye 386/374 and right eye 159/145.
LIP, CHEEKS, EYE_L, EYE_R = (13, 14), (234, 454), (386, 374), (159, 145)
# Upper brow contour, subject's left (293, 334, 296) and right (63, 105, 66).
BROW_L, BROW_R = (293, 334, 296), (63, 105, 66)
# Eye corners (inner, outer) do not move in a blink: subject's left 362/263, right 133/33.
CORNERS_L, CORNERS_R = (362, 263), (133, 33)


def frames(src, fps, max_seconds):
    """Yield (index, time in seconds, RGB array)."""
    if os.path.isdir(src):
        names = sorted(n for n in os.listdir(src) if n.lower().endswith((".png", ".jpg", ".jpeg")))
        for i, n in enumerate(names):
            if i / fps > max_seconds:
                return
            img = cv2.imread(os.path.join(src, n))
            yield i, i / fps, cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return
    cap = cv2.VideoCapture(src)
    rate = cap.get(cv2.CAP_PROP_FPS) or fps
    i = 0
    while True:
        ok, img = cap.read()
        if not ok:
            return
        t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0 or i / rate
        if t > max_seconds:
            return
        yield i, t, cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        i += 1


def head_angles(m):
    """Yaw, pitch, roll in degrees from MediaPipe's 4x4 face transform (rotation part).
    Decomposition R = Ry(yaw) Rx(pitch) Rz(roll); signs checked in experiments (P6)."""
    r = np.array(m)[:3, :3]
    r = r / np.cbrt(np.linalg.det(r))
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, -r[1, 2]))))
    yaw = math.degrees(math.atan2(r[0, 2], r[2, 2]))
    roll = math.degrees(math.atan2(r[1, 0], r[1, 1]))
    return yaw, pitch, roll


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--fps", type=float, default=24.0)
    ap.add_argument("--max-seconds", type=float, default=1e9)
    ap.add_argument("--model", default=MODEL)
    a = ap.parse_args()
    opts = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=a.model),
        running_mode=mp.tasks.vision.RunningMode.VIDEO, num_faces=1,
        output_face_blendshapes=True, output_facial_transformation_matrixes=True)
    found = 0
    with mp.tasks.vision.FaceLandmarker.create_from_options(opts) as lm, open(a.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["frame", "time_s", "found"] + ARKIT + EXTRA)
        last_ms = -1
        for i, t, rgb in frames(a.src, a.fps, a.max_seconds):
            ms = max(int(round(t * 1000)), last_ms + 1)
            last_ms = ms
            res = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)), ms)
            if not res.face_landmarks:
                w.writerow([i, f"{t:.4f}", 0] + [""] * (len(ARKIT) + len(EXTRA)))
                continue
            found += 1
            scores = {c.category_name: c.score for c in res.face_blendshapes[0]}
            p = np.array([[q.x * rgb.shape[1], q.y * rgb.shape[0]] for q in res.face_landmarks[0]])
            width = np.linalg.norm(p[CHEEKS[0]] - p[CHEEKS[1]])
            gap = lambda ab: np.linalg.norm(p[ab[0]] - p[ab[1]]) / width
            yaw, pitch, roll = head_angles(res.facial_transformation_matrixes[0])
            row = [f"{scores[n]:.5f}" if n in scores else "" for n in ARKIT]
            brow = lambda ids, corners: (p[list(corners), 1].mean() - p[list(ids), 1].mean()) / width  # above the eye corners
            row += [f"{v:.3f}" for v in (yaw, pitch, roll)] + [f"{v:.5f}" for v in (gap(LIP), gap(EYE_L), gap(EYE_R),
                                                                                  brow(BROW_L, CORNERS_L), brow(BROW_R, CORNERS_R))]
            w.writerow([i, f"{t:.4f}", 1] + row)
    print(f"{a.out}: face found in {found} frames", file=sys.stderr)


if __name__ == "__main__":
    main()
