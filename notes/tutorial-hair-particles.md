# Tutorial notes: "Create Hair / Fur in Blender 4.2 using Particle System" (FilmTush)

Source: 52 s vertical short supplied by the owner on 13 Nov 2026. Studied from one frame per
second, full-resolution crops of the settings panels, and a transcript of the voiceover
(faster-whisper, base.en model). Status values as elsewhere: **verified (API)** checked on
Blender 5.3.0 · **unverified** not tested.

## The method, step by step

| Time | Step | Exact settings seen or said |
|---|---|---|
| 0:03 | Add a UV sphere, right click, Shade Smooth | Default sphere, 1 m radius |
| 0:05 | Material Properties: two materials, one for the sphere (skin) and one for the hair | Hair material's shader switched to **Principled Hair BSDF** |
| 0:15 | Weight Paint mode: paint where hair should grow | Red = grow, blue = none; painted a scalp patch on the top and back |
| 0:19 | Rename the vertex group (optional), e.g. "hair group" | |
| 0:21 | Add a Particle System, switch Emitter to **Hair** | Number 1000, Hair Length 1.76 m (on a 1 m sphere), Segments 5 |
| 0:24 | Render > Material: pick the hair material; Vertex Groups > Density: the painted group | Render As: Path, Steps 3, B-Spline off |
| 0:28 | Adjust Hair Length; **Particle Edit** mode: comb the strands with the brush; back to Object mode | Combing is done by hand |
| 0:34 | Children: **Interpolated** | Voiceover says "set values to 200". Panel shows Display 200 / Render 100 at one moment and Display 500 / Render 50 later, so the numbers were changed during the video |
| 0:40 | Render Properties: engine **Cycles** | Shown briefly in EEVEE first |
| 0:43 | Particle system: **Hair Dynamics** on, for automatic movement | |
| 0:46 | **Pin Goal Strength 0.460** (said; caption "4 6 0") | Keeps roots and shape from collapsing under gravity |

## What it gets right

- **Guides plus children** is the key idea: style and simulate ~1,000 guide strands, and let
  Blender interpolate 100 to 500 children around each one for render. Cheap to style, dense
  to look at.
- **Painted density map** controls where hair grows and how thick it is, without cutting
  geometry.
- **Principled Hair BSDF** is the right shader (we use it too).
- **Hair dynamics with a pin goal** gives sway and bounce with almost no setup.

## Caveats

- **This is the legacy hair system.** Particle hair still works in Blender 5.3 (verified:
  created headlessly with the same settings), but Blender's current hair system is
  Curves objects shaped with geometry-node tools. New features go there, not to particles.
- **Combing by hand** in Particle Edit mode cannot be scripted repeatably; it is fine for one
  character, not for a toolkit.
- **The children numbers are inconsistent** in the video (see 0:34). 200 per guide is a
  normal viewport value; render values are usually higher than display, not lower.
- **Hair Length 1.76 m** only makes sense on the 1 m test sphere. On a real head this would be
  centimetres.
- **Pin Goal Strength 0.46** is a starting point; stiffer for short hair, lower for long hair.
  It maps to `ClothSettings.pin_stiffness` in Python (verified (API)).
- Nothing on clumping, curl, frizz, roughness, colour variation or hair thickness, which are
  what make hair look real.

## How it maps to our pipeline

| Tutorial step | Our equivalent today | What to adopt |
|---|---|---|
| Weight-painted growth area | Strands rooted on chosen faces (`hair.sample_surface`) | A density map: weight per vertex instead of in/out faces, so edges thin out naturally |
| 1,000 hand-combed guides | Every strand generated and combed by direction vectors | Generate a few hundred guides by code, then interpolate |
| Interpolated children | None: we create every strand (up to 400,000) | Blender 5.3 bundles **Interpolate Hair Curves** for the Curves system (verified (API)); likely faster and better looking |
| Principled Hair BSDF | Same, with per-strand colour variation | Add melanin-based colour and random roughness |
| Hair dynamics, pin goal | Strands are static; they do not follow motion | Blender 5.3 bundles a **Hair Dynamics** node group in its XPBD simulation assets (verified (API)); test it on the dancer's ponytail |
| Not covered | — | Bundled Clump, Curl, Frizz, Braid, Trim and Smooth Hair Curves node groups |

## Proposed experiment (not done)

Rebuild the shearling collar or a short haircut as: ~300 code-generated guides on the Curves
system, `Interpolate Hair Curves` for density, `Clump` and `Frizz` for texture. Compare look
and build time with the current all-strands approach, side by side.
