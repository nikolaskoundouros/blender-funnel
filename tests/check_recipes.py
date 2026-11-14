"""Run every recipe in a fresh scene and report which still work on this Blender.

Tutorials and old scripts go stale as Blender's API changes. Run this after any Blender
upgrade and before trusting the recipe library for a new scene.

Usage: python tests/check_recipes.py      (exit code 1 if any recipe fails)
"""
import json
import os
import sys
import tempfile
import traceback

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import recipes  # noqa: E402
from recipes import camera, cloth, color, face_anim, human, lighting, motion, render, rig, stage, world  # noqa: E402

CAM = (6.0, -6.0, 3.0)


def fresh():
    scene = stage.new_scene()
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.5))
    return scene, bpy.context.object


def check_principled():
    mat = stage.principled("M", (0.2, 0.4, 0.6), 0.3, 1.0)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    assert abs(bsdf.inputs["Metallic"].default_value - 1.0) < 1e-6


def check_backdrop():
    scene, cube = fresh()
    obj = stage.backdrop(scene, CAM, cube.location)
    assert len(obj.data.polygons) == 18 and obj.name in scene.objects


def check_three_point():
    scene, cube = fresh()
    key, fill, rim = lighting.three_point(scene, cube, CAM)
    assert key.data.energy > fill.data.energy and fill.data.size > key.data.size
    assert all(o.constraints[0].target == cube for o in (key, fill, rim))


def check_solid_world():
    scene, _ = fresh()
    w = world.solid_world(scene, (0.1, 0.2, 0.3), 0.5)
    assert scene.world is w


def check_sky_world():
    scene, _ = fresh()
    w = world.sky_world(scene, 35, 120)
    assert any(n.type == "TEX_SKY" for n in w.node_tree.nodes)
    assert len(w.node_tree.links) == 2


def check_set_view():
    scene, _ = fresh()
    vs = color.set_view(scene, "AgX", look="High Contrast", exposure=-1.0)
    assert vs.view_transform == "AgX" and "High Contrast" in vs.look and vs.exposure == -1.0
    try:
        color.set_view(scene, "AgX", look="No Such Look")
    except ValueError:
        pass
    else:
        raise AssertionError("an unknown look should raise")


def check_camera_dof():
    scene, cube = fresh()
    cam = camera.camera_at(scene, CAM, cube, lens=42)
    dof = camera.depth_of_field(cam, cube, 2.0)
    assert scene.camera is cam and dof.use_dof and dof.focus_object is cube


def check_render():
    scene, cube = fresh()
    lighting.three_point(scene, cube, CAM)
    camera.camera_at(scene, CAM, cube)
    render.cycles_cpu(scene, width=64, height=36, samples=4)
    with tempfile.TemporaryDirectory() as tmp:
        path = render.render_to(scene, os.path.join(tmp, "t.png"))
        assert os.path.getsize(path) > 0


def check_human_clothed():
    scene = stage.new_scene()
    body = human.build_human(scene, name="A", outfit=("female_casualsuit01", "shoes01"),
                             hair="long01", gender=0.0)
    assert body.type == "MESH" and len(body.children) == 7
    assert 1.4 < body["funnel_height_m"] < 1.8
    # skin under the outfit is removed
    assert len(body.data.polygons) < 13378


def check_human_posed():
    scene = stage.new_scene()
    root = human.build_human(scene, name="B", outfit=("male_worksuit01", "shoes04"),
                             hair="short02", gender=1.0, pose="wave")
    assert root.type == "ARMATURE" and len(root.data.bones) == 163
    assert all(c.modifiers and c.modifiers[0].type == "ARMATURE" for c in root.children)


def check_human_mixamo_rig():
    scene = stage.new_scene()
    root = human.build_human(scene, name="C", outfit=(), hair=None, pose=[], rig_name="mixamo")
    assert "mixamorig:Hips" in root.data.bones and len(root.data.bones) == 52


