"""Skeleton, skin weights and poses for characters built by human.py.

Our own reader for MakeHuman's rig and weights files (format: mpfb2 docs/fileformats/
rig.md and weights.md). How it works:

  1. Joint positions are not stored as coordinates. Each bone end names a small helper
     cube (or one or two vertices) on the base mesh, and sits at its centre. Because the
     helpers morph with the body, the skeleton fits any body shape automatically.
  2. A weights file lists, per bone, which base-mesh vertices follow it and how strongly.
  3. Clothes and hair have no weights of their own. Each of their vertices is tied to
     three base vertices (see human.fit), so its weights are the same blend of those
     three vertices' weights.
"""
import json
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import human

_GROUPS = None


def _joint_groups():
    global _GROUPS
    if _GROUPS is None:
        with open(os.path.join(human.DATA, "mesh_metadata", "basemesh_vertex_groups.json")) as fh:
            _GROUPS = json.load(fh)
    return _GROUPS


def _position(spec, verts_bl):
    """Resolve one bone end to a point, in Blender coordinates."""
    strategy = spec["strategy"]
    if strategy == "CUBE":
        idx = [i for a, b in _joint_groups()[spec["cube_name"]] for i in range(a, b + 1)]
    elif strategy == "VERTEX":
        idx = [spec["vertex_index"]]
    elif strategy == "MEAN":
        idx = spec["vertex_indices"]
    else:
        raise ValueError(f"unsupported bone position strategy {strategy!r}")
    return Vector(verts_bl[idx].mean(axis=0))


def read_rig(rig_name):
    """Bone definitions for a rig. Files come in two layouts: older ones are the bone
    table itself; newer ones (e.g. mixamo) wrap it as {"bones": ..., "version": ...}."""
    with open(os.path.join(human.DATA, "rigs", "standard", f"rig.{rig_name}.json")) as fh:
        data = json.load(fh)
    return data["bones"] if "bones" in data and "version" in data else data


def _weight_matrix(rig_name, bone_names, normalize=True):
    """Dense (base vertices x bones) weight table from the weights file.

    Rows are scaled to sum to 1. The default and game_engine files already do; the mixamo
    file as shipped has sums from 0.2 to 1.5 (measured in experiments/verify_rig.py, R1).
    """
    with open(os.path.join(human.DATA, "rigs", "standard", f"weights.{rig_name}.json")) as fh:
        weights = json.load(fh)["weights"]
    table = np.zeros((len(human.base_mesh()[0]), len(bone_names)), dtype=np.float32)
    column = {name: i for i, name in enumerate(bone_names)}
    for bone, pairs in weights.items():
        if bone in column and pairs:
            arr = np.array(pairs)
            table[arr[:, 0].astype(int), column[bone]] = arr[:, 1]
    if normalize:
        sums = table.sum(axis=1, keepdims=True)
        table = np.divide(table, sums, out=table, where=sums > 1e-6)
    return table


def _assign(obj, table, bone_names, armature):
    """Create vertex groups from a (vertices x bones) table and bind the armature."""
    for col, bone in enumerate(bone_names):
        rows = np.nonzero(table[:, col] > 1e-4)[0]
        if not len(rows):
            continue
        group = obj.vertex_groups.new(name=bone)
        for r in rows:
            group.add([int(r)], float(table[r, col]), "REPLACE")
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = armature
    # Bend first, then add thickness and smoothing: cheaper and cleaner than the reverse.
    obj.modifiers.move(len(obj.modifiers) - 1, 0)
    obj.parent = armature


def attach(scene, name, base_verts, body, fitted_items, rig_name="default"):
    """Build an armature for a body and bind the body and its fitted items to it.

    fitted_items: list of (object, parsed mhclo dict) as produced in human.build_human.
    """
    bones = read_rig(rig_name)
    verts_bl = human.to_blender(base_verts)

    arm_data = bpy.data.armatures.new(f"{name}_rig")
    armature = bpy.data.objects.new(f"{name}_rig", arm_data)
    scene.collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    for bone_name, spec in bones.items():
        eb = arm_data.edit_bones.new(bone_name)
        eb.head = _position(spec["head"], verts_bl)
        eb.tail = _position(spec["tail"], verts_bl)
        eb.roll = spec.get("roll", 0.0)
    for bone_name, spec in bones.items():
        if spec.get("parent"):
            eb = arm_data.edit_bones[bone_name]
            eb.parent = arm_data.edit_bones[spec["parent"]]
            eb.use_connect = bool(spec.get("use_connect", False))
    bpy.ops.object.mode_set(mode="OBJECT")

    bone_names = list(bones.keys())
    table = _weight_matrix(rig_name, bone_names)
    _assign(body, table[:human.BODY_VERTS], bone_names, armature)
    for obj, item in fitted_items:
        blended = (table[item["tri"]] * item["weight"][:, :, None].astype(np.float32)).sum(axis=1)
        _assign(obj, blended, bone_names, armature)
    return armature


