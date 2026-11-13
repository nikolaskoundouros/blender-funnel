# Cloth: making garments hang and fold

Status values: **verified (test)** measured in `experiments/results_cloth.json` or in
`runs/006-draped-jacket/stats.json` · **unverified** not yet tested.

## Claims

| # | Claim | Source | Status | Evidence |
|---|---|---|---|---|
| 1 | An object with a Collision modifier deflects cloth; pinned vertices stay put | Manual, Cloth | verified (test) | C1: sheet fell 1.0 m over a ball, 0 vertices inside it, pinned corner moved 0.0 mm |
| 2 | Edges that belong to no face act as sewing springs | Manual, Cloth Shape | verified (test) | C2: 9 loose edges closed a 20 cm gap between two panels to 0 |
| 3 | A negative shrinking factor makes cloth grow | Manual, Cloth Shape | verified (test) | C3: -0.1 made a 1 m sheet 1.21 m² |
| 4 | Cloth must rest on a complete body | Own finding | verified (test) | Run 006: against the visible body (skin under garments removed) sleeves fell onto bare arms; against a complete invisible copy, 0.06% of jacket vertices sit inside the skin |
| 5 | Spare material plus gravity turns a shell garment into folds | Own method | verified (test) | Run 006: average angle between neighbouring faces rose from 4.1° to 10.3° with 6% spare leather, pinned at the yoke; simulation 38 s for 45 frames |
| 6 | The pip build exposes `bmesh` only after `bpy` is imported | Own finding | verified (API) | Import order error in the first run of verify_cloth.py |
| 7 | Stiffer bending gives fewer, broader folds (leather vs cotton) | Manual, physical properties | unverified | Leather preset used; not compared |
| 8 | Panels sewn together drape better than an inflated shell | Common practice | unverified | Not attempted; sewing itself works (claim 2) |

## Mistakes made on the way

- Collided cloth with the visible body, which has holes under garments.
- Measured "inside the skin" against that same holed body and got 49%, a repeat of the
  measuring mistake from the rig pass.

## Open questions

1. Build the jacket from sewn panels (front, back, sleeves, collar) for seams and a front
   opening, instead of an inflated shell.
2. Sharper, smaller creases at elbows and armpits: more resolution, less bending stiffness.
3. Simulating through motion, not just settling in one pose.
