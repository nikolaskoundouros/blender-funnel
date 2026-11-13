"""Garments made from scratch: no downloaded clothing assets.

How it works. The base mesh carries two invisible helper shells that morph and bend with
the body: a skin-tight "tights" shell (2,650 quads over torso, arms, legs and feet, about
5 mm off the skin) and a skirt-shaped shell from waist to ankle. A garment is a cut-out of
those shells:

  1. Every base vertex gets a body coordinate: which part it belongs to (torso, arm, leg,
     neck, hand, foot), how far along the limb it is (0 at shoulder or hip, 1 at elbow or
     knee, 2 at wrist or ankle), or how high up the torso (0 at hip joint, 1 at neck base).
  2. A garment is a rule over those coordinates, e.g. a T-shirt is "torso between hem and
     collar, plus arms up to 0.55". The rule is a number per vertex: positive inside the
     garment, negative outside, zero exactly on its edge.
  3. Shell faces fully inside are kept. Faces that straddle the edge are kept too, with
     their outside corners slid along the mesh edge to where the number crosses zero. That
     gives a clean hem line instead of a staircase of faces. (The first version simply
     dropped straddling faces; hems, collars and armholes came out jagged.)
  4. Every garment vertex is tied to one or two base vertices, pushed out along its normal
     by an "ease". So the garment fits any body shape, takes its skin weights from the
     body, and bends with the skeleton with no extra work.
  5. Solidify gives the cloth thickness and real hems; subdivision smooths it.
  6. Skin under the garment (the same rule, pulled in slightly) is removed.

Not done here: draping. These garments follow the body; they do not hang or fold.
"""
import math

import numpy as np

import bpy

from . import human, materials, rig

TIGHTS = (15328, 18001)   # mesh_metadata/basemesh_vertex_groups.json: helper-tights
SKIRT = (18002, 18721)    # helper-skirt

_COORDS = None
FAR = 9.0


def _body_coordinates():
    """Per base vertex: part, torso height h, arm coordinate, leg coordinate, skirt height k.

    arm and leg coordinates run 0 at shoulder/hip, 1 at elbow/knee, 2 at wrist/ankle, and
    beyond 2 on hands and feet. They are also defined on the torso (as the projection onto
    the upper limb, mostly negative there) so armholes and leg openings cut cleanly.
    """
    global _COORDS
    if _COORDS is not None:
        return _COORDS
    bones = rig.read_rig("default")
    names = list(bones.keys())
    table = rig._weight_matrix("default", names)
    vb = human.to_blender(human.base_mesh()[0])
    joint = lambda bone: np.array(rig._position(bones[bone]["head"], vb))

    def part_of(bone):
        b = bone.split(".")[0]
        if b in ("upperarm01", "upperarm02", "lowerarm01", "lowerarm02"):
            return "arm"
        if b in ("upperleg01", "upperleg02", "lowerleg01", "lowerleg02"):
            return "leg"
        if b == "wrist" or b.startswith(("finger", "metacarpal")):
            return "hand"
        if b == "foot" or b.startswith("toe"):
            return "foot"
        if b.startswith(("spine", "breast", "clavicle", "shoulder", "pelvis")) or b == "root":
            return "torso"
        return "neck"  # neck, head and face bones

    dominant = table.argmax(axis=1)
    dom_name = np.array([names[d].split(".")[0] for d in dominant])
    part = np.array([part_of(names[d]) for d in dominant])
    left = vb[:, 0] >= 0
    coords = {}
    for limb, (a, b, c), ends, lower in (("arm", ("upperarm01", "lowerarm01", "wrist"), ("arm", "hand"), "lowerarm"),
                                         ("leg", ("upperleg01", "lowerleg01", "foot"), ("leg", "foot"), "lowerleg")):
        out = np.zeros(len(vb))
        for sd, mask in (("L", left), ("R", ~left)):
            p0, p1, p2 = joint(f"{a}.{sd}"), joint(f"{b}.{sd}"), joint(f"{c}.{sd}")
            t1 = (vb - p0) @ (p1 - p0) / np.dot(p1 - p0, p1 - p0)
            t2 = (vb - p1) @ (p2 - p1) / np.dot(p2 - p1, p2 - p1)
            on_lower = np.char.startswith(dom_name, lower) | (part == ends[1])
            value = np.where(on_lower, 1.0 + np.maximum(t2, 0.0), np.minimum(t1, 1.0))
            out[mask] = value[mask]
        coords[limb] = out
    # Angle round the leg, in degrees: 0 at the front, +90 on the outside, for both legs.
    theta = np.zeros(len(vb))
    for sd, sign, mask in (("L", 1.0, left), ("R", -1.0, ~left)):
        hip, knee, ankle = joint(f"upperleg01.{sd}"), joint(f"lowerleg01.{sd}"), joint(f"foot.{sd}")
        for base, axis, rows in ((hip, knee - hip, mask & (coords["leg"] <= 1.0)),
                                 (knee, ankle - knee, mask & (coords["leg"] > 1.0))):
            a = axis / np.linalg.norm(axis)
            r = vb[rows] - base
            r -= np.outer(r @ a, a)
            front = np.array([0.0, -1.0, 0.0]) - a * (-a[1])
            out = np.array([sign, 0.0, 0.0]) - a * (sign * a[0])
            front /= np.linalg.norm(front)
            out /= np.linalg.norm(out)
            theta[rows] = np.degrees(np.arctan2(r @ out, r @ front))
    # Same for the arms: 0 at the front, +90 along the top of the arm (away from the body).
    arm_theta = np.zeros(len(vb))
    for sd, sign, mask in (("L", 1.0, left), ("R", -1.0, ~left)):
        sh, el, wr = joint(f"upperarm01.{sd}"), joint(f"lowerarm01.{sd}"), joint(f"wrist.{sd}")
        for base, axis, rows in ((sh, el - sh, mask & (coords["arm"] <= 1.0)),
                                 (el, wr - el, mask & (coords["arm"] > 1.0))):
            a = axis / np.linalg.norm(axis)
            r = vb[rows] - base
            r -= np.outer(r @ a, a)
            front = np.array([0.0, -1.0, 0.0]) - a * (-a[1])
            out = np.array([sign, 0.0, 0.0]) - a * (sign * a[0])
            front /= np.linalg.norm(front)
            out /= np.linalg.norm(out)
            arm_theta[rows] = np.degrees(np.arctan2(r @ out, r @ front))
    z_hip, z_neck = joint("upperleg01.L")[2], joint("neck01")[2]
    zs = vb[SKIRT[0]:SKIRT[1] + 1, 2]
    _COORDS = {"part": part, "vb": vb, "eye": joint("eye.L"), "theta": theta, "arm_theta": arm_theta, "left": left,
               "h": (vb[:, 2] - z_hip) / (z_neck - z_hip),
               "arm": coords["arm"], "leg": coords["leg"],
               "k": (zs.max() - vb[:, 2]) / (zs.max() - zs.min())}
    return _COORDS


def _garment(name, shell, field, ease, thickness, material, skin_margin=0.07, soften=0,
             smooth_shell=0, snaps=(), cut=None, puff=0.0):
    covered = (set(np.nonzero(field[:human.BODY_VERTS] > skin_margin)[0].tolist())
               if skin_margin and field is not None else set())
    return {"name": name, "shell": shell, "field": field, "ease": ease, "thickness": thickness,
            "material": material, "delete": covered, "soften": soften,
            "smooth_shell": smooth_shell, "snaps": list(snaps), "cut": cut, "puff": puff}


# ------------------------------------------------------------------ catalogue

def top(name="top", sleeve=0.55, hem=-0.10, collar=0.96, ease=0.008, thickness=0.0025,
        material=None, soften=0, smooth_shell=0):
    """Shirt-like garment. sleeve: 0 sleeveless, 0.55 short, 1.95 long. hem: bottom edge
    relative to the hip joint (negative is lower). collar: 0.9 wide neck, 0.99 high."""
    c = _body_coordinates()
    limb = np.isin(c["part"], ("arm", "hand"))
    armhole = sleeve if sleeve > 0 else -0.10
    field = np.minimum(c["h"] - hem, collar - c["h"])
    if sleeve <= 0:
        field = np.minimum(field, armhole - c["arm"])
    field = np.where(limb, armhole - c["arm"], field)
    # soften: smoothing passes that melt the body's shape out of a thick outer garment
    return _garment(name, TIGHTS, field, ease, thickness,
                    material or materials.fabric((0.85, 0.85, 0.82), on="garment"), soften=soften,
                    smooth_shell=smooth_shell)


