# ECG acquisition and analysis

Use the [root instructions](../README.md) for offline replays, quality output and dashboard serving. Both September acquisitions remain original. Later detector versions change the first acquisition's candidate count; replays do not create new acquisitions. All wave labels are exploratory. NeuroKit2 and Pi DMA hardware paths were not rerun; no clinical validation is claimed.

The corrected quality script handles empty/short RR using explicit null/unavailable values. Always set --out and --fig-dir to new locations. Legacy sources are retained for version comparison.
