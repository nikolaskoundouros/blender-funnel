#!/usr/bin/env bash
# Download the public-domain (CC0) data the character recipes read.
#   1. Base mesh, body-shape targets, skeletons and weights: data files from the MPFB
#      repository at a pinned commit. Only data is copied; none of its code is used.
#   2. Skins, hair, eyes and clothes: the MakeHuman system asset pack (about 280 MB).
#   3. Four dance clips from the CMU motion-capture database (BVH conversion by B. Hahne;
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

if [ ! -f "$TARGET/motion/cmu/05_02.bvh" ]; then
  git clone --quiet --filter=blob:none --no-checkout https://github.com/una-dinosauria/cmu-mocap.git "$WORK/cmu"
  git -C "$WORK/cmu" sparse-checkout set --no-cone \
    /data/005/05_02.bvh /data/015/15_04.bvh /data/055/55_02.bvh /data/060/60_01.bvh
  git -C "$WORK/cmu" checkout --quiet "$CMU_COMMIT"
  mkdir -p "$TARGET/motion/cmu"
  cp "$WORK"/cmu/data/*/*.bvh "$TARGET/motion/cmu/"
fi

echo "assets ready in $TARGET"
du -sh "$TARGET/mpfb_data" "$TARGET/system" "$TARGET/motion"
