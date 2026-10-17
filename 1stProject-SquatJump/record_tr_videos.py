#!/usr/bin/env python3
"""
Records a 5-second 480p60 MP4 video on each press of a button (GPIO 17).
Uses rpicam-vid (hardware encoder) + mkvmerge (timestamp-correct muxing).
Saves as jump_[video_number].mp4 and repeats up to 20 times.
"""

import subprocess
import time
from pathlib import Path
from gpiozero import Button

# --- Configuration ---
BUTTON_PIN = 17
VIDEO_DURATION_MS = 5000     # milliseconds
MAX_RECORDINGS = 20
OUTPUT_DIR = Path("training_dataset")
TEMP_DIR = Path("tmp")

# Video parameters
WIDTH = 640
HEIGHT = 480
FRAMERATE = 60
BITRATE = 8000000            # 8 Mbps
LEVEL = "4.2"

# Create directories
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# --- Setup button ---
button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.1)

print("Ready. Press button to record jump_[n].mp4 (480p60).")
print(f"Will record up to {MAX_RECORDINGS} videos. Ctrl+C to exit.")


def record_video(mp4_path: Path) -> bool:
    """Record a 5s video with rpicam-vid, then mux to MP4 with timestamps."""
    h264_path = TEMP_DIR / f"{mp4_path.stem}.h264"
    pts_path = TEMP_DIR / f"{mp4_path.stem}.pts"
    mkv_path = TEMP_DIR / f"{mp4_path.stem}.mkv"

    # --- Step 1: Record raw H.264 with timestamps ---
    record_cmd = [
        "rpicam-vid",
        "--level", LEVEL,
        "--framerate", str(FRAMERATE),
        "--width", str(WIDTH),
        "--height", str(HEIGHT),
        "--denoise", "cdn_off",
        "--nopreview",
        "--bitrate", str(BITRATE),
        "--timeout", str(VIDEO_DURATION_MS),
        "--save-pts", str(pts_path),
        "--output", str(h264_path),
    ]

    print(f"  Running: {' '.join(record_cmd)}")
    result = subprocess.run(record_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ERROR: rpicam-vid failed:\n{result.stderr}")
        return False

    # --- Step 2: Mux H.264 + timestamps into MKV ---
    mux_cmd = [
        "mkvmerge",
        "-o", str(mkv_path),
        "--timecodes", f"0:{pts_path}",
        str(h264_path),
    ]

    print(f"  Running: {' '.join(mux_cmd)}")
    result = subprocess.run(mux_cmd, capture_output=True, text=True)

    if result.returncode not in (0, 1):  # mkvmerge returns 1 for warnings
        print(f"  ERROR: mkvmerge failed:\n{result.stderr}")
        return False

    # --- Step 3: Remux MKV to MP4 (copy streams, no re-encode) ---
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", str(mkv_path),
        "-c", "copy",
        "-movflags", "+faststart",
        str(mp4_path),
    ]

    print(f"  Running: {' '.join(ffmpeg_cmd)}")
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ERROR: ffmpeg failed:\n{result.stderr}")
        return False

    # --- Cleanup temp files ---
    for f in (h264_path, pts_path, mkv_path):
        try:
            f.unlink()
        except FileNotFoundError:
            pass

    return True


recording_count = 0

try:
    while recording_count < MAX_RECORDINGS:
        print(f"\n[Waiting for button... ({recording_count}/{MAX_RECORDINGS})]")
        button.wait_for_press()
        print("Button pressed! Recording...")

        video_number = recording_count + 1
        filename = OUTPUT_DIR / f"jump_{video_number}.mp4"

        success = record_video(filename)

        if success:
            print(f"  Saved: {filename}")
            recording_count += 1
        else:
            print(f"  Recording failed — not counted. Try again.")

        # Debounce: avoid re-triggering from the same press
        time.sleep(0.5)

    print(f"\nCompleted! Recorded {recording_count} videos.")
    print(f"Videos saved in: {OUTPUT_DIR.resolve()}")

except KeyboardInterrupt:
    print("\n\nInterrupted by user.")

finally:
    print("Done.")