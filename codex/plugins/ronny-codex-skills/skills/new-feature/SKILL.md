---
name: new-feature
description: Create new task branches from freshly fetched origin/main; set up an isolated worktree when requested or needed for concurrent development.
---

# New Task Branch and Workspace

Before creating a new task branch, fetch origin and use the updated origin/main as the default base. This is the user's branch-start preference. Use a worktree for requested isolation or a concrete concurrent-write conflict; a new feature or tiny fix alone does not require a worktree.

- Inspect repository instructions, current branch, working-tree status and existing worktrees. Keep a harness-assigned worktree; do not assume a particular client creates one automatically.
- For a fresh task, run `git fetch origin` successfully before creating the branch. Verify that origin/main was fetched and record its current commit. If the remote's fetch configuration excludes main, explicitly fetch it into refs/remotes/origin/main before proceeding.
- Create the branch from that refreshed origin/main, not a possibly stale local main. Verify the new branch starts at the recorded base before editing; a newly created branch should match it exactly. Fetching does not require checking out, pulling into, or resetting local main.
- Preserve an explicitly requested release branch, PR continuation or other task-specific base. Fetch its relevant remote base where applicable. Do not restart existing work from main or abandon task-relevant uncommitted changes.
- If fetching fails or origin/main is absent, report the limitation and obtain direction before substituting a stale or different base. Do not claim the new branch is up to date without a successful fetch. Keep a harness-assigned branch, but verify its base freshness for a new task and resolve an outdated base without discarding work.
- Open PRs touching the same file are coordination context, not automatically a blocker. Ask only when incompatible scope or ownership cannot be resolved from the instructions.
- Create a unique branch and worktree in a suitable external or gitignored directory. Never force reuse or overwrite another session's checkout.
- Verify branch and checkout before editing. Follow the repository's runtime/dependency setup, installing only when required.

Worktrees isolate working files, including separate copies of dependency lockfiles. They share Git metadata, refs and object storage; ports, external databases and caches may also be shared. Verify which process serves the app under test. Resolve lockfile conflicts with the appropriate package manager while preserving intended version choices.

Keep the worktree while its work is needed. Remove it only when completion/merge and clean status are established within the authorized cleanup scope. Prefer ordinary branch deletion; forced deletion needs confirmation that the changes are retained or no longer needed. Report where the task now lives.
