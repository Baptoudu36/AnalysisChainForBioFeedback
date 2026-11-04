# Analysis Chain for Biofeedback — two Raspberry Pi measurement chains

**Squat-jump analysis from video** and **ECG acquisition**, built on a Raspberry Pi 3B+ from the sensor to a
result a non-specialist can read.

*2nd year of Master of Sciences in Engineering Ergonomics of Physical Activity — Université de Montpellier, UFR STAPS.*
*Course : Analysis Chain for Biofeedback (Gilles Despaux) - Academic year 2026–2027.*
**Authors:** Baptiste Augros, Joël Singer, Victor Salvat.

📄 Scientific report: [`Report/Report-AnalysisChainforBiofeedback.docx`](Report/Report-AnalysisChainforBiofeedback.docx)
(a PDF document is located in the same folder) 

---

## 1. Context and objectives

A biofeedback system measures a physiological or mechanical quantity, turns it into an indicator and
returns it to the user. The course followed this chain link by link — phenomenon, sensor, conditioning and
analogue-to-digital conversion, computer, processing, indicator, decision and feedback — on a Raspberry Pi
3B+ running Linux and Python. The objective of the project was to build two complete chains, to measure
what each link costs in accuracy and timing, and to keep every result traceable to its raw data.

| | Project 1 — Squat jump | Project 2 — ECG |
|---|---|---|
| Phenomenon | vertical squat jump (centre-of-mass flight) | cardiac electrical activity |
| Sensor | Raspberry Pi Camera V2.1 + push button (GPIO 17) | 3 chest electrodes + analogue front-end |
| Digitisation | 640 × 480 H.264 video, 60 fps, frame timestamps | MCP3008 10-bit ADC over SPI, 800 Hz |
| Processing | fixed ROI, linear SVM contact/flight classifier, event search, **mandatory human review** | 0.5–40 Hz zero-phase band-pass, R-peak detection |
| Indicators | flight time, jump height, take-off velocity, mean force, mean power (W, W/kg) | R peaks, RR intervals, heart rate, (illustrative) HRV |
| Feedback | results files, annotated video, **Squat Jump Explorer** | analysis figure, **ECG Explorer** |

## 2. Main results

- **Squat jump, 20 hand-annotated trials** (one participant, 66 kg, 31 cm push-off distance): height
  24.0 ± 2.5 cm, model power 18.9 ± 1.8 W/kg. At 60 fps one frame is worth ≈ 1.8 cm of height.
- **Automatic detector, leave-one-video-out**: both events within ±1 frame in 10/20 unseen videos in the
  historical run (9/20 when re-run in another environment); one video (jump_07) always gets the wrong jump.
  Hence every proposal is now reviewed by the operator.
- **ECG, 16 September 2026**: second acquisition 11 R peaks, median 73.1 bpm; 21 % of the raw power is
  50 Hz mains interference. The first acquisition had 0 R peaks with the early detector and 10 (66.7 bpm)
  with the current one.
- **ECG, 6 October 2026** (DMA version): the input was saturated near 3.3 V; the program refused to output
  a heart rate. The cause is not established.

## 3. Methods in brief

**Squat jump.** A squat jump starts from a held squat without counter-movement. Each frame is cropped to
the bottom 38 % of the image, converted to 320 × 96 grey levels and scored by a linear SVM (contact +,
flight −) trained on 168 annotated frames with brightness augmentation. Scores are smoothed over 5 frames;
a contact → flight → contact sequence with ≥ 3 frames on each side and a margin ≥ 0.15 is proposed, then
confirmed or corrected by the operator. Take-off = first frame with no foot on the ground; landing = first
frame with a foot back on the ground. With flight time T, mass m and push-off distance d we can compute some interesting metrics like :
h = gT²/8, v₀ = gT/2, F = mg(1 + h/d), P = F·v₀/2 (Bosco et al., 1983; Samozino et al., 2008).

**ECG.** The MCP3008 is sampled by a pigpio DMA waveform that
generates every SPI transaction in hardware (v2.0.0). The analysis checks timing and ADC saturation,
applies a 4th-order Butterworth band-pass (0.5–40 Hz, forward-backward), detects R peaks with robust
prominence/height thresholds, keeps RR intervals between 35 and 180 bpm and reports median heart rate.

**Technologies.** Python 3, NumPy, SciPy, Matplotlib, OpenCV, scikit-learn, joblib; on the Pi Picamera2,
gpiozero, pigpio, rpicam-apps, FFmpeg, mkvtoolnix; HTML/JavaScript dashboards (no external resources).

## 4. Installation

Requirements: Python 3.10 or newer (current test suite run on 3.14; the earlier suite and the
reproductions ran on 3.10), Git. 

## 5. Some Limitations

- One participant for the 20 training jumps, two short (10-s) ECG recordings: no physiological or
  between-subject conclusion is possible; HRV values are illustrations.
- No reference instrument: jump height, force and power were not compared with a force plate, heart rate
  not with a clinical ECG. Only the detector timing was checked, against our own annotations.
- Force and power depend on a push-off distance measured by subtracting the height at a « comfortable »
  position (subject to variability in unused individuals) to leg length (robust).
- The detector was trained and tested in one room with one camera position : it is sensitive to light,
  framing and post-landing movements.
- Timing: 60 fps limits flight time to whole frames; sensor-to-frame alignment and the DMA clock were not
  checked against an independent clock; all seven Pi sessions used the nominal-fps fallback.

## Authors and contributions

- **Baptiste Augros** — initial ECG scripts (UDP streaming, first `ecg_lab` version), offline analyses, Squat Jump
  Explorer, report writing & review, repository integration.
- **Joël Singer** — squat-jump Pi prototype (script, recordings and testings), training videos and manual annotations, DMA clock conception, the seven Pi sessions, report writing & review.
- **Victor Salvat** — `ecg_lab` versions up to the DMA version (v2.0.0), design the ECG Explorer, permits reproductions, report writing & review, robustness corrections and testings.

Parts of the code and of the offline analyses were drafted with AI assistants, then reviewed, tested and
integrated by the group. 

## References

Bosco C., Luhtanen P., Komi P. V. (1983). *Eur J Appl Physiol* 50:273–282. · Samozino P. et al. (2008).
*J Biomech* 41:2940–2945. · Task Force ESC/NASPE (1996). *Eur Heart J* 17:354–381. · Makowski D. et al.
(2021). *Behav Res Methods* 53:1689–1696. · Pedregosa F. et al. (2011). *JMLR* 12:2825–2830. ·
Virtanen P. et al. (2020). *Nat Methods* 17:261–272. · Shannon C. E. (1949). *Proc IRE* 37:10–21.
