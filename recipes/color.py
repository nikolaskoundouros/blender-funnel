"""Colour management: how scene light values become display colours."""


def set_view(scene, view="AgX", look=None, exposure=0.0):
    """Set the view transform, an optional contrast look, and exposure in stops.

    Source: Blender 5.3 manual, Displays and Views. Exposure multiplies the image by
    2**exposure before the view transform (measured: experiment E2).

    Look names changed across versions: Blender 4.0+ prefixes them with the view name
    ("AgX - High Contrast"), earlier versions did not ("High Contrast"). Found in
    CGArtPython/blender_plus_python stack_spin_start.py and confirmed against 5.3.
    Pass the short name; this function tries both spellings.
    """
    vs = scene.view_settings
    vs.view_transform = view
    vs.exposure = exposure
    if look in (None, "None"):
        vs.look = "None"
        return vs
    tried = []
    for candidate in (f"{view} - {look}", look):
        try:
            vs.look = candidate
            return vs
        except TypeError as err:
            tried.append(candidate)
            last = err
    raise ValueError(f"look not available for view {view!r}; tried {tried}") from last
