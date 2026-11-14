# Run 019: lip sync from audio

Test speech: "WIKITONGUES- Mckensie speaking English" (CC BY-SA 4.0, Wikimedia Commons),
whose video gives the real mouth as ground truth. Segments: A 10-25 s (tuning), B 40-55 s
and C 25-40 s (held out). Measures in `notes/voice-lipsync.md`; `experiments/voice_contrast.py`
compares mouth opening at p/b/m centres and at open-vowel centres.

| Run | Segment | Change | p/b/m | open vowels | AUC | median lip gap (real) |
|---|---|---|---|---|---|---|
| try1 | A | visemes, gain 1 | 0.019 | 0.045 (real 0.086) | 0.91 (real 0.72) | |
| B_gain19 | B | gain 1.9 | 0.026 | 0.067 (real 0.054) | 0.97 (real 0.67) | 0.044 (0.079) |
| C_try1 | C | + talking jaw | 0.075 (real 0.056) | 0.123 (real 0.091) | 0.997 (real 0.70) | 0.096 (0.083) |
| C_final | C | jaw yields to p/b/m, f/v; borrowed head motion | 0.043 | 0.124 | 0.995 | 0.093 (0.083) |

`C_final/side_by_side.mp4`: real speaker and ours with the audio.

## Owner feedback: "really quick and looks a bit distorted"

| Run | Segment | Change | jitter >6 Hz lip / width (real) | range lip / width (real) |
|---|---|---|---|---|
| C_final | C | as above | 13% / 8% (2% / 1%) | 0.090 / 0.071 (0.116 / 0.064) |
| A_blend | A | visibility, blend, 40 ms smoothing, gain 1 | 2.1% / 1.4% (2% / 1.7%) | 0.048 / 0.018 (0.126 / 0.075) |
| A_g3 | A | plain gain 3 | 3.8% / 1.2% | 0.117 / 0.065: right numbers, distorted vowels |
| A_soft_fill | A | tanh gain 3.5, jaw yields to vowels | 2.4% / 0.6% | 0.059 / 0.057 |
| D_final | D (held out) | + tongue, head, blinks | 1.8% / 1.2% (1.2% / 1.1%) | 0.064 / 0.053 (0.136 / 0.119) |

`before_after_frames.png`: real, before, after; `D_final/side_by_side.mp4` with sound.

## Still wrong / next
- Now about half the real speaker's range on a lively segment: a gain between 3.5 and 4.5 is the next test.
- Teeth render grey inside the mouth (lighting; texture is white/pink).
- Frame-level correlation with the real lip gap is near zero on these clips (V4), so timing
  is judged by phoneme-centre contrast and by eye. ElevenLabs' own timestamps could replace
  Whisper's for its voices.
- No tongue (th, l), no emotion: face expression is neutral apart from blinks and head.
