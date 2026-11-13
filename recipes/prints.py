"""Prints on garments: a graphic placed at a point on the body, at a real size, that moves
with the cloth.

The graphic is drawn into a small image. The garment's own texture coordinates (UVs) are
used to find it: around the chosen point, a linear map from surface position (metres,
right and up across the body) to UV is fitted to the garment's vertices, and the shader
inverts it. So the print stays the given width, upright, and follows every fold after
the cloth is simulated (the UVs travel with the vertices).
"""
import bpy
import numpy as np


def _vertex_uvs(mesh):
    uv = np.zeros((len(mesh.loops), 2))
    mesh.uv_layers.active.data.foreach_get("uv", uv.ravel())
    vidx = np.zeros(len(mesh.loops), dtype=int)
    mesh.loops.foreach_get("vertex_index", vidx)
    out = np.zeros((len(mesh.vertices), 2)); cnt = np.zeros(len(mesh.vertices))
    np.add.at(out, vidx, uv); np.add.at(cnt, vidx, 1.0)
    return out / np.maximum(cnt, 1.0)[:, None]


def fit_uv_frame(obj, centre, radius=0.06):
    """Fit uv = uv0 + A @ (right, up) around `centre` (object coordinates of the rest
    mesh). Returns (uv0, inverse of A, fit error in UV units, number of vertices used)."""
    me = obj.data
    co = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    nrm = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("normal", nrm); nrm = nrm.reshape(-1, 3)
    uv = _vertex_uvs(me)
    near = np.linalg.norm(co - centre, axis=1) < radius
    if near.sum() < 6:
        raise ValueError("too few garment vertices near the print centre")
    n = nrm[near].mean(axis=0); n /= np.linalg.norm(n)
    right = np.array([1.0, 0.0, 0.0]) - n * n[0]; right /= np.linalg.norm(right)
    up = np.cross(n, right)
    if up[2] < 0:
        up = -up
    d = co[near] - centre
    p = np.stack([d @ right, d @ up, np.ones(near.sum())], axis=1)
    m, res, _, _ = np.linalg.lstsq(p, uv[near], rcond=None)
    a = m[:2].T                       # 2x2: metres -> uv
    uv0 = m[2]
    err = float(np.sqrt(np.mean((p @ m - uv[near]) ** 2)))
    return uv0, np.linalg.inv(a), err, int(near.sum())


def graphic_image(draw, width_px=512, aspect=0.7, name="Print"):
    """An RGBA image from draw(x, y) -> (rgb, alpha) on a grid with x in [-1, 1] (left to
    right) and y in [-aspect, aspect] (bottom to top)."""
    h = int(width_px * aspect)
    xs = np.linspace(-1.0, 1.0, width_px)
    ys = np.linspace(-aspect, aspect, h)
    x, y = np.meshgrid(xs, ys)
    rgb, alpha = draw(x, y)
    rgba = np.concatenate([rgb, alpha[..., None]], axis=2).astype(np.float32)
    img = bpy.data.images.new(name, width_px, h, alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    return img


def apply(mat, image, uv0, inv, width, aspect=0.7):
    """Lay `image` over the material's base colour, `width` metres wide, centred on uv0."""
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    tc = nodes.new("ShaderNodeTexCoord")
    sub = nodes.new("ShaderNodeVectorMath"); sub.operation = "SUBTRACT"
    links.new(tc.outputs["UV"], sub.inputs[0]); sub.inputs[1].default_value = (uv0[0], uv0[1], 0.0)
    comb = nodes.new("ShaderNodeCombineXYZ")
    # image coordinates: u = right / width + 0.5, v = up / (width * aspect) + 0.5
    for axis, row, span in ((0, inv[0], width), (1, inv[1], width * aspect)):
        dot = nodes.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"
        links.new(sub.outputs["Vector"], dot.inputs[0]); dot.inputs[1].default_value = (row[0], row[1], 0.0)
        scl = nodes.new("ShaderNodeMath"); scl.operation = "MULTIPLY_ADD"
        links.new(dot.outputs["Value"], scl.inputs[0]); scl.inputs[1].default_value = 1.0 / span
        scl.inputs[2].default_value = 0.5
        links.new(scl.outputs[0], comb.inputs["XY"[axis]])
    tex = nodes.new("ShaderNodeTexImage"); tex.image = image; tex.extension = "CLIP"
    links.new(comb.outputs["Vector"], tex.inputs["Vector"])
    old = next((l for l in links if l.to_socket == bsdf.inputs["Base Color"]), None)
    mix = nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    links.new(tex.outputs["Alpha"], mix.inputs["Factor"])
    if old is not None:
        links.new(old.from_socket, mix.inputs["A"])
    else:
        mix.inputs["A"].default_value = bsdf.inputs["Base Color"].default_value
    links.new(tex.outputs["Color"], mix.inputs["B"])
    links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    return mat


def _srgb(c):
    return np.array(c, dtype=float)


def sunrise_badge(x, y):
    """An original small chest graphic: an orange sun with a yellow core rising behind two
    green hills, with a soft printed edge. (The reference's own logo is not copied.)"""
    soft = lambda d, w=0.025: np.clip(0.5 - d / w, 0.0, 1.0)      # anti-aliased edge
    rgb = np.zeros(x.shape + (3,)); alpha = np.zeros(x.shape)
    sun_d = np.hypot(x, y + 0.05) - 0.52
    a = soft(sun_d)                                                 # sun; the hills cover its lower half
    rgb += a[..., None] * _srgb((0.96, 0.45, 0.12)); alpha = np.maximum(alpha, a)
    core = soft(np.hypot(x, y + 0.05) - 0.28)
    rgb = rgb * (1 - core[..., None]) + core[..., None] * _srgb((1.0, 0.80, 0.22)); alpha = np.maximum(alpha, core)
    for amp, off, col in ((0.16, -0.22, (0.16, 0.55, 0.25)), (0.12, -0.40, (0.08, 0.40, 0.18))):
        hill = soft(y - (off + amp * np.cos(x * 2.4 + off * 6)), 0.02) * soft(np.abs(x) - 0.95)
        rgb = rgb * (1 - hill[..., None]) + hill[..., None] * _srgb(col); alpha = np.maximum(alpha, hill)
    rgb = rgb / np.maximum(alpha, 1e-4)[..., None]                   # layers were blended premultiplied
    alpha *= soft(-(y + 0.62), 0.02)                                 # flat bottom edge
    # Values are sRGB: a byte image's pixels are stored in its sRGB colour space.
    return np.clip(rgb, 0, 1), alpha * 0.92                          # ink, not paint: a touch of cloth shows
