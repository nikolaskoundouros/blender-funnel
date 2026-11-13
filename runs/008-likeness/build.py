"""Run 008: a recognisable likeness of the reference pilot, assembled from what works.

Follows playbooks/outfit.md: complete collision body, draped shell jacket (route B),
shell under-layers and helmet (route A), strand shearling and moustache, goggles.
Colours are taken from measurements of the reference frame (palette_0.6s.json).

Usage: python runs/008-likeness/build.py [width height samples] [sky_strength] [sun_rotation_deg]
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
from recipes import (accessories, camera, cloth, color, garments, hair, human,  # noqa: E402
                     materials, render, stage, world)
from tools.image_stats import stats  # noqa: E402

W, H, SAMPLES = (int(a) for a in sys.argv[1:4]) if len(sys.argv) > 3 else (540, 960, 48)
SKY = float(sys.argv[4]) if len(sys.argv) > 4 else 0.035
SUN_ROT = float(sys.argv[5]) if len(sys.argv) > 5 else 200.0
SLIDERS = dict(gender=1.0, age=0.55, muscle=0.6, weight=0.55, height=0.5, caucasian=1, african=0, asian=0)

scene = stage.new_scene()
jacket_spec = garments.top(name="jacket", sleeve=1.95, collar=0.93, hem=-0.16, ease=0.035, thickness=0.005,
                           material=materials.matte_leather("Jacket", (0.14, 0.10, 0.09), on="garment"))
jacket_spec["panels"] = {"open_above": 0.62}
pilot = human.build_human(
    scene, name="Pilot", skin="middleage_caucasian_male", hair=None, eyes="brown",
    outfit=(jacket_spec,
            garments.top(name="shirt", sleeve=0.4, collar=0.99, hem=-0.05, ease=0.006,
                         material=materials.fabric((0.62, 0.58, 0.48), on="garment")),
            garments.collar(low=0.90, high=1.07, ease=0.05, thickness=0.035),
            garments.helmet(cheeks=True, material=materials.matte_leather("Helmet", (0.11, 0.11, 0.125), mottle=0.2, roughness=0.7)),
            garments.trousers(material=materials.fabric((0.047, 0.06, 0.093), on="garment"))),
    pose="stick", collider=True, **SLIDERS)
body = next(c for c in pilot.children if c.name == "Pilot")
jacket = next(c for c in pilot.children if c.name.endswith("_jacket"))
solid_body = next(c for c in pilot.children if c.name.endswith("_collider"))
materials.soften_skin(body.data.materials[0])

binding = human.BINDINGS[jacket.name]
h, arm = garments.coordinate(binding, "h"), garments.coordinate(binding, "arm")
on_arm = np.isin(garments.part(binding), ("arm", "hand"))
pin = np.where(on_arm, np.clip((0.20 - arm) / 0.14, 0.0, 1.0), np.clip((h - 0.86) / 0.06, 0.0, 1.0))
cloth.make_collider(solid_body)
cloth.add_cloth(jacket, pin_weights=pin, fabric="leather", spare=0.06, sewing_force=60.0)
started = time.time()
cloth.simulate(scene, 45)
sim_seconds = round(time.time() - started)

base_verts = human.morphed_base(**SLIDERS)
lm = accessories.face_landmarks(base_verts)
for part in accessories.goggles(scene, base_verts, parent=pilot, clearance=0.010,
                                strap_material=materials.matte_leather("Strap", (0.05, 0.05, 0.055), mottle=0.1, roughness=0.6)):
    part.location = (0.0, 0.010, 0.064)        # pushed up onto the forehead, as in the reference

# Shearling: short, dense, matte, slightly yellow (reference wool measured at #d0c7b8).
collar_obj = next(c for c in pilot.children if c.name.endswith("_collar"))
cv, cf = hair.evaluated_mesh(collar_obj)
roots, normals = hair.sample_surface(cv, cf, 160000, seed=1)
hair.grow(scene, "Shearling", roots, normals, length=0.007, radius=0.00045,
          material=materials.hair_fibre("Wool", (0.70, 0.63, 0.53), roughness=0.95),
          comb=(0.0, 0.0, -0.05), curl=0.45, steps=4, seed=2, length_jitter=0.25)

# Moustache: thin and tidy.
vb = human.to_blender(base_verts)
nose, lip = lm["nose"], lm["lip"]
lip_faces = [f for f in human.base_mesh()[2] if all(v < human.BODY_VERTS for v in f)
             and abs(vb[list(f)].mean(axis=0)[0]) < 0.027
             and lip[2] - 0.002 < vb[list(f)].mean(axis=0)[2] < lip[2] + 0.009
             and vb[list(f)].mean(axis=0)[1] < nose[1] + 0.03]
mr, mn = hair.sample_surface(vb, lip_faces, 1800, seed=3)
comb = np.concatenate([np.sign(mr[:, 0])[:, None] * 1.2, np.full((len(mr), 1), -0.1), np.full((len(mr), 1), -0.25)], axis=1)
hair.grow(scene, "Moustache", mr, mn, length=0.006 + 0.007 * np.abs(mr[:, 0]) / 0.027, radius=0.00010,
          material=materials.hair_fibre("Moustache", (0.02, 0.014, 0.01), roughness=0.4),
          comb=comb, curl=0.06, steps=5, seed=4, length_jitter=0.15)

# Outdoors: sky and sun only, tarmac underfoot. No studio lamps or backdrop.
world.sky_world(scene, sun_elevation_deg=48.0, sun_rotation_deg=SUN_ROT, strength=SKY)
bpy.ops.mesh.primitive_plane_add(size=400)
bpy.context.object.data.materials.append(materials.plain("Tarmac", (0.11, 0.12, 0.13), 0.85))
aim = stage.empty_at(scene, "Aim", (0.0, -0.05, 1.22))
focus = stage.empty_at(scene, "Focus", (0.0, lm["front_y"], lm["eye_z"]))
cam = camera.camera_at(scene, (0.35, -2.55, 1.05), aim, lens=50.0)
camera.depth_of_field(cam, focus, fstop=2.8)
color.set_view(scene, "AgX", look="Medium High Contrast")
render.cycles_cpu(scene, width=W, height=H, samples=SAMPLES)
scene.cycles_curves.shape = "THICK" if W >= 800 else "RIBBONS"
started = time.time()
out = render.render_to(scene, os.path.join(HERE, "likeness.png" if W >= 800 else "likeness_test.png"))
report = {"size": [W, H], "samples": SAMPLES, "sky_strength": SKY, "sun_rotation": SUN_ROT,
          "simulation_seconds": sim_seconds, "render_seconds": round(time.time() - started), "image": stats(out)}
with open(os.path.join(HERE, "stats.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("STATS " + json.dumps(report))
