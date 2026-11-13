"""Measure that code-sculpt edits do what they say, and that clothes follow them.

Usage: python experiments/verify_sculpt.py
"""
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from recipes import garments, hair, human, sculpt, stage  # noqa: E402

S = dict(gender=1.0, age=0.55, muscle=0.6, weight=0.55, height=0.5, caucasian=1, african=0, asian=0)
results = {}
a = human.to_blender(human.morphed_base(**S))
marks = sculpt.landmarks(a)

# K1: grab moves the centre by the offset and nothing beyond the radius
b = human.to_blender(human.morphed_base(sculpt=[sculpt.grab("chin", 0.035, (0, -0.006, 0))], **S))
d = np.linalg.norm(b - a, axis=1)
near = np.argmin(np.linalg.norm(a - marks["chin"], axis=1))
far = np.linalg.norm(a - marks["chin"], axis=1) > 0.035
results["K1"] = {"claim": "grab moves the centre by the offset, nothing outside the radius",
                 "values_mm": {"at_centre": round(float(d[near]) * 1000, 2), "max_outside_radius": round(float(d[far].max()) * 1000, 4)},
                 "confirmed": bool(abs(d[near] - 0.006) < 0.0005 and d[far].max() < 1e-9)}

# K2: mirror gives a symmetric result
b = human.to_blender(human.morphed_base(sculpt=[sculpt.inflate("cheekbone.L", 0.03, 0.004, mirror=True)], **S))
mv = b - a
left = np.nonzero((a[:, 0] > 0.01) & (np.linalg.norm(mv, axis=1) > 1e-5))[0]
mirror_pts = a[left] * np.array([-1, 1, 1])
tree = BVHTree.FromPolygons([Vector(p) for p in a], [])
idx = np.array([np.argmin(np.linalg.norm(a - p, axis=1)) for p in mirror_pts[:300]])
gap = np.abs(np.linalg.norm(mv[left[:300]], axis=1) - np.linalg.norm(mv[idx], axis=1))
results["K2"] = {"claim": "mirror=True moves left and right sides alike",
                 "values_mm": {"max_left_move": round(float(np.linalg.norm(mv[left], axis=1).max()) * 1000, 2),
                               "median_left_right_difference": round(float(np.median(gap)) * 1000, 3)},
                 "confirmed": bool(np.median(gap) < 0.0003)}

# K3: smoothing removes bumps. Bumps (random 1.5 mm dents) are added on the forehead, then
# smoothed; the measure is how far the surface is from the original, before and after.
# (First version measured mean curvature, which smoothing is designed to keep: a sphere
# has curvature everywhere. It reported "not confirmed" for a tool that works.)
rng = np.random.default_rng(0)
zone = np.linalg.norm(a - marks["forehead"], axis=1) < 0.03
zone[human.BODY_VERTS:] = False          # skin only; helpers follow the skin
noisy = a.copy()
noisy[zone] += rng.normal(0.0, 0.0015, (zone.sum(), 3))
smoothed = sculpt.to_blender(sculpt.apply(sculpt.to_mh(noisy), [sculpt.smooth("forehead", 0.06)]))
err0 = float(np.sqrt(((noisy[zone] - a[zone]) ** 2).sum(axis=1).mean()))
err1 = float(np.sqrt(((smoothed[zone] - a[zone]) ** 2).sum(axis=1).mean()))
# Skeleton must not move: the joint cubes are helpers inside the smoothed region.
from recipes import rig  # noqa: E402
bones = rig.read_rig("default")
jmove = max(np.linalg.norm(np.array(rig._position(b["head"], smoothed)) - np.array(rig._position(b["head"], noisy)))
            for b in bones.values())
results["K3"] = {"claim": "smooth removes bumps while keeping the shape and the skeleton", "values_mm": {
    "rms_bumpy": round(err0 * 1000, 3), "rms_smoothed": round(err1 * 1000, 3), "max_joint_move": round(float(jmove) * 1000, 2)},
    "confirmed": bool(err1 < 0.5 * err0 and jmove < 0.002)}

# K4: clothes follow a sculpted body (a big belly under a shirt)
scene = stage.new_scene()
edits = [sculpt.inflate("belly", 0.16, 0.035)]
root = human.build_human(scene, name="K", outfit=(garments.top(name="shirt", sleeve=0.4, ease=0.006),), hair=None,
                         sculpt=edits, **S)
body = root
shirt = next(c for c in root.children if c.name.endswith("_shirt"))
bv, bf = hair.evaluated_mesh(body)
full_faces = [f for f in human.base_mesh()[2] if all(v < human.BODY_VERTS for v in f)]
whole = human.to_blender(human.morphed_base(sculpt=edits, **S))[:human.BODY_VERTS]
tree = BVHTree.FromPolygons([Vector(p) for p in whole], full_faces)
sv, _ = hair.evaluated_mesh(shirt)
inside = sum(1 for p in sv if (Vector(p) - tree.find_nearest(Vector(p))[0]).dot(tree.find_nearest(Vector(p))[1]) < -0.003)
belly_move = float(np.linalg.norm(whole - a[:human.BODY_VERTS], axis=1).max())
results["K4"] = {"claim": "clothes follow a sculpted body", "values": {"belly_moved_mm": round(belly_move * 1000, 1),
                 "shirt_points_inside_skin": round(inside / len(sv), 4)}, "confirmed": bool(belly_move > 0.03 and inside / len(sv) < 0.01)}

with open(os.path.join(HERE, "results_sculpt.json"), "w") as fh:
    json.dump(results, fh, indent=2)
print("RESULTS " + json.dumps(results))
