# Setup check

If you're an agent working in this repo, check once, with a single command,
whether these skills are installed: does `~/.claude/skills/vault-memory`
exist? If it does — pointing at this checkout, another clone, or a worktree
of this repo — they're installed; say nothing about setup. If it's missing,
tell the user the skills aren't installed and offer to run `./install.sh`. It
links the skills and adds vault-memory's hooks to `~/.claude/settings.json`,
so:

- Ask before running it — it changes the user's global configuration.
- Ask where the vault should live (default `~/agent-vault`; an existing
  Obsidian vault is fine) and pass it as `./install.sh --vault <path>`.
- Show the output, including any warning, and say that a new session (or
  `/hooks`) is needed for the hooks to load.

Skip this when the skills are already linked here, or when the user is
clearly just editing the skills themselves.

# Skill Orchestration

How these 10 skills relate — what has to run in order, and what's safe to run
at the same time. The dividing line is simple: **anything that writes to
source files needs exclusive access to the tree it's writing to. Anything
that only reads/measures/reports doesn't.**

## Skills by role

| Skill | Role | Mutates files? |
|---|---|---|
| `new-feature` | Setup — isolate a task into its own worktree/branch | Repo structure only (branch/worktree), not source |
| `current-docs` | Pre-implementation research — verify against the actually-installed version's official docs | No — read-only research |
| `understand-before-changing` | Ongoing lens — investigate why existing code is the way it is before editing, deleting, *or adding to* any existing file | No — read-only investigation |
| `code-structure` | Ongoing lens applied while writing code | No — guidance only |
| `no-ai-tells` | Ongoing final-pass discipline applied while writing code | Yes — but as part of the same edit, not a separate process |
| `evidence-driven-testing` | Verification — capture proof after implementation | Writes output artifacts (video/report), not source |
| `project-audit` | Diagnostic sweep — architecture/security/deps/tests | No — reports findings |
| `ux-speed-audit` | Diagnostic sweep — UX/loading performance | No — measures and reports (needs the machine quiet while measuring) |
| `no-ai-tells-audit` | Remediation sweep on an existing codebase | **Yes — edits source directly** |
| `vault-memory` | Ongoing recall — search archived sessions and decision notes instead of re-deriving them | Writes to the Obsidian vault (outside the repo), never source |

## Sequence 1 — building a new feature or fix

Runs in order, one agent/session, single worktree:

1. **`new-feature`** — isolate into a fresh worktree/branch before writing
   anything.
2. **`current-docs`**, when the work touches a library/framework/SDK/API
   whose current behavior isn't a sure thing from memory — identify the
   pinned version and pull its official docs before writing code against it.
   Skip this step outright for stable syntax/stdlib work; it's not a tax on
   every task.
3. **Implement**, applying all three ongoing lenses inline — they aren't
   separate phases, they run continuously while writing:
   - `understand-before-changing` the moment the work touches an
     already-existing file, in *any* of the three ways: editing it,
     deleting from it, or adding new code into it. Only genuinely new
     files/modules with nothing existing to reference are exempt.
     `vault-memory` is one more source for its investigation: past
     sessions often hold the "why" that never made it into a commit
     message.
   - `code-structure` for where new logic belongs (existing file vs. new
     one, action vs. service layer) and how much of it to build.
   - `no-ai-tells` as the final pass before considering any code-writing
     step done.
4. **`evidence-driven-testing`** — once the change works and tests pass,
   capture proof.
5. **`vault-memory`**, only if the task settled a decision a future session
   would otherwise rediscover — file a note. The session itself is archived
   by hooks; don't duplicate it.

## Sequence 2 — auditing or cleaning an existing codebase

Not tied to a specific feature; run this against the whole repo:

1. **`project-audit` and `ux-speed-audit`** — neither edits source, and they
   inspect different concerns (correctness/security/deps vs. performance/UX),
   so they never conflict over files. They do conflict over the machine:
   `ux-speed-audit`'s numbers are skewed by anything competing for CPU,
   network, or disk, and `project-audit` runs test suites and dependency
   audits. Run `ux-speed-audit`'s measurements alone (before or after
   `project-audit`); its code-reading parts, and all of `project-audit`, can
   run as parallel agents/forks against the same snapshot. Merge the findings.
2. **`no-ai-tells-audit` alone, after step 1 finishes** — this one edits
   source directly, so it needs the tree to itself. Don't run it at the same
   time as another skill that's also writing to the same files. Before
   actually removing or rewriting anything it flags, run it through
   `understand-before-changing` first — a pattern that looks like an AI tell
   can still be load-bearing, and this is exactly the gate that catches that
   before deletion, not after.
3. **`evidence-driven-testing`** — capture proof the remediation didn't
   break behavior.
4. **`no-ai-tells`** carries forward as the ongoing discipline for whatever
   gets written next.

## Concurrency rule of thumb

- Multiple report-only skills against the same codebase → safe to
  parallelize, with one exception: performance measurement needs a quiet
  machine, so nothing heavy runs alongside `ux-speed-audit`'s measuring.
- Any skill that writes to source files → run it alone, or give it its own
  worktree (via `new-feature`'s pattern) if it truly needs to run alongside
  other in-flight edits. Never point two file-mutating skills at the same
  worktree at the same time — that's the exact conflict `new-feature` exists
  to prevent.
- `vault-memory` writes only under the vault's `claude/` folder, never to
  source, so it's safe alongside everything. Concurrent sessions archive to
  separate files; the one collision is two sessions filing a note with the
  same title, where the last write wins.
