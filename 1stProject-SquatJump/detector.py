"""Contact event detector.

Train a model using train_contact_model.py before relying on automatic detections.
The classifier uses a fixed foot/ground ROI. Front-view recordings require both feet
and the ground-contact region to remain visible within that ROI.
"""
import csv
import json
from pathlib import Path

import cv2
import numpy as np

DEFAULT_CONFIG = {
    "roi_norm": [0.0, 0.62, 1.0, 0.40],  # x, y, width, height in normalized coordinates
    "model_path": "contact_model.joblib",
    "smooth_window": 5,
    "min_flight_frames": 3,
    "min_contact_frames": 3,
    "min_confidence_margin": 0.15,
    "expected_fps": 60.0
}


def load_config(path):
    p = Path(path)
    if not p.exists():
        p.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        print(f"Created default config: {p}. Review roi_norm for your camera framing.")
        return dict(DEFAULT_CONFIG)
    data = json.loads(p.read_text())
    merged = dict(DEFAULT_CONFIG)
    merged.update(data)
    return merged


def crop_roi(frame, roi_norm):
    h, w = frame.shape[:2]
    x, y, rw, rh = roi_norm
    x1, y1 = int(x*w), int(y*h)
    x2, y2 = int((x+rw)*w), int((y+rh)*h)
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    return frame[y1:y2, x1:x2]


def read_timestamps(path):
    if not Path(path).exists():
        return []
    values = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            v = row.get("sensor_timestamp_ns", "")
            try:
                values.append(int(v))
            except (ValueError, TypeError, OverflowError):
                values.append(None)
    return values


def _event_timing(takeoff_idx, landing_idx, frame_count, timestamp_path, config):
    """Validate the entire sidecar; matching counts do not prove physical alignment."""
    if (not isinstance(frame_count, (int, np.integer)) or frame_count < 2
            or not isinstance(takeoff_idx, (int, np.integer))
            or not isinstance(landing_idx, (int, np.integer))
            or not 0 <= takeoff_idx < landing_idx < frame_count):
        return None
    try:
        fps = float(config["expected_fps"])
    except (KeyError, ValueError, TypeError):
        return None
    if not np.isfinite(fps) or fps <= 0:
        return None
    try:
        timestamps = read_timestamps(timestamp_path)
        reason = ("timestamps_missing_or_empty" if not timestamps else
                  "timestamp_frame_count_mismatch" if len(timestamps) != frame_count else
                  "timestamp_invalid_or_nonfinite" if any(t is None for t in timestamps) else
                  "timestamps_not_strictly_increasing" if any(b <= a for a, b in zip(timestamps, timestamps[1:])) else None)
    except (OSError, csv.Error, UnicodeError):
        timestamps, reason = [], "timestamps_unreadable"
    timestamp_source = "nominal_frame_rate_fallback"
    if reason is None:
        flight_time = (timestamps[landing_idx] - timestamps[takeoff_idx]) / 1e9
        timestamp_source = "sensor_timestamp_ns"
    else:
        flight_time = (landing_idx - takeoff_idx) / fps
    if not np.isfinite(flight_time) or flight_time <= 0:
        return None
    fps = float(config["expected_fps"])
    return {
        "takeoff_frame_index": int(takeoff_idx),
        "landing_frame_index": int(landing_idx),
        "takeoff_video_time_s": float(takeoff_idx / fps),
        "landing_video_time_s": float(landing_idx / fps),
        "flight_time_s": float(flight_time),
        "timestamp_source": timestamp_source,
        "timestamp_fallback_reason": reason,
        "timestamp_samples": len(timestamps),
        "timestamp_alignment": "unverified_physical_alignment",
        "timestamp_alignment_note": "Count, finite values and monotonicity are software checks only; sensor-to-encoded-frame alignment is not independently established.",
        "video_time_source": "nominal_frame_rate",
        "frames_decoded": int(frame_count),
    }


