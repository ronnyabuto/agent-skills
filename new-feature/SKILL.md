---
name: new-feature
description: Use before the first edit of a new code task in a git repository — a bug fix, feature or refactor — to fetch origin and start from a fresh origin/main base, or to verify that an assigned branch or worktree is current; and again before committing, pushing or opening a PR. Skip for questions and reviews; on an existing task branch, skip the start steps.
---

# Start a Task From a Fresh Base

Do this before editing. It takes a few commands; don't skip it because the fix is small.

1. Inspect `git status`, the current branch and `git worktree list`. Note any
   uncommitted work; never discard or move it.
2. Run `git fetch origin`. If the fetch fails or `origin/main` is missing, stop
   and report it — don't silently use a cached ref or local main as the base.
   If the fetch refspec excludes main, fetch `main:refs/remotes/origin/main`.
3. Record the `origin/main` commit, then choose the base:
   - **Assigned branch or worktree** (the harness or user says this is the
     task's workspace): keep it. If `HEAD` is behind the fetched `origin/main`
     and the branch has no work of its own, fast-forward it; otherwise rebase
     or report the gap. Don't create another branch or worktree.
   - **On main or an unrelated branch:** create a uniquely named task branch
     with `git switch --no-track -c <branch> origin/main` (not local main;
     without `--no-track` the branch would track and push to main). Don't pull
     into or reset local main.
   - **Explicit base** (release branch, PR continuation): fetch that remote
     branch and use it instead.
4. Verify `git rev-parse HEAD` equals the recorded base (or descends from it for
   continued work) before the first edit, and state the base commit.

Use one branch per task. Keep follow-up fixes and PR revisions on it instead of
starting another branch.

Create a worktree only when the user asks for isolation or another writer is
active in this checkout. Place it outside the repo or in a gitignored
directory, never reuse another session's checkout, and restore required
gitignored configuration before running tests; see
[worktree environments](references/environment.md). Worktrees share refs,
objects, ports, caches and external databases.

## Commit and push

Commit only when asked. Every commit must contain only what the task needs.

1. List `git status --short --untracked-files=all` and decide each path's fate.
   Commit source, tests that guard the changed behavior, and docs that the
   change would otherwise leave wrong. Don't commit:
   - scratch scripts, probes, logs, screenshots, or generated output;
   - summaries, reports, plans or notes written for the conversation;
   - `.env`, credentials, local config, or editor and OS files;
   - files or changes that existed before the task. The user's uncommitted
     work stays in place, uncommitted.
2. Stage named paths: `git add -- <path>...`. Never run `git add -A`,
   `git add .` or `git commit -a`.
3. Read `git diff --cached` before committing and unstage anything the task
   doesn't explain. Run the affected checks. Make one logical change per
   commit, with a subject that says what changed and why.
4. Push only the task branch: `git push -u origin <branch>`. Don't push to
   main or another shared branch unless asked. Don't force-push a branch
   others use.
5. Delete scratch files you created. Delete local branches you created for this
   task that are no longer needed, such as abandoned attempts, after checking
   they hold no unpushed work. Keep the pushed task branch until it merges.
6. Report the branch, the pushed commits, and anything you left uncommitted or
   in place, with the reason.

## Cleanup

Before removing a branch or worktree, verify it is merged into its base, has no
later commits and a clean status. Prefer `git branch -d`; use `-D` after a
squash or rebase merge only when integration is verified. Without being asked,
remove only branches and worktrees you created for this task. Delete a remote
branch only after its PR has merged.
