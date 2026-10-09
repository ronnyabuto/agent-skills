# Optional GUI recorder

Locate scripts/evidence.py relative to this skill's installed directory. Quote script and output paths. The recorder is retained from the attributed upstream collection; see the plugin's PROVENANCE.md.

```bash
python3 "$EVIDENCE" doctor
python3 "$EVIDENCE" start --output "$OUTPUT" --title "Requested behavior"
python3 "$EVIDENCE" annotate "$SESSION" --type test_start --message "It saves the setting"
python3 "$EVIDENCE" annotate "$SESSION" --type assertion --result passed --message "Setting survives reload"
python3 "$EVIDENCE" stop "$SESSION"
```

EVIDENCE is the installed script path. OUTPUT is a task-specific artifact directory. SESSION is the returned session path. Run doctor first: `ready` concerns FFmpeg, libx264 and ASS; `capture_ready` concerns a usable display. Read both. Linux X11 requires DISPLAY, Wayland requires wf-recorder plus compositor support, macOS requires screen permissions, and Windows uses gdigrab. Do not claim a supported capture path when doctor reports none.

Start capture, perform the actual interactions using available computer-use/browser tools, annotate meaningful state changes and stop. Keep messages under the recorder's 80-character limit. Maximize or crop the intended surface as needed; avoid unrelated sensitive content. Do not use the synthetic test source as UI proof.

Inspect the video at assertion timestamps and complete report.md caveats. `verified: true` means the output media was rendered and probed, not that application assertions are correct. For finalization_failed, inspect the cause and retry stop only when the recorder has finished. For recorder_lost/untracked process cases, follow the script's diagnostics; never signal an arbitrary bare PID.

Keep the report, manifest and video together. Upload only to the destination and audience the user authorized, and verify the published artifact before claiming it was posted. Without a usable recorder, switch to screenshots/probes and report the missing recording capability.
