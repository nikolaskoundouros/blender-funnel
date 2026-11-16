"""Camera move buttons: each move is built around OUR subject and room, with timing measured from a reference.

A move returns one camera state per frame: (eye, rotation matrix, lens), the same form run 021 keys.
The camera always circles, pushes or turns relative to a subject point, so it cannot drift onto empty
walls the way copied 2D readings did (run 021, 14 Nov 2026). Defaults are measured on the reference
"My Mom Cracked The Dinosaur" (clip analyzer + COLMAP solve, run 021 review.md):
  pull_out   size -68% in 0.33 s                   (0.00 s, the boy)
  orbit      about 92 deg round the subject, rising 17% of its distance, over 1.3 s, slowing at 23%
             and 75% of the move and nearly stopping at 92-100% (0.3-1.6 s, the boy)
  push       size +289% in 0.77 s                  (4.07 s, Mom, "This is a T-Rex")
  reveal     size -77% in 1.03 s, aim slides to a second subject (8.0 s, bone to the boy)
  crane      size -29% with the view tilting up, the camera rising (11.3 s, toward the T-Rex)
  whip       one fast turn, about 0.1 s, eased     (1.9 s)
Size in frame goes as 1 / distance, so "size x k" = "distance / k".
Checks (check_states): the subject stays inside the frame, the camera never sits inside geometry (a ray
from the subject to the camera must reach it; if something is in the way the camera is moved in front
of it), and the camera is never fully still (every frame moves or turns a little).
"""
import math

from mathutils import Matrix, Vector

UP = Vector((0.0, 0.0, 1.0))
LENS = 36.1                                   # mm, vertical 36 mm sensor: the reference's solved lens
FRAME_H = {"ECU": 0.32, "CU": 0.55, "MED": 1.2, "WIDE": 3.6}   # metres of subject height the frame shows


def vfov(lens=LENS):
    return 2 * math.atan(18.0 / lens)


def distance_for(size, lens=LENS):
    """Camera distance that shows FRAME_H[size] metres top to bottom."""
    return FRAME_H[size] / (2 * math.tan(vfov(lens) / 2))


def distance_for_pair(a, b, lens=LENS, fill=0.8):
    """Distance at which two subjects a and b, side by side, fit across `fill` of the (narrow, 9:16) frame width.
    Run 021: a two-shot at a 'medium' distance put both people outside a vertical frame."""
    hfov = 2 * math.atan(18.0 * 9 / 16 / lens)
    return (a - b).length / (2 * math.tan(fill * hfov / 2))


def progress(n, floor=0.15, slows=()):
    """0..1 over n frames: eased in and out, never fully stopped (floor = share of plain constant speed).
    slows: (where 0..1, how deep 0..1, how wide 0..1) dips in speed, like the reference's pauses."""
    if n <= 1:
        return [1.0] * n
    speed = []
    for k in range(n):
        u = (k + 0.5) / n
        s = (1 - floor) * 30 * u * u * (1 - u) * (1 - u) + floor          # derivative of smootherstep + floor
        for at, depth, width in slows:
            s *= 1 - depth * math.exp(-((u - at) / width) ** 2)
        speed.append(max(s, 1e-3))
    total, acc, out = sum(speed), 0.0, []
    for s in speed:
        acc += s
        out.append(acc / total)
    return out


def look(eye, target, roll=0.0):
    f = (target - eye).normalized()
    r = f.cross(UP)
    r = r.normalized() if r.length > 1e-6 else Vector((1.0, 0.0, 0.0))
    u = r.cross(f)
    if roll:
        R = Matrix.Rotation(math.radians(roll), 3, f)
        r, u = R @ r, R @ u
    return Matrix((r, u, -f)).transposed()


def around(target, az_deg, el_deg, dist):
    a, e = math.radians(az_deg), math.radians(el_deg)
    return target + Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e))) * dist


