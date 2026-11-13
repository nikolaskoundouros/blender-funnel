"""Measure how well a motion-capture clip transfers onto a character.

Usage: python experiments/verify_motion.py [clip.bvh]
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from recipes import human, motion, stage  # noqa: E402

CLIP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(human.ASSETS, "motion", "cmu", "05_02.bvh")
OUTFIT = ("female_sportsuit01", "shoes03")
results = {"clip": os.path.basename(CLIP)}


def evaluated(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mesh = ev.to_mesh()
    verts = np.array([ev.matrix_world @ v.co for v in mesh.vertices])
    faces = [tuple(p.vertices) for p in mesh.polygons]
    ev.to_mesh_clear()
    return verts, faces


def volume(verts, faces):
    total = 0.0
    for f in faces:
        a = verts[f[0]]
        for i in range(1, len(f) - 1):
            total += np.dot(a, np.cross(verts[f[i]], verts[f[i + 1]]))
    return abs(total) / 6.0


clip = motion.read_bvh(CLIP)
scene = stage.new_scene()
root = human.build_human(scene, name="D", outfit=OUTFIT, hair="ponytail01", pose=[],
                         rig_name="cmu_mb", gender=0.0)
body = next(c for c in root.children if c.name == "D")
rest_volume_clothed = None
m = motion.retarget(root, clip)
n = motion.apply(root, m)
sample = [int(x) for x in np.linspace(0, n - 1, 10)]

# M1 -----------------------------------------------------------------------------------
# On each sampled frame, every limb of the character should point the way the clip's limb
# points. This tests the whole chain: BVH reading, axis conversion, the reference pose,
# and the conversion to Blender's parent-relative bone rotations.
joint_index = {j["name"]: i for i, j in enumerate(clip["joints"])}
src_dir = {name: m["source_rest_direction"][i] for name, i in joint_index.items()}
unmatched = sorted(name for name, d in src_dir.items() if d is None)
limbs = ["LeftArm", "LeftForeArm", "RightArm", "RightForeArm", "LeftUpLeg", "LeftLeg",
         "RightUpLeg", "RightLeg", "Spine", "Spine1", "Head"]
errors = {name: [] for name in limbs}
for f in sample:
    scene.frame_set(1 + f)
    for name in limbs:
        pb = root.pose.bones[name]
        have = (root.matrix_world @ pb.tail - root.matrix_world @ pb.head).normalized()
        want = Vector(m["source_rotations"][f, joint_index[name]] @ src_dir[name])
        errors[name].append(math.degrees(have.angle(want)))
results["M1"] = {
    "claim": "Every limb of the character points where the clip's limb points",
    "max_error_degrees_per_limb": {k: round(max(v), 3) for k, v in errors.items()},
    "frames_checked": len(sample),
    "bones_keeping_their_own_rest_orientation": unmatched,
    "confirmed": bool(max(max(v) for v in errors.values()) < 1.0),
}

# M2 -----------------------------------------------------------------------------------
# Feet and floor. Toe joints rest about 2 cm above the floor; over the clip the lower toe
# should come down to that height but not go far beneath it.
toe_rest = min(root.data.bones[b].head_local.z for b in ("LeftToeBase", "RightToeBase"))
lows = []
for f in range(n):
    scene.frame_set(1 + f)
    lows.append(min((root.matrix_world @ root.pose.bones[b].head).z for b in ("LeftToeBase", "RightToeBase")))
lows = np.array(lows)
results["M2"] = {
    "claim": "The lower foot reaches the floor and does not sink more than 3 cm below it",
    "values_m": {"toe_joint_height_at_rest": round(float(toe_rest), 3),
                 "lowest_over_clip": round(float(lows.min()), 3),
                 "typical_low_5th_percentile": round(float(np.percentile(lows, 5)), 3),
                 "highest_low_point": round(float(lows.max()), 3)},
    "frames_below_floor_by_3cm": int((lows < toe_rest - 0.03).sum()),
    "frames": int(n),
    "confirmed": bool((lows < toe_rest - 0.03).mean() < 0.03),
}

# M3 -----------------------------------------------------------------------------------
# Clothes during the dance: outfit vertices more than 5 mm inside visible skin.
all_faces = human.base_mesh()[2]
body_faces = [f for f in all_faces if all(v < human.BODY_VERTS for v in f)]
covered = set()
for item_name in OUTFIT:
    covered |= human.read_mhclo(human.find_asset("clothes", item_name))["delete"]
hidden = [all(v in covered for v in f) for f in body_faces]
poke = {}
for f in sample:
    scene.frame_set(1 + f)
    bverts = evaluated(body)[0]
    tree = BVHTree.FromPolygons([Vector(v) for v in bverts], body_faces)
    inside = total = 0
    for child in root.children:
        if child.name.split("_", 1)[-1] in OUTFIT:
            for p in evaluated(child)[0]:
                loc, normal, face, _ = tree.find_nearest(Vector(p))
                inside += (Vector(p) - loc).dot(normal) < -0.005 and not hidden[face]
                total += 1
    poke[f"frame {1 + f}"] = round(inside / total, 4)
results["M3"] = {
    "claim": "Clothes stay over the skin while dancing (under 2 percent of vertices, 5 mm)",
    "values_fraction_inside_visible_skin": poke,
    "confirmed": bool(max(poke.values()) < 0.02),
}

# M4 -----------------------------------------------------------------------------------
# Joint collapse during the dance, on an unclothed copy with the same motion.
scene = stage.new_scene()
bare = human.build_human(scene, name="N", outfit=(), hair=None, eyes=None, eyebrows=None,
                         eyelashes=None, teeth=False, pose=[], rig_name="cmu_mb", gender=0.0)
bare_body = next(c for c in bare.children if c.name == "N")
rest_volume = volume(*evaluated(bare_body))
motion.apply(bare, motion.retarget(bare, clip))
ratios = {}
for f in sample:
    scene.frame_set(1 + f)
    ratios[f"frame {1 + f}"] = round(float(volume(*evaluated(bare_body)) / rest_volume), 4)
results["M4"] = {
    "claim": "Body volume stays within 5 percent of rest through the dance",
    "values_posed_over_rest": ratios,
    "confirmed": bool(all(abs(v - 1.0) < 0.05 for v in ratios.values())),
}

# M5 -----------------------------------------------------------------------------------
# M1 only shows our own steps agree with each other. An independent reading of the same
# file is Blender's bundled BVH importer: load the clip with it and compare where its
# skeleton's limbs point with where our reader says the clip's limbs point.
import addon_utils  # noqa: E402

scene = stage.new_scene()
addon_utils.enable("io_anim_bvh")
bpy.ops.import_anim.bvh(filepath=CLIP, global_scale=1.0, frame_start=1, use_fps_scale=False,
                        rotate_mode="NATIVE", axis_forward="-Z", axis_up="Y")
imported = bpy.context.object
agree = {name: [] for name in limbs}
for f in sample:
    scene.frame_set(int(m["frame_indices"][f]) + 1)
    for name in limbs:
        pb = imported.pose.bones[name]
        theirs = (imported.matrix_world @ pb.tail - imported.matrix_world @ pb.head).normalized()
        ours = Vector(m["source_rotations"][f, joint_index[name]] @ src_dir[name])
        agree[name].append(math.degrees(theirs.angle(ours)))
results["M5"] = {
    "claim": "Our BVH reader agrees with Blender's own BVH importer on where limbs point",
    "max_difference_degrees_per_limb": {k: round(max(v), 3) for k, v in agree.items()},
    "confirmed": bool(max(max(v) for v in agree.values()) < 1.0),
}

with open(os.path.join(HERE, "results_motion.json"), "w") as fh:
    json.dump(results, fh, indent=2)
print("RESULTS " + json.dumps(results, indent=2))
