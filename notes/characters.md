# Human characters with outfits

Status values: **verified (test)** measured in `experiments/results_human.json` or
`results_rig.json` · **verified (render)** seen in run 002 · **unverified** not yet tested.

## How a clothed character is built

1. **One base mesh.** 19,158 vertices. The first 13,380 are the body. The rest are helper
   geometry: small cubes at every joint, and shells where skirts, tights and hair attach.
2. **Body shape is a weighted sum of targets.** A target is a list of per-vertex offsets.
   Sliders for gender, age, muscle, weight, height and ethnicity each split into two named
   extremes; a target's weight is the product of its parts. The default body uses 52 targets.
3. **Every outfit, hairstyle, eye and eyebrow is fitted, not modelled per character.** Each
   of its vertices is tied to three base-mesh vertices with weights and an offset. Evaluating
   that tie on a morphed body fits the item to that body.
4. **Each item lists the body vertices it covers.** Skin faces fully under an item are
   removed so they cannot poke through.
5. **The skeleton is placed from the joint cubes**, so it follows the body shape. Skin
   weights come from a file; clothes inherit weights through the same three-vertex ties.

## Claims

| # | Claim | Source | Status | Evidence |
|---|---|---|---|---|
| 1 | Item vertex = weighted base vertices + offset × per-axis scale, offsets in file axis order | MPFB format docs (mhclo.md) | verified (test) | H1: three items modelled on the unmorphed body reproduce to 0.01 mm; four other axis orders miss by 5 to 23 mm; file order fits best for 29 of 30 items |
| 2 | Target files hold offsets in MakeHuman axes (Y up) | MPFB format docs (target.md) | verified (test) | H2: default body 1.66 m, male 1.73, female 1.59, child 1.31; ordering as expected |
| 3 | Slider parts multiply into target weights | `macro.json` | verified (test) | H2, and three visibly different bodies in run 002 |
| 4 | `delete_verts` marks skin covered by an item | MPFB format docs | verified (test) | H3: casual suit covers 5,372 vertices and removes 2,688 of 13,378 body faces |
| 5 | An item's `.obj` holds only its faces and UVs; positions come from fitting | Own finding | verified (test) | Most `.obj` files sit 3 to 80 cm from the base mesh; they were modelled on other characters |
| 6 | Default and game-engine weights are complete and sum to 1 | weights files | verified (test) | R1: no unweighted body vertices; sums exactly 1.0 |
| 7 | The Mixamo-named skeleton's weights are complete but not normalised | weights file | verified (test) | R1: sums range 0.2 to 1.5 as shipped; the loader normalises them |
| 8 | Joint-cube placement keeps the skeleton symmetric on any body | MPFB format docs (rig.md) | verified (test) | R2: limb bones equal left to right on four bodies (one 1 mm tongue bone differs in the data) |
| 9 | Posing does not collapse joints | Own test | verified (test) | R3: body volume changes by at most 0.3% in three poses |
| 10 | Clothes follow the body when posed | Own test | verified (test) | R4: under 0.5% of outfit vertices sink 5 mm into visible skin in any pose |
| 11 | Rig files come in two layouts (flat, or wrapped in `"bones"`) | Own finding | verified (test) | Mixamo file loaded as 4 "bones" until the reader handled both |
| 12 | The height slider's top end gives a 2.37 m adult | Own finding | verified (test) | H2. Keep height between about 0.3 and 0.7 for ordinary people |
| 13 | Blender 5.3 can import FBX and BVH animation without add-on installs | API check | verified (API) | Operators present. Importing a real motion file is not yet tested |

## Ways to get clothed humans (survey; only the first row was tested here)

| Route | Cost and licence | What you get | Status |
|---|---|---|---|
| MakeHuman data, own loader (this repo) | Free. Data CC0 | Any body shape, 14 outfits, 6 shoes, 10 hairstyles, 23 skins, 3 skeletons | verified |
| MPFB add-on itself | Free. Code GPL-3, assets CC0 | Same data plus a UI, more asset packs, Rigify, expressions | unverified here: running its code was blocked in this session |
| Extra MakeHuman asset packs (shirts, pants, dresses, suits...) | Free. Licence varies per item (CC0 or CC-BY) | Hundreds more garments in the same format | unverified; same loader should read them |
| Mixamo | Free with an Adobe account | Auto-rigging and a large motion library; a few stock characters | unverified; needs sign-in, no automation interface |
| Paid generators (Human Generator, Character Creator) | Paid | Higher-fidelity skin, hair and clothes | not researched |
| Image-to-3D services | Paid per generation | One fused mesh from a picture; clothes not separable | not researched |
| Cloth simulation with sewing | Built into Blender | Garments draped from flat panels | not tested; solver exists (see architecture research) |

## Mistakes made during verification

- Assumed each item's `.obj` sat on the unmorphed base mesh. It does not; the first fitting
  test "failed" by up to 80 cm for that reason.
- Measured clothes against the clothed body, whose covered skin is removed. A skirt that
  was fine scored 20% "inside". Fixed by measuring against the full body and ignoring
  covered skin.
- First poses used fixed rotation angles. Arms crossed in front of the body, because the
  modelling pose already holds them partly down. Poses now say where each limb points.

## Open questions for the next pass

1. Motion: apply a mocap clip (CMU BVH, or a Mixamo FBX supplied by the owner) to a
   character and check it by rendering frames. Is rest-pose alignment needed?
2. Faces are neutral and identical in expression. The rig has face bones; expressions
   files exist in the MPFB data.
3. Hair is textured cards and can cover the face (see run 002). Check hair per head turn.
4. More garments: do the community asset packs load unchanged, and which are CC0?
5. Hands: fingers are never posed.
