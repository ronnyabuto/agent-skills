# Behavioral evaluation plan

cases.json contains positive, negative and boundary requests with observable success criteria. These are scenarios, not completed benchmark results. Evaluate each with and without the selected skill using the same Codex model and tools. Create a fresh disposable fixture for every case, with no live credentials or production access. Repeat ambiguous/stochastic cases and capture task outcomes, invocation, unintended changes, commands, elapsed time and token use. Do not score merely whether a skill was opened.

Fixtures should provide the actual prerequisite for each case: pinned packages and matching documentation for current-docs, known faults and harmless executable tests for project-audit, a runnable production app with controlled timings for ux-speed-audit, committed code/history for legacy reasoning, separate worktrees and local remotes for isolation, and synthetic notes/transcripts for memory. Use local PR-shaped fixture data rather than real account mutations. Do not import personal archives into evaluations.

The package's unit tests validate concrete memory and installation invariants. They do not substitute for agent behavior evaluation. This release has no paid model benchmark or live desktop capture result.
