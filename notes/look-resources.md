# Look resources: colour, texture, UV maps, contrast

Status values: **verified** (called, measured or run on 13 Nov 2026; the row says how) ·
**unverified** (a lead only). Blender 5.3.0, CPU only. Nothing here was rendered.

## Top five changes to make next

1. **Light the outdoor and cockpit shots with a clouded-sky HDRI and show it as the backdrop.**
   Evidence: 9 to 25% of reference pixels are saturated blue and ours have none; reference
   outdoor median luminance is 0.37 to 0.40 against our 0.23 to 0.25; a CC0 sky is one 1.4 MB
   request away, and two CC0 outdoor HDRIs with a real sun already ship inside Blender
   (1024 x 512: enough to light with, too coarse to show).
2. **Replace the look `AgX - Medium High Contrast` with `AgX - Punchy` plus about half a stop
   of exposure.** Evidence: our darkest 5% sits at 0.09 to 0.10 where the reference sits at
   0.00 to 0.05 in three of four frames; on a test chart Punchy maps 2% grey to 0.039 instead of 0.086 and raises
   yellow saturation from 0.54 to 0.63.
3. **Re-colour leather and skin to measured targets.** Evidence: reference leather reads 0.24
   to 0.41 in a greyed mauve-brown, ours 0.11 to 0.18; reference skin reads 0.29 to 0.38 at
   saturation 0.42 to 0.47, ours 0.53 to 0.75 at 0.20 to 0.36.
4. **Fix the UV scale before any texture goes on a sewn garment.** Evidence: pattern panels
   measure exactly 1.000 m per UV unit, while `materials.py` multiplies every
   `on="garment"` pattern by 21, so grain and weave would come out 21 times too fine.
5. **Add surface detail from CC0 photo sets and form-following wear.** Evidence: fine-detail
   contrast is 0.044 to 0.049 in ours against 0.056 to 0.065 in the reference; the reference
   shearling is a bumpy matte surface, which a fleece texture set reproduces without strands.

## 1. Measurements of the reference and of our output

Method: luminance is Rec.709-weighted display values, as in `tools/image_stats.py`. Spread is
p95 minus p5. Saturation is the mean HSV saturation; chroma is the mean CIELAB chroma. The
palette is k-means (k = 6, CIELAB, 60,000 sampled pixels, fixed seed), each colour given as
the cluster's median with its share of pixels. **Caption text was masked** by dropping rows
1290 to 1440 of 1920 in every reference frame. Unmasked, percentiles move by at most 0.02
and the clipped fraction rises from 0.01% to between 0.15% and 0.57%, so nearly all pure
white in the reference is caption text.

| Image | p5 | Median | p95 | Spread | Sat. | Chroma | Near black | Palette (hex, % of pixels) |
|---|---|---|---|---|---|---|---|---|
| Ref 0.6 s, outdoor | 0.052 | 0.372 | 0.699 | 0.648 | 0.267 | 12.6 | 1.3% | #535457 29, #4b6996 20, #848ca1 18, #100f0f 16, #beaf93 11, #67442d 7 |
| Ref 4.5 s, outdoor | 0.110 | 0.402 | 0.739 | 0.629 | 0.195 | 9.4 | 0.5% | #4f5054 33, #7b859e 28, #bab3a5 12, #211f20 12, #705a4e 10, #c69c7a 5 |
| Ref 24.6 s, cockpit | 0.000 | 0.240 | 0.654 | 0.654 | 0.334 | 10.0 | 13.3% | #0f0b09 35, #45403f 19, #738299 13, #59331a 13, #81725c 11, #a9a6a6 10 |
| Ref 29.5 s, cockpit | 0.010 | 0.280 | 0.632 | 0.622 | 0.362 | 12.8 | 6.1% | #181110 27, #434142 21, #7a889f 19, #583918 14, #385384 10, #9a8463 10 |
| Ours, run 005 | 0.105 | 0.227 | 0.791 | 0.686 | 0.200 | 7.0 | 0.1% | #31373d 33, #2d231f 18, #ada292 16, #c8c1b6 15, #5a4e46 14, #886247 4 |
| Ours, run 006 step 4 | 0.088 | 0.247 | 0.754 | 0.666 | 0.223 | 6.6 | 1.2% | #394045 35, #3d3129 22, #211a17 14, #c0b9ad 13, #6b5f55 10, #c49f8a 7 |

All rows verified: computed with numpy 2.5.4 and Pillow 13.0.0. Our `stats.json` for run 005
gives the same p5, median and p95.

