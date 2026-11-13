"""Measure rig quality: are weights complete, is the skeleton symmetric, and do the body
and clothes hold together when posed?

Usage: python experiments/verify_rig.py
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

from recipes import human, rig, stage  # noqa: E402

results = {}


def evaluated(obj):
    """World-space vertex positions and faces after modifiers (i.e. after the pose)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mesh = ev.to_mesh()
    verts = np.array([ev.matrix_world @ v.co for v in mesh.vertices])
    faces = [tuple(p.vertices) for p in mesh.polygons]
    ev.to_mesh_clear()
    return verts, faces


def volume(verts, faces):
    """Signed volume of a mesh (fan-triangulated). Only ratios are used."""
    total = 0.0
    for f in faces:
        a = verts[f[0]]
        for i in range(1, len(f) - 1):
            total += np.dot(a, np.cross(verts[f[i]], verts[f[i + 1]]))
    return abs(total) / 6.0


# R1 -----------------------------------------------------------------------------------
# Every body vertex should be fully owned by bones: weights present and summing to 1.
report = {}
for rig_name in ("default", "mixamo", "game_engine", "cmu_mb"):
    names = list(rig.read_rig(rig_name).keys())
    table = rig._weight_matrix(rig_name, names, normalize=False)[:human.BODY_VERTS]  # as shipped
    sums = table.sum(axis=1)
    report[rig_name] = {
        "bones": len(names),
        "unweighted_body_vertices": int((sums < 1e-4).sum()),
        "weight_sum_min": round(float(sums.min()), 3),
        "weight_sum_max": round(float(sums.max()), 3),
        "most_bones_on_one_vertex": int((table > 1e-4).sum(axis=1).max()),
    }
results["R1"] = {
    "claim": "Every body vertex is weighted in all four rigs; default and game_engine sum to 1",
    "values_as_shipped": report,
    "note": "mixamo weights are complete but not normalised in the file; the loader normalises them",
    "confirmed": bool(all(v["unweighted_body_vertices"] == 0 for v in report.values())
                      and all(0.98 < report[r]["weight_sum_min"] and report[r]["weight_sum_max"] < 1.02
                              for r in ("default", "game_engine"))),
}

# R2 -----------------------------------------------------------------------------------
# The skeleton is placed from helper cubes on the morphed body, so it should stay
# left/right symmetric and inside the body's height on very different bodies.
sym = {}
for label, sliders in {"default": {}, "heavy tall male": dict(gender=1, weight=1, height=0.9),
                       "child": dict(age=0.19), "slim short female": dict(gender=0, weight=0, height=0.1)}.items():
    scene = stage.new_scene()
    root = human.build_human(scene, name="T", outfit=(), hair=None, pose=[], **sliders)
    bones = root.data.bones
    worst = 0.0
    for b in bones:
        # tongue07 differs by 1 mm left to right in the source data; not a limb, ignored.
        if b.name.endswith(".L") and b.name[:-2] + ".R" in bones and not b.name.startswith("tongue"):
            other = bones[b.name[:-2] + ".R"]
            worst = max(worst, abs(b.length - other.length) / max(b.length, 1e-9))
    top = max(max(b.head_local.z, b.tail_local.z) for b in bones)
    sym[label] = {"worst_left_right_length_difference": round(float(worst), 4),
                  "highest_bone_point_m": round(float(top), 3),
                  "body_height_m": round(root["funnel_height_m"], 3)}
results["R2"] = {
    "claim": "The skeleton stays symmetric and inside the body on different body shapes",
    "values": sym,
    "confirmed": bool(all(v["worst_left_right_length_difference"] < 0.01
                          and v["highest_bone_point_m"] <= v["body_height_m"] + 0.01 for v in sym.values())),
}

# R3 -----------------------------------------------------------------------------------
# Linear-blend skinning can make joints collapse when bent. Measure how much body volume
# is lost in each pose (unclothed body, so the mesh is whole).
vol = {}
for pose in ("relaxed", "wave", "akimbo"):
    scene = stage.new_scene()
    root = human.build_human(scene, name="V", outfit=(), hair=None, eyes=None, eyebrows=None,
                             eyelashes=None, teeth=False, pose=[])
    body = next(c for c in root.children if c.name == "V")
    rest = volume(*evaluated(body))
    rig.apply_pose(root, pose)
    vol[pose] = round(float(volume(*evaluated(body)) / rest), 4)
results["R3"] = {
    "claim": "Posing changes body volume by less than 3 percent (no badly collapsing joints)",
    "values_posed_over_rest": vol,
    "confirmed": bool(all(abs(v - 1.0) < 0.03 for v in vol.values())),
}

# R4 -----------------------------------------------------------------------------------
# Clothes take their weights from the body. After posing, do they still cover the skin?
# Count outfit vertices lying more than 5 mm inside skin that is still visible, in the
# modelling pose and in each named pose, so the effect of posing can be separated from
# how well the outfit fitted in the first place.
#
# (First attempt measured against the clothed body, whose covered skin has been removed.
# Vertices over those holes were compared with far-away skin seen from behind, which
# reported 20 percent "inside" for a skirt that was fine.)
all_faces = human.base_mesh()[2]
body_faces = [f for f in all_faces if all(v < human.BODY_VERTS for v in f)]
poke = {}
for outfit, sliders in [(("female_casualsuit01", "shoes01"), dict(gender=0.0)),
                        (("male_worksuit01", "shoes04"), dict(gender=1.0, weight=0.75)),
                        (("female_elegantsuit01", "shoes02"), dict(gender=0.0, age=0.8))]:
    covered = set()
    for item_name in outfit:
        covered |= human.read_mhclo(human.find_asset("clothes", item_name))["delete"]
    hidden = [all(v in covered for v in f) for f in body_faces]
    row = {}
    for pose in ("modelling pose", "relaxed", "wave", "akimbo"):
        scene = stage.new_scene()
        root = human.build_human(scene, name="C", outfit=outfit, hair=None,
                                 pose=[] if pose == "modelling pose" else pose, **sliders)
        body = next(c for c in root.children if c.name == "C")
        bverts = evaluated(body)[0]            # all body vertices, including covered ones
        tree = BVHTree.FromPolygons([Vector(v) for v in bverts], body_faces)
        inside = total = 0
        for child in root.children:
            if child.name.split("_", 1)[-1] in outfit:
                for p in evaluated(child)[0]:
                    loc, normal, face, _ = tree.find_nearest(Vector(p))
                    inside += (Vector(p) - loc).dot(normal) < -0.005 and not hidden[face]
                    total += 1
        row[pose] = round(inside / total, 4)
    poke[outfit[0]] = row
results["R4"] = {
    "claim": "Posing does not push clothes into visible skin (under 2 percent of vertices, 5 mm)",
    "values_fraction_inside_visible_skin": poke,
    "confirmed": bool(all(v < 0.02 for row in poke.values() for v in row.values())),
}

with open(os.path.join(HERE, "results_rig.json"), "w") as fh:
    json.dump(results, fh, indent=2)
print("RESULTS " + json.dumps(results, indent=2))
