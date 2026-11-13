"""Numbers that describe a render, so reviews do not rest on impressions alone.

Usage: python image_stats.py image.png [image2.png ...]
"""
import json
import sys

import numpy as np
from PIL import Image


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float64) / 255.0


def luminance(rgb):
    return rgb @ np.array([0.2126, 0.7152, 0.0722])


def stats(path):
    rgb = load(path)
    lum = luminance(rgb)
    p5, p50, p95 = np.percentile(lum, [5, 50, 95])
    return {
        "p5": round(float(p5), 3),
        "median": round(float(p50), 3),
        "p95": round(float(p95), 3),
        "spread_p95_minus_p5": round(float(p95 - p5), 3),
        "clipped_fraction": round(float((rgb.max(axis=2) >= 0.985).mean()), 4),
        "near_black_fraction": round(float((lum <= 0.02).mean()), 4),
    }


if __name__ == "__main__":
    print(json.dumps({p: stats(p) for p in sys.argv[1:]}, indent=2))
