"""Draping: turn a shell garment into simulated cloth that hangs and folds.

Rules taken from the Blender manual and confirmed in experiments/verify_cloth.py:
  - A body deflects cloth only if it has a Collision modifier.
  - Pinned vertices (a vertex group) stay where the skeleton puts them; the rest is free.
  - A negative shrinking factor makes the cloth larger than its mesh: the spare material
    is what turns into folds.
  - Cloth must not start inside the body, so the shell needs ease before simulating.
  - Simulation is frame-sequential: every frame must be visited in order, and the scene
    must stay on the last frame for the render.

Method: the garment is already posed by the skeleton. It is subdivided for resolution,
given spare material, pinned along a chosen line (e.g. the shoulder yoke), and simulated
under gravity against the body for a few dozen frames. Thickness and smoothing are
applied after the simulation, on top of the draped shape.
"""
import bpy
import numpy as np

FABRICS = {
    # tension, compression, shear, bending, mass per vertex (kg), air damping
    "leather": dict(tension=40.0, compression=40.0, shear=25.0, bending=6.0, mass=0.5, air=3.0),
    "cotton": dict(tension=15.0, compression=15.0, shear=5.0, bending=0.5, mass=0.3, air=1.0),
    # T-shirt knit: barely stretches under its own weight (cotton sagged, pulled the neckline
    # open and dropped the hem onto the trousers in run 013), but bends easily.
    "jersey": dict(tension=45.0, compression=40.0, shear=15.0, bending=0.4, mass=0.2, air=1.0),
    "silk": dict(tension=5.0, compression=5.0, shear=1.0, bending=0.05, mass=0.15, air=1.0),
}


def make_collider(obj, thickness=0.006):
    """Let cloth collide with this object. Returns the modifier."""
    mod = next((m for m in obj.modifiers if m.type == "COLLISION"), None) or obj.modifiers.new("Collision", "COLLISION")
    obj.collision.thickness_outer = thickness
    obj.collision.thickness_inner = 0.02
    obj.collision.cloth_friction = 8.0
    return mod


def add_cloth(obj, pin_weights=None, fabric="cotton", spare=0.05, resolution=1, quality=10,
              clearance=0.006, self_collision=True, sewing_force=12.0):
    """Make a garment object simulate as cloth.

    pin_weights: one value per base vertex of the garment, 1 = fixed to the skeleton.
    spare: fraction of extra material (0.05 = 5 percent larger each way).
    resolution: subdivision levels before simulating; folds need small faces.
    """
    f = FABRICS[fabric]
    first = 1 if obj.modifiers and obj.modifiers[0].type == "ARMATURE" else 0
    while len(obj.modifiers) > first and obj.modifiers[first].type == "SMOOTH":
        first += 1
    if resolution:
        dense = obj.modifiers.new("Cloth resolution", "SUBSURF")
        dense.levels = dense.render_levels = resolution
        obj.modifiers.move(len(obj.modifiers) - 1, first)
        first += 1
    cloth = obj.modifiers.new("Cloth", "CLOTH")
    obj.modifiers.move(len(obj.modifiers) - 1, first)
    s = cloth.settings
    s.quality = quality
    s.mass = f["mass"]
    s.tension_stiffness, s.compression_stiffness = f["tension"], f["compression"]
    s.shear_stiffness, s.bending_stiffness = f["shear"], f["bending"]
    s.air_damping = f["air"]
    s.shrink_min = -spare
    if any(e.is_loose for e in obj.data.edges):   # panels joined by sewing edges
        s.use_sewing_springs = True
        s.sewing_force_max = sewing_force
    if pin_weights is not None:
        group = obj.vertex_groups.new(name="cloth_pin")
        for i, w in enumerate(pin_weights):
            if w > 0.0:
                group.add([i], float(w), "REPLACE")
        s.vertex_group_mass = group.name
        s.pin_stiffness = 1.0
    c = cloth.collision_settings
    c.use_collision = True
    c.collision_quality = 4
    c.distance_min = clearance
    c.use_self_collision = self_collision
    c.self_distance_min = 0.004
    return cloth


def simulate(scene, frames=40):
    """Step the scene through the frames in order and leave it on the last one."""
    scene.frame_start, scene.frame_end = 1, frames
    for mod in (m for o in scene.objects for m in o.modifiers if m.type == "CLOTH"):
        mod.point_cache.frame_start, mod.point_cache.frame_end = 1, frames
    for f in range(1, frames + 1):
        scene.frame_set(f)
    return frames


def fold_measure(verts, faces):
    """How creased a surface is: the average angle, in degrees, between neighbouring faces."""
    normals = {}
    for i, f in enumerate(faces):
        n = np.cross(verts[f[1]] - verts[f[0]], verts[f[2]] - verts[f[0]])
        normals[i] = n / max(np.linalg.norm(n), 1e-12)
    edge_faces = {}
    for i, f in enumerate(faces):
        for a, b in zip(f, f[1:] + f[:1]):
            edge_faces.setdefault((min(a, b), max(a, b)), []).append(i)
    angles = [np.degrees(np.arccos(np.clip(np.dot(normals[p[0]], normals[p[1]]), -1.0, 1.0)))
              for p in edge_faces.values() if len(p) == 2]
    return float(np.mean(angles))
