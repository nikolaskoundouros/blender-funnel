"""Procedural materials: surfaces made from maths, no image files.

Input and node names were read from Blender 5.3 itself (see sources/log.md); several
differ from older tutorials ("Sheen Weight", "Coat Weight", "Transmission Weight").
Patterns use object coordinates (metres) unless a UV map is asked for, so the pattern has
real-world size regardless of how large the object is.
"""
import bpy


def _new(name):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    return mat, nodes, links, bsdf


# Garment texture coordinates are tiny: one UV unit spans about 21 m of cloth (measured on
# the tights shell: median 20.7, range 13 to 24). Patterns on garments are scaled by this
# so a thread spacing given in metres comes out right, and they stay glued to the cloth
# when it bends (object coordinates would let the pattern swim).
METRES_PER_UV = 21.0


def _bands(spacing, on):
    """Wave-texture Scale giving one band every `spacing` metres (period = 2*pi/(10*Scale))."""
    return 0.628 / spacing * (METRES_PER_UV if on == "garment" else 1.0)


def _coords(nodes, links, scale=(1.0, 1.0, 1.0), rotation=(0.0, 0.0, 0.0), uv=False):
    tc = nodes.new("ShaderNodeTexCoord")
    mp = nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = scale
    mp.inputs["Rotation"].default_value = rotation
    links.new(tc.outputs["UV" if uv else "Object"], mp.inputs["Vector"])
    return mp.outputs["Vector"]


def _ramp(nodes, links, factor, low, high, lo_pos=0.0, hi_pos=1.0):
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = lo_pos
    ramp.color_ramp.elements[0].color = (*low, 1.0)
    ramp.color_ramp.elements[1].position = hi_pos
    ramp.color_ramp.elements[1].color = (*high, 1.0)
    links.new(factor, ramp.inputs["Factor"])
    return ramp.outputs["Color"]


