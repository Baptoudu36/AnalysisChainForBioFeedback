#!/usr/bin/env python3
"""
Overview of the recording conditions in the 20-video training dataset.

Footwear was categorised visually from the videos (barefoot / shoes / socks);
brightness is the mean grey level (0-255) of the detector ROI over all frames.
Writes analysis/output/dataset_conditions.csv and the report figure fig_dataset_overview.jpg.
"""
import csv
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "output"
FIG = ROOT.parent / "Report" / "Figures of the final report"

# Visual categorisation (checked frame by frame by the group's report author).
FOOTWEAR = {**{k: "barefoot" for k in (1, 2, 3)},
            **{k: "shoes" for k in (4, 5, 6, 7, 8, 9, 19, 20)},
            **{k: "socks" for k in (10, 11, 12, 13, 14, 15, 16, 17, 18)}}


def roi_brightness(video, roi):
    cap = cv2.VideoCapture(str(video))
    values = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        h, w = frame.shape[:2]
        x, y, rw, rh = roi
        crop = frame[int(y * h):min(h, int((y + rh) * h)), int(x * w):int((x + rw) * w)]
        values.append(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).mean())
    cap.release()
    return float(np.mean(values))


def main():
    import json
    roi = json.loads((ROOT / "config.json").read_text())["roi_norm"]
    OUT.mkdir(parents=True, exist_ok=True)
    rows, tiles = [], []
    for k in range(1, 21):
        video = ROOT / "training_dataset" / f"jump_{k:02d}.mp4"
        b = roi_brightness(video, roi)
        rows.append({"trial": f"jump_{k:02d}", "footwear": FOOTWEAR[k], "roi_mean_grey_level": round(b, 1),
                     "lighting": "dim" if b < 70 else "normal"})
        cap = cv2.VideoCapture(str(video))
        cap.set(cv2.CAP_PROP_POS_FRAMES, 30)
        ok, frame = cap.read()
        cap.release()
        frame = cv2.resize(frame, (256, 192), interpolation=cv2.INTER_AREA)
        cv2.rectangle(frame, (0, 0), (256, 26), (255, 255, 255), -1)
        cv2.putText(frame, f"J{k:02d} {FOOTWEAR[k]} | grey {b:.0f}", (6, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 30, 30), 1, cv2.LINE_AA)
        tiles.append(frame)
    with (OUT / "dataset_conditions.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    sheet = np.vstack([np.hstack(tiles[i:i + 5]) for i in range(0, 20, 5)])
    FIG.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(FIG / "fig_dataset_overview.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