def baggy_ease(outer=0.032, inner=0.008, waist=0.012, ankle=0.016):
    """Per-vertex ease for loose trousers: roomy at the front and outside of the thigh,
    close on the inner thigh (so the legs do not cut into each other), gathered at the
    waistband and narrowing toward the ankle. Pass the same array, plus an offset, to
    pockets so they lie on the trousers."""
    c = _body_coordinates()
    n = shell_surface(human.base_mesh()[0], 0)[1]
    side = np.where(c["left"], 1.0, -1.0)
    outward = np.clip(0.5 + 0.5 * (n[:, 0] * side) + 0.25 * (-n[:, 1]), 0.0, 1.0)
    roomy = inner + (outer - inner) * outward
    along = np.clip((c["leg"] - 0.2) / 1.6, 0.0, 1.0)            # 0 high on the thigh, 1 at the ankle
    ease = roomy * (1.0 - along) + ankle * along
    up = np.clip((c["h"] + 0.05) / 0.2, 0.0, 1.0)                # blend to the waistband above the hip
    ease = np.where(c["part"] == "torso", waist + (ease - waist) * (1.0 - up), ease)
    return ease


_LEG_CHART = {}


LIMBS = {"leg": {"parts": ("leg", "foot"), "theta": "theta", "radius": 0.09, "length": 0.42},
         "arm": {"parts": ("arm", "hand"), "theta": "arm_theta", "radius": 0.05, "length": 0.29}}


def _leg_chart(side_left, limb="leg"):
    """The tights shell on one limb as triangles in flat limb coordinates, in metres:
    x = round the limb (0 at the front), y = down the limb. Used to wrap flat pieces on."""
    key = (limb, side_left)
    if key in _LEG_CHART:
        return _LEG_CHART[key]
    c = _body_coordinates()
    spec = LIMBS[limb]
    lo, hi = TIGHTS
    flat = np.stack([np.radians(c[spec["theta"]]) * spec["radius"], c[limb] * spec["length"]], axis=1)
    tris = []
    for f in human.base_mesh()[2]:
        if not all(lo <= v <= hi for v in f):
            continue
        if not all(c["part"][v] in spec["parts"] and c["left"][v] == side_left for v in f):
            continue
        for t in ((f[0], f[1], f[2]), (f[0], f[2], f[3])) if len(f) == 4 else ((f[0], f[1], f[2]),):
            th = c[spec["theta"]][list(t)]
            if th.max() - th.min() < 180.0:          # skip triangles that wrap round the back seam
                tris.append(t)
    tris = np.array(tris)
    _LEG_CHART[key] = (flat, tris)
    return flat, tris


LEG_RADIUS = 0.09     # metres per radian round the leg (about a mid-thigh radius)
LEG_LENGTH = 0.42     # metres per unit of the leg coordinate (about a thigh length)


def _rounded_rectangle(x0, x1, y0, y1, radius, step):
    """Outline of a rectangle with rounded corners, as points about `step` apart."""
    r = min(radius, (x1 - x0) / 2.0, (y1 - y0) / 2.0)
    pts = []
    corners = ((x1 - r, y0 + r, -90.0), (x1 - r, y1 - r, 0.0), (x0 + r, y1 - r, 90.0), (x0 + r, y0 + r, 180.0))
    for (cx, cy, start), (nx, ny, _) in zip(corners, corners[1:] + corners[:1]):
        arc = max(2, int(np.ceil(r * np.pi / 2.0 / step))) if r > 0 else 1
        for k in range(arc + 1):
            a = np.radians(start + 90.0 * k / arc)
            pts.append((cx + r * np.cos(a), cy + r * np.sin(a)))
        end = np.array(pts[-1])
        nxt = np.array((nx + r * np.cos(np.radians(start + 90.0)), ny + r * np.sin(np.radians(start + 90.0))))
        length = np.linalg.norm(nxt - end)
        for k in range(1, max(1, int(length / step))):
            pts.append(tuple(end + (nxt - end) * k / int(length / step)))
    out = [pts[0]]
    for p_ in pts[1:]:
        if np.hypot(p_[0] - out[-1][0], p_[1] - out[-1][1]) > step * 0.3:
            out.append(p_)
    return np.array(out)


def _inside_polygon(points, polygon):
    """Even-odd test: which 2D points lie inside the polygon."""
    x, y = points[:, 0], points[:, 1]
    inside = np.zeros(len(points), dtype=bool)
    for (x0, y0), (x1, y1) in zip(polygon, np.roll(polygon, -1, axis=0)):
        inside ^= ((y0 > y) != (y1 > y)) & (x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-12) + x0)
    return inside


def _wrap(points, side_left, limb="leg"):
    """Bind flat limb-coordinate points to the shell: (tri, weight) per point."""
    flat, tris = _leg_chart(side_left, limb)
    A, B, Cc = flat[tris[:, 0]], flat[tris[:, 1]], flat[tris[:, 2]]
    v0, v1 = B - A, Cc - A
    den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
    ok = np.abs(den) > 1e-10                     # a few leg triangles are flat in this chart
    tris, A, v0, v1, den = tris[ok], A[ok], v0[ok], v1[ok], den[ok]
    tri_out, w_out = [], []
    for p_ in points:
        d = p_ - A
        u = (d[:, 0] * v1[:, 1] - v1[:, 0] * d[:, 1]) / den
        v = (v0[:, 0] * d[:, 1] - d[:, 0] * v0[:, 1]) / den
        worst = np.minimum.reduce([u, v, 1.0 - u - v])
        best = int(np.argmax(worst))                 # containing triangle, or the nearest one
        uu, vv = u[best], v[best]
        w = np.clip(np.array([1.0 - uu - vv, uu, vv]), 0.0, None)
        tri_out.append(tris[best])
        w_out.append(w / w.sum())
    return np.array(tri_out), np.array(w_out)


def leg_patch(name, s=(0.18, 0.85), theta=(-35.0, 50.0), side="both", ease=0.012,
              thickness=0.0022, material=None, smooth_shell=0, snaps=(), corner=0.012,
              step=0.008, cut=None, puff=0.0, limb="leg"):
    """A flat piece lying on the leg: a patch pocket, a pocket flap, a reinforcement.

    Drawn as an exact rounded rectangle in flat leg coordinates and wrapped onto the leg,
    so its edges are straight and its corners clean at any body shape. (The first version
    cut it from the body mesh, whose 2.7 cm squares gave wavy edges and notched corners.)

    s: from-to along the leg (0 hip, 1 knee, 2 ankle). theta: from-to round the leg in
    degrees (0 front, 90 outside). side: "L", "R" or "both". Give it the trousers' ease
    plus a few millimetres so it sits on top. snaps: list of (s, theta) for press-studs.
    corner: corner radius in metres. step: mesh spacing in metres.
    cut: the trousers' leg shape (see trousers); pass the same one so the patch lies on them.
    puff: how far the middle of the patch bulges out, in metres (a filled pocket).
    """
    from mathutils import geometry as geo
    radius, length = LIMBS[limb]["radius"], LIMBS[limb]["length"]
    outline = _rounded_rectangle(np.radians(theta[0]) * radius, np.radians(theta[1]) * radius,
                                 s[0] * length, s[1] * length, corner, step)
    lo, hi = outline.min(axis=0), outline.max(axis=0)
    gx = np.arange(lo[0] + step, hi[0] - step * 0.5, step)
    gy = np.arange(lo[1] + step, hi[1] - step * 0.5, step * 0.866)
    grid = np.array([(x + (step * 0.5 if j % 2 else 0.0), y) for j, y in enumerate(gy) for x in gx])
    inside = _inside_polygon(grid, outline) if len(grid) else []
    keep = grid[inside] if len(grid) else np.zeros((0, 2))
    keep = keep[[np.min(np.linalg.norm(outline - k, axis=1)) > step * 0.55 for k in keep]] if len(keep) else keep
    points = np.concatenate([outline, keep])
    n = len(outline)
    out_v, _, out_f, orig, _, _ = geo.delaunay_2d_cdt([tuple(q) for q in points],
                                                     [(i, (i + 1) % n) for i in range(n)], [], 1, 1e-7)
    out_v = np.array([tuple(v) for v in out_v])
    faces = [tuple(f) for f in out_f if len(f) == 3
             and _inside_polygon(out_v[list(f)].mean(axis=0)[None, :], outline)[0]]
    pieces = []
    for side_left in {"L": (True,), "R": (False,), "both": (True, False)}[side]:
        tri, weight = _wrap(out_v, side_left, limb)
        f = faces if side_left else [tuple(reversed(t)) for t in faces]   # keep normals outward
        pieces.append((f, tri, weight, out_v))
    faces_all, tri_all, w_all, uv_all, base = [], [], [], [], 0
    for f, tri, weight, uv in pieces:
        faces_all += [tuple(base + i for i in t) for t in f]
        tri_all.append(tri); w_all.append(weight); uv_all.append(uv / materials.METRES_PER_UV)
        base += len(uv)
    spec = _garment(name, TIGHTS, None, ease, thickness,
                    material or materials.fabric((0.05, 0.06, 0.09), on="garment"),
                    skin_margin=None, smooth_shell=smooth_shell, snaps=snaps, cut=cut, puff=puff)
    spec["explicit"] = {"faces": faces_all, "tri": np.concatenate(tri_all),
                        "weight": np.concatenate(w_all), "uv": np.concatenate(uv_all)}
    return spec


