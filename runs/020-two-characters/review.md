# Run 020: two characters in one scene (step 1 of the reference test)

Reference: "My Mom Cracked The Dinosaur" (owner-supplied, kept out of git; not available in
the cloud session that made this step). Owner: match the reference's shots and zooms; the
zooms can come later. To be continued in the owner's "FaceTracker Blender video analysis"
session, which has the clip.

Step 1 (`build.py`, `shot_two.png`, 480x270, 24 samples; build 82 s, render 8 s):
- `recipes/characters.py`: `curly_boy()` (run 013 route E outfit, run 012 hair, freckles,
  odd eyes, chest print, yellow shoes) and `mom()`; each adds all Faceunits and viseme
  shape keys right after it is built (human.BINDINGS keeps only the latest character).
- Both face each other across about 1.2 m in a plain room, one two-shot camera.

## Still wrong / next (needs the clip)
1. Mom is a PLACEHOLDER (young-looking, shorts outfit, long01 hair): match her body, hair,
   clothes and colours to the reference, measured like the boy's (run 012/013).
2. Set: plain floor and wall; build the reference's room.
3. Shots: list each shot from the clip (start/end time, framing, lens feel, camera move or
   zoom), then one camera per shot with keyframed zooms; render beside the reference with
   `tools/side_by_side.py`.
4. Dialogue: their lines through `tools/talk.sh`-style viseme keys per character
   (experiments/voice_drive.py drives one character; extend to two).
5. Lip work checkpoint is in runs/019-voice-lipsync/review.md.
