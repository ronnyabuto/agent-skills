# Ronny's Codex skills

A separate personal Codex plugin containing twelve scoped development workflows. It uses the portable plugin manifest plus the supported Codex compatibility manifest, with a local marketplace at .agents/plugins/marketplace.json. No external connector or authentication service is required. Optional vault-memory lifecycle hooks require user authorization and Codex hook trust.

## Contents

current-docs, project-audit, ux-speed-audit, understand-before-changing, code-structure, no-ai-tells, no-ai-tells-audit, new-feature, evidence-driven-testing, vault-memory, managed-audit and system-reasoning.

Use system-reasoning before substantial design decisions or unclear bug fixes:
derive requirements and invariants, separate evidence from assumptions, test
causal explanations, and verify the correction. Routine CRUD and established
local causes stay lightweight. code-structure and managed-audit hand off to this
skill when the decision needs it.

The historical no-ai-tells names remain recognizable, but their instructions concern readability rather than authorship detection. Skills are available for automatic matching and explicit invocation; their narrow descriptions do not mandate running every skill on every task. Use the namespaced selector shown by Codex if another plugin offers the same skill name.

## Managed audits

New task branches default to freshly fetched origin/main. The new-feature skill requires a successful fetch and base verification, preserves explicit release/PR bases, and does not pull into or reset local main just to create a branch.

Invoke `$managed-audit` for a manager-led audit with specialist workers or a station-by-station role/dashboard review. The manager owns task scope, live state, questions and final synthesis. Worker targets default to 15-minute checkpoints and a 60-minute assignment, with observable evidence instead of mandatory commits. These are operating targets; the skill does not install a timer or external supervisor. It provides bounded replacement and handoff guidance.

Keep platform URLs, account identities, credentials, reset permissions, implementation authority and station pacing in your task prompt. The skill does not confer them. Example:

```text
Use $managed-audit to understand this platform, map its actual roles and
customer journey, and audit one station at a time. Inspect each role's
rendered dashboard and perform an orientation walkthrough with the
designated test client. Ask focused questions as needed. Give me supported
findings and the simplest adequate improvements; discuss this station
with me before advancing. Do not implement changes yet.
```

## Install

Store the complete marketplace directory at a stable user-owned location, then run:

```bash
codex plugin marketplace add /absolute/path/to/ronny-codex-skills --json
codex plugin add ronny-codex-skills@ronny-local --json
codex plugin list --json
```

Use codex plugin commands to manage configuration. Codex installs a cached copy; editing the source does not necessarily update the loaded plugin. Refresh the marketplace and reinstall/update through the supported client, then start a new session. Do not hand-edit the plugin cache.

The provided scripts/install_local.py stages the source under ~/.codex/local-marketplaces/ronny-codex-skills, backs up Codex configuration, invokes the supported CLI commands and verifies installed/enabled status. With --migrate-duplicates it moves only byte-identical copies of the three skills installed during the preceding review into a backup, after the plugin is verified. It refuses unknown source directories, marketplace-name conflicts or modified duplicates rather than overwriting them. Use --dry-run to inspect targets. Claude paths are never install targets.

## Memory

The installer preserves the chosen vault in ~/.config/ronny-codex-skills/memory.json;
CODEX_MEMORY_VAULT can override it. Saving decisions and importing selected
Codex transcripts remain explicit operations. When authorized, trust the three
user-level memory hooks in Codex `/hooks` to archive before compaction and at session end,
and receive a bounded recall pointer at session start. The helper never reads
Claude archives or modifies Claude settings. See the memory skill for exclusions
and transcript-format limitations.

To upgrade from this repository while retaining an already configured vault:

```bash
python3 codex/scripts/install_local.py --agent-guidance --memory-hooks
```

The optional --agent-guidance flag preserves existing global Codex AGENTS.md
text and updates only this package's marked block. Configuration and prior
marketplace source are backed up. Review and trust new hooks in `/hooks`; the
installer does not bypass trust. Restart Codex after plugin upgrades.

--memory-hooks merges three user-level handlers into ~/.codex/hooks.json and
preserves unrelated hooks. Commands use the stable installed marketplace path,
so the cache's version directory is not embedded in configuration. This route
was verified on the local CLI; bundled plugin-hook discovery was unavailable
there. Archive before compaction and at shutdown, not continuously; local
hooks do not imply support in cloud-orchestrated sessions.

## Validation

```bash
python3 scripts/validate.py
python3 -B -m unittest discover -s tests -v
```

Validation checks manifests, skill frontmatter, contained references, Python syntax and unchanged recorder provenance. Tests cover memory scoping, realpath containment, concurrent notes, redaction, index freshness, transcript import and superseded notes. evals/cases.json contains independent positive/negative behavior scenarios for a future agent evaluation; it is not a claimed model benchmark. Do not run paid agent evaluations without authorization. Each behavioral case needs a fresh disposable fixture and comparison with/without the skill.

`python3 codex/evals/run_system_reasoning.py <new-output-directory>` runs five
read-only Codex cases with fresh synthetic fixtures and saves JSONL events,
answers, token usage, and fixture-integrity checks. It uses the installed plugin
and configured Codex model. Invocation checks supplement human review of actual
answers; this smoke suite alone is not a comparative benchmark. API failures
are reported as errors. Keep output outside the package directory.

GUI recorder smoke checks require ffmpeg/ffprobe and a supported capture environment. A successful manifest check or media probe does not establish successful agent behavior. See plugins/ronny-codex-skills/PROVENANCE.md before sharing this personal package.
