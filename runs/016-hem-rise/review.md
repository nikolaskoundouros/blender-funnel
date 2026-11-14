# Run 016: why the draped T-shirt's hem rises (HANDOFF question 1)

Not a new outfit: the run 013 route-B scene rebuilt by `experiments/hem_real.py`, one
setting changed per variant, then the fix checked. Images: 240x320, 16 samples.

- `compare.png`: self distance 4 mm (as in run 013), 1 mm, self collision off.
- `capped.png`: the new `recipes.cloth.add_cloth` default (cap 1.05 mm). `stats.json` from it.

## What improved
- Cause found: self-collision distance too large for the cloth's edge length (notes/cloth.md
  claims 9 to 12). Hem change over 40 frames: +7.7 cm before, +0.7 cm with the cap.
- The fix is in the recipe, with a check (`check_cloth_self_distance_cap`), so the pro-tutorial
  settle (`SETTLE=1`, 15 mm self distance) is now capped too.

## Still wrong
- With 1 mm self distance the shirt hangs straight but shows few folds; the route-B shell
  is still a shell (no seams, no shoulder slope). Compare against route E before switching.
- Why the spurious contacts lift the cloth rather than spread it is unexplained.

## Next questions
1. Re-run run 013 with `TEE=shell` and the capped recipe at full size, side by side with
   route E and the reference clip.
2. Re-run the `SETTLE=1` pro-tutorial method (was 15 mm on 2x-subdivided cloth).
