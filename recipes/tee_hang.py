"""Reshape a posed T-shirt so it hangs like a loose real one (straight from the chest, wide neck, loose sleeves).

Written with the owner on 14 Nov 2026 to match the boy in "My Mom Cracked The Dinosaur"; tested on the
box with probe renders (straight side profile, no belly bulge, hem 7 cm lower). A Laplacian smoothing
modifier tore the shirt at its seams (SHIRT_SMOOTH, keep 0); SHIRT_TAUBIN smooths with seams held.

No cloth simulation. The shirt, as posed on the body, is taken as a mesh and:
  1. below the chest it hangs straight down: at each height and direction around the body its
     radius becomes the largest radius found above it (shirt, body and trousers + clearance),
     so it falls from the chest like cloth and can only move outwards;
  2. it is lengthened a little and flared slightly at the hem;
  3. the sleeves are pushed out from the arm bones (looser, wider towards the cuff);
  4. a lower, wider neck is cut;
  5. round bands are laid along the new neckline, the cuffs and the hem.
"""
import math

import bmesh
import bpy
import numpy as np

LIMB_PREFIXES = ("upperarm", "lowerarm", "wrist", "finger", "metacarpal", "thumb", "hand")


def _log(*a):
    print("HANG", *a, flush=True)


def _smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _world(obj, dg):
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    mw = np.array(ev.matrix_world)
    ev.to_mesh_clear()
    return co.reshape(n, 3) @ mw[:3, :3].T + mw[:3, 3]


def _group_share(obj, prefixes):
    """Per vertex: share of its skin weights in groups whose name starts with one of prefixes."""
    idx = {g.index for g in obj.vertex_groups if g.name.startswith(prefixes)}
    n = len(obj.data.vertices)
    part, total = np.zeros(n), np.zeros(n)
    for v in obj.data.vertices:
        for g in v.groups:
            total[v.index] += g.weight
            if g.group in idx:
                part[v.index] += g.weight
    return np.where(total > 0, part / np.maximum(total, 1e-9), 0.0), len(idx)


def _fill_circular(row):
    nz = np.nonzero(row > 0)[0]
    if len(nz) == 0:
        return row
    n = len(row)
    xp = np.concatenate([nz - n, nz, nz + n])
    return np.interp(np.arange(n), xp, np.concatenate([row[nz]] * 3))


