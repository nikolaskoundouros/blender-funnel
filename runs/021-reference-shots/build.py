"""Run 021: the boy and his mom in a museum, filmed with the reference clip's own camera moves.

Reference: "My Mom Cracked The Dinosaur" (owner-supplied clip, kept out of git), 0 to 12.6 s.
The camera moves come from the clip analyzer (motion_0_12.json, copied from
clip-analyzer clips/dino/data.json): per frame zoom (% size per second), pan (% of the
frame per second), roll, and the whip / cut / lost status. Each shot gets a hand-set start
camera (eye, aim point, lens); from there every frame is driven only by the analyzer
numbers, so the render shows how much of the reference's camera work the analysis holds.
  zoom   -> dolly toward the aim point (lens change only where the label says zoom)
  pan    -> the camera turns in place; on "orbit" frames it circles the aim point instead
  whip   -> the same, with motion blur on; cut and lost frames hold the camera
One camera per shot, switched by timeline markers, so motion blur never spans a cut.

Usage: python runs/021-reference-shots/build.py [width height samples]
Environment:
  MODE    stills (default: one picture per shot, at its first frame) or anim (FRAMES range)
  FRAMES  first-last analyzer frame for MODE=anim, default 0-378
  HAIR    hair children, default 30000
  DEVICE  cpu (default) or gpu
  OUT     output folder, default <run>/out
"""
import json
import math
import os
import sys
import time

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from recipes import characters, color, lighting, materials, render, stage  # noqa: E402

W, H, SAMPLES = (int(a) for a in sys.argv[1:4]) if len(sys.argv) > 3 else (270, 480, 16)
env = lambda k, d: type(d)(os.environ.get(k, d))
OUT = env("OUT", os.path.join(HERE, "out"))
t0 = time.time()
scene = stage.new_scene()


# ------------------------------------------------------------------ set pieces
def _obj():
    return bpy.context.object


def box(name, center, size, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    o = _obj()
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        m = o.modifiers.new("Bevel", "BEVEL")
        m.width, m.segments = bevel, 2
    o.data.materials.append(mat)
    return o


def ball(name, center, radii, mat, segs=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=segs // 2, radius=1.0, location=center)
    o = _obj()
    o.name = name
    o.scale = radii
    bpy.ops.object.shade_smooth()
    o.data.materials.append(mat)
    return o


def rod(name, a, b, r, mat, r2=None, verts=16):
    """Cylinder (or cone when r2 is given) from point a to point b."""
    a, b = Vector(a), Vector(b)
    d = b - a
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=(a + b) / 2)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=d.length, location=(a + b) / 2)
    o = _obj()
    o.name = name
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    bpy.ops.object.shade_smooth()
    o.data.materials.append(mat)
    return o


