"""Zoom presets: one per big zoom (size change of 20% or more) the clip analyzer read in the reference.

Table = recipes/zoom_presets.json, made by tools/make_zoom_presets.py from the analyzer's per-frame
numbers. Each preset has a size change (%), a duration and a speed profile (how the size change is
spread over the move). `zoom_curve` is pure maths; `zoom_states` turns it into camera states with
recipes/camera_moves (needs bpy's mathutils, so it runs on the pod, not on the Mac).

Dials for the game: `strength` scales the size change (1.0 = the reference's), `dur_scale` stretches time.
Size in frame goes as 1 / distance, so a +289% zoom means distance / 3.89.
pan_pct and tilt_pct are stored in the table for later; they are not applied here.
"""
import json
import math
import os

TABLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zoom_presets.json")


def load():
    return {p["id"]: p for p in json.load(open(TABLE))["presets"]}


def frames_for(preset, fps=30.03, dur_scale=1.0):
    return max(2, round(preset["dur_s"] * dur_scale * fps))


def zoom_curve(preset, n, strength=1.0):
    """Size factor at each of n frames (1.0 at the start, ends at 1 + size_pct/100 for strength 1)."""
    total = math.log(1 + preset["size_pct"] / 100) * strength
    prof = preset["profile"]
    out = []
    for k in range(n):
        u = k / (n - 1) * (len(prof) - 1)
        i = min(int(u), len(prof) - 2)
        p = prof[i] + (prof[i + 1] - prof[i]) * (u - i)
        out.append(math.exp(total * p))
    return out


def zoom_states(preset, target, az, el, d_start, n=None, strength=1.0, dur_scale=1.0, aim_to=None):
    """Camera states (eye, rotation, lens) for one zoom: the camera dollies along the line to `target`."""
    from recipes import camera_moves as cm  # imported late: mathutils exists only inside Blender
    n = n or frames_for(preset, dur_scale=dur_scale)
    out = []
    for t, size in zip([k / (n - 1) for k in range(n)], zoom_curve(preset, n, strength)):
        aim = target.lerp(aim_to, t) if aim_to is not None else target
        eye = cm.around(aim, az, el, d_start / size)
        out.append((eye, cm.look(eye, aim), cm.LENS))
    return out
