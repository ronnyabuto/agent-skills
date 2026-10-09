# Release validation — 2026-10-09 (1.2.0)

- Package validation and all twelve skill entrypoints pass structural checks.
- Twenty-four isolated tests pass: memory scoping/imports, installation safety,
  guidance preservation, hook preservation/idempotence, archive updates,
  exclusions, redaction, malformed/torn transcripts, search/read, and recall.
- Five live system-reasoning smoke cases passed on this PC with Codex CLI
  0.161.0 and its default GPT-6.1-Sol model. Three positive cases read the skill;
  routine CRUD and an established local bug did not. Answers and harmless
  probes were reviewed; all fixture hashes remained unchanged. See
  [evals/system-reasoning-results.json](evals/system-reasoning-results.json).
  These are single runs on synthetic fixtures, without a comparative baseline.
  The other catalog scenarios have not been run.
- The installed/enabled 1.2.0 plugin contains all twelve skill entrypoints and
  resources. Global Codex AGENTS.md includes the scoped guidance block.
  Installation preserves Claude settings/skills and the existing Codex vault.
- This CLI's hook browser did not discover bundled plugin hooks. Installation
  uses user-level ~/.codex/hooks.json instead. All three exact hook definitions
  were reviewed and trusted through the native `/hooks` interface; the browser
  reports one installed and active handler for each event.
- A real local Codex session archived on shutdown into the configured vault;
  search and bounded reads recovered its unique test marker. A native `/compact`
  archived another session before compaction completed. The immediate model
  continuation identified the correct vault and pre-compaction archive from
  its injected pointer without tools. Hook JSON recall and compaction pointers
  also pass isolated tests. These results concern local
  Codex execution, not cloud-orchestrated hook support.

## Previous release — 2026-10-02

- All eleven skills pass Codex's bundled quick_validate.py.
- Portable/Codex compatibility manifests, marketplace, relative references, entrypoint lengths, Python syntax and retained recorder hash pass scripts/validate.py.
- Fifteen isolated tests pass: ten memory tests and five installation safety tests. They cover scoped recall, worktree identity, bounded output, fresh indexes, redaction examples, supersession, concurrent note writes, containment, explicit transcript imports, preserved duplicates after a failed plugin verification, modified/symlink duplicate refusal, mutation-free dry runs and a local upgrade that preserves Claude/memory configuration without attempting a Git-marketplace refresh.
- One hundred ten behavioral scenarios are provided, ten per skill. They are marked not-run; no paid model evaluations were performed. The new managed-audit cases cover manager requests, narrow non-trigger requests, evidence without commits, missing tools and preservation of audit permissions.
- The retained recorder's doctor was run during the preceding review and reported missing ffmpeg/ffprobe and no capture source in that execution environment. GUI recording, interruption recovery and browser capture are not end-to-end validated here.
- Local installation is checked with codex plugin list --json and byte comparisons against all installed skill entrypoints. The installer compares Claude settings, skill contents and symlink targets before/after the operation. The original three standalone Codex skills were backed up during initial installation; updates retain those backups and the memory configuration.

The structural checks use this package's supported subset, not full remote JSON Schema validation. Passing them does not prove agent workflow quality. The unit tests use only synthetic notes/transcripts and disposable Git fixtures.
