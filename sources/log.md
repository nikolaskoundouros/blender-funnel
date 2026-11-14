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

## Pass 6: cloth and garment prior work (13 Nov 2026)

| Source | Trust | Targets | What it gave |
|---|---|---|---|
| Blender 5.3 manual: Cloth introduction, physical properties, collisions, shape; Collision | B | 5.3 | Pinning, sewing springs, shrinking factor, collider rules. Three claims confirmed in `experiments/verify_cloth.py` |
| `maria-korosteleva/GarmentCode` @ d449629 (MIT) | C | 172 cm reference body | Sewing-pattern file format and four finished patterns; see `notes/garment-prior-work.md` |
| Licence files of CLOTH3D, Deep Fashion3D, synthetic-cloth-data, BlenderProc; Hugging Face record for GarmageSet | A | n/a | Which garment data may be used in a public toolkit |
| Owner-supplied overview of garment datasets | E | n/a | Leads; each checked independently |

## Reference clip (supplied by the owner, 13 Nov 2026)

| Source | Trust | What it gave |
|---|---|---|
| "How I Met My Best Friend" by The Art Of War (66 s vertical short, 1080x1920, 30 fps), uploaded as a file | target | The quality target. One frame per second extracted to a contact sheet; full-size frames at 0.6 s (pilot with notebook) and 24.6 s (cockpit close-up) used for side-by-side comparison |

The clip is someone else's work. Its frames are kept out of the repository
(`sources/reference/` and `runs/compare/` are git-ignored) and are used only to compare
quality, not copied into anything we ship.

## Tutorial video: particle hair (13 Nov 2026)

| Source | Trust | Targets | What it gave |
|---|---|---|---|
| "Create Hair / Fur in Blender 4.2 using Particle System" (FilmTush, 52 s), file supplied by the owner | D | Blender 4.2 | Step-by-step legacy particle-hair workflow with settings; transcript by faster-whisper base.en. See `notes/tutorial-hair-particles.md` |

## Pass 7: curly hair (13 Nov 2026)

| Source | Trust | Targets | What it gave |
|---|---|---|---|
| Blender 5.3.0 `procedural_hair_node_assets.blend`: inputs of Curl, Clump, Frizz Hair Curves and Hair Curves Noise, read on the installed program | A | 5.3.0 | Curl design: start along the strand, radius, frequency, random offset per curve, and a guide map so strands of one clump curl together. Re-implemented in numpy (`haircut.grow_ringlets`) |
| "My Mom Cracked The Dinosaur" (87 s vertical short), file supplied by the owner | target | n/a | Reference for the orange curly hair; frames kept out of git |

## Tutorial video: FaceTracker for Blender (13 Nov 2026)

| Source | Trust | Targets | What it gave |
|---|---|---|---|
| KeenTools "FaceTracker for Blender" tutorial (4 min 31 s), on the owner's computer; analysed there by another session | D | Blender 4.2, FaceTracker 2024.2.3 | Facial mocap workflow and export format; see `notes/tutorial-facetracker.md` |

## Tutorial video: pro T-shirt (13 Nov 2026)

| Source | Trust | Targets | What it gave |
|---|---|---|---|
| "Noob vs PRO Realistic Clothes in Blender" (73 s short), file supplied by the owner | D | not shown | Box-modelled shirt, box collider, subdivision before cloth, self collision; see `notes/tutorial-pro-tshirt.md` |

| "Noob vs Pro Artist 3D Pants Design in Blender" (96 s short), file supplied by the owner | D | not shown | Two sewn flat panels with a crotch slit, no gravity, shrink; see `notes/tutorial-pro-pants.md` |

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

## Cloth: why a draped shirt's hem rises (14 Nov 2026)

| Source | Trust | Targets | What it gave |
|---|---|---|---|
| Installed Blender 5.3.0, `ClothCollisionSettings`, `CollisionSettings` via `bl_rna` | A | 5.3.0 | `self_distance_min` hard minimum 1 mm, default 15 mm; `use_culling` default on ("acts with respect to the collider normals"); `use_normal` default off |
| Manual: Cloth > Shape, Cloth > Collisions, Physics > Collision (docs.blender.org, latest = 5.3) | B | 5.3 | Rest shape from the first frame unless Dynamic Mesh or Rest Shape Key; shrinking factor; self distance meaning |
| Blender source at tag v5.3.0 (GitHub mirror, raw files): `blenkernel/intern/cloth.cc`, `collision.cc`, `simulation/intern/SIM_mass_spring.cc` | C | 5.3.0 | Spring rest lengths from `xrest` x shrink factor, re-applied each step; goal (pin) weights to the 4th power; single-sided collision test; self collision excludes only triangle pairs sharing a vertex |
| MakeHuman asset packs index and FAQ, Faceunits 01 page (`static.makehumancommunity.org/assets/assetpacks/`) | B | hm08 | "Functional asset packs ... The assets are shared under CC0"; Faceunits 01 "contributed by Mika Suominen"; CC0 = "no restrictions on the use" |
| `faceunits01.zip` (`files.makehumancommunity.org/functional/`, 257,821 bytes), `packs/faceunits01.json` | A | hm08 | 52 entries, each `"license": "CC0"`, author Mika Suominen, `original_source` empty, description "Autogenerated ARKit faceunit"; target files carry no header |

## Facial mocap: tracker and a real face clip (14 Nov 2026)

| Source | Trust | Targets | What it gave |
|---|---|---|---|
| MediaPipe Face Landmarker `face_landmarker.task` (float16/latest, sha256 64184e22...) run with `mediapipe==1.2.3` | C | n/a | 478 landmarks, 52 blendshape scores (no tongueOut), 4x4 face transform per frame; fetched by `tools/fetch_assets.sh` (Apache-2.0 model card, survey 13 Nov) |
| "WIKITONGUES Kavyanjali speaking Hindi" (Wikimedia Commons, `File:WIKITONGUES_Kavyanjali_speaking_Hindi.ogg`, 720p VP9 transcode, 134.7 s), by Wikitongues, **CC BY-SA 4.0** | data | n/a | A real person talking to camera, used to test the face pipeline (P5). The video is not stored in git; tracked curves and our renders derived from it are credited here and shared under CC BY-SA 4.0. Segment used: 40 to 55 s at 24 fps |
| Commons API (`commons.wikimedia.org/w/api.php`) | data | n/a | Licence and author fields (`extmetadata`). Needs a User-Agent; original-file downloads returned HTTP 429, the transcoded 720p file did not |
