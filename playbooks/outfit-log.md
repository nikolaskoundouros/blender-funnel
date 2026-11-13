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

## What the log says so far

- Route B took 4 tries the first time. With the playbook it should take 1.
- Route C has cost 7 tries and is not reliable. Each try is about 2.5 minutes of
  simulation plus a render.
- The same mistake happened twice (measuring against the holed body). It is now in the
  failure table and should be built into the recipe.