def _bump(nodes, links, bsdf, height, strength=0.3, distance=0.001):
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    links.new(height, bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


def plain(name, color, roughness=0.5, metallic=0.0):
    mat, _, _, bsdf = _new(name)
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def wood(name="Wood", light=(0.55, 0.36, 0.20), dark=(0.30, 0.17, 0.08), grain=18.0,
         roughness=0.45, axis="X"):
    """Wood with grain running along one object axis: stretched noise bands."""
    mat, nodes, links, bsdf = _new(name)
    stretch = {"X": (0.12, 1.0, 1.0), "Y": (1.0, 0.12, 1.0), "Z": (1.0, 1.0, 0.12)}[axis]
    vec = _coords(nodes, links, scale=stretch)
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = grain
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Distortion"].default_value = 0.6
    links.new(vec, noise.inputs["Vector"])
    links.new(_ramp(nodes, links, noise.outputs["Factor"], dark, light, 0.3, 0.75),
              bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness
    _bump(nodes, links, bsdf, noise.outputs["Factor"], strength=0.15)
    return mat


def floorboards(name="Floorboards", light=(0.62, 0.45, 0.28), dark=(0.42, 0.28, 0.16),
                board_width=0.14, board_length=1.6):
    """Plank floor: a brick pattern for the boards, each tinted differently, plus grain."""
    mat, nodes, links, bsdf = _new(name)
    vec = _coords(nodes, links)
    brick = nodes.new("ShaderNodeTexBrick")
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Brick Width"].default_value = board_length
    brick.inputs["Row Height"].default_value = board_width
    brick.inputs["Mortar Size"].default_value = 0.002
    brick.inputs["Mortar Smooth"].default_value = 0.2
    brick.inputs["Bias"].default_value = 0.0
    brick.inputs["Color1"].default_value = (*light, 1.0)
    brick.inputs["Color2"].default_value = (*dark, 1.0)
    brick.inputs["Mortar"].default_value = (0.08, 0.05, 0.03, 1.0)
    links.new(vec, brick.inputs["Vector"])
    grain_vec = _coords(nodes, links, scale=(0.08, 1.0, 1.0))
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 30.0
    noise.inputs["Detail"].default_value = 5.0
    links.new(grain_vec, noise.inputs["Vector"])
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 0.55
    links.new(brick.outputs["Color"], mix.inputs[6])
    links.new(_ramp(nodes, links, noise.outputs["Factor"], (0.55, 0.55, 0.55), (1.0, 1.0, 1.0), 0.3, 0.8),
              mix.inputs[7])
    links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.35
    bsdf.inputs["Coat Weight"].default_value = 0.25  # varnish
    bsdf.inputs["Coat Roughness"].default_value = 0.2
    _bump(nodes, links, bsdf, brick.outputs["Factor"], strength=-0.4, distance=0.002)
    return mat


def plaster(name="Wall paint", color=(0.86, 0.84, 0.80)):
    """Painted wall: flat colour with a faint uneven surface."""
    mat, nodes, links, bsdf = _new(name)
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 60.0
    noise.inputs["Detail"].default_value = 4.0
    links.new(_coords(nodes, links), noise.inputs["Vector"])
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    _bump(nodes, links, bsdf, noise.outputs["Factor"], strength=0.08, distance=0.0005)
    return mat


def fabric(color=(0.6, 0.6, 0.62), name="Fabric", thread=0.0012, on="object", sheen=0.4):
    """Woven cloth: two crossed thread directions as a fine bump, plus sheen at grazing
    angles. thread: thread spacing in metres. on: "object" for props, "garment" for
    clothes built by recipes/garments.py."""
    mat, nodes, links, bsdf = _new(name)
    vec = _coords(nodes, links, uv=(on == "garment"))
    waves = []
    for direction in ("X", "Y"):
        wave = nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.bands_direction = direction
        wave.inputs["Scale"].default_value = _bands(thread, on)
        links.new(vec, wave.inputs["Vector"])
        waves.append(wave)
    cross = nodes.new("ShaderNodeMath")
    cross.operation = "MAXIMUM"
    links.new(waves[0].outputs["Factor"], cross.inputs[0])
    links.new(waves[1].outputs["Factor"], cross.inputs[1])
    shade = tuple(c * 0.85 for c in color)
    links.new(_ramp(nodes, links, cross.outputs["Value"], shade, color, 0.2, 0.9), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Sheen Weight"].default_value = sheen
    bsdf.inputs["Sheen Roughness"].default_value = 0.5
    _bump(nodes, links, bsdf, cross.outputs["Value"], strength=0.2, distance=0.0003)
    return mat


def denim(color=(0.10, 0.17, 0.33), name="Denim", on="garment"):
    """Twill: fine diagonal ridges with lighter threads showing, and broad uneven fading."""
    mat, nodes, links, bsdf = _new(name)
    uv = on == "garment"
    twill = nodes.new("ShaderNodeTexWave")
    twill.wave_type = "BANDS"
    twill.bands_direction = "DIAGONAL"
    twill.inputs["Scale"].default_value = _bands(0.0015, on)
    links.new(_coords(nodes, links, uv=uv), twill.inputs["Vector"])
    fade = nodes.new("ShaderNodeTexNoise")
    fade.inputs["Scale"].default_value = 4.0 * (METRES_PER_UV if uv else 1.0)
    fade.inputs["Detail"].default_value = 3.0
    links.new(_coords(nodes, links, uv=uv), fade.inputs["Vector"])
    mix = nodes.new("ShaderNodeMath")
    mix.operation = "MULTIPLY"
    links.new(twill.outputs["Factor"], mix.inputs[0])
    links.new(fade.outputs["Factor"], mix.inputs[1])
    light = tuple(min(1.0, c * 2.2 + 0.06) for c in color)
    links.new(_ramp(nodes, links, mix.outputs["Value"], color, light, 0.05, 0.9), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.8
    bsdf.inputs["Sheen Weight"].default_value = 0.2
    _bump(nodes, links, bsdf, twill.outputs["Factor"], strength=0.25, distance=0.0003)
    return mat


def knit(color=(0.75, 0.2, 0.18), name="Knit", rib=0.006, on="garment"):
    """Knitwear: ribs every few millimetres with a soft, fuzzy sheen."""
    mat, nodes, links, bsdf = _new(name)
    ribs = nodes.new("ShaderNodeTexWave")
    ribs.wave_type = "BANDS"
    ribs.bands_direction = "X"
    ribs.inputs["Scale"].default_value = _bands(rib, on)
    ribs.inputs["Distortion"].default_value = 0.6
    links.new(_coords(nodes, links, uv=(on == "garment")), ribs.inputs["Vector"])
    shade = tuple(c * 0.75 for c in color)
    links.new(_ramp(nodes, links, ribs.outputs["Factor"], shade, color), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    bsdf.inputs["Sheen Weight"].default_value = 0.8
    bsdf.inputs["Sheen Roughness"].default_value = 0.6
    _bump(nodes, links, bsdf, ribs.outputs["Factor"], strength=0.5, distance=0.001)
    return mat


def metal(name="Metal", color=(0.75, 0.75, 0.78), roughness=0.25):
    return plain(name, color, roughness, metallic=1.0)


def ceramic(name="Ceramic", color=(0.92, 0.92, 0.90)):
    """Glazed: smooth coloured body under a clear glossy coat."""
    mat, _, _, bsdf = _new(name)
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.35
    bsdf.inputs["Coat Weight"].default_value = 1.0
    bsdf.inputs["Coat Roughness"].default_value = 0.05
    return mat


def glass(name="Glass", thin=True):
    """Clear glass. thin=True for window panes (no refraction shift through a flat sheet)."""
    mat, _, _, bsdf = _new(name)
    bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.0
    bsdf.inputs["Transmission Weight"].default_value = 1.0
    bsdf.inputs["IOR"].default_value = 1.45
    bsdf.inputs["Thin Wall"].default_value = thin
    return mat


def glow(name="Glow", color=(1.0, 0.85, 0.65), strength=8.0):
    """A surface that emits light, for bulbs and lamp shades."""
    mat, _, _, bsdf = _new(name)
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
    bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def leather(name="Leather", color=(0.22, 0.12, 0.06), on="object", grain=0.0025, wear=0.5):
    """Leather: pebbled grain from cell edges, broad uneven colour, shinier where worn.

    grain: size of the pebbles in metres. wear: 0 new and even, 1 patchy and scuffed.
    """
    mat, nodes, links, bsdf = _new(name)
    k = METRES_PER_UV if on == "garment" else 1.0
    vec = _coords(nodes, links, uv=(on == "garment"))
    cells = nodes.new("ShaderNodeTexVoronoi")
    cells.feature = "DISTANCE_TO_EDGE"
    cells.inputs["Scale"].default_value = k / grain
    links.new(vec, cells.inputs["Vector"])
    patches = nodes.new("ShaderNodeTexNoise")
    patches.inputs["Scale"].default_value = 9.0 * k
    patches.inputs["Detail"].default_value = 5.0
    patches.inputs["Roughness"].default_value = 0.6
    links.new(vec, patches.inputs["Vector"])
    light = tuple(min(1.0, c * (1.0 + 1.6 * wear) + 0.03 * wear) for c in color)
    links.new(_ramp(nodes, links, patches.outputs["Factor"], color, light, 0.35, 0.8), bsdf.inputs["Base Color"])
    rough = nodes.new("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.62
    rough.inputs["To Max"].default_value = 0.62 - 0.3 * wear
    links.new(patches.outputs["Factor"], rough.inputs["Value"])
    links.new(rough.outputs["Result"], bsdf.inputs["Roughness"])
    creases = nodes.new("ShaderNodeTexNoise")
    creases.inputs["Scale"].default_value = 40.0 * k
    creases.inputs["Detail"].default_value = 3.0
    links.new(vec, creases.inputs["Vector"])
    both = nodes.new("ShaderNodeMath")
    both.operation = "ADD"
    ramp_cells = nodes.new("ShaderNodeMapRange")       # cell edges become shallow grooves
    ramp_cells.inputs["From Max"].default_value = 0.12
    links.new(cells.outputs["Distance"], ramp_cells.inputs["Value"])
    links.new(ramp_cells.outputs["Result"], both.inputs[0])
    links.new(creases.outputs["Factor"], both.inputs[1])
    _bump(nodes, links, bsdf, both.outputs["Value"], strength=0.3, distance=0.0004)
    return mat


def hair_fibre(name="Hair", color=(0.08, 0.05, 0.03), roughness=0.45):
    """Material for strand hair and fur (Principled Hair shader, set by colour)."""
    mat, nodes, links, bsdf = _new(name)
    out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
    hair = nodes.new("ShaderNodeBsdfHairPrincipled")
    hair.parametrization = "COLOR"
    hair.inputs["Color"].default_value = (*color, 1.0)
    hair.inputs["Roughness"].default_value = roughness
    hair.inputs["Radial Roughness"].default_value = min(1.0, roughness + 0.2)
    links.new(hair.outputs["BSDF"], out.inputs["Surface"])
    return mat


def soften_skin(mat, amount=0.25, depth=0.006):
    """Let light travel a little way into skin before coming out (subsurface scattering),
    which removes the painted-plastic look. depth is in metres."""
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Subsurface Weight"].default_value = amount
    bsdf.inputs["Subsurface Scale"].default_value = depth
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
    bsdf.inputs["Roughness"].default_value = 0.42
    return mat


def matte_leather(name="Matte leather", color=(0.14, 0.10, 0.09), on="object", mottle=0.35,
                  roughness=0.9):
    """Worn, napped leather (flying-jacket sheepskin, suede): no shine, uneven colour.

    Written after measuring the owner's reference: its jacket's brightest areas are only
    1.14 to 1.23 times its median brightness, where the first glossy leather gave 1.81.
    mottle: how far lighter and darker patches stray from the base colour.
    """
    mat, nodes, links, bsdf = _new(name)
    k = METRES_PER_UV if on == "garment" else 1.0
    vec = _coords(nodes, links, uv=(on == "garment"))
    patches = nodes.new("ShaderNodeTexNoise")
    patches.inputs["Scale"].default_value = 14.0 * k
    patches.inputs["Detail"].default_value = 6.0
    patches.inputs["Roughness"].default_value = 0.65
    links.new(vec, patches.inputs["Vector"])
    dark = tuple(c * (1.0 - mottle) for c in color)
    light = tuple(min(1.0, c * (1.0 + mottle)) for c in color)
    links.new(_ramp(nodes, links, patches.outputs["Factor"], dark, light, 0.3, 0.75), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Specular IOR Level"].default_value = 0.2
    bsdf.inputs["Sheen Weight"].default_value = 0.25
    bsdf.inputs["Sheen Roughness"].default_value = 0.7
    nap = nodes.new("ShaderNodeTexNoise")
    nap.inputs["Scale"].default_value = 900.0 * k
    nap.inputs["Detail"].default_value = 2.0
    links.new(vec, nap.inputs["Vector"])
    _bump(nodes, links, bsdf, nap.outputs["Factor"], strength=0.15, distance=0.0003)
    return mat


def add_stitches(mat, inset=0.0045, stitch=0.0038, gap=0.0022, width=0.0012, rows=1,
                 row_spacing=0.0055, color=None, depth=0.6):
    """Topstitching along every open edge and seam of a garment built by garments.build.

    Reads the mesh attributes edge_dist (distance to the nearest edge, metres) and
    edge_along (position along that edge). A thread is drawn where the distance is
    `inset` (plus `row_spacing` per extra row) and the position falls on a stitch rather
    than a gap. All sizes in metres. The thread is coloured and slightly raised."""
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    dist = nodes.new("ShaderNodeAttribute"); dist.attribute_name = "edge_dist"
    along = nodes.new("ShaderNodeAttribute"); along.attribute_name = "edge_along"

    def math_node(op, a, b=None):
        node = nodes.new("ShaderNodeMath"); node.operation = op
        for i, value in enumerate((a, b)):
            if value is None:
                continue
            if isinstance(value, (int, float)):
                node.inputs[i].default_value = value
            else:
                links.new(value, node.inputs[i])
        return node.outputs[0]

    period = stitch + gap
    phase = math_node("FRACT", math_node("DIVIDE", along.outputs["Fac"], period))
    dash = math_node("LESS_THAN", phase, stitch / period)
    band = None
    for r in range(rows):
        off = math_node("ABSOLUTE", math_node("SUBTRACT", dist.outputs["Fac"], inset + r * row_spacing))
        line = math_node("SUBTRACT", 1.0, math_node("DIVIDE", off, width / 2.0))
        line = math_node("MAXIMUM", line, 0.0)
        band = line if band is None else math_node("MAXIMUM", band, line)
    mask = math_node("MULTIPLY", band, dash)

    base_link = next((l for l in links if l.to_socket == bsdf.inputs["Base Color"]), None)
    thread = nodes.new("ShaderNodeMix"); thread.data_type = "RGBA"
    links.new(mask, thread.inputs[0])
    if base_link is not None:
        links.new(base_link.from_socket, thread.inputs[6])
    else:
        thread.inputs[6].default_value = bsdf.inputs["Base Color"].default_value
    if color is None:
        b = bsdf.inputs["Base Color"].default_value
        color = tuple(min(1.0, 0.08 + 1.6 * b[i]) for i in range(3))
    thread.inputs[7].default_value = (*color, 1.0)
    links.new(thread.outputs[2], bsdf.inputs["Base Color"])
    normal_link = next((l for l in links if l.to_socket == bsdf.inputs["Normal"]), None)
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = depth
    bump.inputs["Distance"].default_value = 0.0006
    links.new(mask, bump.inputs["Height"])
    if normal_link is not None:
        links.new(normal_link.from_socket, bump.inputs["Normal"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat
