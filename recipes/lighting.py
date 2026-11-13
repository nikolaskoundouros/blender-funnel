"""Light rigs."""
import math

import bpy

from .stage import azimuth


def aim(obj, target):
    """Point an object's -Z axis (the direction cameras look and lights shine) at a target."""
    con = obj.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    return con


def area_light(scene, name, location, target, power, size, color=(1.0, 1.0, 1.0)):
    """Disk area light aimed at a target object.

    Source: Blender 5.3 manual, Light Objects. Power is in watts. A larger size gives
    softer shadows (measured in experiments/verify_claims.py, experiment E1).
    """
    data = bpy.data.lights.new(name, type="AREA")
    data.shape = "DISK"
    data.size = size
    data.energy = power
    data.color = color
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    scene.collection.objects.link(obj)
    aim(obj, target)
    return obj


def _orbit(target_location, az, elevation_deg, distance):
    el = math.radians(elevation_deg)
    return (
        target_location[0] + distance * math.cos(el) * math.cos(az),
        target_location[1] + distance * math.cos(el) * math.sin(az),
        target_location[2] + distance * math.sin(el),
    )


def three_point(scene, target, camera_location, key_power=300.0, fill_ratio=0.25,
                rim_ratio=1.5, distance=6.0, key_size=2.5):
    """Key, fill and rim area lights placed relative to where the camera is.

    Key: to one side of the camera and above, the main light and shadow direction.
    Fill: other side, lower, larger and weaker, so shadows keep detail without flattening.
    Rim: behind the subject, to separate its outline from the background.
    Source: web search summaries of three-point lighting guides (a weak source); the
    layout is standard practice. Default power was set by measurement in runs/001:
    1500 W over-exposed a 2 m subject at 6 m (median brightness 0.88); 300 W gave 0.62.
    """
    t = tuple(target.location)
    cam_az = azimuth(t, camera_location)
    key = area_light(scene, "Key", _orbit(t, cam_az + math.radians(45), 40, distance),
                     target, key_power, key_size, color=(1.0, 0.96, 0.9))
    fill = area_light(scene, "Fill", _orbit(t, cam_az - math.radians(50), 15, distance),
                      target, key_power * fill_ratio, key_size * 2.0, color=(0.9, 0.95, 1.0))
    rim = area_light(scene, "Rim", _orbit(t, cam_az + math.radians(155), 45, distance),
                     target, key_power * rim_ratio, key_size * 0.6)
    return key, fill, rim
