# Selected execution evidence

Historical outputs stay in each project's analysis/output. Reproduction comparisons and baseline/convergence output/fits are separate here. The copied numerical environment record documents the executed environment, not a portable installation path. Full transient runtimes, logs, backups and trained fold models are excluded. No historical model is loaded by the package checker.

Software evidence: 12 Python tests, 20 unchanged saved-score proposal pairs, 41 ECG assertions and 100 jump assertions. The six responsive stages passed. Original 035847 import was checked. A separate 22 October iframe-origin investigation reproduced no errors; its only MutationObserver call came from Playwright on a valid document. It does not resolve the exact source of the two earlier source-less host errors; no dependency was changed.

The finalization directory contains seven-session arithmetic/timestamp/video checks. GUI opening is observed; interaction remains pending. None of these checks is new hardware validation or a new scientific manual review.

## Video references and mechanics — reproduced

Twenty files decode to 291 frames each. All PTS sequences are strictly increasing; annotations bracket each contact/flight transition in adjacent zero-based frames. Take-off is the **first labelled FLIGHT frame**, landing the **first CONTACT frame after the labelled flight**. Victor's uncertainty about remembering this convention is resolved by code/annotation inspection, not by recollection.

FFprobe and OpenCV PTS agree to at most **4.44e-16 s**. The retained stream time base is **1/16000 s**, while observed presentation intervals include the 16/17-ms pattern. The first/last PTS span is 4.84 s and stream duration is 4.856 s; a requested five-second recording and 291/60 nominal duration are distinct descriptions. PTS establish container presentation timing, not an independently calibrated camera clock or sensor/frame alignment.

The independent FFprobe/annotation calculation differs from saved mechanical fields by at most **2.05e-12** in the respective units. The original script's PTS reference summary reproduces exactly at stored precision:

| Indicator | Historical and recalculated mean ± sample SD |
|---|---:|
| Flight time | 442.15 ± 22.67 ms |
| Flight-derived height | 24.0326 ± 2.4545 cm |
| Take-off velocity | 2.16875 ± 0.11120 m/s |
| Conditional model push-off force | 1149.40 ± 51.26 N |
| Conditional model push-off power | 1249.09 ± 119.42 W |
| Conditional model power per mass | 18.9255 ± 1.8094 W/kg |

The saved nominal-60-fps versus PTS flight-time difference also reproduces: mean −0.4833 ms, maximum absolute 1.3333 ms. One extra nominal frame changes height near the mean duration by 1.84135 cm; this is sensitivity, not a validated discrimination threshold.

The implemented identities `h=gT²/8`, `v0=gT/2`, `F=m*g*(1+h/d)` and `P=F*v0/2` were checked independently. For a declared CMJ, flight-based h/v0 remain conditional on ballistic flight and equal COM heights at take-off/landing. The work–energy force could concern an upward phase starting at zero vertical COM velocity, but **the 31 cm value is not established as that concentric-phase displacement**. Constant acceleration is additionally assumed to interpret `v0/2` and the product as time-mean quantities. Numerical reproduction does not validate force/power as measured CMJ performance. A clearly labelled hypothetical distance-sensitivity illustration is stored separately; it changes no baseline input.


## LOVO baseline — unresolved discrepancy

Recipe preserved: ROI `[0,0.62,1,0.40]` clamped to the image; grayscale resize 320×96; pixel values /255; original plus ×0.75 and ×1.20+0.04 augmentations; training-only StandardScaler; LinearSVC balanced classes, C=0.1, random state 42, max_iter=10000, other defaults from the recorded version. Each test video is excluded in full. Scores are smoothed across five frames; minimum flight/contact runs are three frames; stable-margin threshold is 0.15. Margins are not calibrated probabilities.

| Metric | Saved historical | Current baseline |
|---|---:|---:|
| Accepted / rejected videos | 20 / 0 | 20 / 0 |
| Both events exact | 4/20 | 4/20 |
| Both within ±1 frame | 10/20 | **9/20** |
| Both within ±2 frames | 15/20 | **14/20** |
| Wrong sequence, event error >10 frames | jump_07 | **jump_07 and jump_20** |
| Mean per-video annotated-frame accuracy | 83.2639% | **82.5694%** |
| Signed mean flight-time error | +12.5 ms | +13.3333 ms |
| Absolute flight-time error, mean / median / max | 39.1667 / 33.3333 / 150 ms | **50 / 33.3333 / 233.3333 ms** |
| Signed mean height error | +1.84108 cm | +2.34009 cm |
| Absolute height error, mean / median / max | 4.40258 / 3.27 / 19.92656 cm | **5.51472 / 3.27 / 27.795 cm** |
| Convergence-warning entries | 9 in historical log, folds unidentified | **12 identified fits** |

Detected events differ in six videos: `jump_03`, `jump_07`, `jump_08`, `jump_15`, `jump_17`, `jump_20`. Exact per-column comparisons and scores are retained; the discrepancy is not silently accepted as a rounding tolerance. Known environment/build differences and incomplete convergence are plausible contributors, but their separate causal effects have not been isolated. The original outputs remain the historical record; the current outputs are a distinct run.

