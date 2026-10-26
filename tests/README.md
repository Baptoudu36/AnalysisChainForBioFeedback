# Offline regression tests

From the repository root, with Python 3.10 and the numerical dependencies in requirements-offline.txt:

```sh
python -B tests/test_robustness.py
python -B tests/check_saved_scores.py
```

The twelve existing robustness tests have been relocated with only input/output path changes: retained ECG acquisitions are read from data/, and generated fixtures/plots use a temporary directory under the ignored outputs/ folder. They cover empty/single/invalid RR, short signals, real archived quality results, timestamps, review decisions and pending exports. The second script checks twenty retained rounded baseline score traces against their recorded event pairs and verifies the pending-review gate. The earlier old/new detector comparison remains in evidence/software/saved_score_review.json. No serialized model, training or graphical selector is invoked by these commands.

Browser assertions and responsive checks are retained execution evidence under evidence/software/. They are dated results, not newly executed browser tests on this branch. Actual OpenCV navigation/correction/acceptance/export/cancel and Pi retesting remain outside these tests.
