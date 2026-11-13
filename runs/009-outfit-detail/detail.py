"""Run 009, step 5: the full outfit with surface detail: weathering (dirt in seams and
cavities, grime patches, rubbed leather edges, scratches), creases, webbing weave.

Usage: python runs/009-outfit-detail/detail.py VIEW [width height samples]
VIEW: chest, belt or full.
"""
import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from recipes import camera, color, garments, hair, human, materials, render, stage, straps, world  # noqa: E402
from tools.image_stats import stats  # noqa: E402

VIEW = sys.argv[1] if len(sys.argv) > 1 else "chest"
W, H, SAMPLES = (int(a) for a in sys.argv[2:5]) if len(sys.argv) > 4 else ((540, 540, 64) if VIEW != "full" else (540, 720, 48))
wear = materials.add_wear
SLIDERS = dict(gender=1.0, age=0.55, muscle=0.6, weight=0.55, height=0.5, caucasian=1, african=0, asian=0)
SMOOTH = 30
CUT = {"thigh": 0.118, "knee": 0.098, "ankle": 0.088, "folds": 0.007}

scene = stage.new_scene()


def stitched(mat, **kw):
    return materials.add_stitches(mat, **kw)


# --- trousers and boots, as step 2 -----------------------------------------------------
cloth_blue = (0.047, 0.06, 0.093)
twill = lambda n: wear(stitched(materials.fabric(cloth_blue, name=n, thread=0.0011, on="garment", sheen=0.3),
                                rows=2, inset=0.004, row_spacing=0.005, color=(0.16, 0.18, 0.22)),
                       grime=0.35, grime_color=(0.07, 0.065, 0.06), patches=0.3)
baggy = garments.baggy_ease(outer=0.012, inner=0.008, waist=0.014, ankle=0.012)
lower = [garments.trousers(name="trousers", ease=baggy, smooth_shell=SMOOTH, thickness=0.0025, cut=CUT, material=twill("Trousers")),
         garments.leg_patch("front_pocket", s=(0.20, 0.86), theta=(-38, 48), ease=baggy + 0.004, material=twill("Pocket"),
                            smooth_shell=SMOOTH, cut=CUT, puff=0.012),
         garments.leg_patch("front_flap", s=(0.16, 0.44), theta=(-41, 51), ease=baggy + 0.0165, thickness=0.003,
                            material=twill("Flap"), smooth_shell=SMOOTH, cut=CUT, puff=0.006, snaps=[(0.395, -28), (0.395, 38)]),
         garments.boots(name="boots", top_at=1.5, ease=0.022, thickness=0.004, smooth_shell=SMOOTH, cut=CUT,
                        material=wear(stitched(materials.matte_leather("Boot", (0.035, 0.03, 0.028), mottle=0.25, roughness=0.6),
                                               inset=0.006, color=(0.09, 0.08, 0.07)),
                                      grime=0.4, grime_color=(0.12, 0.11, 0.1), edge_wear=0.5))]

# --- jacket: panels with stitched seams, shoulder straps, shearling cuffs -------------
JACKET_EASE = 0.03
jacket = garments.top(name="jacket", sleeve=1.95, collar=0.97, hem=-0.12, ease=JACKET_EASE, thickness=0.005,
                      smooth_shell=SMOOTH,
                      material=materials.add_creases(wear(
                          stitched(materials.matte_leather("Jacket", (0.14, 0.10, 0.09), on="garment"),
                                   rows=2, inset=0.005, row_spacing=0.005, color=(0.21, 0.16, 0.14), depth=0.4),
                          grime=0.4, grime_color=(0.07, 0.05, 0.045), edge_wear=0.7, scratches=0.5),
                          scale=14.0, strength=0.45))
