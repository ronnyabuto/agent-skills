---
name: new-feature
description: Create new task branches from freshly fetched origin/main; set up an isolated worktree when requested or needed for concurrent development.
---

# New Task Branch and Workspace

Fetch origin before creating a task branch; default to updated origin/main. Use a worktree for requested isolation or concurrent-write conflicts, not every feature or tiny fix.

- Inspect repository instructions, current branch, working-tree status and existing worktrees. Keep a harness-assigned worktree; do not assume a particular client creates one automatically.
- For a fresh task, run `git fetch origin` successfully before creating the branch. Verify that origin/main was fetched and record its current commit. If the remote's fetch configuration excludes main, explicitly fetch it into refs/remotes/origin/main before proceeding.
- Create the branch from that refreshed origin/main, not a possibly stale local main. Verify the new branch starts at the recorded base before editing; a newly created branch should match it exactly. Fetching does not require checking out, pulling into, or resetting local main.
- Preserve an explicitly requested release branch, PR continuation or other task-specific base. Fetch its relevant remote base where applicable. Do not restart existing work from main or abandon task-relevant uncommitted changes.
- If fetching fails or origin/main is absent, report the limitation and obtain direction before substituting a stale or different base. Do not claim the new branch is up to date without a successful fetch. Keep a harness-assigned branch, but verify its base freshness for a new task and resolve an outdated base without discarding work.
- Open PRs touching the same file are coordination context, not automatically a blocker. Ask only when incompatible scope or ownership cannot be resolved from the instructions.
- Create a unique branch and worktree in a suitable external or gitignored directory. Never force reuse or overwrite another session's checkout.
- Verify branch and checkout before editing. Follow the repository's runtime/dependency setup, installing only when required. Restore required gitignored configuration before tests; see [worktree environments](references/environment.md).

Worktrees isolate working files, including separate copies of dependency lockfiles. They share Git metadata, refs and object storage; ports, external databases and caches may also be shared. Verify which process serves the app under test. Resolve lockfile conflicts with the appropriate package manager while preserving intended version choices.

Prefer short-lived task branches; delete them after merge when no longer needed. Retain long-lived branches only for maintained releases or ongoing work.

Keep needed worktrees. Before cleanup, verify merge into the intended base, no later unmerged commits, and clean status. Within authorized cleanup scope, leave and remove the worktree, then prefer `git branch -d`. Use `-D` after squash/rebase only when integration is verified and no additional work remains. Report where the work lives.

Deleting branches preserves commits reachable from main. Squash/rebase retain integrated work, potentially with different commit IDs.

Recommend GitHub's [Automatically delete head branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-the-automatic-deletion-of-branches) setting under Settings → General → Pull Requests. It cleans remote PR branches; local branches/worktrees need cleanup. Repository rules may prevent deletion. Change settings only when authorized.
