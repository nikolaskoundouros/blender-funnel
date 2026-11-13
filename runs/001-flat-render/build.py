"""Run 001: the first demo render looked flat. Rebuild it with the lighting recipes.

Renders the same three objects twice:
  before.png  the original setup (sun + bright blue ambient world, flat ground plane)
  after.png   backdrop, three-point area lights, dim world, AgX with a contrast look
and writes stats.json so the comparison is measured, not just eyeballed.

Usage: python runs/001-flat-render/build.py [key_power]
"""
import json
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from recipes import camera, color, lighting, render, stage, world  # noqa: E402
from tools.image_stats import stats  # noqa: E402

KEY_POWER = float(sys.argv[1]) if len(sys.argv) > 1 else 300.0
CAMERA_AT = (6.5, -6.5, 3.6)


def subjects(scene):
    bpy.ops.mesh.primitive_monkey_add(location=(0, 0, 1.0), rotation=(0, 0, math.radians(20)))
    monkey = bpy.context.object
    monkey.name = "Suzanne"
    monkey.data.materials.append(stage.principled("Copper", (0.9, 0.42, 0.2), 0.3, 1.0))
    mod = monkey.modifiers.new("Subdivision", "SUBSURF")
    mod.levels = mod.render_levels = 2
    monkey.data.shade_smooth()

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(-2.2, 0.6, 0.6))
    ball = bpy.context.object
    ball.data.materials.append(stage.principled("Blue plastic", (0.08, 0.25, 0.8), 0.15))
    ball.data.shade_smooth()

    bpy.ops.mesh.primitive_cube_add(size=1.1, location=(2.1, -0.4, 0.55),
                                    rotation=(0, 0, math.radians(30)))
    cube = bpy.context.object
    cube.data.materials.append(stage.principled("Green matte", (0.15, 0.6, 0.3), 0.8))
    return monkey


def before():
    scene = stage.new_scene()
    bpy.ops.mesh.primitive_plane_add(size=30)
    bpy.context.object.data.materials.append(stage.principled("Floor", (0.55, 0.57, 0.6), 0.9))
    monkey = subjects(scene)
    data = bpy.data.lights.new("Sun", "SUN")
    data.energy = 3.0
    data.angle = math.radians(8)
    sun = bpy.data.objects.new("Sun", data)
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    scene.collection.objects.link(sun)
    fill = bpy.data.lights.new("Fill", "AREA")
    fill.energy = 250
    fill.size = 4
    fill_ob = bpy.data.objects.new("Fill", fill)
    fill_ob.location = (-4, -4, 4)
    scene.collection.objects.link(fill_ob)
    world.solid_world(scene, (0.6, 0.72, 0.9), 0.5)
    camera.camera_at(scene, CAMERA_AT, monkey)
    color.set_view(scene, "AgX")
    render.cycles_cpu(scene)
    return render.render_to(scene, os.path.join(HERE, "before.png"))


def after():
    scene = stage.new_scene()
    monkey = subjects(scene)
    stage.backdrop(scene, CAMERA_AT, monkey.location)
    lighting.three_point(scene, monkey, CAMERA_AT, key_power=KEY_POWER)
    world.solid_world(scene, (0.6, 0.72, 0.9), 0.03)  # ambient kept low so the key defines shadows
    # Aim between the objects instead of at the monkey, and widen the lens: the first
    # "after" render cropped the cube at the bottom edge (see review.md).
    aim_point = stage.empty_at(scene, "Aim", (0.5, -0.3, 0.75))
    cam = camera.camera_at(scene, CAMERA_AT, aim_point, lens=42.0)
    camera.depth_of_field(cam, monkey, fstop=2.8)
    color.set_view(scene, "AgX", look="Medium High Contrast")
    render.cycles_cpu(scene)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "after.blend"))
    return render.render_to(scene, os.path.join(HERE, "after.png"))


result = {"blender": bpy.app.version_string, "key_power": KEY_POWER,
          "before": stats(before()), "after": stats(after())}
with open(os.path.join(HERE, "stats.json"), "w") as fh:
    json.dump(result, fh, indent=2)
print("STATS " + json.dumps(result, indent=2))
