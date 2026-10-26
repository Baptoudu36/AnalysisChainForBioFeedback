# Recovered jump sessions

22 October 2026. Original delivery: `joel-drive-biofeedback-jump-data.zip`, supplied by Victor after Joël reported adding jump_data to Drive on 21 October. Archive SHA-256: `82bd7f5d0634acabc0834b56b5ce8b19a79322ad84e62d7e1e49ae4a29ee782f`. The archive is retained in the course sources; this submission includes every extracted payload byte unchanged. `jump_delivery_manifest.csv` maps the 42 archive members to delivered paths and hashes.

Seven directories each contain recording.h264, recording.mp4, annotated_review.mp4, timestamps.csv, results.json and results.csv. No standalone metadata.json, acquisition log, subject identification, calibration record, push-off measurement description, ECG data or eighth jump session is present. Folder names encode local date/time without a timezone or verified wall clock. Sensor timestamps are a separate monotonic clock; their values do not establish calendar time.

| Session (14 October) | Frames / timestamp rows | Event indices | Mass / distance | Saved height | Saved method/status |
|---|---:|---|---|---:|---|
| jump_20261014_035847 | 336 / 338 | 172 / 197 | 66 kg / 31 cm | 21.289 cm | historical manual selection |
| jump_20261014_044047 | 184 / 187 | 82 / 101 | 65 kg / 34 cm | 12.297 cm | historical manual selection |
| jump_20261014_044853 | 340 / 343 | 193 / 250 | 66 kg / 31 cm | 110.669 cm | automatic, review required |
| jump_20261014_045210 | 165 / 169 | 20 / 45 | 66 kg / 31 cm | 21.289 cm | historical manual selection |
| jump_20261014_051434 | 161 / 165 | 91 / 124 | 80 kg / 35 cm | 37.094 cm | historical manual selection |
| jump_20261014_052005 | 258 / 261 | 197 / 227 | 70 kg / 40 cm | 30.656 cm | historical manual selection |
| jump_20261014_052459 | 124 / 127 | 66 / 98 | 72 kg / 37 cm | 34.880 cm | historical manual selection |

The six manual exports record historical manual selections; they are not newly accepted reviews. The automatic 044853 export has `OK_WITH_REVIEW_REQUIRED`, T = 0.95 s and h = 110.669 cm. Selected-frame inspection shows foot movement/walking in the nominated interval rather than establishing a single ballistic flight. It must not be treated as confirmed performance. No replacement event pair or participant identity was inferred.

All seven MP4s decode at 640 × 480; saved frame counts agree. CSV and JSON scalar/string fields agree, and independent recalculation of T, h, v, F and P matches exactly at Python float precision. All sidecars have sequential callback indices and strictly increasing integer sensor timestamps, but contain 2–4 more rows than decoded frames. The corrected timing routine reports `timestamp_frame_count_mismatch` for every session and preserves nominal 60-fps fallback. This is evidence for the software fallback, not a physical alignment correction. H.264/MP4 decoded pixels were compared separately; container/Annex-B byte differences must not be mistaken for changed imagery.

## The 035847 demonstration and screen transcription

The recovered `1stProject-SquatJump/jump_data/jump_20261014_035847/results.json` is now the primary source. Every one of the 21 fields transcribed in `dashboard/example_session_20261014_results.json` agrees exactly; the original additionally includes `ok` and `model_assumptions`. The transcription is preserved unchanged as a secondary historical artifact, including its then-correct statement that the original remained on the Pi. The original is also consistent with the session name and 172/197, 336-frame, 66 kg/31 cm results shown at 161.3 s in `MediaSources/Demo recordings/SquatJump script trial.mp4`. The recovered recording shows the same indoor bedroom setting as the screen demonstration; the six later recordings show a classroom setting. Do not equate folder clocks with independently timed classroom presentations.

The 31 cm value is still an input parameter. None of the new files records the landmarks, instrument or phase used to measure it. The 20 training CMJs are attributed to Joël by Victor’s testimony; that account is not automatically extended to all seven recovered sessions. The 035847 screen demonstration was previously attributed to Joël. Identities of the six other sessions, weighing methods and distances require group confirmation.

Seven session sets have been recovered, not the eight previously mentioned by the report. Without an authoritative list, the identity or contents of any remaining session are unknown. The 6 October ECG raw session is still absent. These sessions supplement the archive; they do not enlarge the 20-video training/LOVO dataset or change its statistics. No LOVO training was rerun.
