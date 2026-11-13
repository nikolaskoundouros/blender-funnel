# Tutorial notes: "Noob vs Pro Artist 3D Pants Design in Blender" (pro pants, 0:08 to 1:36)

Source: 96 s vertical short supplied by the owner (top: Blender screen recording; bottom:
a reaction clip, ignored). Music only, no speech used. Frames read at 1 per second plus
full-size frames of the panels. Blender version not shown. Trust D. Video kept out of git.

| Claim | Evidence | Status |
|---|---|---|
| A plane is added in front of the T-posed body (front orthographic view) and scaled from waist to ankles, wider than the hips | 0:08 to 0:14 | unverified |
| The plane is subdivided into a dense grid (about 40 x 60 squares), and a narrow column of faces is deleted from the bottom up to the crotch, giving a two-legged panel | 0:18 to 0:28 | unverified |
| The panel is duplicated behind the body: a front panel and a back panel | 0:30 to 0:48 (side and top views) | unverified |
| The two panels are joined at the outer side seams and inner leg seams by edges for sewing (the "sew" search at 0:57 opens Shape > sewing) | 0:49 to 0:57 | unverified; values below the visible panel |
| The body is a collider (Physics > Collision on the mannequin) | 0:54 to 1:00 | unverified |
| Cloth: quality steps 10, mass 0.3 kg, collision quality 15, self collision on, friction 5, distance 0.015 m | panels 0:56 to 1:16 | readable |
| Gravity 0 (Field Weights) | 1:17 | readable |
| A shrink setting is changed (search "shrink" at 1:10 to 1:15); value not visible | 1:10 to 1:15 | unknown value |
| Simulated (cache 1 to 250 frames): the sewing pulls the panels together round the legs and the shrink tightens them, giving fitted trousers with natural folds | 1:19 to 1:32 | unverified |
| Afterwards: Solidify (thickness about 0.02 m shown, "Simple" mode) and Subdivision Surface are added after the Cloth modifier | 1:25 to 1:31 | unverified |

How this maps to our tools: `cloth.add_cloth` already turns on sewing springs when the mesh has
loose edges, and `patterns.build` (route C) places flat panels. This method is simpler than
GarmentCode's: two rectangles with a slit, sewn at four seams, no gravity, then shrink.
Test it as route F: for loose track pants, keep the shrink small so the legs stay roomy.
