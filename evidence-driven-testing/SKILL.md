---
name: evidence-driven-testing
description: >
  Choose realistic verification and capture reproducible proof of behavior:
  annotated UI recordings, headless screenshots, or measured probes. Use when
  asked to prove a fix, demonstrate improvement, design realistic tests, or
  assess which tests to retain or replace. Scale checks to the changed behavior;
  routine edits do not automatically need recordings or new test files.
compatibility: Optional desktop recording requires Python 3, a drivable GUI, and ffmpeg/ffprobe with libx264 and the ass filter. Headless capture uses the project's browser tooling or a scripted probe.
metadata:
  version: "1.4"
---

# Evidence-Driven Testing

Choose evidence proportional to the claim. Existing checks or a focused probe
usually suffice for a small local change. Add permanent tests for meaningful
uncovered behavior or regression risk; preserve useful older cases. For test
selection, realistic scenarios or replacing tests, read
[Useful tests](references/useful-tests.md). A test-design request alone does not
require starting the app or recording it.

1. Define the observable behavior or metric, starting conditions and assertions.
   Identify the revision, uncommitted changes, environment and tested process.
   For a fix, capture the old failure when reproducible; otherwise disclose its
   absence. Confirm a running server belongs to this checkout before probing it.
2. Choose one route and read only that reference:
   - [Desktop recording](references/recorder.md) for a live GUI interaction.
     The helper is `${CLAUDE_SKILL_DIR}/scripts/evidence.py`; run its `doctor`
     first and inspect both toolchain readiness and `capture_ready`.
   - [Headless capture and probes](references/headless.md) for browser
     automation, screenshots, APIs, SQL counts, performance or agent behavior.
3. Drive the actual test and save repeatable scripts plus observed results in
   a gitignored `.artifacts/<task>/` folder. Record meaningful assertions as
   `passed`, `failed` or `untested` with a reason. Observe the relevant state
   before marking it passed. Include persisted outcomes and failure/recovery
   paths when they are part of the claim.
4. Review the evidence and report the exact check, result, artifact paths and
   limitations. A rendered video's `verified` flag establishes media validity,
   not application correctness. Capture complements relevant tests and builds.

Claude Code's bundled `/run` and `/verify`, or an existing project launch skill,
can supply the launch and interaction recipe. Reuse that recipe and existing
results when they cover the claim; this skill adds assertion records and
reproducible evidence. Avoid running a second full verification workflow for
checks that have already passed.

Stop once the requested behavior and relevant checks pass. Repeat or broaden
verification only after a change, failure or unresolved risk justifies it.

Save locally and deliver to the requester. Publish to a PR, tracker or external
host only when authorized; naming a PR as context alone does not authorize an
upload or comment. Keep credentials, personal/customer data and unrelated
windows out of captures. Evaluate alternatives and permissions before installing
system packages or changing project dependencies for evidence capture.

Never present synthetic frames, stitched playback or static screenshots as a
recording of live interaction. If capture is unavailable, mark that check
untested and retain the meaningful evidence that can be obtained.
