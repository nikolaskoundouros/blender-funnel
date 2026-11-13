"""Skin detail on a character: freckles, pores and tone, added to the MakeHuman skin.

Freckles are painted into an image in the skin's UV layout (the base mesh's own texture
coordinates), so they stay on the nose and cheeks when the body is posed or sculpted.
Where they go is decided in 3D from face landmarks: dense over the nose bridge and upper
cheeks, sparse elsewhere on the face, as in the owner's reference for run 012. Each
freckle is a soft dot of a real size in millimetres, converted to pixels from how much
UV space that part of the face uses.

Pores are a fine bump from a noise texture in UV space; tone is a gentle colour
multiply on the skin texture.
"""
import bpy
import numpy as np

from . import accessories, human


def _face_tris(base_verts):
    """Body triangles with 3D corners and UV corners (quads split in two)."""
    _, uvs, faces, face_uvs = human.base_mesh()
    vb = human.to_blender(base_verts)
    tri_v, tri_uv = [], []
    for f, fu in zip(faces, face_uvs):
        if not all(v < human.BODY_VERTS for v in f):
            continue
        for a, b, c in ((0, 1, 2), (0, 2, 3)) if len(f) == 4 else ((0, 1, 2),):
            tri_v.append((f[a], f[b], f[c]))
            tri_uv.append((fu[a], fu[b], fu[c]))
    tv = vb[np.array(tri_v)]
    tu = np.asarray(uvs)[np.array(tri_uv)]
    return tv, tu


def freckle_density(points, lm, spread=1.0):
    """0..1 freckle density at 3D points: a band over the nose and upper cheeks, a light
    sprinkle on the rest of the front of the face."""
    nose = lm["nose"]
    x = points[:, 0]
    dz = points[:, 2] - (nose[2] + 0.012)                 # band centred just above the nose tip
    band = np.exp(-(x / (0.048 * spread)) ** 2 - (dz / (0.022 * spread)) ** 2)
    front = points[:, 1] < lm["front_y"] + 0.07          # only the front of the head
    face = (points[:, 2] > lm["lip"][2] - 0.05) & (points[:, 2] < lm["eye_z"] + 0.07)
    return np.where(front & face, 0.15 + 0.85 * band, 0.0)


def freckle_image(base_verts, count=1400, size=2048, radius_mm=(0.5, 1.4), seed=0, spread=1.0,
                  name="Freckles"):
    """An image (alpha = freckle strength) in the skin's UV layout."""
    rng = np.random.default_rng(seed)
    lm = accessories.face_landmarks(base_verts)
    tv, tu = _face_tris(base_verts)
    area = 0.5 * np.linalg.norm(np.cross(tv[:, 1] - tv[:, 0], tv[:, 2] - tv[:, 0]), axis=1)
    e1, e2 = tu[:, 1] - tu[:, 0], tu[:, 2] - tu[:, 0]
    uv_area = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    centre = tv.mean(axis=1)
    weight = area * freckle_density(centre, lm, spread)
    if weight.sum() == 0:
        raise ValueError("no face area found for freckles")
    pick = rng.choice(len(tv), count, p=weight / weight.sum())
    r1, r2 = rng.random(count), rng.random(count)
    s = np.sqrt(r1)
    bary = np.stack([1 - s, s * (1 - r2), s * r2], axis=1)
    uv = np.einsum("ij,ijk->ik", bary, tu[pick])
    px_per_m = np.sqrt(uv_area[pick] / np.maximum(area[pick], 1e-12)) * size
    rad_px = rng.uniform(*radius_mm, count) / 1000.0 * px_per_m
    strength = rng.uniform(0.35, 1.0, count)
    img = np.zeros((size, size), dtype=np.float32)
    for (u, v), r, k in zip(uv, rad_px, strength):
        cx, cy = u * size, v * size
        rr = int(np.ceil(r * 1.6)) + 1
        x0, x1 = max(int(cx) - rr, 0), min(int(cx) + rr + 1, size)
        y0, y1 = max(int(cy) - rr, 0), min(int(cy) + rr + 1, size)
        if x0 >= x1 or y0 >= y1:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        d = np.hypot(xx + 0.5 - cx, yy + 0.5 - cy) / max(r, 0.5)
        img[y0:y1, x0:x1] = np.maximum(img[y0:y1, x0:x1], k * np.clip(1.2 - d, 0.0, 1.0) ** 0.7)
    rgba = np.zeros((size, size, 4), dtype=np.float32)
    rgba[..., :3] = 1.0
    rgba[..., 3] = img
    image = bpy.data.images.new(name, size, size, alpha=True)
    image.pixels.foreach_set(rgba.ravel())
    image.pack()
    return image, {"freckles": int(count), "median_radius_px": round(float(np.median(rad_px)), 2)}


def add_detail(mat, freckles=None, freckle_color=(0.42, 0.17, 0.07), freckle_amount=0.75,
               tone=(1.0, 1.0, 1.0), pores=0.04, pore_scale=900.0, roughness=0.45):
    """Add freckles (an image from `freckle_image`), a colour tone and pores to a skin
    material made by human.material_from_mhmat."""
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    base_link = next((l for l in links if l.to_socket == bsdf.inputs["Base Color"]), None)
    base = base_link.from_socket if base_link else None
    uv = nodes.new("ShaderNodeTexCoord")
    toned = nodes.new("ShaderNodeMix"); toned.data_type = "RGBA"; toned.blend_type = "MULTIPLY"
    toned.inputs["Factor"].default_value = 1.0
    if base is not None:
        links.new(base, toned.inputs["A"])
    else:
        toned.inputs["A"].default_value = bsdf.inputs["Base Color"].default_value
    toned.inputs["B"].default_value = tuple(tone) + (1.0,)
    out = toned.outputs["Result"]
    if freckles is not None:
        tex = nodes.new("ShaderNodeTexImage"); tex.image = freckles
        tex.image.colorspace_settings.name = "Non-Color"
        links.new(uv.outputs["UV"], tex.inputs["Vector"])
        amount = nodes.new("ShaderNodeMath"); amount.operation = "MULTIPLY"
        links.new(tex.outputs["Alpha"], amount.inputs[0]); amount.inputs[1].default_value = freckle_amount
        mix = nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
        links.new(amount.outputs[0], mix.inputs["Factor"])
        links.new(out, mix.inputs["A"])
        mix.inputs["B"].default_value = tuple(c * 1.6 for c in freckle_color) + (1.0,)
        out = mix.outputs["Result"]
    links.new(out, bsdf.inputs["Base Color"])
    if pores:
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = pore_scale
        noise.inputs["Detail"].default_value = 2.0
        links.new(uv.outputs["UV"], noise.inputs["Vector"])
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = pores
        links.new(noise.outputs["Factor"], bump.inputs["Height"])
        old = next((l for l in links if l.to_socket == bsdf.inputs["Normal"]), None)
        if old is not None:
            links.new(old.from_socket, bump.inputs["Normal"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def two_eye_colours(eyes_obj, right_material, left_material):
    """Heterochromia: give the character's right eye (x < 0) one material and the left
    eye another. Works on the fitted MakeHuman eyes mesh (both eyes in one object)."""
    me = eyes_obj.data
    me.materials.clear()
    me.materials.append(right_material)
    me.materials.append(left_material)
    co = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    idx = [1 if co[list(p.vertices)].mean(axis=0)[0] > 0 else 0 for p in me.polygons]
    me.polygons.foreach_set("material_index", idx)
    return eyes_obj
