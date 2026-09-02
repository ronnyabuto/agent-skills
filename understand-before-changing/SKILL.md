---
name: understand-before-changing
description: Use before modifying, refactoring, simplifying, or removing existing implementation — not for writing genuinely new code. Investigate why the original engineer built it that way (git blame/log, commit messages, linked issues/PRs, tests, comments) before touching it, then explicitly classify the reasoning as confirmed-valid, outdated/wrong, or undeterminable, and let that classification drive the change instead of guessing.
---

# Understand Before Changing

Chesterton's Fence for code: don't remove or rewrite something until you know
why it's there. This is for changing *existing* implementation — not writing
new code from scratch, where there's no prior intent to investigate.

## When to use

- Refactoring, simplifying, "cleaning up," or removing existing code
- A bug fix that touches code that looks wrong, redundant, or overly
  defensive
- Anything `no-ai-tells-audit` or a general audit flags as a tell, before
  actually removing it — a pattern that *looks* like an AI tell can still be
  load-bearing

**Don't use** for genuinely new code with no prior implementation to
investigate.

## Process

1. **Investigate before touching anything.** In order of signal strength:
   - `git blame` / `git log -p` on the specific lines — commit message,
     author, date, and linked issue/PR discussion if accessible
   - Existing tests covering this code — tests often encode the actual
     intended behavior and edge cases better than comments do
   - Comments at or near the code
   - Related code elsewhere in the codebase doing something similar
   - CHANGELOG/release notes, if the repo keeps one

2. **Classify what you found** into exactly one of three states — don't
   blend them or jump straight to a fix:

   - **Confirmed valid** — the original reasoning holds up (a real edge
     case, a genuine constraint, a documented bug workaround still
     applicable). Preserve the behavior; refactor for clarity only if
     needed, never change what it does.
   - **Outdated/wrong** — the reasoning is traceable and no longer applies
     (the library it worked around has been upgraded, the constraint it
     handled no longer exists, the bug it worked around is fixed
     upstream). State the specific reason it no longer applies, then
     change it.
   - **Undeterminable** — no real signal on why it's there (terse or absent
     commit messages, no tests exercising it, no related comments). Say so
     explicitly. Do not invent a plausible-sounding justification either
     way — a fabricated "why" is worse than admitting you don't know.
     Proceed conservatively: prefer the smallest change that fixes the
     actual problem over removing the code outright, and flag the
     uncertainty in the summary so a human can weigh in.

3. **Design the replacement**, if changing, from the union of what the
   investigation revealed and what current research/docs say is correct now
   — pairs with `current-docs` when the reasoning involves a specific
   library/API's behavior. Not a stock "modern" rewrite that discards
   whatever the original actually solved.

## Nuance

"Undeterminable" is a legitimate, common outcome — most codebases don't have
perfect commit hygiene. The failure mode this skill exists to prevent isn't
*not knowing why* — it's confidently guessing why and being wrong, or
confidently assuming "whoever wrote this was careless" and deleting
something load-bearing. When genuinely uncertain, say so and act
conservatively; that's the correct result, not a shortcoming of the process.
