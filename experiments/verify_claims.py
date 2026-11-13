"""Test claims taken from sources by rendering and measuring.

A claim from a manual page or tutorial is only a claim until a render confirms it on
the Blender version in use. Each experiment states the claim, renders the smallest
scene that can show it, and records numbers in results.json.

Usage: python experiments/verify_claims.py
"""
import json
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from recipes import camera, color, lighting, render, stage, world  # noqa: E402
from tools.image_stats import load, luminance, stats  # noqa: E402

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
results = {"blender": bpy.app.version_string, "experiments": {}}


def small(scene, samples=48):
    render.cycles_cpu(scene, width=320, height=180, samples=samples)


def floor(scene, size=30, grey=0.5):
    bpy.ops.mesh.primitive_plane_add(size=size)
    plane = bpy.context.object
    plane.data.materials.append(stage.principled("Floor", (grey, grey, grey), roughness=1.0))
    return plane


# E1 ---------------------------------------------------------------------------------
# Claim (manual, Light Objects): "Lights with larger size have softer shadows".
def e1_shadow_softness():
    widths = {}
    for radius in (0.02, 1.0):
        scene = stage.new_scene()
        floor(scene)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.5))
        cube = bpy.context.object
        data = bpy.data.lights.new("Lamp", "POINT")
        data.energy = 3000
        data.shadow_soft_size = radius
        lamp = bpy.data.objects.new("Lamp", data)
        lamp.location = (-4, 0, 4)
        scene.collection.objects.link(lamp)
        world.solid_world(scene, (0, 0, 0), 0.0)
        # Straight-down orthographic camera over the floor where the shadow falls.
        cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 6
        cam.location = (2.2, 0, 10)
        scene.collection.objects.link(cam)
        scene.camera = cam
        color.set_view(scene, "Standard")
        small(scene, samples=96)
        path = render.render_to(scene, os.path.join(OUT, f"e1_radius_{radius}.png"))
        lum = luminance(load(path))
        row = lum[lum.shape[0] // 2]  # scanline: cube top, shadow, then lit floor
        row = row[int(np.argmin(row)):]  # start at the darkest shadow pixel
        lo, hi = row.min(), row.max()
        # Pixels needed to climb from 10% to 90% of the way out of the shadow.
        # (First attempt counted every in-between pixel on the row and was fooled by the
        # lamp's distance falloff on the lit floor; see notes.)
        start = int(np.argmax(row > lo + 0.1 * (hi - lo)))
        end = int(np.argmax(row > lo + 0.9 * (hi - lo)))
        widths[str(radius)] = max(end - start, 1)
    passed = widths["1.0"] > 3 * widths["0.02"]
    return {
        "claim": "Larger light radius gives softer shadows",
        "source": "manual: render/lights/light_object",
        "measure": "pixels of partial shadow along a scanline across the shadow edge",
        "values": widths,
        "confirmed": bool(passed),
    }


# E2 ---------------------------------------------------------------------------------
# Claim (manual, Displays and Views): output_value = render_value * 2**exposure.
def e2_exposure_doubling():
    means = {}
    for exposure in (0.0, 1.0):
        scene = stage.new_scene()
        floor(scene, grey=0.18)
        data = bpy.data.lights.new("Sun", "SUN")
        data.energy = 1.0
        sun = bpy.data.objects.new("Sun", data)
        scene.collection.objects.link(sun)  # default orientation shines straight down
        world.solid_world(scene, (0, 0, 0), 0.0)
        cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
        cam.location = (0, 0, 8)
        scene.collection.objects.link(cam)
        scene.camera = cam
        color.set_view(scene, "Raw", exposure=exposure)  # Raw: no tone curve, values stay linear
        small(scene, samples=16)
        path = render.render_to(scene, os.path.join(OUT, f"e2_exposure_{exposure}.png"))
        means[str(exposure)] = float(load(path).mean())
    ratio = means["1.0"] / means["0.0"]
    return {
        "claim": "+1 stop of exposure doubles pixel values",
        "source": "manual: render/color_management/displays_views",
        "measure": "mean pixel value under the Raw view at exposure 0 and +1",
        "values": {k: round(v, 4) for k, v in means.items()},
        "ratio": round(ratio, 3),
        "confirmed": bool(abs(ratio - 2.0) < 0.1),
    }


# E3 ---------------------------------------------------------------------------------
# Claim (manual): AgX "desaturates highly exposed colors"; Standard does no extra conversion.
def e3_agx_desaturates():
    sat = {}
    for view in ("Standard", "AgX"):
        scene = stage.new_scene()
        floor(scene)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 1))
        ball = bpy.context.object
        ball.data.shade_smooth()
        ball.data.materials.append(stage.principled("Red", (0.8, 0.03, 0.03), roughness=0.6))
        data = bpy.data.lights.new("Sun", "SUN")
        # Bright enough to push red past the display maximum while green and blue stay low.
        # (First attempt used 60, which clipped all three channels to white under Standard
        # and made the comparison meaningless; see notes.)
        data.energy = 8.0
        sun = bpy.data.objects.new("Sun", data)
        sun.rotation_euler = (math.radians(40), 0, math.radians(30))
        scene.collection.objects.link(sun)
        world.solid_world(scene, (0, 0, 0), 0.0)
        camera.camera_at(scene, (5, -5, 3), ball)
        color.set_view(scene, view)
        small(scene, samples=32)
        path = render.render_to(scene, os.path.join(OUT, f"e3_{view}.png"))
        rgb = load(path)
        red = rgb[..., 0] > rgb[..., 1] + 0.05  # pixels on the red ball
        mx, mn = rgb.max(axis=2), rgb.min(axis=2)
        s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-9), 0)
        bright = red & (mx >= np.percentile(mx[red], 75))
        sat[view] = float(s[bright].mean())
    return {
        "claim": "AgX desaturates over-exposed colours; Standard clips them at full saturation",
        "source": "manual: render/color_management/displays_views",
        "measure": "mean saturation of the brightest quarter of an over-lit red ball",
        "values": {k: round(v, 3) for k, v in sat.items()},
        "confirmed": bool(sat["AgX"] < sat["Standard"] - 0.1),
    }


