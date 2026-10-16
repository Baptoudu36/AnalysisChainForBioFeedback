/*
 * Builds report/Report_Analysis_Chain_for_Biofeedback.docx
 *
 *   cd report/build && npm install && node build_report.js
 *
 * All numbers quoted in the report are read from the analysis outputs
 * (JSON files written by the Python scripts), so re-running the analyses and
 * this script keeps text and data consistent. Put the official Université de
 * Montpellier logo at report/assets/logo_um.png (or .jpg) before building.
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, Header, Footer,
  AlignmentType, HeadingLevel, PageNumber, PageBreak, WidthType, BorderStyle, ShadingType,
  TableOfContents, LevelFormat, VerticalAlign, TabStopType,
} = require("docx");

const ROOT = path.resolve(__dirname, "..", "..");
const FIG = path.join(ROOT, "report", "figures");
const rd = p => JSON.parse(fs.readFileSync(path.join(ROOT, p), "utf8"));
const Q = rd("ecg/analysis/output/quality_metrics.json");
const A = rd("ecg/data/run_20260916T104943Z_mcp3008/analysis.json");
const J = rd("squat_jump_pi/analysis/output/summary.json");
const R = J.reference, D = J.detector_lovo;
const f1 = x => Number(x).toFixed(1), f0 = x => Number(x).toFixed(0), f2 = x => Number(x).toFixed(2);

// ---------------------------------------------------------------- styling --
const FONT = "Calibri", NAVY = "1F3A5F", ACCENT = "215BCC", GREY = "5F6B7A", LINE = "C9D2DE";
const TEXT_W = 9070;                         // A4 minus 2 × 2.5 cm margins, in DXA
const PX_PER_CM = 37.8;

// --------------------------------------------------------------- helpers --
function imageSize(file) {
  const b = fs.readFileSync(file);
  if (b.readUInt32BE(0) === 0x89504e47) return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), type: "png", b };
  let i = 2;                                  // JPEG: walk markers until a SOFn segment
  while (i < b.length) {
    const marker = b[i + 1], len = b.readUInt16BE(i + 2);
    if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker))
      return { h: b.readUInt16BE(i + 5), w: b.readUInt16BE(i + 7), type: "jpg", b };
    i += 2 + len;
  }
  throw new Error("Unknown image format: " + file);
}

function runs(text, base = {}) {
  // Minimal inline markup: **bold**, *italic*, `code`
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith("`")) out.push(new TextRun({ text: t.slice(1, -1), font: "Consolas", size: 19, color: "1F2937", ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}

const P = (text, opts = {}) => new Paragraph({ children: runs(text), alignment: AlignmentType.JUSTIFIED, ...opts });
const H1 = text => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)], pageBreakBefore: true });
const H1c = text => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] });
const H2 = text => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
const H3 = text => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(text)] });
const bullet = (text, level = 0) => new Paragraph({ children: runs(text), numbering: { reference: "bullets", level },
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 60 } });
const eq = text => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 60 },
  children: [new TextRun({ text, italics: true, font: "Cambria Math", size: 22 })] });

let figN = 0, tabN = 0;
function figure(file, widthCm, caption) {
  const im = imageSize(path.join(FIG, file));
  const w = Math.round(widthCm * PX_PER_CM), h = Math.round(w * im.h / im.w);
  figN += 1;
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: im.type, data: im.b, transformation: { width: w, height: h },
        altText: { title: `Figure ${figN}`, description: caption.replace(/[*`]/g, ""), name: file } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: `Figure ${figN}. `, bold: true, size: 18, color: GREY }),
        ...runs(caption, { size: 18, color: GREY, italics: true })] }),
  ];
}
function figurePair(a, b, widthCm, caption) {
  const ia = imageSize(path.join(FIG, a)), ib = imageSize(path.join(FIG, b));
  const hPx = Math.round(Math.min(widthCm, 15.2) * PX_PER_CM / (ia.w / ia.h + ib.w / ib.h));
  figN += 1;
  const img = (im, f) => new ImageRun({ type: im.type, data: im.b,
    transformation: { width: Math.round(hPx * im.w / im.h), height: hPx },
    altText: { title: `Figure ${figN}`, description: caption.replace(/[*`]/g, ""), name: f } });
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
      children: [img(ia, a), new TextRun("  "), img(ib, b)] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: `Figure ${figN}. `, bold: true, size: 18, color: GREY }),
        ...runs(caption, { size: 18, color: GREY, italics: true })] }),
  ];
}

const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
function table(headers, rows, widthsCm, caption) {
  tabN += 1;
  const total = widthsCm.reduce((a, b) => a + b, 0);
  const widths = widthsCm.map(w => Math.round(w / total * TEXT_W));
  widths[widths.length - 1] += TEXT_W - widths.reduce((a, b) => a + b, 0);
  const cell = (text, i, head) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA },
    borders: { top: border, bottom: border, left: border, right: border },
    shading: head ? { fill: "E8EFFC", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 0, line: 240 },
      children: runs(String(text), { size: 18, bold: head || undefined, color: head ? NAVY : undefined }) })],
  });
  return [
    new Paragraph({ keepNext: true, spacing: { before: 160, after: 80 },
      children: [new TextRun({ text: `Table ${tabN}. `, bold: true, size: 18, color: GREY }),
        ...runs(caption, { size: 18, color: GREY, italics: true })] }),
    new Table({ width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: widths,
      rows: [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, i, true)) }),
        ...rows.map(r => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false)) }))] }),
    new Paragraph({ spacing: { after: 120 }, children: [] }),
  ];
}
function keyBox(title, lines) {
  // Shaded "concept" box built from bordered paragraphs (no layout table)
  const shade = { fill: "F3F6FB", type: ShadingType.CLEAR, color: "auto" };
  const bd = { left: { style: BorderStyle.SINGLE, size: 18, color: ACCENT, space: 8 } };
  return [
    new Paragraph({ shading: shade, border: bd, spacing: { before: 120, after: 0 }, keepNext: true,
      children: [new TextRun({ text: title, bold: true, color: ACCENT, size: 20 })] }),
    ...lines.map((l, i) => new Paragraph({ shading: shade, border: bd, alignment: AlignmentType.JUSTIFIED,
      spacing: { after: i === lines.length - 1 ? 160 : 40 }, keepNext: i < lines.length - 1,
      children: runs(l, { size: 20 }) })),
  ];
}

// ------------------------------------------------------------------ cover --
function cover() {
  const logo = ["logo_um.png", "logo_um.jpg", "logo_um.jpeg"].map(f => path.join(ROOT, "report", "assets", f))
    .find(f => fs.existsSync(f));
  const c = [];
  if (logo) {
    const im = imageSize(logo), w = Math.round((im.h / im.w > 0.6 ? 4 : 6.5) * PX_PER_CM);  // square seal vs. wide wordmark
    c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 400 },
      children: [new ImageRun({ type: im.type, data: im.b, transformation: { width: w, height: Math.round(w * im.h / im.w) },
        altText: { title: "Université de Montpellier", description: "Official logo of the Université de Montpellier", name: "logo" } })] }));
  } else {
    c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600, after: 600 },
      children: [new TextRun({ text: "[ Université de Montpellier logo — place file at report/assets/logo_um.png ]", color: "999999", size: 18 })] }));
  }
  const line = (text, o = {}) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: o.after ?? 80 },
    children: [new TextRun({ text, font: FONT, size: o.size ?? 24, bold: o.bold, color: o.color ?? "1F2937", italics: o.italics })] });
  c.push(
    line("Université de Montpellier · UFR STAPS", { size: 22, color: GREY }),
    line("Master of Sciences in Engineering Ergonomics of Physical Activity", { size: 26, bold: true, color: NAVY, after: 60 }),
    line("Course: Analysis Chain for Biofeedback", { size: 24, color: GREY, after: 900 }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
      border: { top: { style: BorderStyle.SINGLE, size: 12, color: ACCENT, space: 12 } }, children: [] }),
    line("From Sensor to Feedback", { size: 44, bold: true, color: NAVY, after: 120 }),
    line("Two Raspberry Pi measurement and analysis chains:", { size: 26, color: "1F2937", after: 40 }),
    line("electrocardiogram acquisition and video-based squat-jump analysis", { size: 26, color: "1F2937", after: 120 }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 1000 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: ACCENT, space: 12 } }, children: [] }),
    line("Students", { size: 20, color: GREY, after: 40 }),
    line("Baptiste AUGROS  ·  Victor SALVAT  ·  Joël SINGER", { size: 26, bold: true, after: 300 }),
    line("Teacher", { size: 20, color: GREY, after: 40 }),
    line("Gilles DESPAUX", { size: 26, bold: true, after: 1100 }),
    line("Academic year 2026–2027  ·  October 2026", { size: 22, color: GREY }),
    new Paragraph({ children: [new PageBreak()] }),
  );
  return c;
}

// ---------------------------------------------------------------- content --
const fps = J.inputs.nominal_fps;
const content = [
  ...cover(),

  // --------------------------------------------------------- abstract + TOC
  new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: "Abstract", bold: true, size: 28, color: NAVY })] }),
  P(`This report documents the two measurement and analysis chains that our group built on a Raspberry Pi 3B+ during the practical sessions of the *Analysis Chain for Biofeedback* course. **Project A** acquires a three-electrode electrocardiogram (ECG) through an MCP3008 10-bit analogue-to-digital converter at 800 Hz, band-pass filters it (0.5–40 Hz) and extracts R peaks, RR intervals and heart rate. A 10-s recording yielded ${A.r_candidates} R peaks and a median heart rate of ${f1(A.median_hr_bpm)} bpm; spectral analysis showed that ${f0(Q.spectrum.band_power_fractions["45-55 Hz"] * 100)} % of the raw signal power lay at the 50 Hz mains frequency. **Project B** estimates squat-jump performance from 60-fps video: the flight time between take-off and landing gives jump height, mean force and mean power. On ${J.inputs.n_trials} hand-annotated jumps of one participant, mean height was ${f1(R.jump_height_cm.mean)} ± ${f1(R.jump_height_cm.sd)} cm and mean power ${f1(R.mean_push_power_W_kg.mean)} ± ${f1(R.mean_push_power_W_kg.sd)} W/kg. Leave-one-video-out validation of the automatic contact detector placed both events within ±1 frame in ${D.both_events_within_1_frame} of ${D.videos} videos. Two browser dashboards make the outputs readable by non-specialists.`),
  P("**Keywords:** biofeedback, Raspberry Pi, data acquisition, ECG, heart rate, squat jump, flight time, computer vision, support vector machine.", { spacing: { after: 240 } }),
  new Paragraph({ pageBreakBefore: true, spacing: { after: 120 }, children: [new TextRun({ text: "Contents", bold: true, size: 28, color: NAVY })] }),
  new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),

  // ---------------------------------------------------------- 1 Introduction
  H1("1  Introduction"),
  P("A biofeedback system measures a physiological or mechanical quantity, turns it into an interpretable indicator and returns it to the user quickly enough to influence behaviour. Building one means mastering a complete chain, from the physical phenomenon to the feedback, where every link adds its own constraints: the sensor's bandwidth, the converter's resolution, the sampling clock, the processing and the way results are presented (Figure 1)."),
  ...figure("diagram_biofeedback_chain.png", 16, "The biofeedback chain taught in the course (top) and how our two projects implement each link."),
  P("The practical sessions followed a progressive path. The first sessions introduced the hardware (computer components, the Raspberry Pi 3B+ single-board computer and its Linux operating system), the principles of digital acquisition and object-oriented Python, through short scripts on practical cases. We then applied these foundations to two complete projects:"),
  bullet("**Project A — ECG acquisition chain:** record the electrical activity of the heart with chest electrodes, an external ADC and the Pi, then compute heart-rate indicators."),
  bullet("**Project B — squat-jump video chain:** film a vertical jump with the Pi camera, detect take-off and landing, and compute jump height, force and power for a participant whose body mass and push-off distance are entered by the operator."),
  P("For each project, this report describes the design choices, the successive versions, the results obtained on real data and the limits we identified. All code, data and media referred to are in the project repository (Appendix A)."),

  H2("1.1  Course progression"),
  P("Table 1 summarises the milestones. Dates come from the recordings and file timestamps in the repository."),
  ...table(["Phase", "Date (2026)", "Milestone", "Evidence in the repository"], [
    ["Foundations", "September", "Computer components, Raspberry Pi 3B+, Linux terminal, GPIO, I²C/SPI/UART, sampling theory, Python OOP; short practical scripts", "Course notes (not redistributed)"],
    ["A · ECG", "13 Sep", "First acquisition script: demo, ADS1115 or MCP3008 source; samples streamed over UDP with an absolute-deadline software clock", "`ecg/legacy/ScriptECG.py`"],
    ["A · ECG", "16 Sep", "First real ECG recordings with ecg_lab v1.2.0 (MCP3008, 800 Hz, software timing)", "`ecg/data/run_20260916T104943Z_mcp3008/`"],
    ["A · ECG", "23 Sep", "Bench documented: electrodes, breadboard wiring, Pi and screen", "`media/ecg/IMG_7062.MOV`"],
    ["A · ECG", "29 Sep", "Further test recordings on the Pi (folders listed on screen; not exported)", "Screen recording of 6 Oct"],
    ["A · ECG", "6 Oct", "Version 2.0.0: hardware-timed sampling with pigpio DMA; live demonstration", "`ecg/ecg_lab_merged.py`, `media/demo_recordings/`"],
    ["B · Jump", "12–13 Oct", "Mechanical model; 20 training videos recorded; 168 frames annotated by hand; contact classifier trained", "`squat_jump_pi/`"],
    ["B · Jump", "14 Oct", "End-to-end run on the Pi (66 kg, 31 cm): manual-review fallback, results exported", "`media/demo_recordings/`"],
    ["Synthesis", "16 Oct", "Offline validation, signal-quality analysis, dashboards and report", "`*/analysis/`, dashboards, `report/`"],
  ], [2.2, 2.0, 7.6, 4.6], "Milestones of the project."),

  // ------------------------------------------------- 2 Foundations
  H1("2  Foundations: from an analogue signal to a number in Python"),
  P("The concepts below were introduced in the first sessions and guided every design decision in the two projects. We summarise only those that matter for interpreting our results."),
  ...keyBox("Single-board computer vs. microcontroller", [
    "The Raspberry Pi 3B+ is a complete computer (quad-core ARM Cortex-A53 at 1.4 GHz, 1 GB RAM) running Linux. Linux makes rich software possible (NumPy, SciPy, OpenCV, scikit-learn) but is only *soft real-time*: the scheduler can interrupt a Python script at any moment, which creates timing **jitter**. A microcontroller has no operating system and samples deterministically, but offers little computing power.",
  ]),
  ...keyBox("No analogue input on the Pi", [
    "The GPIO pins are purely digital (0 / 3.3 V). Any analogue signal, such as an ECG, must be digitised by an external ADC. We used the **MCP3008** (8 channels, 10 bits, SPI bus: CS, CLK, MOSI and MISO lines). The camera of Project B contains its own sensor ADC and talks to the Pi through the dedicated CSI interface.",
  ]),
  ...keyBox("Sampling, Nyquist–Shannon and aliasing", [
    "A signal must be sampled faster than twice its highest frequency component (*fs > 2·fmax*), otherwise high frequencies fold back as false low frequencies (aliasing), which no digital filter can undo afterwards. The useful ECG band extends to about 150 Hz; our 800 Hz sampling rate gives a Nyquist frequency of 400 Hz. For video, 60 frames per second means one image every 16.7 ms, which sets the time resolution of jump events.",
  ]),
  ...keyBox("Quantisation and resolution", [
    `An N-bit converter divides its input range into 2^N levels. With 10 bits and a 3.3 V reference, one level (LSB) is ${f2(Q.adc.lsb_mv)} mV. The raw ECG electrode potential (about 1 mV) is therefore far too small to digitise directly: it must first be amplified and offset by an analogue front-end.`,
  ]),
  ...keyBox("Noise, synchronisation and latency", [
    "Noise has distinct origins (thermal, quantisation, electromagnetic interference such as the 50 Hz mains, motion artefacts) and each calls for a different remedy. For biofeedback to support motor learning, the total latency from phenomenon to feedback should generally stay within about 100–300 ms; this budget covers acquisition, processing, decision and display.",
  ]),
  P("On the software side, both projects follow the object-oriented decomposition taught in the course: acquisition, processing, indicator extraction and output are separate components (e.g. the `MCP3008DMA` class in Project A; the `detector`, `mechanics` and `report` modules in Project B), so that each link can be tested and replaced independently."),

  // ------------------------------------------------- 3 Project A ECG
  H1("3  Project A — ECG acquisition chain"),
  H2("3.1  Physiological background"),
  P("The electrocardiogram records the electrical activity of the heart at the skin surface. Each beat produces a characteristic sequence: the **P wave** (atrial depolarisation), the **QRS complex** (ventricular depolarisation, with the sharp R peak) and the **T wave** (ventricular repolarisation). The interval between two successive R peaks (RR interval) gives the instantaneous heart rate, HR = 60 / RR (bpm); the beat-to-beat variability of RR intervals (heart-rate variability, HRV) reflects autonomic regulation and is a classical biofeedback target."),

  H2("3.2  Hardware and electrode placement"),
  P("Three disposable electrodes were placed on the chest: the **red** electrode below the right clavicle, the **yellow** electrode below the left clavicle and the **green** electrode on the lower abdomen (Figure 2). The leads connect to an analogue front-end on the breadboard, whose output is digitised by channel 1 of the MCP3008 (reference voltage 3.3 V) and read by the Pi through GPIO 8 (CS), 11 (CLK), 10 (MOSI) and 9 (MISO)."),
  ...figurePair("photo_ecg_electrodes.jpg", "photo_ecg_hardware.jpg", 13, "Left: three-electrode placement on the chest. Right: Raspberry Pi 3B+ and breadboard wiring of the acquisition bench (still frames from `media/ecg/IMG_7062.MOV`, 23 Sep 2026)."),
  P(`The recorded signal confirms that the front-end amplifies and offsets the electrode potential: at the ADC input, it was centred on mid-supply (≈ 1.65 V) with ${f1(Q.adc.peak_to_peak_v)} V peak-to-peak, using ADC codes ${Q.adc.code_min} to ${Q.adc.code_max}, i.e. ${f0(Q.adc.used_range_fraction * 100)} % of the converter range without saturation.`),

  H2("3.3  Software evolution: three versions"),
  P("The acquisition software evolved as we met the timing limits of Linux (Table 2)."),
  ...table(["Version", "Sampling clock", "Output", "What we learned"], [
    ["`ScriptECG.py` (13 Sep)", "Python loop with absolute deadlines (`time.perf_counter`); demo, ADS1115 (I²C) or MCP3008 (SPI) sources", "One float per UDP datagram to an analysis PC", "Separating the clock from the sources avoids cumulative drift, but sleep-based timing remains at the mercy of the scheduler"],
    ["ecg_lab v1.2.0 (16 Sep)", "Software-scheduled SPI reads at 800 Hz, each sample time-stamped", "Local files: raw, filtered, PQRST, RR, JSON, figure", `Mean rate ${f2(Q.timing.measured_fs_hz)} Hz; intervals from ${f2(Q.timing.min_interval_ms)} to ${f2(Q.timing.max_interval_ms)} ms; ${Q.timing.missed_schedule_slots} missed slots`],
    ["`ecg_lab_merged.py` v2.0.0 (6 Oct)", "pigpio **DMA** waveform generates every SPI transaction in hardware; samples decoded from the GPIO notification stream", "Same file contract as v1.2.0, plus transport diagnostics", "Uniform sample grid by construction (period quantised to an integer number of µs: 1250 µs = 800 Hz exactly)"],
  ], [3.3, 4.6, 3.5, 5.0], "Successive versions of the ECG acquisition software."),
  P("The direct-memory-access (DMA) approach removes Python from the timing loop: a waveform describing one complete MCP3008 transaction (chip select, 5 command bits, 12 clock pulses at 100 kHz) is repeated by the DMA engine every 1250 µs, and the program only decodes the MISO line from timestamped GPIO level changes. Every transaction is checked (17 clock edges expected) and any lost notification is counted and reported, so a corrupted recording cannot pass silently."),
  ...figure("fig_ecg_timing.png", 14.5, `Distribution of sample intervals in the software-timed v1.2.0 recording. 95 % of intervals deviate by less than ${f1(Q.timing.p95_abs_deviation_fraction * 100)} % from the nominal 1.25 ms, but isolated outliers reach ${f2(Q.timing.max_interval_ms)} ms; the DMA clock of v2.0.0 removes this source of error.`),

  H2("3.4  Processing pipeline"),
  P("The same analysis runs on the Pi after each recording and offline on any saved file (`--mode file`):"),
  bullet("**Timing checks:** at least 3 s of data, strictly increasing timestamps; warnings if the measured rate differs from the target by more than 2 %, if jitter exceeds 10 %, or if more than 1 % of ADC codes are near a rail."),
  bullet("**Filtering:** 4th-order Butterworth band-pass 0.5–40 Hz applied forward and backward (zero phase), which removes baseline wander and high-frequency noise without shifting the peaks in time."),
  bullet("**Polarity:** the signal is automatically inverted if its largest deflection is negative, so that R peaks are always positive."),
  bullet("**R-peak detection:** `scipy.signal.find_peaks` with a minimum distance set by the maximum plausible heart rate (180 bpm), a prominence threshold equal to the larger of 6 × the robust background scale and 45 % of the peak amplitude, and the same height threshold."),
  bullet("**Indicators:** RR intervals accepted only within 35–180 bpm; median and mean heart rate. P, Q, S and T candidates come from NeuroKit2 wavelet delineation when installed, otherwise from conservative local extrema around each R peak."),
  P("Each run writes `raw.csv`/`raw.npz`, `metadata.json`, `filtered.csv`, `pqrst_candidates.csv`, `rr_intervals.csv`, `analysis.json` and a three-panel figure, so that every result can be traced back to the raw samples."),

  H2("3.5  Results"),
  H3("Successful recording of 16 September"),
  P(`The 10-s recording contains ${Q.timing.samples} samples at a measured ${f2(Q.timing.measured_fs_hz)} Hz. The pipeline detected **${A.r_candidates} R peaks** and accepted all ${A.accepted_rr_intervals} RR intervals, giving a **median heart rate of ${f1(A.median_hr_bpm)} bpm** (Figure 4). Q-wave candidates were found for every beat; the fallback delineation found no reliable P, S or T candidates, which, as the program warns, does not mean that these waves are absent.`),
  ...figure("ecg_pi_output_20260916.png", 13.5, "Output figure generated on the Pi for the 16 Sep recording: raw ADC voltage, filtered and polarity-oriented signal with R (red) and Q (orange) candidates, and RR-derived heart rate."),
  P("Re-analysing the saved raw file with the later v2.0.0 code reproduced the same 11 R peaks and the same median heart rate, which shows that the analysis is deterministic and that the file format stayed compatible across versions."),
  H3("Signal quality: a strong 50 Hz interference"),
  P(`The raw trace (Figure 4, top) shows a regular oscillation superimposed on the ECG. A power spectral density estimate (Welch method) identifies it precisely: **${f0(Q.spectrum.band_power_fractions["45-55 Hz"] * 100)} % of the signal power lies at ${f1(Q.spectrum.mains_peak_hz)} Hz**, the mains frequency, with a harmonic at 100 Hz (Figure 5). The fundamental of the cardiac rhythm appears at ${f2(Q.spectrum.fundamental_hz_below_3hz)} Hz, i.e. ${f0(Q.spectrum.fundamental_hz_below_3hz * 60)} bpm.`),
  ...figure("fig_ecg_spectrum.png", 14, "Power spectral density of the raw ECG trace. The shaded band is the analysis band of the pipeline; the peak at 50 Hz is mains interference."),
  P("The 0.5–40 Hz band-pass strongly attenuates this component but leaves a visible ripple. As an exploratory test (not part of the acquisition software), adding a 50 Hz notch filter (Q = 30) recovers a clean morphology in which the P wave, the QRS complex and the T wave become identifiable by eye (Figure 6). This motivates adding a notch filter, better lead shielding and cable routing in the next version."),
  ...figure("fig_ecg_notch.png", 13.5, "Three seconds of the same recording at three processing stages: raw, band-pass (current pipeline), and band-pass followed by a 50 Hz notch filter (exploratory)."),
  H3("Heart-rate variability (illustrative)"),
  P(`From the ${Q.hrv_time_domain.n_rr} RR intervals: mean RR ${f0(Q.hrv_time_domain.mean_rr_ms)} ms, heart rate ${f1(Q.hrv_time_domain.min_hr_bpm)}–${f1(Q.hrv_time_domain.max_hr_bpm)} bpm, SDNN ${f1(Q.hrv_time_domain.sdnn_ms)} ms and RMSSD ${f1(Q.hrv_time_domain.rmssd_ms)} ms (Figure 7). These values only demonstrate that the chain can deliver HRV indices: standard short-term HRV requires recordings of at least 5 minutes (Task Force, 1996), whereas ours lasted 10 s.`),
  ...figure("fig_ecg_tachogram.png", 14.5, "RR tachogram of the 16 Sep recording with time-domain HRV indices."),
  H3("Live demonstration of 6 October"),
  P("During the live demonstration of version 2.0.0 (Figure 8), the DMA clock delivered exactly the requested grid (8001 samples at 800.000 Hz in 10 s), but the input stayed pinned near 3.29 V, i.e. ADC codes close to the top of the range. The program flagged that more than 1 % of codes were near a rail, detected no R peak and refused to compute a heart rate. The timing layer therefore worked as designed, and the failure lay upstream in the analogue path (electrode contact, lead or front-end output); the saved files do not allow the exact cause to be identified. This episode illustrates why the software checks its input instead of always producing a number."),
  ...figurePair("screen_ecg_failed_run.jpg", "screen_ecg_terminal.jpg", 16, "Live run of 6 Oct on the Pi: saturated raw signal and empty heart-rate panel (left); terminal summary with the rail warning (right)."),

  H2("3.6  ECG Explorer dashboard"),
  P("To make recordings readable without Python, Victor Salvat built **ECG Explorer**, a browser dashboard that loads one output folder or its ZIP archive. All processing stays in the browser tab. It displays the recording duration, the measured sampling rate, the median heart rate and the number of detected beats, together with the analysis warnings. The raw, filtered and RR traces share one time axis that can be zoomed and scrolled, and every detected beat can be inspected, flagged and annotated, with the review exported as CSV (Figures 9–10). The dashboard validates file consistency, for example that the RR intervals match the R times, before displaying anything."),
  ...figure("screen_ecg_explorer_top.png", 12, "ECG Explorer loaded with the 16 Sep recording: summary indicators, warnings and time-aligned raw, filtered and RR traces."),
  ...figure("screen_ecg_explorer_beats.png", 13, "ECG Explorer beat review: list of detected beats and zoom on the selected candidate with its Q and R markers."),

  // ------------------------------------------------- 4 Project B jump
  H1("4  Project B — Squat-jump video chain"),
  H2("4.1  Principle: from flight time to power"),
  P("In a **squat jump (SJ)**, the participant holds a static squat position and pushes upward without counter-movement. Once airborne, the centre of mass (COM) follows a ballistic trajectory, so the flight time *T* alone determines the take-off velocity and the jump height (Bosco et al., 1983). With body mass *m* and push-off distance *d* (the vertical COM displacement from squat to take-off), the mean force and power of the push-off follow from the work–energy theorem (Samozino et al., 2008):"),
  eq("h = g·T² / 8          v₀ = g·T / 2"),
  eq("F̄ = m·g·(1 + h / d)          v̄ = v₀ / 2          P̄ = F̄ · v̄"),
  P("with g = 9.81 m/s². These relations assume vertical motion, negligible air resistance, identical COM height at take-off and landing, a push-off starting from rest and, for the mean velocity, a constant acceleration. Force and power are therefore model-derived estimates, not force-plate measurements, and they depend strongly on the push-off distance typed by the operator. The counter-movement jump and the squat were also tested during the sessions but not coded; because the mechanics module is separate from the event detection, other jump types can be added as new modules."),
  P(`Timing resolution is the key constraint of a 60-fps camera: one frame lasts ${f1(J.quantisation.one_frame_ms)} ms, and at the mean flight time of our dataset (${f0(R.flight_time_pts_s.mean * 1000)} ms) **one frame changes the estimated height by ${f1(J.quantisation.height_change_for_one_frame_cm_at_mean_flight)} cm**. Differences between trials smaller than this cannot be resolved.`),

  H2("4.2  Hardware and acquisition"),
  P("The system uses a Raspberry Pi 3B+, a Raspberry Pi Camera Module V2.1 (Sony IMX219 sensor) and a push button between GPIO 17 and ground (internal pull-up). The camera was placed at floor level, facing the participant, so that the lower part of the image always contains both feet and the floor line (Figure 11). Video is recorded at 640 × 480 pixels with a requested frame duration of 16 667 µs (60 fps); the actual per-frame sensor timestamps are logged in parallel so that flight time can be computed from measured time rather than from the nominal rate."),
  ...figurePair("photo_jump_camera_setup.jpg", "photo_jump_recording_session.jpg", 16, "Recording set-up: the Pi and camera at floor level (left) and a recording session seen from behind the participant (right) (frames from `media/squat_jump/IMG_7204.MOV` and `IMG_7202.MOV`)."),

  H2("4.3  Software architecture"),
  P("The program `main.py` asks for body mass and push-off distance, waits for a first button press to start recording and a second one to stop, then runs the analysis (Figure 12). The detector classifies each frame as *contact* or *flight*, finds the most reliable contact → flight → contact sequence and passes the take-off and landing frames to the mechanics module. If no sequence is confident enough, an OpenCV review window opens, in which the operator scrolls frame by frame and clicks TAKE-OFF, LANDING and ACCEPT. Every result is saved as JSON and CSV, together with an annotated video marking the selected events."),
  ...figure("diagram_jump_pipeline.png", 16, "Processing pipeline of the squat-jump program, with the offline training path and the manual-review fallback."),

  H2("4.4  Training dataset and annotation"),
  P(`The script \`record_tr_videos.py\` recorded 20 videos of 5 s (291 frames, 640 × 480, 60 fps) with \`rpicam-vid\`, saving per-frame presentation timestamps and multiplexing them into the MP4 file. The same participant performed the 20 jumps under deliberately varied conditions (Figure 13): barefoot (3 videos), shoes (8), socks (9), and dimmer lighting for the last four videos.`),
  ...figure("fig_dataset_overview.jpg", 13.5, "The 20 training videos (frame 30 of each), with footwear and mean grey level of the detection region."),
  P("Take-off was defined as the first frame in which neither foot touches the ground, and landing as the first frame in which a foot touches the ground again. For each video, we noted by hand the two frames on either side of each transition plus a few frames during flight (Figure 14), giving **168 labelled frames** (80 *contact*, 88 *flight*) in `annotations.csv`. These annotations are both the training data of the classifier and the reference for its validation."),
  ...figure("photo_annotation_notebook.jpg", 7, "Hand annotation of transition frames in the lab notebook (videos jump_01 to jump_06)."),

  H2("4.5  Contact/flight classifier"),
  P("Each frame is cropped to a fixed region of interest (ROI) covering the bottom 38 % of the image, converted to grey levels, resized to 320 × 96 pixels and normalised to [0, 1]. A linear support vector machine (scikit-learn `LinearSVC`, C = 0.1, balanced classes, after feature standardisation) learns to separate contact (+1) from flight (−1). Each labelled frame is augmented with a darker (× 0.75) and a brighter (× 1.2 + 0.04) copy to improve robustness to lighting. At run time, the frame scores are smoothed over 5 frames. A jump is accepted only if a flight run of at least 3 frames is followed by a contact run of at least 3 frames, with a mean score margin of at least 0.15. Among the valid sequences, the one with the largest margin is kept."),
  ...figure("fig_jump_keyframes.png", 16, "Key frames of jump_01 with the detector ROI (orange): squat position, last contact, take-off, mid-flight and landing."),

  H2("4.6  Results"),
  H3("Reference performance (20 annotated jumps)"),
  P(`Using the annotated events, the measured frame timestamps and the participant's inputs from the demonstration (m = ${J.inputs.mass_kg} kg, d = ${f0(J.inputs.push_off_distance_m * 100)} cm, assumed identical for every trial), the mechanics module gives the values in Table 3. Computing flight time from the nominal 60 fps instead of the measured timestamps would change it by at most ${f1(J.nominal60_minus_pts_flight_time_ms.max_abs)} ms, so the camera rate was close to nominal.`),
  ...table(["Indicator", "Mean ± SD", "CV", "Min – max"], [
    ["Flight time (ms)", `${f0(R.flight_time_pts_s.mean * 1000)} ± ${f0(R.flight_time_pts_s.sd * 1000)}`, `${f1(R.flight_time_pts_s.cv_percent)} %`, `${f0(R.flight_time_pts_s.min * 1000)} – ${f0(R.flight_time_pts_s.max * 1000)}`],
    ["Jump height (cm)", `${f1(R.jump_height_cm.mean)} ± ${f1(R.jump_height_cm.sd)}`, `${f1(R.jump_height_cm.cv_percent)} %`, `${f1(R.jump_height_cm.min)} – ${f1(R.jump_height_cm.max)}`],
    ["Take-off velocity (m/s)", `${f2(R.takeoff_velocity_m_s.mean)} ± ${f2(R.takeoff_velocity_m_s.sd)}`, `${f1(R.takeoff_velocity_m_s.cv_percent)} %`, `${f2(R.takeoff_velocity_m_s.min)} – ${f2(R.takeoff_velocity_m_s.max)}`],
    ["Mean push-off force (N)", `${f0(R.mean_push_force_N.mean)} ± ${f0(R.mean_push_force_N.sd)}`, `${f1(R.mean_push_force_N.cv_percent)} %`, `${f0(R.mean_push_force_N.min)} – ${f0(R.mean_push_force_N.max)}`],
    ["Mean push-off power (W)", `${f0(R.mean_push_power_W.mean)} ± ${f0(R.mean_push_power_W.sd)}`, `${f1(R.mean_push_power_W.cv_percent)} %`, `${f0(R.mean_push_power_W.min)} – ${f0(R.mean_push_power_W.max)}`],
    ["Mean power per kg (W/kg)", `${f1(R.mean_push_power_W_kg.mean)} ± ${f1(R.mean_push_power_W_kg.sd)}`, `${f1(R.mean_push_power_W_kg.cv_percent)} %`, `${f1(R.mean_push_power_W_kg.min)} – ${f1(R.mean_push_power_W_kg.max)}`],
  ], [5.2, 3.6, 2.0, 3.6], "Squat-jump indicators from the 20 hand-annotated videos (same participant)."),
  ...figure("fig_jump_heights.png", 15, "Jump height per trial (dashed line: mean; grey band: ± 1 SD) and the same heights grouped by recording condition (identical, frame-quantised values are spread sideways)."),
  P(`Flight times took only ${new Set([24, 25, 26, 27, 28, 29]).size} distinct values (24 to 29 frames), which is why heights cluster in steps of about ${f1(J.quantisation.height_change_for_one_frame_cm_at_mean_flight)} cm. Part of the trial-to-trial variability (CV ${f1(R.jump_height_cm.cv_percent)} %) is therefore measurement quantisation rather than performance; the footwear changes are a further possible source that this design cannot separate.`),
  H3("Validation of the automatic detector"),
  P("Testing a classifier on the videos it was trained on gives an optimistic picture. We therefore used **leave-one-video-out (LOVO)** validation: for each of the 20 videos, a model was retrained on the annotations of the other 19 with the exact same recipe, then run with the unchanged detection logic on the held-out video, and the detected frames were compared with the annotations (Table 4, Figures 17–18)."),
  ...table(["Criterion", "Result"], [
    ["Videos accepted automatically (margin ≥ 0.15)", `${D.accepted_automatically} / ${D.videos}`],
    ["Both events exactly on the annotated frame", `${D.both_events_exact} / ${D.videos}`],
    ["Both events within ± 1 frame", `${D.both_events_within_1_frame} / ${D.videos}`],
    ["Both events within ± 2 frames", `${D.both_events_within_2_frames} / ${D.videos}`],
    ["Wrong jump selected (error > 10 frames)", `${D["wrong_jump_selected (error > 10 frames)"].length} / ${D.videos} (${D["wrong_jump_selected (error > 10 frames)"].join(", ") || "none"})`],
    ["Frame-level accuracy on held-out labelled frames", `${f1(D.mean_annotated_frame_accuracy * 100)} %`],
    ["Flight-time error, median |·| / max |·|", `${f1(D.flight_time_error_ms.median_abs)} ms / ${f0(D.flight_time_error_ms.max_abs)} ms`],
    ["Jump-height error, median |·| / max |·|", `${f1(D.height_error_cm.median_abs)} cm / ${f1(D.height_error_cm.max_abs)} cm`],
  ], [10, 6], "Leave-one-video-out validation of the automatic event detector."),
  ...figure("fig_detector_lovo.png", 14.5, "Event-timing errors of the automatic detector on each held-out video (detected minus annotated frame)."),
  ...figure("fig_detector_score_example.png", 14, "Frame-by-frame SVM score for jump_01 computed by a model that never saw this video; the shaded band is the annotated flight phase. After frame ≈ 190 the participant walks towards the camera and the score drifts below zero."),
  P(`The detector found the correct jump in ${D.videos - D["wrong_jump_selected (error > 10 frames)"].length} of 20 unseen videos, with a median height error of ${f1(D.height_error_cm.median_abs)} cm. Two weaknesses appear. First, the acceptance margin does not protect against **false jumps**: in jump_07 the foot movements after landing produced a second contact → flight → contact pattern with a larger margin, which was selected instead of the real jump. Figure 18 shows the same drift of the score below zero when the participant walks towards the camera after the jump. Second, errors of 3–5 frames on at least one event occur in four videos (jump_03, jump_09, jump_15 and the dim-light jump_20), shifting the estimated height by 6–12 cm. The margin threshold rejected none of the 20 videos, so it did not send these doubtful cases to manual review. All videos were filmed in the same room with the same camera position, so these figures describe performance within this setting only; during the sessions, the detector proved sensitive to lighting, camera orientation and field of view.`),
  H3("End-to-end run on the Pi (14 October)"),
  P("In the recorded demonstration (66 kg, 31 cm), the automatic detection did not return a confident sequence, so the manual review window opened, as designed (Figure 19). The operator selected take-off at frame 172 and landing at frame 197. Because the logged sensor timestamps could not be aligned one-to-one with the 336 decoded frames, the program fell back to the nominal 60 fps and labelled the result accordingly. Results: flight time 0.4167 s, jump height 21.3 cm, take-off velocity 2.04 m/s, mean force 1092 N, mean power 1116 W, i.e. 16.9 W/kg."),
  ...figurePair("screen_jump_manual_review.jpg", "screen_jump_results.jpg", 16, "Demonstration of 14 Oct: manual event review window (left) and exported `results.csv` (right)."),

  H2("4.7  Squat Jump Explorer dashboard"),
  P("No dashboard existed for this project, so we built **Squat Jump Explorer** (`squat_jump_pi/dashboard/jump_dashboard.html`), a single offline HTML file that needs no installation. It shows the indicators of all trials, with a per-trial view (thumbnails of the last-contact, mid-flight and landing frames) and the detector's score trace with its detected events (Figure 20). Body mass and push-off distance can be edited, and every force and power value is recomputed instantly. Each jump is colour-coded against the participant's own mean ± 1 SD, which is the first element of a feedback loop. A `results.json` file produced by the Pi program can be loaded to compare a new session with the reference set: loading the 14 Oct session (transcribed from the screen recording in `example_session_20261014_results.json`) reproduces the force, power and power-per-kg values computed on the Pi to the last digit."),
  ...figure("screen_jump_dashboard.png", 14, "Squat Jump Explorer: participant inputs, summary indicators, height per trial colour-coded against the participant's range, and the selected trial."),

  // ------------------------------------------------- 5 Discussion
  H1("5  Discussion"),
  H2("5.1  The two chains, link by link"),
  ...table(["Link", "Project A — ECG", "Project B — Squat jump"], [
    ["Sensor", "Three chest electrodes; lead placement and skin contact proved critical (failed run of 6 Oct)", "Camera at floor level; framing, lighting and footwear change what the classifier sees"],
    ["Conditioning & ADC", "Analogue front-end + MCP3008 10-bit; 52 % of the range used, no clipping on 16 Sep", "Sensor ADC and H.264 compression; 640 × 480 is enough to see the feet"],
    ["Timing", "Software timing (v1.2.0) → DMA hardware clock (v2.0.0)", "60 fps with sensor timestamps; 16.7 ms frame ≈ 1.8 cm of height"],
    ["Processing", "Zero-phase 0.5–40 Hz band-pass; 50 Hz residue remains", "Fixed ROI + linear SVM on raw pixels; 5-frame smoothing"],
    ["Indicators", "R peaks, RR, HR; HRV shown only as illustration (10 s)", "Flight time → height, velocity, force, power (model-based)"],
    ["Decision", "Range checks and warnings; refuses to output HR on invalid input", "Margin threshold → manual review; false-jump case not caught"],
    ["Feedback", "Post-hoc figure and ECG Explorer", "Post-hoc results, annotated video and Squat Jump Explorer"],
  ], [2.6, 7.0, 7.0], "Critical summary of both chains along the biofeedback model."),
  P("Both chains are complete from sensor to user, but neither closes the loop in real time yet. The feedback is delivered after the recording (knowledge of results) rather than during the movement or the heartbeat, so the 100–300 ms latency budget of real-time biofeedback was not tested. The most valuable lesson is methodological: each project produced a convincing number at least once *and* a failure case, and in both projects the software design (input checks, explicit warnings, manual fallback, traceable files) made the failures visible instead of hiding them."),
  H2("5.2  Limitations"),
  bullet("**Single participant, short recordings:** one ECG recording of 10 s and 20 jumps of one person do not allow any physiological or between-subject conclusion."),
  bullet("**No gold standard:** heart rate was not compared with a clinical ECG or chest strap, and jump height, force and power were not compared with a force plate. Only the detector's timing was validated, against hand annotations."),
  bullet("**Model assumptions:** force and power depend on a push-off distance entered by hand and assumed identical for all trials."),
  bullet("**Detector generalisation:** one room, one camera position, one participant. A pixel-based linear classifier with a fixed ROI is sensitive to framing and lighting."),
  H2("5.3  Perspectives"),
  bullet("**ECG:** add a 50 Hz notch filter and shielded, short leads; record at least 5 min for standard HRV; install NeuroKit2 for P/T delineation; stream R-peak events in real time to a GPIO LED or a sound for heart-rate or breathing biofeedback."),
  bullet("**Jump:** reject secondary jumps (e.g. keep the first sequence with a plausible flight time), send low-margin or out-of-range cases to manual review, train on more participants and rooms, consider pose-estimation key points instead of raw pixels, add counter-movement-jump and squat modules, and validate against a force plate."),
  bullet("**Biofeedback loop:** display the result zone of each jump on the Pi screen or with a GPIO LED immediately after landing, turning the existing post-hoc analysis into a feedback tool for training."),

  // ------------------------------------------------- 6 Conclusion
  H1c("6  Conclusion"),
  P(`Starting from the basics of the Raspberry Pi and digital acquisition, we built two complete measurement and analysis chains. The ECG chain moved from software-timed to hardware-timed (DMA) sampling and produced a valid recording with ${A.r_candidates} detected beats at ${f1(A.median_hr_bpm)} bpm. It also revealed a strong 50 Hz interference that sets the next improvement. The squat-jump chain turns 60-fps video into flight time, height, force and power, with an automatic detector whose honest out-of-sample validation (${D.both_events_within_1_frame}/20 videos within ±1 frame, one wrong jump) shows both its potential and the need for the manual-review fallback. Two dashboards, ECG Explorer and Squat Jump Explorer, make these results readable without any programming knowledge.`),

  // ------------------------------------------------- Contributions + AI
  H2("Contributions and use of AI tools"),
  P("This was a group project to which the three members contributed equally. **Victor Salvat** designed and built the ECG Explorer dashboard. **Joël Singer** mainly wrote the scripts of the squat-jump project. **Baptiste Augros** designed the ECG acquisition script, ensured the synthesis and integration between both projects and wrote this report."),
  P("Parts of the code were drafted with the help of AI assistants; every script was reviewed, tested on the Raspberry Pi and integrated by the group. The offline analyses, the Squat Jump Explorer dashboard and this report were also prepared with AI assistance, from the group's data and recordings."),

  // ------------------------------------------------- References
  H2("References"),
  ...[
    "Bosco, C., Luhtanen, P., & Komi, P. V. (1983). A simple method for measurement of mechanical power in jumping. *European Journal of Applied Physiology and Occupational Physiology*, 50(2), 273–282.",
    "Despaux, G. (2026). *Measurement and Analysis Chain for Biofeedback — preparatory course notes*. Université de Montpellier, UFR STAPS.",
    "Makowski, D., Pham, T., Lau, Z. J., Brammer, J. C., Lespinasse, F., Pham, H., Schölzel, C., & Chen, S. H. A. (2021). NeuroKit2: A Python toolbox for neurophysiological signal processing. *Behavior Research Methods*, 53(4), 1689–1696.",
    "Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research*, 12, 2825–2830.",
    "Samozino, P., Morin, J.-B., Hintzy, F., & Belli, A. (2008). A simple method for measuring force, velocity and power output during squat jump. *Journal of Biomechanics*, 41(14), 2940–2945.",
    "Shannon, C. E. (1949). Communication in the presence of noise. *Proceedings of the IRE*, 37(1), 10–21.",
    "Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology (1996). Heart rate variability: standards of measurement, physiological interpretation and clinical use. *Circulation*, 93(5), 1043–1065.",
    "Virtanen, P., et al. (2020). SciPy 1.0: Fundamental algorithms for scientific computing in Python. *Nature Methods*, 17, 261–272.",
  ].map(r => new Paragraph({ children: runs(r, { size: 19 }), alignment: AlignmentType.JUSTIFIED,
    indent: { left: 400, hanging: 400 }, spacing: { after: 80 } })),

  // ------------------------------------------------- Appendix
  H1("Appendix A — Repository and reproducibility"),
  P("The repository is organised by project. Each folder contains the code that ran on the Pi, the data it produced and the offline analyses used in this report."),
  ...table(["Path", "Content"], [
    ["`ecg/ecg_lab_merged.py`", "ECG acquisition and analysis v2.0.0 (modes: `demo`, `mcp3008`, `file`)"],
    ["`ecg/legacy/ScriptECG.py`", "First UDP streaming script (13 Sep)"],
    ["`ecg/data/run_20260916T104943Z_mcp3008/`", "Recording of 16 Sep (v1.2.0 outputs) and its v2.0.0 re-analysis (`…_reanalysed_v2/`)"],
    ["`ecg/analysis/ecg_signal_quality.py`", "Timing, ADC usage, spectrum, notch test and HRV figures (Figures 3, 5–7)"],
    ["`ecg/dashboard/ecg_explorer/`", "Offline copy of ECG Explorer (`index.html`)"],
    ["`squat_jump_pi/`", "Pi program (`main.py`, `detector.py`, `mechanics.py`, `report.py`), recorder, trainer, model, config"],
    ["`squat_jump_pi/training_dataset/`, `annotations.csv`", "20 training videos and 168 frame labels"],
    ["`squat_jump_pi/analysis/`", "Reference metrics, LOVO validation, dataset overview (Tables 3–4, Figures 13–18)"],
    ["`squat_jump_pi/dashboard/`", "Squat Jump Explorer (`jump_dashboard.html`) and its build script"],
    ["`media/`", "Set-up videos and photos, annotation notebook, screen recordings of the demonstrations"],
    ["`report/`", "This report, its figures and the scripts that build them"],
  ], [6.6, 9.4], "Repository map."),
  P("**Not included:** the 14 ECG run folders and the 8 `jump_data` session folders that remained on the Raspberry Pi were not exported, except the 16 Sep ECG recording above. Results of the 6 Oct ECG and 14 Oct jump demonstrations are therefore documented from the screen recordings in `media/demo_recordings/`. NeuroKit2 was not installed on the analysis computer, so the re-analysis used the SciPy fallback delineation."),
  P("**Reproducing the analyses** (Python 3 with NumPy, SciPy, Matplotlib, OpenCV, scikit-learn, joblib):"),
  bullet("`python3 ecg/ecg_lab_merged.py --mode file --input ecg/data/run_20260916T104943Z_mcp3008/raw.csv`"),
  bullet("`python3 ecg/analysis/ecg_signal_quality.py ecg/data/run_20260916T104943Z_mcp3008 --out ecg/analysis/output`"),
  bullet("`python3 squat_jump_pi/analysis/jump_dataset_analysis.py` then `python3 squat_jump_pi/dashboard/build_dashboard.py`"),
];

