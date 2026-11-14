"""Which side of each collider face does the draped shirt start on? (HANDOFF question 1)

Blender's cloth collision is single sided by default (Collision > use_culling, "Cloth
collision acts with respect to the collider normals"): collision.cc treats cloth behind a
collider face as penetrating and pushes it along that face's normal. experiments/hem_rise.py
showed that a tube around a body with inward normals is dragged into the body and its hem
rises 6 cm; with outward normals the hem drops 1.5 cm.

This builds run 013's route-B scene (body collider, trousers, generated tee shell) at frame 1
without simulating, takes each collider's evaluated mesh (what the Collision modifier sees),
and reports for the shirt vertices within reach of the collider how many sit behind their
nearest face.

Usage: python experiments/collider_sides.py      -> experiments/results_collider_sides.json
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
from recipes import garments, human, looks, stage  # noqa: E402

S = looks.CURLY_BOY_SLIDERS
scene = stage.new_scene()
base_verts = human.morphed_base(**S)
CUT = {"thigh": 0.088, "knee": 0.074, "ankle": 0.062, "folds": 0.005}
baggy = garments.baggy_ease(outer=0.012, inner=0.008, waist=0.010, ankle=0.006)
pants = garments.trousers(name="pants", length=1.93, waist=0.0, ease=baggy, smooth_shell=30, thickness=0.003, cut=CUT)
tee = garments.top(name="tee", sleeve=0.85, collar=0.965, hem=-0.03, ease=garments.tee_ease(hem=0.06),
                   thickness=0.003, smooth_shell=30)
boy = human.build_human(scene, name="Boy", skin="young_caucasian_male", hair=None, eyes="green",
                        outfit=(pants, tee), pose=None, collider=True, **S)
scene.frame_set(1)
dg = bpy.context.evaluated_depsgraph_get()


def evaluated(obj, stop_at=None):
    """World-space evaluated mesh; stop_at: name of the first modifier to switch off."""
    saved = []
    if stop_at:
        hit = False
        for m in obj.modifiers:
            hit = hit or m.name == stop_at
            if hit:
                saved.append((m, m.show_viewport))
                m.show_viewport = False
        bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    mw = ev.matrix_world
    v = [mw @ x.co for x in me.vertices]
    f = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    for m, s in saved:
        m.show_viewport = s
    return v, f


def signed_volume(v, f):
    vol = 0.0
    for poly in f:
        a = v[poly[0]]
        for i in range(1, len(poly) - 1):
            vol += a.dot(v[poly[i]].cross(v[poly[i + 1]])) / 6.0
    return vol


def sides(cloth_v, col_v, col_f, reach):
    tree = BVHTree.FromPolygons(col_v, col_f)
    behind = near = 0
    behind_z = []
    for p in cloth_v:
        q, n, _, d = tree.find_nearest(p)
        if q is None or d > reach:
            continue
        near += 1
        if (p - q).dot(n) < 0:
            behind += 1
            behind_z.append(p.z)
    return {"near": near, "behind": behind, "behind_fraction": round(behind / max(near, 1), 3),
            "behind_z_range": [round(min(behind_z), 3), round(max(behind_z), 3)] if behind_z else None}


kids = {o.name: o for o in boy.children_recursive}
tee_obj, pants_obj, col_obj = kids["Boy_tee"], kids["Boy_pants"], kids["Boy_collider"]
tee_v, _ = evaluated(tee_obj, stop_at="Thickness")       # the cloth sees the shell before thickness
col_v, col_f = evaluated(col_obj)
pants_full = evaluated(pants_obj)                          # Collision is appended last: sees both walls
pants_shell = evaluated(pants_obj, stop_at="Thickness")
reach = 0.03
out = {
    "collider_signed_volume_m3": round(signed_volume(col_v, col_f), 4),
    "collider_modifiers": [m.type for m in col_obj.modifiers],
    "pants_modifiers": [m.type for m in pants_obj.modifiers],
    "tee_modifiers": [m.type for m in tee_obj.modifiers],
    "tee_vs_body_collider": sides(tee_v, col_v, col_f, reach),
    "tee_vs_pants_with_thickness": sides(tee_v, *pants_full, reach),
    "tee_vs_pants_shell_only": sides(tee_v, *pants_shell, reach),
    "pants_signed_volume_with_thickness_m3": round(signed_volume(*pants_full), 5),
    "reach_m": reach,
    "blender": bpy.app.version_string,
}
print(json.dumps(out, indent=1))
json.dump(out, open(os.path.join(HERE, "results_collider_sides.json"), "w"), indent=1)
if os.environ.get("RANGES"):
    for nm, (v, _) in (("tee", (tee_v, None)), ("pants", pants_full), ("collider", (col_v, None))):
        z = np.array([p.z for p in v]); print(nm, len(v), round(z.min(), 3), round(z.max(), 3))
