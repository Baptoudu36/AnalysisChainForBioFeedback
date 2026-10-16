"""Report export and annotated video generation."""
import json
from pathlib import Path
import cv2


def write_report(session_dir, result, annotated_video):
    session = Path(session_dir)
    out = dict(result)
    if annotated_video:
        out["annotated_video"] = str(annotated_video)
    (session / "results.json").write_text(json.dumps(out, indent=2))
    with (session / "results.csv").open("w") as f:
        f.write("metric,value\n")
        for key, value in out.items():
            if isinstance(value, (int, float, str)) and not isinstance(value, bool):
                f.write(f'"{key}","{value}"\n')


def make_annotated_video(video_path, output_path, result):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps < 1 or fps > 240:
        fps = 60.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"),
                             fps, (width, height))
    method = result.get("detection_method", "automatic")
    method_label = "manual" if method == "manual" else "detected"
    takeoff = int(result["takeoff_frame_index"])
    landing = int(result["landing_frame_index"])
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx == takeoff:
            cv2.line(frame, (0, height//2), (width, height//2), (0, 255, 255), 2)
            cv2.putText(frame, f"TAKE-OFF ({method_label})", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        if idx == landing:
            cv2.putText(frame, f"LANDING ({method_label})", (20, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        if takeoff <= idx <= landing:
            cv2.putText(frame, f"Flight: {result['flight_time_s']:.4f} s",
                        (20, height-25), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (255, 255, 255), 2)
        writer.write(frame)
        idx += 1
    cap.release()
    writer.release()
