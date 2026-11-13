"""Run 006: the pilot again, with a jacket draped by cloth simulation.

Usage: python runs/006-draped-jacket/build.py [width height samples]
"""
import json
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from recipes import (accessories, camera, cloth, color, garments, hair, human, lighting,  # noqa: E402
                     materials, render, stage, world)

W, H, SAMPLES = (int(a) for a in sys.argv[1:4]) if len(sys.argv) > 3 else (864, 1080, 160)
SLIDERS = dict(gender=1.0, age=0.55, muscle=0.6, weight=0.55, height=0.5,
               caucasian=1, african=0, asian=0)

scene = stage.new_scene()
leather = materials.leather("Jacket leather", (0.032, 0.017, 0.010), on="garment", wear=0.3, grain=0.0014)
pilot = human.build_human(
    scene, name="Pilot", skin="middleage_caucasian_male", hair=None, eyes="brown",
    outfit=(garments.top(name="jacket", sleeve=1.95, collar=0.93, hem=-0.16, ease=0.035,
                         thickness=0.005, material=leather, soften=6),
            garments.collar(low=0.90, high=1.07, ease=0.05, thickness=0.035),
            garments.helmet(material=materials.leather("Helmet leather", (0.022, 0.015, 0.011), wear=0.3, grain=0.0014)),
            garments.trousers(material=materials.fabric((0.30, 0.27, 0.20), on="garment"))),
    pose="stick", collider=True, **SLIDERS)
body = next(c for c in pilot.children if c.name == "Pilot")
jacket = next(c for c in pilot.children if c.name.endswith("_jacket"))
materials.soften_skin(body.data.materials[0])

# Drape: pin the yoke (top of the shoulders and neckline), free everything below.
binding = human.BINDINGS[jacket.name]
h = garments.coordinate(binding, "h")
on_arm = np.isin(garments.part(binding), ("arm", "hand"))
pin = np.where(on_arm, 0.0, np.clip((h - 0.86) / 0.06, 0.0, 1.0))
# Step 1 collided with the visible body, whose skin under the jacket is removed: the
# sleeves fell onto bare arms. The cloth now rests on a complete invisible copy.
solid_body = next(c for c in pilot.children if c.name.endswith("_collider"))
cloth.make_collider(solid_body)
cloth.add_cloth(jacket, pin_weights=pin, fabric="leather", spare=0.06)
before_v, before_f = hair.evaluated_mesh(jacket)
started = time.time()
frames = cloth.simulate(scene, 45)
sim_seconds = round(time.time() - started)
after_v, after_f = hair.evaluated_mesh(jacket)

# Measurements of the drape.
bv, bf = hair.evaluated_mesh(solid_body)
tree = BVHTree.FromPolygons([Vector(v) for v in bv], bf)
inside = sum(1 for p in after_v[::3]
             if (Vector(p) - tree.find_nearest(Vector(p))[0]).dot(tree.find_nearest(Vector(p))[1]) < -0.003)
drape = {"frames": frames, "simulation_seconds": sim_seconds,
         "fold_measure_degrees_before": round(cloth.fold_measure(before_v, before_f), 2),
         "fold_measure_degrees_after": round(cloth.fold_measure(after_v, after_f), 2),
         "largest_vertex_move_m": round(float(np.linalg.norm(after_v - before_v, axis=1).max()), 3),
         "fraction_inside_skin_3mm": round(inside / len(after_v[::3]), 4)}
print("DRAPE " + json.dumps(drape))

base_verts = human.morphed_base(**SLIDERS)
lm = accessories.face_landmarks(base_verts)
accessories.goggles(scene, base_verts, parent=pilot, clearance=0.008)
collar_obj = next(c for c in pilot.children if c.name.endswith("_collar"))
cv, cf = hair.evaluated_mesh(collar_obj)
roots, normals = hair.sample_surface(cv, cf, 60000, seed=1)
hair.grow(scene, "Collar fur", roots, normals, length=0.022, radius=0.00035,
          material=materials.hair_fibre("Wool", (0.72, 0.62, 0.44), roughness=0.8),
          comb=(0.0, 0.0, -0.15), curl=0.75, steps=6, seed=2)
vb = human.to_blender(base_verts)
nose, lip = lm["nose"], lm["lip"]
lip_faces = [f for f in human.base_mesh()[2] if all(v < human.BODY_VERTS for v in f)
             and abs(vb[list(f)].mean(axis=0)[0]) < 0.034
             and lip[2] - 0.004 < vb[list(f)].mean(axis=0)[2] < nose[2] - 0.004
             and vb[list(f)].mean(axis=0)[1] < nose[1] + 0.03]
mr, mn = hair.sample_surface(vb, lip_faces, 2600, seed=3)
comb = np.concatenate([np.sign(mr[:, 0])[:, None] * 1.1, np.full((len(mr), 1), -0.15),
                       np.full((len(mr), 1), -0.45)], axis=1)
hair.grow(scene, "Moustache", mr, mn, length=0.012 + 0.016 * np.abs(mr[:, 0]) / 0.034,
          radius=0.00011, material=materials.hair_fibre("Moustache", (0.045, 0.03, 0.02), roughness=0.35),
          comb=comb, curl=0.12, steps=6, seed=4)

# Wider than run 005 so the jacket's folds are in frame.
focus = stage.empty_at(scene, "Focus", (0.0, lm["front_y"] + 0.02, lm["eye_z"]))
aim = stage.empty_at(scene, "Aim", (0.0, -0.10, lm["eye_z"] - 0.22))
cam_at = (0.62, -1.50, lm["eye_z"] - 0.05)
stage.backdrop(scene, cam_at, (0.0, 0.0, 0.0), color=(0.30, 0.33, 0.36))
lighting.three_point(scene, aim, cam_at, key_power=110.0, fill_ratio=0.2, rim_ratio=2.2,
                     distance=2.6, key_size=1.1)
world.solid_world(scene, (0.6, 0.72, 0.9), 0.08)
cam = camera.camera_at(scene, cam_at, aim, lens=70.0)
camera.depth_of_field(cam, focus, fstop=2.8)
color.set_view(scene, "AgX", look="Medium High Contrast")
render.cycles_cpu(scene, width=W, height=H, samples=SAMPLES)
scene.cycles_curves.shape = "THICK" if W >= 800 else "RIBBONS"
started = time.time()
render.render_to(scene, os.path.join(HERE, "pilot_draped.png" if W >= 800 else "pilot_draped_test.png"))
report = {"blender": bpy.app.version_string, "size": [W, H], "samples": SAMPLES,
          "render_seconds": round(time.time() - started), "drape": drape}
with open(os.path.join(HERE, "stats.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("STATS " + json.dumps(report))
