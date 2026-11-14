"""Speech audio -> per-frame viseme curves for lip sync (CSV), plus the timed words.

Runs in the tracker environment (.venv-face) with faster-whisper (MIT):
    uv pip install -p .venv-face/bin/python faster-whisper==1.2.1
Pronunciations: CMUdict (assets/cmudict, BSD-style), fetched by tools/fetch_assets.sh.

Usage:
    .venv-face/bin/python -I tools/voice_track.py AUDIO out.csv [--fps 24] [--model base.en]
        [--start S --duration D]
Columns: frame, time_s, the 21 Visemes 01 names (0..1), loudness (0..1). Writes out.json
with the words, their times and phonemes.

Method (notes/voice-lipsync.md): Whisper word timestamps; each word's CMUdict phonemes
share its span (vowels count double); each phoneme is a raised-cosine bump on its viseme,
widened by 50% either side so neighbours overlap (coarticulation); per frame each viseme
takes the strongest bump; everything is scaled by the loudness envelope (RMS, 50 ms).
"""
import argparse
import csv
import json
import os
import re
import subprocess

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CMUDICT = os.path.join(ROOT, "assets", "cmudict", "cmudict.dict")
VISEMES = ["aa_ah_ax_01", "aa_02", "ao_03", "ey_eh_uh_04", "er_05", "y_iy_ih_ix_06", "w_uw_07", "ow_08",
           "aw_09", "oy_10", "ay_11", "h_12", "r_13", "l_14", "s_z_15", "sh_ch_jh_zh_16", "th_dh_17",
           "f_v_18", "d_t_n_19", "k_g_ng_20", "p_b_m_21"]
PHONE_TO_VISEME = {
    "AE": "aa_ah_ax_01", "AH": "aa_ah_ax_01", "AA": "aa_02", "AO": "ao_03", "EY": "ey_eh_uh_04",
    "EH": "ey_eh_uh_04", "UH": "ey_eh_uh_04", "ER": "er_05", "Y": "y_iy_ih_ix_06", "IY": "y_iy_ih_ix_06",
    "IH": "y_iy_ih_ix_06", "W": "w_uw_07", "UW": "w_uw_07", "OW": "ow_08", "AW": "aw_09", "OY": "oy_10",
    "AY": "ay_11", "HH": "h_12", "R": "r_13", "L": "l_14", "S": "s_z_15", "Z": "s_z_15",
    "SH": "sh_ch_jh_zh_16", "CH": "sh_ch_jh_zh_16", "JH": "sh_ch_jh_zh_16", "ZH": "sh_ch_jh_zh_16",
    "TH": "th_dh_17", "DH": "th_dh_17", "F": "f_v_18", "V": "f_v_18", "D": "d_t_n_19", "T": "d_t_n_19",
    "N": "d_t_n_19", "K": "k_g_ng_20", "G": "k_g_ng_20", "NG": "k_g_ng_20", "P": "p_b_m_21",
    "B": "p_b_m_21", "M": "p_b_m_21"}
VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"}
# Rough spelling fallback for words missing from CMUdict.
LETTERS = {"a": "AE", "b": "B", "c": "K", "d": "D", "e": "EH", "f": "F", "g": "G", "h": "HH", "i": "IH",
           "j": "JH", "k": "K", "l": "L", "m": "M", "n": "N", "o": "OW", "p": "P", "q": "K", "r": "R",
           "s": "S", "t": "T", "u": "AH", "v": "V", "w": "W", "x": "K", "y": "Y", "z": "Z"}


def load_cmudict(path=CMUDICT):
    d = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.split("#")[0].split()
            if not parts:
                continue
            word = re.sub(r"\(\d+\)$", "", parts[0])
            if word not in d:                       # first pronunciation
                d[word] = [re.sub(r"\d", "", p) for p in parts[1:]]
    return d


def phonemes(word, cmu):
    w = re.sub(r"[^a-z']", "", word.lower())
    if not w:
        return []
    if w in cmu:
        return cmu[w]
    if w.strip("'") in cmu:
        return cmu[w.strip("'")]
    return [LETTERS[c] for c in w if c in LETTERS]


def read_audio(path, start=0.0, duration=None, rate=16000):
    """Mono float32 samples via ffmpeg."""
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start)] + (["-t", str(duration)] if duration else []) + \
          ["-i", path, "-ac", "1", "-ar", str(rate), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, check=True, capture_output=True).stdout, dtype=np.float32), rate


def loudness(samples, rate, fps, n):
    """RMS over 50 ms windows at frame times, scaled so the 95th percentile of voiced frames is 1."""
    half = int(0.025 * rate)
    out = np.zeros(n)
    for i in range(n):
        c = int(i / fps * rate)
        seg = samples[max(0, c - half):c + half]
        out[i] = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0
    voiced = out[out > 0.1 * out.max()] if out.max() > 0 else out
    return np.clip(out / max(np.percentile(voiced, 95), 1e-9), 0.0, 1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("out")
    ap.add_argument("--fps", type=float, default=24.0)
    ap.add_argument("--model", default="base.en")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--spread", type=float, default=0.5, help="bump widening either side, fraction of the phoneme")
    a = ap.parse_args()
    from faster_whisper import WhisperModel
    samples, rate = read_audio(a.audio, a.start, a.duration)
    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(samples, language="en", word_timestamps=True, vad_filter=True)
    cmu = load_cmudict()
    words, phones = [], []
    for seg in segments:
        for w in seg.words:
            ph = phonemes(w.word, cmu)
            words.append({"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3), "phonemes": ph})
            if not ph:
                continue
            weights = np.array([2.0 if p in VOWELS else 1.0 for p in ph])
            edges = w.start + (w.end - w.start) * np.concatenate([[0], np.cumsum(weights)]) / weights.sum()
            for p, t0, t1 in zip(ph, edges[:-1], edges[1:]):
                phones.append((PHONE_TO_VISEME.get(p), t0, t1))
    n = int(len(samples) / rate * a.fps) + 1
    t = np.arange(n) / a.fps
    curves = {v: np.zeros(n) for v in VISEMES}
    for vis, t0, t1 in phones:
        if vis is None:
            continue
        mid, half = (t0 + t1) / 2, (t1 - t0) / 2 * (1 + a.spread)
        half = max(half, 0.75 / a.fps)                 # at least visible for a frame and a half
        bump = np.clip(np.cos(np.clip((t - mid) / half, -1, 1) * np.pi / 2), 0, None) ** 2
        curves[vis] = np.maximum(curves[vis], bump)
    loud = loudness(samples, rate, a.fps, n)
    scale = 0.4 + 0.6 * loud                           # quieter speech, smaller shapes
    with open(a.out, "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["frame", "time_s"] + VISEMES + ["loudness"])
        for i in range(n):
            wr.writerow([i, f"{t[i]:.4f}"] + [f"{curves[v][i] * scale[i]:.4f}" for v in VISEMES] + [f"{loud[i]:.4f}"])
    json.dump({"audio": os.path.basename(a.audio), "start": a.start, "fps": a.fps, "model": a.model,
               "words": words}, open(os.path.splitext(a.out)[0] + ".json", "w"), indent=1)
    print(f"{a.out}: {n} frames, {len(words)} words, {sum(1 for w in words if not w['phonemes'])} without phonemes")


if __name__ == "__main__":
    main()
