# From Sensor to Feedback — Raspberry Pi measurement chains for squat-jump and ECG analysis

**University of Montpellier · UFR STAPS**
Master 2 of Sciences in Engineering Ergonomics of Physical Activity
Course: **Analysis Chain for Biofeedback**, taught by Gilles Despaux, academic year 2026–2027

**Students:** Baptiste Augros, Victor Salvat & Joël Singer

---

This repository contains the two measurement-and-analysis chains we built together on a **Raspberry Pi 3B+** during the 5 practical sessions (and beyond). It includes the code that ran on the Pi, the data it produced, the media we recorded, the offline analyses and two dashboards.

| | Project 1: Squat jump | Project 2: ECG |
|---|---|---|
| Sensors | Raspberry Pi Camera V2.1 + push button (GPIO 17) | 3 chest electrodes, analogue front-end |
| Digitisation | 640 × 480 video at 60 fps, per-frame timestamps | MCP3008 10-bit ADC, sampling frequency 800 Hz |
| Processing | Fixed ROI, linear SVM contact/flight classifier, event detection | 0.5–40 Hz band-pass, R-peak detection, RR and HR |
| Indicators | Flight time, jump height, take-off velocity, mean force, power, W/kg | Heart rate, RR intervals, PQRST candidates |
| Dashboard | **Squat Jump Explorer** (Baptiste) | **ECG Explorer** (Victor) |

📄 **Full report:** [`Report/Report-AnalysisChainforBiofeedback.docx`](Report/Report-AnalysisChainforBiofeedback.docx) (Word, editable)

## Key results

- **Squat jump, 20 hand-annotated trials** (same participant, 66 kg, 31 cm push-off): mean height 24.0 ± 2.5 cm and mean power 18.9 ± 1.8 W/kg. At 60 fps, one frame is worth about 1.8 cm of jump height.
- **Automatic jump detector, leave-one-video-out validation:** both events were within ±1 frame in 10 of 20 unseen videos. In one video (jump_07) the wrong jump was selected.
- **ECG, 16 Sep 2026 recording** (10 s, 800 Hz): 11 R peaks and a median heart rate of 73.1 bpm. 21 % of the raw signal power was 50 Hz mains interference; a notch filter brought out the P–QRS–T waves.
- **ECG, 6 Oct 2026 live demonstration** (DMA clock, v2.0.0): the sampling grid was exactly 800.000 Hz, but the input was saturated near the 3.3 V rail. The software caught it and refused to output a heart rate.

## Repository map

```
.
├── README.md
├── requirements.txt                    everything needed for the offline analyses
├── 1stProject-SquatJump/               Project 1 (copied as-is to the Pi Desktop)
│   ├── main.py                         record a jump (button start/stop) and analyse it
│   ├── detector.py                     contact/flight classifier + manual review window
│   ├── mechanics.py                    flight time → height, velocity, force, power
│   ├── report.py                       results.json / results.csv + annotated video
│   ├── record_tr_videos.py             records the 5-s training videos
│   ├── train_contact_model.py          trains contact_model.joblib from annotations.csv
│   ├── config.json  contact_model.joblib  requirements.txt  README.md
│   ├── training_dataset/               20 training videos (jump_01 … jump_20)
│   ├── annotations.csv                 168 hand-labelled frames (CONTACT / FLIGHT)
│   ├── annotations/                    photos of the lab-notebook annotations
│   ├── analysis/                       reference metrics, LOVO validation, dataset overview
│   │   └── output/                     CSV / JSON results used in the report
│   └── dashboard/
│       ├── jump_dashboard.html         Squat Jump Explorer (single offline file)
│       ├── template.html  build_dashboard.py   rebuild the dashboard from analysis/output
│       └── example_session_20261014_results.json   14 Oct demo session (to load in the dashboard)
├── 2ndProject-ECGAnalyzer/             Project 2
│   ├── ecg_lab_merged.py               acquisition + analysis v2.0.0 (modes: demo | mcp3008 | file)
│   ├── legacy/ScriptECG.py             first version: UDP streaming (13 Sep)
│   ├── requirements.txt
│   ├── data/run_20260916T104943Z_mcp3008/   recording of 16 Sep (raw + analysis files)
│   ├── analysis/ecg_signal_quality.py  timing, ADC use, spectrum, notch test, HRV
│   │   └── output/quality_metrics.json
│   └── dashboard/ecg_explorer/         offline copy of ECG Explorer
├── MediaSources/
│   ├── SquatJump videos/               Video 1 (recording session), Video 2 (camera set-up, 960×540 copy)
│   ├── ECG/                            electrode placement and bench (23 Sep)
│   └── Demo recordings/                screen recordings of the ECG (6 Oct) and squat-jump (14 Oct) runs on the Pi
└── Report/
    ├── Report-AnalysisChainforBiofeedback.docx   final group report
    └── Figures of the final report/    every figure and photo used in the report
```

