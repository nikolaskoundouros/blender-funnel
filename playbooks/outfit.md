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
