"""Run 013 route B (generated tee shell draped over trousers) with one ingredient changed.

The drape block is copied from runs/013-boy-outfit/outfit.py (DRAPE=1, TEE=shell) so each
variant differs from the failing run in one setting only. Records the hem height (1st
percentile of z of the evaluated tee) every 2 frames, and at the end, for the hem band,
how far each part moved and how close it is to the body collider.

Usage: python experiments/hem_real.py variant [variant ...]
Appends to experiments/results_hem_real.json.
"""
import json
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from recipes import camera, cloth, garments, human, lighting, looks, render, stage, world  # noqa: E402
from recipes import rig as _rig  # noqa: E402

VARIANTS = {
    "base": {},
    "rest_pose": {"pose": "rest"},            # no pose at all: nothing moves
    "posed_at_once": {"pose": "at_once"},
    "no_body_collider": {"body": False},
    "no_pants_collider": {"pants": False},
    "no_colliders": {"body": False, "pants": False},
    "no_culling": {"culling": False},
    "no_pin": {"pin": False},
    "no_subsurf": {"resolution": 0},
    "no_gravity": {"gravity": False},
    "no_self": {"self_collision": False},
    "self_1.5mm": {"self_distance": 0.0015},
    "self_8mm": {"self_distance": 0.008},
    "self_1mm": {"self_distance": 0.001},
    "capped": {"cap": True},            # recipes.cloth default since this pass
}


def evaluated(obj):
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    ev.to_mesh_clear()
    m = np.array(ev.matrix_world)
    return co.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]


def cloth_points(obj):
    """Cloth vertices only (modifiers after the Cloth modifier switched off)."""
    after = False
    saved = []
    for m in obj.modifiers:
        if after:
            saved.append((m, m.show_viewport)); m.show_viewport = False
        after = after or m.type == "CLOTH"
    bpy.context.view_layer.update()
    co = evaluated(obj)
    for m, s in saved:
        m.show_viewport = s
    return co