def bone_material(name="Bone", dark=(0.03, 0.021, 0.015), light=(0.10, 0.068, 0.04)):
    """Fossil bone: dark brown, mottled by noise, with a matching bump."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 9.0
    noise.inputs["Detail"].default_value = 8.0
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.35, 0.7
    ramp.color_ramp.elements[0].color = (*dark, 1.0)
    ramp.color_ramp.elements[1].color = (*light, 1.0)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.55
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.01
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


CARPET = materials.plain("Carpet", (0.16, 0.022, 0.026), 0.95)
WALL = materials.plain("Wall", (0.36, 0.28, 0.18), 0.9)
BAND = materials.plain("Wall band", (0.70, 0.68, 0.62), 0.7)
CEIL = materials.plain("Ceiling", (0.04, 0.035, 0.03), 0.9)
PLATFORM = materials.plain("Platform", (0.30, 0.30, 0.28), 0.8)
PLINTH = materials.plain("Plinth", (0.07, 0.07, 0.07), 0.6)
BRASS = materials.metal("Brass", (0.80, 0.60, 0.30), 0.3)
ROPE = materials.plain("Rope", (0.50, 0.025, 0.035), 0.7)
BONE = bone_material()

# Room: x -4.5..7, y -5..6.5, 5 m high. Red carpet, beige walls with a white band, dark ceiling.
X0, X1, Y0, Y1, TOP = -4.5, 7.0, -5.0, 6.5, 5.0
box("Floor", ((X0 + X1) / 2, (Y0 + Y1) / 2, -0.01), (X1 - X0, Y1 - Y0, 0.02), CARPET)
box("Ceiling", ((X0 + X1) / 2, (Y0 + Y1) / 2, TOP), (X1 - X0, Y1 - Y0, 0.05), CEIL)
for name, c, s in (("Wall back", ((X0 + X1) / 2, Y1, TOP / 2), (X1 - X0, 0.1, TOP)),
                   ("Wall front", ((X0 + X1) / 2, Y0, TOP / 2), (X1 - X0, 0.1, TOP)),
                   ("Wall left", (X0, (Y0 + Y1) / 2, TOP / 2), (0.1, Y1 - Y0, TOP)),
                   ("Wall right", (X1, (Y0 + Y1) / 2, TOP / 2), (0.1, Y1 - Y0, TOP))):
    box(name, c, s, WALL)
    band = (s[0] + 0.04 if s[0] > 1 else 0.14, s[1] + 0.04 if s[1] > 1 else 0.14, 0.32)
    box(name + " band", (c[0], c[1], 2.55), band, BAND)

# Raised grey platform the skeleton stands on (front edge at y = 0.85).
PT = 0.45
box("Platform", (1.5, 2.85, PT / 2), (10.0, 4.0, PT), PLATFORM, bevel=0.02)

_before_rex = set(bpy.data.objects.keys())
# Stand-in T-Rex: head toward -X, tail toward +X, left foot by the mom.
def leg(side, foot, hip):
    f = Vector((*foot, PT))
    ankle = f + Vector((0.05, 0.03, 0.12))
    hock = ankle + Vector((0.35, 0.12, 1.0))
    knee = hock + Vector((-0.55, 0.08, 0.9))
    hip = Vector(hip)
    for n, a, b, r, r2 in (("meta", ankle, hock, 0.085, 0.07), ("shin", hock, knee, 0.10, 0.12), ("thigh", knee, hip, 0.17, 0.22)):
        rod(f"Rex {side} {n}", a, b, r, BONE, r2=r2)
    for n, p, r in (("ankle", ankle, 0.10), ("hock", hock, 0.10), ("knee", knee, 0.15)):
        ball(f"Rex {side} {n}", p, (r, r, r), BONE)
    for k, turn in enumerate((-0.45, 0.0, 0.45)):                 # three toes forward (-X), spread
        d = Vector((-math.cos(turn), -math.sin(turn) * 0.8 - 0.25, 0.0)).normalized()
        a = ankle + Vector((0, 0, -0.05))
        pts = [a, a + d * 0.22 + Vector((0, 0, -0.04)), a + d * 0.42 + Vector((0, 0, -0.06)), a + d * 0.58 + Vector((0, 0, -0.07))]
        for j in range(3):
            rod(f"Rex {side} toe{k}{j}", pts[j], pts[j + 1], 0.05 - 0.008 * j, BONE, r2=0.045 - 0.008 * j)
            ball(f"Rex {side} knuckle{k}{j}", pts[j + 1], (0.045,) * 3, BONE, segs=12)
        rod(f"Rex {side} claw{k}", pts[3], pts[3] + d * 0.16 + Vector((0, 0, -0.04)), 0.035, BONE, r2=0.002)


HIP = Vector((1.4, 2.0, 3.05))
leg("L", (0.95, 1.05), HIP + Vector((0, -0.3, 0)))
leg("R", (2.0, 2.6), HIP + Vector((0.1, 0.3, 0)))
ball("Rex pelvis", HIP + Vector((0, 0, 0.15)), (0.85, 0.35, 0.45), BONE)
spine = [(6.2, 2.0, 1.9), (5.0, 2.0, 2.45), (3.8, 2.0, 2.85), (2.6, 2.0, 3.15), (1.4, 2.0, 3.35),
         (0.4, 2.0, 3.35), (-0.4, 2.0, 3.45), (-0.9, 2.0, 3.75), (-1.2, 2.0, 3.9)]
for (a, b) in zip(spine[:-1], spine[1:]):
    a, b = Vector(a), Vector(b)
    n = max(3, int((b - a).length / 0.16))
    for k in range(n):
        p = a.lerp(b, k / n)
        r = 0.06 + 0.07 * min(1.0, max(0.0, (6.2 - p.x) / 4.8))
        ball(f"Rex vert {p.x:.2f}", p, (r * 0.8, r, r), BONE, segs=12)
        rod(f"Rex spine {p.x:.2f}", p, p + Vector((0, 0, r * 2.2)), r * 0.25, BONE, r2=r * 0.1, verts=8)
for k in range(9):                                              # ribs hang under the back
    x = -0.2 + k * 0.17
    bpy.ops.mesh.primitive_torus_add(major_radius=0.42 - abs(k - 4) * 0.03, minor_radius=0.025, location=(x, 2.0, 2.95),
                                     rotation=(0.0, math.radians(90), 0.0), major_segments=28, minor_segments=8)
    _obj().data.materials.append(BONE)
SKULL = Vector((-1.75, 2.0, 3.85))
box("Rex skull", SKULL, (0.95, 0.32, 0.36), BONE, bevel=0.06)
jaw = box("Rex jaw", SKULL + Vector((-0.05, 0, -0.27)), (0.85, 0.26, 0.12), BONE, bevel=0.04)
jaw.rotation_euler = (0.0, math.radians(-8), 0.0)
for k in range(10):
    x = SKULL.x - 0.42 + k * 0.07
    for y in (-0.13, 0.13):
        rod("Rex tooth", (x, SKULL.y + y, SKULL.z - 0.16), (x, SKULL.y + y, SKULL.z - 0.26), 0.014, BONE, r2=0.002, verts=8)
for side, y in (("L", 1.8), ("R", 2.2)):
    rod(f"Rex arm {side}", (0.1, y, 2.95), (-0.15, y, 2.6), 0.035, BONE)

# 15 Nov 2026 (Nick: "get a proper dinosaur in there"): DINO_GLB = marcllobet's "Tyrannosaurus rex skeleton" (CC-BY 4.0,
# https://sketchfab.com/3d-models/tyrannosaurus-rex-skeleton-9aabc82e228141b2b8bba56849032430, 63,810 faces).
# It replaces the stand-in above: scaled to DINO_LEN metres long, head turned toward -X, its front-side foot's toe tip put
# on TOE (the shots 9-11 aim there), standing on the platform, every bone in the scene's bone material (Nick: "change its color").
if env("DINO_GLB", ""):
    for _n in [n for n in bpy.data.objects.keys() if n not in _before_rex]:
        bpy.data.objects.remove(bpy.data.objects[_n], do_unlink=True)
    _before_imp = set(bpy.data.objects.keys())
    bpy.ops.import_scene.gltf(filepath=env("DINO_GLB", ""))
    _imp = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in _before_imp]
    _root = bpy.data.objects.new("Rex root", None)
    scene.collection.objects.link(_root)
    for _o in _imp:
        if _o.parent is None:
            _o.parent = _root
    _mesh = [_o for _o in _imp if _o.type == "MESH"]
    bpy.context.view_layer.update()
    _pts = [_o.matrix_world @ Vector(_c) for _o in _mesh for _c in _o.bound_box]
    _len = max(p.y for p in _pts) - min(p.y for p in _pts)             # the model's long axis is Y, head toward -Y
    _s = env("DINO_LEN", 9.0) / _len
    _root.rotation_euler = (0.0, 0.0, math.radians(-90.0))             # head -Y -> -X
    _root.scale = (_s, _s, _s)
    bpy.context.view_layer.update()
    _v = [_o.matrix_world @ _vv.co for _o in _mesh for _vv in _o.data.vertices]
    _zmin = min(p.z for p in _v)
    _low = [p for p in _v if p.z < _zmin + 0.12]
    _mid = (min(p.y for p in _low) + max(p.y for p in _low)) / 2
    _near = [p for p in _low if p.y < _mid]                            # the foot on the front-edge side (small y)
    _tip = min(_near, key=lambda p: p.x)
    _root.location = Vector((0.55 - _tip.x, 1.08 - _tip.y, PT - _zmin))      # TOE is defined later: the same x and y as TOE below (y 1.08 keeps the foot on the platform, front edge 0.85)
    bpy.context.view_layer.update()
    for _o in _mesh:
        _o.data.materials.clear()
        _o.data.materials.append(BONE)
    _v = [_o.matrix_world @ _vv.co for _o in _mesh for _vv in _o.data.vertices]
    print("DINO placed: scale", round(_s, 3), "meshes", len(_mesh), "x", round(min(p.x for p in _v), 2), "to", round(max(p.x for p in _v), 2),
          "y", round(min(p.y for p in _v), 2), "to", round(max(p.y for p in _v), 2), "z", round(min(p.z for p in _v), 2), "to", round(max(p.z for p in _v), 2),
          "front toe tip", tuple(round(c, 2) for c in _tip))

# Rope barrier: brass posts along y = 0.3, red rope sagging between them.
posts = [(-3.0, 0.3), (-1.6, 0.3), (-0.2, 0.3), (1.2, 0.3), (2.6, 0.3), (4.0, 0.3)]
for x, y in posts:
    rod("Post", (x, y, 0.0), (x, y, 0.92), 0.022, BRASS)
    rod("Post base", (x, y, 0.0), (x, y, 0.03), 0.15, BRASS, verts=24)
    ball("Post top", (x, y, 0.95), (0.045,) * 3, BRASS, segs=12)
for (xa, ya), (xb, yb) in zip(posts[:-1], posts[1:]):
    cu = bpy.data.curves.new("Rope", "CURVE")
    cu.dimensions, cu.bevel_depth, cu.bevel_resolution = "3D", 0.018, 3
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(2)
    for p, xyz in zip(sp.bezier_points, ((xa, ya, 0.9), ((xa + xb) / 2, ya, 0.76), (xb, yb, 0.9))):
        p.co = xyz
        p.handle_left_type = p.handle_right_type = "AUTO"
    o = bpy.data.objects.new("Rope", cu)
    o.data.materials.append(ROPE)
    scene.collection.objects.link(o)

# Display plinths with dark skulls on the left.
for y in (-1.2, 0.3, 1.8):
    box("Plinth", (-3.6, y, 0.5), (0.6, 0.6, 1.0), PLINTH)
    ball("Plinth skull", (-3.6, y, 1.13), (0.2, 0.13, 0.13), BONE)

# ------------------------------------------------------------------ the two characters
BOY_AT, BOY_FACING = (-0.5, -0.2), 150.0          # faces +Y, a little toward the mom and the skeleton
MOM_AT, MOM_FACING = (0.75, 0.55), -20.0          # by the left foot, facing the room (-Y), a little toward the boy
# The boy's shirt step (recipes/tee_hang) was only tested at the origin facing 0 and fails elsewhere,
# so he is built there and everything he is made of is then moved into place as one piece.
before = set(scene.objects)
boy, _ = characters.curly_boy(scene, location=(0.0, 0.0, 0.0), facing_deg=0.0, hair_children=env("HAIR", 30000))
bpy.context.view_layer.update()
place = Matrix.Translation((*BOY_AT, 0.0)) @ Matrix.Rotation(math.radians(BOY_FACING), 4, "Z")
made = set(scene.objects) - before
# The boy's curls, measured while he still stands at the origin facing -Y: width across him (X) and centre.
_dg = bpy.context.evaluated_depsgraph_get()
_curls = [o for o in made if any(s.material and s.material.name.startswith("Curls") for s in o.material_slots)]
_cb = [o.matrix_world @ Vector(c) for o in _curls for c in o.evaluated_get(_dg).bound_box]
HAIR_W = max(p.x for p in _cb) - min(p.x for p in _cb)
HAIR_C = place @ (sum(_cb, Vector()) / len(_cb))
print("CURLS", [o.name for o in _curls], "width", round(HAIR_W, 3), "centre after placing", tuple(round(v, 3) for v in HAIR_C))
for o in [o for o in made if o.parent not in made]:
    o.matrix_world = place @ o.matrix_world
_before_mom = set(scene.objects)
mom, _ = characters.mom(scene, location=(*MOM_AT, 0.0), facing_deg=MOM_FACING)
CHARACTER_NAMES = {o.name for o in made | (set(scene.objects) - _before_mom)}
bpy.context.view_layer.update()
build_s = round(time.time() - t0, 1)


def head_of(root):
    """World position of the 'head' bone's base, else 93% up the tallest mesh under root."""
    stack, arm = [root], None
    while stack:
        o = stack.pop()
        if o.type == "ARMATURE":
            arm = o
            break
        stack += list(o.children)
    if arm and "head" in arm.pose.bones:
        return arm.matrix_world @ arm.pose.bones["head"].head
    zs = [(o.matrix_world @ Vector(c)).z for o in root.children_recursive if o.type == "MESH" for c in o.bound_box]
    return Vector((root.location.x, root.location.y, 0.93 * max(zs)))


