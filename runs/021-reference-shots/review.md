# Run 021 review: the reference's camera moves on our two characters (14 Nov 2026)

Test: does the clip analyzer's reading of "My Mom Cracked The Dinosaur" (0 to 12.6 s) hold enough to
re-create its camera work in Blender? Each of the 13 shots got a hand-set start camera; every frame
after that was driven only by the analyzer's numbers (motion_0_12.json). Rendered on the shared
RTX 4090 pod: 379 frames at 360x640, 16 samples, 3 min 25 s (OptiX). The clip analyzer was then run
on our render with the same settings as on the reference (review/compare.py, review/compare.json).

## Measured (analyzer on ours vs analyzer on the reference, same frames)
- Zoom curve correlation 0.86, pan curve correlation 0.93 (per frame, 379 frames).
- All 9 reference zooms of 20% or more go the same way in ours:

| time | reference | ref zoom | ours |
|---|---|---|---|
| 0.00 s | pull out | -68.1% | -65.0% |
| 1.63 s | push in | +35.4% | +36.1% |
| 2.37 s | pull out | -20.1% | -16.6% |
| 4.07 s | dolly in | +289.8% | +329.1% |
| 5.87 s | push in | +24.9% | +6.2% |
| 6.13 s | dolly in | +48.1% | +22.5% |
| 8.00 s | dolly out | -77.2% | -65.0% |
| 10.97 s | move left | -28.9% | -26.5% |
| 11.33 s | pull out | -29.4% | -46.8% |

- Brightness after two light cuts: 0.24 average over the 13 shot stills vs 0.26 for the reference.

## Still wrong
1. Whips: 36 reference frames are whips; the analyzer reads only 2 of ours as whips. Ours turn
   too little blur into the picture (shutter 0.5, one key per frame) and cut hard to the next shot,
   where the reference smears through. Next question: whip in AND out (the next shot starts mid-whip),
   longer shutter on whip frames.
2. Orbit at 0.7 to 1.6 s: the reference circles to the boy's 3/4 back; ours stays in front. The
   analyzer's 3D reading is "unsure" on 224 of 379 frames (15 of the 27 orbit frames), and the driver
   turns an orbit only by the size of the picture's sideways slide, so the orbit comes out far too small. Next question: read orbit angle from the subject staying put while the background slides.
3. 5.87 to 6.7 s (frames 176-198) the push reads +84.9% in the reference but +30.1% in ours, although
   all 23 frames are tracked and the driver applied every reading. Cause not found yet. A guess to
   test, not a finding: the driver dollies toward one aim point, and a dolly enlarges near and far
   things by different amounts, so the frame-wide size change the analyzer reads can come out smaller.
4. S10 dolly out passes behind the boy's head at the end (one shot of orange hair fills the frame).
5. Characters do not move (Mom does not slap the leg or drag the boy); Mom is still the placeholder.

## Files
review/side_by_side.mp4 (reference left with its sound, ours right), review/sbs_sheet.jpg,
review/whip_sheet.jpg, review/compare_stills_v3.jpg, review/compare.json, review/compare.py.
Our render is also in the clip analyzer as clip "run021-ours" for frame-by-frame viewing.

## Step 3, 14 Nov 2026: the opening shot with the camera solved from the reference (COLMAP)
The 2D readings could not make an orbit (0 of 55 orbit frames, 7% sideways travel). So the reference's
frames 0-54 were solved with COLMAP 4.2.1 / pycolmap (BSD licence, read from its LICENSE file) on the box:
55 of 55 frames, 0.79 px mean reprojection error, lens 36.1 mm. build.py `SOLVED=solved_s1.json` puts
that path on our boy (origin = solved points on the reference boy's hair, forward = toward the first
frame's camera, scale from the curls' width x `SOLVED_SCALE` 0.63, measured from the first render).

| check (frames 0-54) | reference | v2 (driven) | solved |
|---|---|---|---|
| camera round the boy, frames 9-48 (COLMAP on each video; ours measured on the first solved render, before the scale fix, which does not change angles) | 93.3 deg | not measured | 91.8 deg |
| reference orbit frames our analyzer also reads as orbit | 15 | 0 | 13 |
| camera travelling sideways or up (trusted 3D frames) | 64% | 4% | 67% |
| boy's hair height vs reference, frames 12-48 (median) | 1.00 | | 1.00 (correlation 0.99) |
| frames with hair height within 15% of the reference | | | 25 of 49 |

Still wrong: frames 0-11 show the boy 1.29x too big (the close-up is sensitive to where the anchor sits);
the reference boy turns further away from camera than ours (his own body turn, likely, not the camera:
not verified); our boy's hands are not behind his back. Files: review/solved_s1/.