def hold(target, az, el, dist, n, drift=0.04, lens=LENS):
    """No big move: a slow push of `drift` (share of distance) so the camera is never still."""
    p = progress(n, floor=1.0)
    return [(around(target, az, el, dist * (1 - drift * t)), look(around(target, az, el, dist * (1 - drift * t)), target), lens) for t in p]


def push(target, az, el, d0, d1, n, slows=(), lens=LENS, aim_to=None):
    """Dolly along the line to the subject from distance d0 to d1 (pull out: d1 > d0). aim_to slides the aim."""
    out = []
    for t in progress(n, slows=slows):
        aim = target.lerp(aim_to, t) if aim_to is not None else target
        eye = around(aim, az, el, d0 + (d1 - d0) * t)
        out.append((eye, look(eye, aim), lens))
    return out


def orbit(target, az0, el0, d0, n, angle=92.0, rise=0.17, d1=None, slows=((0.23, 0.6, 0.05), (0.75, 0.4, 0.05), (0.96, 0.9, 0.06)), lens=LENS):
    """Circle the subject by `angle` degrees (+ = counter-clockwise from above), rising by `rise` x distance."""
    d1 = d0 if d1 is None else d1
    out = []
    for t in progress(n, slows=slows):
        d = d0 + (d1 - d0) * t
        el = math.degrees(math.asin(max(-0.95, min(0.95, math.sin(math.radians(el0)) + rise * t))))
        eye = around(target, az0 + angle * t, el, d)
        out.append((eye, look(eye, target), lens))
    return out


def crane(target, az, el0, el1, d0, d1, n, aim_to=None, lens=LENS):
    """Rise from elevation el0 to el1 while moving from d0 to d1; aim_to tilts the view toward a reveal."""
    out = []
    for t in progress(n):
        aim = target.lerp(aim_to, t) if aim_to is not None else target
        eye = around(target, az, el0 + (el1 - el0) * t, d0 + (d1 - d0) * t)
        out.append((eye, look(eye, aim), lens))
    return out


def whip(eye, aim0, aim1, n, lens=LENS):
    """One fast turn in place from aim0 to aim1 (blur comes from the render's motion blur)."""
    out = []
    d0, d1 = (aim0 - eye).normalized(), (aim1 - eye).normalized()
    for t in progress(n, floor=0.05):
        d = d0.slerp(d1, t) if d0.angle(d1) > 1e-4 else d0
        out.append((eye.copy(), look(eye, eye + d), lens))
    return out


def check_states(scene, states, subject, clear=0.15, keep_off=0.06, see_through=(), near=0.10):
    """The four built-in checks, fixing what can be fixed. Returns (states, report).

    1 inside geometry: a ray from just outside the subject toward the camera; if it hits something before
      the camera, the camera moves to `keep_off` m in front of the hit, on the same line. Objects named in
      see_through (the characters) do not count: a person between camera and subject is a framing choice
      (over-the-shoulder), not a wall. Run 021: counting Mom as a wall wrecked the over-her-back shot.
    2 subject in frame: the subject's angle off the view centre must stay inside 45% of the frame width.
    3 never still: each frame must move at least 1 mm or turn at least 0.05 deg.
    4 too close: nothing within `near` m of the lens in any of 6 directions (run 021: the reveal passed
      through the rope, a thin thing the subject-to-camera ray missed). Counted, not fixed: the plan moves."""
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    out, moved, off, still, too_close = [], 0, 0, 0, 0
    prev = None
    for eye, rot, lens in states:
        to_cam = eye - subject
        dist = to_cam.length
        if dist > clear + 0.02:
            d = to_cam.normalized()
            start, left = subject + d * clear, dist - clear
            while True:
                hit, loc, _n, _i, obj, _m = scene.ray_cast(dg, start, d, distance=left)
                if not hit or obj is None or obj.name not in see_through:
                    break
                step = (loc - start).length + 0.01
                start, left = loc + d * 0.01, left - step
                if left <= 0:
                    hit = False
                    break
            if hit:
                eye = loc - d * keep_off
                rot = look(eye, subject) if (subject - eye).length > 0.05 else rot
                moved += 1
        hfov = 2 * math.atan(18.0 * 9 / 16 / lens)
        view = -(rot.col[2].xyz)
        if view.angle(subject - eye) > 0.45 * hfov:
            off += 1
        if prev is not None:
            pe, pr = prev
            if (eye - pe).length < 0.001 and math.degrees(view.angle(-(pr.col[2].xyz))) < 0.05:
                still += 1
        for dvec in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            h2, _l, _n, _i, o2, _m = scene.ray_cast(dg, eye, Vector(dvec), distance=near)
            if h2 and (o2 is None or o2.name not in see_through):
                too_close += 1
                break
        prev = (eye, rot)
        out.append((eye, rot, lens))
    return out, dict(moved_out_of_geometry=moved, subject_out_of_frame=off, still_frames=still, too_close=too_close)