## Running the code

### On the Raspberry Pi

**Squat jump** (camera + button on GPIO 17). Installation details are in [`1stProject-SquatJump/README.md`](1stProject-SquatJump/README.md).

```bash
cd 1stProject-SquatJump && python3 main.py --once
```

**ECG** (MCP3008 on SPI, channel 1). Start the pigpio daemon first:

```bash
sudo pigpiod -s 1
```

```bash
cd 2ndProject-ECGAnalyzer && python3 ecg_lab_merged.py --mode mcp3008 --channel 1 --vref 3.3 --fs 800 --duration 30 --show
```

### Offline (any computer)

```bash
pip install -r requirements.txt
```

Re-run the squat-jump analysis. The full run re-trains 20 models and takes about 10 minutes; add `--figures-only` to redraw the figures from the saved results:

```bash
cd 1stProject-SquatJump && python3 analysis/jump_dataset_analysis.py
```

```bash
cd 1stProject-SquatJump && python3 analysis/dataset_overview.py && python3 dashboard/build_dashboard.py
```

Re-analyse the ECG recording and compute its signal-quality figures:

```bash
cd 2ndProject-ECGAnalyzer && python3 ecg_lab_merged.py --mode file --input data/run_20260916T104943Z_mcp3008/raw.csv
```

```bash
cd 2ndProject-ECGAnalyzer && python3 analysis/ecg_signal_quality.py data/run_20260916T104943Z_mcp3008 --out analysis/output
```

Try the ECG pipeline on a synthetic signal:

```bash
cd 2ndProject-ECGAnalyzer && python3 ecg_lab_merged.py --mode demo --show
```

The analysis scripts write their CSV/JSON results to `analysis/output/` and their figures directly to `Report/Figures of the final report/`.

### Dashboards

- **Squat Jump Explorer:** open `1stProject-SquatJump/dashboard/jump_dashboard.html` in a browser. Everything is embedded, so it works without internet access. You can change body mass and push-off distance, or load a `results.json` from a Pi session (e.g. `example_session_20261014_results.json`) to compare it with the 20 reference jumps.
- **ECG Explorer:** online at <https://victor-ecg-explorer.hoi987.chatgpt.site>, or offline in `2ndProject-ECGAnalyzer/dashboard/ecg_explorer/`. For the offline copy, run `python3 -m http.server` inside that folder and open `http://localhost:8000`. Then load an output folder, or a ZIP of one, such as `2ndProject-ECGAnalyzer/data/run_20260916T104943Z_mcp3008/`.

## What is not in the repository

- **Other Pi sessions:** 8 squat-jump session folders (`jump_data/`) and 14 ECG run folders (16 Sep, 29 Sep, 6 Oct) stayed on the Raspberry Pi. Only the 16 Sep ECG recording was exported. The 14 Oct jump run and the 6 Oct ECG run are documented through their screen recordings in `MediaSources/Demo recordings/`.
- **`ecg_lab` v1.2.0 source:** the version that produced the 16 Sep recording was later replaced by `ecg_lab_merged.py` v2.0.0. Its output files are compatible: re-analysing the raw file with v2.0.0 gives the same 11 R peaks and 73.1 bpm.
- **Original of `Video 2`:** the 116 MB `.MOV` is over GitHub's 100 MB limit, so only a 960 × 540 copy without sound is kept.
- **ECG front-end model:** the reference of the analogue ECG front-end board was not written down during the sessions.

## Contributions and use of AI tools

This was a group project to which all three members contributed equally:

- **Victor Salvat** built the ECG Explorer dashboard.
- **Joël Singer** mainly wrote the squat-jump scripts.
- **Baptiste Augros** designed the ECG acquisition script, wrote the basis of the final report, handled the synthesis and integration of both projects, and manages the GitHub repository.

Parts of the code were drafted with the help of AI assistants, then reviewed, tested on the Pi and integrated by the group. The offline analyses and the Squat Jump Explorer were also prepared with AI assistance, from the group's own data.

*Exploratory course project: not a validated measurement or clinical instrument.*
