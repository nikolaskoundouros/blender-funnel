"""World (environment) lighting."""
import math

import bpy


def _world(scene):
    world = scene.world or bpy.data.worlds.new("World")
    if world.node_tree is None:  # Blender 4.x
        world.use_nodes = True
    scene.world = world
    return world


def solid_world(scene, color=(0.05, 0.05, 0.05), strength=1.0):
    """Uniform ambient light. Keep it low when lamps should define the shadows."""
    world = _world(scene)
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*color, 1.0)
    bg.inputs["Strength"].default_value = strength
    return world


def sky_world(scene, sun_elevation_deg=35.0, sun_rotation_deg=0.0, strength=1.0):
    """Procedural daylight sky with a sun disc.

    Source: Blender 5.3 manual, Sky Texture node. The manual warns the sky is "very
    bright by default" and says to lower scene exposure; experiment E4 measured how much.
    Node layout follows CGArtPython/blender_plus_python (bpybb/set_up_world_sun_light).
    """
    world = _world(scene)
    nodes, links = world.node_tree.nodes, world.node_tree.links
    nodes.clear()
    sky = nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_elevation = math.radians(sun_elevation_deg)
    sky.sun_rotation = math.radians(sun_rotation_deg)
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    out = nodes.new("ShaderNodeOutputWorld")
    links.new(sky.outputs["Color"], bg.inputs["Color"])
    links.new(bg.outputs["Background"], out.inputs["Surface"])
    return world
