# Tutorial notes: "Noob vs PRO Realistic Clothes in Blender" (pro T-shirt, 0:05 to 1:12)

Source: 73 s vertical short supplied by the owner (top half: Blender screen recording with
key-press overlay; bottom half: a film clip as a reaction, ignored). No speech (music only;
the transcript is empty), so everything comes from frames at 1 per second plus full-size
frames of the property panels. Blender version not shown. Trust D. Video kept out of git.

| Claim | Evidence | Status |
|---|---|---|
| The shirt starts as a cube flattened front to back (S X), cut with loop cuts (Ctrl+R), sleeves extruded, neck shaped with bevel (Ctrl+B), hem, neck and sleeve-end faces deleted | key overlays 0:05 to 0:22 | unverified |
| A second object (a box, "Cube.001") is added inside the shirt as the body to collide with | 0:25 to 0:29, outliner at 0:51 | unverified |
| Cloth with default settings: quality 5, mass 0.3 kg, air 1, angular bending, stiffness tension 15 / compression 15 / shear 5 / bending 0.5, damping 5 / 5 / 5 / 0.5, collision quality 2 | panels 0:53 to 0:56 | matches Blender 5.3 defaults (our `cloth.FABRICS["cotton"]` uses the same stiffness) |
| Self collision switched on, friction 5, distance 0.015 m | panels 0:57 to 0:59 | unverified |
| No pinning: the shirt is simply played (Space) and falls onto the box | 0:58 to 1:02 | unverified |
| A Subdivision modifier (Catmull-Clark, levels viewport 3, render 2) above the Cloth modifier, so cloth runs on the dense mesh; at level 1 the result crumples (1:03), so it was undone and raised | 1:03 to 1:07 | unverified; our `add_cloth(resolution=1)` uses level 1 |
| The simulation is stopped at a good-looking frame (54) and applied (Ctrl+A) | 1:08 to 1:12 | unverified |

What differs from our attempts (run 013 steps 3 to 10): we pinned the yoke, used one
subdivision level, started from a body-hugging shell instead of a boxy one, and collided
with a full detailed body. Next test: route E's modelled T-shirt with subdivision 2 before
the cloth, self collision 0.015 m, no pins, settled on the body, best frame kept.
