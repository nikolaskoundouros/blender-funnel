"""Cameras."""
import bpy

from .lighting import aim


def camera_at(scene, location, target, lens=50.0):
    """Camera placed at a location and aimed at a target object; becomes the scene camera."""
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    cam.location = location
    cam.data.lens = lens
    scene.collection.objects.link(cam)
    aim(cam, target)
    scene.camera = cam
    return cam


def depth_of_field(cam, focus_object, fstop=2.8):
    """Blur what is nearer or farther than the focus object.

    Source: Blender 5.3 property description: lower f-stop gives more defocus.
    The tutorial repo uses values from 0.1 to 1.1 for strong blur on small scenes.
    """
    dof = cam.data.dof
    dof.use_dof = True
    dof.focus_object = focus_object
    dof.aperture_fstop = fstop
    return dof
