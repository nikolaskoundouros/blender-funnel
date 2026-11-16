"""Import a glTF model into an empty scene, print its size, orientation hints and part names, and render three clay views.
Runs inside bpy on the pod. Env: GLB (path), OUT (folder for the pictures)."""
import math
import os

import bpy
from mathutils import Vector

GLB, OUT = os.environ["GLB"], os.environ["OUT"]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
sc = bpy.context.scene
ms = [o for o in sc.objects if o.type == "MESH"]
pts = [o.matrix_world @ Vector(c) for o in ms for c in o.bound_box]
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
print("DINO meshes", len(ms), "faces", sum(len(o.data.polygons) for o in ms))
print("DINO bbox min", tuple(round(v, 3) for v in mn), "max", tuple(round(v, 3) for v in mx), "dims", tuple(round(v, 3) for v in (mx - mn)))
print("DINO first names", [o.name for o in ms[:45]])
# where is the mass along each axis: vertex counts in 10 slices (the skull end is dense, the tail end thin)
verts = [o.matrix_world @ v.co for o in ms for v in o.data.vertices]
for ax, nm in enumerate("xyz"):
    lo, hi = mn[ax], mx[ax]
    cnt = [0] * 10
    for p in verts:
        cnt[min(9, int((p[ax] - lo) / max(hi - lo, 1e-9) * 10))] += 1
    print(f"DINO slices along {nm}:", cnt)
# clay + three views
clay = bpy.data.materials.new("clay")
clay.diffuse_color = (0.8, 0.78, 0.72, 1)
for o in ms:
    o.data.materials.clear()
    o.data.materials.append(clay)
c = (mn + mx) / 2
R = max(mx - mn) * 0.62
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(50), 0, math.radians(30))
sc.collection.objects.link(sun)
w = bpy.data.worlds.new("w")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.35, 0.35, 0.38, 1)
sc.world = w
from recipes import render  # noqa: E402
import sys  # noqa: E402
render.cycles_gpu(sc, 800, 600, 16)
for nm, d in (("from_plus_x", (1, 0, 0)), ("from_plus_y", (0, 1, 0)), ("from_plus_z_top", (0, 0.001, 1))):
    cam = bpy.data.objects.new(nm, bpy.data.cameras.new(nm))
    cam.data.type, cam.data.ortho_scale = "ORTHO", max(mx - mn) * 1.15
    cam.location = c + Vector(d).normalized() * (R * 3)
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.filepath = os.path.join(OUT, nm + ".png")
    bpy.ops.render.render(write_still=True)
    print("DINO rendered", nm)
