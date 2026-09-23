---
name: ux-speed-audit
description: Measures an app's load speed and interaction responsiveness live and reports findings against Core Web Vitals (LCP, INP, CLS) and Nielsen's response-time limits. Use when asked to audit page load speed, UX responsiveness, or performance — "make it feel instant," "why is this slow," "audit loading speed," Core Web Vitals, perceived performance — and for CLI/desktop cold-start audits.
---

# UX / Loading Speed Audit

Audits user experience and load performance against published thresholds, not
a vibe. Two different yardsticks apply, and mixing them up produces wrong
verdicts:

- **Page load and responsiveness — Core Web Vitals**, judged at the 75th
  percentile of page loads, mobile and desktop separately:

  | Metric | Good | Poor |
  |---|---|---|
  | LCP (loading) | ≤ 2.5 s | > 4 s |
  | INP (interaction latency) | ≤ 200 ms | > 500 ms |
  | CLS (visual stability) | ≤ 0.1 | > 0.25 |

  Between the two columns is "needs improvement". INP replaced FID as a Core
  Web Vital in 2024; don't report FID.
- **Individual interactions — Nielsen's response-time limits**: under
  **0.1 s** feels instant; up to **1 s** keeps the user's flow of thought but
  the delay is noticed; around **10 s** is the limit of attention. Past 1 s the
  requirement is visible feedback (a busy state), past 10 s a progress
  indicator and a way to cancel. A slow action with the right feedback is a
  finding to improve, not automatically a failure.

## Ground rule

Don't just read the code — actually run the app (start the dev server / build,
launch it in a browser) and measure it live. Static reading alone doesn't count
as an audit here. If a UI is involved, use the browser to interact with it
directly rather than inferring behavior from source.

Measure a production build, not the dev server, on a machine that isn't
doing other heavy work — concurrent Lighthouse runs, test suites, or builds
skew results through resource contention. Lab numbers vary run to run: report
the median of at least 5 runs (Lighthouse's own guidance: the median of 5 is
about twice as stable as one run), and say lab vs. field (CrUX/RUM) data.

## Measure and report against concrete numbers

1. **Load** — LCP, CLS, INP, plus TTFB as the diagnostic for slow LCP. Use
   Lighthouse/DevTools Performance for a web app, or cold-start-to-usable
   time for a CLI/desktop app. A page-load-only lab run can't report INP —
   drive real user flows (including interacting while the page is still
   loading) and measure those interactions; Total Blocking Time approximates
   INP but doesn't substitute for it. State the actual measured numbers, never estimates.
2. **Render-blocking resources** — unminified/unsplit JS bundles, blocking CSS,
   web fonts without `font-display: swap`, third-party scripts loaded
   synchronously.
3. **Bundle size** — what's shipped vs. what's used on first paint; flag
   anything that should be code-split or lazy-loaded but isn't.
4. **Perceived speed** — does every interaction acknowledge the input within
   ~100 ms even when the real work takes longer (pressed state, optimistic UI,
   skeleton, spinner)? A 2 s action with no feedback reads as broken even if
   it "works"; the same action with immediate feedback is acceptable.
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
