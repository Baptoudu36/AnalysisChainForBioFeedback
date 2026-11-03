# Raspberry Pi measurement chains for biofeedback

**Group review candidate — 22 October 2026.** Baptiste Augros, Joël Singer and Victor Salvat. University of Montpellier, UFR STAPS; course taught by Gilles Despaux, 2026–2027.

Read the [Word report](Report/Report-AnalysisChainforBiofeedback.docx) or [PDF report](Report/Report-AnalysisChainforBiofeedback.pdf). 

## Findings and evidence

Through the practical sessions of the 5 *Analysis Chain for Biofeedback* courses, as well as homework, we built two complete measurement chains on a Raspberry Pi 3B+, from the sensor to a result a non-specialist can read. **Project 1** estimates squat-jump performance from a 60-fps video. The time spent in the air between take-off and landing permits to calculate some interesting metrics such as jump height, take-off velocity and, thanks to the participant's mass and push-off distance, mean force and power. On 20 jumps of one participant annotated by hand, mean height was 24.0 ± 2.5 cm and mean power 18.9 ± 1.8 W/kg. A linear classifier detecting foot contact placed both events within one frame of our annotations in 10 of 20 videos it had never seen, given that all are coming from a very homogeneous dataset. **Project 2** records a three-electrode electrocardiogram (ECG) through an MCP3008 10-bit ADC at 800 Hz, filters it and extracts R peaks, RR intervals and heart rate. A 10-s recording gave 11 R peaks and a median heart rate of 73.1 bpm but also showed that 21 % of the raw signal power came from 50 Hz mains interference. Two browser dashboards present the results of each project.

## Installation and safe offline commands

Python 3.10 was used for numerical verification. Create a fresh environment and install the recorded offline numerical versions (internet/package cache needed for installation):

```sh
python -m venv .venv
# Windows PowerShell: .venv/Scripts/Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements-offline.txt
python tools/check_data.py
```

The check uses only the standard library and verifies delivered hashes, seven-session formulas, timestamp mismatch, reference-video count and local Markdown links. It never unpickles a model. Dependencies are specified, not bundled environments or wheels. FFmpeg/FFprobe must be installed separately for video remux/inspection; OpenCV performs the delivered offline decoding. The historical joblib model is retained unchanged and its original scikit-learn version is unknown; do not treat it as a newly validated model.

Use new output paths; historical scripts may otherwise overwrite analysis files or report figures:

```sh
python 2ndProject-ECGAnalyzer/ecg_lab_merged.py --mode file --input 2ndProject-ECGAnalyzer/data/run_20260916T104943Z_mcp3008/raw.csv --out outputs/ecg_replay
python 2ndProject-ECGAnalyzer/analysis/ecg_signal_quality.py 2ndProject-ECGAnalyzer/data/run_20260916T104943Z_mcp3008 --out outputs/quality --fig-dir outputs/quality_figures
python 2ndProject-ECGAnalyzer/analysis/ecg_signal_quality.py 2ndProject-ECGAnalyzer/data/20260916T101922_610535Z_mcp3008 --out outputs/quality_no_rr --fig-dir outputs/quality_no_rr_figures
```

These file-mode/quality commands were checked from the candidate copy. Output folders are not part of the delivered historical data. NeuroKit2 is optional and was absent from the verified environment; SciPy fallback was used. A full LOVO rerun is optional, slow and was not repeated during finalization:

```sh
python 1stProject-SquatJump/analysis/jump_dataset_analysis.py --out outputs/new_lovo --fig-dir outputs/new_lovo_figures
```

Do not rebuild the historical dashboard in place simply to view it: its embedded historical table is intentionally preserved.

## Dashboards

From this root:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Open [Squat Jump Explorer](http://127.0.0.1:8000/1stProject-SquatJump/dashboard/jump_dashboard.html) or [ECG Explorer](http://127.0.0.1:8000/2ndProject-ECGAnalyzer/dashboard/ecg_explorer/index.html). All delivered assets are local. Stop the server with Ctrl+C. Jump Explorer also works as a self-contained HTML file.

For jumps, import 1stProject-SquatJump/jump_data/jump_20261014_035847/results.json as the original source. The older dashboard/example_session_20261014_results.json remains an unchanged secondary screen transcription. Imported sessions stay outside the reference distribution; importing is not accepting events. The automatic 044853 export is pending and must not be accepted as a measured 110.67 cm jump.

For ECG, choose either complete data directory under 2ndProject-ECGAnalyzer/data/ with the folder picker. The first archived output has no R/RR; the second has 11/10. Initial synthetic data are labelled separately. Beat review/export modifies review output, not the original acquisition.

## Graphical and hardware requirements

The [manual file-review protocol](docs/MANUAL_REVIEW.md) uses the existing OpenCV selector. For that path, use a separate environment with opencv-python==4.11.0.86 instead of opencv-python-headless; never install both in one environment. A visible desktop is required. The GUI-capable window opened, but actual navigation/correction/acceptance/export/cancel remains pending. No test fixture is a scientific event review.

Historical Pi requirements: Raspberry Pi OS, Pi 3B+, Camera V2.1, Picamera2/libcamera, gpiozero, GPIO 17 button and FFmpeg for jumps; MCP3008 with SPI wiring, an appropriate ECG analogue front-end and pigpio daemon for DMA. The physically wired channel must be checked for that session; CH1 is a September metadata value, not a universal wiring instruction. Pi dependency notes are retained in each project's requirements.txt. The hardware was returned; corrected code has not been retested on Pi. JumpLab Pi is Victor’s separate MVP, not this historically tested prototype.

## Before submission

The group should review the candidate, contributions and media sharing; clarify push-off measurement and the six other recovered-session participants; match Victor’s demo to the October clip if evidence permits; complete the GUI protocol; and confirm deadline/delivery route. Missing raw October ECG, unresolved LOVO discrepancies, unverified physical timing and absent reference-instrument/clinical validation remain stated limitations. Private notes, chats, credentials, environments, caches and backups are excluded.

## Contribution branch

Original sources and attribution are described in [SOURCE_PROVENANCE.md](docs/SOURCE_PROVENANCE.md). Offline regression commands are in [tests/README.md](tests/README.md); targeted changes are in [SOFTWARE_FIXES.md](docs/SOFTWARE_FIXES.md). The candidate report remains for group review. Received archives, local environments, private course notes and the full submission ZIP are outside Git.
