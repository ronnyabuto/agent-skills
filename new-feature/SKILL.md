---
name: new-feature
description: Starts a new task in an isolated Git worktree branched from freshly fetched origin/main (or an explicitly requested release/PR base) so multiple agents can work on the same repo in parallel without conflicts. Use at the beginning of every new feature, bug fix, or task in a git repo — including small fixes like "fix the off-by-one in X" — before editing any file.
---

# New Feature

Every task gets its own worktree and branch, created from the latest
`origin/main` by default. Preserve an explicitly requested release branch,
PR head, or other base instead. Never build on `main`, and never reuse
another agent's worktree or branch.

## Harness deltas — read first

- **Claude Code**: when a worktree was assigned by `--worktree` or
  `EnterWorktree`, keep its branch and directory. Skip steps 3–4 only after
  checking it against the freshly fetched base in steps 1 and 5. Ordinary
  sessions do not automatically get a worktree; request one or follow the
  manual steps. Make sure `.claude/worktrees/` is gitignored.
- **Other harness-managed worktrees**: keep the assigned branch and
  directory, but apply the same fetch and base verification.
- A harness-created worktree is not proof of freshness. Claude's `fresh`
  mode can use a cached remote ref when fetching fails; `head` mode uses
  local HEAD. See [Claude Code worktree bases](https://code.claude.com/docs/en/worktrees#choose-the-base-branch).
- No harness support: follow all steps.

## Steps

1. **Fetch and select the base before creating the task branch**:
   run `git fetch origin` and require success. Default to `origin/main`,
   never a potentially stale local `main`. Record the base commit with
   `git rev-parse --verify 'origin/main^{commit}'`.

   If origin's fetch configuration excludes main, explicitly fetch it:
   `git fetch origin refs/heads/main:refs/remotes/origin/main`, then record
   the commit. If the user requested a release branch, PR head, or other
   base, fetch and resolve that base instead; do not replace it with main.
   Use the selected commit in step 4. If fetching fails or the base cannot
   be resolved, report the blocker and ask for direction before using a
   cached ref or substituting a different base. No checkout, pull, or reset
   of local `main` is needed.

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
     -b <branch-prefix>/<task-name> <fetched-base-commit>
   ```

   Use a **gitignored** directory for worktrees (e.g. `.claude/worktrees/`
   or `.worktrees/`) so they can never be committed by accident, and a
   consistent branch prefix (e.g. `agent/`). Follow the repo's conventions
   if it defines them.

5. **Enter and verify**:

   ```bash
   cd <worktrees-dir>/<task-name>
   git branch --show-current   # must print your new branch, not main
   git rev-parse HEAD          # must equal the recorded base before edits
   ```

   For a newly created branch, verify HEAD equals the recorded base commit
   before editing. If a harness already created a branch at a stale or
   different base, resolve that mismatch first without discarding commits
   or uncommitted work. Recreate only an unused, clean task worktree through
   the harness when supported; otherwise ask how to preserve its work.
   Continuing an existing task or PR does not mean restarting its branch.

   Then install dependencies fresh inside the worktree (worktrees don't
   share `node_modules`/virtualenvs) and confirm the runtime version the
   repo requires before running anything.

## Remember

- Worktrees do **not** isolate shared resources: dev-server ports, shared
  databases, and dependency lockfiles are global. Confirm a port answers
  *your* process (`lsof -i :<port>`) before trusting what it serves, and
  resolve lockfile conflicts by regenerating, never by hand-merging.
- Prefer short-lived task branches; delete them after their work is merged
  and no longer needed. Retain long-lived branches only for maintained
  releases or ongoing work. Keep the worktree while its work is needed;
  a closed, unmerged PR alone is not evidence that its work can be discarded.
- Before cleanup, confirm the PR was merged into the intended base, the
  task branch has no later unmerged commits, and the worktree is clean.
  Leave the worktree, then remove it and try ordinary branch deletion:

  ```bash
  git worktree remove <worktrees-dir>/<task-name>
  git branch -d <branch-prefix>/<task-name>
  ```

  If `-d` refuses after a squash or rebase merge, use `-D` only after
  confirming the branch's work is integrated and no additional work remains,
  within the authorized cleanup scope. Never force-remove a dirty worktree.
- Deleting a branch whose commits are reachable from `main` preserves those
  commits. Squash and rebase merges retain the integrated work but may not
  retain the original task commit IDs.
- For GitHub repositories, recommend **Settings → General → Pull Requests →
  Automatically delete head branches**. This deletes remote PR branches
  after merge; local branches and worktrees still need cleanup. Repository
  rules can prevent automatic deletion. Change the setting only when
  authorized. See [GitHub's automatic branch deletion documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-the-automatic-deletion-of-branches).
