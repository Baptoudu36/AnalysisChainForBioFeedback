#!/usr/bin/env python3
"""Train a simple HOG-like pixel SVM contact classifier from frame annotations.

Annotation CSV columns:
video_path,frame_index,label
label must be CONTACT or FLIGHT.
Use a fixed camera and the same ROI for every video. Annotate frames across videos,
especially near take-off and landing, with a mixture of lighting and footwear.
"""
import argparse
import csv
from pathlib import Path

import cv2
import numpy as np
import joblib
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

from detector import crop_roi, load_config


def extract_frame(video, frame_index):
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise ValueError(f"Could not read frame {frame_index} from {video}")
    return frame


def feature(frame, roi_norm):
    crop = crop_roi(frame, roi_norm)
    if crop.size == 0:
        raise ValueError("ROI is empty; update roi_norm in config.json.")
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (320, 96), interpolation=cv2.INTER_AREA)
    # Small brightness/contrast perturbations are performed during training.
    return gray.reshape(-1).astype(np.float32) / 255.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("annotations_csv", help="CSV with video_path,frame_index,label")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--out", default="contact_model.joblib")
    args = ap.parse_args()
    config = load_config(args.config)

    X, y = [], []
    with open(args.annotations_csv, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit("Annotation CSV is empty.")
    for row in rows:
        label = row["label"].strip().upper()
        if label not in ("CONTACT", "FLIGHT"):
            raise ValueError(f"Invalid label {label}; use CONTACT or FLIGHT.")
        frame = extract_frame(row["video_path"], int(row["frame_index"]))
        base = feature(frame, config["roi_norm"])
        X.append(base)
        y.append(1 if label == "CONTACT" else -1)
        # Conservative illumination augmentation on normalized grayscale pixels.
        img = np.clip(base.reshape(96, 320) * 0.75, 0, 1).reshape(-1)
        X.append(img)
        y.append(1 if label == "CONTACT" else -1)
        img = np.clip(base.reshape(96, 320) * 1.20 + 0.04, 0, 1).reshape(-1)
        X.append(img)
        y.append(1 if label == "CONTACT" else -1)

    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y, dtype=np.int32)
    if len(np.unique(y)) != 2:
        raise SystemExit("Need examples of both CONTACT and FLIGHT.")
    model = make_pipeline(
        StandardScaler(),
        LinearSVC(class_weight="balanced", C=0.1, max_iter=10000, random_state=42)
    )
    model.fit(X, y)
    # detector expects positive score = CONTACT. LinearSVC class order is [-1, +1].
    joblib.dump(model, args.out)
    print(f"Saved model to {args.out}")
    print(f"Training crops: {len(y)} (augmented from {len(rows)} annotated frames)")
    print("Important: training accuracy is not a validation result. Hold out entire videos")
    print("and report event timing errors before using this for research/clinical decisions.")


if __name__ == "__main__":
    main()