def check_motion_retarget():
    clip_path = os.path.join(human.ASSETS, "motion", "cmu", "05_02.bvh")
    scene = stage.new_scene()
    root = human.build_human(scene, name="D", outfit=(), hair=None, pose=[], rig_name="cmu_mb")
    move = motion.retarget(root, motion.read_bvh(clip_path), stop=200)
    frames = motion.apply(root, move)
    assert frames == 39 and move["fps"] == 24
    scene.frame_set(1)
    a = (root.matrix_world @ root.pose.bones["LeftForeArm"].head).copy()
    scene.frame_set(frames)
    b = root.matrix_world @ root.pose.bones["LeftForeArm"].head
    assert (a - b).length > 0.01  # the arm actually moves


def check_cloth_self_distance_cap():
    """add_cloth keeps the self-collision distance at most 0.3 x the cloth's short edges
    (notes/cloth.md claim 9). One subdivision level halves a flat grid's edges: a coarse grid
    keeps the requested 4 mm; 60 cuts (8.3 mm edges) is cut to 0.3 x 8.3 mm; 200 cuts (2.5 mm)
    is below Blender's 1 mm minimum, so self collision is switched off."""
    import bmesh
    for cuts in (25, 60, 200):
        scene, _ = fresh()
        me = bpy.data.meshes.new("g")
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=cuts, y_segments=cuts, size=0.5)
        bm.to_mesh(me)
        bm.free()
        obj = bpy.data.objects.new("g", me)
        scene.collection.objects.link(obj)
        edge = me.edges[0]
        half = (me.vertices[edge.vertices[0]].co - me.vertices[edge.vertices[1]].co).length / 2
        expect = min(0.004, 0.3 * half)
        mod = cloth.add_cloth(obj, resolution=1, self_distance=0.004)
        got = mod.collision_settings.self_distance_min
        if expect >= 0.001:
            assert abs(got - expect) < 0.05 * expect, (cuts, got, expect)
            assert mod.collision_settings.use_self_collision
        else:
            assert not mod.collision_settings.use_self_collision, cuts


def check_face_keys():
    """A Faceunits shape key at 1.0 gives the same body and teeth as the static morph
    (notes/facial-mocap-plan.md P1; needs the faceunits01 asset pack)."""
    import numpy as np
    def coords(obj):
        dg = bpy.context.evaluated_depsgraph_get()
        me = obj.evaluated_get(dg).to_mesh()
        co = np.array([v.co for v in me.vertices])
        obj.evaluated_get(dg).to_mesh_clear()
        return co
    scene, _ = fresh()
    root = human.build_human(scene, name="F", outfit=(), expression={"jawOpen": 1.0})
    ref = {o.name: coords(o) for o in [root] + list(root.children_recursive) if o.type == "MESH"}
    scene, _ = fresh()
    root = human.build_human(scene, name="F", outfit=())
    moved = face_anim.add_faceunit_keys(root, units=["jawOpen"])
    face_anim.set_units(root, {"jawOpen": 1.0})
    bpy.context.view_layer.update()
    assert moved["jawOpen"] >= 2, moved            # body and teeth at least
    for o in [root] + list(root.children_recursive):
        if o.type == "MESH":
            assert np.abs(coords(o) - ref[o.name]).max() < 1e-6, o.name


HUMAN_CHECKS = [check_human_clothed, check_human_posed, check_human_mixamo_rig, check_motion_retarget, check_face_keys]
HAVE_ASSETS = os.path.exists(os.path.join(human.DATA, "3dobjs", "base.obj"))

CHECKS = [check_principled, check_backdrop, check_three_point, check_solid_world,
          check_sky_world, check_set_view, check_camera_dof, check_render, check_cloth_self_distance_cap]

report = {"blender": bpy.app.version_string, "recipes_tested_with": recipes.TESTED_WITH, "checks": {}}
for fn in HUMAN_CHECKS:
    if not HAVE_ASSETS:
        report["checks"][fn.__name__] = "skipped: run tools/fetch_assets.sh first"
for fn in CHECKS + (HUMAN_CHECKS if HAVE_ASSETS else []):
    try:
        fn()
        report["checks"][fn.__name__] = "pass"
    except Exception:
        report["checks"][fn.__name__] = "FAIL: " + traceback.format_exc().strip().splitlines()[-1]

with open(os.path.join(HERE, "last_check.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("CHECK " + json.dumps(report, indent=2))
sys.exit(1 if any(v.startswith("FAIL") for v in report["checks"].values()) else 0)
