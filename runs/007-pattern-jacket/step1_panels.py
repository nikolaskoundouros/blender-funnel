"""Run 007, step 1: stand the shirt pattern's panels round our character, unsewn."""
import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from recipes import camera, color, human, lighting, materials, patterns, render, stage, world  # noqa: E402

SLIDERS = dict(gender=1.0, age=0.55, muscle=0.6, weight=0.55, height=0.5, caucasian=1, african=0, asian=0)
scene = stage.new_scene()
person = human.build_human(scene, name="Pilot", skin="middleage_caucasian_male", hair="short02", **SLIDERS)
PATTERN = sys.argv[1] if len(sys.argv) > 1 else "shirt_mean_specification.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "step1_panels.png"
pattern, props = patterns.load(os.path.join(human.ASSETS, "patterns", PATTERN))
scale = person["funnel_height_m"] / 1.7199          # their reference body is 171.99 cm tall
obj, info = patterns.build(scene, pattern, name="Jacket panels", to_metres=0.01 * scale,
                           material=materials.plain("Panel", (0.75, 0.45, 0.12), 0.8))
print("INFO " + json.dumps({k: v for k, v in info.items() if k != "owner"} | {"scale": round(scale, 4), "units_in_meter": props.get("units_in_meter")}))
aim = stage.empty_at(scene, "Aim", (0.0, 0.0, 1.2))
cam_at = (1.6, -3.0, 1.5)
stage.backdrop(scene, cam_at, (0, 0, 0))
lighting.three_point(scene, aim, cam_at, key_power=250.0, distance=4.5, key_size=2.5)
world.solid_world(scene, (0.6, 0.72, 0.9), 0.1)
camera.camera_at(scene, cam_at, aim, lens=50.0)
color.set_view(scene, "AgX", look="Medium High Contrast")
render.cycles_cpu(scene, width=540, height=540, samples=40)
render.render_to(scene, os.path.join(HERE, OUT))
