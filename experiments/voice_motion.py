"""How much and how fast the mouth moves: real speaker vs our render (landmarks only).

For lip gap and mouth width (face widths): spread (p95 - p5), mean absolute change per
frame (speed), and the share of the motion above 6 Hz (jitter; real lips move at syllable
rate, about 3 to 6 Hz). Usage: python experiments/voice_motion.py REAL.csv OURS.csv [FPS]
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from recipes import face_anim  # noqa: E402


def stats(x, fps):
    x = np.nan_to_num(x, nan=float(np.nanmedian(x)))
    spec = np.abs(np.fft.rfft(x - x.mean())) ** 2
    f = np.fft.rfftfreq(len(x), 1 / fps)
    return {"spread": round(float(np.percentile(x, 95) - np.percentile(x, 5)), 4),
            "speed_per_frame": round(float(np.mean(np.abs(np.diff(x)))), 4),
            "share_above_6hz": round(float(spec[f > 6].sum() / max(spec[f > 0.3].sum(), 1e-12)), 3)}


if __name__ == "__main__":
    fps = float(sys.argv[3]) if len(sys.argv) > 3 else 24.0
    _, real = face_anim.read_curves(sys.argv[1])
    _, ours = face_anim.read_curves(sys.argv[2])
    n = min(len(real["lip_gap"]), len(ours["lip_gap"]))
    out = {k: {"real": stats(real[k][:n], fps), "ours": stats(ours[k][:n], fps)} for k in ("lip_gap", "mouth_width")}
    print(json.dumps(out, indent=1))
