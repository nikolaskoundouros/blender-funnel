# Run 018: the curly-haired boy's face driven from a real face video

Source: Wikitongues clip (CC BY-SA 4.0, `SOURCE.md`), 40-55 s, 24 fps. Procedure:
`playbooks/face-mocap.md`. Each `try*/check.json` compares the source with our render,
both tracked by `tools/face_track.py`; landmark measures (lip gap, eye opening) do not
depend on the blendshape model.

| Try | Change | Lip gap r / amp | Eyes r | Notes |
|---|---|---|---|---|
| 1 | Plain mapping, forward smoothing | 0.62 / 0.49 | 0.78 / 0.75 | 2-3 frames late; mouth barely opens |
| 2 | Zero-lag smoothing, linear jaw top-up | 0.71 / 0.40 | 0.84 / 0.83 | Lag gone |
| 3 | Top-up through measured jaw curve | 0.69 / 0.36 | 0.84 / 0.83 | Lips sealed below jawOpen 0.15 |
| 4 | One lip feedback pass | 0.90 / 0.70 | 0.82 / 0.84 | Blinks 0.88 / 0.85, smiles 0.81 |
| 5 | + head on neck/head bones | 0.82 / 0.76 | 0.89 / 0.83 | Head r 0.99, roll 154% |
| 6 | Head axes measured with the same split | 0.94 / 0.69 | 0.87 / 0.83 | Head amplitude 1.07 / 1.01 / 1.17 |
| full | 15 s, two passes | 0.92 / 0.88 | 0.91 / 0.92 | Blinks 0.95 / 0.94, smiles 0.85 / 0.84; `full/side_by_side.mp4` |

## Still wrong
- Brows do not move (browInnerUp amplitude 1%): the Faceunits brow shapes are small and
  the tracker hardly sees them on our face (P2). Try a gain, or stronger brow targets.
- mouthPucker overshoots (2.9x); mouthUpperUp/LowerDown read weakly back (0.2-0.3).
- Lip gap is fitted by the feedback pass, so it is not an independent check.
- 240x240 close-ups only; bald head, no hair, no teeth/tongue check.

## Next questions
1. Brow gain from the response matrix, then re-run.
2. Per-unit gains for all channels from the response matrix (pucker down, smile R up).
3. Eye gaze: eyeLook units vs eye bones, measured with the iris landmarks.
