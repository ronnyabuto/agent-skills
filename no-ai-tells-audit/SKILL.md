---
name: no-ai-tells-audit
description: Sweeps an existing codebase for the no-ai-tells patterns, gates each removal through understand-before-changing, edits the source, and verifies nothing broke. Use when asked to sweep an existing codebase for AI-generated/vibe-coded/junior-level tells and remove them — a full-repo remediation pass, not the always-on final-pass discipline of no-ai-tells. Use for "clean up this codebase," "get rid of AI tells," "make this look hand-written."
---

# No AI Tells — Codebase Audit

Full sweep of an existing codebase, not a diff review — go through the whole
project, not just recent changes. Applies the `no-ai-tells` checklist as a
one-time remediation pass rather than an ongoing writing discipline.

**Mutates files.** Unlike `project-audit` and `ux-speed-audit`, which mostly
report, this skill edits the codebase directly — see `AGENTS.md`'s concurrency
rules before running it alongside other in-flight work.

## What counts as a tell

**Comments:**
- Restates the line instead of explaining why (`// increment counter` above `i++`)
- Explains *what* instead of the non-obvious *why*
- Banner/divider comments (`# ===== Section =====`) in a file or codebase that
  doesn't otherwise use them — some codebases use section banners on purpose
- Comments spread evenly everywhere instead of clustering at genuinely hard
  decision points — and the inverse: real complexity left unexplained while
  trivial lines get commented
- Change-history references (`// fixed for issue #123`, `// added for the new
  signup flow`) — that belongs in the commit message, not the file. Keep links
  to an upstream bug that a live workaround depends on (`// works around
  foo#123; remove once fixed`) — they say when the code can go
- Removed-code narration (`// no longer using X`, `// removed old validation`)
- Staged/phased narration (`// Step 1: validate`, `// Step 2: process`) instead
  of just writing the steps as code
- Untracked TODO/placeholder/stub comments in code that's actually shipped.
  A tracked TODO — owner or issue ID plus a removal condition — is standard
  practice (Google's C++ style guide recommends that form); leave it
- Apologetic or hedging comments ("this might not be the best way but...")
- Generic, context-free phrasing that doesn't match this codebase's actual tone

These compound rather than appearing alone — e.g. a function where every line
has a comment restating it, and the one comment that survives cleanup is the
one explaining an actual choice (a cost parameter, a non-default flag) the
code doesn't already show. Read the whole function before deciding what to
cut, not comment-by-comment on a first pass.

**Structure/naming:**
- Defensive completeness beyond what the real failure modes justify (e.g.
  re-validating data already validated one layer up)
- Naming inconsistent with the surrounding file (not verbose or terse in
  isolation — the *mismatch* with existing convention is the tell)
- Near-duplicated logic (2-3 blocks 90% identical) instead of one shared path
- Mechanical placeholder names (`tempData`, `result`, `item`) past the point
  where a real name is easy
- Phase-named identifiers — functions/variables/section headers named after
  narration order rather than what they do (`step1Validate()`, `step1Result`,
  a `## Step 1: Setup` header) — the staged-narration tell moved into the name
  instead of a comment above it
- Test smells: module-wide `jest.mock()` where targeted `spyOn()` would do,
  redundant `beforeEach` resets "just to be safe," loose `as any`, regex
  assertions where exact-match works, reimplemented helpers that already exist
  in the codebase

## Process

1. Scan the codebase and list every match with file:line, the category from
   above, and a one-line reason it qualifies here specifically — not just that
   it matches a pattern name.
2. Apply cumulative-case reasoning, not single-pattern triggers. Full test
   coverage, complete error handling, and descriptive names are normally good
   engineering — flag them only when disproportionate to actual risk or
   inconsistent with this codebase's own convention. Don't strip something
   just because it matches a category; strip it because inspection confirms
   it isn't earning its place.
3. Before deleting or rewriting anything from step 1's list, run it through
   `understand-before-changing` — a pattern that looks like an AI tell (an
   over-defensive check, a "redundant" re-validation) can still be
   load-bearing. Then fix what's confirmed: delete the comment, rename for
   consistency, collapse the duplication, trim the excess defensiveness.
   Don't touch comments that are doing real work — a genuine "why" note on a
   non-obvious constraint stays.
4. After each batch of changes, verify nothing broke: run the type checker,
   linter, and test suite. A comment-stripping pass that breaks the build is a
   regression, not a cleanup.
5. Report what changed as a short list (category, count, example), not a
   diff dump — and call out anything you deliberately left alone because it
   didn't actually qualify on inspection, so the report doesn't read as
   padded.

If `evidence-driven-testing` is loaded, use it after step 4 to capture proof
the remediation didn't break behavior.
