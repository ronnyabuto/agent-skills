# Claude worktree environment

Fresh worktrees contain committed files, not untracked or gitignored configuration.
Follow the project setup command and install dependencies only when needed.
Claude-created worktrees can copy approved files through `.worktreeinclude`;
manual `git worktree add` does not process that allowlist. Restore approved
configuration explicitly, preserving permissions and Git ignores. Avoid blanket
`.env*` copying or shared writable configuration links.

Preserve a harness-assigned worktree and branch. Verify the requested base when
starting a fresh task; continuing a task does not mean restarting it from main.
See https://code.claude.com/docs/en/worktrees for installed-client behavior.
