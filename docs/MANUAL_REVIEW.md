# Remaining manual review

Use a desktop session with a visible display and the GUI package opencv-python (do not install it together with opencv-python-headless). Raspberry Pi hardware is not needed for this file-only check. From the package root:

```sh
python tools/review_jump.py --session 1stProject-SquatJump/jump_data/jump_20261014_035847 --out outputs/manual_035847
```

1. Check that the video and prefilled event indices appear. Move with the Frame slider and n/p keys; verify forward and backward movement.
2. In a disposable test output, choose a different frame with t (TAKE-OFF), set landing with l, and select ACCEPT (a or Enter). Inspect the exported JSON/CSV and annotated MP4. Original proposal and confirmed events must remain separate, with corrected status when indices differ.
3. Repeat into another new output without changing indices. The status should be confirmed. This verifies UI mechanics only; document an actual scientific event review separately.
4. Repeat into a third new output and click CANCEL or press Escape. The JSON must remain pending, with the proposal preserved and no accepted mechanical metrics or annotated result.

Do not overwrite a recovered session. Record OS, Python/OpenCV versions, tested controls and output names. The wrapper refuses existing output folders and does not load a serialized model. A real review must inspect the whole sequence; the automatic 044853 proposal is not a validated flight, and recovered manual selections still require group review before performance interpretation.

Other human checks before submission: agree the report/contributions and media sharing; clarify push-off-distance measurement and six recovered-session participants; confirm whether Victor’s demonstration matches the 6 October clip; confirm deadline and submission route. Pi hardware, physical timing, independent reference measurements, NeuroKit2 and additional browsers remain unverified.
