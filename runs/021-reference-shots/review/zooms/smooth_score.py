"""Smoothness score: how much the picture changes every frame, ours vs the reference (what the eye feels as cuts and dead stretches).
Usage: python3 smooth_score.py REFERENCE.mp4 OURS.mp4 [OURS2.mp4 ...]
Prints per video: median change, share of frames above 10, hard jumps above 25, and the correlation of the per-frame change with the reference's (frame by frame, then in 1/3 s blocks)."""
import subprocess, sys
import numpy as np

def change(p):
    r = subprocess.run(["ffmpeg", "-v", "error", "-t", "12.62", "-i", p, "-vf", "scale=90:160,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    f = np.frombuffer(r, np.uint8).reshape(-1, 160, 90).astype(float)
    return np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))

def blocks(v, k=10):
    n = len(v) // k * k
    return v[:n].reshape(-1, k).mean(axis=1)

ref = change(sys.argv[1])
for p in sys.argv[1:]:
    v = change(p); n = min(len(v), len(ref))
    print(f"{p.split('/')[-1][:44]:<44} median {np.median(v):5.2f}  >10: {100*(v>10).mean():3.0f}%  jumps>25: {int((v>25).sum()):2d}  corr frame {np.corrcoef(v[:n], ref[:n])[0,1]:5.2f}  corr 1/3s {np.corrcoef(blocks(v[:n]), blocks(ref[:n]))[0,1]:5.2f}")
