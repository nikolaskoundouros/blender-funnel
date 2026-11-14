# Lip sync from a voiceover (14 Nov 2026)

Question (owner): if we get an ElevenLabs voiceover, can the character talk it?
Route: audio -> words with times (faster-whisper) -> phonemes (CMUdict) -> visemes
(Microsoft IDs, MakeHuman Visemes 01 shapes, CC0) -> shape keys. Code: `tools/voice_track.py`,
`experiments/voice_drive.py`, `recipes/face_anim.VISEMES`. Sources: `sources/log.md`.

## Prior work considered
| Item | Decision | Why |
|---|---|---|
| ElevenLabs timestamps (TTS "with timestamps", forced alignment API) | Optional later | Gives exact character timing for its own voices, but costs credits; local Whisper timing proved good enough (claim V3) |
| Rhubarb Lip Sync (MIT) | Learn from | Audio -> 6-9 cartoon mouth shapes; we have 21 realistic visemes. Repository code is not run here |
| Montreal Forced Aligner (MIT) | Reject for now | Phoneme-level alignment, but a heavy install; word timing + proportional split worked |
| NVIDIA Audio2Face-3D | Reject | Needs CUDA (survey 13 Nov) |
| Wav2Lip, SadTalker, FaceFormer | Reject | 2D output or non-commercial training data |

## Claims
| # | Claim | Source | Status | Evidence |
|---|---|---|---|---|
| V1 | Visemes 01 is CC0 and its 22 targets apply to our base mesh like Faceunits | Pack JSON, host index (functional packs CC0) | verified (licence, test) | keyed through `face_anim.add_faceunit_keys(units=VISEMES)`, renders in `runs/019-voice-lipsync` |
| V2 | faster-whisper base.en on CPU transcribes and word-times 15 s of speech in about 10 s; numbers come out as digits ("4 ,000") | Own run | verified (test) | `voice_track.py` spells numbers (`number_words`) |
| V3 | Word times + CMUdict phonemes split by length (vowels double) land on the real mouth: at p/b/m centres the real speaker's lips are closer than at open vowels | Own measurement, Mckensie clip | verified (test) | AUC 0.72 (10-25 s), 0.67 (40-55 s): `experiments/voice_contrast.py` |
| V4 | Frame-by-frame correlation with a real speaker's lip gap cannot judge lip sync on these clips | Own measurement | verified (test) | The speaker's own loudness correlates with her lip gap at r 0.30 / 0.07; her mouth also moves with smiles |
| V5 | Our viseme-driven mouth opens about half as much as a real speaker's at gain 1 (vowel centres 0.045 vs 0.086 face widths); gain 1.9 matches (0.067 vs 0.054 on a held-out segment) with open/closed separation AUC 0.97 | Own experiment | verified (test) | `runs/019-voice-lipsync/try1`, `B_gain19` |
| V6 | Between sounds visemes alone close the mouth (median lip gap 0.044 vs 0.079 real). A talking baseline (jawOpen 0.22 while speech is active) that yields to p/b/m and f/v fixes it | Own experiment, held-out segment 25-40 s | verified (test) | `C_final`: median 0.093 vs real 0.083, 95th percentile 0.142 vs 0.136; p/b/m centres 0.043 vs real 0.056; separation AUC 0.995. Without the yield, p/b/m stayed open (0.075, `C_try1`) |
| V7 | At gain 1.9 with the talking baseline, open vowels are about 30% wider than the real speaker's (0.124 vs 0.091) | Own experiment | verified (test) | `C_final`; next: gain about 1.5, checked on a fourth segment |
| V8 | A still head looks robotic; borrowing a tracked real speaker's head motion (`--head-from`) works with lip sync unchanged | Own experiment | verified (visual) | `C_final/side_by_side.mp4` |
