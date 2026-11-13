"""Put motion-capture clips (BVH files) onto characters built by human.py.

Our own BVH reader and retargeting. Written for the CMU motion-capture database in its
"MotionBuilder-friendly" BVH conversion, whose 31 joints carry the same names as the
"cmu_mb" skeleton in the MakeHuman data.

Why copying the clip's rotations straight onto the character does not work: a clip's
rotations are measured from the clip skeleton's own rest pose (arms straight out), while
the character rests with arms angled down. The same numbers mean different poses.

What is done instead, per bone:
  1. Work out how far the clip's joint has turned from its rest, as a rotation in world
     space. In BVH the rest orientation of every joint is "no rotation", so this is just
     the joint's accumulated world rotation.
  2. Find the character bone's "reference" orientation: its own rest orientation, turned
     so the bone points the way the clip's bone points at rest.
  3. The bone's orientation on a frame is (1) applied to (2).
  4. Convert that world orientation into the rotation Blender stores on the bone, which is
     relative to the bone's parent and rest pose.
The hips also move through space; that path is scaled by the ratio of leg lengths so the
character's steps match its own size, then shifted so the feet meet the floor.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

# BVH axes (x left, y up, z forward) -> Blender axes (x left, y back, z up).
C = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])

# Clip joint name -> character bone name, where they differ.
RENAME = {"LeftHandIndex1": "LeftHandFinger1", "RightHandIndex1": "RightHandFinger1"}


# ------------------------------------------------------------------ BVH reading

def read_bvh(path):
    """Parse a BVH file. Returns joints (in file order) and a frames array.

    Each joint: name, parent index (-1 for the root), offset from parent, channel names,
    and the column where its channels start. "End Site" offsets are kept on the joint
    as end_offset so the last bone of a chain has a direction.
    """
    with open(path) as fh:
        tokens = fh.read().split()
    joints, stack, i, column = [], [], 0, 0
    while tokens[i] != "MOTION":
        tok = tokens[i]
        if tok in ("ROOT", "JOINT"):
            joints.append({"name": tokens[i + 1], "parent": stack[-1] if stack else -1,
                           "offset": None, "channels": [], "column": 0, "end_offset": None})
            stack.append(len(joints) - 1)
            i += 2
        elif tok == "End":  # "End Site { OFFSET x y z }"
            joints[stack[-1]]["end_offset"] = np.array([float(t) for t in tokens[i + 4:i + 7]])
            i += 8
        elif tok == "OFFSET":
            joints[stack[-1]]["offset"] = np.array([float(t) for t in tokens[i + 1:i + 4]])
            i += 4
        elif tok == "CHANNELS":
            n = int(tokens[i + 1])
            joints[stack[-1]]["channels"] = tokens[i + 2:i + 2 + n]
            joints[stack[-1]]["column"] = column
            column += n
            i += 2 + n
        elif tok == "}":
            stack.pop()
            i += 1
        else:
            i += 1
    n_frames = int(tokens[tokens.index("Frames:", i) + 1])
    t = tokens.index("Time:", i)
    frame_time = float(tokens[t + 1])
    data = np.array(tokens[t + 2:t + 2 + n_frames * column], dtype=float).reshape(n_frames, column)
    return {"joints": joints, "frames": data, "frame_time": frame_time}


def _axis_rotation(axis, degrees):
    c, s = np.cos(np.radians(degrees)), np.sin(np.radians(degrees))
    z, o = np.zeros_like(c), np.ones_like(c)
    if axis == "X":
        m = [[o, z, z], [z, c, -s], [z, s, c]]
    elif axis == "Y":
        m = [[c, z, s], [z, o, z], [-s, z, c]]
    else:
        m = [[c, -s, z], [s, c, z], [z, z, o]]
    return np.moveaxis(np.array(m), -1, 0)  # (frames, 3, 3)


def world_rotations(clip, frame_indices):
    """World rotation of every joint on the chosen frames, in Blender axes.

    Returns (rotations[frames, joints, 3, 3], root_positions[frames, 3]).
    """
    joints, data = clip["joints"], clip["frames"][frame_indices]
    n = len(frame_indices)
    out = np.zeros((n, len(joints), 3, 3))
    root_pos = np.zeros((n, 3))
    for j, joint in enumerate(joints):
        local = np.tile(np.eye(3), (n, 1, 1))
        pos = np.zeros((n, 3))
        for k, channel in enumerate(joint["channels"]):
            values = data[:, joint["column"] + k]
            if channel.endswith("rotation"):
                local = local @ _axis_rotation(channel[0], values)  # applied in channel order
            else:
                pos[:, "XYZ".index(channel[0])] = values
        out[:, j] = local if joint["parent"] < 0 else out[:, joint["parent"]] @ local
        if joint["parent"] < 0:
            root_pos = pos
    return C @ out @ C.T, root_pos @ C.T


def rest_directions(clip):
    """Candidate directions each clip joint's bone could point at rest, in Blender axes.

    A joint's bone runs to a child joint, but in these clips many children sit at zero
    distance (the hip sockets, the neck on the upper spine, the finger base on the hand),
    and some joints branch (hips, upper spine). So this returns, per joint, the direction
    to the nearest descendant with a real offset along each child branch. retarget() picks
    the candidate that matches the character's own bone.
    """
    joints = clip["joints"]

    def reach(j, accumulated):
        found = []
        children = [c for c, joint in enumerate(joints) if joint["parent"] == j]
        if not children and joints[j]["end_offset"] is not None:
            total = accumulated + joints[j]["end_offset"]
            if np.linalg.norm(total) > 1e-6:
                found.append(total)
        for c in children:
            total = accumulated + joints[c]["offset"]
            if np.linalg.norm(total) > 1e-6:
                found.append(total)
            else:
                found.extend(reach(c, total))
        return found

    return {joint["name"]: [C @ (v / np.linalg.norm(v)) for v in reach(j, np.zeros(3))]
            for j, joint in enumerate(joints)}


# ------------------------------------------------------------------ retargeting

def retarget(armature, clip, start=5, stop=None, step=5):
    """Compute the character's pose for each chosen clip frame.

    step=5 turns the clips' 120 frames per second into 24. Returns a dict with per-frame
    local rotations (as quaternions) per bone, hip locations, and the data needed by
    apply() and by experiments/verify_motion.py.
    """
    stop = stop or len(clip["frames"])
    frame_indices = np.arange(start, stop, step)
    src_rot, src_root = world_rotations(clip, frame_indices)
    src_dir = rest_directions(clip)
    name_of = {j: RENAME.get(joint["name"], joint["name"]) for j, joint in enumerate(clip["joints"])}
    bones = armature.data.bones

    rest, ref, chosen = {}, {}, {}
    for j, joint in enumerate(clip["joints"]):
        bone = bones[name_of[j]]
        r = np.array(bone.matrix_local.to_3x3())
        rest[j] = r
        current = (bone.tail_local - bone.head_local).normalized()
        # Of the clip joint's possible bone directions, take the one nearest the
        # character's bone. If none is within 60 degrees the two bones do not describe the
        # same thing (e.g. the hips), so the character's rest orientation is kept.
        best = max(src_dir[joint["name"]], key=lambda d: current.dot(Vector(d)), default=None)
        if best is None or current.dot(Vector(best)) < 0.5:
            ref[j], chosen[j] = r, None
        else:
            q = current.rotation_difference(Vector(best))
            ref[j], chosen[j] = np.array(q.to_matrix()) @ r, best

    n = len(frame_indices)
    desired = {j: src_rot[:, j] @ ref[j] for j in rest}      # armature-space orientation
    local = {}
    for j, joint in enumerate(clip["joints"]):
        p = joint["parent"]
        if p < 0:
            parent_frame = np.tile(rest[j], (n, 1, 1))
        else:
            parent_frame = desired[p] @ rest[p].T @ rest[j]
        local[j] = np.transpose(parent_frame, (0, 2, 1)) @ desired[j]

    # Hip path: scale by leg length, then drop to the floor.
    def leg(length_of):
        return length_of("LeftUpLeg") + length_of("LeftLeg")
    by_name = {joint["name"]: joint for joint in clip["joints"]}
    src_leg = leg(lambda nm: float(np.linalg.norm(
        next(c for c in clip["joints"] if c["parent"] == clip["joints"].index(by_name[nm]))["offset"])))
    tgt_leg = leg(lambda nm: bones[nm].length)
    scale = tgt_leg / src_leg
    hips = src_root * scale

    # Forward kinematics for the feet, to find where the floor is in the clip.
    heads = {j: np.array(bones[name_of[j]].head_local) for j in rest}
    pos = {}
    for j, joint in enumerate(clip["joints"]):
        p = joint["parent"]
        if p < 0:
            pos[j] = hips
        else:
            pos[j] = pos[p] + (desired[p] @ rest[p].T @ (heads[j] - heads[p]))
    toes = [j for j in rest if name_of[j] in ("LeftToeBase", "RightToeBase")]
    lowest = np.minimum(pos[toes[0]][:, 2], pos[toes[1]][:, 2])
    rest_toe_height = min(heads[t][2] for t in toes)
    hips = hips.copy()
    hips[:, 2] += rest_toe_height - np.percentile(lowest, 5)
    root = next(j for j, joint in enumerate(clip["joints"]) if joint["parent"] < 0)
    shift = hips - pos[root]
    pos = {j: p + shift for j, p in pos.items()}

    return {"frame_indices": frame_indices, "local": local, "desired": desired, "hips": hips,
            "positions": pos, "names": name_of, "root": root, "rest": rest, "scale": scale,
            "source_rotations": src_rot, "source_rest_direction": chosen, "fps": round(1.0 / (clip["frame_time"] * step))}


def apply(armature, motion, first_frame=1):
    """Key the retargeted motion onto the armature, one key per bone per frame."""
    scene = bpy.context.scene
    scene.render.fps = motion["fps"]
    n = len(motion["frame_indices"])
    root = motion["root"]
    root_bone = armature.data.bones[motion["names"][root]]
    root_rest = np.array(root_bone.matrix_local.to_3x3())
    root_head = np.array(root_bone.head_local)
    for j, name in motion["names"].items():
        pbone = armature.pose.bones[name]
        pbone.rotation_mode = "QUATERNION"
        previous = None
        for f in range(n):
            q = Matrix(motion["local"][j][f].tolist()).to_quaternion()
            if previous is not None:
                q.make_compatible(previous)  # avoid sign flips between frames
            previous = q.copy()
            pbone.rotation_quaternion = q
            pbone.keyframe_insert("rotation_quaternion", frame=first_frame + f)
            if j == root:
                pbone.location = (root_rest.T @ (motion["hips"][f] - root_head)).tolist()
                pbone.keyframe_insert("location", frame=first_frame + f)
    scene.frame_start = first_frame
    scene.frame_end = first_frame + n - 1
    return n
