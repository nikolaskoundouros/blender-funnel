# Run 001 review: flat render

**Brief.** Same three objects as the first demo. Make the image read as lit, not flat.

**Built from.** `recipes/` only: backdrop, three-point lights, dim world, camera with
depth of field, AgX with the Medium High Contrast look.

## Numbers (Blender 5.3.0, 960x540, 64 samples)

| | Before | After |
|---|---|---|
| 5th percentile brightness | 0.52 | 0.34 |
| Median brightness | 0.68 | 0.65 |
| 95th percentile brightness | 0.76 | 0.77 |
| Spread (95th minus 5th) | 0.24 | 0.43 |
| Clipped pixels | 0.01% | 0.11% |

Spread is the useful figure: the before image had almost no dark values at all.

## What improved

- Objects now cast clear, soft-edged shadows that show where they sit.
- The horizon band behind the objects is gone.
- The copper shows highlights and a dark side instead of an even tone.
- The background falls slightly out of focus.

## Iterations it took

1. Key light at 1500 W: over-exposed, median 0.88. Lowered to 300 W.
2. Camera aimed at the monkey cropped the cube at the frame edge. Aimed at a point
   between the objects and widened the lens from 50 to 42 mm.

## Still wrong

- The copper reflects an empty room, so it reads as plastic-like in places.
- The floor is brighter than the subject; attention goes to the floor.
- The monkey's shadow and the cube's shadow merge into one dark patch at the bottom.
- "Looks lit" was judged by eye plus one spread figure. There is no reference image to
  match, so there is no real target.

## Next questions

Carried into `notes/lighting-and-exposure.md`: reflections for metal, automatic exposure,
composition. A reference image or clip would turn the next review into a comparison.
