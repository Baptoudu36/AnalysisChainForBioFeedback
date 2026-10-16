# From Sensor to Feedback — Raspberry Pi measurement chains for ECG and squat-jump analysis

**Université de Montpellier · UFR STAPS**
Master of Sciences in Engineering Ergonomics of Physical Activity
Course: **Analysis Chain for Biofeedback**, taught by Gilles Despaux, 2026–2027

**Students:** Baptiste Augros, Victor Salvat, Joël Singer

---

This repository holds the two measurement-and-analysis chains we built on a **Raspberry Pi 3B+** during the practical sessions, along with their data, media, offline analyses and dashboards.

| | Project A: ECG | Project B: Squat jump |
|---|---|---|
| Sensor | 3 chest electrodes, analogue front-end | Raspberry Pi Camera V2.1 + push button (GPIO 17) |
| Digitisation | MCP3008 10-bit ADC over SPI, 800 Hz | 640 × 480 video at 60 fps, per-frame timestamps |
| Processing | 0.5–40 Hz band-pass, R-peak detection, RR and HR | Fixed ROI, linear SVM contact/flight classifier, event detection |
| Indicators | Heart rate, RR intervals, PQRST candidates | Flight time, jump height, take-off velocity, mean force, power, W/kg |
| Dashboard | **ECG Explorer** (V. Salvat) | **Squat Jump Explorer** (new) |

📄 **Full report:** [`report/Report_Analysis_Chain_for_Biofeedback.docx`](report/Report_Analysis_Chain_for_Biofeedback.docx)

## Key results

- **ECG, 16 Sep 2026 recording** (10 s, 800 Hz): 11 R peaks and a median heart rate of 73.1 bpm. 21 % of the raw signal power was 50 Hz mains interference, and a notch filter brought out the P–QRS–T waves.
- **ECG, 6 Oct 2026 live demonstration** (DMA clock v2.0.0): the sampling grid was exactly 800.000 Hz, but the input was saturated near the 3.3 V rail. The software caught this and refused to output a heart rate.
- **Squat jump, 20 hand-annotated trials** (same participant, 66 kg, 31 cm push-off): mean height 24.0 ± 2.5 cm and mean power 18.9 ± 1.8 W/kg. At 60 fps, one frame is about 1.8 cm of jump height.
- **Automatic detector, leave-one-video-out validation:** both events were within ±1 frame in 10 of 20 unseen videos. One false jump was selected (jump_07).

## Repository map

```
.
├── README.md
├── ecg/                                   Project A
│   ├── ecg_lab_merged.py                  acquisition + analysis v2.0.0 (demo | mcp3008 | file)
│   ├── requirements.txt
│   ├── legacy/ScriptECG.py                first version: UDP streaming (13 Sep)
│   ├── data/
│   │   ├── run_20260916T104943Z_mcp3008/              recording of 16 Sep (v1.2.0 outputs)
│   │   └── run_20260916T104943Z_mcp3008_reanalysed_v2/ same raw file re-analysed with v2.0.0
│   ├── analysis/ecg_signal_quality.py     timing, ADC use, spectrum, notch test, HRV → analysis/output/
│   └── dashboard/ecg_explorer/            offline copy of ECG Explorer (open index.html)
├── squat_jump_pi/                         Project B (folder copied as-is to the Pi Desktop)
│   ├── main.py  detector.py  mechanics.py  report.py
│   ├── record_tr_videos.py  train_contact_model.py
│   ├── config.json  contact_model.joblib  requirements.txt  README.md
│   ├── training_dataset/jump_01…20.mp4    20 training videos (5 s, 60 fps)
│   ├── annotations.csv  annotations/      168 hand labels + photos of the lab notebook
│   ├── analysis/                          reference metrics, LOVO validation, dataset overview → analysis/output/
│   └── dashboard/jump_dashboard.html      Squat Jump Explorer (single offline file)
├── media/
│   ├── ecg/IMG_7062.MOV                   electrode placement and bench (23 Sep)
│   ├── squat_jump/                        camera set-up and recording session videos
│   └── demo_recordings/                   screen recordings of the ECG (6 Oct) and jump (14 Oct) demos
└── report/                                report (.docx), figures and the scripts that build them
```

## Running the code

### On the Raspberry Pi

**ECG** (MCP3008 on SPI, channel 1):

```bash
sudo pigpiod -s 1
```

```bash
python3 ecg/ecg_lab_merged.py --mode mcp3008 --channel 1 --vref 3.3 --fs 800 --duration 30 --show
```

**Squat jump** (camera + button on GPIO 17). See [`squat_jump_pi/README.md`](squat_jump_pi/README.md) for installation.

```bash
cd squat_jump_pi && python3 main.py --once
```

### Offline (any computer)

You need Python 3 with `numpy scipy matplotlib opencv-python scikit-learn joblib`.

```bash
python3 ecg/ecg_lab_merged.py --mode demo --show
```

```bash
python3 ecg/ecg_lab_merged.py --mode file --input ecg/data/run_20260916T104943Z_mcp3008/raw.csv
```

```bash
python3 ecg/analysis/ecg_signal_quality.py ecg/data/run_20260916T104943Z_mcp3008 --out ecg/analysis/output
```

```bash
python3 squat_jump_pi/analysis/jump_dataset_analysis.py
```

```bash
python3 squat_jump_pi/dashboard/build_dashboard.py
```

### Dashboards

- **Squat Jump Explorer:** open `squat_jump_pi/dashboard/jump_dashboard.html` in a browser. Everything is embedded, so it works without internet access. You can load a `results.json` from a Pi session to compare it with the reference set.
- **ECG Explorer:** online at <https://victor-ecg-explorer.hoi987.chatgpt.site>, or offline in `ecg/dashboard/ecg_explorer/`. To use the offline copy, serve the folder (`python3 -m http.server` inside it) and open `http://localhost:8000`. Then load an output folder, or a ZIP of one, such as `ecg/data/run_20260916T104943Z_mcp3008/`.

### Rebuilding the report

```bash
cd report/build && npm install && node build_report.js
```

All numbers in the report are read from the analysis outputs; the cover logo is `report/assets/logo_um.jpg`.

## What is not in the repository

- **Other ECG runs:** 14 ECG run folders (16 Sep, 29 Sep, 6 Oct) and 8 squat-jump session folders (`jump_data/`) stayed on the Raspberry Pi. Only the 16 Sep ECG recording was exported. The 6 Oct ECG and 14 Oct jump demonstrations are documented through their screen recordings in `media/demo_recordings/`.
- **`ecg_lab` v1.2.0 source:** the version that produced the 16 Sep recording was superseded by `ecg_lab_merged.py` v2.0.0. Its output files are fully compatible and were re-analysed with v2.0.0.
- **`media/squat_jump/IMG_7204.MOV`** (116 MB) is over GitHub's 100 MB limit, so a 960 × 540 copy (`IMG_7204_960x540.mp4`) is committed instead.
- **ECG front-end model:** the reference of the analogue ECG front-end board is not recorded in the project files.

## Contributions and use of AI

This was a group project to which all three members contributed equally:

- **Victor Salvat** built the ECG Explorer dashboard.
- **Joël Singer** mainly wrote the squat-jump scripts.
- **Baptiste Augros** designed the ECG acquisition script, ensured the synthesis and integration of both projects and wrote the report.

Parts of the code were drafted with AI assistants, then reviewed, tested on the Pi and integrated by the group. The offline analyses, Squat Jump Explorer and the report were also prepared with AI assistance from the group's own data.

*Exploratory course project: not a validated measurement or clinical instrument.*
