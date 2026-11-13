"""Run 009, step 1: flight trousers with cargo pockets, flaps, press-studs and stitching.

Usage: python runs/009-outfit-detail/trousers.py [width height samples]
"""
import json
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from recipes import camera, color, garments, human, materials, render, stage, world  # noqa: E402
from tools.image_stats import stats  # noqa: E402

W, H, SAMPLES = (int(a) for a in sys.argv[1:4]) if len(sys.argv) > 3 else (540, 720, 48)
SLIDERS = dict(gender=1.0, age=0.55, muscle=0.6, weight=0.55, height=0.5, caucasian=1, african=0, asian=0)
CLOTH = (0.047, 0.06, 0.093)       # reference trousers, measured (palette_0.6s.json)
THREAD = (0.16, 0.18, 0.22)
SMOOTH = 30                         # smoothing passes on the garment base: hides muscle shape
# First test: 8 passes and 3.2 cm ease left the crotch and buttocks showing through.


def twill(name):
    mat = materials.fabric(CLOTH, name=name, thread=0.0011, on="garment", sheen=0.3)
    return materials.add_stitches(mat, rows=2, inset=0.004, row_spacing=0.005, color=THREAD)


scene = stage.new_scene()            # first: starting a new scene deletes earlier materials
# Step 2: the leg shape now comes from a straight wide tube (CUT) rather than inflating
# the tights, which only made fatter leggings in step 1.
CUT = {"thigh": 0.118, "knee": 0.098, "ankle": 0.088, "folds": 0.007}
baggy = garments.baggy_ease(outer=0.012, inner=0.008, waist=0.014, ankle=0.012)
front_pocket = garments.leg_patch("front_pocket", s=(0.20, 0.86), theta=(-38, 48), ease=baggy + 0.004,
                                  material=twill("Pocket"), smooth_shell=SMOOTH, cut=CUT, puff=0.012)
front_flap = garments.leg_patch("front_flap", s=(0.16, 0.44), theta=(-41, 51), ease=baggy + 0.0165,
                                thickness=0.003, material=twill("Flap"), smooth_shell=SMOOTH, cut=CUT, puff=0.006,
                                snaps=[(0.395, -28), (0.395, 38)])
side_pocket = garments.leg_patch("side_pocket", s=(0.64, 1.06), theta=(58, 122), ease=baggy + 0.004,
                                 material=twill("Side pocket"), smooth_shell=SMOOTH, cut=CUT, puff=0.012)
side_flap = garments.leg_patch("side_flap", s=(0.60, 0.76), theta=(55, 125), ease=baggy + 0.0165,
                               thickness=0.003, material=twill("Side flap"), smooth_shell=SMOOTH, cut=CUT, puff=0.006,
                               snaps=[(0.72, 90)])
trousers = garments.trousers(name="trousers", ease=baggy, smooth_shell=SMOOTH, thickness=0.0025, cut=CUT,
                             material=twill("Trousers"))
# Tucked in: on the same smoothed base as the trousers, with less ease, so it stays under
# them at the waist (step 2 showed it poking through).
shirt = garments.top(name="shirt", sleeve=0.4, collar=0.99, hem=0.08, ease=0.004, smooth_shell=SMOOTH,
                     material=materials.fabric((0.62, 0.58, 0.48), on="garment"))
boot_leather = materials.matte_leather("Boot", (0.035, 0.03, 0.028), mottle=0.25, roughness=0.6)
boots = garments.boots(name="boots", top_at=1.5, ease=0.022, thickness=0.004, smooth_shell=SMOOTH,
                       cut=CUT, material=materials.add_stitches(boot_leather, inset=0.006, color=(0.09, 0.08, 0.07)))

started = time.time()
pilot = human.build_human(scene, name="Pilot", skin="middleage_caucasian_male", hair="short02",
                          outfit=(trousers, front_pocket, front_flap, side_pocket, side_flap, shirt, boots),
                          pose="relaxed", **SLIDERS)
build_seconds = round(time.time() - started, 1)

world.sky_world(scene, sun_elevation_deg=48.0, sun_rotation_deg=200.0, strength=0.035)
bpy.ops.mesh.primitive_plane_add(size=400)
bpy.context.object.data.materials.append(materials.plain("Tarmac", (0.11, 0.12, 0.13), 0.85))
aim = stage.empty_at(scene, "Aim", (0.03, 0.0, 0.72))
camera.camera_at(scene, (1.05, -2.3, 0.80), aim, lens=70.0)   # wider: whole leg to the ankle
aim.location = (0.02, 0.0, 0.62)
color.set_view(scene, "AgX", look="Medium High Contrast")
render.cycles_cpu(scene, width=W, height=H, samples=SAMPLES)
out = render.render_to(scene, os.path.join(HERE, "trousers.png"))
report = {"build_seconds": build_seconds, "image": stats(out),
          "objects": sorted(o.name for o in scene.objects if o.name.startswith("Pilot_"))}
print("STATS " + json.dumps(report))