def trousers(name="trousers", length=1.93, waist=0.20, ease=0.008, thickness=0.003,
             material=None, smooth_shell=0, cut=None):
    """cut: None for trousers that follow the leg; or a dict giving loose straight legs,
    e.g. {"thigh": 0.115, "knee": 0.095, "ankle": 0.085, "folds": 0.006} (radii and fold
    depth in metres)."""
    """length: 0.5 shorts, 1.0 knee, 1.93 ankle. waist: waistband height above the hip
    joint as a fraction of hip-to-neck."""
    c = _body_coordinates()
    field = waist - c["h"]
    field = np.where(np.isin(c["part"], ("leg", "foot")), np.minimum(field, length - c["leg"]), field)
    field = np.where(np.isin(c["part"], ("arm", "hand")), -FAR, field)
    return _garment(name, TIGHTS, field, ease, thickness, material or materials.denim(),
                    smooth_shell=smooth_shell, cut=cut)


def boots(name="boots", top_at=1.55, ease=0.007, thickness=0.004, material=None,
          smooth_shell=0, cut=None):
    """Soft boot or sock from the foot up to a point on the shin (1.0 knee, 2.0 ankle).
    No separate sole or heel."""
    c = _body_coordinates()
    field = np.where(np.isin(c["part"], ("leg", "foot")), c["leg"] - top_at, -FAR)
    return _garment(name, TIGHTS, field, ease, thickness,
                    material or materials.plain("Boot leather", (0.06, 0.05, 0.05), 0.45),
                    smooth_shell=smooth_shell, cut=cut)


def skirt(name="skirt", length=0.55, ease=0.004, thickness=0.003, material=None):
    """length: fraction of waist-to-ankle. 0.35 mini, 0.55 knee, 0.95 full."""
    c = _body_coordinates()
    return _garment(name, SKIRT, length - c["k"], ease, thickness,
                    material or materials.fabric((0.25, 0.27, 0.32), on="garment"), skin_margin=None)


def vest(name="vest", low=0.28, high=1.02, opening=0.045, armhole=(0.11, 0.075), ease=0.045,
         thickness=0.028, material=None, smooth_shell=0):
    """Padded vest over the chest, sides and back: open down the centre front (half-width
    `opening`, metres), open armholes, from torso height `low` up to `high` at the collar.
    armhole: half-height and half-depth in metres of the oval cut round each shoulder.
    (The first version cut armholes by the arm coordinate; with arms angled down most of
    the chest counted as arm and the vest shrank to two tabs.)"""
    c = _body_coordinates()
    vb = c["vb"]
    bones = rig.read_rig("default")
    field = np.minimum(c["h"] - low, high - c["h"])
    front = vb[:, 1] < vb[TIGHTS[0]:TIGHTS[1] + 1, 1].mean()
    field = np.where(front, np.minimum(field, (np.abs(vb[:, 0]) - opening) / 0.25), field)
    for sd in ("L", "R"):
        j = np.array(rig._position(bones[f"upperarm01.{sd}"]["head"], vb))
        lateral = np.abs(vb[:, 0]) > abs(j[0]) - 0.07
        oval = np.hypot((vb[:, 2] - (j[2] - 0.035)) / armhole[0], (vb[:, 1] - j[1]) / armhole[1])
        same_side = np.sign(vb[:, 0]) == np.sign(j[0])
        field = np.where(lateral & same_side, np.minimum(field, (oval - 1.0) * 0.1), field)
    field = np.where(np.isin(c["part"], ("torso", "neck")), field, -FAR)
    return _garment(name, TIGHTS, field, ease, thickness,
                    material or materials.fabric((0.60, 0.38, 0.12), on="garment"),
                    skin_margin=None, smooth_shell=smooth_shell)


def band(name="cuff", limb="arm", start=1.72, end=1.97, ease=0.04, thickness=0.02,
         material=None, smooth_shell=0, cut=None):
    """A ring round a limb between two limb coordinates: turned-back cuffs, boot tops."""
    c = _body_coordinates()
    field = np.minimum(c[limb] - start, end - c[limb]) * 0.3
    field = np.where(np.isin(c["part"], LIMBS[limb]["parts"]), field, -FAR)
    return _garment(name, TIGHTS, field, ease, thickness,
                    material or materials.plain("Shearling", (0.62, 0.55, 0.42), 0.95),
                    skin_margin=None, smooth_shell=smooth_shell, cut=cut)


TORSO_RADIUS = 0.15   # metres per radian round the torso (about the upper-chest radius)
TORSO_HEIGHT = 0.55   # metres per unit of torso height h (hip joint to base of neck)


def _torso_chart():
    """Torso and neck of the tights shell as flat triangles: x = angle round the body from
    the centre back (so the seam of the chart falls at the centre front), y = height."""
    if "torso" in _LEG_CHART:
        return _LEG_CHART["torso"]
    c = _body_coordinates()
    vb = c["vb"]
    bones = rig.read_rig("default")
    neck = np.array(rig._position(bones["neck01"]["head"], vb))
    psi = np.degrees(np.arctan2(vb[:, 0], vb[:, 1] - neck[1]))          # 0 back, +-180 front
    flat = np.stack([np.radians(psi) * TORSO_RADIUS, c["h"] * TORSO_HEIGHT], axis=1)
    lo, hi = TIGHTS
    tris = []
    for f in human.base_mesh()[2]:
        if not all(lo <= v <= hi and c["part"][v] in ("torso", "neck") for v in f):
            continue
        for t in ((f[0], f[1], f[2]), (f[0], f[2], f[3])) if len(f) == 4 else ((f[0], f[1], f[2]),):
            if np.ptp(psi[list(t)]) < 180.0:
                tris.append(t)
    _LEG_CHART["torso"] = (flat, np.array(tris), psi)
    return _LEG_CHART["torso"]


def _smooth_outline(points, rounds=3):
    """Round off the corners of a closed outline (Chaikin corner cutting)."""
    pts = np.asarray(points, dtype=float)
    for _ in range(rounds):
        nxt = np.roll(pts, -1, axis=0)
        pts = np.stack([0.75 * pts + 0.25 * nxt, 0.25 * pts + 0.75 * nxt], axis=1).reshape(-1, 2)
    return pts


def _resample(outline, step):
    out = []
    for p_, q in zip(outline, np.roll(outline, -1, axis=0)):
        n = max(1, int(np.ceil(np.linalg.norm(q - p_) / step)))
        out.extend(p_ + (q - p_) * k / n for k in range(n))
    return np.array(out)


