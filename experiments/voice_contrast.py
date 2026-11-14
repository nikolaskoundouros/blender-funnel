"""Lip-sync check that does not need frame-level correlation: mouth opening at the centres
of closing phonemes (P, B, M) versus open vowels (AA, AE, AH, AO, AW, AY), in the real
speaker's video and in our render, using the timed phonemes from tools/voice_track.py.

Usage: python experiments/voice_contrast.py VOICE.json REAL_TRACK.csv RENDER_TRACK.csv [--shift FRAMES]
"""
import json
import sys

import numpy as np

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
from recipes import face_anim  # noqa: E402

VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY"}
CLOSE = {"P", "B", "M"}
VOWEL_W = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"}


def centres(words, fps):
    out = {"close": [], "open": []}
    for w in words:
        ph = w["phonemes"]
        if not ph:
            continue
        weights = np.array([2.0 if p in VOWEL_W else 1.0 for p in ph])
        edges = w["start"] + (w["end"] - w["start"]) * np.concatenate([[0], np.cumsum(weights)]) / weights.sum()
        for p, a, b in zip(ph, edges[:-1], edges[1:]):
            f = int(round((a + b) / 2 * fps))
            if p in CLOSE:
                out["close"].append(f)
            elif p in VOWELS:
                out["open"].append(f)
    return out


def contrast(lip, c, shift=0):
    get = lambda fs: np.array([lip[f + shift] for f in fs if 0 <= f + shift < len(lip) and not np.isnan(lip[f + shift])])
    lo, hi = get(c["close"]), get(c["open"])
    # Probability that a random open-vowel frame is more open than a random closing frame (AUC).
    auc = float(np.mean(hi[:, None] > lo[None, :])) if len(lo) and len(hi) else float("nan")
    return {"close_median": round(float(np.median(lo)), 4), "open_median": round(float(np.median(hi)), 4),
            "n_close": int(len(lo)), "n_open": int(len(hi)), "auc_open_gt_close": round(auc, 3)}


if __name__ == "__main__":
    d = json.load(open(sys.argv[1]))
    shift = int(sys.argv[sys.argv.index("--shift") + 1]) if "--shift" in sys.argv else 0
    c = centres(d["words"], d["fps"])
    res = {}
    for name, path in (("real_video", sys.argv[2]), ("our_render", sys.argv[3])):
        _, t = face_anim.read_curves(path)
        res[name] = contrast(t["lip_gap"], c, shift)
    print(json.dumps(res, indent=1))
