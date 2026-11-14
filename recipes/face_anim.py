"""Facial animation from ARKit-named blendshape curves (face mocap).

Source and checks: notes/facial-mocap-plan.md. The 52 shapes are MakeHuman's Faceunits 01
targets (CC0) for our base mesh; tracked curves come from tools/face_track.py (MediaPipe
Face Landmarker, Apache-2.0), one value 0..1 per ARKit name per frame.

add_faceunit_keys: one shape key per unit on the body and on every fitted MakeHuman item
(eyes, brows, lashes, teeth, clothes), so teeth and lashes move with the face. A fitted
item's vertex is a fixed weighted sum of base-mesh vertices (human.fit), so its key is
fit(base + unit) - fit(base). Garments made by recipes/garments.py are not keyed.

apply_curves: keyframes those shape keys from per-frame values, with neutral offset, gain
and smoothing; head rotation goes onto the head and neck bones.
"""
import csv
import math

import bpy
import numpy as np

from . import human

ARKIT = ["browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight",
         "cheekPuff", "cheekSquintLeft", "cheekSquintRight", "eyeBlinkLeft", "eyeBlinkRight",
         "eyeLookDownLeft", "eyeLookDownRight", "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft",
         "eyeLookOutRight", "eyeLookUpLeft", "eyeLookUpRight", "eyeSquintLeft", "eyeSquintRight",
         "eyeWideLeft", "eyeWideRight", "jawForward", "jawLeft", "jawOpen", "jawRight", "mouthClose",
         "mouthDimpleLeft", "mouthDimpleRight", "mouthFrownLeft", "mouthFrownRight", "mouthFunnel",
         "mouthLeft", "mouthLowerDownLeft", "mouthLowerDownRight", "mouthPressLeft", "mouthPressRight",
         "mouthPucker", "mouthRight", "mouthRollLower", "mouthRollUpper", "mouthShrugLower",
         "mouthShrugUpper", "mouthSmileLeft", "mouthSmileRight", "mouthStretchLeft", "mouthStretchRight",
         "mouthUpperUpLeft", "mouthUpperUpRight", "noseSneerLeft", "noseSneerRight", "tongueOut"]


def _object_positions(name, item, verts_mh):
    """Blender-space positions of one built object for given base-mesh positions."""
    if "offset" in item:                                  # fitted MakeHuman item (.mhclo)
        return human.to_blender(human.fit(item, verts_mh))
    return human.to_blender(verts_mh[:human.BODY_VERTS])  # body or collider copy


def keyable_objects(root):
    """{object: binding} for the body and fitted items of a character built by build_human."""
    kids = {o.name: o for o in [root] + list(root.children_recursive) if o.type == "MESH"}
    out = {}
    for name, item in human.BINDINGS.items():
        if name in kids and ("offset" in item or len(kids[name].data.vertices) == human.BODY_VERTS):
            out[kids[name]] = item
    body = next((o for o in kids.values() if len(o.data.vertices) == human.BODY_VERTS
                 and not o.name.endswith("_collider")), None)
    if body is not None:
        out[body] = {}
    return out


def add_faceunit_keys(root, units=ARKIT, sculpt=None, **sliders):
    """Add one zero-valued shape key per unit to every keyable object of the character.

    sliders and sculpt must be the ones the character was built with. Returns
    {unit: number of objects it moves}."""
    neutral = human.morphed_base(sculpt=sculpt, **sliders)
    objects = keyable_objects(root)
    for obj in objects:
        if obj.data.shape_keys is None:
            obj.shape_key_add(name="Basis", from_mix=False)
    moved = {}
    for unit in units:
        shaped = human.morphed_base(expression={unit: 1.0}, sculpt=sculpt, **sliders)
        moved[unit] = 0
        for obj, item in objects.items():
            base = _object_positions(obj.name, item, neutral)
            new = _object_positions(obj.name, item, shaped)
            delta = new - base
            if not np.any(np.abs(delta) > 1e-7):
                continue
            key = obj.shape_key_add(name=unit, from_mix=False)
            co = np.empty(len(obj.data.vertices) * 3)
            obj.data.shape_keys.key_blocks["Basis"].data.foreach_get("co", co)
            key.data.foreach_set("co", (co.reshape(-1, 3) + delta).ravel())
            key.value = 0.0
            moved[unit] += 1
    return moved


def set_units(root, values):
    """Set shape key values by unit name on every keyed object: {unit: 0..1}."""
    for obj in keyable_objects(root):
        keys = obj.data.shape_keys
        if keys is None:
            continue
        for unit, v in values.items():
            if unit in keys.key_blocks:
                keys.key_blocks[unit].value = float(v)


def read_curves(path):
    """Per-frame curves from tools/face_track.py's CSV: (times, {channel: array})."""
    with open(path) as fh:
        rows = list(csv.DictReader(fh))
    times = np.array([float(r["time_s"]) for r in rows])
    chans = {k: np.array([float(r[k]) if r[k] not in ("", "nan") else np.nan for r in rows])
             for k in rows[0] if k not in ("frame", "time_s")}
    return times, chans