def torso_patch(name, outline, ease, thickness, material, smooth_shell=0, step=0.009):
    """A flat piece drawn as an exact outline on the torso and wrapped onto it.
    outline: closed list of (angle from the centre back in degrees, torso height h)."""
    from mathutils import geometry as geo
    flat, tris, _ = _torso_chart()
    pts = np.array([(np.radians(a_) * TORSO_RADIUS, h_ * TORSO_HEIGHT) for a_, h_ in outline])
    pts = _resample(_smooth_outline(pts), step)
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    gx = np.arange(lo[0] + step, hi[0], step)
    gy = np.arange(lo[1] + step, hi[1], step * 0.866)
    grid = np.array([(x + (step * 0.5 if j % 2 else 0.0), y) for j, y in enumerate(gy) for x in gx])
    grid = grid[_inside_polygon(grid, pts)] if len(grid) else grid
    grid = grid[[np.min(np.linalg.norm(pts - g, axis=1)) > step * 0.55 for g in grid]] if len(grid) else grid
    allp = np.concatenate([pts, grid])
    n = len(pts)
    out_v, _, out_f, _, _, _ = geo.delaunay_2d_cdt([tuple(q) for q in allp],
                                                  [(i, (i + 1) % n) for i in range(n)], [], 1, 1e-7)
    out_v = np.array([tuple(v) for v in out_v])
    # Keep only triangles inside the outline. The triangulation also fills the outline's
    # convex hull; for the collar that bridged the V opening (a "bib") and, once smoothed,
    # blew up into large flat planes.
    faces = [tuple(f) for f in out_f if len(f) == 3
             and _inside_polygon(out_v[list(f)].mean(axis=0)[None, :], pts)[0]]
    # wrap: containing chart triangle, or the nearest one
    A, B, C = flat[tris[:, 0]], flat[tris[:, 1]], flat[tris[:, 2]]
    v0, v1 = B - A, C - A
    den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
    ok = np.abs(den) > 1e-10
    tris, A, v0, v1, den = tris[ok], A[ok], v0[ok], v1[ok], den[ok]
    tri_out, w_out = [], []
    for p_ in out_v:
        d = p_ - A
        u = (d[:, 0] * v1[:, 1] - v1[:, 0] * d[:, 1]) / den
        v = (v0[:, 0] * d[:, 1] - d[:, 0] * v0[:, 1]) / den
        best = int(np.argmax(np.minimum.reduce([u, v, 1.0 - u - v])))
        w = np.clip(np.array([1.0 - u[best] - v[best], u[best], v[best]]), 0.0, None)
        tri_out.append(tris[best]); w_out.append(w / w.sum())
    # outward normals: the chart runs right-handed when seen from outside on the back
    faces = [tuple(reversed(f)) for f in faces]
    spec = _garment(name, TIGHTS, None, ease, thickness, material, skin_margin=None, smooth_shell=smooth_shell)
    spec["explicit"] = {"faces": faces, "tri": np.array(tri_out), "weight": np.array(w_out),
                        "uv": out_v / materials.METRES_PER_UV}
    return spec


def lapel_collar(name="collar", tips=0.64, wings=0.80, back=0.86, neckline=1.02, throat=0.94,
                 tip_angle=150.0, ease=0.105, roll=0.02, thickness=0.036, material=None,
                 smooth_shell=0, soften=8, cushion=0.0, cushion_width=0.05):
    """A large turned-down shearling collar: a roll behind the neck, wings lying over the
    shoulders, and two rounded lapel points on the chest with a V opening between them.

    Heights are torso heights (0 hip joint, 1 base of neck): `tips` how far down the lapel
    points reach, `wings` the lower edge over the shoulders, `back` at the centre back,
    `neckline` the top edge, `throat` where the two lapels meet at the front. tip_angle:
    how far round from the centre back the lapel points sit (180 is the centre front).
    ease: height of the outer edge above the skin (must clear a vest). roll: extra height
    toward the neck, so the collar curls up there.
    (First collar: a band of equal depth, read as a fur tube. Second: cut from the body
    mesh with no V opening, gave a ragged bib.)"""
    right = [(0.0, back), (50.0, back - 0.02), (95.0, wings), (125.0, wings - 0.05),
             (tip_angle, tips), (tip_angle + 12.0, tips + 0.04), (172.0, throat), (178.0, neckline - 0.03),
             (150.0, neckline), (90.0, neckline + 0.01), (0.0, neckline + 0.01)]
    outline = right[:-1] + [(-a_, h_) for a_, h_ in reversed(right[1:-1])]
    c = _body_coordinates()
    lift = ease + roll * np.clip((c["h"] - (neckline - 0.16)) / 0.14, 0.0, 1.0)
    spec = torso_patch(name, outline, lift, thickness, material or materials.shearling(),
                       smooth_shell=smooth_shell)
    # Relax the crumpling where the neck shell bends sharply, with the edge held still.
    # (Plain smoothing, tried first, pulled the edge in unevenly and left it ragged.)
    spec["relax"] = int(soften)
    # cushion: how far the middle of each lobe swells out, in metres; with a rounded
    # profile this gives the thick, pillowy roll of real shearling instead of a flat flap.
    spec["puff"], spec["puff_width"], spec["puff_shape"] = cushion, cushion_width, 0.5
    return spec


def collar(name="collar", low=0.88, high=1.06, ease=0.022, thickness=0.02, material=None):
    """A thick rolled collar lying on the shoulders round the neck: the base for fur trim."""
    c = _body_coordinates()
    field = np.minimum(c["h"] - low, high - c["h"])
    field = np.where(np.isin(c["part"], ("torso", "neck")), field, -FAR)
    return _garment(name, TIGHTS, field, ease, thickness,
                    material or materials.plain("Collar base", (0.78, 0.72, 0.6), 0.9),
                    skin_margin=None, soften=4)


def helmet(name="helmet", ease=0.006, thickness=0.004, material=None, cheeks=False):
    """Close-fitting leather flying helmet: crown, back and sides of the head down past
    the ears, leaving the face open. Cut from the head's own surface, then smoothed so
    the ears do not show through."""
    c = _body_coordinates()
    vb, eye = c["vb"], c["eye"]
    crown = (vb[:, 2] - (eye[2] + 0.024)) / 0.03
    back = np.minimum((vb[:, 1] - (eye[1] + 0.085)) / 0.03, (vb[:, 2] - (eye[2] - 0.085)) / 0.03)
    field = np.maximum(crown, back)
    if cheeks:  # flaps down the sides of the face to the jaw, leaving eyes, nose and mouth open
        side = np.minimum((np.abs(vb[:, 0]) - 0.050) / 0.02, (vb[:, 2] - (eye[2] - 0.115)) / 0.03)
        field = np.maximum(field, side)
    on_head = (c["part"] == "neck") & (vb[:, 2] > eye[2] - 0.12)
    field = np.where(on_head, field, -FAR)
    return _garment(name, (0, human.BODY_VERTS - 1), field, ease, thickness,
                    material or materials.leather("Helmet leather", (0.10, 0.075, 0.055)),
                    skin_margin=0.3, soften=12)


def _round_rect(dx, dz, hx, hz, r):
    """Signed distance (metres) to a rounded rectangle: negative inside."""
    qx, qz = np.abs(dx) - (hx - r), np.abs(dz) - (hz - r)
    return np.hypot(np.maximum(qx, 0.0), np.maximum(qz, 0.0)) + np.minimum(np.maximum(qx, qz), 0.0) - r


_FACE = {}


def face_surface(base_verts, iterations=30):
    """Head and face of the body, smoothed (Taubin) so pieces laid on it (goggle masks, a
    moustache base) do not follow eyelids, nostrils and lip creases. Returns positions and
    normals for every base vertex, in Blender coordinates; only the head is smoothed."""
    key = (iterations, float(base_verts[::173].sum()))
    if key in _FACE:
        return _FACE[key]
    c = _body_coordinates()
    pos = human.to_blender(base_verts).copy()
    head = (np.arange(len(pos)) < human.BODY_VERTS) & (c["part"] == "neck")
    faces = [f for f in human.base_mesh()[2] if all(head[v] for v in f)]
    e = np.array(sorted({(min(a, b), max(a, b)) for f in faces for a, b in zip(f, f[1:] + f[:1])}))
    deg = np.zeros(len(pos)); np.add.at(deg, e[:, 0], 1.0); np.add.at(deg, e[:, 1], 1.0)
    free = deg > 0
    for k in range(2 * iterations):
        mean = np.zeros_like(pos)
        np.add.at(mean, e[:, 0], pos[e[:, 1]]); np.add.at(mean, e[:, 1], pos[e[:, 0]])
        step = 0.5 if k % 2 == 0 else -0.53
        pos[free] += step * (mean[free] / deg[free, None] - pos[free])
    normals = np.zeros_like(pos)
    for f in faces:
        n = np.cross(pos[f[1]] - pos[f[0]], pos[f[2]] - pos[f[0]])
        for v in f:
            normals[v] += n
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    _FACE[key] = (pos, normals, faces)
    return _FACE[key]


