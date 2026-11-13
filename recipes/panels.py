"""Garments sewn from flat panels by cloth simulation (route F).

From the owner's pro-pants tutorial (notes/tutorial-pro-pants.md): two flat rectangles,
one in front of the legs and one behind, each with a slit cut up to the crotch, joined by
sewing edges at the outer side seams and the inner leg seams. With gravity off, the sewing
springs pull the panels together round the legs and a small shrink settles them, which
gives trousers with natural folds without drafting a pattern.

Built directly as one mesh: the sewing edges are loose edges, which `cloth.add_cloth`
turns into sewing springs.
"""
import bpy
import numpy as np

from . import human


def leg_box(base_verts):
    """Size of the legs and hips from the body (Blender coordinates): waist and ankle
    heights, crotch height, hip half-width, front and back of the hips."""
    full = human.to_blender(base_verts)
    vb = full[:human.BODY_VERTS]
    from . import rig
    bones = rig.read_rig("default")
    pos = lambda b, end="head": np.array(rig._position(bones[b][end], full))   # joints use helper cubes
    hip_z = float(pos("pelvis.L")[2])
    knee_z = float(pos("lowerleg01.L")[2]) if "lowerleg01.L" in bones else hip_z * 0.55
    ankle_z = float(pos("foot.L")[2]) if "foot.L" in bones else 0.08
    from . import garments
    part = garments._body_coordinates()["part"][:human.BODY_VERTS]
    lower = np.isin(part, ("leg", "torso")) & (vb[:, 2] < hip_z + 0.12) & (vb[:, 2] > ankle_z)
    legs = vb[lower]                       # not the hands, which hang at hip height in the rest pose
    crotch = vb[(np.abs(vb[:, 0]) < 0.012) & (vb[:, 2] < hip_z + 0.05)]
    return {"waist_z": hip_z + 0.10, "hip_z": hip_z, "knee_z": knee_z, "ankle_z": ankle_z,
            "crotch_z": float(crotch[:, 2].min()) if len(crotch) else hip_z - 0.08,
            "half_width": float(np.abs(legs[:, 0]).max()),
            "front_y": float(legs[:, 1].min()), "back_y": float(legs[:, 1].max())}


def trouser_panels(base_verts, step=0.012, room=0.03, gap=0.035, slit=0.018, length_to=None,
                   waist=None):
    """Front and back panels with sewing edges. room: extra half-width beyond the hips.
    gap: distance in front of / behind the body. slit: half-width of the crotch slit.
    Returns (verts, faces, sewing edges)."""
    box = leg_box(base_verts)
    top = waist if waist is not None else box["waist_z"]
    bottom = length_to if length_to is not None else box["ankle_z"]
    w = box["half_width"] + room
    xs = np.arange(-w, w + 1e-9, step)
    zs = np.arange(bottom, top + 1e-9, step)
    verts, faces, ids = [], [], []
    for y in (box["front_y"] - gap, box["back_y"] + gap):
        idx = -np.ones((len(zs), len(xs)), dtype=int)
        for j, z in enumerate(zs):
            for i, x in enumerate(xs):
                if abs(x) < slit and z < box["crotch_z"]:
                    continue                                   # the slit between the legs
                idx[j, i] = len(verts)
                verts.append((x, y, z))
        for j in range(len(zs) - 1):
            for i in range(len(xs) - 1):
                q = (idx[j, i], idx[j, i + 1], idx[j + 1, i + 1], idx[j + 1, i])
                if min(q) >= 0:
                    faces.append(q)
        ids.append(idx)
    front, back = ids
    sew = []
    for j in range(len(zs)):
        for i in (0, len(xs) - 1):                             # outer side seams
            sew.append((front[j, i], back[j, i]))
        if zs[j] < box["crotch_z"]:                            # inner leg seams
            for i in range(len(xs)):
                if abs(xs[i]) >= slit and (i == 0 or abs(xs[i - 1]) < slit or (i + 1 < len(xs) and abs(xs[i + 1]) < slit)):
                    if front[j, i] >= 0 and back[j, i] >= 0 and 0 < i < len(xs) - 1:
                        sew.append((front[j, i], back[j, i]))
    # crotch: join the top of the slit front to back
    return np.array(verts), faces, sew, box


def build_trousers(scene, base_verts, name="Trousers", material=None, **kw):
    """The panel mesh as an object, ready for cloth (see cloth.add_cloth)."""
    verts, faces, sew, box = trouser_panels(base_verts, **kw)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [tuple(e) for e in sew], [tuple(f) for f in faces])
    me.update()
    me.shade_smooth()
    if material is not None:
        me.materials.append(material)
    obj = bpy.data.objects.new(name, me)
    scene.collection.objects.link(obj)
    return obj, {"verts": len(verts), "faces": len(faces), "sewing_edges": len(sew), **{k: round(v, 3) for k, v in box.items()}}