def facing(deg):
    a = math.radians(deg)
    return Vector((math.sin(a), -math.cos(a), 0.0))      # 0 faces -Y (recipes/human.build_human)


BH, MH = head_of(boy) + Vector((0, 0, 0.06)), head_of(mom) + Vector((0, 0, 0.06))   # about eye level
FB, FM = facing(BOY_FACING), facing(MOM_FACING)
TOE = Vector((0.55, 1.08 if env("DINO_GLB", "") else 0.88, PT + 0.05))       # the new skeleton's toe tip sits at y 1.08
up = Vector((0, 0, 1))
mid = (BH + MH) / 2
side = (MH - BH).cross(up).normalized()
if side.y > 0:
    side = -side                                          # the side toward the room (-Y)
rot = lambda v, deg: Matrix.Rotation(math.radians(deg), 3, "Z") @ v
FM_CAM = rot(FM, 25.0)                                    # mom's front cameras sit off the line to the boy
DMB = Vector(((BH - MH).x, (BH - MH).y, 0.0)).normalized()  # from mom toward the boy
PERP = DMB.cross(up).normalized()
if PERP.y > 0:
    PERP = -PERP
print("HEADS", tuple(round(v, 3) for v in BH), tuple(round(v, 3) for v in MH))

# ------------------------------------------------------------------ shots
# name, nominal first analyzer frame, eye, aim, lens (mm, vertical 36 mm sensor). The shot starts
# at the first settled ("track") frame at or after the nominal frame; whip frames before that
# finish the previous shot (whip out of it).
SHOTS = [
    ("S1 boy extreme close-up", 0, BH + FB * 0.4 + Vector((0, 0, -0.04)), BH + Vector((0, 0, -0.05)), 30.0),
    ("S2 mom medium front", 57, MH + FM_CAM * 1.3 + Vector((0, 0, -0.1)), MH + Vector((0, 0, -0.12)), 35.0),
    ("S3 over mom's back to the boy", 68, MH - DMB * 0.55 + PERP * 0.28 + Vector((0, 0, 0.08)), BH, 30.0),
    ("S4 two-shot medium", 90, mid + side * 2.2 + Vector((0, 0, -0.1)), mid + Vector((0, 0, -0.2)), 30.0),
    ("S5 wide under the skeleton", 101, Vector((1.6, 1.9, 1.3)), Vector((-0.05, 0.2, 0.8)), 18.0),
    ("S6 mom front, dolly in", 120, MH + FM_CAM * 2.6 + Vector((0, 0, -0.1)), MH + Vector((0, 0, -0.15)), 35.0),
    ("S7 wide side, mom at the leg", 161, Vector((2.6, -0.8, 1.2)), Vector((0.5, 0.7, 1.0)), 24.0),
    ("S8 mom medium, foot in front", 176, Vector((1.6, 0.25, 0.95)), MH + Vector((0, 0, -0.2)), 32.0),
    ("S9 hand and crack close", 200, TOE + Vector((-0.35, -0.3, 0.25)), TOE, 40.0),
    ("S10 bone close, dolly out", 226, TOE + (BH - TOE).normalized() * 0.5, TOE, 30.0),
    ("S11 crack close", 280, TOE + Vector((-0.15, -0.5, 0.2)), TOE, 40.0),
    ("S12 boy close-up from below", 302, BH + FB * 0.55 + Vector((0, 0, -0.35)), BH, 30.0),
    ("S13 boy's back, out to the wide", 329, BH - FB * 0.6 + Vector((0, 0, 0.02)), BH + FB, 28.0),
]