def orbit_flyback_arc(boy, mom, wide_eye, wide_aim, n1=19, n2=5, n3=19, start_az=60.0, angle=230.0, d_orbit=1.3,
                      el_orbit=-12.0, arc_angle=-33.0, arc_close=0.46, lens=LENS, pair_mid=None, arc_aim_mix=1.0):
    """The reference's move from "over" to "rope" (2.73-4.13 s), read frame by frame on 14 Nov 2026:
      1 whip orbit (n1 frames): round the pair from low, starting in front of the boy (start_az) and turning
        `angle` degrees (+ = counter-clockwise from above, by his left side) while the aim slides from the
        boy to Mom; fast in the middle, eased at both ends (reference: about 270 deg in 0.6 s, by eye).
      2 fly-back (n2 frames): straight to the wide spot (wide_eye, looking at wide_aim), very fast
        (reference: medium to small in about 4 frames, through the skeleton's legs, by eye).
      3 arc in (n3 frames): from the wide spot, circle Mom by `arc_angle` degrees while closing to
        `arc_close` of the distance (reference COLMAP solve 3.53-3.97 s: 33 deg, x0.46, a slight drop).
    Angles and lengths are settings because parts 1 and 2 are by eye: they are tuned by matching the clip
    analyzer's readings of our render to the reference's.
    pair_mid (15 Nov 2026, frame sheet vs the reference): part 1 circles this point, aim fixed on it, so BOTH people
    stay in frame (with aim sliding boy to Mom at 1.3 m, only one person was ever in the picture, and the arc
    ended on Mom's hair). arc_aim_mix: how far the aim ends on Mom (1.0 = on Mom, 0.5 = halfway to the boy)."""
    out = []
    p1 = progress(n1, floor=0.25)
    for t in p1:
        aim = pair_mid.copy() if pair_mid is not None else boy.lerp(mom, t)
        eye = around(aim, start_az + angle * t, el_orbit, d_orbit)
        out.append((eye, look(eye, aim), lens))
    e1, a1 = out[-1][0], (pair_mid.copy() if pair_mid is not None else mom.copy())
    end_aim = mom.lerp(boy, 1.0 - arc_aim_mix)
    for t in progress(n2, floor=0.1):
        eye = e1.lerp(wide_eye, t)
        aim = a1.lerp(wide_aim, t)
        out.append((eye, look(eye, aim), lens))
    v = wide_eye - mom
    d0 = v.length
    az0 = math.degrees(math.atan2(v.y, v.x))
    el0 = math.degrees(math.asin(max(-1.0, min(1.0, v.z / d0))))
    for t in progress(n3, floor=0.3):
        aim = wide_aim.lerp(end_aim, min(1.0, t * 1.5))
        eye = around(mom, az0 + arc_angle * t, el0 - 4.0 * t, d0 * (1 + (arc_close - 1) * t))
        out.append((eye, look(eye, aim), lens))
    return out
