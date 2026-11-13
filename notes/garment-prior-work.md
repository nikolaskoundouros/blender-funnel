# Garments: what already exists (survey, 13 Nov 2026)

Prompted by the owner: research should start with what others have built, not only with
manuals and our own experiments. Every row was checked directly (repository reachable,
licence file read) unless marked otherwise.

| Project | What it is | Licence (as read) | Use for us |
|---|---|---|---|
| GarmentCode (`maria-korosteleva/GarmentCode`, ETH Zurich, SIGGRAPH Asia 2023) | Python library that writes parametric sewing patterns from body measurements: bodices, sleeves, collars, pants, skirts. Ships four finished pattern files (shirt, hoody, pencil dress, jumpsuit) and a measurement list for a 172 cm body | MIT | **High.** Its pattern file is exactly what our jacket lacks: real panel outlines in centimetres, curved edges, where each panel sits round the body, and which edges are stitched together |
| Garment-Pattern-Generator (same author, 2021) | Earlier pattern templates and dataset generator | MIT | Medium; superseded by GarmentCode |
| synthetic-cloth-data (`tlpss/synthetic-cloth-data`) | Blender Python scripts that make deformed cloth meshes with keypoints, for robotics | MIT | Low to medium; examples of scripted cloth in Blender |
| BlenderProc (`DLR-RM/BlenderProc`) | Pipeline for rendering synthetic training images | GPL-3.0 | Low; solves dataset rendering, not garment making |
| CLOTH3D (`hbertiche/CLOTH3D`) | Large set of simulated clothed humans | No licence file found in the repository; terms not verified | Not usable as assets until terms are known |
| Deep Fashion3D (`GAP-LAB-CUHK-SZ/deepFashion3D`) | 3D scans of real garments | CC BY-NC 4.0 | Reference only: non-commercial |
| Style3D GarmageSet (Hugging Face) | About 14,800 designed garments with sewing patterns | CC BY-NC-ND 4.0, access gated | Not usable in a public toolkit: non-commercial and no derivatives |
| Commercial Blender add-ons (Easy Cloth, Garment Tool, Simply Cloth) | Sewing-pattern and cloth tools sold on marketplaces | Sold products; source not public (search result, not verified) | Evidence that panels plus cloth simulation is the standard method in Blender |

## What the pasted overview got right and wrong for our purpose

- It answers "how do I train a model to generate outfits". We are not training a model; we
  are generating garments by code inside Blender. Most of its list is training data.
- Its licence warning is correct and matters: the two largest pattern datasets cannot be
  used in a public toolkit.
- It did not mention GarmentCode, which is the most directly useful find here.

## What the GarmentCode pattern file contains (read from `assets/Patterns`)

- `panels`: each has 2D `vertices` in centimetres, `edges` between them (straight, or
  curved as cubic or circle arcs), and a 3D `translation` and `rotation` placing it by the body.
- `stitches`: pairs of (panel, edge) to sew together.
- Example: the shirt is 8 panels (front and back torso halves, front and back sleeve
  halves per side) and 18 stitches.

## Proposed use (not yet done)

1. Write our own reader for this pattern format: panel outline to a filled, evenly meshed
   panel in Blender; stitches to sewing edges.
2. Place panels round our character by scaling from their 172 cm body to ours.
3. Sew and drape with `recipes/cloth.py`, which is already verified.
4. Check fit by measurement, then compare with the shell-cut jacket from run 006.

Unverified: whether their panel placement transfers to our body shape without adjustment,
and whether Blender's solver sews panels that start several centimetres apart as cleanly
as their own simulator does.

## Using the generator (13 Nov 2026, with the owner's go-ahead)

- `pygarment` 2.0.2 installs from the Python package index, but that build cannot be
  imported as `pygarment` (its modules are installed under other names). The generator is
  therefore run from a checkout of the repository, using the installed dependencies, in
  its own Python 3.11 environment. `tools/draft_pattern.py` wraps this.
- Design options that matter for jackets: body `Shirt` or `FittedShirt` with length, width
  and flare; necklines including V; collar components `Turtle`, `SimpleLapel`, `Hood2Panels`;
  sleeves up to 1.15 of arm length with `CuffBand` cuffs; a waistband. There is no front
  opening, zip, pocket or shearling option.
- A jacket-style draft (loose body, V neck with lapel collar, full-length sleeves with cuff
  bands, waistband) came out as 18 panels and 35 stitches, with no self-intersection.
- Newer pattern files add a third item to some stitches (`"right_wrong"`, used on collars)
  and use circle-arc edges. The reader handles both; the arc direction rule was derived
  from the library's drawing code and is not yet checked against it numerically.

| Step | Result |
|---|---|
| Shirt pattern, panels placed | Worked |
| Shirt pattern, sewn | Worked on the third attempt (see run 007 notes below) |
| Jacket pattern, panels placed | Worked |
| Jacket pattern, sewn | Body, V neck and lapels form; **sleeves miss the arms** and bunch at the shoulders; one seam left 14 cm open |

Why the sleeves miss: the pattern was drafted and placed for the library's own body
(arms held about 45 degrees down, lower and more sloped shoulders). Our character's arms
and shoulders sit elsewhere, and the 7 cm lift that rescued the shirt's shoulder seams
moves the sleeves further off the arms. Lifting was a patch. The proper fix is to give
the generator our character's measurements, so the pattern is drafted and placed for it.

Next: measure our character from its mesh into the library's body-measurement file
(about 27 values: height, bust, waist, hips, shoulder width and slope, arm length, arm
pose angle, wrist, neck width and others), then draft and sew again without the lift.