M = json.load(open(os.path.join(HERE, "motion_0_12.json")))
FPS, N = M["fps"], M["n"]
ST, LAB, SER = M["status"], M["label"], M["series"]


def smoothed(values, weights=(1, 2, 3, 2, 1)):
    """5-frame weighted average inside each run of tracked frames (never across a whip, cut or lost frame).

    The analyzer's per-frame readings carry measurement noise; driven straight into the camera it
    became real shake (run 021 v1: twice the reference's pan reversals). Measured on 0-12.6 s: this
    cuts the frame-to-frame change (jerk) of zoom, pan and tilt several times.
    The running total (where the camera has got to) is what gets smoothed, with each run's first and
    last value pinned, so every run still adds up to exactly the same move."""
    import numpy as np
    x, w, k = np.array(values, float), np.array(weights, float), len(weights) // 2
    w = w / w.sum()
    y, a = x.copy(), None
    for i in range(len(x) + 1):
        tracked = i < len(x) and ST[i] == "track"
        if tracked and a is None:
            a = i
        if not tracked and a is not None:
            c = np.concatenate([[0.0], np.cumsum(x[a:i])])
            cs = np.convolve(np.pad(c, k, mode="edge"), w, "valid")
            cs[0], cs[-1] = c[0], c[-1]
            y[a:i] = np.diff(cs)
            a = None
    return y.tolist()


if env("SMOOTH", 1):
    SER = {key: smoothed(v) if key in ("zoom_per_s", "pan_x_per_s", "pan_y_per_s") else v for key, v in SER.items()}
if env("SERCORR", ""):         # 15 Nov: closed loop, per-frame corrections added to the analyzer's readings (tools/graph_loop.py)
    _corr = json.load(open(env("SERCORR", "")))
    SER = {key: ([x + y for x, y in zip(v, _corr[key])] if key in _corr else v) for key, v in SER.items()}
    print("SERCORR applied:", {k: round(max(abs(x) for x in v), 1) for k, v in _corr.items()})
ROLL = env("ROLL", 0)          # off: the analyzer's roll reading leans one way and tilted the horizon up to 33 deg per shot
starts = []
for _, nominal, *_ in SHOTS:
    f = nominal
    while f < N - 1 and ST[f] != "track":
        f += 1
    starts.append(f)
ends = [s - 1 for s in starts[1:]] + [N - 1]


def basis(direction, roll_deg):
    f = direction.normalized()
    r = f.cross(up)
    r = r.normalized() if r.length > 1e-6 else Vector((1, 0, 0))
    u = r.cross(f)
    rot = Matrix.Rotation(math.radians(roll_deg), 3, f)
    r, u = rot @ r, rot @ u
    return Matrix((r, u, -f)).transposed()          # columns: camera X, Y, Z (looks along -Z)


def drive(eye, aim, lens, a, b):
    """Camera states for analyzer frames a..b, starting from (eye, aim, lens) at frame a."""
    eye, aim = Vector(eye), Vector(aim)
    v = aim - eye
    D, yaw, pitch, roll = v.length, math.atan2(v.y, v.x), math.asin(max(-1, min(1, v.z / v.length))), 0.0
    dirv = lambda: Vector((math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch)))
    out = []
    last = (0.0, 0.0, 0.0, LAB[a])                           # zoom, pan x, pan y, label of the last real reading
    subject = aim.copy()
    # Whips (14 Nov, owner: "at second 3 the camera nods left to right really fast"): in the reference a run
    # of whip / lost / cut frames is the camera following people who move, so its readings swing right, left,
    # right (frames 83-96: +311, -163, +529 %/s). Copied onto a set where nobody moves, the camera swung across
    # empty walls. Each such run is now ONE turn in ONE direction: the run's net pan, eased in and out.
    whip_pan = {}
    i = a + 1
    while i <= b:
        if ST[i] in ("whip", "lost", "cut"):
            j = i
            while j + 1 <= b and ST[j + 1] in ("whip", "lost", "cut"):
                j += 1
            n = j - i + 1
            w = [math.sin(math.pi * (k + 0.5) / n) for k in range(n)]
            w = [x / sum(w) for x in w]
            netx = sum(M["series"]["pan_x_per_s"][f] for f in range(i, j + 1))
            nety = sum(M["series"]["pan_y_per_s"][f] for f in range(i, j + 1))
            for k in range(n):
                whip_pan[i + k] = (netx * w[k], nety * w[k])
            i = j + 1
        else:
            i += 1
    for i in range(a, b + 1):
        if i > a:
            # The reference camera never stops (1 near-still frame in 379). Where the analyzer has no
            # reading (a lost or cut frame) or an untrusted zoom (the frame after a whip), the camera
            # keeps the last speed instead of freezing; v1 froze there, 14 stop-start frames.
            if ST[i] in ("cut", "lost"):
                z, px, py, lab = last
            else:
                settled = ST[i] == "track" and ST[i - 1] == "track"
                z = SER["zoom_per_s"][i] if settled else last[0]
                px, py, lab = SER["pan_x_per_s"][i], SER["pan_y_per_s"][i], LAB[i]
                if ST[i] == "track":                         # never carry a whip's speed into a lost frame
                    last = (z, px, py, lab)                  # (v2 did: up to 346 %/s where the reference has none)
            if i in whip_pan and not env("WHIPRAW", 0):      # WHIPRAW=1: the reference's own per-frame whip readings (15 Nov)
                px, py = whip_pan[i]
            vfov = 2 * math.atan(18.0 / lens)
            hfov = 2 * math.atan(18.0 * 9 / 16 / lens)
            s = 1.0 + max(-0.25, min(0.25, z / 100.0 / FPS))
            if "zoom" in lab:
                lens *= s                                    # true zoom: the lens changes
            else:
                D /= s                                       # dolly: the camera moves toward the aim point
                eye = aim - dirv() * D
            dx = px / 100.0 / FPS * hfov
            dy = py / 100.0 / FPS * vfov
            pitch = max(-1.4, min(1.4, pitch - dy))
            if lab.startswith("orbit"):                      # circle the aim point
                yaw += abs(dx) * (1 if lab.endswith("right") else -1)
                eye = aim - dirv() * D
            else:                                            # turn in place
                yaw -= dx
                aim = eye + dirv() * D
            # Keep the shot's subject in frame (14 Nov, owner: "keep the camera on its subject"): the turn may
            # put the subject at most 35% of the frame width off centre; past that the camera turns back.
            to_s = subject - eye
            if to_s.length > 1e-6:
                to_s.normalize()
                d = dirv()
                lim, ang = 0.35 * hfov, d.angle(to_s)
                if ang > lim:
                    d = d.slerp(to_s, 1.0 - lim / ang)
                    yaw, pitch = math.atan2(d.y, d.x), math.asin(max(-1.0, min(1.0, d.z)))
                    aim = eye + dirv() * D
            if ROLL and ST[i] == "track" and ST[i - 1] == "track":
                roll +=max(-3.0, min(3.0, SER["roll_deg_per_s"][i] / FPS))
        out.append((eye.copy(), basis(dirv(), roll), lens))
    return out


