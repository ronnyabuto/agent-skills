# Skill Orchestration

How these 8 skills relate — what has to run in order, and what's safe to run
at the same time. The dividing line is simple: **anything that writes to
source files needs exclusive access to the tree it's writing to. Anything
that only reads/measures/reports doesn't.**

## Skills by role

| Skill | Role | Mutates files? |
|---|---|---|
| `new-feature` | Setup — isolate a task into its own worktree/branch | Repo structure only (branch/worktree), not source |
| `current-docs` | Pre-implementation research — verify against the actually-installed version's official docs | No — read-only research |
| `code-structure` | Ongoing lens applied while writing code | No — guidance only |
| `no-ai-tells` | Ongoing final-pass discipline applied while writing code | Yes — but as part of the same edit, not a separate process |
| `evidence-driven-testing` | Verification — capture proof after implementation | Writes output artifacts (video/report), not source |
| `project-audit` | Diagnostic sweep — architecture/security/deps/tests | No — reports findings |
| `ux-speed-audit` | Diagnostic sweep — UX/loading performance | No — measures and reports |
| `no-ai-tells-audit` | Remediation sweep on an existing codebase | **Yes — edits source directly** |

## Sequence 1 — building a new feature or fix

Runs in order, one agent/session, single worktree:

1. **`new-feature`** — isolate into a fresh worktree/branch before writing
   anything.
2. **`current-docs`**, when the work touches a library/framework/SDK/API
   whose current behavior isn't a sure thing from memory — identify the
   pinned version and pull its official docs before writing code against it.
   Skip this step outright for stable syntax/stdlib work; it's not a tax on
   every task.
3. **Implement**, applying `code-structure` as the architecture lens and
   `no-ai-tells` as the final pass before considering any code-writing step
   done. These aren't separate phases — they run inline with the writing.
4. **`evidence-driven-testing`** — once the change works and tests pass,
   capture proof.

## Sequence 2 — auditing or cleaning an existing codebase

Not tied to a specific feature; run this against the whole repo:

1. **`project-audit` and `ux-speed-audit` concurrently** — both are
   read/measure-first and inspect different concerns (correctness/security/
   deps vs. performance/UX), so they don't conflict. Run them as two parallel
   agents/forks against the same snapshot and merge the findings.
2. **`no-ai-tells-audit` alone, after step 1 finishes** — this one edits
   source directly, so it needs the tree to itself. Don't run it at the same
   time as another skill that's also writing to the same files.
3. **`evidence-driven-testing`** — capture proof the remediation didn't
   break behavior.
4. **`no-ai-tells`** carries forward as the ongoing discipline for whatever
   gets written next.

## Concurrency rule of thumb

- Multiple report-only skills against the same codebase → safe to
  parallelize freely.
- Any skill that writes to source files → run it alone, or give it its own
  worktree (via `new-feature`'s pattern) if it truly needs to run alongside
  other in-flight edits. Never point two file-mutating skills at the same
  worktree at the same time — that's the exact conflict `new-feature` exists
  to prevent.
