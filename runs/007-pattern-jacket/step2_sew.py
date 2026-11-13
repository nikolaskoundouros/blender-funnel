"""Run 007, step 2: sew the panels together on the standing character and let them drape.

Usage: python runs/007-pattern-jacket/step2_sew.py [fabric]
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
from recipes import camera, cloth, color, hair, human, lighting, materials, patterns, render, stage, world  # noqa: E402

FABRIC = sys.argv[1] if len(sys.argv) > 1 else "cotton"
SLIDERS = dict(gender=1.0, age=0.55, muscle=0.6, weight=0.55, height=0.5, caucasian=1, african=0, asian=0)
scene = stage.new_scene()
person = human.build_human(scene, name="Pilot", skin="middleage_caucasian_male", hair="short02",
                           pose=[], collider=True, **SLIDERS)
solid_body = next(c for c in person.children if c.name.endswith("_collider"))
cloth.make_collider(solid_body)

pattern, _ = patterns.load(os.path.join(human.ASSETS, "patterns", "shirt_mean_specification.json"))
scale = person["funnel_height_m"] / 1.7199
# Second attempt (gentle sewing) still ended at the hips. Cause: the pattern's shoulder
# seam sits at 1.43 m, below the top of this character's shoulders (the pattern was drafted
# for a slimmer, more sloped body). The seam could only close by cutting through the
# shoulder. Panels now start 7 cm higher, so seams close above the shoulders and settle.
LIFT = float(sys.argv[2]) if len(sys.argv) > 2 else 0.07
jacket, info = patterns.build(scene, pattern, name="Jacket", to_metres=0.01 * scale,
                              offset=(0.0, 0.0, LIFT),
                              material=materials.plain("Panel", (0.75, 0.45, 0.12), 0.8))
# First attempt used a sewing force of 30: the seams closed in a few frames, but the panels
# hit the body so fast that they passed through the shoulders and the whole garment slid
# to the hips. Sewing is now gentle and slow, with more solver steps and a thicker
# collision margin, so the cloth meets the body before the seams finish closing.
solid_body.collision.thickness_outer = 0.012
mod = cloth.add_cloth(jacket, fabric=FABRIC, spare=0.0, resolution=0, sewing_force=2.5,
                      self_collision=False, quality=18)
mod.collision_settings.collision_quality = 8
# Sew first, then let it hang: gravity is faded in so the panels do not fall off the body
# before the seams have closed.
weights = mod.settings.effector_weights
weights.gravity = 0.0
weights.keyframe_insert("gravity", frame=1)
weights.keyframe_insert("gravity", frame=80)
weights.gravity = 1.0
weights.keyframe_insert("gravity", frame=110)

loose = [e.vertices[:] for e in jacket.data.edges if e.is_loose]
gap = lambda v: float(np.mean([np.linalg.norm(v[a] - v[b]) for a, b in loose]))
before, _ = hair.evaluated_mesh(jacket)
started = time.time()
cloth.simulate(scene, 140)
after, faces = hair.evaluated_mesh(jacket)
bv, bf = hair.evaluated_mesh(solid_body)
tree = BVHTree.FromPolygons([Vector(p) for p in bv], bf)
inside = sum(1 for p in after if (Vector(p) - tree.find_nearest(Vector(p))[0]).dot(tree.find_nearest(Vector(p))[1]) < -0.003)
report = {"fabric": FABRIC, "simulation_seconds": round(time.time() - started),
          "seam_gap_before_m": round(gap(before), 3), "seam_gap_after_m": round(gap(after), 4),
          "largest_seam_gap_after_m": round(float(max(np.linalg.norm(after[a] - after[b]) for a, b in loose)), 4),
          "fraction_inside_skin_3mm": round(inside / len(after), 4),
          "fold_measure_degrees": round(cloth.fold_measure(after, faces), 2),
          "hem_height_m": round(float(after[:, 2].min()), 3), **{k: v for k, v in info.items() if k != "owner"}}
print("SEW " + json.dumps(report))
with open(os.path.join(HERE, f"step2_{FABRIC}.json"), "w") as fh:
    json.dump(report, fh, indent=2)

thick = jacket.modifiers.new("Thickness", "SOLIDIFY")
thick.thickness, thick.offset = 0.003, 1.0
aim = stage.empty_at(scene, "Aim", (0.0, 0.0, 1.2))
cam_at = (1.6, -3.0, 1.5)
stage.backdrop(scene, cam_at, (0, 0, 0))
lighting.three_point(scene, aim, cam_at, key_power=250.0, distance=4.5, key_size=2.5)
world.solid_world(scene, (0.6, 0.72, 0.9), 0.1)
camera.camera_at(scene, cam_at, aim, lens=50.0)
color.set_view(scene, "AgX", look="Medium High Contrast")
render.cycles_cpu(scene, width=540, height=540, samples=40)
render.render_to(scene, os.path.join(HERE, f"step2_sewn_{FABRIC}.png"))
