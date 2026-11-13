"""Run 002: three clothed human characters with different bodies, skins and outfits.

Everything comes from recipes/: human.py for the characters, the lighting and camera
recipes from run 001 for the shot.

Usage: python runs/002-characters/build.py [width height samples]
"""
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from recipes import camera, color, human, lighting, render, stage, world  # noqa: E402
from tools.image_stats import stats  # noqa: E402

W, H, SAMPLES = (int(a) for a in sys.argv[1:4]) if len(sys.argv) > 3 else (960, 540, 96)
CAMERA_AT = (0.0, -7.2, 1.25)

CAST = [
    dict(name="Ana", location=(-1.25, 0, 0), gender=0.0, age=0.45, weight=0.45, height=0.5,
         caucasian=1, african=0, asian=0, skin="young_caucasian_female",
         outfit=("female_casualsuit01", "shoes01"), hair="long01", eyes="blue",
         pose="wave", facing_deg=-12),
    dict(name="Ben", location=(0.0, 0, 0), gender=1.0, age=0.6, weight=0.75, muscle=0.6, height=0.6,
         caucasian=0, african=1, asian=0, skin="middleage_african_male",
         outfit=("male_worksuit01", "shoes04"), hair="short02", eyes="brown",
         pose="relaxed"),
    dict(name="Chen", location=(1.25, 0, 0), gender=0.0, age=0.8, weight=0.55, height=0.4,
         caucasian=0, african=0, asian=1, skin="old_asian_female",
         outfit=("female_elegantsuit01", "shoes02"), hair="bob01", eyes="brown",
         pose="akimbo", facing_deg=15),
]

scene = stage.new_scene()
people = [human.build_human(scene, **spec) for spec in CAST]

aim = stage.empty_at(scene, "Aim", (0.0, 0.0, 0.95))
stage.backdrop(scene, CAMERA_AT, aim.location)
lighting.three_point(scene, aim, CAMERA_AT, key_power=450.0, distance=6.5, key_size=3.0)
world.solid_world(scene, (0.6, 0.72, 0.9), 0.05)
cam = camera.camera_at(scene, CAMERA_AT, aim, lens=50.0)
color.set_view(scene, "AgX", look="Medium High Contrast")
render.cycles_cpu(scene, width=W, height=H, samples=SAMPLES)

out = render.render_to(scene, os.path.join(HERE, "characters.png"))
report = {
    "blender": bpy.app.version_string,
    "image": stats(out),
    "people": {p.name: {"height_m": round(p["funnel_height_m"], 3),
                        "parts": len(p.children)} for p in people},
}
with open(os.path.join(HERE, "stats.json"), "w") as fh:
    json.dump(report, fh, indent=2)
if W >= 900:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "characters.blend"))
print("STATS " + json.dumps(report, indent=2))
