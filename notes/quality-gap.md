# Quality gap: current output versus the owner's reference

Reference (supplied 13 Nov 2026): a close-up of a pilot in a cockpit. Leather flying
helmet with seams and creases, goggles with reflective lenses, shearling-collared jacket,
harness straps and buckles, gloves, a moustache, a lively facial expression, shallow depth
of field. The image carries an "AFTER" caption, so it is one half of a before/after pair.
What the "before" was, and which tool produced the "after", is not known.

Current state (pass 4, in progress): garments cut from the body's helper shells fit any
body and pose, but they are skin-tight shells with wavy edges and flat colour. See the
test image description in this file's last section.

## Element by element

| Element in the reference | What produces it | Available here | Status |
|---|---|---|---|
| Close-up framing, shallow depth of field, soft key with rim light | Camera and light placement | Yes: recipes from pass 1 | Works in wide shots; no close-up attempted yet |
| Folds, creases, weight of cloth | Cloth simulation of garments built from panels, or sculpting | Blender's cloth modifier; an experimental XPBD solver ships as node groups in this build | Not attempted. Current garments cannot fold |
| Thick layered clothing (collar, lapels, cuffs, seams, stitching) | Separate modelled pieces with thickness and edge detail | Modelling tools only | Not attempted |
| Shearling and fur | Hair curves generated on a surface | Yes: 32 procedural hair node groups ship with Blender (generate, interpolate, clump, noise, trim) | Found, not used |
| Worn leather, scuffed metal | PBR materials: colour, roughness and bump variation | Procedural nodes; Poly Haven CC0 texture sets are reachable (leather set confirmed) | Simple procedural materials written; none at this level |
| Goggles, buckles, straps | Hard-surface modelling with bevels; glass shader | Modelling tools; glass material written | Not attempted |
| Moustache, eyebrows, head hair | Hair curves, or textured cards | Hair node groups; MakeHuman hair cards | Cards in use; curves not attempted |
| Facial expression | Face bones or expression morphs | MakeHuman expression targets exist in the data | Not attempted |
| Skin that looks alive | Subsurface scattering, pore-level bump, eye cornea and wetness | Principled shader has subsurface inputs | Skin is a flat colour texture today |
| Cockpit set | Modelled environment and props | From scratch | Not attempted |
| Final polish | Grain, vignette, colour grade | Compositing node groups ship with Blender | Not attempted |

## After run 005 (first attempt, all in Blender)

Decision by the owner on 13 Nov 2026: everything is to be done in Blender, and the
repository is meant to become a public toolkit for animators.

| Element | Result of the first attempt |
|---|---|
| Fur | Close. Strand generator written; 70,000 strands render as wool |
| Moustache | Close. Strands rooted and combed on the lip |
| Goggles | Recognisable; strap is wrong |
| Skin | Improved by subsurface scattering; no pore detail |
| Leather | Acceptable after colour correction; no wear patterns that follow the form |
| Cloth structure | Not achieved. Shell garments cannot fold or carry seams |
| Face expression, cockpit | Not attempted |

See `runs/005-pilot/review.md`.

## Two routes to that level

**A. All in Blender.** Every row above becomes its own learn-and-verify pass. The rows where
code-driven modelling is strongest: lighting, camera, materials, fur, hard-surface props.
The rows where it is weakest: convincing cloth wrinkles and an appealing, specific face.
Fur, subsurface skin and depth of field are slow on this CPU-only machine (minutes per
frame at useful resolution).

**B. Blender for structure, an image or video model for surface detail.** The "AFTER" caption
is consistent with this: a plain 3D render in, a detailed frame out. Blender then only needs
to get pose, layout, camera and motion right, which already works. Costs credits per frame
or clip, and consistency between shots has to be managed. Not tested here.

Neither route has been tested against the reference. Nothing in this file is verified
beyond the "Available here" column.

## State of the from-scratch garments (test render, not kept in the repo)

- Works: tops, trousers, shorts, skirts and soft boots generated for any body; they follow
  poses; fabric patterns are sized in millimetres.
- Wrong: hems and collars are still wavy; the sleeveless top is cut incorrectly (it comes
  out as a bib); everything is skin-tight; boots have no sole.
- Not yet measured: poke-through and fit for generated garments.

## Open questions

1. Where does the reference come from, and what was its "before"?
2. Which matters more: full control inside Blender, or reaching the look quickly?
3. Stills, or moving shots? Fur, skin and cloth simulation all cost far more per frame.

## Side by side with real frames from the clip (13 Nov 2026)

Comparing `runs/005-pilot/pilot.png` with the clip at 24.6 s, and run 006 step 4 with the
clip at 0.6 s. What the full-size frames show that the first pasted image did not:

- **Light.** The reference is outdoors in bright daylight under a clouded sky. Ours is a
  dim studio. This is probably the cheapest large gain: sky lighting and a sky backdrop.
- **Shearling.** Theirs is short, dense and matte, a few millimetres deep, slightly yellow.
  Ours is long white fluff. Shorten, densify, darken.
- **Moustache.** Theirs is thin and tidy. Ours is too bushy and wide.
- **Helmet.** Theirs is grey leather in stitched panels with flaps down the cheeks meeting
  under the chin. Ours is a dome that stops above the ears.
- **Goggles.** Theirs have a soft dark gasket and a strap clipped to the helmet. Ours have
  thick metal rings and a stub strap.
- **Outfit layers.** Brown jacket with shearling cuffs, yellow life vest, cream harness
  webbing with a round white release box, scarf, belt. We have jacket and collar only.
- **Face.** Theirs smiles, shows teeth, and has darker, glossier skin.
- **Style.** The clip is stylised realism (slightly enlarged heads and hands, game-like
  shading), not photorealism. That is a more reachable target than a photograph.
