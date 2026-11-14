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
3. **Facial mocap: working end to end (runs 017-019).** Faceunits 01 and Visemes 01 are
   CC0; `recipes/face_anim.py` keys them on body and fitted items. Video: `tools/face_track.py`
   (MediaPipe), `playbooks/face-mocap.md`; brows (gain 2) and pucker (rest offset) fixed and
   validated on a held-out segment. Voice: `tools/talk.sh voiceover.mp3 runs/NNN` (Whisper
   word times, CMUdict, visemes), `playbooks/voiceover.md`. Open: vowels ~30% wide, no tongue,
   no emotion from audio, check renders are 240x240 (final 720x720 is slow on CPU).
4. **Shoes**: tongue and padded collar missing; put the code-built trainers on the boy.
5. **Shoemaster tutorial** (YouTube k-VGL4jRPnw) not watched: YouTube blocks cloud machines.

## In progress: two-character reference test (run 020)
Owner's "real test": the boy and his mom from "My Mom Cracked The Dinosaur" in one scene
with the reference's shots and zooms. Step 1 done (both built from `recipes/characters.py`,
two-shot). Next steps and what needs the clip: `runs/020-two-characters/review.md`.
Continue in the session that has the clip ("FaceTracker Blender video analysis").

## Environment notes
- Blender 5.3 as `bpy` needs Python 3.13. Assets: `tools/fetch_assets.sh`.
- Cloud sessions: 4 cores, no GPU, 30-minute limit on background jobs. Keep cloth runs small.
- YouTube is blocked from the cloud; the owner's analyzer or uploads are used instead.
