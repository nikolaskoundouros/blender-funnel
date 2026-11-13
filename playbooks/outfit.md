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

## Time per step on this machine (4 CPU cores, no graphics card)

| Step | Time |
|---|---|
| Build character with outfit shells | about 5 s |
| Drape a shell jacket | 40 to 45 s |
| Sew a pattern garment | 75 to 135 s |
| 70,000 fur strands | about 2 s to build |
| Test render 432x540, 48 samples | 20 s |
| Full render 864x1080, 160 samples with fur | 7 min |

## Rules for keeping this useful

1. After every outfit, add a row to `outfit-log.md`: what was made, route per layer, steps
   that failed and why, total time.
2. When a failure repeats, promote its fix into the procedure above or into the recipe
   itself, so it cannot happen a third time.
3. When a step's settings change, change them here in the same commit.
4. When a route becomes reliable, say so here and add a check for it to the test suite.
