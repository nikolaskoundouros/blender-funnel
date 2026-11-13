"""Scene setup, materials and a studio backdrop."""
import math

import bpy


def new_scene():
    """Start from an empty file and return its scene."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def principled(name, color, roughness=0.5, metallic=0.0):
    """Material with a Principled BSDF. Finds the node by type, not by its display name."""
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:  # Blender 4.x; 5.x creates the node tree by default
        mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def empty_at(scene, name, location):
    """Invisible marker object, useful as an aim point for cameras and lights."""
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    scene.collection.objects.link(obj)
    return obj


def azimuth(from_point, to_point):
    """Compass angle (radians, in the XY plane) of to_point as seen from from_point."""
    return math.atan2(to_point[1] - from_point[1], to_point[0] - from_point[0])


def backdrop(scene, camera_location, target_location=(0, 0, 0), width=40.0, front=14.0,
             back=7.0, height=12.0, radius=4.0, color=(0.5, 0.5, 0.52)):
    """Studio sweep: a floor that curves up into a wall behind the subject.

    Removes the hard horizon line a flat ground plane gives. The wall is placed on the
    far side of the target from the camera.
    Provenance: studio practice from prior knowledge, not from a fetched source.
    """
    steps = 16
    profile = [(-front, 0.0), (back - radius, 0.0)]
    for i in range(1, steps + 1):
        a = (math.pi / 2) * i / steps
        profile.append((back - radius + radius * math.sin(a), radius - radius * math.cos(a)))
    profile.append((back, height))

    verts, faces = [], []
    for y, z in profile:
        verts.append((-width / 2, y, z))
        verts.append((width / 2, y, z))
    for i in range(len(profile) - 1):
        a = 2 * i
        faces.append((a, a + 1, a + 3, a + 2))

    mesh = bpy.data.meshes.new("Backdrop")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.shade_smooth()
    obj = bpy.data.objects.new("Backdrop", mesh)
    obj.location = (target_location[0], target_location[1], 0.0)
    # Local +Y is "towards the wall"; point it away from the camera.
    away = azimuth(camera_location, target_location)
    obj.rotation_euler = (0.0, 0.0, away - math.pi / 2)
    mesh.materials.append(principled("Backdrop", color, roughness=0.85))
    scene.collection.objects.link(obj)
    return obj
