---
name: no-ai-tells-audit
description: Remediate AI-style boilerplate across an existing codebase when explicitly asked for a repository-wide readability cleanup; edits source and verifies affected behavior.
---

# No AI Tells — Codebase Remediation

A one-time sweep of the whole project, not a diff review. This skill edits
source: check for other in-flight work on the same files before starting, and
give concurrent writers separate worktrees.

## What qualifies

These are readability heuristics, not evidence of authorship. Flag an instance
only when inspection shows it isn't earning its place in this codebase.

- Comments that restate the code, narrate removed code or change history
  (`// fixed for #123`), or stage obvious steps (`// Step 1: validate`).
- Untracked TODOs or stubs in shipped code, and apologetic or hedging comments.
- Identifiers named after narration order (`step1Result`) or mechanical
  placeholders where a real name is easy.
- Naming or formatting that departs from the surrounding file's convention.
- Defensive checks that repeat validation already enforced one layer up.
- Tests that mock away the boundary at risk or only assert a mock's configured answer.

Keep: comments explaining non-obvious constraints, invariants, API contracts or
cost parameters; links to upstream bugs that a live workaround depends on;
tracked TODOs (owner or issue plus removal condition); license notices; section
banners the codebase uses on purpose; boundary validation and error recovery.
Repetition alone is not a defect: collapse duplication only when the shared
semantics are stable and the policy is the same.

## Process

1. Inventory matches with `file:line`, category and a reason specific to that
   instance. Read the whole function before cutting its comments.
2. Before removing a check, workaround or "redundant" path, establish why it
   exists from callers, tests and history. Leave it when the purpose is unknown
   and the risk is real.
3. Fix in batches. After each batch run the project's type checker, linter and
   affected tests; a cleanup that breaks the build is a regression.
4. Report changes as a short list (category, count, example) and name what you
   deliberately left alone and why.
