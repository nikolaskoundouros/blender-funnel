"""Curve comparison used by the face and voice experiments."""
import numpy as np


def compare(x, y, max_lag=6):
    m = ~np.isnan(x) & ~np.isnan(y)
    x, y = x[m], y[m]
    best = (-2.0, 0)
    for lag in range(-max_lag, max_lag + 1):
        xs, ys = (x[:len(x) - lag], y[lag:]) if lag >= 0 else (x[-lag:], y[:len(y) + lag])
        r = float(np.corrcoef(xs, ys)[0, 1])
        best = max(best, (r, lag))
    amp = lambda z: float(np.percentile(z, 95) - np.percentile(z, 5))
    return {"r_lag0": round(float(np.corrcoef(x, y)[0, 1]), 3), "r_best": round(best[0], 3), "lag_frames": best[1],
            "amplitude_ratio_render_over_source": round(amp(y) / max(amp(x), 1e-9), 3)}