jacket["panels"] = {"open_above": 0.9}            # seams at sleeves and centre front become stitched edges
strap = garments.leg_patch("shoulder_strap", limb="arm", s=(-0.02, 0.40), theta=(72, 108), ease=JACKET_EASE + 0.005,
                           thickness=0.003, corner=0.006, smooth_shell=SMOOTH,
                           material=wear(stitched(materials.matte_leather("Strap leather", (0.14, 0.08, 0.068), on="garment"),
                                                  inset=0.004, color=(0.22, 0.15, 0.13), depth=0.4),
                                         grime=0.4, grime_color=(0.07, 0.05, 0.045), edge_wear=0.7))
cuffs = garments.band(name="cuffs", limb="arm", start=1.70, end=1.97, ease=JACKET_EASE + 0.016, thickness=0.02,
                      smooth_shell=SMOOTH, material=materials.plain("Shearling", (0.62, 0.55, 0.42), 0.95))
# Shearling lapel collar lying over the vest (step 7). The first collar was a fur tube.
# Step 8: step 7's outline, inflated into thick cushions (as step 5 had thickness), sitting
# low round the neck, with short dense fuzz. Step 7 was flat and rose like a hood.
collar = garments.lapel_collar(smooth_shell=SMOOTH, neckline=0.98, throat=0.90, roll=0.0, ease=0.088,
                               thickness=0.012, cushion=0.05, cushion_width=0.055,
                               material=wear(materials.shearling(relief=0.45, clump=0.004), grime=0.35, grime_color=(0.32, 0.29, 0.24),
                                             seams=True, seam_width=0.01, cavities=0.6))
shirt = garments.top(name="shirt", sleeve=0.4, collar=0.99, hem=0.08, ease=0.004, smooth_shell=SMOOTH,
                     material=materials.fabric((0.62, 0.58, 0.48), on="garment"))

# --- life vest: padded yellow canvas with vertical channels ---------------------------
vest_mat = materials.add_channels(wear(stitched(materials.fabric((0.55, 0.33, 0.065), name="Vest canvas", thread=0.0013,
                                                                 on="garment", sheen=0.2),
                                                rows=1, inset=0.006, color=(0.75, 0.6, 0.35), depth=0.5),
                                       grime=0.75, grime_color=(0.20, 0.13, 0.05), patches=0.6, seam_width=0.02,
                                       cavities=0.8, patch_scale=11.0),
                                  width=0.075, depth=0.012)
vest = garments.vest(low=0.06, ease=JACKET_EASE + 0.016, thickness=0.028, smooth_shell=SMOOTH, material=vest_mat)

pilot = human.build_human(scene, name="Pilot", skin="middleage_caucasian_male", hair="short02",
                          outfit=tuple(lower) + (shirt, jacket, strap, cuffs, vest, collar), pose="relaxed", **SLIDERS)
vest_obj = next(o for o in pilot.children if o.name.endswith("_vest"))
vest_obj.modifiers["Subdivision"].render_levels = 3      # resolution for the channel displacement

# shearling strands on collar and cuffs
wool = materials.hair_fibre("Wool", (0.56, 0.50, 0.39), roughness=0.95, variation=0.25)
# No strands on the collar: at this distance the clip's collar reads as smooth pile, and
# strands made it look like a towel.
for part_name, count, length in (("_collar", 160000, 0.0035), ("_cuffs", 50000, 0.004)):
    obj = next(o for o in pilot.children if o.name.endswith(part_name))
    v, f = hair.evaluated_mesh(obj)
    roots, normals = hair.sample_surface(v, f, count, seed=len(part_name))
    hair.grow(scene, "Fur" + part_name, roots, normals, length=length, radius=0.0004, material=wool,
              comb=(0.0, 0.0, -0.05), curl=0.45, steps=4, seed=2, length_jitter=0.25)

