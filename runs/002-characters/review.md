# Run 002 review: clothed characters

**Brief.** Create human characters with outfits.

**Built from.** `recipes/human.py` and `recipes/rig.py` (new this pass), plus the backdrop,
lighting, camera and colour recipes from run 001. No third-party code is executed; the
character data is MakeHuman's CC0 asset set.

## Result (Blender 5.3.0, 1280x720, 96 samples, 68 s on 4 CPU cores)

Three people in one frame, each built by one function call:

| | Body | Skin | Outfit | Hair | Pose | Height |
|---|---|---|---|---|---|---|
| Ana | young woman | young caucasian | T-shirt and jeans, brown shoes | long | wave | 1.55 m |
| Ben | heavier middle-aged man | middle-aged african | overalls, black shoes | short | relaxed | 1.94 m |
| Chen | older woman | old asian | blouse and skirt, grey shoes | bob | hands on hips | 1.43 m |

## What works

- Different body shapes from sliders; outfits refit to each body without gaps.
- Skin, eyes, eyebrows, lashes, teeth and hair are all present.
- Skeleton poses body and clothes together; measured checks all pass (see notes).
- Lighting from run 001 carried over with one change (key light 450 W for a wider group).

## Iterations it took

1. Pose by fixed angles: arms crossed in front of the body. Replaced with limb directions.
2. Hands-on-hips: forearms met at the stomach. Forearm direction corrected once.

## Still wrong

- Chen's hair falls across her face; the bob hairstyle sits forward on this head shape.
- Ben is 1.94 m and Chen 1.43 m. Both are legitimate slider results but the gap is large;
  the height slider is steeper than expected.
- Faces are expressionless and everyone looks straight ahead.
- Ana's jeans show pale marks at the ankles. Not yet determined whether that is the
  texture (distressed denim) or skin showing through.
- Hands are flat and open; fingers are not posed.
- Feet stay planted in the modelling stance, so poses read as stiff from the waist down.
- There was no reference image; "good" is still my judgment plus the measured checks.

## Next questions

Motion from mocap files, facial expression, hair checks, leg and finger posing.
Listed in `notes/characters.md`.
