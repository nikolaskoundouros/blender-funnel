"""Finished character looks, so a character made once can be rebuilt in any scene.

Each look gathers the settings chosen in a run (and recorded in playbooks/outfit.md), so a
new scene calls one function instead of copying a run script.
"""
import numpy as np

from . import haircut, human, materials, rig, skin

# The boy from run 012 ("My Mom Cracked The Dinosaur" reference): about 12 years old.
CURLY_BOY_SLIDERS = dict(gender=1.0, age=0.22, muscle=0.5, weight=0.45, height=0.45,
                         caucasian=1, african=0, asian=0)
# Head chin-down, tilted and turned a little, as in the reference close-ups (degrees,
# world axes: +X nods down, Y rolls, +Z turns to his left).
CURLY_BOY_HEAD = (14.0, -7.0, 10.0)


def head_pose(nod=0.0, roll=0.0, turn=0.0):
    """Pose steps for the head and neck: a nod shared between the neck and the head."""
    return [("turn", "neck01", "X", nod * 0.4), ("turn", "head", "X", nod * 0.6),
            ("turn", "head", "Y", roll), ("turn", "head", "Z", turn)]


def orange_curls_material():
    """Coral-orange hair, in direct colour mode (melanin mode came out golden).
    Measured against the reference: hue 18 deg, saturation 0.62, value 0.82 (ref 16, 0.73, 0.85)."""
    mat = haircut.material("Curls", melanin=0.25, white=0.0, redness=1.0, roughness=0.45)
    hair = next(n for n in mat.node_tree.nodes if n.type == "BSDF_HAIR_PRINCIPLED")
    hair.parametrization = "COLOR"
    hair.inputs["Color"].default_value = (1.0, 0.075, 0.02, 1.0)
    return mat


def orange_curls(scene, base_verts, armature=None, parent=None, children=150000, seed=0):
    """Thick, frayed, coral curls in a short mop with a lock over the right eye (run 012
    step 18). With an armature the hair follows the head bone."""
    obj, info = haircut.curls(
        scene, base_verts, guides=260, children=children, mat=orange_curls_material(),
        parent=None if armature is not None else parent, radius=0.00005, seed=seed,
        style=lambda sc, p: haircut.curly_mop(sc, p, length=0.065, side=0.32, fringe_cut=0.25, sweep=0.35),
        grow_args=dict(coil_radius=0.009, coil_pitch=0.06, volume=0.028),
        ribbon=dict(width=0.012, thickness=0.005, taper=0.1, frizz=0.0006, fray=0.003, shorten=0.35))
    if armature is not None:
        rig.parent_to_bone(obj, armature, "head")
    return obj, info


def freckled_skin(body, base_verts, count=1000, amount=0.6, tone=(1.0, 0.93, 0.70)):
    """Soft, freckled, peach skin (run 012 steps 7 to 10; tone matched by measured colour)."""
    mat = body.data.materials[0]
    materials.soften_skin(mat)
    freckles, _ = skin.freckle_image(base_verts, count=count)
    skin.add_detail(mat, freckles=freckles, freckle_amount=amount, tone=tone, pores=0.04)
    return mat


def odd_eyes(root, name, right="lightblue", left="green"):
    """Different coloured eyes: `right` is the character's right eye."""
    eyes = next(o for o in [root] + list(root.children_recursive) if o.name == f"{name}_low-poly")
    mat = lambda colour: human.material_from_mhmat(f"{human.PACK}/eyes/materials/{colour}.mhmat", f"eye_{colour}")
    return skin.two_eye_colours(eyes, mat(right), mat(left))


def body_of(root, name):
    """The body mesh of a character, whether or not it was posed."""
    return root if root.type == "MESH" else next(o for o in root.children_recursive if o.name == name)