def solved_states(path, states, a):
    """Replace driven camera states with a camera path solved from the reference by COLMAP (step 3, 14 Nov 2026).

    The solve has its own scale and axes. It is moved onto our boy: its origin = the solved points on the
    reference boy's hair, its up = the cameras' average up, its forward = from the boy toward the first
    frame's camera (that frame shows his face), mapped to our boy's facing. Scale = our curls' width over
    the solved curls' width. Lens from the solved focal length (vertical 36 mm sensor). COLMAP cameras look
    along +Z with +Y down; Blender cameras look along -Z with +Y up."""
    J = json.load(open(path))
    up, c = Vector(J["up"]), Vector(J["boy"])
    P = {int(f): v for f, v in J["path"].items()}
    e1 = Vector(P[min(P)]["center"]) - c
    e1 = (e1 - up * e1.dot(up)).normalized()
    e2 = e1.cross(up)
    F, Z = FB.normalized(), Vector((0.0, 0.0, 1.0))
    R = F.cross(Z)
    to_ours = lambda v: R * v.dot(e2) + F * v.dot(e1) + Z * v.dot(up)
    # SOLVED_SCALE: correction measured on the render. First try (curls' bounding box, which includes stray
    # strands) put the camera too far: the boy's hair came out 0.63 of the reference's height (frames 12-48).
    scale = HAIR_W / J["hair"]["width"] * env("SOLVED_SCALE", 1.0)
    lens = 18.0 * J["camera"]["params"][0] / (J["camera"]["height"] / 2)
    # SOLVED_FRONT: the solve's anchor is the FRONT of the reference boy's hair (the points the camera sees);
    # ours was the centre of the curls, so the close-up started too near (hair 1.25x the reference's height at
    # 0 s while the solved distances matched). The path moves toward the first camera by this share of its distance.
    d0 = (Vector(P[min(P)]["center"]) - c).length * scale
    shift = F * env("SOLVED_FRONT", 0.0) * d0
    print(f"SOLVED {path}: {len(P)} frames, scale {scale:.4f}, lens {lens:.1f} mm, front shift {shift.length:.3f} m")
    out = list(states)
    for f, s in P.items():
        if a <= f < a + len(states):
            Rt = Matrix(s["R"]).transposed()
            X = to_ours(Rt @ Vector((1.0, 0.0, 0.0)))
            Y = to_ours(-(Rt @ Vector((0.0, 1.0, 0.0))))
            Zc = to_ours(-(Rt @ Vector((0.0, 0.0, 1.0))))
            out[f - a] = (HAIR_C + shift + to_ours(Vector(s["center"]) - c) * scale, Matrix((X, Y, Zc)).transposed(), lens)
    return out


def solved_shot(path, eye, aim, states, a):
    """A shot's camera path solved from the reference (solve_shots.py), lined up on our hand-set first camera.

    Reference subject (the solved points in the middle of the shot's middle frame) -> our aim point; the
    reference's first camera -> our hand-set eye's direction and distance; the solve's up -> +Z. Lens fixed at
    the opening shot's solved value. Frames the solve missed hold the nearest solved camera. Returns the driven
    states unchanged when the solve is too thin to trust (under 75% of frames, no subject points, error >= 2 px)."""
    J = json.load(open(path))
    q = J["quality"]
    if J.get("anchor") is None or q["solved"] < 0.75 * q["frames"] or q["reproj_px"] >= 2.0:
        print(f"SOLVED {path}: not used ({q}); driven camera kept")
        return states
    up, anc = Vector(J["up"]), Vector(J["anchor"])
    P = {int(f): v for f, v in J["path"].items()}
    C0 = Vector(P[min(P)]["center"])
    e1 = C0 - anc
    e1 = (e1 - up * e1.dot(up)).normalized()
    e2 = e1.cross(up)
    v = Vector(eye) - Vector(aim)
    F, Z = Vector((v.x, v.y, 0.0)).normalized(), Vector((0.0, 0.0, 1.0))
    R = F.cross(Z)
    to_ours = lambda w: R * w.dot(e2) + F * w.dot(e1) + Z * w.dot(up)
    scale = v.length / (C0 - anc).length
    lens = 18.0 * 961.431 / 480.0
    out = []
    for i in range(len(states)):
        f = min(P, key=lambda g: abs(g - (a + i)))
        Rt = Matrix(P[f]["R"]).transposed()
        X = to_ours(Rt @ Vector((1.0, 0.0, 0.0)))
        Y = to_ours(-(Rt @ Vector((0.0, 1.0, 0.0))))
        Zc = to_ours(-(Rt @ Vector((0.0, 0.0, 1.0))))
        out.append((Vector(aim) + to_ours(Vector(P[f]["center"]) - anc) * scale, Matrix((X, Y, Zc)).transposed(), lens))
    print(f"SOLVED {path}: used, {q['solved']}/{q['frames']} frames, scale {scale:.3f}")
    return out


