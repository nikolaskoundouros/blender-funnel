"""Hair and fur as real strands, generated from scratch.

A strand is a short chain of points with a radius. Strands are rooted at random points on
a surface (chosen in proportion to area, so density is even), start along the surface
normal, and at each step are nudged by a combing direction and by random curl. Blender
renders the result as hair curves. Works for fur trim, moustaches, brows and short hair.
Strands are placed once, on the surface as it is when they are grown; they do not yet
follow a surface that moves afterwards.
"""
import bpy
import numpy as np


def evaluated_mesh(obj):
    """World-space vertices and faces of an object after its modifiers and pose."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mesh = ev.to_mesh()
    verts = np.array([ev.matrix_world @ v.co for v in mesh.vertices])
    faces = [tuple(p.vertices) for p in mesh.polygons]
    ev.to_mesh_clear()
    return verts, faces


def sample_surface(verts, faces, count, seed=0):
    """Random points on a mesh, uniform per unit area. Returns (points, normals)."""
    rng = np.random.default_rng(seed)
    tris = np.array([(f[0], f[i], f[i + 1]) for f in faces for i in range(1, len(f) - 1)])
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    n = np.cross(b - a, c - a)
    area = np.linalg.norm(n, axis=1) / 2.0
    pick = rng.choice(len(tris), size=count, p=area / area.sum())
    u, v = rng.random(count), rng.random(count)
    flip = u + v > 1.0
    u[flip], v[flip] = 1.0 - u[flip], 1.0 - v[flip]
    points = a[pick] + u[:, None] * (b[pick] - a[pick]) + v[:, None] * (c[pick] - a[pick])
    normals = n[pick] / np.maximum(np.linalg.norm(n[pick], axis=1, keepdims=True), 1e-12)
    return points, normals


def grow(scene, name, roots, normals, length, radius, material, comb=(0.0, 0.0, 0.0),
         curl=0.3, steps=6, seed=0, length_jitter=0.35):
    """Create strands. length and comb may be single values or one per root.

    comb: a direction the strands lean toward (e.g. down for gravity, sideways for a
    combed moustache). curl: how much each step wanders; 0 is straight, 1 is woolly.
    """
    rng = np.random.default_rng(seed)
    n = len(roots)
    lengths = np.broadcast_to(np.asarray(length, dtype=float), (n,)) * (
        1.0 + length_jitter * (rng.random(n) * 2.0 - 1.0))
    comb = np.broadcast_to(np.asarray(comb, dtype=float), (n, 3))
    pts = np.zeros((n, steps, 3))
    pts[:, 0] = roots
    d = normals + comb
    d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-12)
    for k in range(1, steps):
        d = d + curl * rng.normal(size=(n, 3)) + 0.35 * comb
        d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-12)
        pts[:, k] = pts[:, k - 1] + d * (lengths / (steps - 1))[:, None]
    curves = bpy.data.hair_curves.new(name)
    curves.add_curves([steps] * n)
    curves.points.foreach_set("position", pts.astype(np.float32).ravel())
    taper = np.tile(np.linspace(radius, radius * 0.35, steps), n).astype(np.float32)
    curves.points.foreach_set("radius", taper)
    curves.materials.append(material)
    obj = bpy.data.objects.new(name, curves)
    scene.collection.objects.link(obj)
    return obj
