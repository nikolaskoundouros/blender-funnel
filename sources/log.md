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

## Could not be used

| Source | Why |
|---|---|
| YouTube tutorial `hvfoRTGUsDg` and YouTube in general | "Sign in to confirm you're not a bot" on metadata and captions. Not worked around. Video goes through the owner's analyzer instead |
| Blender manual source repository | Hosted on projects.blender.org, no public GitHub mirror found; pages fetched from docs.blender.org instead |

## Earlier in this project

| Source | Trust | What it gave |
|---|---|---|
| Blender source @ a561bcbc (5.4 alpha) | A | Architecture research: main loop, data model, dependency graph, engines |
| `ahujasid/blender-mcp`, `renezander030/blender-cli` (both MIT) | C | How AI bridges run code inside Blender |
