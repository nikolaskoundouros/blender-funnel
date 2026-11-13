"""Render settings."""
import bpy


def cycles_cpu(scene, width=960, height=540, samples=64, denoise=True, seed=0):
    """Cycles on CPU: works headless with no GPU or display.

    Blender 5.3 defaults are 4096 samples with adaptive sampling at a 0.01 noise
    threshold; a fixed low sample cap keeps test renders to seconds.
    """
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = denoise
    scene.cycles.seed = seed
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"


def render_to(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path
