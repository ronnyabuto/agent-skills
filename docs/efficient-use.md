# Using the skills efficiently with Claude Opus 5.5

Keep the twelve skills available on demand. Give Claude the requested outcome,
constraints and acceptance check; let it select the procedure that answers the
actual uncertainty. Do not require the entire collection for every edit.

| Task | Relevant procedure |
|---|---|
| Fresh implementation | `new-feature` once; preserve existing work and verify the base |
| Established local fix | Inspect the owner and callers, fix it, run the affected check |
| Unknown workaround or risky removal | `understand-before-changing` |
| Concrete ownership or duplication question | `code-structure` |
| Unclear recurring failure or architecture decision | `system-reasoning` |
| Uncertain version-specific integration | `current-docs` |
| Requested proof, test design or measured improvement | `evidence-driven-testing`; choose the relevant reference |
| Previous decision needed | `vault-memory`; search distinctive terms, then read matching lines |
| Requested audit | The audit matching the scope; `managed-audit` only for requested coordination |
| Requested readability cleanup | `no-ai-tells` for a diff; `no-ai-tells-audit` for repository-wide remediation |

Do not repeat a successful launch, review or verification pass unless something
changed or a remaining risk requires it. Read referenced skills and documents
when their stated condition applies, not simply because a link is present.

## Model and effort

For Opus 5.5, select the exact model and start at medium effort:

```bash
claude --model claude-opus-5-5 --effort medium
```

Check the session's effective model and effort, including environment or managed
overrides. Anthropic documents strong multistep repository work and recommends
calibrating from medium rather than carrying over higher settings from older
models. Higher effort can spend more thinking tokens. Keep explicit completion
criteria for unattended tasks: a progress report alone does not prove completion.
Do not introduce an automatic continuation loop for ordinary interactive work.
See [model configuration](https://code.claude.com/docs/en/model-config) and
[Opus 5.5 prompting](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5).

## Context and memory

Discovery descriptions are visible before invocation; full skill instructions
load when invoked. Current Claude Code documentation describes deduplication of
identical invocations and carrying invoked instructions through compaction within
budgets. Ordinary shell/file reads are not the Skill tool's invocation mechanism.
See [skill lifecycle](https://code.claude.com/docs/en/skills#skill-content-lifecycle).

Keep the existing settings-level vault hooks. SessionStart emits bounded recall
context; PreCompact and SessionEnd archive locally without loading whole
archives into the prompt. Search only when the task needs a prior decision or
attempt. Setup and hook changes are separate from routine recall.

Repository instructions must work without a contributor's personal CLAUDE.md.
Do not remove useful project constraints just to reduce overlap with your own
global configuration, or hide useful skills merely to shrink their descriptions.

## Measure a proposed improvement

Choose one observed unnecessary read, repeated check or misleading instruction.
Compare the unchanged and proposed versions in fresh sessions on the same source
snapshot, exact model, effort, tools and acceptance criteria. The
[paired runner](../evals/README.md) supports explicit effort selection. Live
comparisons consume model usage; offline harness checks do not establish savings.

Compare task correctness and preserved scope first, then tool calls, input/cache
categories, output, elapsed time and available cost. Claude's ordinary input,
cache-read and cache-creation fields are separate usage categories; keep them
visible. A smaller instruction can cause more exploration, so compare complete
tasks, not file lengths. Keep existing safeguards unless a measured replacement
preserves their behavior. A passing baseline is a valid result.
