# Motion: making characters move from motion-capture clips

Status values: **verified (test)** measured in `experiments/results_motion.json` ·
**verified (render)** seen in run 003 · **unverified** not yet tested.

## How a clip gets onto a character

1. **A BVH clip is a skeleton plus numbers.** The file lists joints with their offset from
   the parent, then one row per frame holding each joint's rotation (and the hips' position).
2. **Rotations cannot be copied across.** They are measured from the clip skeleton's rest
   pose (arms straight out). Our characters rest with arms angled down, so the same numbers
   would give a different pose.
3. **Transfer by world orientation instead.** Per bone and frame: how far the clip's joint
   has turned from its rest, applied to the character bone after that bone has been
   re-aimed to match the clip's rest direction. Then convert into Blender's bone-local
   rotation.
4. **Hips path is scaled by leg length** so steps fit the character's size, then lowered or
   raised so the feet meet the floor.
5. **Matching names make this easy.** The CMU clips in their "MotionBuilder-friendly"
   conversion and the `cmu_mb` skeleton in the MakeHuman data share 31 joint names.

## Claims

| # | Claim | Source | Status | Evidence |
|---|---|---|---|---|
| 1 | BVH rotations compose in the order the channels are listed | BVH format; own reader | verified (test) | M5: our reader and Blender's bundled BVH importer agree on limb directions to 0.0° (upper spine 0.8°, a branch point) |
| 2 | Transferring world orientation reproduces the clip's limb directions on a differently-posed skeleton | Own method | verified (test) | M1: 11 limbs, 10 frames, 0.0° error on the character |
| 3 | Scaling the hips path by leg-length ratio and dropping to the floor keeps feet grounded | Own method | verified (test) | M2: lower toe joint between 1.8 and 12.7 cm over 224 frames; never more than 3 cm under its rest height |
| 4 | Clothes survive dancing | Own test | verified (test) | M3: at most 0.55% of outfit vertices sink 5 mm into visible skin on any sampled frame |
| 5 | The 31-bone skeleton does not collapse joints in dance poses | Own test | verified (test) | M4: body volume stays between +1.1% and +3.6% of rest |
| 6 | The `cmu_mb` skeleton's weights are complete and normalised | weights file | verified (test) | R1 in `results_rig.json` |
| 7 | Many clip joints sit at zero distance from their parent, and some branch | Own finding | verified (test) | Hip sockets, neck on upper spine, finger base on hand. A bone's direction must be taken from the nearest descendant with a real offset, matched to the character's bone |
| 8 | CMU clips are 120 frames per second and start with an added T-pose frame | Dataset readme | verified (API) | Frame time 0.00833 s; reader skips the first 5 frames and keeps every 5th for 24 fps |
| 9 | The CMU data is free for research and commercial use | Dataset readme | read, not a legal review | Quoted usage paragraph in READMEFIRST.txt |
| 10 | Feet do not slide while planted | — | unverified | Not measured. No foot locking is applied |
| 11 | Mixamo FBX clips transfer the same way onto the `mixamo` skeleton | — | unverified | Skeleton loads; no Mixamo file has been tested |

## Mistakes made on the way

- Took each joint's bone direction from its first child. Four joints (hips, upper spine,
  both hands) have a first child at zero distance, so they had no direction at all.
- The first self-check (M1) could only show my steps agreed with each other. A wrong
  reading of the file would have passed it. Added M5, a comparison with Blender's own
  importer, as an independent reading.
- First camera sat 7 m back; the dancer filled a third of the frame.

## Open questions for the next pass

1. Foot sliding: measure it, and lock planted feet if it is visible.
2. Fingers and face do not move; the clips carry no data for them.
3. Hair is rigid: the ponytail does not swing. Cloth and hair simulation exist in Blender
   but are frame-sequential (see architecture research).
4. Longer clips and blending between clips.
5. A Mixamo FBX on the `mixamo` skeleton, when the owner supplies files.