def rotate_bone(armature, bone_name, axis, degrees):
    """Rotate a bone about a world axis ('X', 'Y' or 'Z') through its own joint.

    World axes are used so a pose does not depend on each bone's roll. With the character
    facing -Y: +X is the character's left, +Z is up.
    """
    pbone = armature.pose.bones[bone_name]
    world = armature.matrix_world @ pbone.matrix
    pivot = world.translation.copy()
    turn = (Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(degrees), 4, axis)
            @ Matrix.Translation(-pivot))
    pbone.matrix = armature.matrix_world.inverted() @ turn @ world
    bpy.context.view_layer.update()  # children must see the new parent pose


def aim_limb(armature, bone, toward, direction):
    """Rotate a bone about its own joint until the next joint lies in a given direction.

    bone: the bone to turn (e.g. "upperarm01.L"); toward: the bone that starts at the next
    joint (e.g. "lowerarm01.L" for the elbow); direction: world vector, not normalised.
    Describing a pose by where limbs point makes it independent of the modelling pose and
    of body shape. (A first attempt used fixed rotation angles; arms overshot and crossed
    in front of the body because the modelling pose already holds them partly down.)
    """
    bpy.context.view_layer.update()
    pbone = armature.pose.bones[bone]
    world = armature.matrix_world @ pbone.matrix
    pivot = world.translation.copy()
    current = (armature.matrix_world @ armature.pose.bones[toward].matrix).translation - pivot
    turn = current.rotation_difference(Vector(direction)).to_matrix().to_4x4()
    pbone.matrix = (armature.matrix_world.inverted() @ Matrix.Translation(pivot) @ turn
                    @ Matrix.Translation(-pivot) @ world)
    bpy.context.view_layer.update()


def _arm(side, upper, fore):
    """Aim steps for one arm. Directions are given for the left arm and mirrored for the right."""
    m = 1.0 if side == "L" else -1.0
    return [
        ("aim", f"upperarm01.{side}", f"lowerarm01.{side}", (m * upper[0], upper[1], upper[2])),
        ("aim", f"lowerarm01.{side}", f"wrist.{side}", (m * fore[0], fore[1], fore[2])),
    ]


# With the character facing -Y: +X is its left, -Y is forward, +Z is up.
_DOWN = ((0.20, 0.0, -1.0), (0.10, -0.20, -1.0))          # hanging, elbow slightly bent
_FORWARD = ((0.22, -0.55, -1.0), (-0.30, -1.0, 0.05))     # elbows bent, hands together in front
POSES = {
    "relaxed": _arm("L", *_DOWN) + _arm("R", *_DOWN),
    # Seated-pilot arms: hands forward as if holding a control stick.
    "stick": _arm("L", *_FORWARD) + _arm("R", *_FORWARD),
    # Left hand raised in greeting, right arm hanging, head turned a little.
    "wave": _arm("R", *_DOWN) + _arm("L", (1.0, -0.1, 0.15), (0.25, -0.15, 1.0))
            + [("turn", "head", "Z", 10)],
    # Elbows out and back, forearms angled in toward the hips.
    "akimbo": _arm("L", (0.70, 0.30, -1.0), (-0.55, -0.30, -0.75))
              + _arm("R", (0.70, 0.30, -1.0), (-0.55, -0.30, -0.75)),
}


def apply_pose(armature, pose):
    """Apply a named pose from POSES, or a list of steps:
    ("aim", bone, toward_bone, direction) or ("turn", bone, world_axis, degrees)."""
    steps = POSES[pose] if isinstance(pose, str) else pose
    for step in steps:
        if step[0] == "aim":
            aim_limb(armature, step[1], step[2], step[3])
        else:
            rotate_bone(armature, step[1], step[2], step[3])