def select_manual_events(video_path, timestamp_path, config, proposal=None):
    """Let an operator mark take-off and landing in an OpenCV review window."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"ok": False, "message": f"Cannot open video for manual review: {video_path}"}

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if frame_count < 2:
        cap.release()
        return {"ok": False, "message": "Video is too short for manual event selection."}

    window = "Manual jump event review"
    proposal = proposal or {}
    state = {"index": proposal.get("takeoff_frame_index", 0),
             "takeoff": proposal.get("takeoff_frame_index"),
             "landing": proposal.get("landing_frame_index"), "accept": False, "cancel": False}
    button_positions = []
    try:
        cv2.namedWindow(window, cv2.WINDOW_AUTOSIZE)
    except cv2.error:
        cap.release()
        raise

    def on_frame(value):
        state["index"] = int(value)

    cv2.createTrackbar("Frame", window, 0, frame_count - 1, on_frame)
    cv2.setTrackbarPos("Frame", window, min(frame_count - 1, int(proposal.get("takeoff_frame_index", 0))))

    def on_mouse(event, x, y, _flags, _param):
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        button_y = display_height - 55
        if button_y <= y < display_height - 8:
            if button_positions and button_positions[0][0] <= x < button_positions[0][1]:
                state["takeoff"] = state["index"]
            elif button_positions and button_positions[1][0] <= x < button_positions[1][1]:
                state["landing"] = state["index"]
            elif (button_positions and button_positions[2][0] <= x < button_positions[2][1]
                  and state["takeoff"] is not None and state["landing"] is not None):
                state["accept"] = True
            elif button_positions and button_positions[3][0] <= x < button_positions[3][1]:
                state["cancel"] = True

    cv2.setMouseCallback(window, on_mouse)
    display_height = 0
    try:
        while not state["accept"] and not state["cancel"]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, state["index"])
            ok, frame = cap.read()
            if not ok:
                state["cancel"] = True
                break

            max_width = 1100
            scale = min(1.0, max_width / frame.shape[1])
            width = max(1, int(frame.shape[1] * scale))
            height = max(1, int(frame.shape[0] * scale))
            image = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
            display_height = height + 75
            canvas = np.zeros((display_height, width, 3), dtype=np.uint8)
            canvas[:height] = image
            cv2.putText(canvas, f"Frame {state['index']}/{frame_count - 1}", (15, height + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (240, 240, 240), 1)
            status = f"Take-off: {state['takeoff']}   Landing: {state['landing']}"
            cv2.putText(canvas, status, (15, height + 43), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (240, 240, 240), 1)
            button_width = max(1, (width - 75) // 4)
            button_positions = []
            buttons = [
                ("TAKE-OFF", state["takeoff"] is not None),
                ("LANDING", state["landing"] is not None),
                ("ACCEPT", state["takeoff"] is not None and state["landing"] is not None),
                ("CANCEL", True),
            ]
            for button_index, (label, enabled) in enumerate(buttons):
                x = 15 + button_index * (button_width + 10)
                button_positions.append((x, x + button_width))
                color = (40, 150, 40) if enabled else (80, 80, 80)
                cv2.rectangle(canvas, (x, height + 10), (x + button_width, height + 57), color, -1)
                text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)[0]
                text_x = x + (button_width - text_size[0]) // 2
                cv2.putText(canvas, label, (text_x, height + 40), cv2.FONT_HERSHEY_SIMPLEX,
                            0.45, (255, 255, 255), 1)
            cv2.imshow(window, canvas)
            key = cv2.waitKey(30) & 0xFF
            if key in (27, ord("q")):
                state["cancel"] = True
            elif key in (ord("t"), ord("T")):
                state["takeoff"] = state["index"]
            elif key in (ord("l"), ord("L")):
                state["landing"] = state["index"]
            elif key in (ord("a"), 13) and state["takeoff"] is not None and state["landing"] is not None:
                state["accept"] = True
            elif key in (ord("n"), 83):
                next_index = min(frame_count - 1, state["index"] + 1)
                cv2.setTrackbarPos("Frame", window, next_index)
            elif key in (ord("p"), 81):
                previous_index = max(0, state["index"] - 1)
                cv2.setTrackbarPos("Frame", window, previous_index)
    finally:
        cap.release()
        cv2.destroyWindow(window)

    if state["cancel"]:
        return {"ok": False, "message": "Manual event selection cancelled."}
    if state["takeoff"] is None or state["landing"] is None:
        return {"ok": False, "message": "Both take-off and landing frames are required."}
    if state["takeoff"] >= state["landing"]:
        return {"ok": False, "message": "Take-off must occur before landing."}

    timing = _event_timing(state["takeoff"], state["landing"], frame_count,
                           timestamp_path, config)
    if timing is None:
        return {"ok": False, "message": "Computed manual flight time is invalid."}
    timing.update({
        "ok": True,
        "detection_method": "manual",
        "detection_note": "Operator explicitly accepted the reviewed event frames; not independent biomechanical validation.",
    })
    return timing


def detect_events(video_path, timestamp_path, config):
    model_path = Path(config["model_path"])
    if not model_path.exists():
        return {
            "ok": False,
            "message": (
                f"No trained contact model found at {model_path}. "
                "Annotate representative videos and run train_contact_model.py first. "
                "Do not use a guessed event time for scientific results."
            ),
        }

    try:
        import joblib
        model = joblib.load(model_path)
    except Exception as e:
        return {"ok": False, "message": f"Could not load contact model: {e}"}

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"ok": False, "message": f"Cannot open video: {video_path}"}

    roi_norm = config["roi_norm"]
    scores = []
    frame_indices = []
    index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        crop = crop_roi(frame, roi_norm)
        if crop.size == 0:
            cap.release()
            return {"ok": False, "message": "ROI is empty; correct roi_norm in config.json."}
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (320, 96), interpolation=cv2.INTER_AREA)
        # Models are trained on flattened grayscale crops; normalize identically.
        feature = gray.reshape(1, -1).astype(np.float32) / 255.0
        if hasattr(model, "decision_function"):
            score = float(np.ravel(model.decision_function(feature))[0])
        else:
            prob = model.predict_proba(feature)[0]
            classes = list(model.classes_)
            score = float(prob[classes.index("CONTACT")] - prob[classes.index("FLIGHT")])
        scores.append(score)
        frame_indices.append(index)
        index += 1
    cap.release()

    if len(scores) < 10:
        return {"ok": False, "message": "Video is too short or no frames could be decoded."}

    scores = np.asarray(scores, dtype=float)
    win = max(1, int(config["smooth_window"]))
    if win % 2 == 0:
        win += 1
    kernel = np.ones(win, dtype=float) / win
    # Reflect at the ends instead of zero-padding, which can create false
    # flight states when a recording starts or ends during contact.
    pad = win // 2
    padded = np.pad(scores, (pad, pad), mode="edge")
    smooth = np.convolve(padded, kernel, mode="valid")
    # Training convention: CONTACT is positive; FLIGHT is negative.
    flight = smooth < 0
    min_flight = int(config["min_flight_frames"])
    min_contact = int(config["min_contact_frames"])

    # Find a stable contact -> flight -> contact sequence. Pick the first frame
    # of the stable flight run and first frame of the stable landing-contact run.
    runs = []
    start = 0
    for i in range(1, len(flight) + 1):
        if i == len(flight) or flight[i] != flight[start]:
            runs.append((bool(flight[start]), start, i - 1, i - start))
            start = i
    candidates = []
    for j in range(1, len(runs)-1):
        prev_run, flight_run, next_run = runs[j-1], runs[j], runs[j+1]
        if (not prev_run[0] and flight_run[0] and not next_run[0]
                and flight_run[3] >= min_flight and next_run[3] >= min_contact):
            takeoff_idx = flight_run[1]
            landing_idx = next_run[1]
            flight_margin = abs(float(np.mean(smooth[flight_run[1]:flight_run[2] + 1])))
            contact_margin = abs(float(np.mean(smooth[next_run[1]:next_run[2] + 1])))
            margin = float(min(flight_margin, contact_margin))
            candidates.append((margin, prev_run, flight_run, next_run))
    if not candidates:
        return {
            "ok": False,
            "message": "No clear stable contact → flight → contact sequence detected. Check ROI, labels, framing and model.",
            "frames_decoded": len(scores),
        }

    min_margin = float(config["min_confidence_margin"])
    candidates = [candidate for candidate in candidates if candidate[0] >= min_margin]
    if not candidates:
        return {
            "ok": False,
            "message": (
                "A contact → flight → contact sequence was found, but the event "
                "score margin is too small for automatic acceptance. Visually review "
                "the video or improve the training set."
            ),
            "frames_decoded": len(scores),
        }

    # Prefer the clearest complete jump instead of whichever noisy transition
    # happens to occur first in a long recording.
    stable_margin, prev_run, flight_run, next_run = max(
        candidates, key=lambda candidate: candidate[0]
    )
    takeoff_idx = flight_run[1]
    landing_idx = next_run[1]
    timing = _event_timing(takeoff_idx, landing_idx, len(scores), timestamp_path, config)
    if timing is None:
        return {"ok": False, "message": "Computed flight time is invalid; inspect timestamp alignment."}

    # Neither value is a calibrated probability. The stable margin selects a
    # proposal; explicit operator review is required before acceptance.
    transition_margin = float(min(abs(smooth[takeoff_idx]), abs(smooth[landing_idx])))
    timing.update({
        "ok": True,
        "detection_method": "automatic",
        "review_status": "required",
        "analysis_status": "REVIEW_REQUIRED",
        "event_score_margin": float(stable_margin),
        "transition_score_margin": transition_margin,
        "detection_note": (
            "SVM score margins are not calibrated probabilities. Visually verify "
            "the annotated take-off and landing frames before accepting the result."
        ),
    })
    return timing


def review_events(video_path, timestamp_path, config, proposal, reviewer=None):
    """Keep automatic evidence separate from an explicit human review decision."""
    reviewer = reviewer or select_manual_events
    try:
        reviewed = reviewer(video_path, timestamp_path, config, proposal=proposal if proposal.get("ok") else None)
    except cv2.error as exc:
        reviewed = {"ok": False, "message": "Manual review UI unavailable: " + str(exc)}
    if not reviewed.get("ok"):
        return {"ok": False, "analysis_status": "REVIEW_REQUIRED", "review_status": "pending",
                "automatic_proposal": dict(proposal), "review_message": reviewed.get("message", "Review not completed")}
    timing = _event_timing(reviewed.get("takeoff_frame_index"), reviewed.get("landing_frame_index"),
                           reviewed.get("frames_decoded"), timestamp_path, config)
    if timing is None:
        return {"ok": False, "analysis_status": "REVIEW_REQUIRED", "review_status": "pending",
                "automatic_proposal": dict(proposal), "review_message": "Invalid reviewed event indices or timing"}
    same = proposal.get("ok") and all(timing[k] == proposal.get(k) for k in ("takeoff_frame_index", "landing_frame_index"))
    status = "confirmed" if same else "corrected" if proposal.get("ok") else "manually_selected"
    timing.update(ok=True, detection_method="manual", review_status=status,
                  analysis_status="OK_WITH_REVIEWED_EVENTS", automatic_proposal=dict(proposal),
                  confirmed_events={k: timing[k] for k in ("takeoff_frame_index", "landing_frame_index", "flight_time_s")},
                  review_note="Explicit operator acceptance; not independent physical validation.")
    return timing
