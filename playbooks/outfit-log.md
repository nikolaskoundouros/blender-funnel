# Outfit log

One row per outfit attempt, newest last. "Tries" counts simulate-and-look cycles.

| Date | Outfit | Route per layer | Tries | What failed, in order | Outcome |
|---|---|---|---|---|---|
| 13 Nov 2026 | Three casual outfits (run 002) | Downloaded MakeHuman garments | 1 | Nothing | Usable; not from scratch |
| 13 Nov 2026 | Tops, trousers, skirts, boots (pass 4 test) | A: shells | 2 | Jagged hems (faces dropped at the edge); fabric pattern far too coarse | Usable for under-layers; hems still wavy; sleeveless top wrong |
| 13 Nov 2026 | Pilot jacket, helmet, collar (run 005) | A: shells, with strand fur and goggles | 2 full renders | Jacket read as bare skin; strap floated; framing too wide; leather too pale | Recognisable ingredients, no cloth structure |
| 13 Nov 2026 | Pilot jacket, draped (run 006) | B: draped shell, then panels | 4 | No collision body (sleeves on bare arms); shoulder seams tore | Works: folds, seams, open front over a shirt |
| 13 Nov 2026 | Shirt from GarmentCode pattern (run 007) | C: sewn pattern | 3 | Sewing too violent; shoulder seam below the shoulders | Works as a short-sleeved shirt |
| 13 Nov 2026 | Jacket from drafted pattern (run 007) | C: sewn pattern | 4 | Sleeves missed arms (other body's measurements); wrong head measurement; body slid to waist | Not usable yet: sleeves bunch, one seam open |
| 13 Nov 2026 | Pilot likeness (run 008) | B: draped shell jacket; A: shirt, trousers, helmet with cheek flaps, collar; strand shearling and moustache; goggles | 1 | Nothing failed; first use of the playbook | Recognisable palette and layers under daylight. Missing: vest, harness, clouds, closer camera |
| 13 Nov 2026 | Pilot outfit detail: flight trousers with cargo pockets, boots, jacket seams and straps, shearling cuffs, life vest, harness, release box, hose, belt, cartridges (run 009) | A and D, no cloth simulation | 10 | Wavy pockets; NaN pocket positions; crotch showing; leggings shape; shirt through waistband; vest cut to tabs; vest too short; straps and box hidden under channels; box in vest gap; cartridges merged | Every major piece of the reference outfit present and recognisable |

## What the log says so far

- Route B took 4 tries the first time and 1 try the second time (run 008), following the playbook.
- Route D (detail pieces) took 10 tries the first time, but each try is about 25 s, so the
  whole outfit took under 10 minutes of rendering. Every failure is now in the table.
- Route C has cost 7 tries and is not reliable. Each try is about 2.5 minutes of
  simulation plus a render.
- The same mistake happened twice (measuring against the holed body). It is now in the
  failure table and should be built into the recipe.
| 012 curls | Orange curly mop on a boy (clip: My Mom Cracked The Dinosaur) | 5 steps | ~18 s build, 90 s render | Ringlets, colour, silhouette close; looser C-shaped curls and peach highlights still differ |
| 013 boy outfit | Tee, blue track pants with red stripe (owner's change), yellow trainers | 6 steps | ~30 s build, ~70 s render | Shapes and colours right; tee stiff (draping over trousers failed), no chest print yet |
