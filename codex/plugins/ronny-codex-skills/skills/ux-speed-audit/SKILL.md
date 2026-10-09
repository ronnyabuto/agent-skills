---
name: ux-speed-audit
description: Measure app load speed and interaction responsiveness when asked to diagnose slow UX, audit Core Web Vitals, or assess desktop or CLI startup.
---

# UX Speed Audit

Measure the requested app or flow; reading source alone cannot establish latency. A diagnostic request authorizes measurement and reporting, not unrelated optimization or production mutation.

- Prefer a production build. Verify the tested process, revision, route and deployment.
- Record device, browser, network throttling, cache state, dataset and competing load. Keep comparisons under the same conditions.
- For repeatable lab load tests, report the median of at least five runs and the range. Label a smaller sample preliminary. Separate lab diagnostics from field/RUM percentiles.
- Drive the relevant interactions, including during loading where relevant. A load-only Lighthouse run does not measure INP; TBT is a diagnostic, not a substitute. Do not claim a site passes field Core Web Vitals from a few lab runs.
- Assess LCP, CLS, interaction latency and TTFB for web apps; time-to-usable and operation feedback for desktop/CLI apps. Check current official metric definitions and targets when reporting compliance.
- Inspect request waterfalls, bundle costs, blocking resources, images, caching and slow backend operations where measurements point to them.
- Check whether input receives timely visible acknowledgement. Use Nielsen's 0.1/1/10-second response-time heuristics as design guidance, not a universal SLA.

Use existing tools first. If tools, app access or representative field data are unavailable, report the measurement limit and offer source-supported hypotheses clearly labeled as hypotheses. Do not fabricate metrics.

Report measured value, conditions, comparison target, evidence and a concrete fix direction per finding. Rank by effect on users. For authorized fixes, rerun the affected measurement and retain traces or screenshots locally; upload only when requested or already authorized.
