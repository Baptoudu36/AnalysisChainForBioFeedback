#!/usr/bin/env python3
"""
Offline analysis of the 20-video squat-jump training dataset.

Three questions, all answered from files already in the repository:

1. Reference performance  - what do the manually annotated take-off / landing
   frames (annotations.csv) give in flight time, jump height, force and power?
   Mechanics use mechanics.calculate_metrics(), i.e. exactly the on-Pi code.
2. Timing resolution      - how much does one video frame (~16.7 ms) weigh on
   the estimated jump height?
3. Detector validity      - how well does the automatic contact/flight detector
   (detector.detect_events) recover the annotated events on videos it has NOT
   seen during training? Evaluated by leave-one-video-out (LOVO) re-training
   with the same features and classifier as train_contact_model.py.

Body mass and push-off distance are those typed during the 14 Oct 2026 demo
(66 kg, 31 cm); the group confirmed that the 20 videos show the same person.
The push-off distance is assumed identical for every trial.

Outputs (in --out):
  jump_reference_metrics.csv, detector_lovo.csv, summary.json,
  dashboard_data.json and fig_*.png for the report.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
from pathlib import Path

import cv2
import joblib
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from detector import crop_roi, detect_events, load_config  # noqa: E402
from mechanics import G, calculate_metrics  # noqa: E402
from train_contact_model import extract_frame, feature  # noqa: E402

MASS_KG = 66.0
PUSH_OFF_M = 0.31

plt.rcParams.update({
    "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25,
})
INK, ACCENT, MUTED, WARN, OK = "#1f2937", "#1d4ed8", "#9ca3af", "#b91c1c", "#047857"


# --------------------------------------------------------------------------- #
# Reference events from the manual annotations
# --------------------------------------------------------------------------- #
def read_annotations(path: Path):
    per_video: dict[str, list[tuple[int, str]]] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            per_video.setdefault(row["video_path"], []).append(
                (int(row["frame_index"]), row["label"].strip().upper()))
    return {k: sorted(v) for k, v in sorted(per_video.items())}


def reference_events(rows):
    """Take-off = first FLIGHT frame; landing = first CONTACT frame after flight.

    This is the README convention: take-off is the first frame with neither foot
    on the ground, landing the first frame with a foot back on the ground.
    """
    flight = [i for i, lab in rows if lab == "FLIGHT"]
    takeoff = min(flight)
    landing = min(i for i, lab in rows if lab == "CONTACT" and i > max(flight))
    last_contact_before = max(i for i, lab in rows if lab == "CONTACT" and i < takeoff)
    if last_contact_before != takeoff - 1 or max(flight) != landing - 1:
        raise ValueError("Annotations do not bracket the transitions frame-to-frame.")
    return takeoff, landing


def frame_pts_ms(video: Path):
    cap = cv2.VideoCapture(str(video))
    pts = []
    while True:
        ok, _ = cap.read()
        if not ok:
            break
        pts.append(cap.get(cv2.CAP_PROP_POS_MSEC))
    cap.release()
    return np.asarray(pts)


# --------------------------------------------------------------------------- #
# Detector re-training (identical recipe to train_contact_model.py)
# --------------------------------------------------------------------------- #
def build_features(annotations, roi_norm):
    cache = {}
    for video, rows in annotations.items():
        X, y = [], []
        for idx, lab in rows:
            base = feature(extract_frame(ROOT / video, idx), roi_norm)
            sign = 1 if lab == "CONTACT" else -1
            for img in (base,
                        np.clip(base * 0.75, 0, 1),
                        np.clip(base * 1.20 + 0.04, 0, 1)):
                X.append(img)
                y.append(sign)
        cache[video] = (np.asarray(X, np.float32), np.asarray(y, np.int32))
    return cache


def train(cache, videos):
    X = np.concatenate([cache[v][0] for v in videos])
    y = np.concatenate([cache[v][1] for v in videos])
    model = make_pipeline(StandardScaler(),
                          LinearSVC(class_weight="balanced", C=0.1, max_iter=10000, random_state=42))
    return model.fit(X, y)


def frame_scores(model, video: Path, roi_norm):
    cap = cv2.VideoCapture(str(video))
    scores = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(crop_roi(frame, roi_norm), cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (320, 96), interpolation=cv2.INTER_AREA)
        scores.append(float(model.decision_function(gray.reshape(1, -1).astype(np.float32) / 255.0)[0]))
    cap.release()
    return np.asarray(scores)


def height_from_flight(t):
    return G * t * t / 8.0


# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--annotations", type=Path, default=ROOT / "annotations.csv")
    ap.add_argument("--config", type=Path, default=ROOT / "config.json")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "output")
    ap.add_argument("--figures-only", action="store_true",
                    help="Redraw figures from the saved outputs (skips the ~10 min LOVO re-training)")
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    config = load_config(args.config)
    roi = config["roi_norm"]
    if args.figures_only:
        saved = json.loads((args.out / "dashboard_data.json").read_text())
        make_figures(args.out, saved["trials"], saved["lovo"], saved["scores"], saved["summary"], roi)
        return
    fps = float(config["expected_fps"])
    annotations = read_annotations(args.annotations)
    videos = list(annotations)

    # ---- 1. Reference metrics --------------------------------------------- #
    ref_rows = []
    for video, rows in annotations.items():
        takeoff, landing = reference_events(rows)
        pts = frame_pts_ms(ROOT / video)
        t_pts = (pts[landing] - pts[takeoff]) / 1000.0
        t_nom = (landing - takeoff) / fps
        m = calculate_metrics(t_pts, MASS_KG, PUSH_OFF_M)
        ref_rows.append({
            "trial": Path(video).stem, "video": video,
            "takeoff_frame": takeoff, "landing_frame": landing,
            "flight_frames": landing - takeoff,
            "flight_time_pts_s": t_pts, "flight_time_nominal60_s": t_nom,
            "jump_height_cm": m["jump_height_cm"],
            "jump_height_nominal60_cm": height_from_flight(t_nom) * 100,
            "takeoff_velocity_m_s": m["takeoff_velocity_m_s"],
            "mean_push_force_N": m["mean_push_force_N"],
            "mean_push_velocity_m_s": m["mean_push_velocity_m_s"],
            "mean_push_power_W": m["mean_push_power_W"],
            "mean_push_power_W_kg": m["mean_push_power_W_kg"],
            "frames_in_video": int(len(pts)),
            "median_frame_interval_ms": float(np.median(np.diff(pts))),
        })
    with (args.out / "jump_reference_metrics.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ref_rows[0]))
        w.writeheader()
        w.writerows(ref_rows)

    def stats(key):
        a = np.array([r[key] for r in ref_rows])
        return {"mean": float(a.mean()), "sd": float(a.std(ddof=1)),
                "cv_percent": float(a.std(ddof=1) / a.mean() * 100),
                "min": float(a.min()), "max": float(a.max())}

    keys = ["flight_time_pts_s", "jump_height_cm", "takeoff_velocity_m_s",
            "mean_push_force_N", "mean_push_power_W", "mean_push_power_W_kg"]
    reference_summary = {k: stats(k) for k in keys}
    nominal_vs_pts_ms = np.array([(r["flight_time_nominal60_s"] - r["flight_time_pts_s"]) * 1000
                                  for r in ref_rows])

    # ---- 2. Frame quantisation ------------------------------------------- #
    t_mean = reference_summary["flight_time_pts_s"]["mean"]
    one_frame_s = 1.0 / fps
    dh_one_frame_cm = (height_from_flight(t_mean + one_frame_s) - height_from_flight(t_mean)) * 100

    # ---- 3. Detector LOVO evaluation -------------------------------------- #
    cache = build_features(annotations, roi)
    lovo_rows, score_traces = [], {}
    with tempfile.TemporaryDirectory() as tmp:
        for held_out in videos:
            model = train(cache, [v for v in videos if v != held_out])
            model_path = Path(tmp) / "fold.joblib"
            joblib.dump(model, model_path)
            fold_config = dict(config, model_path=str(model_path))
            result = detect_events(str(ROOT / held_out), str(Path(tmp) / "no_timestamps.csv"), fold_config)

            Xh, yh = cache[held_out]
            pred = np.sign(model.decision_function(Xh[::3]))  # un-augmented frames only
            frame_acc = float(np.mean(pred == yh[::3]))

            ref = next(r for r in ref_rows if r["video"] == held_out)
            row = {"trial": ref["trial"], "status": "accepted" if result.get("ok") else "rejected",
                   "message": result.get("message", ""), "annotated_frame_accuracy": frame_acc,
                   "ref_takeoff": ref["takeoff_frame"], "ref_landing": ref["landing_frame"],
                   "det_takeoff": "", "det_landing": "", "takeoff_error_frames": "",
                   "landing_error_frames": "", "flight_time_error_ms": "", "height_error_cm": "",
                   "event_score_margin": result.get("event_score_margin", "")}
            if result.get("ok"):
                dt_ = result["takeoff_frame_index"] - ref["takeoff_frame"]
                dl_ = result["landing_frame_index"] - ref["landing_frame"]
                t_det = (result["landing_frame_index"] - result["takeoff_frame_index"]) / fps
                row.update({
                    "det_takeoff": result["takeoff_frame_index"],
                    "det_landing": result["landing_frame_index"],
                    "takeoff_error_frames": dt_, "landing_error_frames": dl_,
                    "flight_time_error_ms": (t_det - ref["flight_time_nominal60_s"]) * 1000,
                    "height_error_cm": (height_from_flight(t_det)
                                        - height_from_flight(ref["flight_time_nominal60_s"])) * 100,
                })
            lovo_rows.append(row)
            score_traces[ref["trial"]] = frame_scores(model, ROOT / held_out, roi).tolist()

    with (args.out / "detector_lovo.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lovo_rows[0]))
        w.writeheader()
        w.writerows(lovo_rows)

    accepted = [r for r in lovo_rows if r["status"] == "accepted"]
    fte = np.array([r["flight_time_error_ms"] for r in accepted], float)
    he = np.array([r["height_error_cm"] for r in accepted], float)
    exact_both = sum(1 for r in accepted
                     if r["takeoff_error_frames"] == 0 and r["landing_error_frames"] == 0)
    within1 = sum(1 for r in accepted
                  if abs(r["takeoff_error_frames"]) <= 1 and abs(r["landing_error_frames"]) <= 1)
    within2 = sum(1 for r in accepted
                  if abs(r["takeoff_error_frames"]) <= 2 and abs(r["landing_error_frames"]) <= 2)
    wrong_jump = [r["trial"] for r in accepted
                  if max(abs(r["takeoff_error_frames"]), abs(r["landing_error_frames"])) > 10]
    detector_summary = {
        "videos": len(lovo_rows),
        "accepted_automatically": len(accepted),
        "rejected_to_manual_review": len(lovo_rows) - len(accepted),
        "both_events_exact": exact_both,
        "both_events_within_1_frame": within1,
        "both_events_within_2_frames": within2,
        "wrong_jump_selected (error > 10 frames)": wrong_jump,
        "mean_annotated_frame_accuracy": float(np.mean([r["annotated_frame_accuracy"] for r in lovo_rows])),
        "flight_time_error_ms": ({"mean": float(fte.mean()), "mean_abs": float(np.abs(fte).mean()),
                                  "median_abs": float(np.median(np.abs(fte))),
                                  "max_abs": float(np.abs(fte).max())} if len(fte) else None),
        "height_error_cm": ({"mean": float(he.mean()), "mean_abs": float(np.abs(he).mean()),
                             "median_abs": float(np.median(np.abs(he))),
                             "max_abs": float(np.abs(he).max())} if len(he) else None),
    }

    summary = {
        "inputs": {"mass_kg": MASS_KG, "push_off_distance_m": PUSH_OFF_M, "nominal_fps": fps,
                   "roi_norm": roi, "n_trials": len(ref_rows),
                   "timing_source": "MP4 presentation timestamps written by rpicam-vid --save-pts"},
        "reference": reference_summary,
        "nominal60_minus_pts_flight_time_ms": {"mean": float(nominal_vs_pts_ms.mean()),
                                               "max_abs": float(np.abs(nominal_vs_pts_ms).max())},
        "quantisation": {"one_frame_ms": one_frame_s * 1000,
                         "height_change_for_one_frame_cm_at_mean_flight": dh_one_frame_cm},
        "detector_lovo": detector_summary,
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (args.out / "dashboard_data.json").write_text(json.dumps({
        "summary": summary, "trials": ref_rows, "lovo": lovo_rows,
        "scores": {k: [round(s, 4) for s in v] for k, v in score_traces.items()},
    }) + "\n")

    make_figures(args.out, ref_rows, lovo_rows, score_traces, summary, roi)
    print(json.dumps(summary, indent=2))


# --------------------------------------------------------------------------- #
def make_figures(out, ref_rows, lovo_rows, score_traces, summary, roi):
    trials = [r["trial"].replace("jump_", "J") for r in ref_rows]
    heights = np.array([r["jump_height_cm"] for r in ref_rows])
    power = np.array([r["mean_push_power_W_kg"] for r in ref_rows])

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.7), constrained_layout=True,
                             gridspec_kw={"width_ratios": [3, 1.2]})
    ax = axes[0]
    ax.bar(trials, heights, color=ACCENT, width=0.7)
    ax.axhline(heights.mean(), color=INK, ls="--", lw=1)
    ax.fill_between([-0.5, len(trials) - 0.5], heights.mean() - heights.std(ddof=1),
                    heights.mean() + heights.std(ddof=1), color=MUTED, alpha=0.25, lw=0)
    ax.set(ylabel="Jump height (cm)", ylim=(0, heights.max() * 1.25),
           title=f"Reference jump height per trial (mean {heights.mean():.1f} ± {heights.std(ddof=1):.1f} cm)")
    ax.tick_params(axis="x", labelsize=7, rotation=90)
    ax = axes[1]
    conditions_csv = out / "dataset_conditions.csv"
    if conditions_csv.exists():
        with conditions_csv.open(newline="") as f:
            cond = {r["trial"]: r for r in csv.DictReader(f)}
        groups = ["barefoot", "shoes", "socks"]
        for gi, g in enumerate(groups):
            seen: dict[tuple, int] = {}
            for r, h in zip(ref_rows, heights):
                c = cond.get(r["trial"])
                if c and c["footwear"] == g:
                    dim = c["lighting"] == "dim"
                    key = (dim, round(h, 1))
                    k = seen.get(key, 0)
                    seen[key] = k + 1          # spread identical (frame-quantised) values sideways
                    x = gi + (0.18 if dim else -0.12) + 0.09 * k
                    ax.scatter(x, h, s=20, color=WARN if dim else ACCENT,
                               marker="s" if dim else "o", zorder=3)
        ax.scatter([], [], color=ACCENT, s=18, label="normal light")
        ax.scatter([], [], color=WARN, marker="s", s=18, label="dim light")
        ax.set_xticks(range(len(groups)), groups)
        ax.set(ylabel="Height (cm)", title="By recording condition", xlim=(-0.6, 2.6))
        ax.legend(frameon=False, fontsize=7, loc="lower right")
    fig.savefig(out / "fig_jump_heights.png", dpi=200)
    plt.close(fig)

    # Detector example: score trace with reference events
    example = "jump_01"
    ref = next(r for r in ref_rows if r["trial"] == example)
    s = np.asarray(score_traces[example])
    fig, ax = plt.subplots(figsize=(7.2, 2.5), constrained_layout=True)
    ax.plot(np.arange(len(s)), s, color=INK, lw=0.9, label="SVM decision score (held-out model)")
    ax.axhline(0, color=MUTED, lw=1)
    ax.axvspan(ref["takeoff_frame"], ref["landing_frame"], color=ACCENT, alpha=0.12,
               label="Annotated flight phase")
    ax.set(xlabel="Frame index (≈60 fps)", ylabel="Score  (+ contact / − flight)",
           title=f"{example}: frame-by-frame contact score from the leave-one-video-out model")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    fig.savefig(out / "fig_detector_score_example.png", dpi=200)
    plt.close(fig)

    # Detector outcome per video
    fig, ax = plt.subplots(figsize=(7.2, 2.6), constrained_layout=True)
    lim = 6
    ax.axhspan(-1, 1, color=OK, alpha=0.08, lw=0)
    for i, r in enumerate(lovo_rows):
        errs = [r["takeoff_error_frames"], r["landing_error_frames"]]
        if r["status"] == "accepted" and max(abs(float(e)) for e in errs) > 10:
            ax.annotate(f"wrong jump\n({errs[0]:+}/{errs[1]:+})", xy=(i, lim - 0.3), ha="center", va="top",
                        fontsize=6.5, color=WARN)
            ax.scatter(i, lim - 0.15, marker="^", color=WARN, s=26)
        elif r["status"] == "accepted":
            ax.scatter(i, r["takeoff_error_frames"], marker="^", color=ACCENT, s=22,
                       label="Take-off error" if i == 0 else None)
            ax.scatter(i, r["landing_error_frames"], marker="v", color=OK, s=22,
                       label="Landing error" if i == 0 else None)
        else:
            ax.scatter(i, 0, marker="x", color=WARN, s=30)
    if any(r["status"] != "accepted" for r in lovo_rows):
        ax.scatter([], [], marker="x", color=WARN, label="Rejected → manual review")
    ax.set_xticks(range(len(lovo_rows)), [r["trial"].replace("jump_", "J") for r in lovo_rows],
                  fontsize=7, rotation=90)
    ax.set(ylabel="Detected − annotated (frames)", ylim=(-lim, lim),
           title="Event errors on unseen videos (leave-one-video-out); green band = ±1 frame")
    ax.legend(frameon=False, fontsize=7, ncol=3, loc="lower left")
    fig.savefig(out / "fig_detector_lovo.png", dpi=200)
    plt.close(fig)

    # Key frames of one jump with the detector ROI
    video = ROOT / ref["video"]
    frames = [(ref["takeoff_frame"] - 30, "Squat position"),
              (ref["takeoff_frame"] - 1, "Last contact"),
              (ref["takeoff_frame"], "Take-off (1st flight frame)"),
              ((ref["takeoff_frame"] + ref["landing_frame"]) // 2, "Mid-flight"),
              (ref["landing_frame"], "Landing (1st contact frame)")]
    fig, axes = plt.subplots(1, len(frames), figsize=(7.2, 1.9), constrained_layout=True)
    for ax, (idx, label) in zip(axes, frames):
        img = extract_frame(video, idx)
        h, w = img.shape[:2]
        x, y, rw, rh = roi
        cv2.rectangle(img, (int(x * w) + 2, int(y * h)), (int((x + rw) * w) - 3, min(h, int((y + rh) * h)) - 3),
                      (40, 200, 255), 3)
        ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        ax.set_title(f"{label}\nframe {idx}", fontsize=7)
        ax.axis("off")
    fig.savefig(out / "fig_jump_keyframes.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()
