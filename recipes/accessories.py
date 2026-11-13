"""Hard accessories built from scratch and sized to a character's own face."""
import math

import bpy
import numpy as np

from . import human, materials, rig


def face_landmarks(base_verts):
    """Key points of a morphed body's head, in Blender coordinates (character facing -Y)."""
    vb = human.to_blender(base_verts)
    bones = rig.read_rig("default")
    eye = np.array(rig._position(bones["eye.L"]["head"], vb))
    lip = np.array(rig._position(bones["oris05"]["head"], vb))
    head = vb[:human.BODY_VERTS]
    mid = (np.abs(head[:, 0]) < 0.01) & (head[:, 2] < eye[2]) & (head[:, 2] > eye[2] - 0.07)
    nose = head[np.argmin(np.where(mid, head[:, 1], 9.0))]
    level = np.abs(head[:, 2] - eye[2]) < 0.012
    return {"eye_x": float(abs(eye[0])) + 0.004, "eye_z": float(eye[2]), "nose": nose, "lip": lip,
            "half_width": float(np.abs(head[level, 0]).max()), "back_y": float(head[level, 1].max()),
            "front_y": float(nose[1]), "top_z": float(head[:, 2].max())}


def _mesh(scene, name, verts, faces, material, parent=None, smooth=True, thickness=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    mesh.update()
    if smooth:
        mesh.shade_smooth()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    if thickness:
        mod = obj.modifiers.new("Thickness", "SOLIDIFY")
        mod.thickness = thickness
        mod.offset = 1.0
    if parent is not None:
        obj.parent = parent
    return obj


def _outline(a, b, power, n):
    """Rounded-rectangle (superellipse) outline in the XZ plane."""
    t = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    x = a * np.sign(c) * np.abs(c) ** (2.0 / power)
    z = b * np.sign(s) * np.abs(s) ** (2.0 / power)
    return np.stack([x, np.zeros(n), z], axis=1)


def goggles(scene, base_verts, parent=None, clearance=0.006, frame_material=None,
            strap_material=None):
    """Aviator goggles over the eyes: two framed glass lenses with padded cups, a nose
    bridge and a strap round the head. clearance: extra room for a helmet under the strap."""
    lm = face_landmarks(base_verts)
    frame_material = frame_material or materials.metal("Goggle frame", (0.18, 0.17, 0.16), 0.35)
    strap_material = strap_material or materials.leather("Goggle strap", (0.12, 0.09, 0.07))
    n, m, tube = 56, 10, 0.0042
    a, b = 0.030, 0.025
    path = _outline(a, b, 2.6, n)
    y_frame = lm["front_y"] - 0.004
    fv, ff, lv, lf, cv, cf = [], [], [], [], [], []
    for side in (1.0, -1.0):
        wrap = math.radians(14.0) * side          # turn each lens to follow the face
        rot = np.array([[math.cos(wrap), -math.sin(wrap), 0.0],
                        [math.sin(wrap), math.cos(wrap), 0.0], [0.0, 0.0, 1.0]])
        centre = np.array([side * (lm["eye_x"] + 0.004), y_frame + 0.004 * 1.0, lm["eye_z"] + 0.002])
        place = lambda pts: pts @ rot.T + centre
        # frame: a tube swept round the outline
        tangent = np.roll(path, -1, axis=0) - np.roll(path, 1, axis=0)
        tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
        n1 = np.array([0.0, 1.0, 0.0])
        n2 = np.cross(tangent, n1)
        base = len(fv)
        for i in range(n):
            for j in range(m):
                phi = 2.0 * math.pi * j / m
                fv.append(path[i] + tube * (math.cos(phi) * n1 + math.sin(phi) * n2[i]))
        fv[base:] = list(place(np.array(fv[base:])))
        for i in range(n):
            for j in range(m):
                p, q = base + i * m + j, base + ((i + 1) % n) * m + j
                ff.append((p, q, base + ((i + 1) % n) * m + (j + 1) % m, base + i * m + (j + 1) % m))
        # lens: rings shrinking to the centre, bulging slightly forward
        base = len(lv)
        rings = [1.0, 0.75, 0.5, 0.25]
        pts = [path * s + np.array([0.0, -0.004 * (1.0 - s * s), 0.0]) for s in rings]
        pts.append(np.array([[0.0, -0.004, 0.0]]))
        lv.extend(place(np.concatenate(pts)))
        for r in range(len(rings) - 1):
            for i in range(n):
                lf.append((base + r * n + i, base + r * n + (i + 1) % n,
                           base + (r + 1) * n + (i + 1) % n, base + (r + 1) * n + i))
        last, centre_i = base + (len(rings) - 1) * n, base + len(rings) * n
        for i in range(n):
            lf.append((last + i, last + (i + 1) % n, centre_i))
        # cup: padding from the frame back to the face
        base = len(cv)
        cv.extend(place(np.concatenate([path + np.array([0.0, tube, 0.0]),
                                        path * 1.16 + np.array([0.0, 0.020, 0.0])])))
        for i in range(n):
            cf.append((base + i, base + (i + 1) % n, base + n + (i + 1) % n, base + n + i))
    made = [_mesh(scene, "Goggle frames", fv, ff, frame_material, parent),
            _mesh(scene, "Goggle lenses", lv, lf, materials.glass("Goggle glass", thin=True), parent),
            _mesh(scene, "Goggle cups", cv, cf, strap_material, parent, thickness=0.004)]
    # strap round the head, and the bridge over the nose
    # half_width includes the ears; the strap sits on the temples, about 1.5 cm narrower.
    # (First version added a margin instead and the strap floated off the head.)
    rx = lm["half_width"] - 0.006 + clearance
    yc = (lm["front_y"] + 0.02 + lm["back_y"]) / 2.0
    ry = (lm["back_y"] - (lm["front_y"] + 0.02)) / 2.0 + 0.008 + clearance
    z0, half = lm["eye_z"] + 0.002, 0.011
    start = math.asin(min(1.0, (lm["eye_x"] + a + 0.004) / rx))
    sv, sf = [], []
    angles = np.linspace(start, 2.0 * math.pi - start, 72)
    for phi in angles:
        x, y = rx * math.sin(phi), yc - ry * math.cos(phi)
        sv.extend([(x, y, z0 - half), (x, y, z0 + half)])
    for i in range(len(angles) - 1):
        sf.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    k = len(sv)
    gap = lm["eye_x"] + 0.004 - a
    sv.extend([(-gap, y_frame, z0 - 0.004), (-gap, y_frame, z0 + 0.004),
               (gap, y_frame, z0 - 0.004), (gap, y_frame, z0 + 0.004)])
    sf.append((k, k + 2, k + 3, k + 1))
    made.append(_mesh(scene, "Goggle strap", sv, sf, strap_material, parent, thickness=0.003))
    return made


def goggle_lenses(scene, base_verts, glass_material, rim_material, parent=None, eye_offset=0.032,
                  lift=0.0, size=(0.025, 0.019), overlap=1.08, standoff=0.015, dome=0.003,
                  rim_radius=0.0019, corner=0.55):
    """Clean lenses with chrome rims for goggles made by garments.goggle_parts (pass the
    same eye_offset, lift and lens size). Each lens is an exact rounded rectangle, gently
    domed, standing `standoff` metres off the face plane around the eye and slightly
    larger than the mask's opening so its edge tucks under the mask.
    (Lenses cut from the face mesh came out crumpled; fitting them to the mask's openings
    failed where an opening merged with the mask edge near the nose.)"""
    from mathutils import geometry as geo

    from . import garments, straps
    c = garments._body_coordinates()
    base, morphed = c["vb"], human.to_blender(base_verts)
    eye = c["eye"]
    front = np.nonzero((np.arange(len(base)) < human.BODY_VERTS) & (c["part"] == "neck")
                       & (base[:, 1] < eye[1] + 0.012))[0]
    made = []
    for k, side in enumerate((1.0, -1.0)):
        target = np.array([side * eye_offset, eye[2] + lift])
        gap = np.hypot(base[front, 0] - target[0], base[front, 2] - target[1])
        near = front[gap < 0.03]
        pts = morphed[near]
        centre = pts.mean(axis=0)
        _, _, vt = np.linalg.svd(pts - centre)
        w = vt[2] if vt[2][1] < 0 else -vt[2]                       # facing forward
        u = np.cross((0.0, 0.0, 1.0), w); u /= np.linalg.norm(u)
        v = np.cross(w, u)
        centre = centre + w * standoff
        hx, hz = size[0] * overlap, size[1] * overlap
        outline = garments._resample(garments._rounded_rectangle(-hx, hx, -hz, hz, corner * min(hx, hz), 0.0015), 0.0015)
        n = len(outline)
        grid = np.array([(x, y) for x in np.arange(-hx + 0.001, hx, 0.002) for y in np.arange(-hz + 0.001, hz, 0.002)])
        grid = grid[garments._inside_polygon(grid, outline)]
        grid = grid[[np.min(np.linalg.norm(outline - g, axis=1)) > 0.0012 for g in grid]]
        flat = np.concatenate([outline, grid])
        out_v, _, out_f, _, _, _ = geo.delaunay_2d_cdt([tuple(q) for q in flat], [(i, (i + 1) % n) for i in range(n)],
                                                      [], 1, 1e-8)
        out_v = np.array([tuple(q) for q in out_v])
        faces = [tuple(f) for f in out_f if len(f) == 3
                 and garments._inside_polygon(out_v[list(f)].mean(axis=0)[None, :], outline)[0]]
        r2 = np.clip((out_v[:, 0] / hx) ** 2 + (out_v[:, 1] / hz) ** 2, 0.0, 1.0)
        verts = centre + np.outer(out_v[:, 0], u) + np.outer(out_v[:, 1], v) + np.outer(dome * (1.0 - r2), w)
        f0 = faces[0]
        if np.dot(np.cross(verts[f0[1]] - verts[f0[0]], verts[f0[2]] - verts[f0[0]]), w) < 0:
            faces = [tuple(reversed(f)) for f in faces]
        mesh = bpy.data.meshes.new(f"Goggle lens {k}")
        mesh.from_pydata(verts.tolist(), [], faces)
        dist, along = garments.edge_attributes(verts, faces)
        mesh.attributes.new("edge_dist", "FLOAT", "POINT").data.foreach_set("value", dist.astype(np.float32))
        mesh.attributes.new("edge_along", "FLOAT", "POINT").data.foreach_set("value", along.astype(np.float32))
        mesh.update()
        mesh.shade_smooth()
        mesh.materials.append(glass_material)
        lens = bpy.data.objects.new(mesh.name, mesh)
        scene.collection.objects.link(lens)
        rim_pts = centre + np.outer(outline[:, 0], u) + np.outer(outline[:, 1], v) + w * 0.0006
        rim = straps.ring_tube(scene, f"Goggle rim {k}", rim_pts, rim_radius, material=rim_material)
        for obj in (lens, rim):
            if parent is not None:
                obj.parent = parent
                obj.matrix_parent_inverse = parent.matrix_world.inverted()
        made += [lens, rim]
    return made
