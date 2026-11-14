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

## Still wrong / next
- Vowels about 30% too wide (try gain 1.5 on a fourth segment).
- Frame-level correlation with the real lip gap is near zero on these clips (V4), so timing
  is judged by phoneme-centre contrast and by eye. ElevenLabs' own timestamps could replace
  Whisper's for its voices.
- No tongue (th, l), no emotion: face expression is neutral apart from blinks and head.
