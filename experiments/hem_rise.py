"""Why does a draped T-shirt's hem rise? (HANDOFF question 1)

The smallest scene with the same parts as run 013 route B: a closed lathe "body" (chest,
waist, flared hips, thighs) with a Collision modifier, and an open tube "shirt" around it,
pinned along its top ring, made with recipes.cloth.add_cloth exactly as route B does
(jersey, 2% spare, one subdivision level, self collision). Each variant switches off one
ingredient; the hem height (1st percentile of z) is recorded per frame.

Usage: python experiments/hem_rise.py [variant ...]      (default: all)
Writes experiments/results_hem.json (merged with earlier runs).
"""
import json
import math
import os
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from recipes import cloth, stage  # noqa: E402

# Body profile (z, radius): shoulders, chest, waist, hip flare, thighs. Metres.
BODY = [(1.50, 0.02), (1.47, 0.12), (1.40, 0.155), (1.25, 0.150), (1.10, 0.130),
        (1.00, 0.140), (0.92, 0.170), (0.85, 0.165), (0.75, 0.140), (0.60, 0.120), (0.55, 0.02)]
SEG = 48


def lathe(name, profile, closed, seg=SEG, inward=False):
    verts, faces = [], []
    for z, r in profile:
        for k in range(seg):
            a = 2 * math.pi * k / seg
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(len(profile) - 1):
        for k in range(seg):
            a, b = i * seg + k, i * seg + (k + 1) % seg
            # Rings run downwards, so (a, a+seg, b+seg, b) faces outward. The first version
            # of this file had the reverse winding: inward normals (see variant 'inward').
            faces.append((a, b, b + seg, a + seg) if inward else (a, a + seg, b + seg, b))
    if closed:
        verts += [(0, 0, profile[0][0]), (0, 0, profile[-1][0])]
        top, bot = len(verts) - 2, len(verts) - 1
        last = (len(profile) - 1) * seg
        cap_t = [(top, k, (k + 1) % seg) for k in range(seg)]
        cap_b = [(bot, last + (k + 1) % seg, last + k) for k in range(seg)]
        if inward:
            cap_t, cap_b = [f[::-1] for f in cap_t], [f[::-1] for f in cap_b]
        faces += cap_t + cap_b
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def body_radius(z):
    zs = [p[0] for p in BODY][::-1]
    rs = [p[1] for p in BODY][::-1]
    return float(np.interp(z, zs, rs))


def shirt_profile(ease, hem_z, top_z=1.40, rows=24):
    # Hem flare ease as in garments.tee_ease: snug at the yoke, roomier towards the hem.
    out = []
    for i in range(rows + 1):
        z = top_z + (hem_z - top_z) * i / rows
        t = i / rows
        out.append((z, body_radius(z) + ease + 0.03 * t * t))
    return out


def evaluated_z(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    ev.to_mesh_clear()
    co = co.reshape(-1, 3) @ np.array(obj.matrix_world)[:3, :3].T + np.array(obj.matrix_world)[:3, 3]
    return co


def outward_fraction(obj):
    """Share of faces whose normal points away from the body axis."""
    n = 0
    for p in obj.data.polygons:
        c, nr = p.center, p.normal
        if abs(nr.z) > 0.9:          # end caps: outward means away from the body's middle height
            n += nr.z * (c.z - 1.0) > 0
        else:
            n += (nr.x * c.x + nr.y * c.y) > 0
    return n / len(obj.data.polygons)


VARIANTS = {
    "baseline": {},
    "no_collider": {"collider": False},
    "no_subsurf": {"resolution": 0},
    "no_spare": {"spare": 0.0},
    "no_self": {"self_collision": False},
    "no_friction": {"friction": 0.0},
    "no_gravity": {"gravity": False},
    "no_pin": {"pin": False},
    "cotton": {"fabric": "cotton"},
    "inward": {"inward": True},
    "fine": {"rows": 48, "seg": 96},
    "fine_self_1.5mm": {"rows": 48, "seg": 96, "self_distance": 0.0015},
    "fine_capped": {"rows": 48, "seg": 96, "cap": True},
    "inward_no_culling": {"inward": True, "culling": False},
}


def run(name, frames=40):
    opt = VARIANTS[name]
    scene = stage.new_scene()
    for o in list(scene.objects):
        bpy.data.objects.remove(o)
    scene.use_gravity = opt.get("gravity", True)
    body = lathe("Body", BODY, closed=True, inward=opt.get("inward", False))
    if opt.get("collider", True):
        cloth.make_collider(body)
        body.collision.use_culling = opt.get("culling", True)
        body.collision.cloth_friction = opt.get("friction", 8.0)
    prof = shirt_profile(ease=0.015, hem_z=0.86, rows=opt.get("rows", 24))
    shirt = lathe("Shirt", prof, closed=False, seg=opt.get("seg", SEG))
    z = np.array([v.co.z for v in shirt.data.vertices])
    pin = np.clip((z - 1.37) / 0.03, 0.0, 1.0) if opt.get("pin", True) else None
    cloth.add_cloth(shirt, pin_weights=pin, fabric=opt.get("fabric", "jersey"), spare=opt.get("spare", 0.02),
                    resolution=opt.get("resolution", 1), self_collision=opt.get("self_collision", True),
                    self_distance=opt.get("self_distance", 0.004),
                    cap_self_distance=opt.get("cap", False))
    scene.frame_start, scene.frame_end = 1, frames
    shirt.modifiers["Cloth"].point_cache.frame_start = 1
    shirt.modifiers["Cloth"].point_cache.frame_end = frames
    t0 = time.time()
    hem, inside = [], []
    for f in range(1, frames + 1):
        scene.frame_set(f)
        co = evaluated_z(shirt)
        hem.append(round(float(np.percentile(co[:, 2], 1)), 4))
        r = np.hypot(co[:, 0], co[:, 1])
        inside.append(int(np.sum(r < np.array([body_radius(zz) for zz in co[:, 2]]))))
    return {"hem_z_start": hem[0], "hem_z_end": hem[-1], "rise_cm": round(100 * (hem[-1] - hem[0]), 2),
            "hem_z_by_frame": hem[::4] + [hem[-1]], "verts_inside_start": inside[0], "verts_inside_end": inside[-1], "verts": len(co),
            "radius_ease_mid_end_cm": round(100 * float(np.median(r[np.abs(co[:, 2] - 1.1) < 0.03] - body_radius(1.1))), 2),
            "seconds": round(time.time() - t0, 1), "blender": bpy.app.version_string,
            "body_normals_outward_fraction": round(outward_fraction(body), 3),
            "self_distance_used_mm": round(1000 * shirt.modifiers["Cloth"].collision_settings.self_distance_min, 2)}


if __name__ == "__main__":
    names = sys.argv[1:] or list(VARIANTS)
    path = os.path.join(HERE, "results_hem.json")
    results = json.load(open(path)) if os.path.exists(path) else {}
    for n in names:
        results[n] = run(n)
        print(n, json.dumps(results[n]))
        json.dump(results, open(path, "w"), indent=1)