How ours differs, in numbers:

- **Brightness.** Our median (0.23 to 0.25) matches the cockpit shots (0.24 to 0.28) and is
  0.12 to 0.18 below the outdoor shots. The reference is not bright at the top: its p95 is
  0.63 to 0.74 and its clouds are mid-grey (#9598a7, luminance 0.60). Our p95 is higher,
  0.75 to 0.79, because of the white fur.
- **Contrast.** The overall spread is the same or slightly larger in ours. The shape differs:
  the reference reaches black (p5 of 0.00 to 0.05 in three frames, 0.11 in the fourth; up
  to 13% of pixels at or below 0.02) and ours stops at 0.09 to 0.10. Detail contrast at a radius of 1% of image width, all images
  resized to 432 px wide, is 0.056 to 0.065 in the reference and 0.044 to 0.049 in ours.
- **Saturation.** CIELAB chroma is 9.4 to 12.8 in the reference and 6.6 to 7.0 in ours, 26
  to 48% lower. Much of that is content: saturated blue alone covers 9 to 25% of their
  frames and none of ours, and we have no yellow vest.
- **No split-tone grade is visible.** Their brightest tenth averages warm grey (#bbb3a5) and
  their darkest tenth neutral (#0d0c0c).

Material targets, as display colours from 28-pixel patches placed by eye (verified as
measurements, unverified as albedo, because the reference tone mapping is unknown):

| Surface | Reference, lit | Reference, shade | Ours |
|---|---|---|---|
| Jacket leather | #7a665f (0.41) | #453939 (0.24) | #352b25 (0.18), #1e1a19 (0.11) |
| Shearling | #cfc4b7 (0.78) | #7c715b (0.45), yellower | #d1c7bc (0.79), #9a9688 (0.59) |
| Skin | cheek #7e4f49 (0.35, sat 0.42) | nose #6f3f3b (0.29, sat 0.47) | cheek #a6826b (0.53, sat 0.36); hand #d8bbac (0.75, sat 0.20) |
| Life vest | #cfb487 (0.72) | #6a4b1c (0.31, sat 0.74) | not built |
| Sky / cloud | #416192 to #6a7f9d | #9598a7 | backdrop #31373c (0.21) |
| Helmet leather | #43474b (0.28), grey | #363a45 (0.23) | #5c544e (0.33), brown |

## 2. Texture, HDRI and model sources

Every call used `curl -sS -m 20 -A "blender-research-script"`. No asset files were downloaded.

| Source | Licence as its own site states it | Request made and result | Decision | Status |
|---|---|---|---|---|
| Poly Haven: 869 textures, 997 HDRIs, 522 models | CC0; assets may be redistributed and bundled. API terms: free including commercial use, needs a unique User-Agent or Referer and a visible Poly Haven credit where the live API is surfaced | `https://api.polyhaven.com/assets?t=textures&c=leather` 200, 6 sets. `https://api.polyhaven.com/assets?t=hdris&c=partly%20cloudy` 200, 325 HDRIs. `https://api.polyhaven.com/files/brown_leather` 200, per-map URLs with sizes. HEAD on the 1k `kloofendal_48d_partly_cloudy_puresky` .hdr at `dl.polyhaven.org` 200, 1,435,119 bytes | Adopt as the main source; fetch by script, do not store in git | verified (called) |
| ambientCG: 56 assets match "leather", 284 HDRIs match "sky" | CC0 1.0; raw files may be included in projects | `https://ambientcg.com/api/v3/assets?type=hdri&q=sky&limit=3&include=title,tags,downloads` 200, zip URLs with sizes. `https://ambientcg.com/get?file=Leather037_1K-JPG.zip` HEAD 302. Its docs warn the API is run by one person | Adopt as second source | verified (called) |
| Blender's own data files | `studiolights/world/license.txt`: all HDRIs CC0, from Poly Haven. `assets/LICENSE`: CC0 1.0 | Loaded `city.exr` and `sunrise.exr` (1024 x 512, sun peak about 32,000) and wired one into a world | Adopt as the offline sky; no download | verified (loaded in bpy) |
| Physically Based database | CC0 (repository LICENSE) | `https://api.physicallybased.info/v2/materials` 200, 122 materials with linear base colour, roughness, IOR, subsurface radius | Adopt for colour values (skin types I to VI, metals, asphalt) | verified (called) |
| TextureCan | Terms page: CC0 1.0 | `https://www.texturecan.com/terms/` 200; no API found | Manual fetch only | verified licence, unverified API |
| 3dtextures.me | About page: "All textures on this site are licensed as CC0" | `https://3dtextures.me/about/` 200; no API found | Manual fetch only | verified licence, unverified API |
| AMD MaterialX library | API field per material: "MIT Public Domain" | `https://api.matlib.gpuopen.com/api/materials/?limit=3&search=leather` 200, 7 results, `.mtlx` files | Learn from; import into Cycles untested | unverified |
| MatSynth on Hugging Face | Readme: CC0 and CC-BY items mixed, licence stored per item | `https://huggingface.co/api/datasets/gvecchio/MatSynth` 200, not gated | Lead; too large to fetch here | unverified |
| Sketchfab | Per model; search filter `license=cc0` | `https://api.sketchfab.com/v3/search?type=models&q=pilot&downloadable=true&license=cc0&count=3` 200, including a CC0 museum scan of a Polish RAF pilot's jacket. Download endpoint 401 without a token | Reference for jacket construction; fetching needs the owner's token | verified search, unverified download |
| ShareTextures | "Custom CC0": forbids redistribution in plugins or collections and automated downloads | `https://www.sharetextures.com/p/license` 200 | Reject | verified (read) |
| BlenderKit | Free leather materials are `royalty_free`, not CC0 | `https://www.blenderkit.com/api/v1/search/?query=leather+asset_type:material+is_free:true&page_size=3` 200, 1,343 results | Reference only; cannot ship | verified (called) |
| cgbookcase | Home page: "100% free, no restrictions" | Home 200; `/license` 404 | Lead | unverified |
| Kenney | Support page: assets are CC0 | `https://kenney.nl/support` 200; low-poly, no API | Wrong style; skip | verified licence |

Poly Haven items that match the brief (verified as listed, not downloaded): `brown_leather`
(40 cm tile, worn and creased), `curly_teddy_natural` (beige curly fleece, 34 cm), `hessian_230`
and `rough_linen` (27 cm weaves for webbing), 20 asphalt sets, 25 metal sets, 37 midday
partly-cloudy skies, and models `life_jacket` (8,968 polygons, orange), `vintage_radio_transceiver`,
`metal_office_desk`, `old_military_crate`, `ammo_box`, `clipboard`, `desk_lamp_arm_01`.
ambientCG returned nothing for "canvas", "webbing" or "sheepskin".

## 3. UV mapping from code

All operators ran with `bpy.app.background` true on four meshes: a 0.4 m cube, a 24-sided
barrel, a 0.5 x 0.7 m sheet bent round a 0.2 m radius, and an open tube with one seam.
Context needed, and sufficient: the object active and selected, Edit Mode, all faces
selected. No `temp_override`. In Object Mode every UV operator fails its poll.

| Method | Result on the test meshes | Use for | Status |
|---|---|---|---|
| Write UVs with the data API from known flat coordinates (`patterns.build` does this) | Shirt pattern: 1.000 m per UV unit, stretch 1.00, 8 islands that overlap in UV space | Sewn panels. Best option; needs no unwrap | verified (measured) |
| Geometry Nodes `UV Unwrap` then `Pack UV Islands`, stored as a corner attribute | Tube with the `uv_seam` edge attribute: 1 island, stretch 1.00. No operator, no Edit Mode | Cloth or props that lack UVs; fits the data-API rule | verified (ran) |
| `uv.unwrap`, methods `ANGLE_BASED`, `CONFORMAL`, `MINIMUM_STRETCH`, seams set through `edge.use_seam` | Bent sheet and tube: 1 island, stretch 1.00 to 1.02. Closed mesh without seams: returns FINISHED with only a console warning and leaves one island per face | Cloth; check the island count afterwards | verified (ran) |
| `uv.cube_project(cube_size=1.0)` | 1.00 m per UV unit on the cube, 1.04 to 1.06 on curved meshes, stretch up to 1.16; opposite sides overlap | Generated props with tiling textures | verified (ran) |
| `uv.smart_project` | Stretch 1.00 to 1.37, arbitrary scale; cuts the bent sheet into 2 islands | Props that need unique texels for baking; not cloth | verified (ran) |
| `uv.cylinder_project`, `uv.sphere_project` | Run, but leave degenerate cap faces; stretch up to 3.8 | Avoid | verified (ran) |
| `uv.lightmap_pack` | One island per face | Light baking only | verified (ran) |
| `uv.follow_active_quads` | Needs `bm.faces.active`; then an even grid on the tube | Straps and belts made of quads | verified (ran) |
| `uv.project_from_view` | Poll fails without a 3D viewport | Not usable headless | verified (ran) |
| Image Texture node with `projection="BOX"` on Object coordinates | Option exists with a blend setting; needs no UVs | Hard props, quickest route | verified option, unverified look |

Texel density check, verified on the meshes above: per face, metres per UV unit is
sqrt(3D area / UV area). Report the area-weighted global value and the ratio of the 95th to
the 5th percentile as stretch. Pixels per metre is then image width divided by metres per UV
unit. After any packing operator the scale is arbitrary (0.60 to 1.23 here); multiplying the
UVs by the measured value restores 1 m per unit (verified on the barrel).

## 4. Colour and contrast controls

Tone curves were measured without rendering: a scene-linear chart saved through
`Image.save_render`, which applies the scene's view settings. Display device sRGB.

| View / look | 0.5% grey | 2% grey | 18% grey | 72% | 200% | Yellow sat. | Sky-blue sat. |
|---|---|---|---|---|---|---|---|
| AgX / None (same as Base Contrast) | 0.031 | 0.125 | 0.463 | 0.725 | 0.855 | 0.48 | 0.36 |
| AgX / Medium High Contrast (runs 005, 006) | 0.012 | 0.086 | 0.463 | 0.765 | 0.898 | 0.54 | 0.39 |
| AgX / Very High Contrast | 0.000 | 0.039 | 0.463 | 0.827 | 0.961 | 0.56 | 0.40 |
| AgX / Punchy | 0.004 | 0.039 | 0.345 | 0.635 | 0.796 | 0.63 | 0.49 |
| Khronos PBR Neutral / None | 0.000 | 0.031 | 0.412 | 0.843 | 0.984 | 0.72 | 0.56 |
| ACES 2.0 / None | 0.000 | 0.035 | 0.349 | 0.643 | 0.824 | 0.57 | 0.48 |
| Standard / None | 0.059 | 0.149 | 0.463 | 0.867 | 1.000 | 0.61 | 0.51 |

All rows verified (measured). The reference has deep blacks, highlights held near 0.63 to
0.74 and vest saturation of 0.64 to 0.74 in the mid-tones. Punchy and ACES 2.0 are the two
curves with that shape; Very High Contrast fixes the blacks but pushes highlights up.

| Control | Name in 5.3 | Moves us toward the reference? | Status |
|---|---|---|---|
| Looks | `view_settings.look`; AgX has Punchy, Greyscale and seven contrast steps | Yes: blacks and saturation, see table | verified (measured) |
| Exposure | `view_settings.exposure` | Yes, +0.5 to offset Punchy's darker mid-grey | verified (measured: -1 stop takes 18% grey to 0.322) |
| RGB curves | `view_settings.use_curve_mapping`, `curve_mapping.black_level` | Yes as fine tuning: black level 0.02 sends 2% grey to 0.000 | verified (measured) |
| White balance | `use_white_balance`, `white_balance_temperature` (2000 to 11000), `white_balance_tint` | No gap measured; 8000 K warms the image, 5000 K cools it | verified (measured) |
| Scene effects stack | `scene.compositor_effects.new(name)`, then `.node_group`. `scene.compositing_node_group` warns that it will be removed in 6.0 | Carrier for everything below | verified (API), unverified (execution) |
| Bundled groups in `compositing_nodes_essentials.blend` | Tune Image (Contrast, Color Boost, Clarity, Detail, Sharpen), Split Toning, Vignette, Film Grain, Sensor Noise, Bloom, Chromatic Aberration, Unsharp Mask, Sepia; CC0 | Tune Image is the candidate for the detail gap; no evidence the reference uses vignette, bloom or split toning | verified (loaded, sockets listed), unverified (effect) |
| Compositor nodes | Color Balance (lift/gamma/gain, ASC-CDL, white point), Color Correction, Hue/Saturation/Value, RGB Curves, Glare (Bloom, Fog Glow, Streaks and four more), Lens Distortion, Tonemap, Convert to Display | Hue/Saturation for chroma if the look is not enough; Glare and Lens Distortion not needed | verified (nodes created), unverified (effect) |

## 5. Procedural material techniques

Node availability was checked with `nodes.new` on 5.3. No look was rendered, so every
"look" below is unverified.

| Surface | Technique | Source and licence | Status |
|---|---|---|---|
| Worn leather | Warp the Voronoi distance-to-edge coordinates with noise (Linear Light mix, factor 0.02) so cells become irregular creases; darken the colour in the grooves and in broad noise patches; roughness 0.3 to 0.7; true displacement instead of bump | `princeton-vl/infinigen` @ 53033dd, `fabric/leather.py`, BSD-3-Clause | verified (source read, licence read), unverified look |
| Wear that follows form | Geometry node Pointiness: "dirt maps and wear-off effects" (Cycles only). Ambient Occlusion node: "weathering effects to corners", slow, bake it or use Pointiness | Manual: `render/shader_nodes/input/geometry`, `input/ao`; CC BY-SA 4.0 | verified (pages read, nodes exist) |
| Painted metal | Edge mask from the Bevel node normal (radius 5 to 10 mm, 20 samples) minus the surface normal, through a colour ramp, mixed to bare metal; scratches from stretched noise; Coat for "clearcoat, lacquer or car paint" | Infinigen `wear_tear/edge_wear.py`, `scratches.py`, BSD-3; Manual: `input/bevel`, `shader/principled` | verified (source and pages read) |
| Wool and shearling | Sheen: "very small fibers ... soft velvet like reflection near edges". Hair Info node gives Intercept and Random for darker roots and strand variation. For short dense pile, a fleece texture set with displacement | Manual: `shader/principled`, `input/hair_info`; Poly Haven `curly_teddy_natural`, CC0 | verified (pages read, asset listed), unverified look |
| Canvas webbing | Crossed wave bands (ours already); a brick texture as weave; wave plus noise with displacement; Gabor texture for directional fibre | Infinigen `fabric/sofa_fabric.py`, `lined_fabric.py`, BSD-3; Manual: `textures/gabor` | verified (source and page read) |
| Skin | Subsurface method `RANDOM_WALK_SKIN`; radius (0.482, 0.169, 0.109), IOR 1.4, roughness 0.5, linear base colour (0.623, 0.433, 0.343) for type III and (0.436, 0.227, 0.131) for type IV. Our `soften_skin` radius has the same ratio | Physically Based API, CC0; enum checked on 5.3 | verified (values fetched, enum exists) |
| Fetch scripts to learn from | Downloaders for ambientCG and Poly Haven sets | `DLR-RM/BlenderProc`, GPL-3; `Poly-Haven/polyhavenassets`, GPL-3 | verified (repositories and licences), unverified (code not opened) |

## Mistakes and dead ends

- No compositor tree was executed and no look was applied to our own frames, because
  rendering was off limits. The predicted gains in changes 2 and 5 come from the chart and
  need a small render to confirm.
- Four material patches were dropped: one helmet patch landed on skin, one webbing patch in
  shadow, and one helmet and one face patch straddled two surfaces. Positions were chosen by
  eye and no crop of a reference frame was saved anywhere.
- Reference frames are video-compressed and tone-mapped by an unknown pipeline. Their
  colours are display targets, not albedo. Grain could not be assessed.
- `tools/html_to_text.py` fails under the bpy interpreter (no `bs4` there); the system
  `python3` runs it.
- `bl_rna` enum lists for display, view and look return only `NONE`; the real lists came
  from the error raised by assigning an invalid value.
- `CompositorNodeGamma` does not exist in 5.3; the compositor takes `ShaderNodeGamma`.
  `ShaderNodeBrightContrast` and `ShaderNodeHueSaturation` are refused there.
- Not reachable or not checked: Smithsonian API (429 with the demo key), Wikimedia Commons
  API (429), `blender.org/download/demo-files` (403), cgbookcase licence page (404),
  GitHub contents API (blocked for this session), manual pages for the Geometry Nodes UV
  nodes (guessed URLs gave 404).
- `git ls-remote` found no `blender/blender-manual`, `blender/blender-assets` or
  `blender/blender-studio-tools` on GitHub. `blender/blender` exists.
- Sketchfab returned no CC0 result for "ww2 pilot".
- Scripts and raw outputs are in
  `/tmp/claude-0/-home-user/bce94795-3d17-5044-8bec-4d67a098d1a2/scratchpad/look/`
  (`measure.py`, `patches.py`, `detail.py`, `tonecurve.py`, `uvtest.py`, `uvtest2.py`,
  `panel_uv.py`, `compnodes.py`, `matnodes.py`). That folder is temporary; none of it is in
  the repository or in `sources/log.md` yet.
