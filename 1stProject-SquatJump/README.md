# Raspberry Pi squat-jump recorder and analysis prototype

The historical SquatJump project name is retained. Victor identifies the twenty training trials as CMJs by Joël, hands on hips. The current branch requires explicit review of every automatic proposal. Seven original session exports are documented in [JUMP_SESSIONS.md](../docs/JUMP_SESSIONS.md). Corrected code has not been retested on Raspberry Pi; use the [root instructions](../README.md) for offline work.

This is a **research prototype**, not a validated measurement instrument. The camera is front-facing, so the lower ROI must show both feet and the ground line throughout the movement. Very poor lighting, occlusion, and camera framing can make event detection fail. Always visually check `annotated_review.mp4` before accepting a result.

## Hardware

- Raspberry Pi 3B+
- Raspberry Pi Camera Module V2.1
- Momentary push button between BCM GPIO 17 and GND
- Raspberry Pi OS with the Picamera2/libcamera stack
- Stable power supply and sufficient free storage

The GPIO pin number is BCM 17 by default (physical pin 11). The program uses the internal pull-up. Do not connect 3.3 V or 5 V to the GPIO pin.

## Install

On Raspberry Pi OS, install the camera stack and system packages first:

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-opencv ffmpeg python3-gpiozero
```

If using a virtual environment, create it with system packages enabled so Picamera2 is visible:

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If `pip install opencv-python` conflicts with the system OpenCV on your Pi, remove it from `requirements.txt` and use `python3-opencv` from apt. Avoid upgrading the system-managed Picamera2 stack with pip.

## Camera and button test

Check the camera works before running the program:

```bash
rpicam-hello --timeout 5000
```

Depending on the Raspberry Pi OS version, the command may be named `libcamera-hello`.

Run one recording:

```bash
python3 main.py --once
```

Enter body mass in kg and push-off distance in cm. The first button press starts recording; the second stops it. Data are saved in a timestamped folder under `jump_data/`.

The camera is configured for 640x480 with a requested 16,667 microsecond frame duration. This is a request, not a guarantee. Check `timestamps.csv` for timestamp gaps, callback counts and frame durations. H.264 is remuxed to MP4 with ffmpeg for playback; `recording.h264` is retained. The timestamp sidecar is generated from Picamera2 request metadata during the recording window. If timestamp count does not match decoded video frames, the current implementation deliberately falls back to nominal 60 fps and labels that source in results. **Do not treat that fallback as equivalent to verified sensor timing.**

## Detector setup and training

The event detector requires `contact_model.joblib`. The model included here was trained on our 20 videos (`training_dataset/`, `annotations.csv`); it fits our camera, floor, footwear and lighting only, so retrain it for any new set-up with the steps below.

1. Record a set of representative videos using the final camera placement.
2. Make sure the ROI covers both feet and the ground. Edit `roi_norm` in `config.json`. Values are normalized `[x, y, width, height]`, from 0 to 1. The default ROI starts at 62 % of the image height and covers the bottom of the frame (about the lower 38 %).
3. Create a CSV with columns `video_path,frame_index,label`, using labels `CONTACT` or `FLIGHT`. Label frames around both transitions and sample throughout the flight/contact phases. Include examples from every lighting condition.
4. Train:

```bash
mkdir -p outputs
python3 train_contact_model.py annotations.csv --config config.json --out outputs/contact_model_candidate.joblib
```

The included model is a basic linear SVM over normalized grayscale ROI pixels with modest brightness augmentation. It is a baseline only; it is not guaranteed to be robust in poor lighting. For 20 videos, split evaluation by whole video, not by randomly splitting adjacent frames. Do not report training accuracy as generalisation performance.

## Important annotation convention

For a bilateral jump, define take-off as the first frame where neither foot touches the ground, and landing as the first frame where either foot touches the ground again. Apply the same convention in every annotation. If you instead define take-off by the first foot leaving, record that alternative explicitly; it changes the measured event time.

## Output files

- `recording.h264` and `recording.mp4`
- `timestamps.csv` with camera metadata timestamps when available
- `results.json` and `results.csv`
- `annotated_review.mp4`

The annotated video marks the detected frame indices. It is a quality-control aid, not proof that the detector is correct.

## Manual event review

Every automatic proposal requires explicit operator review before mechanical calculations are run. The proposal is saved separately before the existing review window opens, including when automatic detection fails. Drag the `Frame` trackbar to any frame, or use `n`/Right Arrow and `p`/Left Arrow for frame-by-frame review. Click `TAKE-OFF` on the first frame where neither foot touches the ground, then click `LANDING` on the first frame where either foot touches the ground again. Click `ACCEPT` to calculate and report the result, or `CANCEL`/Escape to leave the analysis pending without accepted mechanical metrics. The output retains `automatic_proposal`, records the review decision and accepted `confirmed_events`, and labels reviewed events in the annotated video. Software test fixtures are not actual scientific reviews.

Manual review requires a graphical display because it uses OpenCV HighGUI. If the Raspberry Pi is operated headlessly over SSH, run the review locally with a display or use an X11/VNC session.

## Mechanical interpretation

For flight time T, mass m, push-off distance d and g = 9.81 m/s²:

- Jump height: h = g T² / 8
- Take-off COM velocity: v = g T / 2
- Mean vertical force: F = m g (1 + h/d)
- Mean push-off COM velocity under constant acceleration from rest: v_mean = v/2
- Mean push-off power estimate: P = F v_mean

The flight-time equation assumes vertical ballistic motion and equal COM heights at take-off and landing. Force and power are model-derived estimates, not direct force-plate measurements. The mean force equation depends strongly on the supplied push-off distance.

## Limitations and recommended next steps

- The first version uses one fixed ROI. If the participant moves sideways, feet leave the ROI, or the floor line is not visible, detection may fail.
- The SVM score is not a calibrated probability. Do not interpret it as a confidence percentage.
- Video frame index and camera callback timestamp index may not map one-to-one on every Picamera2/encoder configuration. This prototype checks counts and falls back to nominal fps if they differ. For a study-grade implementation, validate timestamp/frame alignment experimentally and consider recording frames with their own timestamps or using a camera/encoder pipeline that preserves frame PTS.
- A nominal 60 fps video has about 16.7 ms frame spacing. Verify actual timing and quantify event-detection errors against manual labels.
- Before using results for research or clinical decisions, validate event timing on held-out videos under the actual range of lighting and footwear.

For file-only review with a new output directory, follow [MANUAL_REVIEW.md](../docs/MANUAL_REVIEW.md). Actual GUI navigation, correction, acceptance, export and cancellation remain pending. The 31 cm input has no verified measurement definition; force and power remain conditional estimates for the declared CMJ protocol.
