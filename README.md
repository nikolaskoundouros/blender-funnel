# Blender learning and execution funnel

A repeatable way to turn outside material (manual pages, repositories, tutorials) into
tested building blocks, and to build Blender scenes from those blocks.

    question -> sources -> claims -> experiments -> recipes -> scene -> review -> next question

| Folder | What it holds |
|---|---|
| `sources/` | Log of everything consulted, and the raw text of manual pages |
| `notes/` | Claims extracted from sources, each marked verified or not, with evidence |
| `experiments/` | Small renders that test claims by measurement |
| `recipes/` | Tested functions for lights, world, colour, camera, backdrop, materials, human characters, skeletons and motion |
| `tests/` | Re-runs every recipe; catches breakage when Blender changes |
| `runs/` | One folder per scene built: script, renders, numbers, written review |
| `tools/` | Page-to-text converter, image statistics, on-screen label lookup |

`CLAUDE.md` holds the operating rules an AI assistant follows when working here.

## First pass (13 Nov 2026, Blender 5.3.0)

Question: why did the first demo render look flat, and how should a scene be lit and exposed?

- 8 manual pages read, 1 tutorial code repository read, property descriptions read from Blender itself
- 4 claims tested by render, all confirmed (2 only after fixing my own measurements)
- 8 recipe checks pass
- Result: `runs/001-flat-render/before.png` and `after.png`; brightness spread went from 0.24 to 0.43

See `notes/lighting-and-exposure.md` for what was learned and `runs/001-flat-render/review.md`
for what is still wrong.

## Second pass (13 Nov 2026, Blender 5.3.0)

Question: how can human characters with outfits be created from code?

- Read the MakeHuman file formats and wrote an independent loader (`recipes/human.py`, `recipes/rig.py`)
- 7 claims tested by measurement, all confirmed (3 only after fixing my own tests)
- 11 recipe checks pass
- Result: `runs/002-characters/characters.png`, three people with different bodies, skins, outfits and poses

See `notes/characters.md` and `runs/002-characters/review.md`.

## Third pass (13 Nov 2026, Blender 5.3.0)

Question: how can a character be made to dance from motion-capture data?

- Wrote a BVH reader and motion transfer (`recipes/motion.py`) for the CMU motion-capture clips
- 5 claims tested by measurement, all confirmed, including agreement with Blender's own importer
- 12 recipe checks pass
- Result: `runs/003-dance/dance.mp4`, a clothed character performing a 9-second modern-dance clip

See `notes/motion.md` and `runs/003-dance/review.md`.

## Fourth and fifth passes (13 Nov 2026, in progress)

Question: can outfits, props and a hero close-up be built from scratch at the level of the owner's reference?

- Garments cut from the body's helper shells; strand hair and fur; goggles; leather, fabric and skin materials
- Result: `runs/005-pilot/pilot.png`. Fur, moustache, glass and skin get close; cloth structure does not
- Not yet measured: these recipes have no checks in the test suite
- Environments and props are not started

See `notes/quality-gap.md` and `runs/005-pilot/review.md`.

## Setup

    pip install -r requirements.txt
    tools/fetch_assets.sh               # character and motion data, about 370 MB, not stored in git
    python tests/check_recipes.py

Needs Python 3.13 for `bpy` 5.3. No Blender installation or GPU is required.
