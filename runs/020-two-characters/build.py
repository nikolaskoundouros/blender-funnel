"""Run 020: two characters in one scene, the test of the whole funnel (owner, 14 Nov 2026).

Reference: "My Mom Cracked The Dinosaur" (owner-supplied clip, kept out of git): the boy and
his mom. Step 1 (this file): both characters from recipes, facing each other in a plain
room, one two-shot camera. The reference's shots and zooms come in a later step, from the
clip; the mom is a placeholder until the clip is available (recipes/characters.mom).

Usage: python runs/020-two-characters/build.py [width height samples]
Environment: HAIR (hair children, default 40000), SHOTS (comma list, default "two").
"""
import json
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from recipes import camera, characters, color, lighting, materials, render, stage, world  # noqa: E402

W, H, SAMPLES = (int(a) for a in sys.argv[1:4]) if len(sys.argv) > 3 else (320, 180, 24)
env = lambda k, d: type(d)(os.environ.get(k, d))
t0 = time.time()
scene = stage.new_scene()

# Facing each other across about 1.2 m, both turned a little toward the camera (at -Y).
boy, _ = characters.curly_boy(scene, location=(-0.55, 0.0, 0.0), facing_deg=60.0,
                              hair_children=env("HAIR", 40000))
mom, _ = characters.mom(scene, location=(0.6, 0.05, 0.0), facing_deg=-55.0)
build_s = round(time.time() - t0, 1)

# Plain room: floor and back wall, warm soft light.
bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
bpy.context.object.data.materials.append(materials.plain("Floor", (0.30, 0.22, 0.16), 0.6))
bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 2.5, 3), rotation=(1.5708, 0, 0))
bpy.context.object.data.materials.append(materials.plain("Wall", (0.55, 0.50, 0.42), 0.9))
world.sky_world(scene, sun_elevation_deg=40.0, sun_rotation_deg=220.0, strength=0.006)
mid = stage.empty_at(scene, "Mid", (0.0, 0.0, 1.1))
lighting.three_point(scene, mid, (0.0, -4.0, 1.5), key_power=300.0, fill_ratio=0.35, rim_ratio=1.0,
                     distance=4.0, key_size=2.0)
scene.cycles_curves.shape = "THICK"
color.set_view(scene, "AgX", look="Medium High Contrast")
render.cycles_cpu(scene, width=W, height=H, samples=SAMPLES)

SHOTS = {"two": ((0.0, -4.2, 1.25), (0.0, 0.0, 1.0), 35.0)}
for label in env("SHOTS", "two").split(","):
    for o in [o for o in scene.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(o, do_unlink=True)
    eye, at, lens = SHOTS[label]
    camera.camera_at(scene, eye, stage.empty_at(scene, f"Aim_{label}", at), lens=lens)
    render.render_to(scene, os.path.join(HERE, f"shot_{label}.png"))
print("STATS " + json.dumps({"build_seconds": build_s, "total_seconds": round(time.time() - t0, 1)}))
