# Playbook: making an outfit for a character

Purpose: make each new outfit faster than the last. This file is the current best
procedure, in order, with the settings that worked and the failures already paid for.
Update it after every outfit (rules at the bottom). History lives in `outfit-log.md`.

## Step 0. Read the reference (5 min)

- Extract frames (`ffmpeg -ss T -i clip -frames:v 1`) and list every layer from skin
  outward: under-layer, main garment, outer layer, straps, headgear, hand and footwear.
- For each layer note: material, fit (tight, loose, draped), where it opens, what trims it.
- Decide per layer which route below it takes. Tight layers: route A. Anything that should
  hang or crease: route B. Anything needing real tailoring: route C.

## Step 0b. Measure the reference's colours (2 min)

- Overlay a grid on the frame, pick one patch per material, and record its median colour
  and its highlight ratio (98th percentile brightness over median). Save as a palette file.
- Highlight ratio tells you the finish: about 1.1 to 1.25 is matte (use
  `materials.matte_leather`), 1.8 and above is glossy.
- Displayed colour is roughly surface colour times light. Under daylight, dividing the
  linear value by about 0.9 gave usable base colours (jacket 0.14, 0.10, 0.09).
- Do not judge darkness by eye under studio light: the first leather was darkened to
  0.03 and ended up four times too dark.

## Step 1. Build the character with a complete collision body (1 min)

    human.build_human(..., pose="<pose>", collider=True, **sliders)

- `collider=True` is required for any cloth. The visible body has holes under garments.
- Record the sliders; the same values are needed for measuring and for landmarks.

## Route A. Shell garment (seconds; skin-tight layers, hats, gloves, boots)

    garments.top(...), trousers(...), skirt(...), boots(...), helmet(...), collar(...)

- Cut from the body's helper shells by body coordinates; fits any body, follows any pose.
- Use for: undershirts, leggings, socks, close caps, anything hidden under other layers.
- Known limits: skin-tight; hems slightly wavy; `top(sleeve=0)` (sleeveless) cuts wrongly.
- Colours are scene-linear: dark leather is about 0.03, not 0.10.

## Route B. Draped shell (about 45 s simulation; jackets, coats, loose tops)

1. Make a shell with generous ease: `top(ease=0.035, thickness=0.005)`.
2. Optional panels: `spec["panels"] = {"open_above": 0.62}` splits fronts and sleeves and
   sews them; the front stays open above that torso height. Put a shirt shell underneath.
3. Pin the yoke and the sleeve tops (weights from `garments.coordinate(binding, "h")` and
   `"arm"`); everything else free.
4. `cloth.add_cloth(obj, pin_weights=pin, fabric="leather", spare=0.06, sewing_force=60)`
5. `cloth.simulate(scene, 45)` and render on the last frame.

Settings that worked: ease 3.5 cm, spare 6%, leather preset, 45 frames, collider
thickness 6 mm. Result: folds, visible seams, under 0.1% of points inside the skin.

## Route C. Sewn pattern (2 to 3 min simulation; real tailoring) — NOT YET RELIABLE

1. Measure: `tools/measure_body.py REF.yaml OUT.yaml <sliders>` (bpy environment).
2. Draft: `tools/draft_pattern.py GARMENTCODE_DIR OUT.yaml pattern.json <design keys>`
   (GarmentCode environment). Design keys are listed in `notes/garment-prior-work.md`.
3. Place and mesh: `patterns.build(scene, pattern, to_metres=0.01, offset=(0, 0, 0.045))`.
4. Sew gently: sewing force 2.5, quality 18, collision quality 8, collider thickness 12 mm,
   gravity off until frame 80 then faded in by 110, 140 frames.

Status: body, collar and lapels sit correctly; sleeves reach the arms but bunch above the
elbows; one seam stays open. Do not use for a deliverable until that is fixed.

## Route D. Detail pieces (seconds; pockets, flaps, shoulder straps, cuffs, vests, harness)

