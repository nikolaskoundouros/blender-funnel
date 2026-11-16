"""Build the zoom preset table from the clip analyzer's reading of a reference clip.

A "zoom" here = a move the analyzer reads with a size change of 20% or more (run 021 review.md uses
the same cut: 9 zooms in the first 12.6 s of "My Mom Cracked The Dinosaur").
Every number is computed from the per-frame zoom series (% size per second), nothing is typed in.

Usage: python tools/make_zoom_presets.py runs/021-reference-shots/motion_0_12.json recipes/zoom_presets.json
"""
import json
import math
import sys

MIN_ZOOM = 20.0       # % size change that counts as a zoom
POINTS = 9            # speed profile resolution


def build(motion):
    fps = motion["fps"]
    z = motion["series"]["zoom_per_s"]
    presets = []
    for mv in motion["moves"]:
        if abs(mv["zoom_total"]) < MIN_ZOOM:
            continue
        seg = z[mv["a"]:mv["b"] + 1]
        size, logs = 1.0, [0.0]          # 0.0 = the size before the first frame of the move
        for v in seg:
            size *= 1 + v / 100 / fps
            logs.append(math.log(size))
        total = (size - 1) * 100
        assert abs(total - mv["zoom_total"]) < 0.2, (mv, total)       # recomputed = analyzer's own total
        end = logs[-1]
        profile = [logs[min(len(logs) - 1, round(k * (len(logs) - 1) / (POINTS - 1)))] / end for k in range(POINTS)]
        profile[-1] = 1.0
        presets.append({
            "id": f"Z{len(presets) + 1}",
            "label": mv["label"],
            "start_s": mv["start"],
            "dur_s": mv["dur"],
            "frames": len(seg),
            "size_pct": round(total, 1),
            "profile": [round(p, 3) for p in profile],     # share of the (log) size change done at each ninth
            "pan_pct": mv["pan"],                           # stored from the analyzer, NOT applied by zoom_states
            "tilt_pct": mv["tilt"],                         # stored from the analyzer, NOT applied by zoom_states
        })
    return {"source": motion["source"], "fps": fps, "min_zoom_pct": MIN_ZOOM, "presets": presets}


if __name__ == "__main__":
    data = build(json.load(open(sys.argv[1])))
    json.dump(data, open(sys.argv[2], "w"), indent=1)
    print(len(data["presets"]), "presets ->", sys.argv[2])
