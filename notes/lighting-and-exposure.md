# Lighting and exposure

Status values: **verified (render)** measured in `experiments/results.json` ·
**verified (API)** checked on Blender 5.3.0 · **unverified** not yet tested.

## Claims

| # | Claim | Source | Status | Evidence |
|---|---|---|---|---|
| 1 | A larger light radius gives softer shadows | Manual, Light Objects | verified (render) | E1: shadow edge 2 px wide at radius 0.02 m, 30 px at 1.0 m |
| 2 | Each +1 stop of exposure doubles pixel values | Manual, Displays and Views | verified (render) | E2: ratio 2.002 under the Raw view |
| 3 | AgX desaturates over-exposed colours; Standard clips them | Manual, Displays and Views | verified (render) | E3: highlight saturation 0.63 Standard, 0.45 AgX |
| 4 | The procedural sky is too bright at exposure 0 | Manual, Sky Texture | verified (render) | E4: 84% of pixels clipped at exposure 0; none at -2, but median still 0.90; 0.75 at -4 |
| 5 | AgX is the default view and Filmic is deprecated | Manual + API | verified (API) | New scene reports `AgX`, look `None` |
| 6 | Look names carry the view prefix since 4.0 | Tutorial repo | verified (API) | 5.3 rejects `"High Contrast"`, accepts `"AgX - High Contrast"` |
| 7 | Sun strength is W/m², other lights are watts | API descriptions | verified (API) | `SunLight.energy` description |
| 8 | New materials and worlds already have node trees in 5.x | Deprecation warning | verified (API) | `use_nodes` warns "expected to be removed in Blender 6.0" |
| 9 | Lower f-stop gives more background blur | API description | unverified by measurement | Used at f/2.8 in run 001; blur visible on the backdrop |
| 10 | Key, fill and rim lights separate a subject from its background | Search summaries | unverified by measurement | Used in run 001; looks right, no metric yet |
| 11 | A curved backdrop removes the horizon line | Prior knowledge | unverified by measurement | Used in run 001; horizon band is gone |
| 12 | Track To is a "legacy tracking constraint prone to twisting" | API description | unverified | Recipes use it for aiming. Fine for still frames; check before animating cameras |
| 13 | Khronos PBR Neutral keeps material colours closest to their input values | Manual | unverified | Candidate for product-style renders |
| 14 | False Color view shows exposure as a heat map (grey = 16 to 22%) | Manual | unverified | Candidate for an automatic exposure check |

## What changed in practice

- The flat demo had ambient light almost as strong as its key light. Ambient world strength
  went from 0.5 to 0.03, so shadows now come from the key.
- Light power is not guessable. 1500 W on a 2 m subject at 6 m over-exposed (median 0.88);
  300 W gave 0.62. Measure with `tools/image_stats.py` before a full render.
- A sky world needs roughly -4 stops or more of exposure. Do not combine it with lamp powers
  tuned for exposure 0.

## Mistakes made during verification

Both were mine, not the manual's, and both produced a false "not confirmed":

- E1 first counted every mid-brightness pixel on the scanline. A point lamp's light falls
  off with distance, so the whole lit floor counted as "partial shadow". Fixed by measuring
  only the climb out of the shadow core.
- E3 first used a light so strong that all three colour channels clipped to white under
  Standard, leaving no colour to compare. Fixed by lowering the light until only red clipped.

## Open questions for the next pass

1. How should a metal object be lit so it has something to reflect? (Copper in run 001
   reflects an empty studio.)
2. Can exposure be set automatically from a small test render, using the False Color ranges?
3. What do the manual's camera pages say about composition aids and sensor fit?
