"""Run 012: orange curly hair (a mop of ringlets) on a boy, from guides plus children.

Reference: the boy in "My Mom Cracked The Dinosaur" (owner-supplied clip, kept out of git).
Usage: python runs/012-curls/curls.py [width height samples]
Environment: GUIDES, CHILDREN, COIL (radius m), PITCH (m per turn), VOLUME (m), LENGTH (m),
SPREAD (round lock width m), RIBBON (flat lock width m, 0 for round springs), THICK, TAPER, RFRIZZ, COLOR ("r,g,b" for direct colour) or MELANIN/REDNESS, OUT, VIEWS.
"""
import json
import os
import sys
import time

import bpy
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from recipes import accessories, camera, color, garments, haircut, human, materials, render, skin, stage, world  # noqa: E402

W, H, SAMPLES = (int(a) for a in sys.argv[1:4]) if len(sys.argv) > 3 else (360, 360, 32)
SLIDERS = dict(gender=1.0, age=0.22, muscle=0.5, weight=0.45, height=0.45, caucasian=1, african=0, asian=0)
env = lambda k, d: type(d)(os.environ.get(k, d))
# Head angle from the reference close-ups: chin down, tilted and turned a little.
# World axes, character facing -Y: +X nods down, Y rolls, +Z turns to his left.
TILT = [float(a) for a in os.environ.get("HEAD", "14,-7,10").split(",")]
POSE = [("turn", "neck01", "X", TILT[0] * 0.4), ("turn", "head", "X", TILT[0] * 0.6),
        ("turn", "head", "Y", TILT[1]), ("turn", "head", "Z", TILT[2])] if any(TILT) else None

scene = stage.new_scene()
base_verts = human.morphed_base(**SLIDERS)
boy = human.build_human(scene, name="Boy", skin="young_caucasian_male", hair=None, eyes="green",
                        outfit=(garments.top(name="tee", sleeve=0.3, collar=1.0, hem=0.0, ease=0.006,
                                             material=materials.fabric((0.72, 0.70, 0.64), on="garment")),),
                        pose=POSE, **SLIDERS)
body = next(o for o in boy.children_recursive if o.name == "Boy") if POSE else boy
materials.soften_skin(body.data.materials[0])
# Reference: one blue eye (his right, under the fringe) and one green eye (his left).
eyes_obj = next(c for c in boy.children_recursive if c.name == "Boy_low-poly")
eye_mat = lambda colour: human.material_from_mhmat(f"{human.PACK}/eyes/materials/{colour}.mhmat", f"eye_{colour}")
skin.two_eye_colours(eyes_obj, eye_mat(os.environ.get("EYE_R", "lightblue")), eye_mat(os.environ.get("EYE_L", "green")))
if env("FRECKLES", 1):
    freckles, finfo = skin.freckle_image(base_verts, count=env("FRECKLE_COUNT", 1000))
    print("FRECKLES " + json.dumps(finfo))
else:
    freckles = None
skin.add_detail(body.data.materials[0], freckles=freckles, freckle_amount=env("FRECKLE_AMOUNT", 0.6),
                tone=tuple(float(c) for c in os.environ.get("TONE", "1.0,0.93,0.70").split(",")),
                pores=env("PORES", 0.04))


def curl_material():
    mat = haircut.material("Curls", melanin=env("MELANIN", 0.25), white=0.0, redness=env("REDNESS", 1.0),
                           roughness=env("ROUGH", 0.45))
    rgb = os.environ.get("COLOR", "1.0,0.075,0.02")   # coral; melanin mode came out golden
    if rgb:
        hair = next(n for n in mat.node_tree.nodes if n.type == "BSDF_HAIR_PRINCIPLED")
        hair.parametrization = "COLOR"
        hair.inputs["Color"].default_value = [float(c) for c in rgb.split(",")] + [1.0]
    return mat


obj, info = haircut.curls(
    scene, base_verts, guides=env("GUIDES", 260), children=env("CHILDREN", 150000), mat=curl_material(), parent=None if POSE else boy, radius=env("STRAND", 0.00005),
    style=lambda sc, p: haircut.curly_mop(sc, p, length=env("LENGTH", 0.065), side=env("SIDE", 0.32),
                                           fringe_cut=env("FRINGE_CUT", 0.25), sweep=env("SWEEP", 0.35)),
    grow_args=dict(coil_radius=env("COIL", 0.009), coil_pitch=env("PITCH", 0.06), volume=env("VOLUME", 0.028)),
    child_args=dict(spread=env("SPREAD", 0.006)),
    ribbon=dict(width=env("RIBBON", 0.012), thickness=env("THICK", 0.005), taper=env("TAPER", 0.1),
                frizz=env("RFRIZZ", 0.0006),
                fray=env("FRAY", 0.003), shorten=env("SHORTEN", 0.35))
    if env("RIBBON", 0.012) > 0 else None)
print("HAIR " + json.dumps(info))
if POSE:
    from recipes import rig  # noqa: E402
    rig.parent_to_bone(obj, boy, "head")

lm = accessories.face_landmarks(base_verts)
if os.environ.get("LIGHT", "studio") == "studio":
    # soft warm indoor light like the reference (a museum hall), instead of hard sun
    from recipes import lighting  # noqa: E402
    world.sky_world(scene, sun_elevation_deg=40.0, sun_rotation_deg=220.0, strength=0.004)
    target = stage.empty_at(scene, "Head", (0.0, lm["front_y"] + 0.09, lm["eye_z"]))
    lighting.three_point(scene, target, (-0.2, -2.0, lm["eye_z"]), key_power=env("KEY", 58.0), fill_ratio=0.35,
                         rim_ratio=1.2, distance=2.0, key_size=1.2)
else:
    world.sky_world(scene, sun_elevation_deg=40.0, sun_rotation_deg=220.0, strength=0.035)
scene.cycles_curves.shape = "THICK"
color.set_view(scene, "AgX", look="Medium High Contrast")
render.cycles_cpu(scene, width=W, height=H, samples=SAMPLES)
aim = stage.empty_at(scene, "Aim", (0.0, lm["front_y"] + 0.09, lm["eye_z"] + 0.03))
views = {"front": (-0.12, -0.80, lm["eye_z"] + 0.02), "side": (0.80, -0.05, lm["eye_z"] + 0.10),
         "back": (0.25, 0.95, lm["eye_z"] + 0.20),
         "low": (-0.10, -0.55, lm["eye_z"] - 0.22),
         "face": (-0.03, -0.42, lm["eye_z"] - 0.10)}   # close-up like the reference at 24 s   # looking up, like the reference close-up
names = os.environ.get("VIEWS", "front,side,back").split(",")
tiles = []
started = time.time()
for label in names:
    for o in [o for o in scene.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(o, do_unlink=True)
    aim.location = (0.0, lm["front_y"] + (0.05 if label == "face" else 0.09), lm["eye_z"] + (-0.01 if label == "face" else 0.03))
    camera.camera_at(scene, views[label], aim, lens=85.0)
    path = os.path.join(HERE, f"curls_{label}.png")
    render.render_to(scene, path)
    tiles.append(Image.open(path).convert("RGB"))
sheet = Image.new("RGB", (W * len(tiles), H))
for i, t in enumerate(tiles):
    sheet.paste(t, (W * i, 0))
out = os.environ.get("OUT") or os.path.join(HERE, "curls.png")
sheet.save(out)
print("STATS " + json.dumps({"render_seconds": round(time.time() - started), **info}))
