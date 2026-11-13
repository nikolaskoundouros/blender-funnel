# Blender learning and execution funnel

A repeatable way to turn outside material (manual pages, repositories, tutorials) into
tested building blocks, and to build Blender scenes from those blocks.

    question -> sources -> claims -> experiments -> recipes -> scene -> review -> next question

| Folder | What it holds |
|---|---|
| `sources/` | Log of everything consulted, and the raw text of manual pages |
| `notes/` | Claims extracted from sources, each marked verified or not, with evidence |
| `experiments/` | Small renders that test claims by measurement |
| `recipes/` | Tested functions for lights, world, colour, camera, backdrop, materials |
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

## Setup

    pip install -r requirements.txt
    python tests/check_recipes.py

Needs Python 3.13 for `bpy` 5.3. No Blender installation or GPU is required.
