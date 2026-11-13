"""Run 010: the head: leather flying hood, goggles worn over the eyes, moustache.

Usage: python runs/010-head/head.py [width height samples]
Environment: CLAY=1 for a fast grey shape preview; OUT=path to choose the output file.
"""
import json
import math
import os
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from recipes import (accessories, camera, color, garments, hair, human, materials, render,  # noqa: E402
                     stage, straps, world)
from tools.image_stats import stats  # noqa: E402

W, H, SAMPLES = (int(a) for a in sys.argv[1:4]) if len(sys.argv) > 3 else (540, 540, 64)
CLAY = os.environ.get("CLAY") == "1"
SLIDERS = dict(gender=1.0, age=0.55, muscle=0.6, weight=0.55, height=0.5, caucasian=1, african=0, asian=0)
SMOOTH = 30
wear = materials.add_wear

scene = stage.new_scene()
# Smile with teeth showing and a slight squint, as in the clip (expression units, 0..1).
EXPRESSION = {"mouth-corner-puller": 0.9, "mouth-upward-retraction": 0.35, "mouth-open": 0.12,
              "eye-left-slit": 0.25, "eye-right-slit": 0.25}
if os.environ.get("NEUTRAL") == "1":
    EXPRESSION = None
base_verts = human.morphed_base(expression=EXPRESSION, **SLIDERS)
lm = accessories.face_landmarks(base_verts)
eye_z = lm["eye_z"]

# --- materials (measured: helmet #595a5f, semi-gloss, scuffed lighter) -----------------
helmet_mat = wear(materials.leather("Helmet leather", (0.085, 0.088, 0.098), grain=0.0013, wear=0.55),
                  grime=0.35, grime_color=(0.05, 0.05, 0.055), edge_wear=0.8, scratches=0.5, seams=True,
                  seam_width=0.006, edge_color=(0.30, 0.31, 0.33))
# Subtle seams: thread close to the leather colour (step 1's white stitches were far too bright).
helmet_mat = materials.add_seam_lines(helmet_mat, planes=(-0.026, 0.026), above=eye_z + 0.03,
                                      color=(0.13, 0.135, 0.15),
                                      rings=(((0.075, lm["front_y"] + 0.105, eye_z - 0.025), 0.034),
                                             ((-0.075, lm["front_y"] + 0.105, eye_z - 0.025), 0.034)))
mask_mat = materials.add_stitches(
    wear(materials.leather("Goggle mask", (0.030, 0.031, 0.034), grain=0.0009, wear=0.3),
         grime=0.3, grime_color=(0.06, 0.06, 0.06), edge_wear=0.4, seams=False),
    inset=0.0028, stitch=0.0022, gap=0.0014, width=0.0008, color=(0.09, 0.09, 0.09), depth=0.4)
chrome = materials.metal("Chrome", (0.80, 0.80, 0.82), 0.14)

# Narrower face opening, so the hood edge runs close beside the goggles down to the chin.
helmet = garments.flying_helmet(material=helmet_mat, soften=0, opening=(0.052, 0.083))
helmet["relax"] = 14                       # hide the ears with the face edge held still
# Clay test 1: frames too shallow, read as a visor bar. Taller frames and lenses.
# Frames widened (outer edge 0.069, inner 0.001) so at least 6 mm of mask surrounds each lens.
mask = garments.goggle_mask(material=mask_mat)
whiskers = garments.moustache_base()
collar = garments.lapel_collar(smooth_shell=SMOOTH, neckline=0.98, throat=0.90, roll=0.0, ease=0.088,
                               thickness=0.012, cushion=0.065, cushion_width=0.055, tips=0.66, wings=0.84,
                               soften=20, tip_angle=160, material=materials.shearling(relief=0.6, clump=0.004))
jacket = garments.top(name="jacket", sleeve=1.95, collar=0.97, hem=-0.12, ease=0.03, thickness=0.005,
                      smooth_shell=SMOOTH, material=materials.matte_leather("Jacket", (0.14, 0.10, 0.09), on="garment"))
shirt = garments.top(name="shirt", sleeve=0.4, collar=0.99, hem=0.08, ease=0.004, smooth_shell=SMOOTH,
                     material=materials.fabric((0.62, 0.58, 0.48), on="garment"))

pilot = human.build_human(scene, name="Pilot", skin="middleage_caucasian_male", hair=None, eyes="brown",
                          outfit=(shirt, jacket, collar, helmet, mask, whiskers), pose="relaxed",
                          expression=EXPRESSION, **SLIDERS)
body = next(c for c in pilot.children if c.name == "Pilot")
materials.soften_skin(body.data.materials[0])
part = lambda suffix: next(c for c in pilot.children if c.name.endswith(suffix))
helmet_obj, mask_obj = part("_helmet"), part("_goggle_mask")

