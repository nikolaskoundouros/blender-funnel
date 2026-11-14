# Handoff: where the research stands (14 Nov 2026)

Read `CLAUDE.md` first (the loop and rules), then this.

## Done, with recipes and playbook entries
- Characters from MakeHuman CC0 data (`recipes/human.py`), rigs and poses, CMU mocap clips.
- Code sculpting (`recipes/sculpt.py`): grab, inflate, flatten, smooth, scale at named
  landmarks; `sculpt.clothes(...)` edits only the clothing helper layer. Checks K1 to K4 pass.
- Hair: short cuts and orange curls (`recipes/haircut.py`, `recipes/looks.py`).
- Skin detail: freckles in UV space, tone matched by measured colour, two eye colours (`recipes/skin.py`).
- The curly-haired boy (runs 012, 013): ready-made CC0 T-shirt loosened by clothing-layer sculpt,
  chest print on garment UVs (`recipes/prints.py`), blue track pants with red stripe.
- Trainers by code (`recipes/shoes.py`, run 015): footprint soles, upper, seams, eyelets, laces.
- Playbooks: `playbooks/outfit.md` (routes A to F, every failure with its fix), `outfit-log.md`.

## Open questions (next research)
1. **Draping a T-shirt rises 5 to 10 cm** in every variant tried (playbook: "Draping a
   T-shirt (route B) over trousers: not solved"). Find the cause in Blender's cloth solver
   (rest shape, shrink, collision response on sloping hips) before more trial runs.
2. **Tutorial methods not yet run to the end** (too slow on a 4-core cloud machine):
   pro T-shirt (`notes/tutorial-pro-tshirt.md`, `SETTLE=1` in run 013) and sewn-panel
   pants (`notes/tutorial-pro-pants.md`, `recipes/panels.py`, run 014). Run on the owner's
   RunPod when it is set up; the render recipe still needs a GPU option.
3. **Facial mocap**: survey done (`notes/facial-mocap-survey.md`, `notes/tutorial-facetracker.md`):
   MediaPipe Face Landmarker (Apache-2.0) gives 52 ARKit-named blendshapes; MakeHuman
   "Faceunits 01" has the same names for our base mesh (licence still to be checked by us).
   Next: confirm that licence, build video -> per-frame blendshapes -> shape keys, verify on a
   real face clip (needs one from the owner).
4. **Shoes**: tongue and padded collar missing; put the code-built trainers on the boy.
5. **Shoemaster tutorial** (YouTube k-VGL4jRPnw) not watched: YouTube blocks cloud machines.

## Environment notes
- Blender 5.3 as `bpy` needs Python 3.13. Assets: `tools/fetch_assets.sh`.
- Cloud sessions: 4 cores, no GPU, 30-minute limit on background jobs. Keep cloth runs small.
- YouTube is blocked from the cloud; the owner's analyzer or uploads are used instead.
