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
1. **Draping a T-shirt rises 5 to 10 cm: solved (14 Nov, run 016).** Cause: cloth
   self-collision distance larger than the cloth's triangle spacing (neighbour triangles
   repel). `cloth.add_cloth` now caps it; hem +0.7 cm instead of +7.7 cm. Next: full-size
   route-B re-run beside route E; re-run the `SETTLE=1` pro method (was 15 mm). See
   `notes/cloth.md` claims 9 to 14 and `playbooks/outfit.md`.
2. **Tutorial methods not yet run to the end** (too slow on a 4-core cloud machine):
   pro T-shirt (`notes/tutorial-pro-tshirt.md`, `SETTLE=1` in run 013) and sewn-panel
   pants (`notes/tutorial-pro-pants.md`, `recipes/panels.py`, run 014). Run on the owner's
   RunPod when it is set up; the render recipe still needs a GPU option.
3. **Facial mocap**: Faceunits 01 licence confirmed CC0 (14 Nov; host index, pack JSON,
   contributor page). Fetched by `tools/fetch_assets.sh`; `morphed_base(expression={"jawOpen": 1})`
   works and units render correctly (run 017). Plan with checks P1 to P6 in
   `notes/facial-mocap-plan.md`; P1 to P4 need no outside data, P5 needs a face clip from the owner.
4. **Shoes**: tongue and padded collar missing; put the code-built trainers on the boy.
5. **Shoemaster tutorial** (YouTube k-VGL4jRPnw) not watched: YouTube blocks cloud machines.

## Environment notes
- Blender 5.3 as `bpy` needs Python 3.13. Assets: `tools/fetch_assets.sh`.
- Cloud sessions: 4 cores, no GPU, 30-minute limit on background jobs. Keep cloth runs small.
- YouTube is blocked from the cloud; the owner's analyzer or uploads are used instead.
