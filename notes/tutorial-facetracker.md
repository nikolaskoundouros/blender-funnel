# Tutorial notes: KeenTools FaceTracker for Blender (facial mocap)

Source: vendor tutorial "Facial Mocap & 3D Facial Animation in One — FaceTracker for Blender"
(4 min 31 s), on the owner's computer. Analysed by another session on the owner's Mac
(272 frames, one per second, plus a Whisper small.en transcript), 13 Nov 2026. Trust D.
On screen: Blender 4.2.0, FaceTracker 2024.2.3 / 2024.3.0. Paid add-on (FaceBundle plans,
no prices shown). Every step is manual in the interface; nothing scripted or headless shown.

| Claim | Source | Status |
|---|---|---|
| Pipeline: face video -> 3D head track -> ARKit shape keys or a Rigify face rig | spoken 0:11 | unverified |
| Target needs ARKit-named shape keys (eyeBlinkLeft ... noseSneerRight), or a Rigify face rig | 0:22 to 0:33, shape key list on screen | names match MediaPipe's blendshape names (notes/facial-mocap-survey.md) |
| Head geometry is fitted by hand: snapshots on 3 frames, "Auto Align", then pins | 1:43 to 2:08 | unverified |
| Tracking mode "Camera" puts head motion on the camera, leaving only expressions on a static head | spoken 2:09 | unverified |
| Focal length set by hand (26 mm, sensor 36 x 24 mm) instead of estimated | 2:17 | unverified |
| Export: "ARKit" or "Rigify" tab, target object, "Convert"; also "Save as .csv" for use elsewhere | 3:02 to 3:42 | unverified |

What we take: the hand-off format (52 ARKit names, one curve per name per frame, CSV),
and the head-versus-expression split (head motion to the neck/head bones, the rest to
shape keys). What we do not take: the add-on itself (paid, manual, not scriptable).
Our route stays MediaPipe Face Landmarker (Apache-2.0) -> ARKit names -> MakeHuman face units.