scene.render.fps, scene.render.fps_base = 30, 1.0
scene.render.use_motion_blur = True
scene.render.motion_blur_shutter = env("SHUTTER", 0.5)
def button_plan():
    """0 to 10 s built only from camera buttons (recipes/camera_moves), one plan per shot, chosen by the
    script rules measured in the clip analyzer (14 Nov 2026): spoken line -> close-up of the speaker with a
    push; a named person -> that person, landing about 0.5 s after the word; bone / crack -> close on the
    bone, no face; size words -> wide. Timings inside each shot are the reference's (frame numbers)."""
    from recipes import camera_moves as cm
    az = lambda v: math.degrees(math.atan2(v.y, v.x))
    boy_az, mom_az = az(FB), az(FM)
    mid_floor = (BH + MH) / 2 - Vector((0, 0, 0.6))
    ECU, CU, MED, WIDE = (cm.distance_for(k) for k in ("ECU", "CU", "MED", "WIDE"))

    def fit(states, n):                      # exactly n frames: trim, or continue the last frame's motion
        states = list(states)[:n]
        while len(states) < n:
            (e1, r1, l1), (e0, r0, l0) = states[-1], states[-2] if len(states) > 1 else states[-1]
            states.append((e1 + (e1 - e0), r1, l1))
        return states

    def last_eye(states):
        return states[-1][0]

    ZOOMS = env("ZOOMS", 0)
    if ZOOMS:
        from recipes import zoom_presets as zp
        ZP = zp.load()

        def Z(pid, target, az_, el_, d, **kw):
            """One preset zoom: its camera states and the distance the camera ends at."""
            return zp.zoom_states(ZP[pid], target, az_, el_, d, **kw), d / (1 + ZP[pid]["size_pct"] / 100)

    plan = {}
    # S1 0-59 "I was at the archaeology museum with my mom": pull out from the boy's face, orbit to his
    # right side rising, small push, then whip to Mom on "mom".
    if ZOOMS:
        s, d1 = Z("Z1", BH, boy_az, -5, ECU)                                   # 0.00 s pull out
        s += cm.orbit(BH, boy_az, -5, d1, 39, angle=-92.0, rise=0.17)
        o_az = boy_az - 92.0
        s2, _ = Z("Z2", BH, o_az, math.degrees(math.asin(math.sin(math.radians(-5)) + 0.17)), d1)   # 1.63 s push in
        s += s2
    else:
        s = cm.push(BH, boy_az, -5, ECU, ECU * 3.1, 10)
        s += cm.orbit(BH, boy_az, -5, ECU * 3.1, 39, angle=-92.0, rise=0.17)
        o_az = boy_az - 92.0
        s += cm.push(BH, o_az, math.degrees(math.asin(math.sin(math.radians(-5)) + 0.17)), ECU * 3.1, ECU * 3.1 / 1.35, 6)
    s += cm.whip(last_eye(s), BH, MH, 5)
    plan["S1"] = (s, BH, None)                # the last 5 frames whip away to Mom on purpose
    # S2 60-68 "when she": Mom, medium, off the line to the boy.
    plan["S2"] = (cm.hold(MH, mom_az + 25, -3, MED, 9), MH, None)
    # S3 69-96 "dragged me over": over Mom's back to the boy, small pull out, then one whip to the pair.
    a_mb = az(BH - MH) + 180 + 8
    d_mb = (BH - MH).length + 0.3            # 0.6 put the camera inside the T-Rex's left leg (the check moved it 25 frames)
    if ZOOMS:
        s, d3 = Z("Z3", BH, a_mb, 10, d_mb)                                    # 2.37 s pull out
        s += cm.hold(BH, a_mb, 10, d3, 16)
    else:
        s = cm.push(BH, a_mb, 10, d_mb, d_mb * 1.12, 8) + cm.hold(BH, a_mb, 10, d_mb * 1.12, 14)
    s += cm.whip(last_eye(s), BH, (BH + MH) / 2, 6)
    plan["S3"] = (s, BH, None)                # the last 6 frames whip to the pair on purpose
    # S4 97-101 "the 'Do Not": both, medium, from the room side.
    plan["S4"] = (cm.hold((BH + MH) / 2 - Vector((0, 0, 0.2)), az(side), 0, cm.distance_for_pair(BH, MH), 5), (BH + MH) / 2, None)
    # S5 102-119 "Touch' rope": wide, low, from under the skeleton.
    e5 = Vector((1.6, 1.9, 1.3))
    v5 = e5 - mid_floor
    plan["S5"] = (cm.hold(mid_floor, az(v5), math.degrees(math.asin(v5.z / v5.length)), v5.length, 18, drift=0.06), mid_floor, None)
    # S6 120-166 "This is a T-Rex" (spoken by Mom): medium to close-up push, +289% in 23 frames, then a small orbit.
    if ZOOMS:
        s = cm.hold(MH, mom_az + 25, -3, MED, 2)
        s4, d6 = Z("Z4", MH, mom_az + 25, -3, MED)                              # 4.07 s dolly in
        s += s4 + cm.orbit(MH, mom_az + 25, -3, d6, 22, angle=10.0, rise=0.0, slows=())
    else:
        s = cm.hold(MH, mom_az + 25, -3, MED, 2) + cm.push(MH, mom_az + 25, -3, MED, MED / 3.89, 23)
        s += cm.orbit(MH, mom_az + 25, -3, MED / 3.89, 22, angle=10.0, rise=0.0, slows=())
    plan["S6"] = (s, MH, None)
    # S7 167-175 "She slapped": wide side, Mom at the leg.
    v7 = Vector((2.6, -0.8, 1.2)) - MH
    plan["S7"] = (cm.hold(MH, az(v7), math.degrees(math.asin(v7.z / v7.length)), v7.length, 9, drift=0.05), MH, None)
    # S8 176-199 "its leg and a": Mom medium, two pushes (+25% then +48%).
    if ZOOMS:
        s, d8 = Z("Z5", MH, mom_az + 40, 0, MED * 1.2)                          # 5.87 s push in
        s8, _ = Z("Z6", MH, mom_az + 40, 0, d8)                                 # 6.13 s dolly in
        s += s8
    else:
        s = cm.push(MH, mom_az + 40, 0, MED * 1.2, MED * 1.2 / 1.25, 8)
        s += cm.push(MH, mom_az + 40, 0, MED * 1.2 / 1.25, MED * 1.2 / 1.25 / 1.48, 16)
    plan["S8"] = (s, MH, None)
    # S9 200-225 "small crack formed": close on the bone, no face, slow move.
    plan["S9"] = (cm.hold(TOE, az(Vector((-0.35, -0.3, 0))), 25, CU * 0.8, 26, drift=0.08), TOE, None)
    # S10 226-280 "on its leg where I was standing": close on the bone, then pull back 4.35x with the aim
    # sliding to the boy ("I").
    a10 = az(BH - TOE)
    if ZOOMS:
        s7, d10 = Z("Z7", TOE, a10, 28, ECU, aim_to=BH)                         # 8.00 s dolly out, aim slides to the boy
        s = cm.hold(TOE, a10, 28, ECU, 14, drift=0.15) + s7 + cm.hold(BH, a10, 28, d10, 10)
    else:
        s = cm.hold(TOE, a10, 28, ECU, 14, drift=0.15) + cm.push(TOE, a10, 28, ECU, ECU * 4.35, 31, aim_to=BH) + cm.hold(BH, a10, 28, ECU * 4.35, 10)   # 15 deg passed through the rope
    plan["S10"] = (s, TOE, BH)
    # S11 281-302 "If that crack spread": close on the bone from the other side.
    plan["S11"] = (cm.hold(TOE, az(Vector((-0.15, -0.5, 0))), 20, CU * 0.8, 22, drift=0.08), TOE, None)
    if ZOOMS:
        # S12 302-328: boy from below. NOT matched to the reference's small orbit: a held shot with a slow drift.
        e12 = BH + FB * 0.55 + Vector((0, 0, -0.35))
        v12 = e12 - BH
        plan["S12"] = (cm.hold(BH, az(v12), math.degrees(math.asin(v12.z / v12.length)), v12.length, 27, drift=0.06), BH, None)
        # S13 329-378: from the boy's back, the 10.97 s move (size -29%) then the 11.33 s pull out (-29%), then held.
        e13 = BH - FB * 0.6 + Vector((0, 0, 0.02))
        v13 = e13 - BH
        a13, el13, d13 = az(v13), math.degrees(math.asin(v13.z / v13.length)), v13.length
        s13a, d13a = Z("Z8", BH, a13, el13, d13)
        s13b, d13b = Z("Z9", BH, a13, el13, d13a)
        plan["S13"] = (s13a + s13b + cm.hold(BH, a13, el13, d13b, 26, drift=0.04), BH, None)
    if ZOOMS and env("WHIPTAIL", 1):
        # 15 Nov: every shot change is a whip, not a hard cut. The reference's whip / lost / cut frames just before each
        # shot start (ST != "track") are the shot's tail: those frames turn the camera on the spot, from where it was
        # looking to where the NEXT shot's first frame looks, so the picture is already pointing the right way at the
        # change; the blur comes from the longer shutter on those frames (WHIPSHUTTER).
        names = [f"S{i + 1}" for i in range(len(SHOTS))]
        fitted = {nm: fit(plan[nm][0], ends[i] - starts[i] + 1) for i, nm in enumerate(names) if nm in plan}
        for i, nm in enumerate(names[:-1]):
            nxt = names[i + 1]
            if nm not in fitted or nxt not in fitted:
                continue
            n = len(fitted[nm])
            w = 0
            while ends[i] - w >= starts[i] and ST[ends[i] - w] != "track":
                w += 1
            w = min(w, n - 2)
            if w < 1:
                continue
            e0, r0, ln = fitted[nm][n - w - 1]
            f0 = -(r0 @ Vector((0.0, 0.0, 1.0)))
            f1 = -(fitted[nxt][0][1] @ Vector((0.0, 0.0, 1.0)))
            fitted[nm] = fitted[nm][:n - w] + cm.whip(e0, e0 + f0 * 3.0, e0 + f1 * 3.0, w)
            print(f"WHIPTAIL {nm}: last {w} frames whip {math.degrees(f0.angle(f1)):.0f} deg toward {nxt}")
        for nm, st_ in fitted.items():
            plan[nm] = (st_, plan[nm][1], plan[nm][2])
    return plan, fit