def _outline_from_sdf(sdf, centre, n=220, reach=0.15):
    """Zero contour of a 2D signed-distance function, found along rays from `centre`
    (the shape must be star-shaped from there). Returns points in order."""
    pts = []
    for a in np.linspace(0.0, 2 * np.pi, n, endpoint=False):
        d = np.array([np.cos(a), np.sin(a)])
        lo, hi = 0.0, reach
        for _ in range(40):
            mid = (lo + hi) / 2.0
            q = centre + d * mid
            if sdf(q[0], q[1]) < 0:
                lo = mid
            else:
                hi = mid
        pts.append(centre + d * lo)
    return np.array(pts)


def face_patch(name, outer, holes=(), ease=0.01, thickness=0.006, material=None, smooth=30,
               step=0.0035, puff=0.0, puff_width=0.006):
    """A piece drawn as exact outlines on the face and wrapped onto the smoothed face.
    outer, holes: closed polygons of (x, z) points in metres, in the unmorphed body's
    coordinates (x to the character's left, z up), seen from the front."""
    from mathutils import geometry as geo
    chart_pos, chart_n, faces_all = face_surface(human.base_mesh()[0], smooth)
    tris = []
    for f in faces_all:
        for t in ((f[0], f[1], f[2]), (f[0], f[2], f[3])) if len(f) == 4 else ((f[0], f[1], f[2]),):
            if chart_n[list(t), 1].mean() < -0.15:          # front-facing only: no overlaps in the chart
                tris.append(t)
    tris = np.array(tris)
    flat = chart_pos[:, [0, 2]]
    outer = _resample(np.asarray(outer, dtype=float), step)
    holes = [_resample(np.asarray(h, dtype=float), step) for h in holes]
    loops = [outer] + holes
    lo, hi = outer.min(axis=0), outer.max(axis=0)
    grid = np.array([(x + (step * 0.5 if j % 2 else 0.0), z) for j, z in enumerate(np.arange(lo[1] + step, hi[1], step * 0.866))
                     for x in np.arange(lo[0] + step, hi[0], step)])
    keep = _inside_polygon(grid, outer)
    for h in holes:
        keep &= ~_inside_polygon(grid, h)
    grid = grid[keep]
    edge_pts = np.concatenate(loops)
    grid = grid[[np.min(np.linalg.norm(edge_pts - g, axis=1)) > step * 0.55 for g in grid]]
    pts = np.concatenate(loops + [grid])
    constraints, base = [], 0
    for loop in loops:
        n = len(loop)
        constraints += [(base + i, base + (i + 1) % n) for i in range(n)]
        base += n
    out_v, _, out_f, _, _, _ = geo.delaunay_2d_cdt([tuple(q) for q in pts], constraints, [], 1, 1e-8)
    out_v = np.array([tuple(q) for q in out_v])
    faces = []
    for f in out_f:
        if len(f) != 3:
            continue
        cpt = out_v[list(f)].mean(axis=0)[None, :]
        if _inside_polygon(cpt, outer)[0] and not any(_inside_polygon(cpt, h)[0] for h in holes):
            faces.append(tuple(f))
    A, B, C = flat[tris[:, 0]], flat[tris[:, 1]], flat[tris[:, 2]]
    v0, v1 = B - A, C - A
    den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
    ok = np.abs(den) > 1e-12
    tris, A, v0, v1, den = tris[ok], A[ok], v0[ok], v1[ok], den[ok]
    tri_out, w_out = [], []
    for p_ in out_v:
        d = p_ - A
        u = (d[:, 0] * v1[:, 1] - v1[:, 0] * d[:, 1]) / den
        v = (v0[:, 0] * d[:, 1] - d[:, 0] * v0[:, 1]) / den
        best = int(np.argmax(np.minimum.reduce([u, v, 1.0 - u - v])))
        w = np.clip(np.array([1.0 - u[best] - v[best], u[best], v[best]]), 0.0, None)
        tri_out.append(tris[best]); w_out.append(w / w.sum())
    # front view, x to the left: counter-clockwise in (x, z) faces the viewer
    spec = _garment(name, (0, human.BODY_VERTS - 1), None, ease, thickness,
                    material or materials.plain(name, (0.04, 0.04, 0.045), 0.55), skin_margin=None)
    spec["explicit"] = {"faces": faces, "tri": np.array(tri_out), "weight": np.array(w_out),
                        "uv": out_v / materials.METRES_PER_UV}
    spec["surface"] = ("face", smooth)
    spec["puff"], spec["puff_width"], spec["puff_shape"] = puff, puff_width, 0.5
    return spec


def goggle_mask(eye_offset=0.032, frame_offset=0.035, lift=0.0, lens=(0.026, 0.020, 0.010),
                frame=(0.035, 0.029, 0.016), bridge_drop=0.006, blend=0.012, ease=0.008,
                thickness=0.007, puff=0.0025, puff_width=0.014, material=None):
    """The padded goggle mask as one smooth band: two rounded frames blended together over
    the nose (a soft V dipping over the bridge), with an opening for each lens. Drawn as
    exact outlines and laid on the smoothed face. (The first mask was cut from the face
    mesh and came out lumpy, with a blocky nose piece.)"""
    c = _body_coordinates()
    ez = c["eye"][2] + lift

    def smin(a, b, k):
        h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
        return b + (a - b) * h - k * h * (1.0 - h)

    def sdf(x, z):
        left = _round_rect(x - frame_offset, z - ez, *frame)
        right = _round_rect(x + frame_offset, z - ez, *frame)
        shape = smin(left, right, blend)
        # carve a soft arch over the nose from below and a shallow dip from above, leaving a
        # narrow bridge (the first version left a 4 cm tall bar across the nose)
        below = np.hypot(x / 0.016, (z - (ez - frame[1] - bridge_drop)) / 0.034) - 1.0
        above = np.hypot(x / 0.012, (z - (ez + frame[1] + 0.010)) / 0.016) - 1.0
        return max(shape, -below * 0.012, -above * 0.012)

    outer = _outline_from_sdf(sdf, np.array([0.0, ez + 0.008]))
    holes = []
    for sx in (1.0, -1.0):
        holes.append(_outline_from_sdf(lambda x, z: _round_rect(x - sx * eye_offset, z - ez, *lens),
                                       np.array([sx * eye_offset, ez]), n=120, reach=0.05))
    spec = face_patch("goggle_mask", outer, holes, ease=ease, thickness=thickness, puff=puff, puff_width=puff_width,
                      material=material or materials.plain("Goggle mask", (0.035, 0.037, 0.04), 0.55))
    spec["relax"] = 0
    return spec


def moustache_base(width=0.031, top=0.011, bottom=-0.0005, curve_top=6.0, curve_bottom=9.0,
                   material=None):
    """A thin dark layer under a strand moustache, so skin does not show between strands.
    Shape: a band on the upper lip, narrowing toward the ends and curving down at them.
    Measurements in metres relative to the centre of the upper lip."""
    from . import accessories
    lm = accessories.face_landmarks(human.base_mesh()[0])
    lip_z = float(lm["lip"][2])
    xs = np.linspace(-width, width, 60)
    upper = [(x, lip_z + top - curve_top * x * x) for x in xs]
    lower = [(x, lip_z + bottom - curve_bottom * x * x) for x in xs[::-1]]
    outline = _smooth_outline(np.array(upper + lower), rounds=2)
    # Laid on the unsmoothed face (smooth=0): on the smoothed one it dipped under the skin
    # in patches and showed as dark blotches on the cheeks.
    spec = face_patch("moustache_base", outline, ease=0.0018, thickness=0.0015, smooth=0, step=0.0025,
                      material=material or materials.plain("Moustache base", (0.012, 0.009, 0.007), 0.55))
    return spec