Worked example: `runs/009-outfit-detail/trousers.py` and `upper.py`.

- **One shared base surface.** Give every loose piece the same `smooth_shell` (30 worked)
  and, for loose trousers, the same `cut` (straight-leg radii). Pieces then lie exactly on
  each other. Ease is per piece: trousers 1 to 1.4 cm, pocket +0.4 cm, flap +1.65 cm,
  jacket 3 cm, strap +0.5 cm, cuffs +1.6 cm, vest +1.6 cm.
- **Loose trousers:** `garments.trousers(cut={"thigh": 0.118, "knee": 0.098, "ankle":
  0.088, "folds": 0.007}, smooth_shell=30)`. Inflating the tights only makes fatter leggings.
- **Pockets, flaps, straps on limbs:** `garments.leg_patch(limb="leg"|"arm", s=(from, to),
  theta=(from, to), puff=..., snaps=[(s, theta)])`. Exact rounded rectangles wrapped onto
  the limb: straight edges, clean corners. theta 0 is the front, 90 the outside (top of the
  arm). Front thigh pocket: s 0.20 to 0.86, theta -38 to 48. Flap: s 0.16 to 0.44.
- **Cuffs and boot tops:** `garments.band(limb, start, end)`.
- **Vest:** `garments.vest(low, high, opening)`; padded channels with
  `materials.add_channels(mat, width=0.075, depth=0.012)` and render subdivision 3.
- **Stitching:** `materials.add_stitches(mat, rows=2, inset=0.004, row_spacing=0.005)`.
  Works on any piece built by `garments.build` or `straps.strap`: the mesh carries the
  distance to its edges and seams. Panel seams (`spec["panels"]`) get stitched too.
- **Straps, hoses, hardware over the outfit:** `straps.surface(outer objects)`, then
  `straps.strap(waypoint rays)`, `straps.tube(points)`, `straps.disc(centre, normal)`.
  Build them last, after everything they lie on.

## Step 2. Trim and accessories (seconds to a minute)

- Fur and hair: `hair.sample_surface` on the evaluated trim mesh, then `hair.grow`.
  Shearling in the reference is short and matte: length about 6 mm, low curl spread,
  slightly yellow. (First attempt used 22 mm and looked like fluff.)
- Goggles: `accessories.goggles(scene, base_verts, parent=root)`.
- Strands and accessories are placed once; build them after posing and simulating.

## Step 3. Check before rendering (under a minute)

- Fraction of garment points more than 3 mm inside the complete body: aim for under 1%.
- Seam gaps closed (route B and C): mean under 5 mm.
- Small test render at 432x540, 48 samples (about 20 s) before any full-size render.
- Put the test next to the reference: `tools/side_by_side.py`.

## Head pieces (run 010)

Worked example: `runs/010-head/head.py`.

- Hood: `garments.flying_helmet(opening=(0.052, 0.083))`, relaxed with the face edge held
  (`spec["relax"] = 14`); rolled edge from `straps.boundary_loops` + `straps.ring_tube`;
  panel seams with `materials.add_seam_lines(..., color=` close to the leather `)`.
- Goggles: `garments.goggle_mask()` (exact outline on the smoothed face) plus
  `accessories.goggle_lenses(..., standoff=0.020, overlap=1.12)` for clean domed lenses
  and chrome rims; `materials.frosted_glass()` for grimy edges.
- Moustache: `garments.moustache_base()` (dark layer on the raw face) under about
  20,000 short strands combed hard sideways and down.
- Expression: `build_human(expression={"mouth-corner-puller": 0.9, ...})`; 34 units in
  `assets/mpfb_data/targets/expression/units/<ethnicity>/`.

## Hair (run 011)

`haircut.haircut(scene, base_verts, guides=400, children=60000)`: scalp map (density,
length, combing direction, greyness) from position; guides grown along the scalp with
volume on longer strands; children interpolated from the nearest guides, clumped and
frizzed. About 4 s to build, 20 s to render two 400 px views. Melanin: dark about 0.9,
white about 0.02 (0.6 came out ginger). Write new cuts as new style functions.

