#!/usr/bin/env python3
"""Raspberry Pi 3B+ squat-jump recorder and analysis pipeline.

Hardware: Raspberry Pi Camera Module V2.1, momentary button GPIO-to-GND.
Run from a terminal on Raspberry Pi OS with Picamera2 installed.
"""
import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from gpiozero import Button
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput

from detector import detect_events, load_config, select_manual_events
from mechanics import calculate_metrics
from report import write_report, make_annotated_video


def prompt_positive(prompt, unit):
    while True:
        try:
            value = float(input(f"{prompt} ({unit}): ").strip().replace(",", "."))
            if math.isfinite(value) and value > 0:
                return value
        except ValueError:
            pass
        print("Please enter a positive number.")


class TimestampLog:
    """Thread-safe per-frame metadata log populated by Picamera2.post_callback."""
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.rows = []
        self.callback_errors = 0

    def callback(self, request):
        try:
            md = request.get_metadata()
            ts = md.get("SensorTimestamp", None)  # nanoseconds, monotonic sensor clock
            with self.lock:
                self.rows.append({
                    "callback_index": len(self.rows),
                    "sensor_timestamp_ns": int(ts) if ts is not None else "",
                    "frame_duration_us": md.get("FrameDuration", ""),
                    "analogue_gain": md.get("AnalogueGain", ""),
                    "exposure_time_us": md.get("ExposureTime", ""),
                })
        except Exception:
            self.callback_errors += 1

    def save(self):
        with self.lock:
            rows = list(self.rows)
        with self.path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "callback_index", "sensor_timestamp_ns", "frame_duration_us",
                "analogue_gain", "exposure_time_us"
            ])
            writer.writeheader()
            writer.writerows(rows)
        return len(rows)


def remux_h264(h264_path, mp4_path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("WARNING: ffmpeg not found; leaving .h264 file. Install ffmpeg to create MP4.")
        return None
    # Use the nominal frame rate only for container playback timing. Sensor timestamps
    # remain the source of truth for measured flight time.
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-framerate", "60",
           "-i", str(h264_path), "-c", "copy", str(mp4_path)]
    try:
        subprocess.run(cmd, check=True)
        return mp4_path
    except subprocess.CalledProcessError:
        print("WARNING: ffmpeg remux failed; leaving .h264 file.")
        return None


def record_one(picam2, button, output_dir, config):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session = output_dir / f"jump_{stamp}"
    session.mkdir(parents=True, exist_ok=False)
    h264_path = session / "recording.h264"
    timestamp_path = session / "timestamps.csv"
    log = TimestampLog(timestamp_path)

    encoder = H264Encoder(bitrate=8_000_000)
    output = FileOutput(str(h264_path))

    print("\nREADY. Press the button once to START recording.")
    while not button.is_pressed:
        time.sleep(0.01)
    # Debounce and wait for release so a held button cannot trigger the stop.
    time.sleep(0.06)
    while button.is_pressed:
        time.sleep(0.01)

    print("RECORDING... Press the button again to STOP.")
    # Start metadata capture at the same boundary as encoded video. Logging
    # during the pre-recording wait shifts the sidecar out of frame alignment.
    picam2.post_callback = log.callback
    picam2.start_recording(encoder, output)
    while not button.is_pressed:
        time.sleep(0.01)
    time.sleep(0.06)
    while button.is_pressed:
        time.sleep(0.01)
    picam2.stop_recording()
    picam2.post_callback = None
    n = log.save()
    print(f"Recording stopped. Timestamp callbacks logged: {n}")
    mp4_path = session / "recording.mp4"
    video_path = remux_h264(h264_path, mp4_path) or h264_path
    return session, video_path, timestamp_path


def run_analysis(video_path, timestamp_path, session, mass_kg, push_cm, config):
    print("Analysing video...")
    result = detect_events(str(video_path), str(timestamp_path), config)
    if not result.get("ok"):
        print("Automatic event detection did not produce a confident result.")
        print(result.get("message", "No further details."))
        print("Opening manual event review. Select take-off and landing, then accept.")
        manual_result = select_manual_events(str(video_path), str(timestamp_path), config)
        if not manual_result.get("ok"):
            result["body_mass_kg"] = mass_kg
            result["push_off_distance_cm"] = push_cm
            result["analysis_status"] = "EVENT_DETECTION_FAILED"
            write_report(session, result, None)
            print(manual_result.get("message", "Manual event selection failed."))
            print(f"Review files in: {session}")
            return
        result = manual_result

    metrics = calculate_metrics(
        flight_time_s=result["flight_time_s"],
        mass_kg=mass_kg,
        push_off_distance_m=push_cm / 100.0,
    )
    result.update(metrics)
    result["body_mass_kg"] = mass_kg
    result["push_off_distance_cm"] = push_cm
    result["analysis_status"] = (
        "OK_WITH_MANUAL_EVENTS" if result.get("detection_method") == "manual"
        else "OK_WITH_REVIEW_REQUIRED"
    )
    annotated = session / "annotated_review.mp4"
    make_annotated_video(str(video_path), annotated, result)
    write_report(session, result, annotated)
    print("\n=== AUTOMATIC RESULT (review the event frames) ===")
    for key, label, unit in [
        ("flight_time_s", "Flight time", "s"),
        ("jump_height_m", "Jump height", "m"),
        ("takeoff_velocity_m_s", "Take-off COM velocity", "m/s"),
        ("mean_push_force_N", "Mean vertical force during push-off", "N"),
        ("mean_push_velocity_m_s", "Mean COM velocity during push-off", "m/s"),
        ("mean_push_power_W", "Mean push-off power", "W"),
        ("mean_push_power_W_kg", "Mean push-off power per kg", "W/kg"),
    ]:
        print(f"{label}: {result[key]:.4f} {unit}")
    print(f"\nReview video: {annotated}")
    print(f"Results: {session / 'results.json'}")
    print("NOTE: automatic results are provisional until event detections are visually verified.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="jump_data", help="Output folder")
    parser.add_argument("--config", default="config.json", help="Detector config JSON")
    parser.add_argument("--gpio", type=int, default=17, help="BCM GPIO number for button")
    parser.add_argument("--once", action="store_true", help="Record and analyse one jump, then exit")
    args = parser.parse_args()

    mass = prompt_positive("Subject body mass", "kg")
    push_cm = prompt_positive("Push-off distance", "cm")
    config = load_config(args.config)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(
        main={"size": (640, 480), "format": "YUV420"},
        controls={"FrameDurationLimits": (16667, 16667)},
        buffer_count=6,
    )
    picam2.configure(video_config)
    picam2.start()
    time.sleep(2.0)

    button = Button(args.gpio, pull_up=True, bounce_time=0.08)
    print("Camera initialised at requested 640x480 / ~60 fps.")
    print("Actual achieved rate and timestamps must be checked in timestamps.csv.")
    try:
        while True:
            session, video_path, timestamp_path = record_one(picam2, button, out, config)
            run_analysis(video_path, timestamp_path, session, mass, push_cm, config)
            if args.once:
                break
            print("\nPress Ctrl+C to exit, or wait for the next jump.")
    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        try:
            picam2.stop()
        except Exception:
            pass
        button.close()


if __name__ == "__main__":
    main()