# E4 ---------------------------------------------------------------------------------
# Claim (manual, Sky Texture): the sky is "very bright by default"; lower scene exposure.
def e4_sky_brightness():
    out = {}
    for exposure in (0.0, -2.0, -4.0):
        scene = stage.new_scene()
        floor(scene)
        bpy.ops.mesh.primitive_cube_add(size=1.5, location=(0, 0, 0.75))
        cube = bpy.context.object
        cube.data.materials.append(stage.principled("Grey", (0.5, 0.5, 0.5)))
        world.sky_world(scene, sun_elevation_deg=35, sun_rotation_deg=120)
        camera.camera_at(scene, (6, -6, 3), cube)
        color.set_view(scene, "AgX", exposure=exposure)
        small(scene, samples=32)
        path = render.render_to(scene, os.path.join(OUT, f"e4_sky_exposure_{exposure}.png"))
        out[str(exposure)] = stats(path)
    return {
        "claim": "Default sky texture is too bright at exposure 0 and needs negative exposure",
        "source": "manual: render/shader_nodes/textures/sky",
        "measure": "median brightness and clipped fraction at exposure 0, -2 and -4 stops",
        "values": {k: {"median": v["median"], "clipped": v["clipped_fraction"]} for k, v in out.items()},
        "confirmed": bool(out["0.0"]["median"] > 0.8 and out["-4.0"]["median"] < out["0.0"]["median"]),
    }


RESULTS_PATH = os.path.join(HERE, "results.json")
ONLY = [a for a in sys.argv[1:] if a.startswith("E")]  # e.g. `verify_claims.py E1 E3`
if ONLY and os.path.exists(RESULTS_PATH):
    with open(RESULTS_PATH) as fh:
        results["experiments"] = json.load(fh).get("experiments", {})

for name, fn in [("E1", e1_shadow_softness), ("E2", e2_exposure_doubling),
                 ("E3", e3_agx_desaturates), ("E4", e4_sky_brightness)]:
    if ONLY and name not in ONLY:
        continue
    try:
        results["experiments"][name] = fn()
    except Exception as err:  # an experiment that cannot run is a finding, not a crash
        results["experiments"][name] = {"error": f"{type(err).__name__}: {err}"}

with open(RESULTS_PATH, "w") as fh:
    json.dump(results, fh, indent=2)
print("RESULTS " + json.dumps(results, indent=2))
