#!/usr/bin/env python3
"""
Build the self-contained squat-jump dashboard (jump_dashboard.html).

Embeds analysis/output/dashboard_data.json (produced by
analysis/jump_dataset_analysis.py) and three small JPEG thumbnails per trial
(last contact, mid-flight, landing) into template.html, so the result opens
offline by double-click, with no server and no internet access.
"""
import base64
import json
from pathlib import Path

import cv2

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def thumb(video: Path, index: int, width: int = 220) -> str:
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(index))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return ""
    h = int(frame.shape[0] * width / frame.shape[1])
    ok, buf = cv2.imencode(".jpg", cv2.resize(frame, (width, h), interpolation=cv2.INTER_AREA),
                           [cv2.IMWRITE_JPEG_QUALITY, 72])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode()


def main():
    data = json.loads((ROOT / "analysis" / "output" / "dashboard_data.json").read_text())
    data["thumbs"] = {}
    for t in data["trials"]:
        video = ROOT / t["video"]
        mid = (t["takeoff_frame"] + t["landing_frame"]) // 2
        data["thumbs"][t["trial"]] = [
            [f"Last contact · {t['takeoff_frame'] - 1}", thumb(video, t["takeoff_frame"] - 1)],
            [f"Mid-flight · {mid}", thumb(video, mid)],
            [f"Landing · {t['landing_frame']}", thumb(video, t["landing_frame"])],
        ]
    html = (HERE / "template.html").read_text(encoding="utf-8")
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    out = HERE / "jump_dashboard.html"
    out.write_text(html.replace("/*__DATA__*/", payload), encoding="utf-8")
    print(f"Wrote {out} ({out.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
