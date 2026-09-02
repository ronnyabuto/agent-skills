# agent-skills

Personal collection of [Agent Skills](https://agentskills.io) — the open, cross-platform
`SKILL.md` format for giving coding agents on-demand procedural knowledge. Works with
Claude Code, Antigravity, and any other client that implements the spec.

Started as a trimmed fork of [michaelshimeles/skills](https://github.com/michaelshimeles/skills).
Kept only what has zero external paid-tool dependency or genuine standalone value;
dropped the skills that existed to orchestrate a specific third-party service (Greptile,
Vercel's before-and-after CLI) I don't use.

**Provenance note:** the upstream repo carries no root `LICENSE` file, so the content
below (including `evidence-driven-testing/scripts/evidence.py`) is still the original
author's unlicensed work, kept here verbatim for personal use — not rewritten, not
relicensed. This repo stays private for that reason. As I customize each skill for my
own workflow the diff from upstream will grow; until then, treat the content as
"borrowed with attribution," not "owned."

## Skills

### [code-structure](code-structure/SKILL.md)

Service layer architecture guidance — separates **actions** (orchestrate domain rules)
from a **service layer** (reusable operational mechanics). Use when multiple workflows
duplicate the same operational logic, or when deciding what belongs in actions vs.
shared services.

### [new-feature](new-feature/SKILL.md)

Starts every new task in an isolated Git worktree branched from `origin/main` — unique
task naming, a scope check against open PRs, cleanup after merge. Use at the start of
any new feature/fix/task, or when running multiple agent sessions on the same repo.

### [evidence-driven-testing](evidence-driven-testing/SKILL.md)

Records visual proof while testing UI behavior (screen recording + structured
annotations, or scripted screenshots in headless environments), then summarizes results.
Needs `ffmpeg`/`ffprobe` (with libx264) locally — see the skill's `compatibility` note.
Use whenever a change needs verifiable evidence instead of prose claims.

## Installing (per machine)

Symlink each skill folder — or the whole repo — into the client's skills directory so
edits here take effect immediately everywhere:

```bash
# Claude Code (global, all projects)
ln -s ~/Desktop/agent-skills/code-structure ~/.claude/skills/code-structure
ln -s ~/Desktop/agent-skills/new-feature ~/.claude/skills/new-feature
ln -s ~/Desktop/agent-skills/evidence-driven-testing ~/.claude/skills/evidence-driven-testing

# Antigravity (global, all workspaces)
ln -s ~/Desktop/agent-skills/code-structure ~/.gemini/antigravity/skills/code-structure
ln -s ~/Desktop/agent-skills/new-feature ~/.gemini/antigravity/skills/new-feature
ln -s ~/Desktop/agent-skills/evidence-driven-testing ~/.gemini/antigravity/skills/evidence-driven-testing
```

Project-scoped instead of global: symlink into `.claude/skills/` or `.agents/skills/`
inside a specific repo instead.

## Adding a new skill

1. New folder, kebab-case name.
2. `SKILL.md` with `name` and `description` frontmatter — the description is what the
   agent matches against, so make it trigger-focused ("Use when...").
3. Keep the body concise; put anything long in `references/`, put runnable helpers in
   `scripts/`.
4. Symlink it into whichever client directories you want it active in (see above).
