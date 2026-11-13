# Source log

Trust levels: **A** installed Blender's own descriptions · **B** official manual ·
**C** code in a repository · **D** tutorial transcript · **E** search summary.

## Pass 1: lighting and exposure (fetched 13 Nov 2026)

| Source | Trust | Targets | What it gave |
|---|---|---|---|
| Blender 5.3.0 property descriptions, read with `bpy.types.*.bl_rna` | A | 5.3.0 | Exact property names, defaults, units: sun strength in W/m², light exposure, area light shapes, f-stop meaning, sky node properties, Cycles defaults (4096 samples, adaptive threshold 0.01) |
| Manual: Displays and Views (`render/color_management/displays_views`) | B | 5.3 | View transforms (AgX, Standard, Filmic deprecated, Khronos PBR Neutral, ACES), exposure formula, False Color table |
| Manual: Light Objects (`render/lights/light_object`) | B | 5.3 | Light types, radius and softness, light exposure and temperature, normalize option |
| Manual: Sky Texture (`render/shader_nodes/textures/sky`) | B | 5.3 | Sky models (Multiple Scattering current, others legacy), warning that the sky is very bright |
| Manual: Cameras, World, Cycles world settings, Film | B | 5.3 | Read; not yet turned into claims |
| `CGArtPython/blender_plus_python` @ 4115938 (MIT) | C | 2.9x to 4.x | Sky world node layout; look names changed in 4.0 (`"Very High Contrast"` became `"AgX - Very High Contrast"`); f-stop values 0.1 to 1.1 for strong blur; area light powers 100 to 1000 W |
| Web search summaries on three-point lighting | E | unknown | Key, fill, rim roles. Layout only; no numbers trusted |

Manual page text is stored in `sources/raw/manual/` (Blender manual, CC BY-SA 4.0).
The tutorial repository is not copied here; ideas were re-implemented.

## Pass 2: human characters with outfits (fetched 13 Nov 2026)

| Source | Trust | Targets | What it gave |
|---|---|---|---|
| `makehumancommunity/mpfb2` @ 9de0707, `docs/fileformats/*.md` (code GPL-3, docs read only) | B | MPFB 2.0.18 | Exact file formats for fitted items, targets, materials, rigs and weights, written with reimplementers in mind |
| Same repository, `src/mpfb/data` (CC0) | A | hm08 base mesh | Base mesh, 1,258 targets, joint and helper vertex groups, 8 skeletons with weights |
| Same repository, `script_samples/*.py` | C | MPFB 2.0.18 | The order a full character is assembled in: body, skin, rig, eyes, brows, lashes, teeth, hair, clothes. One sample's asset-pack link was stale (404) |
| MakeHuman system asset pack, `files.makehumancommunity.org` (CC0, 280 MB) | A | hm08 | 23 skins, 10 hairstyles, 14 outfits, 6 shoes, 2 hats, eyes, brows, lashes, teeth |
| Web search on Blender character generators | E | unknown | Pointed at MPFB; nothing else used |

The asset pack and MPFB data are not stored in this repository. `tools/fetch_assets.sh`
downloads both (tested from scratch: 31 s).

## Pass 3: motion (fetched 13 Nov 2026)

| Source | Trust | Targets | What it gave |
|---|---|---|---|
| `una-dinosauria/cmu-mocap` @ 09a07f5: CMU Graphics Lab Motion Capture Database, BVH conversion by B. Hahne (2010) | A | 31-joint "MotionBuilder-friendly" skeleton | 2,548 clips with an index; four dance clips used: 05_02 modern dance, 15_04 dance moves, 55_02 lambada, 60_01 salsa. Readme states the data is free for research and commercial use |
| MakeHuman data: `rig.cmu_mb.json`, `weights.cmu_mb.json` (CC0) | A | hm08 base mesh | A skeleton with the same joint names as the CMU clips |
| Blender 5.3.0 bundled BVH importer (`io_anim_bvh`) | A | 5.3.0 | Used only as an independent check of our own BVH reader |

Clips are not stored in this repository; `tools/fetch_assets.sh` downloads the four used.

## Pass 4: environments, props, outfits (in progress, 13 Nov 2026)

| Source | Trust | Targets | What it gave |
|---|---|---|---|
| Blender 5.3.0 node and socket names, read from the program | A | 5.3.0 | Principled inputs ("Sheen Weight", "Coat Weight", "Transmission Weight", "Thin Wall"); texture node inputs; `Mesh.set_sharp_from_angle` no longer exists |
| MakeHuman base mesh helper shells (CC0) | A | hm08 | "helper-tights" (2,650 quads, about 5 mm off the skin) and "helper-skirt"; both carry UVs and skin weights. Basis for generated garments |
| Blender 5.3.0 bundled asset files | A | 5.3.0 | 32 procedural hair node groups, XPBD cloth solver node groups, compositing effects (grain, vignette). Found, not yet used |
| Poly Haven API (CC0) | A | n/a | Reachable; texture, HDRI and model listings. Not yet used |
| Owner's reference image (pilot close-up) | target | n/a | Defines the quality level wanted; see notes/quality-gap.md |

## Could not be used

| Source | Why |
|---|---|
| YouTube tutorial `hvfoRTGUsDg` and YouTube in general | "Sign in to confirm you're not a bot" on metadata and captions. Not worked around. Video goes through the owner's analyzer instead |
| Running the MPFB add-on's own code | Blocked by this session's safety check on executing freshly downloaded third-party code. Not worked around; its data and format documentation were read and the logic re-implemented |
| Mixamo | Needs an Adobe sign-in and has no automation interface |
| Blender manual source repository | Hosted on projects.blender.org, no public GitHub mirror found; pages fetched from docs.blender.org instead |

## Earlier in this project

| Source | Trust | What it gave |
|---|---|---|
| Blender source @ a561bcbc (5.4 alpha) | A | Architecture research: main loop, data model, dependency graph, engines |
| `ahujasid/blender-mcp`, `renezander030/blender-cli` (both MIT) | C | How AI bridges run code inside Blender |