def run(name, total_extra=20):
    opt = VARIANTS[name]
    S = looks.CURLY_BOY_SLIDERS
    scene = stage.new_scene()
    scene.use_gravity = opt.get("gravity", True)
    base_verts = human.morphed_base(**S)
    CUT = {"thigh": 0.088, "knee": 0.074, "ankle": 0.062, "folds": 0.005}
    baggy = garments.baggy_ease(outer=0.012, inner=0.008, waist=0.010, ankle=0.006)
    pants = garments.trousers(name="pants", length=1.93, waist=0.0, ease=baggy, smooth_shell=30,
                              thickness=0.003, cut=CUT)
    tee = garments.top(name="tee", sleeve=0.85, collar=0.965, hem=-0.03, ease=garments.tee_ease(hem=0.06),
                       thickness=0.003, smooth_shell=30)
    ARM = 0.2
    pose = looks.head_pose(*looks.CURLY_BOY_HEAD) + _rig._arm("L", (ARM, 0.0, -1.0), (ARM * 0.5, -0.2, -1.0)) \
        + _rig._arm("R", (ARM, 0.0, -1.0), (ARM * 0.5, -0.2, -1.0))
    if opt.get("pose") == "rest":
        pose = []
    boy = human.build_human(scene, name="Boy", skin="young_caucasian_male", hair=None, eyes="green",
                            outfit=(pants, tee), pose=pose, collider=True, **S)
    kids = {o.name: o for o in boy.children_recursive}
    tee_obj, pants_obj, col_obj = kids["Boy_tee"], kids["Boy_pants"], kids["Boy_collider"]
    binding = human.BINDINGS[tee_obj.name]
    h = garments.coordinate(binding, "h")
    on_arm = np.isin(garments.part(binding), ("arm", "hand"))
    arm = garments.coordinate(binding, "arm")
    pin = np.where(on_arm, np.clip((0.20 - arm) / 0.14, 0.0, 1.0), np.clip((h - 0.80) / 0.06, 0.0, 1.0))
    # Same push-outs as run 013: clear of the trousers by 1 cm, of the body by 1.5 cm.
    pv = [Vector(v.co) for v in pants_obj.data.vertices]
    tree = BVHTree.FromPolygons(pv, [tuple(f.vertices) for f in pants_obj.data.polygons])
    for v in tee_obj.data.vertices:
        q, n, _, _ = tree.find_nearest(v.co)
        if q is None:
            continue
        outward = Vector((n.x, n.y, 0.0)).normalized() if abs(n.z) < 0.95 else n
        if outward.dot(Vector((v.co.x, v.co.y, 0.0))) < 0:
            outward = -outward
        depth = (v.co - q).dot(outward)
        if depth < 0.010:
            v.co = v.co + outward * (0.010 - depth)
    cv = [Vector(v.co) for v in col_obj.data.vertices]
    ctree = BVHTree.FromPolygons(cv, [tuple(f.vertices) for f in col_obj.data.polygons])
    for v in tee_obj.data.vertices:
        q, n, _, dist = ctree.find_nearest(v.co)
        side = 1.0 if (v.co - q).dot(n) >= 0 else -1.0
        if side * dist < 0.015:
            v.co = q + n * 0.015
    tee_obj.data.update()
    if opt.get("body", True):
        cloth.make_collider(col_obj)
        col_obj.collision.use_culling = opt.get("culling", True)
    if opt.get("pants", True):
        cloth.make_collider(pants_obj, thickness=0.004)
        pants_obj.collision.use_culling = opt.get("culling", True)
    if opt.get("pose") in ("rest", "at_once"):
        pose_frames = 0
    else:
        pose_frames = _rig.animate_into_pose(boy, frame_end=20)
    cloth.add_cloth(tee_obj, pin_weights=pin if opt.get("pin", True) else None, fabric="jersey", spare=0.02,
                    sewing_force=40.0, resolution=opt.get("resolution", 1),
                    self_collision=opt.get("self_collision", True),
                    self_distance=opt.get("self_distance", 0.004),
                    cap_self_distance=opt.get("cap", False))
    total = pose_frames + total_extra
    scene.frame_start, scene.frame_end = 1, total
    for m in (m for o in scene.objects for m in o.modifiers if m.type == "CLOTH"):
        m.point_cache.frame_start, m.point_cache.frame_end = 1, total
    t0 = time.time()
    hem = []
    for f in range(1, total + 1):
        scene.frame_set(f)
        if f == 1:
            start = cloth_points(tee_obj)
        if f % 2 == 0 or f == 1:
            hem.append((f, round(float(np.percentile(evaluated(tee_obj)[:, 2], 1)), 4)))
    end = cloth_points(tee_obj)
    # Where did the lowest band of the shirt go, and is it touching the body?
    band = start[:, 2] < np.percentile(start[:, 2], 5)
    col_now = evaluated(col_obj)
    body_tree = BVHTree.FromPolygons([Vector(p) for p in col_now], [tuple(f.vertices) for f in col_obj.data.polygons])
    gaps, sides = [], []
    for p in end[band]:
        q, n, _, d = body_tree.find_nearest(Vector(p))
        gaps.append(d)
        sides.append((Vector(p) - q).dot(n) >= 0)
    lift = end[band, 2] - start[band, 2]
    ang = np.degrees(np.arctan2(start[band, 1], start[band, 0]))  # +y is the back in Blender (y back)
    def mean_in(lo, hi):
        m = (ang >= lo) & (ang < hi)
        return round(float(lift[m].mean()) * 100, 2) if m.any() else None
    if os.environ.get("RENDER"):
        # Small check render (CLAUDE.md: 320 px class, tens of samples), front three-quarter view.
        world.solid_world(scene, color=(0.3, 0.3, 0.32), strength=0.4)
        cam_loc = (-0.9, -2.4, 0.95)
        target = bpy.data.objects.new("target", None); scene.collection.objects.link(target)
        target.location = (0.0, 0.0, 0.8)
        camera.camera_at(scene, cam_loc, target, lens=50)
        lighting.three_point(scene, target, cam_loc, key_power=200.0)
        render.cycles_cpu(scene, width=240, height=320, samples=16)
        render.render_to(scene, os.path.join(os.environ["RENDER"], f"{name}.png"))
    return {"hem_z_by_frame": hem, "rise_cm": round(100 * (hem[-1][1] - hem[0][1]), 2),
            "band_lift_cm_median": round(float(np.median(lift)) * 100, 2),
            "band_lift_cm_by_side": {"left(+x)": mean_in(-45, 45), "back(+y)": mean_in(45, 135),
                                      "front(-y)": mean_in(-135, -45),
                                      "right(-x)": mean_in(135, 181) if mean_in(135, 181) is not None else mean_in(-181, -135)},
            "band_gap_to_body_cm_median": round(float(np.median(gaps)) * 100, 2),
            "band_behind_body_faces": int(len(sides) - sum(sides)), "band_points": int(band.sum()),
            "cloth_points": int(len(end)), "pose_frames": pose_frames, "seconds": round(time.time() - t0),
            "blender": bpy.app.version_string}


if __name__ == "__main__":
    out = os.path.join(HERE, "results_hem_real.json")
    for n in sys.argv[1:]:
        r = run(n)
        print(n, json.dumps(r))
        results = json.load(open(out)) if os.path.exists(out) else {}
        results[n] = r
        json.dump(results, open(out, "w"), indent=1)
