"""Straps, hoses and hardware laid over a dressed character.

A strap's path is given as waypoints: each is a ray (start point, direction) aimed at the
character. The ray is cast against the outermost clothing (vest, jacket, trousers) and the
hit point, pushed out along the surface normal, becomes the strap's centre line. A flat
ribbon of the given width is built along that line, facing the surface. So a strap drapes
over whatever is underneath, and changing the vest changes where the strap lies.

Limitation: straps are placed on the outfit as it is when they are built, and parented to
the character as a whole; they do not bend with the skeleton afterwards.
"""
import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from . import garments


def surface(objects):
    """One ray-casting structure over the evaluated (posed, modified) meshes of objects."""
    dg = bpy.context.evaluated_depsgraph_get()
    verts, faces = [], []
    for obj in objects:
        ev = obj.evaluated_get(dg)
        mesh = ev.to_mesh()
        base = len(verts)
        verts.extend(ev.matrix_world @ v.co for v in mesh.vertices)
        faces.extend(tuple(base + i for i in p.vertices) for p in mesh.polygons)
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, faces)


def _path(bvh, waypoints, step, lift):
    """Dense centre line and normals from waypoint rays."""
    origins = np.array([w[0] for w in waypoints], dtype=float)
    dirs = np.array([w[1] for w in waypoints], dtype=float)
    seg = np.linalg.norm(np.diff(origins, axis=0), axis=1)
    total = np.concatenate([[0.0], np.cumsum(seg)])
    samples = np.linspace(0.0, total[-1], max(3, int(total[-1] / step) + 1))
    pts, nrm = [], []
    for t in samples:
        o = np.array([np.interp(t, total, origins[:, k]) for k in range(3)])
        d = np.array([np.interp(t, total, dirs[:, k]) for k in range(3)])
        hit, normal, _, _ = bvh.ray_cast(Vector(o), Vector(d / np.linalg.norm(d)))
        if hit is None:
            continue
        n = np.array(normal)
        if np.dot(n, d) > 0:            # face the ray's origin
            n = -n
        pts.append(np.array(hit) + n * lift)
        nrm.append(n)
    pts, nrm = np.array(pts), np.array(nrm)
    # gentle smoothing so the strap does not follow every small bump, and smoother normals
    # so it lies flat instead of twisting where the surface underneath is uneven
    for _ in range(3):
        pts[1:-1] = 0.5 * pts[1:-1] + 0.25 * (pts[:-2] + pts[2:])
    for _ in range(6):
        nrm[1:-1] = 0.5 * nrm[1:-1] + 0.25 * (nrm[:-2] + nrm[2:])
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    return pts, nrm


def strap(scene, name, bvh, waypoints, width=0.045, thickness=0.003, material=None,
          lift=0.004, step=0.012, parent=None):
    """Flat webbing strap along waypoint rays, lying on the surface."""
    pts, nrm = _path(bvh, waypoints, step, lift + thickness / 2.0)
    tangent = np.gradient(pts, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    side = np.cross(nrm, tangent)
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    across = np.array([-0.5, -0.17, 0.17, 0.5]) * width
    verts = (pts[:, None, :] + across[None, :, None] * side[:, None, :]).reshape(-1, 3)
    k = len(across)
    faces = [(i * k + j, i * k + j + 1, (i + 1) * k + j + 1, (i + 1) * k + j)
             for i in range(len(pts) - 1) for j in range(k - 1)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts.tolist(), [], faces)
    dist, along = garments.edge_attributes(verts, faces)
    mesh.attributes.new("edge_dist", "FLOAT", "POINT").data.foreach_set("value", dist.astype(np.float32))
    mesh.attributes.new("edge_along", "FLOAT", "POINT").data.foreach_set("value", along.astype(np.float32))
    uv = np.stack([np.tile(across, len(pts)), np.repeat(np.linspace(0, 1, len(pts)), k)], axis=1)
    mesh.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array([uv[v] for f in faces for v in f]).ravel())
    mesh.update()
    mesh.shade_smooth()
    if material is not None:
        mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    solid = obj.modifiers.new("Thickness", "SOLIDIFY")
    solid.thickness, solid.offset = thickness, 0.0
    smooth = obj.modifiers.new("Subdivision", "SUBSURF")
    smooth.levels = smooth.render_levels = 1
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj, pts


def tube(scene, name, points, radius, material=None, parent=None, ends_round=True):
    """A hose or cable through given points (a smooth curve with a round section)."""
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 4
    curve.use_fill_caps = True
    spline = curve.splines.new("NURBS")
    spline.points.add(len(points) - 1)
    for p, q in zip(spline.points, points):
        p.co = (*q, 1.0)
    spline.use_endpoint_u = True
    spline.order_u = 4
    curve.resolution_u = 8
    if material is not None:
        curve.materials.append(material)
    obj = bpy.data.objects.new(name, curve)
    scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def disc(scene, name, centre, normal, radius, thickness, material=None, bevel=0.004, parent=None):
    """A round fitting (release box, buckle face, button) facing along `normal`."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=40,
                          radius1=radius, radius2=radius, depth=thickness)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.shade_smooth()
    if material is not None:
        mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    edge = obj.modifiers.new("Rounded edge", "BEVEL")
    edge.width, edge.segments = bevel, 4
    up = Vector((0.0, 0.0, 1.0))
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = up.rotation_difference(Vector(normal))
    obj.location = Vector(centre) + Vector(normal) * (thickness / 2.0)
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def hit(bvh, origin, direction, lift=0.0):
    """Surface point and outward normal where a ray meets the outfit."""
    p, n, _, _ = bvh.ray_cast(Vector(origin), Vector(direction).normalized())
    if p is None:
        return None, None
    n = np.array(n)
    if np.dot(n, direction) > 0:
        n = -n
    return np.array(p) + n * lift, n
