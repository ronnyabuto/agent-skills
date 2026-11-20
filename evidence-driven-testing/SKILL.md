---
name: evidence-driven-testing
description: Record a video of live desktop or GUI interaction as proof, using the bundled annotated screen recorder. Use when asked to record, film or demonstrate UI behavior on video. Not for ordinary tests, screenshots or measured probes.
compatibility: Python 3, a drivable GUI, and ffmpeg/ffprobe with libx264 and the ass filter.
metadata:
  version: "2.0"
---

# Evidence-Driven Testing

The recorder is `${CLAUDE_SKILL_DIR}/scripts/evidence.py`. Run
`python3 ${CLAUDE_SKILL_DIR}/scripts/evidence.py doctor` first and check both
toolchain readiness and `capture_ready`, then follow
[the recorder guide](references/recorder.md) for capture, annotation and
verification.

Save the script, the video and the observed results in a gitignored
`.artifacts/<task>/` folder. A rendered video's `verified` flag establishes
media validity, not application correctness.

Never present synthetic frames, stitched playback or static screenshots as a
recording of live interaction. If capture is unavailable, mark the check
untested and report why. Keep credentials, customer data and unrelated windows
out of captures, and publish a recording only where the user authorized it.
