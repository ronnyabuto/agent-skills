---
name: new-feature
description: Starts a new task in an isolated Git worktree branched from origin/main so multiple agents can work on the same repo in parallel without conflicts. Use at the beginning of every new feature, bug fix, or task in a git repo — including small fixes like "fix the off-by-one in X" — before editing any file.
---

# New Feature

Every task gets its own worktree and branch, created from the latest
`origin/main`. Never build on `main`, and never reuse another agent's
worktree or branch.

## Harness deltas — read first

- **Claude Code**: the harness creates and manages worktrees itself — under
  `.claude/worktrees/<name>/`, on a branch named `worktree-<name>`, branched
  from the remote default branch unless `worktree.baseRef` is `"head"`.
  **Skip steps 3–4 below** (no manual `git worktree add` / `remove`), and
  keep the harness-assigned branch name. Steps 1–2 and 5 still apply. Make
  sure `.claude/worktrees/` is gitignored in the repo.
- **Other harness-managed worktrees** (e.g. Cursor's parallel agents, set up
  via `.cursor/worktrees.json`): same idea — keep the assigned branch and
  worktree, apply steps 2 and 5.
- No harness support: follow all steps.

## Steps

1. **Sync**: `git fetch origin`.

2. **Scope check**: run `gh pr list` and skim the open PRs' changed files
   (`gh pr diff <n> --name-only`). If your task needs files another open PR
   is editing, **stop and ask for direction** instead of proceeding. Also
   check for uncommitted work in the checkout — another agent may be
   mid-task.

3. **Name the task**: lowercase-with-hyphens plus a short unique suffix,
   e.g. `user-auth-0816a`. If `git worktree add` fails because the name
   exists, pick a different name — never force or reuse.

4. **Create the worktree** from the repo root:

   ```bash
   git worktree add <worktrees-dir>/<task-name> \
     -b <branch-prefix>/<task-name> origin/main
   ```

   Use a **gitignored** directory for worktrees (e.g. `.claude/worktrees/`
   or `.worktrees/`) so they can never be committed by accident, and a
   consistent branch prefix (e.g. `agent/`). Follow the repo's conventions
   if it defines them.

5. **Enter and verify**:

   ```bash
   cd <worktrees-dir>/<task-name>
   git branch --show-current   # must print your new branch, not main
   ```

   Then install dependencies fresh inside the worktree (worktrees don't
   share `node_modules`/virtualenvs) and confirm the runtime version the
   repo requires before running anything.

## Remember

- Worktrees do **not** isolate shared resources: dev-server ports, shared
  databases, and dependency lockfiles are global. Confirm a port answers
  *your* process (`lsof -i :<port>`) before trusting what it serves, and
  resolve lockfile conflicts by regenerating, never by hand-merging.
- Keep the worktree until the PR is merged or closed. Cleanup after merge:

  ```bash
  git worktree remove <worktrees-dir>/<task-name>
  git branch -D <branch-prefix>/<task-name>
  ```

  `-D` is expected: after a squash- or rebase-merge, `-d` refuses even
  though the work is merged.