def flying_helmet(name="helmet", opening=(0.058, 0.083), drop=0.0375, lower=0.175, ease=0.007,
                  thickness=0.004, material=None, soften=12):
    """Leather flying hood: covers the crown, back, ears and neck, with an oval opening for
    the face reaching from the forehead to the chin. The flaps along the jaw meet under
    the chin. opening: half-width and half-height of the face oval in metres; drop: how
    far its centre sits below the eyes; lower: how far below the eyes the hood reaches."""
    c = _body_coordinates()
    vb, eye = c["vb"], c["eye"]
    front = vb[:, 1] < eye[1] + 0.05
    r = np.hypot(vb[:, 0] / opening[0], (vb[:, 2] - (eye[2] - drop)) / opening[1])
    face = np.where(front, (r - 1.0) * opening[0], 0.2)
    field = np.minimum(face, vb[:, 2] - (eye[2] - lower))
    field = np.where(c["part"] == "neck", field, -FAR)
    return _garment(name, (0, human.BODY_VERTS - 1), field, ease, thickness,
                    material or materials.leather("Helmet leather", (0.085, 0.088, 0.098)),
                    skin_margin=0.012, soften=soften)


def goggle_parts(eye_offset=0.032, frame_offset=0.037, lift=0.002, lens=(0.026, 0.0155, 0.009), frame=(0.036, 0.024, 0.014),
                 bridge=(0.010, 0.0065, 0.004), mask_ease=0.010, mask_thickness=0.007, puff=0.006,
                 lens_ease=0.016, mask_material=None, lens_material=None):
    """Goggles worn over the eyes, as two pieces cut from the face: the padded mask (two
    rounded frames joined over the nose, with a hole for each lens) and the two lenses.
    Sizes are half-width, half-height and corner radius in metres, measured on the face."""
    c = _body_coordinates()
    vb, eye = c["vb"], c["eye"]
    x, z = vb[:, 0], vb[:, 2] - (eye[2] + lift)
    face_front = (vb[:, 1] < eye[1] + 0.012) & (np.abs(x) < 0.095) & (c["part"] == "neck")
    lens_d = np.minimum(_round_rect(x - eye_offset, z, *lens), _round_rect(x + eye_offset, z, *lens))
    # Frames are centred a little outside the eyes so they do not meet over the nose (with
    # both centred on the eyes, their overlap covered the top of the nose like a block).
    outer = np.minimum.reduce([_round_rect(x - frame_offset, z, *frame), _round_rect(x + frame_offset, z, *frame),
                               _round_rect(x, z - bridge[2], bridge[0], bridge[1], 0.004)])   # bridge: half-width, half-height, raise
    mask_field = np.where(face_front, np.minimum(-outer, lens_d), -FAR)
    lens_field = np.where(face_front, -lens_d + 0.0015, -FAR)          # tucked just under the mask
    mask = _garment("goggle_mask", (0, human.BODY_VERTS - 1), mask_field, mask_ease, mask_thickness,
                    mask_material or materials.plain("Goggle mask", (0.035, 0.037, 0.04), 0.55), skin_margin=None)
    mask["puff"], mask["puff_width"], mask["puff_shape"] = puff, 0.006, 0.5
    mask["relax"] = 6
    glass = _garment("goggle_lenses", (0, human.BODY_VERTS - 1), lens_field, lens_ease, 0.0015,
                     lens_material or materials.glass("Goggle glass", thin=True), skin_margin=None)
    glass["relax"] = 30                                                  # nearly flat across the eye socket
    return mask, glass


# ------------------------------------------------------------------ building

def _cut(garment):
    """Faces and vertex bindings of a garment, with straddling faces trimmed to the edge.

    Returns (faces as tuples of garment-vertex indices, tri[n,3], weight[n,3],
    per-face base vertex tuples for UV lookup, per-face per-corner slide info).
    """
    lo, hi = garment["shell"]
    field = garment["field"]
    shell_faces = [f for f in human.base_mesh()[2] if all(lo <= v <= hi for v in f)]
    inside = field > 0
    # For each outside vertex, the inside neighbour (along a mesh edge) it slides toward:
    # the one with the steepest change, i.e. the edge most square to the garment's edge.
    slide = {}
    for f in shell_faces:
        for i, v in enumerate(f):
            for w in (f[i - 1], f[(i + 1) % len(f)]):
                if not inside[v] and inside[w]:
                    if v not in slide or field[w] - field[v] > field[slide[v]] - field[v]:
                        slide[v] = w
    index, tri, weight, faces, sources = {}, [], [], [], []

    def vertex(v):
        if v not in index:
            index[v] = len(tri)
            if inside[v]:
                tri.append((v, v, v)); weight.append((1.0, 0.0, 0.0))
            else:
                w = slide[v]
                t = float(np.clip(field[w] / (field[w] - field[v]), 0.05, 1.0))
                tri.append((w, v, v)); weight.append((1.0 - t, t, 0.0))
        return index[v]

    for f in shell_faces:
        n_in = sum(inside[v] for v in f)
        if n_in == len(f) or (n_in >= 1 and all(inside[v] or v in slide for v in f)):
            faces.append(tuple(vertex(v) for v in f))
            sources.append(f)
    return faces, np.array(tri, dtype=int), np.array(weight), sources


def coordinate(binding, name):
    """A body coordinate ("h", "arm", "leg") at each vertex of a built garment."""
    values = _body_coordinates()[name]
    return (values[binding["tri"]] * binding["weight"]).sum(axis=1)


def part(binding):
    """Body part name at each vertex of a built garment."""
    return _body_coordinates()["part"][binding["tri"][:, 0]]


def _split_panels(faces, tri, weight, sources, spec):
    """Cut a garment into panels and return what is needed to sew them back together.

    Panels: left and right sleeve, and the body split down the centre front only (the
    back stays in one piece). Where panels meet, each gets its own copy of the shared
    vertices, and a loose edge between the copies acts as a sewing spring in the cloth
    simulation. The centre front is sewn only below spec["open_above"] (a torso height);
    above it the two edges are moved apart to form an opening.

    Returns (faces, tri, weight, nudge[n,3] in metres, sewing edges).
    """
    c = _body_coordinates()
    vb, part = c["vb"], c["part"]
    y_mid = vb[TIGHTS[0]:TIGHTS[1] + 1, 1].mean()

    def panel(src):
        left = vb[list(src), 0].mean() > 0
        if all(part[v] in ("arm", "hand") for v in src):
            return "SL" if left else "SR"
        return "TL" if left else "TR"

    face_panel = [panel(src) for src in sources]
    users = {}
    for f, p in zip(faces, face_panel):
        for gv in f:
            users.setdefault(gv, set()).add(p)
    height = (c["h"][tri] * weight).sum(axis=1)
    new_tri, new_weight = [tuple(t) for t in tri], [tuple(w) for w in weight]
    nudge = [np.zeros(3) for _ in tri]
    remap, sew = {}, []
    for gv, panels in users.items():
        b = tri[gv][0]
        front_mid = abs(vb[b][0]) < 1e-3 and vb[b][1] < y_mid
        torso = sorted(p for p in panels if p[0] == "T")
        classes = []
        if len(torso) == 2 and front_mid:
            classes += [[torso[0]], [torso[1]]]
        elif torso:
            classes.append(torso)
        classes += [[p] for p in sorted(panels) if p[0] == "S"]
        copies = []
        for k, cls in enumerate(classes):
            if k == 0:
                idx = gv
            else:
                idx = len(new_tri)
                new_tri.append(tuple(tri[gv])); new_weight.append(tuple(weight[gv])); nudge.append(np.zeros(3))
            for p in cls:
                remap[(gv, p)] = idx
            copies.append(idx)
        if len(torso) == 2 and front_mid:
            gap = 0.003 + 0.14 * max(0.0, height[gv] - spec["open_above"])
            nudge[copies[0]] = np.array([gap, 0.0, 0.0])     # TL copy moves to the wearer's left
            nudge[copies[1]] = np.array([-gap, 0.0, 0.0])
            if height[gv] <= spec["open_above"]:
                sew.append((copies[0], copies[1]))
            sew += [(copies[0], other) for other in copies[2:]]
        else:
            sew += [(copies[0], other) for other in copies[1:]]
    new_faces = [tuple(remap[(gv, p)] for gv in f) for f, p in zip(faces, face_panel)]
    return new_faces, np.array(new_tri, dtype=int), np.array(new_weight), np.array(nudge), sew


_SURFACES = {}