## Iterating on a shape (learned on the collar, run 009 steps 7 to 10)

- Never replace the best version without a side-by-side against it and the reference.
  Step 7 replaced a better step 5; the fix was to merge their good parts.
- Shape first, in clay: `tools/variants.py SCRIPT VIEW REFERENCE OUT "label=k=v;k=v" ...`
  renders four variants in about a minute (CLAY=1: grey, no fur, 8 samples).
- Surface second, in full renders, again as options side by side.
- Collar settings that worked: cushion 0.065, tips 0.66, wings 0.84, tip_angle 160,
  soften 20; fuzz 400,000 strands, 1.8 mm long, 0.18 mm radius; pile relief 0.6.

## Failure signatures and fixes

| What you see | Cause | Fix |
|---|---|---|
| Sleeves collapse onto bare arms | Cloth collided with the visible body, which has holes | `collider=True`; collide with `<name>_collider` |
| "49% inside skin" on a garment that looks fine | Measured against the holed body | Measure against the complete collider |
| Garment reads as bare skin | Too little ease and colour too light | Ease 3.5 to 4 cm; darker colour |
| Seams tear open at the shoulders | Sleeve weight exceeds sewing force | Pin sleeve tops; sewing force 60 (route B) |
| Whole garment slides to the hips or waist | Shoulder seam closes on or below the shoulder surface and is forced through | Start panels 4.5 to 7 cm higher; gentle sewing |
| Sleeves miss the arms entirely | Pattern drafted for another body | Measure our character and draft for it |
| Head 3 cm long in the measurements | "neck" part includes the head | Exclude it from shoulder measurements |
| Leather looks like cracked eggshell | Grain too large | Grain 1.4 mm, bump strength 0.3 |
| Goggle strap floats off the head | Sized to the ears | Size to the temples (half-width minus 6 mm) |
| Fabric pattern in huge stripes | Garment UVs are tiny (21 m per unit) | Use `on="garment"` materials |
| `import bmesh` fails | Imported before `bpy` | Import `bpy` first |
| "Material has been removed" | Materials made before `stage.new_scene()`, which resets the file | Create the scene first, then materials |
| Pocket edges wavy, corners notched | Cut from the 2.7 cm body mesh | Use `leg_patch` (exact, finely meshed) |
| Patch appears nowhere (NaN positions) | Flat chart has zero-area triangles | Filtered in `_wrap`; check s/theta ranges of the patch |
| Loose trousers look like leggings | Ease alone keeps the body's shape | Use a `cut` (straight-leg radii) |
| Crotch or buttocks show through | Creases larger than the smoothing reach | Built in: `smooth_shell` adds crotch bridging |
| Undershirt pokes through the waistband | Different base surfaces | Same `smooth_shell`, smaller ease, hem above the waistband |
| Trouser hems balloon at the ankle | Straight-leg radius around a thin ankle | Boots over them on the same `cut`, or a smaller ankle radius |
| Vest shrinks to two tabs at the collar | Armholes cut by arm coordinate; with arms down most of the chest counts as arm | `vest()` cuts an oval round each shoulder joint |
| Straps or box vanish into the vest | Padded channels are added at render time, not in the surface straps are laid on | Lift straps by channel depth plus a margin (1.8 cm) |
| Release box hidden | Ray at the centre hits inside the vest opening | Anchor it where the shoulder straps end |
| Cartridges merge into one bar | Spaced sideways | Stack them vertically |
| Collar reads as a fur tube | Band of equal depth all round | `lapel_collar` with a drawn outline |
| Collar flat like paper, rises like a hood | No volume; roll too high | `cushion` 0.05 to 0.065, roll 0, neckline 0.98 |
| Huge flat planes bridging a V opening | Triangulation kept triangles outside the outline | Fixed: only triangles inside the outline are kept |
| Spikes all over a smoothed piece | Blender's Laplacian smooth modifier on this mesh | Edge-pinned smoothing in `garments.build` (`relax`) |
| Lapel points flare outward | tip_angle too small (135) | 160 points them down toward the V |
| Shearling looks like a terry towel | Strands 3.5 mm long, 0.4 mm thick | 1.8 mm long, 0.18 mm thick, many more |
| Segmentation fault, no message | Growing zero hair strands | Skip; `hair.grow` now refuses an empty set |
| Goggles read as a visor bar | Frames too shallow | Frame half-height 0.029 |
| Block of mask over the nose | Both frames centred on the eyes overlap there | `frame_offset` 0.035, arch cut from below, dip from above |
| Lumpy mask, crumpled lenses, wavy rims | Cut from the detailed face mesh | Exact outline on the smoothed face; separate fitted lenses |
| Lenses look like spectacles inside the mask | Lens behind the mask surface | standoff 2 cm |
| Edge-loop finder merges an opening with the outer edge | Walked by neighbours | Follow face winding (fixed in `boundary_loops`) |
| Moustache sticks out like a brush, skin shows through | Strands grow along the normal; too sparse | Comb hard sideways and down; dark base layer |
| Dark blotches on the cheeks | Moustache base on the smoothed face dips under the skin | Lay it on the raw face (smooth=0) |
| Bright white stitch lines on the hood | Thread colour derived from the base | Pass a thread colour close to the leather |
| Hair grows over the face | Depth measured with the wrong sign in the hairline test | Fixed in `short_back_and_sides` |
| Hair looks painted on | Strands lie on a flat shell | `volume` lifts longer strands off the scalp |