BUTTONS, BUTTON_FIT = button_plan() if (env("BUTTONS", 0) or env("ZOOMS", 0)) else ({}, None)
cams = []
for k, ((name, _, eye, aim, lens), a, b) in enumerate(zip(SHOTS, starts, ends)):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    cam.data.sensor_fit, cam.data.sensor_height = "VERTICAL", 36.0
    cam.data.clip_start = 0.02
    cam.rotation_mode = "XYZ"
    scene.collection.objects.link(cam)
    prev = None
    states = drive(eye, aim, lens, a, b)
    if (env("BUTTONS", 0) or env("ZOOMS", 0)) and name.split()[0] in BUTTONS:
        from recipes import camera_moves as cm
        planned, subj, subj2 = BUTTONS[name.split()[0]]
        states = BUTTON_FIT(planned, b - a + 1)
        half = len(states) // 2 if subj2 is not None else len(states)
        states_a, rep_a = cm.check_states(scene, states[:half], subj, see_through=CHARACTER_NAMES)
        states_b, rep_b = cm.check_states(scene, states[half:], subj2, see_through=CHARACTER_NAMES) if subj2 is not None else ([], {})
        states = states_a + states_b
        print(f"BUTTONS {name}: {len(states)} frames, checks {rep_a} {rep_b}")
    if k == 0 and env("SOLVED", ""):
        states = solved_states(os.path.join(HERE, env("SOLVED", "")), states, a)
    shot_file = os.path.join(HERE, env("SOLVED_DIR", "solved"), name.split()[0], "path.json")
    if k > 0 and env("SOLVED_DIR", "") and os.path.exists(shot_file):
        states = solved_shot(shot_file, eye, aim, states, a)
    for i, (e, rot, ln) in zip(range(a, b + 1), states):
        eul = rot.to_euler("XYZ", prev) if prev else rot.to_euler("XYZ")
        prev = eul
        cam.location, cam.rotation_euler, cam.data.lens = e, eul, ln
        for path in ("location", "rotation_euler"):
            cam.keyframe_insert(path, frame=i + 1)        # Blender frame = analyzer frame + 1
        cam.data.keyframe_insert("lens", frame=i + 1)
    scene.timeline_markers.new(name, frame=a + 1).camera = cam
    cams.append((name, cam, a, b))
    print(f"SHOT {name}: frames {a}-{b} ({a / FPS:.2f}-{(b + 1) / FPS:.2f} s)")

WSH = env("WHIPSHUTTER", 0.0)          # longer blur on the reference's whip / lost / cut frames (15 Nov)
if WSH:
    try:
        for f in range(N):
            scene.render.motion_blur_shutter = WSH if ST[f] != "track" else env("SHUTTER", 0.5)
            scene.render.keyframe_insert("motion_blur_shutter", frame=f + 1)
        print("WHIPSHUTTER keyed", WSH, "on", sum(1 for x in ST if x != "track"), "frames")
    except Exception as e:
        print("WHIPSHUTTER failed:", repr(e))
        scene.render.motion_blur_shutter = env("SHUTTER", 0.5)