def _straight_legs(pos, base_verts, cut):
    """Push each leg's cross-section out to a wide, nearly straight tube, as loose flight
    trousers hang, and add soft folds. cut: dict with radii in metres at thigh, knee and
    ankle, and fold amplitude. The legs are kept from crossing the body's centre plane."""
    c = _body_coordinates()
    bones = rig.read_rig("default")
    vb = human.to_blender(base_verts)
    joint = lambda name: np.array(rig._position(bones[name]["head"], vb))
    out = pos.copy()
    for sd, sign, mask in (("L", 1.0, c["left"]), ("R", -1.0, ~c["left"])):
        hip, knee, ankle = joint(f"upperleg01.{sd}"), joint(f"lowerleg01.{sd}"), joint(f"foot.{sd}")
        rows = np.nonzero(mask & (c["part"] == "leg"))[0]
        s_v = c["leg"][rows]
        upper = s_v <= 1.0
        base = np.where(upper[:, None], hip, knee)
        axis = np.where(upper[:, None], knee - hip, ankle - knee)
        axis /= np.linalg.norm(axis, axis=1, keepdims=True)
        rel = pos[rows] - base
        along = (rel * axis).sum(axis=1)
        radial = rel - along[:, None] * axis
        r = np.linalg.norm(radial, axis=1)
        d = radial / np.maximum(r, 1e-9)[:, None]
        target = np.interp(s_v, [0.0, 0.15, 1.0, 1.9, 2.2],
                           [cut["thigh"] * 0.9, cut["thigh"], cut["knee"], cut["ankle"], cut["ankle"]])
        centre_x = (base + along[:, None] * axis)[:, 0]
        toward_mid = (d[:, 0] * sign) < -0.05
        limit = np.where(toward_mid, (np.abs(centre_x) - 0.012) / np.maximum(-d[:, 0] * sign, 0.05), 9.0)
        target = np.minimum(target, np.maximum(limit, r))
        width = 0.012
        grown = r + width * np.log1p(np.exp((target - r) / width))          # smooth maximum
        grown = r + (grown - r) * np.clip(s_v / 0.18, 0.0, 1.0)             # blend into the seat
        theta = np.radians(c["theta"][rows])
        x, y = theta * LEG_RADIUS, s_v * LEG_LENGTH
        folds = (np.sin(2 * np.pi * (y / 0.15 + x * 0.35 / 0.15) + 0.7)
                 + 0.7 * np.sin(2 * np.pi * (y / 0.11 - x * 0.5 / 0.11) + 2.1)
                 + 0.5 * np.sin(2 * np.pi * (y / 0.19 + 0.3)))
        weight = 0.35 + np.exp(-((s_v - 1.0) / 0.25) ** 2) + np.clip((s_v - 1.55) / 0.35, 0.0, 1.0)
        grown = grown + cut.get("folds", 0.0) * weight * folds / 2.2
        out[rows] = base + along[:, None] * axis + d * grown[:, None]
    return out


def shell_surface(base_verts, iterations, cut=None):
    """Positions and normals of the whole tights shell (Blender coordinates), optionally
    smoothed so muscle definition does not show through loose garments. Every garment
    cut from the shell with the same setting lies on the same surface, so pockets sit
    exactly on trousers. Taubin smoothing: alternating shrink and inflate steps keep the
    size from collapsing the way plain averaging would."""
    key = (iterations, base_verts.shape, float(base_verts[::211].sum()),
           tuple(sorted(cut.items())) if cut else None)
    if key in _SURFACES:
        return _SURFACES[key]
    pos = human.to_blender(base_verts).copy()
    if cut:
        pos = _straight_legs(pos, base_verts, cut)
    lo, hi = TIGHTS
    faces = [f for f in human.base_mesh()[2] if all(lo <= v <= hi for v in f)]
    edges = {(min(a, b), max(a, b)) for f in faces for a, b in zip(f, f[1:] + f[:1])}
    e = np.array(sorted(edges))
    degree = np.zeros(len(pos))
    np.add.at(degree, e[:, 0], 1.0)
    np.add.at(degree, e[:, 1], 1.0)
    shell = degree > 0
    for k in range(2 * iterations):
        mean = np.zeros_like(pos)
        np.add.at(mean, e[:, 0], pos[e[:, 1]])
        np.add.at(mean, e[:, 1], pos[e[:, 0]])
        step = 0.5 if k % 2 == 0 else -0.53
        pos[shell] += step * (mean[shell] / degree[shell, None] - pos[shell])
    if iterations:
        # Loose garments bridge the crotch with fabric instead of following the body into
        # it. Extra averaging there flattens the creases a tight shell would show. (Taubin
        # smoothing alone left them: the creases are larger than its reach.)
        c = _body_coordinates()
        zone = np.zeros(len(pos))
        low = np.clip((0.10 - c["h"]) / 0.15, 0.0, 1.0)
        zone[c["part"] == "torso"] = low[c["part"] == "torso"]
        inner_leg = (c["part"] == "leg") & (np.abs(c["theta"]) > 95.0)
        zone[inner_leg] = np.maximum(zone[inner_leg], np.clip((0.25 - c["leg"][inner_leg]) / 0.25, 0.0, 1.0))
        zone = np.where(shell, zone, 0.0)[:, None] * 0.5
        for _ in range(4 * iterations):
            mean = np.zeros_like(pos)
            np.add.at(mean, e[:, 0], pos[e[:, 1]])
            np.add.at(mean, e[:, 1], pos[e[:, 0]])
            pos[shell] += zone[shell] * (mean[shell] / degree[shell, None] - pos[shell])
    normals = np.zeros_like(pos)
    for f in faces:
        n = np.cross(pos[f[1]] - pos[f[0]], pos[f[2]] - pos[f[0]])
        for v in f:
            normals[v] += n
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    _SURFACES[key] = (pos, normals)
    return pos, normals


def edge_attributes(verts, faces):
    """Per vertex: distance to the nearest open edge of the mesh (hems, pocket edges and,
    on garments cut into panels, seams) and how far along that edge it is. Stored on the
    mesh so stitching can be drawn by the material; both survive cloth simulation,
    thickness and smoothing because Blender carries mesh attributes through modifiers."""
    count = {}
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            key = (min(a, b), max(a, b))
            count[key] = count.get(key, 0) + 1
    boundary = [k for k, c in count.items() if c == 1]
    if not boundary:
        return np.full(len(verts), 1.0), np.zeros(len(verts))
    nbr = {}
    for a, b in boundary:
        nbr.setdefault(a, []).append(b)
        nbr.setdefault(b, []).append(a)
    used, seg_a, seg_b, seg_start = set(), [], [], []
    for a0, b0 in boundary:
        if (a0, b0) in used:
            continue
        along, prev, cur = 0.0, a0, b0
        used.add((a0, b0))
        seg_a.append(a0); seg_b.append(b0); seg_start.append(along)
        along += float(np.linalg.norm(verts[b0] - verts[a0]))
        while True:
            nxt = next((n for n in nbr[cur] if n != prev and (min(cur, n), max(cur, n)) not in used), None)
            if nxt is None:
                break
            used.add((min(cur, nxt), max(cur, nxt)))
            seg_a.append(cur); seg_b.append(nxt); seg_start.append(along)
            along += float(np.linalg.norm(verts[nxt] - verts[cur]))
            prev, cur = cur, nxt
    A, B = verts[np.array(seg_a)], verts[np.array(seg_b)]
    start = np.array(seg_start)
    dist = np.empty(len(verts))
    pos = np.empty(len(verts))
    for lo in range(0, len(verts), 512):
        P = verts[lo:lo + 512, None, :]
        d = B - A
        t = np.clip(((P - A) * d).sum(-1) / np.maximum((d * d).sum(-1), 1e-12), 0.0, 1.0)
        gap = np.linalg.norm(P - (A + t[..., None] * d), axis=-1)
        best = gap.argmin(axis=1)
        rows = np.arange(len(best))
        dist[lo:lo + 512] = gap[rows, best]
        pos[lo:lo + 512] = start[best] + t[rows, best] * np.linalg.norm(d[best], axis=-1)
    return dist, pos


def _vertex_normals(verts, faces):
    normals = np.zeros_like(verts)
    for f in faces:
        n = np.cross(verts[f[1]] - verts[f[0]], verts[f[2]] - verts[f[0]])
        for v in f:
            normals[v] += n
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    return normals / np.maximum(length, 1e-12)


