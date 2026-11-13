"""Measure one of our characters in the terms GarmentCode's pattern generator expects.

Writes a body-measurement file (centimetres and degrees). Values that set where panels sit
and how big they are (height, neck-to-shoulder geometry, arm pose and length, chest, waist
and hip girths) are measured from the mesh. The remaining values, which shape darts and
curves, are scaled from the library's average male body by height; they are marked in the
output so nobody mistakes them for measurements.

Usage: python tools/measure_body.py REFERENCE_BODY.yaml OUT.yaml gender=1.0 age=0.55 ...
"""
import math
import os
import sys

import numpy as np
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from recipes import garments, human, rig  # noqa: E402


def hull_perimeter(points):
    """Length round the convex outline of 2D points: what a tape measure would read."""
    pts = sorted(map(tuple, np.round(points, 5)))
    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and ((out[-1][0] - out[-2][0]) * (p[1] - out[-2][1])
                                     - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0])) <= 0:
                out.pop()
            out.append(p)
        return out[:-1]
    ring = np.array(half(pts) + half(pts[::-1]))
    return float(np.linalg.norm(ring - np.roll(ring, -1, axis=0), axis=1).sum())


def measure(sliders):
    vb = human.to_blender(human.morphed_base(**sliders))
    body = vb[:human.BODY_VERTS]
    part = garments._body_coordinates()["part"][:human.BODY_VERTS]
    bones = rig.read_rig("default")
    joint = lambda name: np.array(rig._position(bones[name]["head"], vb))
    # "neck" in the part map also covers the head, so it is left out of shoulder
    # measurements (the first version read the top of the head as the neck point).
    trunk = body[np.isin(part, ("torso", "neck", "leg"))]     # everything a tape goes round
    upper = body[np.isin(part, ("torso", "arm"))]

    height = body[:, 2].max()
    # Where neck meets shoulder, and the shoulder tip, both taken on the top surface.
    x_neck = 0.065
    z_neck = upper[np.abs(np.abs(upper[:, 0]) - x_neck) < 0.01][:, 2].max()
    shoulder, elbow, wrist = joint("upperarm01.L"), joint("lowerarm01.L"), joint("wrist.L")
    x_tip = shoulder[0] + 0.02
    z_tip = upper[np.abs(np.abs(upper[:, 0]) - x_tip) < 0.012][:, 2].max()

    def girth(z):
        ring = trunk[np.abs(trunk[:, 2] - z) < 0.012]
        return hull_perimeter(ring[:, :2])

    hip_z = joint("upperleg01.L")[2]
    span = z_neck - hip_z
    levels = {"bust": z_neck - 0.42 * span, "waist": z_neck - 0.68 * span, "hips": hip_z - 0.02 * span}
    arm = wrist - shoulder
    return {
        "height": height * 100,
        "head_l": (height - z_neck) * 100,
        "shoulder_w": 2 * x_tip * 100,
        "shoulder_incl": math.degrees(math.atan2(z_neck - z_tip, x_tip - x_neck)),
        "arm_pose_angle": math.degrees(math.atan2(-arm[2], arm[0])),
        "arm_length": (np.linalg.norm(elbow - shoulder) + np.linalg.norm(wrist - elbow)) * 100,
        "bust": girth(levels["bust"]) * 100,
        "waist": girth(levels["waist"]) * 100,
        "hips": girth(levels["hips"]) * 100,
        "bust_line": (z_neck - levels["bust"]) * 100,
        "waist_line": (z_neck - levels["waist"]) * 100,
        "hips_line": (levels["waist"] - levels["hips"]) * 100,
    }


if __name__ == "__main__":
    reference_file, out_file = sys.argv[1:3]
    sliders = {k: float(v) for k, v in (a.split("=") for a in sys.argv[3:])}
    with open(reference_file) as fh:
        reference = yaml.safe_load(fh)["body"]
    measured = measure(sliders)
    ratio = float(measured["height"]) / float(reference["height"])
    body = {k: float(round(float(v) * ratio, 3)) for k, v in reference.items()}
    body.update({k: float(round(float(v), 3)) for k, v in measured.items()})
    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
    with open(out_file, "w") as fh:
        fh.write("# Measured from the mesh: " + ", ".join(sorted(measured)) + "\n")
        fh.write("# Scaled from the reference body by height (not measured): "
                 + ", ".join(sorted(set(body) - set(measured))) + "\n")
        yaml.safe_dump({"body": body}, fh)
    print("MEASURED " + " ".join(f"{k}={measured[k]:.1f} (ref {reference[k]:.1f})" for k in measured))
