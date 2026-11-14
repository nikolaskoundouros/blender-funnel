"""P1 (notes/facial-mocap-plan.md): Faceunits shape keys equal the static morphs.

Builds the curly-haired boy, adds all 52 Faceunits shape keys (recipes/face_anim.py), and
compares the evaluated meshes with the boy built with the same expression baked in
(human.morphed_base), object by object: one unit at 1.0, and two units at 0.5 each (claim
F6: proxies mix linearly). Also checks the keys still work under a posed skeleton.

Usage: python experiments/verify_face_anim.py   -> experiments/results_face_anim.json
"""
import json
import os
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from recipes import face_anim, human, looks, rig, stage  # noqa: E402

S = looks.CURLY_BOY_SLIDERS
KW = dict(name="Boy", skin="young_caucasian_male", hair=None, eyes="green", outfit=("shoes05",))


def positions(root):
    dg = bpy.context.evaluated_depsgraph_get()
    out = {}
    for o in [root] + list(root.children_recursive):
        if o.type != "MESH":
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        ev.to_mesh_clear()
        out[o.name] = co.reshape(-1, 3)
    return out


def static(expr, pose=None):
    scene = stage.new_scene()
    root = human.build_human(scene, pose=pose, expression=expr, **KW, **S)
    bpy.context.view_layer.update()
    return positions(root)


cases = {"jawOpen": {"jawOpen": 1.0}, "eyeBlinkLeft": {"eyeBlinkLeft": 1.0},
         "mix_jaw_smile": {"jawOpen": 0.5, "mouthSmileLeft": 0.5}}
results = {"blender": bpy.app.version_string}
refs = {case: static(expr) for case, expr in cases.items()}   # built first: one scene at a time

scene = stage.new_scene()
root = human.build_human(scene, pose=None, **KW, **S)
t0 = time.time()
moved = face_anim.add_faceunit_keys(root, **S)
results["key_build_seconds"] = round(time.time() - t0, 1)
results["objects_keyed"] = sorted(o.name for o in face_anim.keyable_objects(root))
results["objects_per_unit"] = moved
for case, expr in cases.items():
    face_anim.set_units(root, {u: 0.0 for u in face_anim.ARKIT})
    face_anim.set_units(root, expr)
    bpy.context.view_layer.update()
    keyed = positions(root)
    ref = refs[case]
    err = {n: round(float(np.abs(keyed[n] - ref[n]).max()) * 1000, 4) for n in ref if n in keyed}
    results[case] = {"max_error_mm_by_object": err, "max_error_mm": max(err.values())}
    print(case, results[case]["max_error_mm"], err)

# Under a posed skeleton: the jaw still opens (lower lip moves down by about the static amount).
scene = stage.new_scene()
posed = human.build_human(scene, pose="relaxed", **KW, **S)
face_anim.add_faceunit_keys(posed, **S)
bpy.context.view_layer.update()
a = positions(posed)["Boy"]
face_anim.set_units(posed, {"jawOpen": 1.0})
bpy.context.view_layer.update()
b = positions(posed)["Boy"]
results["posed_jawOpen_max_move_cm"] = round(float(np.linalg.norm(b - a, axis=1).max()) * 100, 2)
print("posed jawOpen max move cm", results["posed_jawOpen_max_move_cm"])
json.dump(results, open(os.path.join(HERE, "results_face_anim.json"), "w"), indent=1)
