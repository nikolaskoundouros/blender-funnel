# Facial motion capture from video: survey (13 Nov 2026)

Question: can we drive a MakeHuman character's face, head and eyes from a phone video of a
real face, on this CPU-only Linux machine, with parts we are allowed to ship in a
GPL-compatible toolkit?

Status values: `verified (ran)` installed and executed here · `verified (licence)` licence
file or model card read · `verified (page)` page or file opened · `unverified` lead only.
Downloads and scripts used for this survey are in the scratchpad
(`mocap_survey/`), not in the repository.

## Recommendation

1. Track with **MediaPipe Face Landmarker** (`mediapipe==1.2.3`, Apache-2.0 code and model
   cards). It ran here on Python 3.13: 478 landmarks (incl. 10 iris points), 52 blendshape
   scores and a 4x4 head transform per frame, about 10 ms per frame on CPU.
2. Do **not** map onto our 34 expression units. MakeHuman publishes **Faceunits 01**, 52
   ARKit-named targets for our exact base mesh, **CC0** (read in the pack's metadata).
   MediaPipe scores then key shape keys one to one, by name.
3. Build two pieces: `tools/face_track.py` (video -> per-frame JSON in Live Link Face
   column order, run in its own venv) and `recipes/face_anim.py` (load the 52 targets as
   shape keys on body and fitted proxies, key them, drive `head`/`neck0x` and `eye.L/R` bones).
4. Verify by running the same tracker on small renders of our character and comparing
   curves with the source video (method in section 5).

## 1. Trackers that turn face video into per-frame data

MediaPipe test, exactly as run: `uv venv -p python3.13 venv313`, `uv pip install mediapipe`
installed `mediapipe==1.2.3` plus `opencv-contrib-python==5.0.0.93`, `numpy==2.5.4`,
`matplotlib` and `sounddevice` without error. The import worked, but creating a
`FaceLandmarker` failed with `OSError: libEGL.so.1: cannot open shared object file`:
`tasks/c/libmediapipe.so` links `libEGL.so.1` and `libGLESv2.so.2` even on the CPU path. I
did not install system packages; I extracted Ubuntu 24.04's `libegl1`, `libgles2`,
`libglvnd0` (1.7.0-1build1) debs into the scratchpad and set `LD_LIBRARY_PATH`. Then it ran.
On a real machine `apt install libegl1 libgles2` should do the same (unverified).

Python versions (PyPI JSON, verified): since 0.10.30 (Dec 2025) every release is a single
`py3-none-manylinux_2_28_x86_64` wheel, so any Python 3 works; `uv pip install --dry-run`
resolved 1.2.3 for 3.11 and 3.12 too. Up to 0.10.21 wheels stopped at cp312, which is why
older guides say "no 3.13". Version 1.x has dropped the legacy `mp.solutions` API
(`dir(mediapipe)` is only `Image`, `ImageFormat`, `tasks`), so old scripts written against
`mp.solutions.face_mesh` will not run on it.

Model (`face_landmarker.task`, 3.76 MB, from
`storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/`)
is a zip of face detector, landmark model, geometry metadata and `face_blendshapes.tflite`.
Output on MediaPipe's own test portrait (a broad smile): `mouthSmileLeft` 0.96, `Right`
0.93, `mouthUpperUp*` 0.76, `jawOpen` 0.12. The blendshape list has **52 entries, but the
first is `_neutral` and `tongueOut` is absent**, although the Blendshape V2 model card lists
`tongueOut` as number 52. So 51 usable ARKit channels.

| Tool | Outputs | Licence (as read) | Weights | CPU speed | Status |
|---|---|---|---|---|---|
| MediaPipe Face Landmarker, `google-ai-edge/mediapipe` | 478 3D landmarks incl. iris; 51 ARKit blendshapes + `_neutral`; 4x4 face transform | Code Apache-2.0 (repo LICENSE and wheel metadata); Face Mesh V2, Blendshape V2 and BlazeFace model cards each say "Licensed under Apache License, Version 2.0" | Direct download, no login | Measured here: 12.2 ms/frame IMAGE mode, 9.5 ms VIDEO mode, 820x1024 frame, 4 cores shared with a render | verified (ran) |
| MediaPipe on CG frames | Same | Same | Same | Faces found in 21 of 65 frames of `sources/reference/art-of-war-pilot/frames` (270x480; many frames show no face or goggles) | verified (ran) |
| OpenFace 2.x, `TadasBaltrusaitis/OpenFace` | 68 landmarks, head pose, gaze, FACS action units | "Academic or non-profit organization noncommercial research use only" (`OpenFace-license.txt`) | Yes | not checked | verified (licence); reject for shipping |
| OpenFace 3.0, `CMU-MultiComp-Lab/OpenFace-3.0` | RetinaFace + STAR landmarks (68/98), action units, emotion, gaze; `device='cpu'` supported | Same noncommercial agreement (LICENSE) | Hugging Face `nutPace/openface_weights` (no licence tag) | not stated | verified (licence); reject |
| 3DDFA_V2, `cleardusk/3DDFA_V2` | 3DMM shape/expression params, dense mesh, head pose | Code MIT, but `bfm/readme.md`: the BFM2009 face model "is only for academic use" | Yes, in repo | README: 1.35 ms/face regression (onnxruntime, 4 threads), face detection about 15 ms at 720p | verified (licence); learn from only |
| DECA `yfeng95/DECA`, EMOCA `radekd91/emoca` | FLAME shape, expression, jaw pose | MPI "non-commercial scientific research purposes" (both LICENSE files) | Yes, FLAME needs registration | GPU-oriented, not stated | verified (licence); reject |
| SMIRK, `georgeretsi/smirk` (CVPR 2024) | FLAME expression and jaw incl. asymmetric expressions | Code MIT; needs FLAME model with registration (README); FLAME's own terms not read | Google Drive | not stated | verified (licence of code); FLAME terms unverified |
| SPECTRE `filby89/spectre`; VHAP `ShenhanQian/VHAP` | FLAME tracking (SPECTRE lip-reading aware) | CC BY-NC-SA 4.0 | Yes | not stated | verified (licence); reject |
| py-feat, `cosanlab/py-feat` | Landmarks, action units, emotion, head pose | Code MIT; README says pretrained weights have separate terms with "permissions that remain unresolved" | Hugging Face | not checked | verified (licence); weights unclear |
| LibreFace, `ihp-lab/LibreFace` | Action units, expression | USC: "educational, research and non-profit purposes" | Yes | not checked | verified (licence); reject |
| OpenSeeFace, `emilianavt/OpenSeeFace` | 66 landmarks, head pose, gaze, simple features; not ARKit | BSD-2-Clause | Included (ONNX) | README: 30-60 fps on one core | verified (licence); backup tracker |
| NVIDIA Audio2Face-3D SDK | ARKit-style weights from **audio** | SDK MIT; models "nvidia-open-model-license" on Hugging Face; Audio2Emotion gated | Yes | Needs CUDA 12.8 + TensorRT (README) | verified (licence); not usable here |
| mocap4face, `facemoji/mocap4face` | ARKit-like weights | Alter SDK licence; README: repositories archived and support ended 29 Nov 2022 | No longer hosted | n/a | verified (page); reject |

## 2. Blender-side prior work

| Project | What it does | Licence / price | Status |
|---|---|---|---|
| **MPFB2** `FaceService` (`src/mpfb/services/faceservice.py`, local clone at commit 9de0707) | Loads `faceunits01` (52 ARKit), `visemes01` (22 Microsoft) and `visemes02` (15 Meta) target packs as zero-weight shape keys, interpolates them onto clothes/proxies, wires visemes to the "Lip Sync" add-on | Code GPL-3 (`LICENSE.md`); packs downloaded separately | verified (read code) |
| **Faceunits 01** pack (`files.makehumancommunity.org/functional/faceunits01.zip`, 258 KB, "contributed by Mika Suominen") | 52 `.target` files incl. `tongueOut`; touch body, tongue, lower teeth, eye and eyelash helpers | `packs/faceunits01.json`: every entry `"license": "CC0"`, description "Autogenerated ARKit faceunit" | verified (downloaded, read) |
| BlendArMocap, `cgtinker/BlendArMocap` | Runs MediaPipe inside Blender, drives Rigify rigs from pose/hand/face results | GPL-3.0; README: "I cannot actively maintain BlendArMocap anymore" | verified (licence) |
| Faceit (Superhive) | Generates ARKit shape keys; imports Live Link Face CSV, Face Cap txt, Audio2Face JSON; head and eye import; smoothing | Paid: $78 (1.8), $99 (2.3), $289 studio; listed "License GPL", Blender 3.0-5.2 | verified (page) |
| LiveLinkFace ARKit Receiver, `shun126/livelinkface_arkit_receiver` | Live UDP from the iPhone app onto matching shape keys; README: no head or eye rotation | GPL-3.0 | verified (licence) |
| Rokoko Studio Live, `Rokoko/rokoko-studio-live-blender` | Streams Rokoko Studio face data onto a face mesh | LGPL-3.0; needs Rokoko Studio and its capture app (pricing not checked) | verified (licence) |
| MeFaMo `JimWest/MeFaMo`, PyLiveLinkFace `JimWest/PyLiveLinkFace` | MediaPipe landmarks -> hand-computed blendshapes -> Unreal Live Link packets | MIT, both | verified (licence) |
| Face_Landmark_Link / DeadFace, `Qaanaaq/*` | MediaPipe video -> Live Link Face-style CSV, meant for Faceit | Apache-2.0 / MIT | verified (licence); code not read |
| FaceCap (Bannaflak), iFacialMocap, Live Link Face | iPhone ARKit apps; need a TrueDepth iPhone | Apps; terms not read | unverified |

## 3. Data formats

ARKit names (as returned by MediaPipe here, `verified (ran)`; same order as the model card
appendix): browDownLeft, browDownRight, browInnerUp, browOuterUpLeft, browOuterUpRight,
cheekPuff, cheekSquintLeft, cheekSquintRight, eyeBlinkLeft, eyeBlinkRight,
eyeLookDownLeft, eyeLookDownRight, eyeLookInLeft, eyeLookInRight, eyeLookOutLeft,
eyeLookOutRight, eyeLookUpLeft, eyeLookUpRight, eyeSquintLeft, eyeSquintRight, eyeWideLeft,
eyeWideRight, jawForward, jawLeft, jawOpen, jawRight, mouthClose, mouthDimpleLeft,
mouthDimpleRight, mouthFrownLeft, mouthFrownRight, mouthFunnel, mouthLeft,
mouthLowerDownLeft, mouthLowerDownRight, mouthPressLeft, mouthPressRight, mouthPucker,
mouthRight, mouthRollLower, mouthRollUpper, mouthShrugLower, mouthShrugUpper,
mouthSmileLeft, mouthSmileRight, mouthStretchLeft, mouthStretchRight, mouthUpperUpLeft,
mouthUpperUpRight, noseSneerLeft, noseSneerRight, tongueOut (52; MediaPipe omits the last).
Faceunits 01 file names match these exactly.

| Item | Finding | Status |
|---|---|---|
| Live Link Face CSV | Epic's page confirms each take saves a `.mov` reference and a `.csv` "that contains the raw animation data captured by ARKit". Channel order from PyLiveLinkFace's `FaceBlendShape` enum: the 52 shapes capitalised and grouped by region (EyeBlinkLeft, EyeLookDownLeft, ..., TongueOut), then HeadYaw, HeadPitch, HeadRoll, LeftEyeYaw, LeftEyePitch, LeftEyeRoll, RightEyeYaw, RightEyePitch, RightEyeRoll (61). Leading `Timecode, BlendShapeCount` columns are from memory | Channels verified (code read); header unverified |
| Faceit on Live Link Face | "records animation data for head rotation (no location)"; Face Cap records rotation and location | verified (page) |
| Free real sample with per-frame ARKit data | None confirmed. Leads: `alexdjulin/LiveLinkFace-CSV-Retarget-For-Motionbuilder` (MIT) has test `anim/` CSVs from the app, but I could not list the tree; `sanjuhs/audio_to_blendshapes_test` (MIT, numpy arrays, no provenance); BEAT v1 "facial52" (terms not read). BEAT2 (`haiyangliu0/BEAT2`, apache-2.0 tag) holds FLAME expressions, not ARKit | unverified |
| Our own sample | Not needed from outside: a phone video of the owner, run through MediaPipe here, gives the per-frame data | verified (pipeline ran on stills) |

## 4. Mapping 52 ARKit names to our 34 units (fallback only)

Two things measured on geometry (script `mocap_survey/scripts/analyze_targets.py`; no render):
each Faceunits 01 target compared with our units by cosine similarity of the displacement
field, and fitted as a non-negative combination of all 34 units (R² of that fit). Findings:
**all 15 mouth units are symmetric** (displacement centroid x = 0.00), so left/right mouth
shapes cannot be told apart; and the best non-negative fit explains less than half of most
ARKit shapes (median R² 0.26, 42 of 52 below 0.5; eyeLookIn/Out and tongueOut 0.00). This is why the
recommendation uses Faceunits 01 instead. Symmetric units take `0.5 * (L + R)`.

All rows `unverified`: weights are guesses from names plus the cosine, never rendered.

| ARKit | Our unit(s) x weight | cos | fit R² |
|---|---|---|---|
| browDownLeft / Right | eyebrows-left-down / eyebrows-right-down x1.0 | 0.37 | 0.16 |
| browInnerUp | eyebrows-left-inner-up x1.0 + eyebrows-right-inner-up x1.0 | 0.46 | 0.58 |
| browOuterUpLeft / Right | eyebrows-left-extern-up / right x1.0 | 0.63 | 0.46 |
| cheekPuff | no clean equivalent (mouth-pursing x0.5 is the geometric nearest, different meaning) | 0.72 | 0.52 |
| cheekSquintLeft / Right | no equivalent | 0.07 | 0.02 |
| eyeBlinkLeft / Right | eye-left-closure / eye-right-closure x1.0 | 0.69 | 0.48 |
| eyeLookDown/In/Out/Up (8) | no equivalent: rotate `eye.L` / `eye.R` bones | ≤0.62 | 0.00-0.39 |
| eyeSquintLeft / Right | eye-left-slit / eye-right-slit x1.0 | 0.29 | 0.17 |
| eyeWideLeft / Right | eye-left-opened-up / right x1.0 | 0.81 | 0.66 |
| jawForward, jawLeft, jawRight | no equivalent: `jaw` bone | ≤0.29 | ≤0.12 |
| jawOpen | mouth-open x1.0 | 0.83 | 0.68 |
| mouthClose | no equivalent (approximate: reduce mouth-open by mouthClose) | 0.60 | 0.57 |
| mouthDimpleLeft / Right | mouth-retraction x0.5 (symmetric) | 0.53 | 0.33 |
| mouthFrownLeft / Right | mouth-depression x0.5 (symmetric) | 0.43 | 0.26 |
| mouthFunnel | mouth-protusion x1.0 + mouth-pursing x0.3 | 0.59 | 0.55 |
| mouthLeft / Right | no equivalent | 0.22 | 0.06 |
| mouthLowerDownLeft / Right | mouth-depression-retraction x0.5 (symmetric) | 0.36 | 0.20 |
| mouthPressLeft / Right | mouth-compression x0.5 (symmetric) | 0.40 | 0.25 |
| mouthPucker | mouth-pursing x1.0 | 0.90 | 0.81 |
| mouthRollLower, mouthRollUpper | no equivalent | ≤0.37 | ≤0.26 |
| mouthShrugLower | mouth-eversion x1.0 | 0.68 | 0.52 |
| mouthShrugUpper | mouth-elevation x1.0 | 0.74 | 0.72 |
| mouthSmileLeft / Right | mouth-corner-puller x0.5 (symmetric) | 0.58 | 0.37 |
| mouthStretchLeft / Right | mouth-retraction x0.5 + neck-platysma x0.25 | 0.34 / 0.43 | 0.25 |
| mouthUpperUpLeft / Right | mouth-elevation x0.5 + nose-left/right-elevation x0.3 | 0.56 | 0.46 |
| noseSneerLeft / Right | nose-left/right-elevation x1.0 + nose-left/right-dilatation x0.5 | 0.62 | 0.49 |
| tongueOut | no equivalent: tongue bones or Faceunits 01 | 0.00 | 0.00 |

Unused units: mouth-parling, mouth-part-later, mouth-upward-retraction, nose-compression,
nose-depression, eyebrows-left/right-up.

## 5. Pipeline, what to build, risks, verification

Pipeline: phone video -> `tools/face_track.py` (MediaPipe VIDEO mode, timestamps from the
container, one JSON/CSV row per frame: 51 scores, head yaw/pitch/roll/translation from the
transform, eye yaw/pitch from the eyeLook pairs or iris points) -> neutral calibration
(subtract each channel's value on a chosen neutral frame, per-channel gain) and smoothing
(One-Euro or similar) -> `recipes/face_anim.py` in bpy: add the 52 Faceunits targets as
shape keys, key them per frame, key `head`/`neck01-03` rotations and `eye.L/R`.

To build: (a) shape keys. `morphed_base(expression=...)` bakes a static face today; motion
needs shape keys on the body **and** on the fitted eyebrows, eyelashes, teeth and tongue,
by fitting each proxy to base and base+target and storing the difference (what MPFB's
`interpolate_targets` does; assumes the fit is close to linear, unverified). (b) A loader for
the uncompressed `.target` files (5 to 51 KB each). (c) Tracker venv kept separate from bpy's environment.

Risks:
- **Lip sync**: Blendshape V2 card reports mean absolute deviation about 0.20 on a 0-1
  scale; rolls, press and mouthClose are subtle; expect jitter. Whisper word times from the
  owner's analyzer can check timing.
- **Jaw**: Faceunits jawOpen moves body, lower teeth and tongue helpers as a morph; teeth
  and tongue proxies must get matching keys or teeth will float. Alternative: `jaw` bone.
- **Eyes**: eyeLook targets move the eye helper; our eyes are a separate fitted object.
  Bones are simpler. Blinks must also close the eyelash proxies.
- **Teeth/tongue**: no tongueOut from MediaPipe.
- **Head pose**: the transform is camera-relative; a handheld phone mixes camera and head
  motion. Use a tripod or cancel with background tracking.
- **Framing**: the card warns of degradation beyond 80° yaw or under 50% face visible.

Verification by measurement: (1) response matrix: set each Faceunits target to 1.0 alone,
render 320x180 close-ups, run MediaPipe on them; the matching channel should be the highest.
(2) round trip: run MediaPipe on renders of the animated character and correlate each
channel with the source video's curve (Pearson r, lag in frames), plus a landmark-only check
(inner-lip gap divided by face width) that does not depend on the blendshape model.
(3) Head angles: compare the transform from source and render, degrees per frame.

## Dead ends and things I could not check

- `api.github.com` and `github.com` pages returned 403; licences came from
  `raw.githubusercontent.com`, so repository trees (e.g. the alexdjulin sample CSVs) could not be listed.
- WebFetch could not resolve superhivemarket.com or blenderartists.org; plain `curl` could.
- Exact Live Link Face CSV header line not found in an Epic source.
- No render was made; mapping, Faceunits quality on our characters and proxy transfer are untested.
- OpenFace 3, 3DDFA_V2, SMIRK, OpenSeeFace not installed or run; speeds are from READMEs. FLAME's own terms not read.
- Rokoko, FaceCap and iFacialMocap pricing not checked. visemes01/02 pack licences not read.
- MediaPipe was tested on two stills sources, not on a real face video.
