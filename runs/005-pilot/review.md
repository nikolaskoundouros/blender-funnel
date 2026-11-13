# Run 005 review: pilot close-up

**Brief.** One hero close-up in the style of the owner's reference (aviator in a cockpit),
to find out how close code-driven Blender gets.

**Built from.** `human.py` for the body; new this pass: `garments.py` (jacket, collar,
helmet cut from the body's helper shells), `hair.py` (strand fur and moustache),
`accessories.py` (goggles), `materials.py` (leather, hair fibre, softened skin). Only the
skin texture, eyebrows and eyelashes are downloaded assets.

## Result (Blender 5.3.0, 864x1080, 160 samples, CPU only)

`pilot_v1.png` and `pilot.png` (version 2). Version 2 changed only the leather.

## What holds up

- Collar fur: 70,000 strands; reads as wool.
- Moustache: 2,600 strands rooted on the upper lip, combed outward, longer at the ends.
- Goggles: swept frames, domed glass lenses, padded cups; eye and lashes show through.
- Skin: subsurface scattering removes the painted look.
- Shallow depth of field on an 85 mm lens.

## Iterations it took

1. Jacket at 2 cm ease showed every muscle and read as bare skin: raised to 4 cm with
   ten smoothing passes.
2. Goggle strap sized to the ears floated off the head: sized to the temples.
3. Camera at 1.6 m was too wide: moved to 1.1 m.
4. Leather at a colour value of 0.10 rendered pale taupe: dark brown is about 0.03.
   Grain reduced from 2.5 mm to 1.4 mm; at 2.5 mm it looked like cracked eggshell.

## Still wrong, against the reference

- Jacket is a smooth shell: no folds, seams, zip, lapels or cuffs. This is the largest gap
  and cannot be closed with shell garments; it needs panels and cloth simulation.
- Collar is a flat bib of fur, not a rolled collar with a leather underside.
- Helmet is a plain dome: no seams, ear flaps, chin strap or stitching.
- Goggle strap is a straight stub at the temple; it should wrap from the frame.
- Face has no expression; eyes look straight ahead.
- No cockpit, harness, gloves or control stick.
- Strands are placed once and would not follow the body in motion.
- Nothing here was measured. Unlike earlier passes, this run has no numeric checks.

## Next questions

1. Cloth: build a garment from flat panels, sew and drape it with Blender's cloth solver,
   and measure whether it stays on the body in a pose.
2. Garment construction details: seams, hems, collars with an underside, straps.
3. Face: apply the expression targets in the MakeHuman data; aim the eyes.
4. Make strands follow a moving surface.
5. Add fit and poke-through checks for generated garments to the test suite.
