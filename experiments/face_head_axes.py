"""P6 (notes/facial-mocap-plan.md): which head-bone axis gives which tracked head angle.

Rotates the boy's neck01 and head bones (40/60 split, as apply_curves) by a total of
+-10 degrees about each local axis, renders a
front close-up, and reads yaw/pitch/roll from tools/face_track.py (MediaPipe's face
transform). Writes experiments/results_face_head_axes.json with the 3x3 response
(tracker degrees per bone degree), used by recipes/face_anim.apply_curves.
"""
import json
import math
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

OUT = os.path.join(ROOT, "runs", "017-faceunits", "matrix_frames_head")
os.makedirs(OUT, exist_ok=True)
scene, root = face_scene(pose="relaxed")
# Same split over neck01 and head as recipes/face_anim.apply_curves uses by default.
SPLIT = (("neck01", 0.4), ("head", 0.6))
bones = [(root.pose.bones[b], share) for b, share in SPLIT]
for pb, _ in bones:
    pb.rotation_mode = "XYZ"
bases = [pb.rotation_euler.copy() for pb, _ in bones]
cases = [("neutral", None, 0)] + [(f"{ax}{sg:+d}", i, sg * 10) for i, ax in enumerate("xyz") for sg in (1, -1)]
for k, (name, axis, deg) in enumerate(cases):
    for (pb, share), base in zip(bones, bases):
        e = base.copy()
        if axis is not None:
            e[axis] += math.radians(deg * share)
        pb.rotation_euler = e
    bpy.context.view_layer.update()
    render.render_to(scene, os.path.join(OUT, f"{k:03d}_{name}.png"))
csv_path = os.path.join(OUT, "track.csv")
subprocess.run([os.path.join(ROOT, ".venv-face", "bin", "python"), "-I", os.path.join(ROOT, "tools", "face_track.py"),
                OUT, csv_path, "--fps", "1"], check=True, stderr=subprocess.DEVNULL)
_, got = face_anim.read_curves(csv_path)
ang = np.stack([got["head_yaw"], got["head_pitch"], got["head_roll"]], axis=1)
rel = ang - ang[0]
res = {"split": SPLIT, "neutral_yaw_pitch_roll": ang[0].round(2).tolist(),
       "per_case": {name: rel[k].round(2).tolist() for k, (name, _, _) in enumerate(cases)}}
# Response matrix: rows tracker (yaw, pitch, roll), columns bone axis (x, y, z), deg/deg,
# from the +-10 degree difference.
M = np.zeros((3, 3))
for i in range(3):
    M[:, i] = (rel[1 + 2 * i] - rel[2 + 2 * i]) / 20.0
res["tracker_per_bone_degree"] = M.round(3).tolist()
print(json.dumps(res, indent=1))
json.dump(res, open(os.path.join(HERE, "results_face_head_axes.json"), "w"), indent=1)
