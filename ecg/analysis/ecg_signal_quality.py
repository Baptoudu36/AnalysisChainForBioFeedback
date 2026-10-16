#!/usr/bin/env python3
"""
Offline signal-quality and heart-rate-variability summary for one ECG run.

Reads the files written by ecg_lab_merged.py (raw.csv, rr_intervals.csv,
metadata.json) and produces:
  - quality_metrics.json   sampling timing, ADC usage, spectral content, HRV
  - fig_ecg_spectrum.png   power spectrum of the raw trace (50 Hz mains check)
  - fig_ecg_notch.png      raw vs. 0.5-40 Hz band-pass vs. band-pass + 50 Hz notch
  - fig_ecg_timing.png     distribution of sample intervals (acquisition jitter)
  - fig_ecg_tachogram.png  RR tachogram with HRV time-domain indices

Nothing here changes the recorded data; it only quantifies it.

Example
-------
  python3 ecg_signal_quality.py ../data/run_20260916T104943Z_mcp3008 --out output
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.signal import butter, iirnotch, sosfiltfilt, filtfilt, welch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BANDS_HZ = [(0.0, 0.5), (0.5, 5.0), (5.0, 15.0), (15.0, 40.0),
            (45.0, 55.0), (55.0, 100.0), (100.0, 400.0)]
MAINS_HZ = 50.0
ADC_BITS = 10

plt.rcParams.update({
    "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "figure.dpi": 100,
})
INK, ACCENT, MUTED, WARN = "#1f2937", "#1d4ed8", "#9ca3af", "#b91c1c"


def load_run(folder: Path):
    raw = np.genfromtxt(folder / "raw.csv", delimiter=",", names=True)
    rr = np.genfromtxt(folder / "rr_intervals.csv", delimiter=",", names=True, ndmin=1)
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    return raw, rr, metadata


def band_power_fractions(f, p):
    total = float(p.sum())
    return {f"{lo:g}-{hi:g} Hz": float(p[(f >= lo) & (f < hi)].sum() / total)
            for lo, hi in BANDS_HZ}


def hrv_time_domain(rr_s: np.ndarray):
    rr_ms = rr_s * 1000.0
    diff = np.diff(rr_ms)
    return {
        "n_rr": int(len(rr_ms)),
        "mean_rr_ms": float(rr_ms.mean()),
        "mean_hr_bpm": float(60000.0 / rr_ms.mean()),
        "min_hr_bpm": float(60000.0 / rr_ms.max()),
        "max_hr_bpm": float(60000.0 / rr_ms.min()),
        "sdnn_ms": float(rr_ms.std(ddof=1)),
        "rmssd_ms": float(np.sqrt(np.mean(diff ** 2))),
        "note": ("Ultra-short window (~10 s). Standard HRV reporting needs at "
                 "least 5 min; values are illustrative of the pipeline only."),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_folder", type=Path)
    ap.add_argument("--out", type=Path, default=Path("output"))
    ap.add_argument("--plot-seconds", type=float, default=3.0)
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    raw, rr_table, metadata = load_run(args.run_folder)
    t, v, adc = raw["time_s"], raw["raw_signal"], raw["raw_adc"]
    dt = np.diff(t)
    fs = (len(t) - 1) / (t[-1] - t[0])
    vref = float(metadata.get("vref_v", 3.3))

    # Uniform grid for spectral work (the v1.2.0 run was software-timed).
    grid = np.linspace(t[0], t[-1], len(t))
    x = np.interp(grid, t, v)

    f, p = welch(x - x.mean(), fs=fs, nperseg=min(len(x), 4096))
    fractions = band_power_fractions(f, p)
    mains_mask = (f >= MAINS_HZ - 1) & (f <= MAINS_HZ + 1)
    mains_peak_hz = float(f[mains_mask][np.argmax(p[mains_mask])])

    bp = sosfiltfilt(butter(4, [0.5, 40.0], btype="bandpass", fs=fs, output="sos"), x)
    b, a = iirnotch(MAINS_HZ, Q=30.0, fs=fs)
    bp_notch = filtfilt(b, a, bp)
    residual_50 = bp - bp_notch
    ecg_band = (f >= 0.5) & (f < 40.0)

    rr_s = rr_table["RR_s"][rr_table["in_configured_range"] == 1]
    hrv = hrv_time_domain(rr_s)

    metrics = {
        "run": str(args.run_folder.name),
        "script_version": metadata.get("script_version"),
        "timestamp_kind": metadata.get("timestamp_kind"),
        "timing": {
            "samples": int(len(t)),
            "span_s": float(t[-1] - t[0]),
            "target_fs_hz": metadata.get("target_fs_hz"),
            "measured_fs_hz": float(fs),
            "median_interval_ms": float(np.median(dt) * 1000),
            "min_interval_ms": float(dt.min() * 1000),
            "max_interval_ms": float(dt.max() * 1000),
            "p95_abs_deviation_fraction": float(
                np.percentile(np.abs(dt - np.median(dt)), 95) / np.median(dt)),
            "missed_schedule_slots": metadata.get("missed_schedule_slots"),
            "nyquist_hz": float(fs / 2),
        },
        "adc": {
            "bits": ADC_BITS,
            "vref_v": vref,
            "lsb_mv": vref / (2 ** ADC_BITS) * 1000,
            "code_min": int(np.nanmin(adc)),
            "code_max": int(np.nanmax(adc)),
            "used_range_fraction": float((np.nanmax(adc) - np.nanmin(adc)) / (2 ** ADC_BITS - 1)),
            "near_rail_fraction": float(np.mean((adc <= 1) | (adc >= 1022))),
            "peak_to_peak_v": float(v.max() - v.min()),
        },
        "spectrum": {
            "band_power_fractions": fractions,
            "mains_peak_hz": mains_peak_hz,
            "fundamental_hz_below_3hz": float(f[(f > 0.5) & (f < 3)][np.argmax(p[(f > 0.5) & (f < 3)])]),
            "rms_removed_by_50hz_notch_v": float(np.sqrt(np.mean(residual_50 ** 2))),
            "rms_bandpassed_v": float(np.sqrt(np.mean(bp ** 2))),
            "ecg_band_power_fraction": float(p[ecg_band].sum() / p.sum()),
        },
        "hrv_time_domain": hrv,
    }
    (args.out / "quality_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")

    # --- Figure 1: spectrum -------------------------------------------------
    fig, ax = plt.subplots(figsize=(7.2, 2.8), constrained_layout=True)
    ax.semilogy(f, p, color=INK, lw=0.9)
    ax.axvspan(0.5, 40, color=ACCENT, alpha=0.08, label="ECG analysis band 0.5–40 Hz")
    ax.axvline(MAINS_HZ, color=WARN, lw=1, ls="--", label=f"Mains {MAINS_HZ:g} Hz")
    ax.annotate(f"{fractions['45-55 Hz'] * 100:.0f}% of power\nat {mains_peak_hz:.1f} Hz",
                xy=(mains_peak_hz, p[mains_mask].max()), xytext=(62, p[mains_mask].max() * 0.02),
                color=WARN, fontsize=8, arrowprops=dict(arrowstyle="->", color=WARN))
    ax.set(xlim=(0, 120), xlabel="Frequency (Hz)", ylabel="PSD (V²/Hz)",
           title="Power spectral density of the raw ECG trace (Welch)")
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    fig.savefig(args.out / "fig_ecg_spectrum.png", dpi=200)
    plt.close(fig)

    # --- Figure 2: filtering stages -----------------------------------------
    sel = grid <= grid[0] + args.plot_seconds
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 5.0), sharex=True, constrained_layout=True)
    axes[0].plot(grid[sel], x[sel], color=MUTED, lw=0.8)
    axes[0].set(ylabel="V", title="① Raw ADC voltage (MCP3008, 800 Hz)")
    axes[1].plot(grid[sel], bp[sel], color=INK, lw=0.8)
    axes[1].set(ylabel="V", title="② Zero-phase Butterworth band-pass 0.5–40 Hz (pipeline default)")
    axes[2].plot(grid[sel], bp_notch[sel], color=ACCENT, lw=0.9)
    axes[2].set(ylabel="V", xlabel="Time (s)",
                title="③ Band-pass + 50 Hz notch (Q = 30) — exploratory, not in the pipeline")
    fig.savefig(args.out / "fig_ecg_notch.png", dpi=200)
    plt.close(fig)

    # --- Figure 3: timing ---------------------------------------------------
    fig, ax = plt.subplots(figsize=(7.2, 2.4), constrained_layout=True)
    ax.hist(dt * 1000, bins=120, color=INK, alpha=0.85)
    ax.axvline(1000 / float(metadata.get("target_fs_hz", fs)), color=ACCENT, ls="--", lw=1,
               label="Nominal 1.25 ms (800 Hz)")
    ax.set_yscale("log")
    ax.set(xlabel="Interval between consecutive samples (ms)", ylabel="Count (log)",
           title="Software-timed sampling intervals (script v1.2.0)")
    ax.legend(frameon=False, fontsize=8)
    fig.savefig(args.out / "fig_ecg_timing.png", dpi=200)
    plt.close(fig)

    # --- Figure 4: tachogram ------------------------------------------------
    fig, ax = plt.subplots(figsize=(7.2, 2.4), constrained_layout=True)
    r_end = rr_table["R_time_s"][rr_table["in_configured_range"] == 1]
    ax.plot(r_end, rr_s * 1000, "o-", color=ACCENT, ms=4, lw=1)
    ax.axhline(hrv["mean_rr_ms"], color=MUTED, ls="--", lw=1)
    ax.set(xlabel="Time of R peak (s)", ylabel="RR interval (ms)",
           title=(f"RR tachogram — mean HR {hrv['mean_hr_bpm']:.1f} bpm, "
                  f"SDNN {hrv['sdnn_ms']:.1f} ms, RMSSD {hrv['rmssd_ms']:.1f} ms (n = {hrv['n_rr']})"))
    fig.savefig(args.out / "fig_ecg_tachogram.png", dpi=200)
    plt.close(fig)

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