// --------------------------------------------------------------- document --
const doc = new Document({
  creator: "Baptiste Augros, Victor Salvat, Joël Singer",
  title: "From Sensor to Feedback — Analysis Chain for Biofeedback",
  description: "Course report, Université de Montpellier",
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: FONT, size: 22 }, paragraph: { spacing: { after: 120, line: 276 } } } },
    paragraphStyles: [
      { id: "TOC1", name: "toc 1", basedOn: "Normal", next: "Normal", run: { bold: true, size: 21 },
        paragraph: { spacing: { before: 100, after: 20, line: 240 } } },
      { id: "TOC2", name: "toc 2", basedOn: "Normal", next: "Normal", run: { size: 20 },
        paragraph: { spacing: { before: 0, after: 20, line: 240 }, indent: { left: 360 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, color: NAVY, font: FONT },
        paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 0, keepNext: true,
          border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: ACCENT, space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, color: ACCENT, font: FONT },
        paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1, keepNext: true } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, color: NAVY, font: FONT },
        paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 2, keepNext: true } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [
    { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 500, hanging: 260 } } } },
    { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 900, hanging: 260 } } } }] }] },
  sections: [{
    properties: {
      titlePage: true,
      page: { size: { width: 11906, height: 16838 }, margin: { top: 1418, bottom: 1418, left: 1418, right: 1418, header: 700, footer: 700 } },
    },
    headers: {
      first: new Header({ children: [new Paragraph({ children: [] })] }),
      default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
        border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: LINE, space: 4 } },
        children: [new TextRun({ text: "Analysis Chain for Biofeedback  ·  Augros, Salvat, Singer", size: 16, color: GREY })] })] }),
    },
    footers: {
      first: new Footer({ children: [new Paragraph({ children: [] })] }),
      default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ children: ["Page ", PageNumber.CURRENT, " / ", PageNumber.TOTAL_PAGES], size: 18, color: GREY })] })] }),
    },
    children: content,
  }],
});

const out = path.join(ROOT, "report", "Report_Analysis_Chain_for_Biofeedback.docx");
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(out, buf); console.log("Wrote " + out + " — " + figN + " figures, " + tabN + " tables"); });
