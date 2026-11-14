#!/usr/bin/env bash
# Make the curly-haired boy say a voiceover (playbooks/voiceover.md).
# Usage: tools/talk.sh VOICEOVER.(mp3|wav) OUT_DIR [check|final] [SCRIPT.txt]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AUDIO="$1"; OUT="$2"; QUALITY="${3:-check}"; SCRIPT="${4:-}"
mkdir -p "$OUT"
"$ROOT/.venv-face/bin/python" -I "$ROOT/tools/voice_track.py" "$AUDIO" "$OUT/voice.csv" --fps 24 ${SCRIPT:+--script "$SCRIPT"}
"$ROOT/.venv/bin/python" "$ROOT/experiments/voice_drive.py" "$OUT/voice.csv" "$AUDIO" "$OUT" \
  --gain 3.5 --soft --blinks --head-from "$ROOT/runs/018-face-mocap/source_track.csv" --quality "$QUALITY"
echo "video with sound: $OUT/talk.mp4   words and timings: $OUT/voice.json"