# --- step 4: harness, release box, inflation hose, belt with cartridges ----------------
STEP4 = "--no-harness" not in sys.argv
if STEP4:
    # The collar is left out: straps pass under it, as in the reference. (With it in, the
    # straps rode over the fur and bunched up.)
    outer = [o for o in pilot.children if o.name.split("_", 1)[-1] in ("vest", "jacket", "trousers")]
    bvh = straps.surface(outer)
    webbing = wear(stitched(materials.webbing("Webbing", (0.44, 0.41, 0.31)),
                            inset=0.003, stitch=0.003, gap=0.0018, color=(0.34, 0.31, 0.24), depth=0.4),
                   grime=0.45, grime_color=(0.2, 0.18, 0.12), patches=0.45, seams=False)
    box_z, front = 1.10, (0.0, 1.0, 0.0)
    strap_ends = []
    for sx in (1.0, -1.0):
        # shoulder strap: over the shoulder from the back, down the vest front to the box
        _, line = straps.strap(scene, f"Harness shoulder {sx:+.0f}", bvh, [
            ((sx * 0.105, 0.6, 1.38), (0.0, -1.0, 0.0)),
            ((sx * 0.11, 0.06, 1.75), (0.0, 0.0, -1.0)),
            ((sx * 0.11, -0.06, 1.75), (0.0, 0.0, -1.0)),
            ((sx * 0.10, -1.0, 1.40), front),
            ((sx * 0.075, -1.0, 1.25), front),
            ((sx * 0.035, -1.0, box_z + 0.03), front)], material=webbing, lift=0.018, parent=pilot)
        # (lift 1.8 cm: the vest's padded channels are added at render time and are not in
        # the surface the straps are laid on; at 3 mm the straps vanished under them)
        strap_ends.append(line[-1])
        # leg strap: from the box down the front of the thigh
        straps.strap(scene, f"Harness leg {sx:+.0f}", bvh, [
            ((sx * 0.03, -1.0, box_z - 0.03), front),
            ((sx * 0.07, -1.0, 0.95), front),
            ((sx * 0.10, -1.0, 0.80), front),
            ((sx * 0.13, -1.0, 0.68), front)], material=webbing, lift=0.008, parent=pilot)
    # The box sits where the shoulder straps meet. (Cast straight at the centre, it landed
    # in the gap between the vest fronts and was hidden.)
    normal = np.array([0.0, -1.0, 0.0])
    centre = np.mean(strap_ends, axis=0) + normal * 0.004
    straps.disc(scene, "Release box", centre, normal, radius=0.036, thickness=0.018,
                material=wear(materials.plain("Release box", (0.70, 0.68, 0.62), 0.4), grime=0.3,
                              grime_color=(0.3, 0.27, 0.22), seams=False, cavities=0.8), parent=pilot)
    straps.disc(scene, "Release dial", centre + normal * 0.018, normal, radius=0.022, thickness=0.006,
                material=materials.metal("Dial", (0.55, 0.55, 0.56), 0.3), parent=pilot)
    # inflation hose on the left chest: from the vest up toward the collar, valve at the top
    hose_pts = []
    for z, x in ((1.20, 0.085), (1.28, 0.105), (1.36, 0.11), (1.43, 0.09), (1.47, 0.06)):
        p, n = straps.hit(bvh, (x, -1.0, z), (0.0, 1.0, 0.0), lift=0.016)
        if p is not None:
            hose_pts.append(p)
    rubber = wear(materials.plain("Rubber", (0.025, 0.025, 0.027), 0.45), grime=0.35,
                  grime_color=(0.09, 0.09, 0.09), seams=False, patches=0.5)       # dust lightens black rubber
    straps.tube(scene, "Inflation hose", hose_pts, radius=0.011, material=rubber, parent=pilot)
    straps.disc(scene, "Hose valve", hose_pts[-1], (0.0, -0.3, 1.0), radius=0.015, thickness=0.02,
                material=materials.metal("Valve", (0.35, 0.33, 0.30), 0.35), parent=pilot)
    # belt round the waist over the jacket, below the vest, with flare cartridges on the front
    BELT_Z = 0.925
    belt_pts = []
    for ang in np.radians(np.arange(-180, 181, 6)):
        d = np.array([np.sin(ang), -np.cos(ang), 0.0])
        p, n = straps.hit(bvh, -d * 1.0 + np.array([0.0, 0.0, BELT_Z]), d)
        if p is not None:
            belt_pts.append((p - d * 0.0, d))
    belt_leather = wear(stitched(materials.matte_leather("Belt", (0.09, 0.055, 0.04), mottle=0.25, roughness=0.55),
                                 inset=0.004, color=(0.2, 0.14, 0.1), depth=0.4),
                        grime=0.35, grime_color=(0.05, 0.035, 0.03), edge_wear=0.6)
    straps.strap(scene, "Belt", bvh, [(p - d * 0.5, d) for p, d in belt_pts], width=0.05, thickness=0.005,
                 material=belt_leather, lift=0.004, parent=pilot)
    casing = materials.metal("Cartridge", (0.62, 0.62, 0.64), 0.3)
    # stacked one above the other in a column, as in the reference
    for k, z in enumerate(BELT_Z + 0.02 - 0.021 * np.arange(7)):
        p, n = straps.hit(bvh, (0.075, -1.0, z), (0.0, 1.0, 0.0), lift=0.017)
        if p is None:
            continue
        side = np.cross(n, (0.0, 0.0, 1.0)); side /= np.linalg.norm(side)
        straps.tube(scene, f"Cartridge {k}", [p - side * 0.032, p, p + side * 0.032], radius=0.0088,
                    material=casing, parent=pilot)

