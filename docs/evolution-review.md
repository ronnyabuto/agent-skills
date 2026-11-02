# Two-runtime evolution review — 2026-11-02

Reviewed bases: agent-skills `4fd9385`, codex-skills `81be007`.
The original working trees were clean. CLI help: Claude Code 2.1.300,
Codex CLI 0.166.0. Baseline Claude: 12 eval-harness + 8 vault tests passed.
Baseline Codex: inventory of 55 files and validation passed; 57 tests ran,
55 passed and 2 optional FFmpeg tests skipped. No paid model calls were run.

## Findings at the reviewed revisions

1. **CONFIRMED — identity and supersede gap.** Claude
   `vault-memory/scripts/vault.mjs:60` used a folder basename, special-casing
   only `.claude/worktrees`; its command table at `:643` lacked supersede.
   Codex `plugins/ronny-codex-skills/skills/vault-memory/scripts/memory.py:22`
   used common-directory hashing and its `:304` implemented supersede.
   Original-source regression probes reproduced Claude same-name collisions
   and a further Codex separate-Git-directory label split. Common-dir hashing
   alone did not guarantee the full ID stayed stable for that Codex layout.

2. **PARTIALLY CONFIRMED — footprint and triggers.** Claude
   `new-feature/SKILL.md:8` required a worktree per task; `:43` stopped on PR
   file overlap; `:80` prescribed fresh dependency installation.
   `code-structure/SKILL.md:48` prohibited single-implementation interfaces,
   and `:99` prohibited service database access. `AGENTS.md:44` described a
   mandatory sequence. Codex's corresponding definitions and
   `references/agent-guidance.md:1` were more proportional. However, omission
   of `disable-model-invocation` is not inherently a defect: hiding audits
   would remove intended automatic matching. Existing docs deliberately kept
   discovery enabled. Preserve that policy and narrow descriptions instead.

3. **CONFIRMED design risk, not a measured performance result — outcome prompts.**
   Both `evals/outcome_cases.py:11` collections contained procedural prompts.
   These were fair identical prompts, not cross-arm leakage, but tested a
   narrower task than natural discovery. Removing procedure may reveal an
   incremental benefit; a larger benefit is not established without live runs.

4. **PARTIALLY CONFIRMED — Wayland.** Claude
   `evidence-driven-testing/scripts/evidence.py:154` probed wlr-screencopy,
   then optimistically used desktop names. Its reference already disclosed
   GNOME/KDE limitations. Claude had no test_recorder.py; Codex's
   `tests/test_recorder.py:1` covers its independent recorder. A missing GNOME
   backend is a declared capability limit, not a hidden regression.

5. **PARTIALLY CONFIRMED — drift.** The differences above are real. Different
   hooks, namespaces, installers and recorders are deliberate. Codex
   `scripts/build_release.py:12` and `scripts/install_local.py:69` enforce
   package integrity, not semantic parity. Claude `install.sh:48` links source
   skills instead of installing a verified release copy. A shared runtime or
   generator would couple independently installed packages unnecessarily.

## Decisions and implementation order

1. Keep the Claude Node adapter. Replacing it with Python would also require
   changing installed hook commands, environment keys, transcript parsing,
   archival layout, index behavior and dependency checks. Add stable identity
   and supersede in place; retain legacy notes and explicit basename search.
   Hook pointers label legacy ownership uncertain instead of injecting titles.
   Codex now handles separate-Git-directory labels and retains same-hash legacy
   lookup in search/recent/hooks. No user vault was read, migrated or modified.
2. Extract shared outcome definitions into outcome_contracts.json. Natural
   requests are separate from output serialization contracts and hidden checks.
   Keep filenames/JSON interfaces visible so evidence remains deterministically
   replayable. Add an irrelevant-skill arithmetic control and per-pair overhead.
   Grading remains rule-based, not a claim of complete semantic coverage.
3. Backport compact code-structure, current-docs, no-ai-tells and
   understand-before-changing definitions; make worktree isolation conditional,
   retain fresh-branch guarantees, and replace mandatory standing sequencing.
   Preserve Claude-specific worktree environment guidance and invocation defaults.
4. Require a successful protocol probe for automatic Wayland availability;
   probe failures cannot advertise support. Preserve explicit source attempts.
   Do not add a portal/PipeWire backend as a detection fix.
5. Keep independently installable repos. Add an optional sibling-source check
   for shared outcome definitions and four neutral skills. Tests exercise real
   identity, recall and failure boundaries in each runtime. Rebuild Codex's
   inventory after edits, including new public files.

## Official documentation checked

- [Claude project instruction loading](https://code.claude.com/docs/en/memory):
  modern AGENTS.md fallback is version/settings dependent; @AGENTS.md remains
  supported and need not be removed.
- [Claude skills](https://code.claude.com/docs/en/skills):
  disable-model-invocation removes automatic discovery; allowed-tools is not
  an OS sandbox.
- [Claude hooks](https://code.claude.com/docs/en/hooks) and
  [Codex hooks](https://learn.chatgpt.com/docs/hooks): preserve client-specific
  installation, trust, payload and lifecycle behavior.
- [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
  [skills](https://learn.chatgpt.com/docs/build-skills) and
  [sandbox](https://learn.chatgpt.com/docs/sandboxing): discovery, implicit
  invocation policy and execution boundaries are separate mechanisms.
- [wf-recorder upstream](https://github.com/ammen99/wf-recorder) and
  [ScreenCast portal](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.ScreenCast.html):
  a portal-backed capture route requires session/source/stream handling, not
  compositor-name inference.

## Verification limits

Offline tests use synthetic repos, vaults, subprocess stand-ins and mocked
protocol probes. Before-change identity regression probes failed as expected.
The local capture doctor reports FFmpeg/FFprobe unavailable and no automatic
screen source. No live GUI capture, paid evaluation, installation, global
configuration edit or external publication was performed. Performance uplift
and the effect of shorter prompts remain unmeasured. The sibling-source check
is optional; it does not synchronize remote repositories automatically.

## Verification results and retained evidence

- Claude: 19 evaluation/capture/contract checks plus 13 vault checks passed.
- Codex: 60 tests ran; 58 passed, 2 optional real-media checks skipped because
  FFmpeg is unavailable. Package validation and the 58-file release inventory
  passed. Both repositories pass `git diff --check`.
- The sibling contract check passes in both directions. All 24 skill entry
  points parse as YAML with matching names and string descriptions. Claude's
  supported compatibility field is retained; the Codex-only skill validator's
  narrower field allowlist is not used as a Claude compatibility gate.
- Before-fix probes: `/tmp/evolution-before-regressions.log`.
- Claude checks: `/tmp/evolution-claude-final-evals.log` and
  `/tmp/evolution-claude-final-memory.log`.
- Codex checks: `/tmp/evolution-codex-final-tests.log`.
- Capture diagnostic: `/tmp/evolution-capture-doctor.json` (text doctor output).

Changes are retained on `agent/evolution-1102` in each independent checkout.
The audit and implementation were completed before installation and publication.
