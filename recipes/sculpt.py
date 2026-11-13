"""Sculpting by code: repeatable shape edits on a character, like sculpt-mode brushes.

Sculpt mode in Blender is hand-painting with brushes, which cannot be repeated or
described in a script. These operations do the same kinds of edit as a list of steps:
"pull the chin forward 6 mm with a soft falloff", "inflate the cheekbones". The list is
saved with the scene's script, so it can be re-run on any body, tweaked, or switched off.

Each edit acts on every base-mesh vertex within `radius` of a centre, weighted by a soft
falloff (1 at the centre, 0 at the radius). Because helper geometry moves too, clothes,
hair, eyes, teeth and the skeleton (placed from helper cubes) all follow the new shape.

Positions and sizes are in metres, Blender axes (x to the character's left, y back, z up).
A centre is either a point, or a landmark name such as "chin", "cheekbone.L" (see
`landmarks`), optionally with an offset: ("chin", (0, -0.01, 0)).
"""
import numpy as np

from . import human, rig

FALLOFFS = {
    "smooth": lambda t: 1.0 - (3.0 * t ** 2 - 2.0 * t ** 3),      # smoothstep
    "sphere": lambda t: np.sqrt(np.clip(1.0 - t ** 2, 0.0, 1.0)),
    "linear": lambda t: 1.0 - t,
    "sharp": lambda t: (1.0 - t) ** 3,
}


def to_blender(v_mh):
    return np.stack([v_mh[..., 0], -v_mh[..., 2], v_mh[..., 1]], axis=-1) * human.SCALE


def to_mh(v_bl):
    return np.stack([v_bl[..., 0], v_bl[..., 2], -v_bl[..., 1]], axis=-1) / human.SCALE


def landmarks(verts_bl):
    """Named points on a body (Blender coordinates), from skeleton joints and the face."""
    bones = rig.read_rig("default")
    joint = lambda name, end="head": np.array(rig._position(bones[name][end], verts_bl))
    eye_l, eye_r = joint("eye.L"), joint("eye.R")
    out = {
        "jaw": joint("jaw"), "chin": joint("jaw", "tail"), "head": joint("head"),
        "neck": joint("neck02"), "eye.L": eye_l, "eye.R": eye_r,
        "lip": joint("oris05"), "lip_lower": joint("oris01"),
        "nose": np.array(rig._position(bones["special03"]["tail"], verts_bl)) if "special03" in bones else (eye_l + eye_r) / 2.0,
        "forehead": (eye_l + eye_r) / 2.0 + np.array([0.0, -0.01, 0.055]),
        "chest": joint("spine02"), "belly": joint("spine04"), "hips": joint("pelvis.L") * np.array([0.0, 1.0, 1.0]),
    }
    body = verts_bl[:human.BODY_VERTS]
    mid = (np.abs(body[:, 0]) < 0.006) & (body[:, 2] < eye_l[2]) & (body[:, 2] > eye_l[2] - 0.07)
    out["nose"] = body[np.argmin(np.where(mid, body[:, 1], 9.0))]
    # Chin and jawline on the skin, not at the jaw bone inside the head.
    jt = joint("jaw", "tail")
    chin_band = (np.abs(body[:, 0]) < 0.008) & (np.abs(body[:, 2] - jt[2]) < 0.015)
    out["chin"] = body[np.argmin(np.where(chin_band, body[:, 1], 9.0))]
    out["chin_under"] = out["chin"] + np.array([0.0, 0.03, -0.02])
    for s, eye in (("L", eye_l), ("R", eye_r)):
        sign = 1.0 if s == "L" else -1.0
        out[f"brow.{s}"] = eye + np.array([0.0, -0.012, 0.022])
        out[f"cheekbone.{s}"] = eye + np.array([sign * 0.025, -0.002, -0.028])
        out[f"cheek.{s}"] = eye + np.array([sign * 0.02, -0.004, -0.055])
        band = (np.abs(body[:, 2] - (out["chin"][2] + 0.025)) < 0.008) & (body[:, 1] > out["chin"][1] + 0.03) \
            & (body[:, 1] < out["chin"][1] + 0.07) & (body[:, 0] * sign > 0)
        out[f"jawline.{s}"] = body[np.argmax(np.where(band, body[:, 0] * sign, -9.0))]
        out[f"ear.{s}"] = eye + np.array([sign * 0.045, 0.085, -0.025])
        out[f"shoulder.{s}"] = joint(f"upperarm01.{s}")
    return out


def _centre(spec, marks):
    if isinstance(spec, str):
        return np.array(marks[spec], dtype=float)
    if isinstance(spec, tuple) and len(spec) == 2 and isinstance(spec[0], str):
        return np.array(marks[spec[0]], dtype=float) + np.array(spec[1], dtype=float)
    return np.array(spec, dtype=float)


def _normals(verts):
    faces = human.base_mesh()[2]
    n = np.zeros_like(verts)
    for f in faces:
        fn = np.cross(verts[f[1]] - verts[f[0]], verts[f[2]] - verts[f[0]])
        for v in f:
            n[v] += fn
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def _edges():
    faces = human.base_mesh()[2]
    return np.array(sorted({(min(a, b), max(a, b)) for f in faces for a, b in zip(f, f[1:] + f[:1])}))


def grab(centre, radius, offset, falloff="smooth", mirror=False):
    """Move a region by `offset` (metres), fading out to the radius."""
    return {"op": "grab", "centre": centre, "radius": radius, "offset": offset, "falloff": falloff, "mirror": mirror}


