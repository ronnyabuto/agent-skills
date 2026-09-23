---
name: understand-before-changing
description: Use whenever a task touches an already-existing file — editing, deleting, or adding to code that's already there. Before making the change, investigate why the existing implementation is the way it is (git blame/log, commit messages, linked issues/PRs, tests, comments), then explicitly classify what you found as confirmed-valid, outdated/wrong, or undeterminable, and let that classification drive the change instead of guessing. Not for a brand new file/module with nothing existing to reference.
---

# Understand Before Changing

Chesterton's Fence for code: don't edit, delete, or build on top of something
until you know why it's there. This applies to any change that touches an
existing file — not just refactors or deletions. Adding a new function to a
file that already has a consistent validation/error-handling pattern is still
"touching existing implementation": understand that pattern before deviating
from it or blindly copying it without knowing what it's actually for.

## When to use

- **Editing** existing logic — bug fixes, behavior changes, "cleanups"
- **Deleting** existing code — including anything another skill (e.g.
  `no-ai-tells-audit`) flags as removable; a pattern that *looks* like a
  mistake can still be load-bearing
- **Adding** to an existing file or module — new code that sits alongside,
  extends, or depends on what's already there

**Don't use** for a brand new file or module with no prior implementation to
investigate — there's nothing to understand yet.

## Process

1. **Investigate before touching anything.** In order of signal strength:
   - `git blame` / `git log -p` on the relevant lines — commit message,
     author, date, and linked issue/PR discussion if accessible
   - Existing tests covering this code — tests often encode the actual
     intended behavior and edge cases better than comments do
   - Comments at or near the code
   - Related code elsewhere in the file/codebase doing something similar —
     relevant even when *adding*, since it reveals the convention being
     extended
   - CHANGELOG/release notes, if the repo keeps one
   - Past agent sessions, if `vault-memory` is set up — the "why" behind a
     choice is often in the discussion, not the commit message

   **Scale the digging to the risk.** A one-line addition that follows a
   pattern already visible in the file needs a glance at that pattern, not
   a history dig. Go deep when deleting or changing behavior, when the code
   looks wrong or redundant, or when it touches auth, payments, data writes,
   or concurrency — the places where a load-bearing oddity costs the most.

2. **Classify what you found** into exactly one of three states — don't
   blend them or jump straight to a fix:

   - **Confirmed valid** — the original reasoning holds up (a real edge
     case, a genuine constraint, a documented bug workaround still
     applicable, a deliberate convention). Preserve it; if adding new code,
     follow the same pattern rather than introducing a competing one.
   - **Outdated/wrong** — the reasoning is traceable and no longer applies
     (the library it worked around has been upgraded, the constraint it
     handled no longer exists, the bug it worked around is fixed
     upstream). State the specific reason it no longer applies, then
     change it — or, if adding, deliberately don't propagate it.
   - **Undeterminable** — no real signal on why it's there (terse or absent
     commit messages, no tests exercising it, no related comments). Say so
     explicitly. Do not invent a plausible-sounding justification either
     way — a fabricated "why" is worse than admitting you don't know.
     Proceed conservatively: prefer the smallest change that fixes the
     actual problem over removing or overriding the existing code outright,
     and flag the uncertainty in the summary so a human can weigh in.

3. **Design the change** — edit, deletion, or addition — from the union of
   what the investigation revealed and what current research/docs say is
   correct now (pairs with `current-docs` when the reasoning involves a
   specific library/API's behavior). Not a stock "modern" rewrite that
   discards whatever the original actually solved, and not a bolt-on
   addition that ignores the convention already established around it.

## Nuance

"Undeterminable" is a legitimate, common outcome — most codebases don't have
perfect commit hygiene. The failure mode this skill exists to prevent isn't
*not knowing why* — it's confidently guessing why and being wrong, or
confidently assuming "whoever wrote this was careless" and deleting or
overriding something load-bearing. When genuinely uncertain, say so and act
conservatively; that's the correct result, not a shortcoming of the process.
