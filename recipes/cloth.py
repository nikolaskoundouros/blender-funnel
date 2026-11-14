"""Draping: turn a shell garment into simulated cloth that hangs and folds.

Rules taken from the Blender manual and confirmed in experiments/verify_cloth.py:
  - A body deflects cloth only if it has a Collision modifier.
  - Pinned vertices (a vertex group) stay where the skeleton puts them; the rest is free.
  - A negative shrinking factor makes the cloth larger than its mesh: the spare material
    is what turns into folds.
  - Cloth must not start inside the body, so the shell needs ease before simulating.
  - Simulation is frame-sequential: every frame must be visited in order, and the scene
    must stay on the last frame for the render.
  - Self-collision distance must stay well below the cloth's edge length, or neighbouring
    triangles repel each other and the garment bunches upward (source: collision.cc in
    Blender 5.3.0; verified in experiments/hem_real.py). add_cloth caps it automatically.

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
              clearance=0.006, self_collision=True, sewing_force=12.0, self_distance=0.004,
              cap_self_distance=True):
    """Make a garment object simulate as cloth.

    pin_weights: one value per base vertex of the garment, 1 = fixed to the skeleton.
    spare: fraction of extra material (0.05 = 5 percent larger each way).
    resolution: subdivision levels before simulating; folds need small faces.
    cap_self_distance: limit self_distance to self_distance_cap(); False only to reproduce
    the uncapped behaviour in experiments.
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
    # Self collision skips only triangle pairs that share a vertex (collision.cc,
    # cloth_bvh_selfcollision_is_active). Two triangles one row apart sit about 0.7 edge
    # lengths apart, so a self distance above ~0.35 edge makes the cloth collide with its
    # own neighbours on every step: it bunches and the hem climbs (notes/cloth.md, claim 9).
    cap = self_distance_cap(obj, cloth) if cap_self_distance else self_distance
    obj["self_distance_requested"], obj["self_distance_cap"] = self_distance, cap
    if self_collision and cap < 0.001:
        # Blender's hard minimum is 1 mm (installed 5.3.0 property range): edges this short
        # cannot self-collide without repelling their neighbours, so self collision is off.
        c.use_self_collision = False
        obj["self_collision_off"] = "cloth edges too short for the 1 mm minimum self distance"
    c.self_distance_min = max(0.001, min(self_distance, cap))
    return cloth


def cloth_edge_lengths(obj, cloth_mod):
    """Edge lengths (world units) of the mesh the Cloth modifier receives."""
    after = False
    saved = []
    for m in obj.modifiers:
        after = after or m == cloth_mod
        if after:
            saved.append((m, m.show_viewport))
            m.show_viewport = False
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    ed = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", ed)
    ev.to_mesh_clear()
    for m, s in saved:
        m.show_viewport = s
    co = co.reshape(-1, 3) @ np.array(obj.matrix_world)[:3, :3].T
    ed = ed.reshape(-1, 2)
    return np.linalg.norm(co[ed[:, 0]] - co[ed[:, 1]], axis=1)


def self_distance_cap(obj, cloth_mod, factor=0.3, percentile=2.0):
    """Largest safe self-collision distance for this cloth: factor x a short edge.

    Calibrated in experiments/hem_real.py and hem_rise.py: run 013's tee (2nd-percentile
    edge 3.5 mm) was fine at 1 mm and rose 2.5 cm at 1.5 mm; a 5.6 mm-edge tube was fine
    at 1.5 mm and rose 15 cm at 4 mm."""
    lengths = cloth_edge_lengths(obj, cloth_mod)
    lengths = lengths[lengths > 1e-6]
    return float(factor * np.percentile(lengths, percentile)) if len(lengths) else 0.004


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
