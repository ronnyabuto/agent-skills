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

Audits page-load speed against Core Web Vitals (LCP ≤ 2.5 s, INP ≤ 200 ms,
CLS ≤ 0.1 at the 75th percentile) and interaction feedback against Nielsen's
response-time limits (0.1 s instant, 1 s flow, 10 s attention). Measures live
on a production build, median of 5 runs — render-blocking resources, bundle
size, perceived speed, data-layer waterfalls, caching. Original, self-authored. Use for "make it
feel instant" / loading-speed audits.

### [no-ai-tells](no-ai-tells/SKILL.md)

Final-pass checklist against comment/structural patterns that read as
LLM-generated or templated (comments that restate code, staged "Step 1/2"
narration, change-history comments, untracked stubs, disproportionate defensive
completeness, naming inconsistent with the surrounding file). The structural
entries match peer-reviewed human-vs-LLM code comparisons (more templated,
repetitive, generically named, duplicated); the comment entries are
established readability practice rather than measured AI signatures. Original,
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

### [understand-before-changing](understand-before-changing/SKILL.md)

Chesterton's Fence for code, applied broadly: whenever a task touches an
*already-existing* file — editing it, deleting from it, **or adding new code
into it** — investigate why the existing implementation is the way it is
(git blame/log, tests, comments, linked issues) before touching it. Classify
the finding as confirmed-valid, outdated/wrong, or undeterminable — never
invent a plausible-sounding "why" when the real answer is "unknown." Also
gates `no-ai-tells-audit` before it deletes anything. Original,
self-authored. Only exempt for a genuinely new file/module with nothing
existing to reference.

### [vault-memory](vault-memory/SKILL.md)

Long-term memory in an Obsidian vault, loaded by reference instead of by
value. Hooks archive every session before compaction and at exit — condensed
to prompts, replies, one line per tool call, and the compaction summaries
(96–98% smaller than the raw transcript in the sessions measured), secrets redacted. Session start
injects a ~250-token pointer; everything else is pulled in on demand through
a zero-dependency Node script (SQLite FTS5/BM25, ~120 ms per search) that
returns ~60 tokens per hit and reads only the matching line range. Obsidian
doesn't need to be running. Needs Node >= 22.5 and the hook snippet in
[references/hooks.json](vault-memory/references/hooks.json) merged into
`~/.claude/settings.json`. Original, self-authored.

## How these fit together

[AGENTS.md](AGENTS.md) defines the actual orchestration: which skills run in
sequence (`new-feature` → implement, with `understand-before-changing` /
`code-structure` / `no-ai-tells` all applied inline as ongoing lenses →
`evidence-driven-testing`), and which are safe to run concurrently
(`project-audit` + `ux-speed-audit`, since both are read/measure-only) versus
which need exclusive write access to the tree (`no-ai-tells-audit`, since it
edits source directly).

## Evals

`evals/<skill>.json` holds three scenarios per skill in Anthropic's
documented format (`skills`, `query`, `files`, `expected_behavior`): two that
should trigger the skill and one near-miss that shouldn't. The trigger check
runs each query in a fresh headless session inside a throwaway fixture repo
and records which skills it invokes:

```bash
evals/build_fixture.sh /tmp/skill-evals
python3 evals/run_trigger_evals.py /tmp/skill-evals sonnet   # or: haiku, opus; add skill names to filter
```

It measures the skills installed in `~/.claude/skills`, so merge description
changes first. Last measured on Sonnet (2026-09-23, one sample per case):
27/30, with run-to-run variation on individual cases, so rerun before
reading much into a single miss. It checks triggering only; whether the
skill's instructions are then followed (`expected_behavior` beyond the first
line) still needs a human read of the transcript.

## Installing (per machine)

Symlink each skill folder — or the whole repo — into the client's skills directory so
edits here take effect immediately everywhere:

```bash
# Claude Code (global, all projects)
for skill in code-structure new-feature evidence-driven-testing project-audit ux-speed-audit no-ai-tells no-ai-tells-audit current-docs understand-before-changing vault-memory; do
  ln -s ~/Desktop/agent-skills/$skill ~/.claude/skills/$skill
done

# Antigravity (global, all workspaces)
for skill in code-structure new-feature evidence-driven-testing project-audit ux-speed-audit no-ai-tells no-ai-tells-audit current-docs understand-before-changing vault-memory; do
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
