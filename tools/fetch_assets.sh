#!/usr/bin/env bash
# Download the public-domain (CC0) data the character recipes read.
#   1. Base mesh, body-shape targets, skeletons and weights: data files from the MPFB
#      repository at a pinned commit. Only data is copied; none of its code is used.
#   2. Skins, hair, eyes and clothes: the MakeHuman system asset pack (about 280 MB).
#   3. Faceunits 01: 52 ARKit-named face targets for the same base mesh (CC0, contributed
#      by Mika Suominen; host index: "Functional asset packs ... shared under CC0").
#   4. Four dance clips from the CMU motion-capture database (BVH conversion by B. Hahne;
#      free for research and commercial use).
# Usage: tools/fetch_assets.sh [target_dir]     (default: ./assets)
set -euo pipefail

TARGET="${1:-$(cd "$(dirname "$0")/.." && pwd)/assets}"
MPFB_COMMIT="9de0707fdc88438d7c53a1a2ac7937d9221e2431"
CMU_COMMIT="09a07f54f3bbb58797325f009282d0b2048a2871"
PACK_URL="https://files.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$TARGET"

if [ ! -f "$TARGET/mpfb_data/3dobjs/base.obj" ]; then
  git clone --quiet --filter=blob:none --no-checkout https://github.com/makehumancommunity/mpfb2.git "$WORK/mpfb2"
  git -C "$WORK/mpfb2" sparse-checkout set --no-cone \
    src/mpfb/data/3dobjs src/mpfb/data/mesh_metadata src/mpfb/data/rigs/standard \
    src/mpfb/data/targets/macrodetails src/mpfb/data/targets/breast src/mpfb/data/targets/expression
  git -C "$WORK/mpfb2" checkout --quiet "$MPFB_COMMIT"
  mkdir -p "$TARGET/mpfb_data/targets" "$TARGET/mpfb_data/rigs"
  D="$WORK/mpfb2/src/mpfb/data"
  cp -r "$D/3dobjs" "$D/mesh_metadata" "$TARGET/mpfb_data/"
  cp -r "$D/targets/macrodetails" "$D/targets/breast" "$D/targets/expression" "$TARGET/mpfb_data/targets/"
  cp -r "$D/rigs/standard" "$TARGET/mpfb_data/rigs/"
fi

if [ ! -d "$TARGET/system/clothes" ]; then
  curl -sS -L --retry 3 -o "$WORK/pack.zip" "$PACK_URL"
  mkdir -p "$TARGET/system"
  python3 -I -c "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$WORK/pack.zip" "$TARGET/system"
fi

FACEUNITS_URL="https://files.makehumancommunity.org/functional/faceunits01.zip"
FACEUNITS_SHA256="d113107bd7eb59f3af4df6fc0ec29bfcc593f496d0b336aec14f086a80ce7146"
if [ ! -f "$TARGET/faceunits01/targets/faceunits/jawOpen.target" ]; then
  curl -sS -L --retry 3 -o "$WORK/faceunits01.zip" "$FACEUNITS_URL"
  echo "$FACEUNITS_SHA256  $WORK/faceunits01.zip" | sha256sum -c --quiet
  mkdir -p "$TARGET/faceunits01"
  python3 -I -c "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$WORK/faceunits01.zip" "$TARGET/faceunits01"
fi

# Visemes 01: 22 Microsoft-style viseme targets for the base mesh (CC0, same pack page as
# Faceunits 01), and CMUdict (BSD-style licence) for English pronunciations: voice lip sync.
VISEMES_URL="https://files.makehumancommunity.org/functional/visemes01.zip"
VISEMES_SHA256="f61f4f36bb4fe43486efa2a644eea9d6760e510bde10eecc97a4ddf28424e4d3"
if [ ! -f "$TARGET/visemes01/targets/visemes/p_b_m_21.target" ]; then
  curl -sS -L --retry 3 -o "$WORK/visemes01.zip" "$VISEMES_URL"
  echo "$VISEMES_SHA256  $WORK/visemes01.zip" | sha256sum -c --quiet
  mkdir -p "$TARGET/visemes01"
  python3 -I -c "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$WORK/visemes01.zip" "$TARGET/visemes01"
fi
CMUDICT_COMMIT="74790861f652b15e4ac49015a90074ad62a27690"
CMUDICT_SHA256="81917843c7f44ce2b094ac63873c2c7a4cf802040792c455ba3ca406891c3d22"
if [ ! -f "$TARGET/cmudict/cmudict.dict" ]; then
  mkdir -p "$TARGET/cmudict"
  curl -sS -L --retry 3 -o "$WORK/cmudict.dict" "https://raw.githubusercontent.com/cmusphinx/cmudict/$CMUDICT_COMMIT/cmudict.dict"
  echo "$CMUDICT_SHA256  $WORK/cmudict.dict" | sha256sum -c --quiet
  curl -sS -L --retry 3 -o "$TARGET/cmudict/LICENSE" "https://raw.githubusercontent.com/cmusphinx/cmudict/$CMUDICT_COMMIT/LICENSE"
  cp "$WORK/cmudict.dict" "$TARGET/cmudict/"
fi

# MediaPipe Face Landmarker model (Apache-2.0 model card), for tools/face_track.py.
MP_URL="https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
MP_SHA256="64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"
if [ ! -f "$TARGET/models/face_landmarker.task" ]; then
  mkdir -p "$TARGET/models"
  curl -sS -L --retry 3 -o "$WORK/face_landmarker.task" "$MP_URL"
  echo "$MP_SHA256  $WORK/face_landmarker.task" | sha256sum -c --quiet
  cp "$WORK/face_landmarker.task" "$TARGET/models/"
fi

if [ ! -f "$TARGET/motion/cmu/05_02.bvh" ]; then
  git clone --quiet --filter=blob:none --no-checkout https://github.com/una-dinosauria/cmu-mocap.git "$WORK/cmu"
  git -C "$WORK/cmu" sparse-checkout set --no-cone \
    /data/005/05_02.bvh /data/015/15_04.bvh /data/055/55_02.bvh /data/060/60_01.bvh
  git -C "$WORK/cmu" checkout --quiet "$CMU_COMMIT"
  mkdir -p "$TARGET/motion/cmu"
  cp "$WORK"/cmu/data/*/*.bvh "$TARGET/motion/cmu/"
fi

echo "assets ready in $TARGET"
du -sh "$TARGET/mpfb_data" "$TARGET/system" "$TARGET/faceunits01" "$TARGET/motion"