## Time per step on this machine (4 CPU cores, no graphics card)

| Step | Time |
|---|---|
| Build character with outfit shells | about 5 s |
| Drape a shell jacket | 40 to 45 s |
| Sew a pattern garment | 75 to 135 s |
| 70,000 fur strands | about 2 s to build |
| Test render 432x540, 48 samples | 20 s |
| Full render 864x1080, 160 samples with fur | 7 min |
| Full outfit of route A and D pieces, no cloth simulation | about 2 s to build |
| Outfit test render 540x720, 48 samples, with 170,000 fur strands | 25 s |

## Rules for keeping this useful

1. After every outfit, add a row to `outfit-log.md`: what was made, route per layer, steps
   that failed and why, total time.
2. When a failure repeats, promote its fix into the procedure above or into the recipe
   itself, so it cannot happen a third time.
3. When a step's settings change, change them here in the same commit.
4. When a route becomes reliable, say so here and add a check for it to the test suite.

## Curly hair (run 012, 5 steps, about 18 s to build, 90 s for three views)

`haircut.curls(scene, base_verts, style=curly_mop, ...)`. Each guide is one ringlet; children copy
only their own guide (blending several coiled guides cancels the coils). Design from Blender's
bundled "Curl Hair Curves" node group (procedural_hair_node_assets.blend), re-implemented in numpy.

Settings that matched the reference mop (step 6): length 0.065, sides 0.32 of that, coil radius 0.0095,
pitch 0.038 per turn, volume 0.028, lock spread 0.006, 280 guides, 100,000 children, radius 0.00007.

| Symptom | Fix |
|---|---|
| Golden blond with melanin 0.25, redness 1.0 | Direct colour mode, `Color` (0.8, 0.12, 0.05) for coral |
| Direct colour (0.95, 0.32, 0.18) pale peach | Many strands brighten it: go darker and more saturated |
| Covers the face, hangs to the shoulders | Length 0.11 too long; shorten low sides (length x 0.45 below the temples) |
| Thin telephone-cord coils | Coil radius 0.007 to 0.0095, pitch 0.022 to 0.038, lock spread 0.006 |
| Zig-zag strays | Flyaway frizz 7x too strong; 3x on 1.5 percent of strands |
| Bare parting at the front | Crown point further back (0.13 behind the face), hairline lower (0.042 above the eyes) |
| Mop too wide, sides hang a whole eye-spacing below the eyes (owner: "a bit shorter") | Length 0.08 to 0.065, side factor 0.45 to 0.32, volume 0.035 to 0.028. Measure in eye-spacings against the reference |
| Fringe over one eye vs fringe too high | `fringe_cut` 0.25 (0.45 showed the hairline) |