# rolled edge round the face opening, chrome rims round the lenses
loops = straps.boundary_loops(helmet_obj)
face_loop = min(loops, key=lambda l: l[:, 1].mean())
straps.ring_tube(scene, "Helmet face roll", face_loop, radius=0.0065, material=helmet_mat, parent=pilot)
accessories.goggle_lenses(scene, base_verts, materials.frosted_glass("Lens"), chrome, parent=pilot,
                          eye_offset=0.032, lift=0.0, size=(0.026, 0.020), standoff=0.020, overlap=1.12)
# (standoff 1.5 cm put the lenses behind the mask, like spectacles inside it)

# goggle strap round the hood at eye level, with a buckle at the side
bvh = straps.surface([helmet_obj])
centre = np.array([0.0, (lm["front_y"] + lm["back_y"]) / 2.0, eye_z + 0.006])
ring = []
for a in np.radians(np.linspace(-118, 118, 60)):          # 0 = back of the head
    d = np.array([math.sin(a), math.cos(a), 0.0])
    ring.append((centre + d * 0.4, -d))
strap_mat = materials.add_stitches(materials.leather("Goggle strap", (0.035, 0.036, 0.04), grain=0.001, wear=0.3),
                                   inset=0.003, color=(0.10, 0.10, 0.11), depth=0.4)
straps.strap(scene, "Goggle strap", bvh, ring, width=0.022, thickness=0.003, material=strap_mat, lift=0.002,
             parent=pilot)
p, n = straps.hit(bvh, centre + np.array([0.4 * math.sin(math.radians(108)), 0.4 * math.cos(math.radians(108)), 0.0]),
                  -np.array([math.sin(math.radians(108)), math.cos(math.radians(108)), 0.0]), lift=0.005)
if p is not None:
    straps.box(scene, "Strap buckle", p, n, (0.0, 0.0, 1.0), (0.016, 0.03, 0.004), material=chrome,
               bevel=0.0015, parent=pilot)

# chin strap under the jaw
chin_bvh = straps.surface([body, helmet_obj])
chin_z = lm["lip"][2] - 0.055
straps.strap(scene, "Chin strap", chin_bvh, [((x, -1.0, chin_z + 0.4 * x * x), (0.0, 1.0, 0.0))
                                              for x in np.linspace(-0.055, 0.055, 14)],
             width=0.013, thickness=0.003, material=strap_mat, lift=0.003, parent=pilot)

# moustache: thick, dark, wider than the mouth, ends drooping a little
if not CLAY:
    vb = human.to_blender(base_verts)
    nose, lip = lm["nose"], lm["lip"]
    # Shape on the lip: a band that narrows toward the ends and curves down at them
    # (quick test 3: a straight band up to the nostrils read as a block).
    def on_lip(c):
        x, z = abs(c[0]), c[2] - lip[2]
        return x < 0.036 and (-0.002 - 9.0 * x * x) < z < (0.011 - 6.0 * x * x) and c[1] < nose[1] + 0.03
    lip_faces = [f for f in human.base_mesh()[2] if all(v < human.BODY_VERTS for v in f)
                 and on_lip(vb[list(f)].mean(axis=0))]
    mr, mn = hair.sample_surface(vb, lip_faces, 22000, seed=3)        # dense: reads as one dark shape
    side = np.sign(mr[:, 0])[:, None]
    # Combed hard sideways and down so it lies on the lip (quick test 1 stood out like a brush).
    comb = np.concatenate([side * 2.2, np.full((len(mr), 1), -0.5), np.full((len(mr), 1), -1.3)], axis=1)
    hair.grow(scene, "Moustache", mr, mn, length=0.006 + 0.007 * np.abs(mr[:, 0]) / 0.034, radius=0.00017,
              material=materials.hair_fibre("Moustache", (0.012, 0.009, 0.007), roughness=0.4, variation=0.2),
              comb=comb, curl=0.05, steps=6, seed=4, length_jitter=0.12)

world.sky_world(scene, sun_elevation_deg=48.0, sun_rotation_deg=200.0, strength=0.035)
focus = stage.empty_at(scene, "Focus", (0.0, lm["front_y"] - 0.01, eye_z))
aim = stage.empty_at(scene, "Aim", (0.0, -0.08, eye_z - 0.035))
cam = camera.camera_at(scene, (-0.16, -0.80, eye_z - 0.01), aim, lens=85.0)
camera.depth_of_field(cam, focus, fstop=4.0)
color.set_view(scene, "AgX", look="Medium High Contrast")
if CLAY:
    bpy.context.view_layer.material_override = materials.plain("Clay", (0.5, 0.5, 0.5), 0.6)
    W, H, SAMPLES = 360, 360, 8
render.cycles_cpu(scene, width=W, height=H, samples=SAMPLES)
started = time.time()
out = render.render_to(scene, os.environ.get("OUT") or os.path.join(HERE, "head.png"))
print("STATS " + json.dumps({"render_seconds": round(time.time() - started), "image": stats(out)}))
