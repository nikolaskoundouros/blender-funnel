"""Run 009, step 3: jacket with stitched panel seams, shoulder straps and shearling cuffs,
and the padded yellow life vest over it. Trousers and boots from step 2.

Usage: python runs/009-outfit-detail/upper.py [width height samples]
"""
import json
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from recipes import camera, color, garments, hair, human, materials, render, stage, world  # noqa: E402
from tools.image_stats import stats  # noqa: E402

W, H, SAMPLES = (int(a) for a in sys.argv[1:4]) if len(sys.argv) > 3 else (540, 720, 48)
SLIDERS = dict(gender=1.0, age=0.55, muscle=0.6, weight=0.55, height=0.5, caucasian=1, african=0, asian=0)
SMOOTH = 30
CUT = {"thigh": 0.118, "knee": 0.098, "ankle": 0.088, "folds": 0.007}

scene = stage.new_scene()


def stitched(mat, **kw):
    return materials.add_stitches(mat, **kw)


# --- trousers and boots, as step 2 -----------------------------------------------------
cloth_blue = (0.047, 0.06, 0.093)
twill = lambda n: stitched(materials.fabric(cloth_blue, name=n, thread=0.0011, on="garment", sheen=0.3),
                           rows=2, inset=0.004, row_spacing=0.005, color=(0.16, 0.18, 0.22))
baggy = garments.baggy_ease(outer=0.012, inner=0.008, waist=0.014, ankle=0.012)
lower = [garments.trousers(name="trousers", ease=baggy, smooth_shell=SMOOTH, thickness=0.0025, cut=CUT, material=twill("Trousers")),
         garments.leg_patch("front_pocket", s=(0.20, 0.86), theta=(-38, 48), ease=baggy + 0.004, material=twill("Pocket"),
                            smooth_shell=SMOOTH, cut=CUT, puff=0.012),
         garments.leg_patch("front_flap", s=(0.16, 0.44), theta=(-41, 51), ease=baggy + 0.0165, thickness=0.003,
                            material=twill("Flap"), smooth_shell=SMOOTH, cut=CUT, puff=0.006, snaps=[(0.395, -28), (0.395, 38)]),
         garments.boots(name="boots", top_at=1.5, ease=0.022, thickness=0.004, smooth_shell=SMOOTH, cut=CUT,
                        material=stitched(materials.matte_leather("Boot", (0.035, 0.03, 0.028), mottle=0.25, roughness=0.6),
                                          inset=0.006, color=(0.09, 0.08, 0.07)))]

# --- jacket: panels with stitched seams, shoulder straps, shearling cuffs -------------
JACKET_EASE = 0.03
jacket = garments.top(name="jacket", sleeve=1.95, collar=0.97, hem=-0.12, ease=JACKET_EASE, thickness=0.005,
                      smooth_shell=SMOOTH,
                      material=stitched(materials.matte_leather("Jacket", (0.14, 0.10, 0.09), on="garment"),
                                        rows=2, inset=0.005, row_spacing=0.005, color=(0.21, 0.16, 0.14), depth=0.4))
jacket["panels"] = {"open_above": 0.9}            # seams at sleeves and centre front become stitched edges
strap = garments.leg_patch("shoulder_strap", limb="arm", s=(-0.02, 0.40), theta=(72, 108), ease=JACKET_EASE + 0.005,
                           thickness=0.003, corner=0.006, smooth_shell=SMOOTH,
                           material=stitched(materials.matte_leather("Strap leather", (0.14, 0.08, 0.068), on="garment"),
                                             inset=0.004, color=(0.22, 0.15, 0.13), depth=0.4))
cuffs = garments.band(name="cuffs", limb="arm", start=1.70, end=1.97, ease=JACKET_EASE + 0.016, thickness=0.02,
                      smooth_shell=SMOOTH, material=materials.plain("Shearling", (0.62, 0.55, 0.42), 0.95))
collar = garments.collar(low=0.88, high=1.07, ease=0.06, thickness=0.035)
shirt = garments.top(name="shirt", sleeve=0.4, collar=0.99, hem=0.08, ease=0.004, smooth_shell=SMOOTH,
                     material=materials.fabric((0.62, 0.58, 0.48), on="garment"))

# --- life vest: padded yellow canvas with vertical channels ---------------------------
vest_mat = materials.add_channels(stitched(materials.fabric((0.55, 0.33, 0.065), name="Vest canvas", thread=0.0013,
                                                            on="garment", sheen=0.2),
                                           rows=1, inset=0.006, color=(0.75, 0.6, 0.35), depth=0.5),
                                  width=0.075, depth=0.012)
vest = garments.vest(low=0.06, ease=JACKET_EASE + 0.016, thickness=0.028, smooth_shell=SMOOTH, material=vest_mat)

pilot = human.build_human(scene, name="Pilot", skin="middleage_caucasian_male", hair="short02",
                          outfit=tuple(lower) + (shirt, jacket, strap, cuffs, vest, collar), pose="relaxed", **SLIDERS)
vest_obj = next(o for o in pilot.children if o.name.endswith("_vest"))
vest_obj.modifiers["Subdivision"].render_levels = 3      # resolution for the channel displacement

# shearling strands on collar and cuffs
wool = materials.hair_fibre("Wool", (0.62, 0.55, 0.42), roughness=0.95)
for part_name, count in (("_collar", 120000), ("_cuffs", 50000)):
    obj = next(o for o in pilot.children if o.name.endswith(part_name))
    v, f = hair.evaluated_mesh(obj)
    roots, normals = hair.sample_surface(v, f, count, seed=len(part_name))
    hair.grow(scene, "Fur" + part_name, roots, normals, length=0.007, radius=0.00045, material=wool,
              comb=(0.0, 0.0, -0.05), curl=0.45, steps=4, seed=2, length_jitter=0.25)

world.sky_world(scene, sun_elevation_deg=48.0, sun_rotation_deg=200.0, strength=0.035)
bpy.ops.mesh.primitive_plane_add(size=400)
bpy.context.object.data.materials.append(materials.plain("Tarmac", (0.11, 0.12, 0.13), 0.85))
aim = stage.empty_at(scene, "Aim", (0.02, 0.0, 1.22))
camera.camera_at(scene, (0.95, -2.2, 1.35), aim, lens=70.0)
color.set_view(scene, "AgX", look="Medium High Contrast")
render.cycles_cpu(scene, width=W, height=H, samples=SAMPLES)
out = render.render_to(scene, os.path.join(HERE, "upper.png"))
print("STATS " + json.dumps({"image": stats(out)}))