Warnings occurred in fits holding out **02, 03, 06, 09, 12, 14, 15, 16, 17, 18, 19 and 20**, each reaching 10000 iterations. Full messages, source locations, timing, training-video lists and classifier parameters are in `jump/baseline/fits/*.json`, `folds.json` and logs. The nine historical warnings cannot be assigned to particular folds from that log alone.

### jump_07 and jump_20

For `jump_07`, annotated events are 144/172. The saved detector selected 229/266; the current detector selects **227/267**, errors +83/+95 frames. The current fit terminates at **6931 iterations without a convergence warning**. Its eligible sequence margins include 94/173 (0.30795), 184/203 (0.16356) and 227/267 (0.31626); the maximum-margin rule chooses the last. The annotated flight is not isolated as the intended complete candidate. Frames show post-jump foot movement in the later selected region. Neither a larger iteration cap for warned folds nor the existing margin rule guarantees recovery of the intended jump.

For `jump_20`, reference events are 126/152, saved detection 129/147, current detection **207/219** (errors +81/+67). That fit reaches the cap and warns. This additional false selection is an important instability, not an improved estimate to adopt. The original threshold accepts both wrong-sequence cases.


### Separate convergence experiment

After the complete baseline, a prespecified **max_iter=30000** experiment was launched only for its 12 warning folds, with all remaining parameters/data/exclusions unchanged. Four independent workers are used again. The threefold cap studies solver sensitivity; it is not a search for the saved historical counts. Fits, remaining warnings, changed events and a separately derived aggregate are retained in `jump/convergence_maxiter30000/` and `comparisons/convergence_experiment.csv`.

**Completed:** five of the twelve refits converge (jump_03: 12165 iterations; jump_09: 15015; jump_17: 18770; jump_18: 10578; jump_20: 21155). Seven still reach 30000 and warn (02, 06, 12, 14, 15, 16, 19). Only **jump_20** changes its event pair, from 207/219 to the saved historical 129/147. This directly demonstrates iteration-budget sensitivity in the current environment; it does not isolate every cross-environment difference. jump_07 was not a warning fold and remains wrong.

The clearly labelled combined result (twelve experimental fits plus eight unchanged baseline fits) gives 20 accepted / zero rejected, 4/20 exact, **9/20 within ±1**, **14/20 within ±2**, and one wrong sequence, jump_07. Mean absolute time error is **45 ms**, median 33.3333 ms, maximum 200 ms; mean absolute height error **5.20816 cm**, median 3.27 cm, maximum 27.795 cm. The macro annotated-frame accuracy remains 82.5694%. These are additional experimental results, not a successful recovery of the entire historical LOVO table or a fully converged production model. No experimental model replaces a baseline or historical model.

## ECG replays — eight actual file-mode executions

The two inputs are distinct September acquisitions, not aliases of one recording. The second directory's earlier name is an alias documented by sixteen file/hash correspondences across the two datasets. All replay inputs are copies of the preserved raw CSV and adjacent metadata; file mode retains software-estimated transaction-midpoint timestamps. No new physical sampling occurred.

| Input / source | R candidates | Retained RR | Median HR (bpm) | P / Q / S / T candidates |
|---|---:|---:|---:|---|
| First, saved analysis | 0 | 0 | unavailable | 0 / 0 / 0 / 0 |
| First, early unversioned v1 replay | **0** | **0** | **unavailable** | 0 / 0 / 0 / 0 |
| First, v1.2.0 replay | **10** | **9** | **66.66775** | 0 / 6 / 0 / 0 |
| First, v1.3.0 replay | 10 | 9 | 66.66775 | 0 / 6 / 0 / 0 |
| First, merged replay, SciPy fallback | 10 | 9 | 66.66775 | 0 / 6 / 0 / 0 |
| Second, saved and each of four replays | **11** | **10** | **73.09432** | 0 / 11 / 0 / 0 |

**First acquisition: reproduced with explained version differences.** The early source's R guard compares filtered positive amplitude (~0.17661 V) with six times the high-frequency residual-noise scale (~0.27377 V), and rejects it. v1.2.0 onward instead uses filtered-background scale, with a ~0.12790 V six-times threshold. The filtered arrays between the early source and v1.2.0 are identical in this replay; the threshold change explains the zero-versus-ten-R difference. The early source reproduces the saved no-R warnings. This establishes compatible algorithmic behaviour, not certain authorship/version of the originally unversioned acquisition, nor that the new candidates are true physiological beats.

**Second acquisition: reproduced.** R/Q candidate positions and RR/HR match within tolerances, including the absence of P/S/T markers. This is partial candidate delineation, not confirmation that those waves are absent. Median HR is 73.09432 bpm, mean instantaneous HR 73.15389 bpm and 60/mean(RR) 73.05581 bpm. For the first later-version replay, mean instantaneous HR is 66.86740 bpm, distinct from the median.

v1.2.0 and merged filtered values, candidate matrices and RR files agree for both inputs; v1.3.0 adds inspection output and warning text without changing the candidate results. **NeuroKit2 is absent**; merged `analysis.json` records `scipy-local-extrema`. NeuroKit2/DWT behaviour was **not executed**, and the historical availability of that package is not established by these results. Warnings are compared semantically as well as retained verbatim because wording and fields change across versions.



Host-specific absolute paths in exported evidence were replaced with execution-context labels. Numeric values, model parameters, warnings and outcomes are retained. These paths are provenance, not runtime dependencies.
