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
| 9 | Cloth self collision ignores only triangle pairs that share a vertex; triangles one row apart within 2 x self distance repel on every step | Blender 5.3.0 source, `collision.cc` (`cloth_bvh_selfcollision_is_active`, `cloth_selfcollision`) | verified (test) | `results_hem.json`: same tube, 5.6 mm cloth edges: +14.9 cm hem rise at 4 mm self distance, -1.8 cm at 1.5 mm; 11.6 mm edges: -1.5 cm at 4 mm. Simulation 9x slower when it happens (467 s vs 50 s) |
| 10 | Route B's hem rise (run 013) is caused by claim 9, not by pinning, pose motion, gravity or the colliders | Own experiment | verified (test) | `results_hem_real.json`, run 013 scene, one change each: self distance off / 1 / 1.5 / 4 (as run) / 8 mm gives -0.2 / +0.7 / +2.5 / +7.7 / +14.5 cm. Still rising with: rest pose, nothing moving (+7.0), posed at once (+9.4), no pin (+7.0), no gravity (+11.9), no colliders (+17.0), single-sided collision off (+6.1), no subdivision (+3.1, coarser edges). Spare material not varied on this scene (tube: no effect). Cloth edges after one subdivision: 2nd percentile 3.5 mm, median 11.5 mm |
| 11 | Self distance: hard minimum 1 mm, default 15 mm; object collision distance also 15 mm default | Installed 5.3.0 `ClothCollisionSettings` property ranges | verified (API) | `bl_rna` read: `self_distance_min` hard_min 0.001, default 0.015 |
| 12 | Safe self distance is about 0.3 x the cloth's 2nd-percentile edge length (after the resolution subdivision); below 3.3 mm edges self collision must be off | Own rule from claims 9 and 11 (a split quad's triangles one row apart are ~0.7 edge apart) | verified (test) | Real tee: cap 1.05 mm, hem +0.7 cm (`capped`); fine tube: cap 1.52 mm, -1.8 cm (`fine_capped`); check `check_cloth_self_distance_cap` |
| 13 | Collision is single sided by default (`use_culling`): cloth behind a collider face is pushed along that face's normal, so a collider with inward normals swallows the cloth | Manual (Collision) + `collision.cc` `compute_collision_point_tri_tri` | verified (test) | Tube on inward-normal body: +5.1 cm rise, 98% of points end inside; same with culling off: -1.5 cm, 0 inside. MakeHuman body collider: normals outward (signed volume +0.032 m³, 0 shirt points behind faces, `results_collider_sides.json`) |
| 14 | Shrinking factor rescales structural, shear, bending and internal springs alike and is re-applied every step; rest shape is the first frame's mesh unless Dynamic Mesh or a rest shape key is set | `cloth.cc` (`cloth_update_spring_lengths`, `cloth_shrink_factor`); manual (Shape) | verified (source read) | Code read; no separate experiment. Consistent with tube `no_spare` (hem -0.3 cm vs -1.5 cm with 2% spare) |

## Mistakes made on the way

- Rising-hem pass (14 Nov 2026): my first test body had inward normals, and the tube
  experiment reproduced a rise for the wrong reason (claim 13). A count of points inside the
  body and a look at the face winding caught it before it was blamed on the solver.

- Collided cloth with the visible body, which has holes under garments.
- Measured "inside the skin" against that same holed body and got 49%, a repeat of the
  measuring mistake from the rig pass.

## Open questions

1. Build the jacket from sewn panels (front, back, sleeves, collar) for seams and a front
   opening, instead of an inflated shell.
2. Sharper, smaller creases at elbows and armpits: more resolution, less bending stiffness.
3. Simulating through motion, not just settling in one pose.
4. Why claim 9's spurious contacts move the cloth *up* rather than spreading it evenly is not
   explained (the tube also narrows by 1.3 cm while rising). The fix does not depend on it.
5. The pro-tutorial settle (`SETTLE=1`, run 013) uses 1.5 cm self distance on a twice
   subdivided shirt: by claim 12 it will bunch. Re-run with the capped recipe.
