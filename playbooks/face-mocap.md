# Playbook: drive a character's face from a video

Evidence for every step: `notes/facial-mocap-plan.md` (claims F1 to F12). First done in
run 018 (14 Nov 2026).

## Once per machine
1. `tools/fetch_assets.sh` (Faceunits 01 and the MediaPipe model, both hash-pinned).
2. Tracker environment, kept apart from bpy:
   `uv venv -p 3.13 .venv-face && uv pip install -p .venv-face/bin/python mediapipe==1.2.3`
   and `apt-get update && apt-get install -y libegl1 libgles2` (MediaPipe links them even
   on CPU; without them: `OSError: libEGL.so.1`).
3. Character-specific calibration, about 3 minutes, redo when the face sliders change:
   `python experiments/face_response.py` (per-unit lip/eye response, also the P2 matrix),
   `python experiments/face_jaw_curve.py`, `python experiments/face_head_axes.py`,
   `python experiments/face_rest_offset.py` (rest pucker); gains: drive one segment, set
   gain = 1/amplitude for channels off by >15% (r >= 0.6), validate on another segment.

## Per clip
1. Clip: frontal face, about a third of the frame wide, even light, unmirrored (flip a
   selfie video with `ffmpeg -vf hflip`). Licence checked and logged in `sources/log.md`;
   the video stays out of git.
2. Frames at a fixed rate with ffmpeg, not OpenCV's reader (it skipped most frames of a
   VP9 webm: 437 of ~4000): `ffmpeg -ss START -t SECONDS -i clip -vf "fps=24,scale=960:-1" seg/%04d.png`.
3. Track: `.venv-face/bin/python -I tools/face_track.py seg seg.csv --fps 24` (~10 ms/frame).
   Check `found` is 1 on nearly every row.
4. Drive and render, then one lip feedback pass:
   `python experiments/face_drive.py seg.csv RUN/a --head`
   `python experiments/face_drive.py seg.csv RUN/b --head --refine RUN/a --source-frames seg`
   About 1.2 s per frame at 240x240, 16 samples, per pass.
5. Read `RUN/b/check.json`. Seen in run 018: head r 0.99, blinks 0.85 to 0.92, eye
   opening 0.83 to 0.87, smiles 0.80 to 0.82, lip gap 0.94 (fitted). Look at
   `side_by_side.png` and the video.

## Failure signatures
| Symptom | Cause | Fix |
|---|---|---|
| Mouth hardly opens while the source talks | Real speech lands in mouthUpperUp/LowerDown, which barely open our lips (F8, F7) | Jaw top-up (default in face_drive) and the `--refine` pass |
| Mouth closed at small openings | Lips sealed below jawOpen 0.15 (F9) | Top-up inverts the measured jaw curve |
| Everything 2 to 3 frames late | Forward-only smoothing | `face_anim.zero_phase` (default) |
| Head roll too large | Axis response measured on one bone but driven over two | Measure with the same split (`face_head_axes.py` does) |
| Left and right swapped | Mirrored selfie video | Flip before tracking (F5) |
| Brows dead | browInnerUp/OuterUp shapes too weak for the tracker (F7, F12) | `face_anim.BROW_GAIN` 2 (default; F14). Check by eye: the tracker cannot measure our brows (F13) |
| Pucker overshoot when the source relaxes | Our resting mouth reads as puckered (F15) | `face_anim.REST_OFFSET` mouthPucker -0.5 (default) |
| Smiles or eye channels off by >15% | Character-specific response | Gains in `experiments/results_face_gains.json` (default in face_drive); recalibrate on one segment, validate on another (F16) |