def one_euro(x, rate, min_cutoff=1.5, beta=0.3, d_cutoff=1.0):
    """One-Euro filter (Casiez et al. 2012): little lag on fast moves, steady when still."""
    def alpha(cutoff):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau * rate)
    out = np.array(x, dtype=float)
    dx_prev = 0.0
    for i in range(1, len(out)):
        if np.isnan(out[i]):
            out[i] = out[i - 1]
            continue
        dx = (out[i] - out[i - 1]) * rate
        dx_hat = dx_prev + alpha(d_cutoff) * (dx - dx_prev)
        a = alpha(min_cutoff + beta * abs(dx_hat))
        out[i] = out[i - 1] + a * (out[i] - out[i - 1])
        dx_prev = dx_hat
    return out


def zero_phase(x, rate, **kw):
    """One-Euro run forward and then backward: no lag when the whole clip is known
    (a forward pass alone lagged 2 to 3 frames at 24 fps, runs/018 try1)."""
    return one_euro(one_euro(x, rate, **kw)[::-1], rate, **kw)[::-1]


def lip_top_up(values, source_lip, lip_per_unit, neutral_lip=0.0, jaw_curve=None):
    """Open the jaw by what the keyed units leave short of the source's lip gap.

    On a real talking face MediaPipe puts mouth opening into mouthUpperUp/mouthLowerDown
    (r 0.89 / 0.73 with the landmark lip gap) and hardly into jawOpen, while on our
    character those units open the lips little (runs/018 try1: half the source amplitude).
    lip_per_unit: {unit: lip gap rise at 1.0 on our character}, measured by
    experiments/face_response.py. source_lip: per-frame landmark lip gap / face width.
    jaw_curve: (jawOpen levels, lip gap at each) measured by experiments/face_jaw_curve.py;
    our lips stay sealed below jawOpen 0.15, so a straight line under-opens (try2)."""
    n = len(source_lip)
    predicted = np.full(n, neutral_lip)
    for unit, per in lip_per_unit.items():
        if unit in values and unit != "jawOpen" and per > 0:
            predicted += values[unit] * per
    want = np.nan_to_num(np.asarray(source_lip, dtype=float) - (predicted - neutral_lip), nan=0.0)
    if jaw_curve is not None:
        levels, lips = (np.asarray(x, dtype=float) for x in jaw_curve)
        lips = np.maximum.accumulate(lips)                     # monotonic for inversion
        topped = np.interp(want, lips, levels)
    else:
        topped = np.maximum(want - neutral_lip, 0.0) / lip_per_unit["jawOpen"]
    jaw = np.clip(np.maximum(values.get("jawOpen", np.zeros(n)), topped), 0.0, 1.0)
    out = dict(values)
    out["jawOpen"] = jaw
    return out


def prepare(chans, rate, neutral=None, gain=None, smooth=True, floor=0.0):
    """Neutral offset, per-channel gain, clamp to 0..1 and zero-lag smoothing for the
    shape channels. neutral: {channel: value on a relaxed frame} subtracted first;
    gain: {channel: factor}."""
    out = {}
    for unit in ARKIT:
        x = np.nan_to_num(chans.get(unit, np.zeros(1)), nan=0.0)
        if neutral:
            x = x - neutral.get(unit, 0.0)
        if gain:
            x = x * gain.get(unit, 1.0)
        x = np.clip(x, 0.0, 1.0)
        x[x < floor] = 0.0
        out[unit] = np.clip(zero_phase(x, rate), 0.0, 1.0) if smooth and len(x) > 1 else x
    return out


def apply_curves(root, values, frame_start=1, head=None, head_bones=(("neck01", 0.4), ("head", 0.6)),
                 tracker_per_bone=None):
    """Keyframe shape keys (values: {unit: per-frame array}) and optionally head rotation.

    head: {"yaw", "pitch", "roll"} arrays in tracker degrees (tools/face_track.py), relative
    to the neutral pose. tracker_per_bone: 3x3 matrix, rows tracker (yaw, pitch, roll),
    columns bone axis (x, y, z), measured by experiments/face_head_axes.py on the default rig
    (bone x = pitch, y = yaw, z = roll). The bone rotation solving it is split over head_bones.
    Returns the last frame."""
    n = len(next(iter(values.values())))
    objects = keyable_objects(root)
    for obj in objects:
        keys = obj.data.shape_keys
        if keys is None:
            continue
        for unit, curve in values.items():
            kb = keys.key_blocks.get(unit)
            if kb is None:
                continue
            for i in range(n):
                kb.value = float(curve[i])
                kb.keyframe_insert("value", frame=frame_start + i)
    if head is not None and root.type == "ARMATURE":
        M = np.array(tracker_per_bone if tracker_per_bone is not None else [[0, 1, 0], [1, 0, 0], [0, 0, 1]], dtype=float)
        tracked = np.stack([np.nan_to_num(head["yaw"]), np.nan_to_num(head["pitch"]), np.nan_to_num(head["roll"])])
        bone_deg = np.linalg.solve(M, tracked)               # rows: bone x, y, z
        for bone_name, share in head_bones:
            pb = root.pose.bones.get(bone_name)
            if pb is None:
                continue
            pb.rotation_mode = "XYZ"
            base = pb.rotation_euler.copy()
            for i in range(n):
                pb.rotation_euler = (base.x + math.radians(share * bone_deg[0, i]),
                                     base.y + math.radians(share * bone_deg[1, i]),
                                     base.z + math.radians(share * bone_deg[2, i]))
                pb.keyframe_insert("rotation_euler", frame=frame_start + i)
    return frame_start + n - 1
