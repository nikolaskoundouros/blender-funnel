"""Test what the Blender manual says about cloth simulation, on the smallest scenes.

Usage: python experiments/verify_cloth.py
"""
import json
import os
import sys

import bpy  # must come first: the pip build only exposes bmesh after bpy is loaded
import bmesh  # noqa: I001
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from recipes import stage  # noqa: E402

results = {"blender": bpy.app.version_string}


def grid(scene, name, size, cuts, location):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=cuts, y_segments=cuts, size=size / 2.0)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    scene.collection.objects.link(obj)
    return obj


def world_verts(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mesh = ev.to_mesh()
    out = np.array([ev.matrix_world @ v.co for v in mesh.vertices])
    ev.to_mesh_clear()
    return out


def run(scene, frames):
    """Cloth is computed frame after frame: every frame must be visited in order."""
    scene.frame_start, scene.frame_end = 1, frames
    for f in range(1, frames + 1):
        scene.frame_set(f)


# C1 -----------------------------------------------------------------------------------
# Claims (manual): an object with a Collision modifier deflects cloth; pinned vertices stay
# put; unpinned cloth falls and drapes.
scene = stage.new_scene()
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 0.5), segments=32, ring_count=16)
ball = bpy.context.object
ball.modifiers.new("Collision", "COLLISION")
cloth = grid(scene, "Cloth", 1.6, 30, (0, 0, 1.2))
pin = cloth.vertex_groups.new(name="pin")
corner = [v.index for v in cloth.data.vertices if v.co.x < -0.79 and v.co.y < -0.79]
pin.add(corner, 1.0, "REPLACE")
mod = cloth.modifiers.new("Cloth", "CLOTH")
mod.settings.vertex_group_mass = "pin"
mod.settings.quality = 8
mod.collision_settings.distance_min = 0.01
before = world_verts(cloth)
run(scene, 60)
after = world_verts(cloth)
dist = np.linalg.norm(after - np.array([0, 0, 0.5]), axis=1)
results["C1"] = {
    "claim": "Cloth falls, is deflected by a collision object, and pinned vertices stay put",
    "values": {"pinned_corner_moved_m": round(float(np.linalg.norm(after[corner] - before[corner], axis=1).max()), 4),
               "lowest_point_dropped_m": round(float(before[:, 2].min() - after[:, 2].min()), 3),
               "vertices_inside_ball": int((dist < 0.5).sum()),
               "closest_approach_to_ball_surface_mm": round(float((dist.min() - 0.5) * 1000), 1)},
    "confirmed": bool(np.linalg.norm(after[corner] - before[corner], axis=1).max() < 0.002
                      and before[:, 2].min() - after[:, 2].min() > 0.3 and (dist < 0.5).sum() == 0),
}

# C2 -----------------------------------------------------------------------------------
# Claim (manual): edges that belong to no face act as sewing springs and pull their two
# ends together.
scene = stage.new_scene()
mesh = bpy.data.meshes.new("Panels")
bm = bmesh.new()
left = bmesh.ops.create_grid(bm, x_segments=8, y_segments=8, size=0.25)["verts"]
right = bmesh.ops.create_grid(bm, x_segments=8, y_segments=8, size=0.25)["verts"]
for v in left:
    v.co.x -= 0.35
for v in right:
    v.co.x += 0.35
edge_l = sorted([v for v in left if v.co.x > -0.11], key=lambda v: v.co.y)
edge_r = sorted([v for v in right if v.co.x < 0.11], key=lambda v: v.co.y)
for a, b in zip(edge_l, edge_r):
    bm.edges.new((a, b))
bm.to_mesh(mesh)
bm.free()
panels = bpy.data.objects.new("Panels", mesh)
scene.collection.objects.link(panels)
scene.gravity = (0, 0, 0)
mod = panels.modifiers.new("Cloth", "CLOTH")
mod.settings.use_sewing_springs = True
mod.settings.sewing_force_max = 5.0
loose = [e.vertices[:] for e in mesh.edges if e.is_loose]
gap = lambda v: float(np.mean([np.linalg.norm(v[a] - v[b]) for a, b in loose]))
before = gap(world_verts(panels))
run(scene, 60)
after = gap(world_verts(panels))
results["C2"] = {
    "claim": "Loose edges act as sewing springs and close the gap between two panels",
    "values": {"sewing_edges": len(loose), "gap_before_m": round(before, 3), "gap_after_m": round(after, 4)},
    "confirmed": bool(len(loose) == 9 and after < 0.1 * before),
}

# C3 -----------------------------------------------------------------------------------
# Claim (manual): a negative shrinking factor makes the cloth grow.
areas = {}
for factor in (0.0, -0.1):
    scene = stage.new_scene()
    scene.gravity = (0, 0, 0)
    sheet = grid(scene, "Sheet", 1.0, 12, (0, 0, 0))
    mod = sheet.modifiers.new("Cloth", "CLOTH")
    mod.settings.shrink_min = factor
    run(scene, 40)
    v = world_verts(sheet)
    areas[str(factor)] = round(float(np.ptp(v[:, 0]) * np.ptp(v[:, 1])), 3)
results["C3"] = {
    "claim": "A shrinking factor of -0.1 makes a 1 m sheet about 10 percent larger each way",
    "values_extent_m2": areas,
    "confirmed": bool(1.15 < areas["-0.1"] / areas["0.0"] < 1.27),
}

with open(os.path.join(HERE, "results_cloth.json"), "w") as fh:
    json.dump(results, fh, indent=2)
print("RESULTS " + json.dumps(results, indent=2))
