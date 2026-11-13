"""Run 014: track pants sewn from two flat panels by cloth simulation (route F).

Method from the owner's pro-pants tutorial (notes/tutorial-pro-pants.md): front and back
panels with a crotch slit, sewing edges at the side and inner leg seams, gravity off, a
small shrink, the body as collider. Then thickness and smoothing after the cloth.

Usage: python runs/014-sewn-pants/pants.py [width height samples]
Environment: FRAMES, SHRINK (fraction), SEW (sewing force), ROOM, GAP, OUT.
"""
import json
import os
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from recipes import camera, cloth, color, hair, human, lighting, looks, materials, panels, render, stage, world  # noqa: E402

W, H, SAMPLES = (int(a) for a in sys.argv[1:4]) if len(sys.argv) > 3 else (432, 640, 24)
env = lambda k, d: type(d)(os.environ.get(k, d))
S = looks.CURLY_BOY_SLIDERS
PANTS = (0.012, 0.035, 0.17)

scene = stage.new_scene()
base_verts = human.morphed_base(**S)
boy = human.build_human(scene, name="Boy", skin="young_caucasian_male", hair=None, eyes="green",
                        outfit=("shoes05",), collider=True, **S)
body = looks.body_of(boy, "Boy")
materials.soften_skin(body.data.materials[0])
col = next(o for o in [boy] + list(boy.children_recursive) if o.name == "Boy_collider")
cloth.make_collider(col, thickness=0.004)

mat = materials.fabric(PANTS, name="Pants", thread=0.0008, on="object", sheen=0.25)
pants, pinfo = panels.build_trousers(scene, base_verts, name="Pants", material=mat,
                                     room=env("ROOM", 0.03), gap=env("GAP", 0.035))
mod = cloth.add_cloth(pants, fabric="cotton", spare=-env("SHRINK", 0.05), resolution=0, quality=10,
                      self_distance=0.015, sewing_force=env("SEW", 20.0))
cs = next(m for m in pants.modifiers if m.type == "CLOTH")
cs.settings.effector_weights.gravity = 0.0                # tutorial: gravity off while sewing
cs.collision_settings.collision_quality = 15
total = env("FRAMES", 80)
scene.frame_start, scene.frame_end = 1, total
cs.point_cache.frame_start, cs.point_cache.frame_end = 1, total
t0 = time.time(); track = []
for f in range(1, total + 1):
    scene.frame_set(f)
    if f % 20 == 0 or f == 1:
        v = np.array(hair.evaluated_mesh(pants)[0])
        e = np.array([(pants.data.vertices[a].index, pants.data.vertices[b].index) for a, b in
                      (ed.vertices for ed in pants.data.edges if ed.is_loose)])
        gap = float(np.linalg.norm(v[e[:, 0]] - v[e[:, 1]], axis=1).mean()) if len(e) else 0.0
        track.append((f, round(gap * 1000, 1)))
sim_seconds = round(time.time() - t0)
thick = pants.modifiers.new("Thickness", "SOLIDIFY"); thick.thickness = 0.003; thick.offset = 1.0
smooth = pants.modifiers.new("Smooth", "SUBSURF"); smooth.levels = smooth.render_levels = 1

world.sky_world(scene, sun_elevation_deg=40.0, sun_rotation_deg=220.0, strength=0.006)
target = stage.empty_at(scene, "Body", (0.0, 0.0, 0.6))
lighting.three_point(scene, target, (-0.6, -3.5, 1.0), key_power=260.0, fill_ratio=0.35, rim_ratio=1.2,
                     distance=3.5, key_size=1.8)
color.set_view(scene, "AgX", look="Medium High Contrast")
render.cycles_cpu(scene, width=W, height=H, samples=SAMPLES)
from PIL import Image  # noqa: E402
tiles = []
for label, eye in (("front", (-0.7, -2.6, 0.75)), ("side", (-2.7, -0.3, 0.75))):
    for o in [o for o in scene.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(o, do_unlink=True)
    aim = stage.empty_at(scene, f"Aim_{label}", (0.0, 0.0, 0.5))
    camera.camera_at(scene, eye, aim, lens=50.0)
    path = os.path.join(HERE, f"pants_{label}.png")
    render.render_to(scene, path)
    tiles.append(Image.open(path).convert("RGB"))
sheet = Image.new("RGB", (W * len(tiles), H))
for i, t in enumerate(tiles):
    sheet.paste(t, (W * i, 0))
sheet.save(os.environ.get("OUT") or os.path.join(HERE, "pants.png"))
print("STATS " + json.dumps({**pinfo, "sim_seconds": sim_seconds, "seam_gap_mm_by_frame": track}))