# --- step 6: scarf, hose detail, cartridge holder, hip pouch ----------------------------
if STEP4 and "--step5" not in sys.argv:
    under = straps.surface([o for o in pilot.children if o.name.split("_", 1)[-1] in ("vest", "jacket", "trousers", "shirt")])
    khaki = lambda n: wear(materials.fabric((0.30, 0.29, 0.20), name=n, thread=0.0014, on="object", sheen=0.25),
                           grime=0.6, grime_color=(0.12, 0.11, 0.07), patches=0.55, seams=False, patch_scale=12.0)
    # scarf: a soft band round the neck inside the collar, its end tucked down the front
    scarf = wear(materials.fabric((0.40, 0.38, 0.33), name="Scarf", thread=0.0012, on="object", sheen=0.5),
                 grime=0.4, grime_color=(0.2, 0.19, 0.16), seams=False)
    neck_z = 1.535
    ring = []
    for ang in np.radians(np.arange(-170, 171, 12)):
        d = np.array([np.sin(ang), -np.cos(ang), 0.0])
        ring.append((-d * 0.5 + np.array([0.0, 0.0, neck_z]), d))
    straps.strap(scene, "Scarf wrap", under, ring, width=0.06, thickness=0.012, material=scarf, lift=0.006,
                 parent=pilot)
    tail = [((0.0 + 0.012 * np.sin(k), -1.0, z), (0.0, 1.0, 0.0)) for k, z in enumerate(np.linspace(1.50, 1.33, 8))]
    straps.strap(scene, "Scarf end", under, tail, width=0.07, thickness=0.012, material=scarf, lift=0.012,
                 parent=pilot)
    # hose: outside the shoulder strap, clamped to the vest, valve and mouthpiece at the top
    for old in ("Inflation hose", "Hose valve"):          # replaces the step-4 hose, hidden behind the strap
        bpy.data.objects.remove(bpy.data.objects[old], do_unlink=True)
    hose_line = []
    for z, x in ((1.14, 0.155), (1.22, 0.165), (1.31, 0.16), (1.39, 0.14), (1.45, 0.11), (1.48, 0.085)):
        p_, n_ = straps.hit(bvh, (x, -1.0, z), (0.0, 1.0, 0.0), lift=0.03)
        if p_ is not None:
            hose_line.append(p_)
    straps.tube(scene, "Inflation hose (outside strap)", hose_line, radius=0.011, material=rubber, parent=pilot)
    clamp_metal = wear(materials.metal("Clamp", (0.25, 0.24, 0.22), 0.4), grime=0.4, seams=False,
                       grime_color=(0.1, 0.09, 0.08))
    for k in (1, 3):
        a, b = np.array(hose_line[k]), np.array(hose_line[k + 1])
        axis = (b - a) / np.linalg.norm(b - a)
        straps.disc(scene, f"Hose clamp {k}", a + (b - a) * 0.3, axis, radius=0.0145, thickness=0.009,
                    material=clamp_metal, bevel=0.002, parent=pilot)
    top_end = np.array(hose_line[-1])
    straps.disc(scene, "Hose valve body", top_end, (0.0, -0.4, 1.0), radius=0.017, thickness=0.024,
                material=clamp_metal, parent=pilot)
    straps.disc(scene, "Mouthpiece", top_end + np.array([0.0, -0.01, 0.024]), (0.0, -0.4, 1.0),
                radius=0.011, thickness=0.016, material=rubber, parent=pilot)
    # canvas holder behind the cartridge column, with two keeper straps over it
    holder_top = BELT_Z + 0.04
    straps.strap(scene, "Cartridge holder", under, [((0.075, -1.0, z), (0.0, 1.0, 0.0)) for z in
                 np.linspace(holder_top, holder_top - 0.19, 10)], width=0.085, thickness=0.004,
                 material=khaki("Holder canvas"), lift=0.006, parent=pilot)
    for dx in (-0.024, 0.024):
        straps.strap(scene, f"Cartridge keeper {dx:+.3f}", under, [((0.075 + dx, -1.0, z), (0.0, 1.0, 0.0)) for z in
                     np.linspace(holder_top, holder_top - 0.19, 10)], width=0.012, thickness=0.003,
                     material=khaki("Keeper canvas"), lift=0.030, parent=pilot)
    # map case on the left hip, hanging from the belt on two short straps
    case_at, case_n = straps.hit(under, (1.0, -0.02, 0.80), (-1.0, 0.0, 0.0), lift=0.004)
    case = straps.box(scene, "Map case", case_at, case_n, (0.0, 0.0, 1.0), (0.17, 0.25, 0.05),
                      material=khaki("Case canvas"), bevel=0.012, bulge=0.25, parent=pilot)
    straps.box(scene, "Map case flap", case_at + np.array([0.0, 0.0, 0.085]) + case_n * 0.05,
               case_n, (0.0, 0.0, 1.0), (0.175, 0.085, 0.008), material=khaki("Flap canvas"),
               bevel=0.004, parent=pilot)
    for dy in (-0.05, 0.05):
        straps.tube(scene, f"Case strap {dy:+.2f}", [case_at + np.array([0.0, dy, 0.125]) + case_n * 0.02,
                    case_at + np.array([0.0, dy, 0.18]) + case_n * 0.012], radius=0.006,
                    material=khaki("Case strap"), parent=pilot)

world.sky_world(scene, sun_elevation_deg=48.0, sun_rotation_deg=200.0, strength=0.035)
bpy.ops.mesh.primitive_plane_add(size=400)
bpy.context.object.data.materials.append(materials.plain("Tarmac", (0.11, 0.12, 0.13), 0.85))
VIEWS = {"full": ((0.02, 0.0, 1.22), (0.95, -2.2, 1.35), 70.0),
         "chest": ((0.03, -0.10, 1.27), (0.40, -1.18, 1.36), 60.0),     # matches the reference chest crop
         "belt": ((0.07, -0.10, 0.88), (0.42, -1.18, 0.98), 60.0)}      # matches the reference belt crop
target, eye, lens = VIEWS[VIEW]
aim = stage.empty_at(scene, "Aim", target)
camera.camera_at(scene, eye, aim, lens=lens)
color.set_view(scene, "AgX", look="Medium High Contrast")
render.cycles_cpu(scene, width=W, height=H, samples=SAMPLES)
out = render.render_to(scene, os.path.join(HERE, f"detail_{VIEW}.png"))
print("STATS " + json.dumps({"image": stats(out)}))
