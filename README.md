# agent-skills

Twelve on-demand [Agent Skills](https://agentskills.io) for Claude Code: task
setup, code investigation and design, audits, evidence capture, and local vault
memory. This repository contains `SKILL.md` procedures, supporting references,
helper scripts, an installer, and eval fixtures. It is the Claude Code collection;
the separate Codex package and installation are maintained separately.

## Skills

| Skill | Use |
|---|---|
| [new-feature](new-feature/SKILL.md) | Start tasks in isolated worktrees from a freshly fetched base |
| [current-docs](current-docs/SKILL.md) | Verify uncertain integrations against version-specific official docs |
| [system-reasoning](system-reasoning/SKILL.md) | Investigate architectural choices and unclear root causes |
| [understand-before-changing](understand-before-changing/SKILL.md) | Inspect existing behavior and constraints before editing |
| [code-structure](code-structure/SKILL.md) | Place logic with its owner; extract concrete duplication |
| [no-ai-tells](no-ai-tells/SKILL.md) | Remove redundant comments and scaffolding while writing |
| [evidence-driven-testing](evidence-driven-testing/SKILL.md) | Capture recordings, screenshots, or measured proof |
| [project-audit](project-audit/SKILL.md) | Report prioritized codebase health findings |
| [ux-speed-audit](ux-speed-audit/SKILL.md) | Measure loading and interaction responsiveness |
| [managed-audit](managed-audit/SKILL.md) | Coordinate explicitly requested specialist or station audits |
| [no-ai-tells-audit](no-ai-tells-audit/SKILL.md) | Remediate readability problems across existing source |
| [vault-memory](vault-memory/SKILL.md) | Archive sessions and recall relevant Markdown notes |

[AGENTS.md](AGENTS.md) explains sequencing and concurrency. Audit findings do not
by themselves authorize changes. Concurrent source writers need separate
worktrees; performance measurements need a quiet machine.

For recurring workers, `system-reasoning` includes
[loop admission, retry, and budget guidance](system-reasoning/references/agent-loops.md).
For verification, `evidence-driven-testing` covers
[realistic scenarios and retaining useful tests](evidence-driven-testing/references/useful-tests.md).
Verification need not add permanent test files; retain checks for meaningful
uncovered behavior, and preserve older regression cases while they remain relevant.

## Installation and requirements

```bash
git clone https://github.com/ronnyabuto/agent-skills.git
cd agent-skills
./install.sh --vault ~/agent-vault
```

The Bash installer discovers every top-level folder containing `SKILL.md` and
symlinks it into `~/.claude/skills/` (or `$CLAUDE_CONFIG_DIR/skills/`). It also links
skills for Antigravity when `~/.gemini/antigravity/` exists; that does not make
Claude-specific delegation or hooks portable. Existing folders and links pointing
elsewhere are skipped. Edits in the linked checkout take effect without copying.

By default it merges vault-memory hooks and `AGENT_VAULT` into Claude's
`settings.json`, backing up an existing file before writing. Without `--vault`,
it prompts on an interactive terminal or uses `~/agent-vault`. An existing
`settings.env.AGENT_VAULT` takes precedence. Start a new session or run `/hooks`
after installation to load the hooks.

| Flag | Effect |
|---|---|
| `--vault <path>` | Choose the vault without prompting |
| `--no-hooks` | Link skills without changing settings |
| `--dry-run` | Preview changes without writing |
| `--uninstall` | Remove this checkout's links and matching vault hooks; keep notes and `AGENT_VAULT` |

Vault hooks require Node 22.x ≥ 22.16 or Node ≥ 24 with SQLite FTS5; the installer
probes runtime capabilities and leaves hooks uninstalled if unavailable. Obsidian
is optional. Desktop evidence recording needs Python 3, a drivable GUI, and
`ffmpeg`/`ffprobe` with libx264 and the ass filter. Headless evidence uses a
scriptable browser or probe instead. Git task setup needs Git and GitHub CLI;
live evals need Python 3 and an authenticated Claude Code CLI. The paired
outcome runner requires Claude Code ≥ 2.1.300. See
[compatibility and optional diagnostics](docs/claude-code.md) for the reviewed
client version, invocation controls, and cooperation with bundled workflows.

For project scope, link individual skill folders into `.claude/skills/` manually.
Installed skills provide procedures when invoked. Put standing instructions in
[`~/.claude/CLAUDE.md`](https://code.claude.com/docs/en/memory).
This checkout's `CLAUDE.md` imports `AGENTS.md`; installation does not install
those project instructions globally. Preserve existing personal instructions.

## Privacy

Keep vaults outside source trees and public sync. Git ignores do not exclude
archives from zip/tar files or workspace shares. Pattern redaction cannot remove
all secrets or personal data; use `VAULT_MEMORY_EXCLUDE` for sensitive projects.
The searchable index also contains private text: keep `~/.cache/vault-memory/`
(or its `XDG_CACHE_HOME` location) private. To relocate memory, update the existing
`AGENT_VAULT` setting, safely move `claude/` archives and notes, restart Claude,
and rebuild with `node vault-memory/scripts/vault.mjs index --rebuild`.

## Evaluation and provenance

The collection retains 50 trigger scenarios across 12 skills and adds four
paired outcome cases. Trigger evaluations measure discovery; outcome evaluations
compare fresh enabled/disabled sessions and grade actual files, returned data,
retrieved decisions and retained evidence. Neither establishes complete model
compliance by itself. See [evaluation instructions and rubrics](evals/README.md).

```bash
# Offline checks; no model calls
python3 -m unittest discover -s evals -p 'test_*.py' -v
python3 vault-memory/scripts/test_vault.py

# Inspect paired cases without running Claude
python3 evals/run_outcome_evals.py --list

# Live comparison of the current checkout; consumes model usage
python3 evals/run_outcome_evals.py --model sonnet --case memory-recall --max-budget-usd 0.75
```

Paired runs keep synthetic workspaces, transcripts, grading evidence and metrics
in a new private directory under `/tmp/`. The default cap is $0.75 per arm,
with two arms per case, and may be exceeded. Failed-session costs remain visible;
missing costs stay unknown. A baseline that passes is a valid result. The existing
trigger runner still evaluates installed skills and writes metadata to
`.artifacts/trigger-evals-*.jsonl` without copying full transcripts.

This collection began with `code-structure`, `new-feature`, and
`evidence-driven-testing` from
[michaelshimeles/skills](https://github.com/michaelshimeles/skills).
Their procedures have been modified here; the inherited `evidence.py` recorder
remains unchanged from the initial import. The other skills were authored locally;
`managed-audit` adapts the separate Codex skill for documented Claude Code
capabilities. Attribution records provenance, not a new license grant.
