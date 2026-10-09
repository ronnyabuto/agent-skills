---
name: evidence-driven-testing
description: Capture reproducible screenshots, recordings, or measured probes when asked to prove UI behavior, demonstrate a fix, or compare performance before and after.
metadata:
  requirements: "Python 3 and ffmpeg/ffprobe for the optional recorder; a browser automation environment for headless UI capture."
---

# Evidence-Driven Testing

Capture evidence appropriate to the requested claim. Evidence supplements relevant checks; a video proves what was visible, not complete correctness.

1. Define the behavior or metric, starting conditions and meaningful assertions. Identify the revision and any uncommitted changes, environment and tested process.
2. Choose a measured probe for APIs/performance, screenshots for states, and a recording for multi-step visible behavior. Capture a before case for a bug fix when reproducible; otherwise disclose its absence.
3. Drive the real test and retain repeatable commands/scripts plus results. Mark blocked checks untested, with reasons. Observe the actual state before labeling an assertion passed.
4. Review the generated artifacts and summarize pass/fail, conditions and limitations. A recorder's successful rendering does not establish that an assertion was true.

For a GUI recording, read [references/recorder.md](references/recorder.md) and use the optional bundled recorder. For browser automation or a headless environment, read [references/headless.md](references/headless.md). Read only the chosen route.

Follow existing authorization and user scope. Save locally unless external publication is requested or already authorized; naming a PR as context does not itself authorize a comment or upload. Keep recordings away from credentials, personal/customer data and unrelated desktop content. Scope/crop capture where appropriate. Do not install system packages or change project dependencies merely to create evidence without evaluating the available alternatives and permissions.

Never describe synthetic frames, stitched playback or static screenshots as a recording of live interaction. Include artifact paths and the exact check performed. If no capture capability is available, report that limit and retain whatever meaningful probe evidence can be obtained.