def _boundary_loops(obj, dg):
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    mw = np.array(ev.matrix_world)
    co = co.reshape(n, 3) @ mw[:3, :3].T + mw[:3, 3]
    count = {}
    for p in me.polygons:
        for ek in p.edge_keys:
            count[ek] = count.get(ek, 0) + 1
    ev.to_mesh_clear()
    adj = {}
    for (a, b), c in count.items():
        if c == 1:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
    loops, seen = [], set()
    for start in adj:
        if start in seen:
            continue
        loop, prev, cur = [start], None, start
        seen.add(start)
        while True:
            nxt = [x for x in adj[cur] if x != prev and x not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen.add(cur)
            loop.append(cur)
        if len(loop) >= 8:
            loops.append(co[loop])
    return loops


def _band(scene, name, pts, radius, mat, smooth_iter=20):
    p = pts.copy()
    for _ in range(smooth_iter):
        p = 0.5 * p + 0.25 * (np.roll(p, 1, 0) + np.roll(p, -1, 0))
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    sp = cu.splines.new("POLY")
    sp.points.add(len(p) - 1)
    for i, q in enumerate(p):
        sp.points[i].co = (float(q[0]), float(q[1]), float(q[2]), 1.0)
    sp.use_cyclic_u = True
    ob = bpy.data.objects.new(name, cu)
    scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob


def apply(scene, tee, arm, body, others, chest_z, tee_rgb, env):
    subs = [m for m in tee.modifiers if m.type == "SUBSURF"]
    for m in subs:
        m.show_viewport = m.show_render = False
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    M = bpy.data.meshes.new_from_object(tee.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    n = len(M.vertices)
    assert n == len(tee.data.vertices), ("vertex count changed", n, len(tee.data.vertices))
    mw = np.array(tee.matrix_world)
    co = np.empty(n * 3)
    M.vertices.foreach_get("co", co)
    P = co.reshape(n, 3) @ mw[:3, :3].T + mw[:3, 3]

    sw, ngroups = _group_share(tee, ("upperarm", "lowerarm"))
    torso = sw < 0.4
    _log("shirt verts", n, "arm groups", ngroups, "sleeve verts", int((~torso).sum()))

    # ---- 1-2. straight hang below the chest, a little longer, slight flare
    z_top = chest_z + env("HANG_UP", 0.0)
    ref = torso & (P[:, 2] < z_top) & (P[:, 2] > z_top - 0.25)
    cx = 0.5 * (P[ref, 0].min() + P[ref, 0].max())
    cy = 0.5 * (P[ref, 1].min() + P[ref, 1].max())
    K = env("HANG_LEN", 1.10)
    below = torso & (P[:, 2] < z_top)
    znew = P[:, 2].copy()
    znew[below] = z_top - (z_top - P[below, 2]) * K
    hem_old, hem_new = P[torso, 2].min(), znew[torso].min()
    NS, DZ = 48, 0.02
    nb = int(math.ceil((z_top - hem_new) / DZ)) + 2
    r = np.hypot(P[:, 0] - cx, P[:, 1] - cy)
    th = np.arctan2(P[:, 1] - cy, P[:, 0] - cx)
    sec = lambda t: (((t + math.pi) / (2 * math.pi)) * NS).astype(int) % NS
    band = lambda z: np.clip(((z_top - z) / DZ).astype(int), 0, nb - 1)
    grid = np.zeros((nb, NS))
    np.maximum.at(grid, (band(P[below, 2]), sec(th[below])), r[below])
    clear = env("HANG_CLEAR", 0.008)
    for ob in [body] + list(others):
        Q = _world(ob, dg)
        keep = np.ones(len(Q), bool)
        if ob.vertex_groups and len(Q) == len(ob.data.vertices):
            limb, _ = _group_share(ob, LIMB_PREFIXES)
            keep = limb < 0.3
        q = keep & (Q[:, 2] < z_top) & (Q[:, 2] > hem_new - 0.03)
        rq = np.hypot(Q[q, 0] - cx, Q[q, 1] - cy)
        tq = np.arctan2(Q[q, 1] - cy, Q[q, 0] - cx)
        ok = rq < env("HANG_MAXR", 0.26)
        np.maximum.at(grid, (band(Q[q][ok, 2]), sec(tq[ok])), rq[ok] + clear)
    for b in range(nb):
        grid[b] = _fill_circular(grid[b])
    for b in range(1, nb):
        grid[b] = np.maximum(grid[b], grid[b - 1])
    blurred = sum(np.roll(grid, k, axis=1) for k in (-2, -1, 0, 1, 2)) / 5.0
    grid = np.maximum(blurred, grid - 0.002)
    f = (th + math.pi) / (2 * math.pi) * NS - 0.5
    i0 = np.floor(f).astype(int) % NS
    i1 = (i0 + 1) % NS
    w = f - np.floor(f)
    bn = band(znew)
    R = grid[bn, i0] * (1 - w) + grid[bn, i1] * w
    t = np.clip((z_top - znew) / max(z_top - hem_new, 1e-6), 0, 1)
    blend = _smoothstep((z_top - P[:, 2]) / env("HANG_BLEND", 0.05))
    target = np.maximum(R, r) + env("HANG_FLARE", 0.012) * t
    target += env("FOLD_AMP", 0.0) * t * 0.5 * (1 + np.sin(env("FOLD_N", 7.0) * th + 1.3))
    rf = r + (target - r) * blend
    newP = P.copy()
    newP[below, 0] = cx + rf[below] * np.cos(th[below])
    newP[below, 1] = cy + rf[below] * np.sin(th[below])
    newP[below, 2] = znew[below]
    moved = np.linalg.norm(newP - P, axis=1)
    _log(f"chest z {z_top:.3f}, hem {hem_old:.3f} -> {hem_new:.3f}, axis ({cx:.3f}, {cy:.3f}), "
         f"moved max {moved.max() * 1000:.0f} mm, mean {moved[below].mean() * 1000:.0f} mm")

    # ---- 3. looser sleeves, pushed out from the upper-arm bones
    ease = env("SLEEVE_EASE", 0.012)
    amw = np.array(arm.matrix_world) if arm is not None else None
    for side, sgn in (("L", 1.0), ("R", -1.0)):
        if amw is None:
            break
        ups = sorted((b for b in arm.pose.bones if b.name.startswith("upperarm") and b.name.endswith(side)),
                     key=lambda b: b.name)
        if not ups:
            _log("no upper-arm bones for", side)
            continue
        a = (amw @ np.append(np.array(ups[0].head), 1.0))[:3]
        e = (amw @ np.append(np.array(ups[-1].tail), 1.0))[:3]
        m = (sw > 0.05) & (np.sign(newP[:, 0]) == sgn)
        Q = newP[m]
        u = (e - a) / np.linalg.norm(e - a)
        s = np.clip((Q - a) @ u, 0.0, None)
        radial = Q - (a + np.outer(s, u))
        dist = np.linalg.norm(radial, axis=1)
        dirn = radial / np.maximum(dist, 1e-9)[:, None]
        smax = s[sw[m] > 0.4].max() if (sw[m] > 0.4).any() else s.max()
        prog = _smoothstep(s / max(smax, 1e-6))
        wsl = np.clip((sw[m] - 0.15) / 0.45, 0.0, 1.0)
        newP[m] = Q + dirn * (ease * (0.35 + 0.65 * prog) * wsl)[:, None] \
            + np.outer(env("SLEEVE_LEN", 0.0) * prog * wsl, u)       # longer sleeves, along the arm
        _log(f"sleeve {side}: {int(m.sum())} verts, bone length {np.linalg.norm(e - a):.3f}, sleeve reach {smax:.3f}")

    # ---- even out facets: Taubin smoothing (no shrinking), every open edge and seam held fixed
    it = int(env("SHIRT_TAUBIN", 0))
    if it:
        ed = np.empty(len(M.edges) * 2, dtype=np.int64)
        M.edges.foreach_get("vertices", ed)
        ed = ed.reshape(-1, 2)
        count = {}
        for p in M.polygons:
            for ek in p.edge_keys:
                count[ek] = count.get(ek, 0) + 1
        fixed = np.zeros(n, bool)
        for ek, c in count.items():
            if c == 1:
                fixed[list(ek)] = True
        deg = np.maximum(np.bincount(ed.ravel(), minlength=n), 1).astype(float)
        free = (~fixed)[:, None]
        X = newP.copy()
        for _ in range(it):
            for step in (0.5, -0.53):
                acc = np.zeros_like(X)
                np.add.at(acc, ed[:, 0], X[ed[:, 1]])
                np.add.at(acc, ed[:, 1], X[ed[:, 0]])
                X = X + step * (acc / deg[:, None] - X) * free
        _log(f"taubin {it} rounds, {int(fixed.sum())} edge verts held, moved max "
             f"{np.linalg.norm(X - newP, axis=1).max() * 1000:.1f} mm")
        newP = X

    loc = (newP - mw[:3, 3]) @ np.linalg.inv(mw[:3, :3]).T
    M.vertices.foreach_set("co", loc.ravel())
    M.update()

    # ---- 4. lower, wider neck
    if env("NECK_CUT", 1):
        count = {}
        for p in M.polygons:
            for ek in p.edge_keys:
                count[ek] = count.get(ek, 0) + 1
        bverts = {v for ek, c in count.items() if c == 1 for v in ek}
        top = [v for v in bverts if newP[v, 2] > z_top + 0.05 and torso[v]
               and abs(newP[v, 0] - cx) < 0.12]
        if top:
            T = newP[top]
            cxn, cyn = 0.5 * (T[:, 0].min() + T[:, 0].max()), 0.5 * (T[:, 1].min() + T[:, 1].max())
            a0, b0, zmin = 0.5 * np.ptp(T[:, 0]), 0.5 * np.ptp(T[:, 1]), T[:, 2].min()
            widen = env("NECK_WIDEN", 0.02)
            A, B = a0 + widen, b0 + widen * 0.7
            ell = ((newP[:, 0] - cxn) / A) ** 2 + ((newP[:, 1] - cyn) / B) ** 2
            zl = zmin - env("NECK_DROP", 0.012) - env("NECK_FRONT", 0.03) * np.clip((cyn - newP[:, 1]) / B, 0, 1)
            kill = (ell < 1.0) & (newP[:, 2] > zl) & torso
            bm = bmesh.new()
            bm.from_mesh(M)
            bm.verts.ensure_lookup_table()
            bmesh.ops.delete(bm, geom=[bm.verts[i] for i in np.nonzero(kill)[0]], context="VERTS")
            bm.to_mesh(M)
            bm.free()
            _log(f"neck: old opening {2 * a0:.3f} x {2 * b0:.3f} m, new {2 * A:.3f} x {2 * B:.3f} m, "
                 f"{int(kill.sum())} verts removed")
        else:
            _log("neck: collar edge not found, not cut")

    # ---- swap in the reshaped mesh (it already carries the pose)
    if len(M.materials) == 0:
        for mat in tee.data.materials:
            M.materials.append(mat)
    keep_mw = tee.matrix_world.copy()
    tee.parent = None
    tee.matrix_world = keep_mw
    tee.data = M
    for mod in [m for m in tee.modifiers if m.type == "ARMATURE"]:
        tee.modifiers.remove(mod)
    for m in subs:
        m.show_viewport = m.show_render = True
    if env("SHIRT_SUBDIV", 0):       # more faces on the reshaped shirt
        for m in subs:
            m.levels = m.render_levels = int(env("SHIRT_SUBDIV", 0))
    if env("SHIRT_SMOOTH", 0):       # even out facets and corners before the subdivision
        ls = tee.modifiers.new("Shirt smooth", "LAPLACIANSMOOTH")
        ls.iterations = int(env("SHIRT_SMOOTH", 0))
        ls.lambda_factor = env("SHIRT_LAMBDA", 0.6)
        ls.lambda_border = env("SHIRT_BORDER", 0.3)
        ls.use_volume_preserve = True
        ls.use_normalized = True
        tee.modifiers.move(len(tee.modifiers) - 1, 0)
    _log("shirt modifiers", [m.type for m in tee.modifiers],
         "subdivision", [m.render_levels for m in subs])

    # ---- 5. bands on the neckline, cuffs and hem
    band_mat = bpy.data.materials.new("TeeBand")
    band_mat.use_nodes = True
    bsdf = next(nd for nd in band_mat.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = tuple(tee_rgb) + (1.0,)
    bsdf.inputs["Roughness"].default_value = 0.85
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    loops = _boundary_loops(tee, dg)
    if loops:
        mz = [L[:, 2].mean() for L in loops]
        neck, hem = loops[int(np.argmax(mz))], loops[int(np.argmin(mz))]
        rest = [L for L in loops if L is not neck and L is not hem]
        cuffs = sorted(rest, key=lambda L: -abs(L[:, 0].mean()))[:2]
        made = []
        if env("NECK_BAND", 0.006) > 0:
            made.append(_band(scene, "TeeNeckBand", neck, env("NECK_BAND", 0.006), band_mat))
        for i, L in enumerate(cuffs):
            if env("CUFF_BAND", 0.005) > 0:
                made.append(_band(scene, f"TeeCuff{i}", L, env("CUFF_BAND", 0.005), band_mat))
        if env("HEM_BAND", 0.003) > 0:
            made.append(_band(scene, "TeeHemBand", hem, env("HEM_BAND", 0.003), band_mat))
        _log(f"edges found: {len(loops)}; bands made: {[o.name for o in made]}; "
             f"neck z {neck[:, 2].mean():.3f}, hem z {hem[:, 2].mean():.3f}")
    return tee
