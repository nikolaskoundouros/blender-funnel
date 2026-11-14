# Playbook: make the character say a voiceover

Evidence: `notes/voice-lipsync.md` (V1 to V8). First done in run 019 (14 Nov 2026).

## Setup (once)
Everything from `playbooks/face-mocap.md` "Once per machine", plus
`uv pip install -p .venv-face/bin/python faster-whisper==1.2.1`. `tools/fetch_assets.sh`
brings Visemes 01 and CMUdict. The Whisper model (base.en, MIT, 140 MB) downloads on first use.

## Per voiceover
1. Audio file (mp3/wav, e.g. from ElevenLabs), English. Keep the script text: compare it
   with the transcript in `voice.json`; fix misheard words there if needed (step 4).
2. `tools/talk.sh voiceover.mp3 runs/NNN-name` for a 240x240 check (about 1.2 s per
   frame on 4 cores: 30 s of speech takes about 15 minutes), `... final` for 720x720 at 64
   samples (several times slower: split long audio or use a GPU machine).
3. Watch `talk.mp4`. Check `voice.json`: every word should have phonemes (numbers are
   spelled out; unusual names fall back to letter sounds).
4. If a word is misheard, pass the script: `tools/talk.sh voiceover.mp3 OUT check script.txt`
   (it steers Whisper's spelling; timing still comes from the audio).

## Settings that worked (run 019 D_final, held out)
Visemes: bumps widened 50% each side, visibility weights (h 0.2, d/t/n and k/g 0.3, l 0.4,
r and s/z 0.5, y and th 0.6, sh 0.8), blended to sum at most 1, Gaussian smoothing 40 ms
(p/b/m keep 80% of their peak), loudness 0.4 + 0.6 x loudness, tanh soft limit gain 3.5.
Talking jaw 0.22 while speaking, yielding to p/b/m, f/v and to open vowels. Idle blinks
every 2 to 5 s; head motion borrowed from run 018's tracked speaker; tongue on.

## Failure signatures
| Symptom | Cause | Fix |
|---|---|---|
| Mouth half as open as a real speaker | Viseme shapes are small on our face (V5) | gain 1.9 |
| Mouth snaps shut between sounds | Visemes alone (V6) | talking jaw (default) |
| Lips do not meet on p/b/m | Talking jaw unconditional | it yields to p/b/m, f/v (default) |
| Mouth freezes on numbers | Whisper writes digits | `number_words` (default) |
| Mouth too quick, flaps every frame | One full shape per phoneme (V9) | visibility weights, blending, 40 ms smoothing (default) |
| Grimace or huge "O" | Shapes stacked or pushed past 1; jaw stacked on vowels (V9, V11) | blend + tanh soft limit; jaw yields to vowels (default) |
| Black hole in the open mouth | No tongue | `build_human(tongue=True)` (default) |
| Calmer than a lively speaker | Soft limit keeps peaks natural (V12) | raise `--gain` toward 4.5 if wanted; watch for distortion |
