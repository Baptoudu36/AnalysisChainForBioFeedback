#!/usr/bin/env python3
"""Draw the two schematic figures of the report (biofeedback chain, jump pipeline).

Coordinates are in millimetre-like units with an equal aspect ratio so that
rounded boxes and text keep their proportions.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "figures"
INK, ACCENT, SOFT, ECG, JUMP, MUTED, WARN = "#1f2937", "#215bcc", "#e8effc", "#b91c1c", "#047857", "#6b7280", "#b45309"


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w / 25.4, h / 25.4))
    ax.set(xlim=(0, w), ylim=(0, h), aspect="equal")
    ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    return fig, ax


def box(ax, x, y, w, h, fc="white", ec=INK, lw=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.6", fc=fc, ec=ec, lw=lw))


def arrow(ax, x0, y0, x1, y1, color=INK):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=8, lw=1.0,
                                 color=color, shrinkA=0, shrinkB=0))


def biofeedback_chain():
    W, H = 180, 92
    fig, ax = canvas(W, H)
    stages = ["Phenomenon", "Sensor", "Conditioning\n& ADC", "Raspberry Pi\n(Linux, Python)",
              "Processing", "Indicators", "Decision &\nfeedback"]
    ecg = ["Cardiac\nelectrical\nactivity", "3 chest\nelectrodes", "Analogue\nfront-end +\nMCP3008\n(10-bit, SPI)",
           "800 Hz\nsampling;\npigpio DMA\nclock (v2)", "0.5–40 Hz\nband-pass;\nR-peak\ndetection",
           "HR, RR,\nHRV,\nPQRST\ncandidates", "Figure,\nCSV/JSON,\nECG Explorer"]
    jump = ["Vertical\njump of the\ncentre of\nmass", "Camera\nV2.1 +\nGPIO\nbutton", "Image\nsensor ADC;\nH.264\n640×480",
            "60 fps;\nframe\ntimestamps", "ROI +\nlinear SVM\ncontact /\nflight",
            "Flight time,\nheight,\nforce,\npower", "Annotated\nvideo, results,\ndashboard"]
    n, bw, gap, x0 = 7, 22.0, 3.6, 1.5
    for i in range(n):
        x = x0 + i * (bw + gap)
        box(ax, x, 76, bw, 13, fc=SOFT, ec=ACCENT)
        ax.text(x + bw / 2, 82.5, stages[i], ha="center", va="center", fontsize=6.6, fontweight="bold", color=ACCENT)
        box(ax, x, 41, bw, 27, ec=ECG)
        ax.text(x + bw / 2, 54.5, ecg[i], ha="center", va="center", fontsize=6.2, color=INK, linespacing=1.25)
        box(ax, x, 6, bw, 27, ec=JUMP)
        ax.text(x + bw / 2, 19.5, jump[i], ha="center", va="center", fontsize=6.2, color=INK, linespacing=1.25)
        if i < n - 1:
            for yy, c in [(82.5, ACCENT), (54.5, ECG), (19.5, JUMP)]:
                arrow(ax, x + bw + 0.3, yy, x + bw + gap - 0.3, yy, c)
    ax.text(x0, 70.5, "Project A — ECG acquisition chain", fontsize=7, color=ECG, fontweight="bold")
    ax.text(x0, 35.5, "Project B — Squat-jump video chain", fontsize=7, color=JUMP, fontweight="bold")
    ax.text(W / 2, 1.5, "physical world  →  electronics  →  software  →  user", ha="center", fontsize=6.5, color=MUTED)
    fig.savefig(OUT / "diagram_biofeedback_chain.png", dpi=250)
    plt.close(fig)


def jump_pipeline():
    W, H = 180, 78
    fig, ax = canvas(W, H)
    steps = [("1 · Inputs", "main.py\nbody mass (kg)\npush-off distance (cm)"),
             ("2 · Recording", "GPIO button start/stop\nH.264 + timestamps.csv\nremux to MP4 (ffmpeg)"),
             ("3 · Detection", "detector.py\nROI → 320×96 grey\nSVM score per frame"),
             ("4 · Events", "5-frame smoothing\ncontact → flight → contact\nmargin ≥ 0.15"),
             ("5 · Mechanics", "mechanics.py\nh, v₀, F̄, v̄, P̄\nP̄ per kg"),
             ("6 · Outputs", "report.py\nresults.json / .csv\nannotated_review.mp4")]
    bw, gap, x0, y0, bh = 26.5, 3.6, 1.5, 44, 30
    for i, (t, body) in enumerate(steps):
        x = x0 + i * (bw + gap)
        hi = i in (2, 3)
        box(ax, x, y0, bw, bh, fc=SOFT if hi else "white", ec=ACCENT if hi else INK)
        ax.text(x + bw / 2, y0 + bh - 4.5, t, ha="center", va="center", fontsize=7, fontweight="bold",
                color=ACCENT if hi else INK)
        ax.text(x + bw / 2, y0 + bh / 2 - 3, body, ha="center", va="center", fontsize=5.8, color=INK, linespacing=1.4)
        if i < len(steps) - 1:
            arrow(ax, x + bw + 0.3, y0 + bh / 2, x + bw + gap - 0.3, y0 + bh / 2)
    xd = x0 + 3 * (bw + gap)
    xm = x0 + 4 * (bw + gap)
    box(ax, xd - 4, 4, bw + 8, 26, fc="#fff7ed", ec=WARN)
    ax.text(xd + bw / 2, 25, "Fallback · manual review", ha="center", va="center", fontsize=6.8, fontweight="bold", color=WARN)
    ax.text(xd + bw / 2, 14, "OpenCV window, frame slider\nTAKE-OFF / LANDING / ACCEPT\n→ detection_method = manual",
            ha="center", va="center", fontsize=5.8, color=INK, linespacing=1.4)
    arrow(ax, xd + bw / 2, y0 - 0.3, xd + bw / 2, 30.3, WARN)
    ax.text(xd + bw / 2 + 1.2, 37, "no confident\nsequence", fontsize=5.6, color=WARN, va="center")
    arrow(ax, xd + bw + 4.3, 17, xm + bw / 2, y0 - 0.3, WARN)
    box(ax, x0, 4, 2 * bw + gap + 14, 26, ec=MUTED)
    ax.text(x0 + (2 * bw + gap + 14) / 2, 25, "Offline training", ha="center", va="center", fontsize=6.8,
            fontweight="bold", color=MUTED)
    ax.text(x0 + (2 * bw + gap + 14) / 2, 14,
            "record_tr_videos.py: 20 × 5 s videos\n168 hand-labelled frames (annotations.csv)\n"
            "train_contact_model.py → contact_model.joblib",
            ha="center", va="center", fontsize=5.8, color=INK, linespacing=1.4)
    xdet = x0 + 2 * (bw + gap)
    arrow(ax, x0 + 2 * bw + gap + 14.3, 20, xdet + bw / 2, y0 - 0.3, MUTED)
    fig.savefig(OUT / "diagram_jump_pipeline.png", dpi=250)
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    biofeedback_chain()
    jump_pipeline()
