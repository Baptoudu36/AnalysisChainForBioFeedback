# Targeted robustness corrections

AI-assisted corrections coordinated by Victor Salvat on 21–22 October 2026. The branch carries the previously tested production files without new detector training or scientific parameter changes.

| Area | Correction | Evidence |
|---|---|---|
| ECG quality | Empty/invalid RR gives unavailable statistics, single RR keeps only defined quantities; short signals retain available timing/spectrum; strict JSON rejects nonfinite outputs. | Twelve regression tests, including both retained acquisitions. |
| Jump timing | Validate the whole timestamp sidecar, event bounds and nominal fps; expose fallback reasons and unverified physical alignment. | Timestamp and index cases in tests/test_robustness.py. |
| Jump acceptance | Preserve automatic proposals, require explicit manual acceptance, and keep cancellation/unavailable UI pending without accepted mechanical metrics. | Fixture review decisions and twenty stored-score comparisons. |
| ECG dashboard | Reject invalid signal/RR/container inputs, preserve the previous session on failure, show provenance and unavailable RR, remove captured page fragment. | evidence/software/ecg_browser_results.json. |
| Jump dashboard | Preserve imported provenance, separate session mass/distance from reference controls, validate inputs, fix narrow layout and reject legacy OK_WITH_REVIEW_REQUIRED imports. | evidence/software/jump_browser_results.json and responsive_results.json; finalization evidence records original-session import. |

The selection algorithm and mechanical equations are unchanged. A mandatory review gate does not improve detector accuracy. Historical manual exports are not newly confirmed events. Stored browser assertions are 41 ECG and 100 jump checks; these results do not certify hardware, physiological accuracy or the manual OpenCV workflow. No dependency was modified to address the two unreproduced iframe errors.

Portable offline commands and the scope of their fixture-based decisions are in [tests/README.md](../tests/README.md). The software evidence retains its original execution dates. GUI and hardware limitations remain documented in the candidate report and manual protocol.
