---
name: new-feature
description: Use before the first edit of a new code task in a git repository — a bug fix, feature or refactor — to fetch origin and start from a fresh origin/main base, or to verify that an assigned branch or worktree is current. Skip for questions, reviews and continuing an existing task branch.
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

Create a worktree only when the user asks for isolation or another writer is
active in this checkout. Place it outside the repo or in a gitignored
directory, never reuse another session's checkout, and restore required
gitignored configuration before running tests; see
[worktree environments](references/environment.md). Worktrees share refs,
objects, ports, caches and external databases.

## Cleanup

Before removing a branch or worktree, verify it is merged into its base, has no
later commits and a clean status. Prefer `git branch -d`; use `-D` after a
squash or rebase merge only when integration is verified. Without being asked,
remove only branches and worktrees you created for this task. Delete a remote
branch only after its PR has merged.
