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

### [project-audit](project-audit/SKILL.md)

Full-codebase health audit — architecture, correctness risk, security, dependencies,
test coverage, operational readiness — as a prioritized, severity-ranked findings
report. Original, self-authored (not from upstream). Use for "audit this project" /
"review the codebase" style requests.

### [ux-speed-audit](ux-speed-audit/SKILL.md)

Audits UX responsiveness and page-load speed against Nielsen's response-time
thresholds (0.1s = instant, 1s = max before flow breaks). Measures live, not from
source alone — Core Web Vitals, render-blocking resources, bundle size, perceived
speed, data-layer waterfalls, caching. Original, self-authored. Use for "make it
feel instant" / loading-speed audits.

### [no-ai-tells](no-ai-tells/SKILL.md)

Final-pass checklist against comment/structural patterns that read as
LLM-generated or amateur (redundant comments, banner dividers, staged "Step 1/2"
narration, task-reference comments, disproportionate defensive completeness,
naming inconsistent with the surrounding file). Sourced from cross-checked
research (AI-code-review-tooling writeups), not just opinion. Original,
self-authored. Use as a final pass before finishing any code-writing task.

### [no-ai-tells-audit](no-ai-tells-audit/SKILL.md)

The one-time remediation version of `no-ai-tells` — sweeps an *existing*
codebase for the same tells and fixes them, rather than applying the checklist
inline while writing new code. **Mutates source directly** — see
[AGENTS.md](AGENTS.md) for how to sequence it against the other skills.
Original, self-authored. Use for "clean up this codebase" / "get rid of AI
tells."

### [current-docs](current-docs/SKILL.md)

Before implementing against a library/framework/SDK/API whose current
behavior isn't certain from memory, identify the version actually pinned in
this project (lockfile/manifest, not "latest") and fetch *that* version's
official docs as source of truth. Greenfield/unpinned deps get latest docs
instead, since there's no existing constraint to respect. Original,
self-authored. Skip it for stable stdlib/syntax work — it's scoped to
genuine version uncertainty, not every task.

## How these fit together

[AGENTS.md](AGENTS.md) defines the actual orchestration: which skills run in
sequence (`new-feature` → implement with `code-structure`/`no-ai-tells` →
`evidence-driven-testing`), and which are safe to run concurrently
(`project-audit` + `ux-speed-audit`, since both are read/measure-only) versus
which need exclusive write access to the tree (`no-ai-tells-audit`, since it
edits source directly).

## Installing (per machine)

Symlink each skill folder — or the whole repo — into the client's skills directory so
edits here take effect immediately everywhere:

```bash
# Claude Code (global, all projects)
for skill in code-structure new-feature evidence-driven-testing project-audit ux-speed-audit no-ai-tells no-ai-tells-audit current-docs; do
  ln -s ~/Desktop/agent-skills/$skill ~/.claude/skills/$skill
done

# Antigravity (global, all workspaces)
for skill in code-structure new-feature evidence-driven-testing project-audit ux-speed-audit no-ai-tells no-ai-tells-audit current-docs; do
  ln -s ~/Desktop/agent-skills/$skill ~/.gemini/antigravity/skills/$skill
done
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
