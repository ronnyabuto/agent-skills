---
name: ux-speed-audit
description: Use when asked to audit page load speed, UX responsiveness, or performance — "make it feel instant," "why is this slow," "audit loading speed," Core Web Vitals, perceived performance. Use for web apps, but also CLI/desktop cold-start audits with the same response-time bar.
---

# UX / Loading Speed Audit

Audits user experience and load performance against one bar: everything should
feel instantaneous. Use Nielsen's response-time thresholds as the literal
target, not a vibe — **0.1s (100ms)** reads as instant, **1s** is the max before
the user notices a delay and loses flow, anything past that is a failure worth
flagging as such.

## Ground rule

Don't just read the code — actually run the app (start the dev server / build,
launch it in a browser) and measure it live. Static reading alone doesn't count
as an audit here. If a UI is involved, use the browser to interact with it
directly rather than inferring behavior from source.

## Measure and report against concrete numbers

1. **Load** — TTFB, LCP, CLS, INP (or FID if INP tooling isn't available). Use
   Lighthouse/DevTools Performance for a web app, or cold-start-to-usable time
   for a CLI/desktop app. State the actual measured numbers, never estimates.
2. **Render-blocking resources** — unminified/unsplit JS bundles, blocking CSS,
   web fonts without `font-display: swap`, third-party scripts loaded
   synchronously.
3. **Bundle size** — what's shipped vs. what's used on first paint; flag
   anything that should be code-split or lazy-loaded but isn't.
4. **Perceived speed** — do interactions get feedback within 100ms even if the
   real work takes longer (optimistic UI, skeleton states, spinners appearing
   immediately)? A 2s action with zero feedback for the first second reads as
   broken even if it "works."
5. **Data layer** — N+1 queries, missing indexes, over-fetching (returning more
   than the view needs), unnecessary request waterfalls (sequential fetches
   that could run in parallel).
6. **Caching** — HTTP cache headers, CDN usage for static assets, any obvious
   re-fetching of data that hasn't changed.
7. **Images/media** — unoptimized formats, missing lazy-loading, no responsive
   sizing.

## Deliverable

For each finding: the measured number, the target number, the specific fix,
and the expected improvement if estimable. Rank by user-perceived impact, not
by how easy the fix is.

If the `evidence-driven-testing` skill is loaded, capture before/after evidence
for the top 2-3 fixes once applied — a number in a report is weaker proof than
a recording of the actual before/after.
