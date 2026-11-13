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
from recipes import camera, color, lighting, render, stage, world  # noqa: E402

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


CHECKS = [check_principled, check_backdrop, check_three_point, check_solid_world,
          check_sky_world, check_set_view, check_camera_dof, check_render]

report = {"blender": bpy.app.version_string, "recipes_tested_with": recipes.TESTED_WITH, "checks": {}}
for fn in CHECKS:
    try:
        fn()
        report["checks"][fn.__name__] = "pass"
    except Exception:
        report["checks"][fn.__name__] = "FAIL: " + traceback.format_exc().strip().splitlines()[-1]

with open(os.path.join(HERE, "last_check.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("CHECK " + json.dumps(report, indent=2))
sys.exit(0 if all(v == "pass" for v in report["checks"].values()) else 1)
