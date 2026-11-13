"""Run 003: a clothed character dancing to a CMU motion-capture clip.

Usage:
  python runs/003-dance/build.py sheet            8 frames tiled into contact_sheet.png
  python runs/003-dance/build.py clip [w h spp]   every frame to frames/, then dance.mp4
"""
import json
import os
import subprocess
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from recipes import camera, color, human, lighting, motion, render, stage, world  # noqa: E402

MODE = sys.argv[1] if len(sys.argv) > 1 else "sheet"
CLIP = os.path.join(human.ASSETS, "motion", "cmu", "05_02.bvh")  # modern dance: expressive arms, pirouette

scene = stage.new_scene()
dancer = human.build_human(scene, name="Dancer", outfit=("female_sportsuit01", "shoes03"),
                           hair="ponytail01", skin="young_caucasian_female2", eyes="brown",
                           pose=[], rig_name="cmu_mb", gender=0.0, age=0.45, muscle=0.6, weight=0.4)
move = motion.retarget(dancer, motion.read_bvh(CLIP))
frames = motion.apply(dancer, move)

# Frame the whole path the hips travel, not just the starting spot.
path = move["hips"]
centre = (float(path[:, 0].mean()), float(path[:, 1].mean()), 1.0)
# 4.4 m plus the sideways travel keeps a 1.6 m dancer with raised arms inside a 45 mm frame.
# (First sheet used 7 m and the dancer filled only a third of the frame height.)
reach = float(np.ptp(path[:, 0]))
cam_at = (centre[0], float(path[:, 1].min()) - (4.4 + reach), 1.25)
aim = stage.empty_at(scene, "Aim", centre)
stage.backdrop(scene, cam_at, centre)
lighting.three_point(scene, aim, cam_at, key_power=450.0, distance=6.5, key_size=3.0)
world.solid_world(scene, (0.6, 0.72, 0.9), 0.05)
camera.camera_at(scene, cam_at, aim, lens=45.0)
color.set_view(scene, "AgX", look="Medium High Contrast")

if MODE == "sheet":
    from PIL import Image
    render.cycles_cpu(scene, width=480, height=270, samples=24)
    picks = [int(x) for x in np.linspace(1, frames, 8)]
    tiles = []
    started = time.time()
    for f in picks:
        scene.frame_set(f)
        tiles.append(Image.open(render.render_to(scene, os.path.join(HERE, "frames", f"sheet_{f:04d}.png"))))
    sheet = Image.new("RGB", (480 * 4, 270 * 2))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, (480 * (i % 4), 270 * (i // 4)))
    sheet.save(os.path.join(HERE, "contact_sheet.png"))
    print("SHEET", json.dumps({"frames": picks, "seconds_per_frame": round((time.time() - started) / 8, 1)}))
else:
    w, h, spp = (int(a) for a in sys.argv[2:5]) if len(sys.argv) > 4 else (640, 360, 24)
    render.cycles_cpu(scene, width=w, height=h, samples=spp)
    scene.render.filepath = os.path.join(HERE, "frames", "dance_")
    started = time.time()
    bpy.ops.render.render(animation=True)
    out = os.path.join(HERE, "dance.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(move["fps"]),
                    "-i", os.path.join(HERE, "frames", "dance_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", out], check=True)
    info = {"blender": bpy.app.version_string, "clip": os.path.basename(CLIP), "frames": frames,
            "fps": move["fps"], "size": [w, h], "samples": spp,
            "render_minutes": round((time.time() - started) / 60, 1)}
    with open(os.path.join(HERE, "stats.json"), "w") as fh:
        json.dump(info, fh, indent=2)
    print("CLIP", json.dumps(info))