def inflate(centre, radius, amount, falloff="smooth", mirror=False):
    """Push a region out along the surface (negative to deflate)."""
    return {"op": "inflate", "centre": centre, "radius": radius, "amount": amount, "falloff": falloff, "mirror": mirror}


def flatten(centre, radius, amount=1.0, falloff="smooth", mirror=False):
    """Pull a region toward its average plane (amount 0 to 1)."""
    return {"op": "flatten", "centre": centre, "radius": radius, "amount": amount, "falloff": falloff, "mirror": mirror}


def smooth(centre, radius, amount=1.0, iterations=30, falloff="smooth", mirror=False, keep_volume=True):
    """Even out bumps and creases in a region, like the sculpt-mode Smooth brush.
    The effect is strongest well inside the radius, so make the radius about twice the
    bumpy area. keep_volume=False uses plain smoothing, which also shrinks the region."""
    return {"op": "smooth", "centre": centre, "radius": radius, "amount": amount, "iterations": iterations,
            "falloff": falloff, "mirror": mirror, "keep_volume": keep_volume}


def scale(centre, radius, factor, falloff="smooth", mirror=False):
    """Enlarge or shrink a region about its centre (factor 1.1 = 10 percent larger)."""
    return {"op": "scale", "centre": centre, "radius": radius, "factor": factor, "falloff": falloff, "mirror": mirror}


# Clothing helper shells of the base mesh (garments.TIGHTS and SKIRT): MakeHuman clothes
# are fitted to these, so moving only them reshapes the clothes and leaves the body (and
# the joint cubes that place the skeleton) alone.
CLOTHES_LAYER = (15328, 18722)


def clothes(edit):
    """Apply an edit to the clothing layer only: loosen a shirt, lengthen nothing else.
    e.g. sculpt.clothes(sculpt.inflate("belly", 0.18, 0.02))"""
    return {**edit, "layer": "clothes"}


def apply(base_verts_mh, edits):
    """Apply a list of edits to base-mesh positions (MakeHuman coordinates). Returns new
    positions; the input is not changed."""
    v = to_blender(base_verts_mh)
    for edit in edits:
        marks = landmarks(v)
        centres = [_centre(edit["centre"], marks)]
        if edit.get("mirror"):
            centres.append(centres[0] * np.array([-1.0, 1.0, 1.0]))
        for k, c in enumerate(centres):
            flip = np.array([-1.0, 1.0, 1.0]) if k == 1 else np.ones(3)
            d = np.linalg.norm(v - c, axis=1)
            w = np.where(d < edit["radius"], FALLOFFS[edit["falloff"]](np.clip(d / edit["radius"], 0, 1)), 0.0)
            if edit.get("layer") == "clothes":
                keep = np.zeros(len(v), dtype=bool); keep[CLOTHES_LAYER[0]:CLOTHES_LAYER[1]] = True
                w = np.where(keep, w, 0.0)
            elif edit.get("layer") == "body":
                w[human.BODY_VERTS:] = 0.0
            if not w.any():
                continue
            op = edit["op"]
            if op == "grab":
                v = v + w[:, None] * (np.array(edit["offset"], dtype=float) * flip)
            elif op == "inflate":
                v = v + w[:, None] * edit["amount"] * _normals(v)
            elif op == "scale":
                v = v + w[:, None] * (edit["factor"] - 1.0) * (v - c)
            elif op == "flatten":
                rows = w > 0.05
                p = v[rows]
                mean = (p * w[rows, None]).sum(axis=0) / w[rows].sum()
                _, _, vt = np.linalg.svd((p - mean) * w[rows, None])
                n = vt[2]
                v = v - (edit["amount"] * w * ((v - mean) @ n))[:, None] * n
            elif op == "smooth":
                # Smooth the skin only. Helper geometry (joint cubes that place the skeleton,
                # clothing shells) would collapse under smoothing and move the bones, so each
                # helper vertex instead copies the move of its nearest skin vertex.
                e = _edges()
                e = e[(e < human.BODY_VERTS).all(axis=1)]
                deg = np.zeros(len(v)); np.add.at(deg, e[:, 0], 1.0); np.add.at(deg, e[:, 1], 1.0)
                keep = edit.get("keep_volume", True)
                before = v.copy()
                wb = w.copy(); wb[human.BODY_VERTS:] = 0.0
                for i in range(2 * edit["iterations"] if keep else edit["iterations"]):
                    mean = np.zeros_like(v)
                    np.add.at(mean, e[:, 0], v[e[:, 1]]); np.add.at(mean, e[:, 1], v[e[:, 0]])
                    step = (0.5 if i % 2 == 0 else -0.53) if keep else 0.5
                    lap = mean / np.maximum(deg, 1.0)[:, None] - v
                    v = v + (edit["amount"] * step * wb)[:, None] * lap
                helpers = np.nonzero(w[human.BODY_VERTS:] > 0)[0] + human.BODY_VERTS
                skin = np.nonzero(wb > 0)[0]
                if len(helpers) and len(skin):
                    for chunk in np.array_split(helpers, max(1, len(helpers) // 512)):
                        near = skin[np.argmin(((before[chunk, None, :] - before[None, skin, :]) ** 2).sum(-1), axis=1)]
                        v[chunk] = before[chunk] + (v[near] - before[near])
            else:
                raise ValueError(f"unknown sculpt operation {op!r}")
    return to_mh(v)