if env("MOVETEST", 0):
    # One button over 2.73-4.13 s (frames 82-124): the reference's "over" to "rope" move (orbit, fly-back,
    # arc in). Settings come from the environment so several versions can be rendered and the one whose
    # clip-analyzer readings match the reference's is kept.
    from recipes import camera_moves as cm
    wide_eye = Vector((1.6, 1.9, 1.3))
    if env("MT_WIDE", 0.0):         # 15 Nov: the fly-back spot on the side the two face (the old spot saw Mom's back), MT_WIDE metres out, low
        fr_ = (FB + FM).normalized()
        wide_eye = Vector((((BH + MH) / 2).x + fr_.x * env("MT_WIDE", 0.0), ((BH + MH) / 2).y + fr_.y * env("MT_WIDE", 0.0), 0.9))
        print("MOVETEST wide eye", tuple(round(v, 2) for v in wide_eye), "faces", tuple(round(v, 2) for v in fr_))
    mt = cm.orbit_flyback_arc(BH, MH, wide_eye, (BH + MH) / 2 - Vector((0, 0, 0.6)),
                              start_az=math.degrees(math.atan2(FB.y, FB.x)), angle=env("MT_ANGLE", 230.0),
                              d_orbit=env("MT_D", 1.3) or cm.distance_for_pair(BH, MH), el_orbit=env("MT_EL", -12.0), arc_angle=env("MT_ARC", -33.0),
                              arc_close=env("MT_CLOSE", 0.46), arc_aim_mix=env("MT_AIMMIX", 1.0),
                              pair_mid=(BH + MH) / 2 if env("MT_PAIR", 0) else None)
    parts = ((0, 19, (BH + MH) / 2), (19, 24, (BH + MH) / 2 - Vector((0, 0, 0.6))), (24, 43, MH))
    checked = []
    for i0, i1, subj in parts:
        st, rep = cm.check_states(scene, mt[i0:i1], subj, see_through=CHARACTER_NAMES)
        checked += st
        print("MOVETEST part", i0, i1, rep)
    cam = bpy.data.objects.new("Move test", bpy.data.cameras.new("Move test"))
    cam.data.sensor_fit, cam.data.sensor_height, cam.data.clip_start = "VERTICAL", 36.0, 0.02
    scene.collection.objects.link(cam)
    prev = None
    for i, (e, rot, ln) in enumerate(checked):
        eul = rot.to_euler("XYZ", prev) if prev else rot.to_euler("XYZ")
        prev = eul
        cam.location, cam.rotation_euler, cam.data.lens = e, eul, ln
        cam.keyframe_insert("location", frame=83 + i)
        cam.keyframe_insert("rotation_euler", frame=83 + i)
        cam.data.keyframe_insert("lens", frame=83 + i)
    for m in [m for m in scene.timeline_markers if 83 <= m.frame <= 125]:
        scene.timeline_markers.remove(m)
    scene.timeline_markers.new("Move test", frame=83).camera = cam
    cams.append(("Move test", cam, 82, 124))
    scene.render.motion_blur_shutter = env("MT_SHUTTER", 0.5)
    print("MOVETEST", dict(angle=env("MT_ANGLE", 230.0), d=env("MT_D", 1.3), el=env("MT_EL", -12.0), arc=env("MT_ARC", -33.0),
                           shutter=env("MT_SHUTTER", 0.5)), len(checked), "frames")

# ------------------------------------------------------------------ light and render settings
for k, (x, y) in enumerate((x, y) for x in (-2.0, 1.2, 4.4) for y in (-2.6, 1.6)):
    lighting.area_light(scene, f"Ceiling {k}", (x, y, TOP - 0.3), stage.empty_at(scene, f"Down {k}", (x, y, 0.0)),
                        power=60.0, size=1.6, color=(1.0, 0.78, 0.55))
lighting.area_light(scene, "Rex wash", (0.0, -1.8, 4.4), stage.empty_at(scene, "Rex aim", (1.0, 2.0, 2.4)),
                    power=150.0, size=1.0, color=(1.0, 0.82, 0.6))
world = bpy.data.worlds.new("World")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.03, 0.024, 0.018, 1.0)
scene.world = world
scene.cycles_curves.shape = "THICK"
color.set_view(scene, "AgX", look="Medium High Contrast", exposure=env("EXPOSURE", -0.4))
device = render.cycles_gpu(scene, W, H, SAMPLES) if env("DEVICE", "cpu") == "gpu" else (render.cycles_cpu(scene, W, H, SAMPLES) or "CPU")
print("DEVICE", device)

os.makedirs(OUT, exist_ok=True)
if env("MODE", "stills") == "path":                         # no render: every frame's active camera, for checks
    fa, fb = (int(v) for v in env("FRAMES", "0-378").split("-"))
    rows = []
    for f in range(fa, fb + 1):
        scene.frame_set(f + 1)
        cam = next(c for n, c, a2, b2 in reversed(cams) if a2 <= f <= b2)     # a later override (MOVETEST) wins
        m = cam.matrix_world
        rows.append(dict(f=f, shot=cam.name, eye=list(m.translation), look=list(-m.col[2].xyz), up=list(m.col[1].xyz),
                         lens=cam.data.lens, aim=list(next((s[3] for s in SHOTS if s[0] == cam.name), (BH + MH) / 2))))
    json.dump(rows, open(os.path.join(OUT, "camera_path.json"), "w"))
    print("PATH", len(rows), "frames ->", os.path.join(OUT, "camera_path.json"))
elif env("MODE", "stills") == "stills" and env("OVERVIEW", 0):
    # 15 Nov: whole-room views from inside the corners (wide lens), to see the room, the dinosaur, the rope and the two people at once
    LENS_O = env("OVERVIEW_LENS", 26.0)
    scene.timeline_markers.clear()          # markers bind the shot cameras and override scene.camera on every frame change
    for nm, e, a_ in (("corner_right_front", (6.3, -4.5, 3.9), (0.3, 1.0, 1.0)), ("corner_left_front", (-4.0, -4.5, 3.9), (1.2, 1.2, 1.0)),
                      ("corner_left_back", (-4.0, 6.0, 3.9), (1.5, -0.2, 1.0)), ("corner_right_back", (6.3, 6.0, 3.9), (0.5, 0.0, 1.0))):
        oc = bpy.data.objects.new("Overview " + nm, bpy.data.cameras.new("Overview " + nm))
        oc.data.sensor_fit, oc.data.sensor_height, oc.data.lens, oc.data.clip_start = "VERTICAL", 36.0, LENS_O, 0.02
        oc.location = Vector(e)
        oc.rotation_euler = (Vector(a_) - Vector(e)).to_track_quat("-Z", "Y").to_euler()
        scene.collection.objects.link(oc)
        scene.camera = oc
        render.render_to(scene, os.path.join(OUT, f"overview_{nm}.png"))
        print("OVERVIEW rendered", nm)
elif env("MODE", "stills") == "stills":
    for name, cam, a, b in cams:
        scene.camera = cam
        scene.frame_set(a + 1)
        render.render_to(scene, os.path.join(OUT, f"still_{a:03d}.png"))
else:
    fa, fb = (int(v) for v in env("FRAMES", "0-378").split("-"))
    scene.frame_start, scene.frame_end = fa + 1, fb + 1
    scene.render.filepath = os.path.join(OUT, "frames", "f")
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_persistent_data = True              # only the cameras move: keep the scene between frames
    bpy.ops.render.render(animation=True)
print("STATS " + json.dumps({"build_seconds": build_s, "total_seconds": round(time.time() - t0, 1), "device": device,
                             "shots": [(n, a, b) for n, _, a, b in cams]}))