def _vertex_normals_welded(verts, faces):
    """Vertex normals where vertices at the same position share one normal."""
    key = {}
    group = np.array([key.setdefault(tuple(np.round(v, 6)), len(key)) for v in verts])
    normals = np.zeros((len(key), 3))
    for f in faces:
        n = np.cross(verts[f[1]] - verts[f[0]], verts[f[2]] - verts[f[0]])
        for v in f:
            normals[group[v]] += n
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    return (normals / np.maximum(length, 1e-12))[group]


def build(scene, base_verts, garment, name, parent=None):
    """Create the garment object on a given (morphed) body. Returns (object, binding)."""
    all_bl = human.to_blender(base_verts)
    _, uvs, all_faces, all_face_uvs = human.base_mesh()
    uv_of = {f: fu for f, fu in zip(all_faces, all_face_uvs)}
    explicit = garment.get("explicit")
    if explicit:
        faces, tri, weight, sources = explicit["faces"], explicit["tri"], explicit["weight"], None
    else:
        faces, tri, weight, sources = _cut(garment)
    sewing = []
    nudge = None
    if garment.get("panels"):
        faces, tri, weight, nudge, sewing = _split_panels(faces, tri, weight, sources, garment["panels"])
    ease = garment["ease"]
    if not np.isscalar(ease):                     # per-base-vertex ease (e.g. baggy_ease)
        ease = (np.asarray(ease)[tri] * weight).sum(axis=1)[:, None]
    if tuple(garment["shell"]) == TIGHTS:
        # Garments on the tights shell take position and normal from the (optionally
        # smoothed) whole shell, so separate pieces line up exactly.
        surf, normals = shell_surface(base_verts, garment.get("smooth_shell", 0), garment.get("cut"))
        verts = (surf[tri] * weight[:, :, None]).sum(axis=1)
        n = (normals[tri] * weight[:, :, None]).sum(axis=1)
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    elif garment.get("surface") and garment["surface"][0] == "face":
        surf, normals, _ = face_surface(base_verts, garment["surface"][1])
        verts = (surf[tri] * weight[:, :, None]).sum(axis=1)
        n = (normals[tri] * weight[:, :, None]).sum(axis=1)
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    else:
        verts = (all_bl[tri] * weight[:, :, None]).sum(axis=1)
        # Normals are taken before panels are moved apart, so both copies of a seam
        # vertex get the same push outward.
        n = _vertex_normals_welded(verts, faces)
    if garment.get("puff"):                       # a filled pocket or a cushion bulges in the middle
        inner, _ = edge_attributes(verts, faces)
        reach = garment.get("puff_width", 0.035)
        ease = ease + garment["puff"] * np.clip(inner / reach, 0.0, 1.0)[:, None] ** garment.get("puff_shape", 0.7)
    verts = verts + ease * n
    if garment.get("relax"):
        # Smooth the piece with its outline held still. Done here rather than with
        # Blender's Laplacian Smooth modifier, which blew this mesh apart into spikes.
        edges = {(min(a, b), max(a, b)) for f in faces for a, b in zip(f, f[1:] + f[:1])}
        count = {}
        for f in faces:
            for a, b in zip(f, f[1:] + f[:1]):
                key = (min(a, b), max(a, b)); count[key] = count.get(key, 0) + 1
        rim = {v for k, c in count.items() if c == 1 for v in k}
        e = np.array(sorted(edges))
        deg = np.zeros(len(verts)); np.add.at(deg, e[:, 0], 1.0); np.add.at(deg, e[:, 1], 1.0)
        free = np.array([i not in rim and deg[i] > 0 for i in range(len(verts))])
        for k in range(2 * garment["relax"]):
            mean = np.zeros_like(verts)
            np.add.at(mean, e[:, 0], verts[e[:, 1]]); np.add.at(mean, e[:, 1], verts[e[:, 0]])
            step = 0.5 if k % 2 == 0 else -0.53
            verts[free] += step * (mean[free] / deg[free, None] - verts[free])
    if nudge is not None:
        verts = verts + nudge

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts.tolist(), sewing, faces)
    # UVs: a slid corner takes the UV part-way along the same edge, when that edge is in
    # this face; otherwise it keeps its own UV (a small stretch at the hem).
    flat = []
    if explicit:
        flat = [c for face in faces for v in face for c in explicit["uv"][v]]
    for face, src in zip(faces, sources or []):
        for corner, (gv, bv) in enumerate(zip(face, src)):
            uv = uvs[uv_of[src][corner]]
            w0 = tri[gv][0]
            if weight[gv][1] > 0 and w0 in src:
                uv_in = uvs[uv_of[src][src.index(w0)]]
                uv = uv_in + weight[gv][1] * (uv - uv_in)
            flat.extend(uv)
    mesh.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array(flat))
    dist, along = edge_attributes(verts, faces)
    mesh.attributes.new("edge_dist", "FLOAT", "POINT").data.foreach_set("value", dist.astype(np.float32))
    mesh.attributes.new("edge_along", "FLOAT", "POINT").data.foreach_set("value", along.astype(np.float32))
    mesh.update()
    mesh.shade_smooth()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    mesh.materials.append(garment["material"])
    if garment.get("soften"):
        relax = obj.modifiers.new("Soften", "SMOOTH")
        relax.factor = 0.7
        relax.iterations = garment["soften"]
    solid = obj.modifiers.new("Thickness", "SOLIDIFY")
    solid.thickness = garment["thickness"]
    solid.offset = 1.0  # grow outward, so the inner face stays clear of the skin
    smooth = obj.modifiers.new("Subdivision", "SUBSURF")
    smooth.levels, smooth.render_levels = 1, 2
    if parent is not None:
        obj.parent = parent
    return obj, {"tri": tri, "weight": weight, "delete": garment["delete"],
                 "rest": verts, "normals": n}


def build_extras(scene, base_verts, garment, name, parent=None):
    """Hardware that belongs to a garment: press-studs at the (s, theta) places listed in
    garment["snaps"], on every leg the garment covers. Each stud is bound to the nearest
    garment vertex, so it bends with the leg like the cloth it sits on."""
    if not garment.get("snaps"):
        return []
    import bmesh
    c = _body_coordinates()
    if garment.get("explicit"):
        tri, weight = garment["explicit"]["tri"], garment["explicit"]["weight"]
    else:
        _, tri, weight, _ = _cut(garment)
    s_v = (c["leg"][tri] * weight).sum(axis=1)
    t_v = (c["theta"][tri] * weight).sum(axis=1)
    left_v = c["left"][tri[:, 0]]
    surf, normals = shell_surface(base_verts, garment.get("smooth_shell", 0), garment.get("cut"))
    ease = garment["ease"]
    ease_v = (np.asarray(ease)[tri] * weight).sum(axis=1) if not np.isscalar(ease) else np.full(len(tri), ease)
    pos = (surf[tri] * weight[:, :, None]).sum(axis=1)
    nrm = (normals[tri] * weight[:, :, None]).sum(axis=1)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    metal = materials.metal("Press-stud", (0.30, 0.27, 0.22), 0.35)
    made = []
    for side in (True, False):
        rows = np.nonzero(left_v == side)[0]
        if not len(rows):
            continue
        for k, (s_at, t_at) in enumerate(garment["snaps"]):
            gap = np.hypot((s_v[rows] - s_at) * 0.42, np.radians(t_v[rows] - t_at) * 0.09)
            near = rows[np.argsort(gap)[:4]]
            w = 1.0 / np.maximum(np.sort(gap)[:4], 1e-4)
            w /= w.sum()
            p = (pos[near] * w[:, None]).sum(axis=0)
            n = (nrm[near] * w[:, None]).sum(axis=0)
            n /= np.linalg.norm(n)
            centre = p + n * ((ease_v[near] * w).sum() + garment["thickness"] + 0.0012)
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=0.0062)
            for v in bm.verts:                       # flatten into a dome along the normal
                local = np.array(v.co)
                v.co = tuple(centre + local - n * (local @ n) * 0.62)
            mesh = bpy.data.meshes.new(f"{name}_stud{k}")
            bm.to_mesh(mesh)
            bm.free()
            mesh.shade_smooth()
            mesh.materials.append(metal)
            obj = bpy.data.objects.new(mesh.name, mesh)
            scene.collection.objects.link(obj)
            if parent is not None:
                obj.parent = parent
            nearest = near[0]
            count = len(mesh.vertices)
            made.append((obj, {"tri": np.tile(tri[nearest], (count, 1)),
                               "weight": np.tile(weight[nearest], (count, 1)), "delete": set()}))
    return made