## Skin detail and eyes (run 012, steps 7 to 10)

`skin.freckle_image(base_verts)` paints freckles into the skin's UV layout, placed in 3D from
face landmarks (band over nose and upper cheeks, light sprinkle on the rest of the face), so
they stay put under posing. `skin.add_detail(mat, freckles, tone, pores)` multiplies them and a
tone into the skin texture and adds a pore bump. `skin.two_eye_colours(eyes, right, left)` for
heterochromia (right = character's right, x < 0).

Match skin by measuring: median colour of the lit half of a cheek and forehead patch, as
fractions of R+G+B, ours against the reference. Reference 0.428 / 0.328 / 0.245.

| Symptom | Fix |
|---|---|
| Freckles big, dark, everywhere (1,400, amount 0.75) | 1,000 at amount 0.6 |
| Skin too red under sun (0.448 red) | Lighting first: soft warm three-point at 2 m, key 40 W. Then tone multiply |
| Skin too cool under studio lights (0.383 red, 0.288 blue) | Tone (1.0, 0.93, 0.70) gave 0.403 / 0.329 / 0.269 |
| Blue eye reads dark teal | `lightblue` eye material |
| Swept lock hangs like a stick (sweep 0.6) | sweep 0.35 |

## Flat ribbon curls (run 012, steps 11 to 14)

`haircut.curls(..., ribbon=dict(width, thickness, taper))`: each lock is a flat band that
curls, instead of a round spring. Chosen: 220 guides, width 0.016, coil radius 0.011, pitch
0.055, thickness 0.0015, taper 0.5.

| Symptom | Fix |
|---|---|
| Thin flat noodles | Band width was laid along the coil axis, which mostly runs along the strand. Use the axis direction minus its part along the coiling strand |
| Wood-shaving look, very crisp | Acceptable; closest to the reference (12a) |
| Mush, curls lost (thickness 0.003, frizz 0.0012, tips widening) | Keep thickness under 0.002 and frizz under 0.0008 |
| Fewer guides lose the swept lock over the eye | Check the eye cover after changing guide count |

## Thick fibrous curls and head angle (run 012, steps 15 to 18)

Reference locks are thick bundles of fine visible hairs that curl about once and fray into
wisps. Settings: 260 guides, 150,000 children, strand radius 0.00005, band 0.012 wide and
0.005 thick, coil radius 0.009, pitch 0.06 (about one turn), `fray` 0.003 (ends fan out),
`shorten` 0.35 (hairs end at different lengths), colour (1.0, 0.075, 0.02), roughness 0.45.

Head angle: `pose=[("turn", "neck01", "X", ...), ("turn", "head", ...)]` and
`rig.parent_to_bone(hair, armature, "head")` so rigid hair follows the head.

Measure hair colour on the lit half of orange pixels as hue, saturation, value.
Reference 16 deg / 0.73 / 0.85.

| Symptom | Fix |
|---|---|
| Thin smooth sheets (owner: "his curls are thicker") | Thickness 0.0015 to 0.005, more children, thinner strands, fray and shorten the ends |
| Hair yellower and darker (22 deg, value 0.74) | Direct colour (1.0, 0.10, 0.03) and key light 40 to 58 W |
| Fine fibres wash out to pink (saturation 0.50) | Colour (1.0, 0.075, 0.02), roughness 0.45: 18 deg / 0.62 / 0.82 |
| Curls too big (owner) | Coil radius 0.011 to 0.009, band 0.016 to 0.012 |
