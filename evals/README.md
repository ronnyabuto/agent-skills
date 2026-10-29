# Evaluating this collection

Triggering and outcome quality answer different questions. Keep both: a skill
can be discovered correctly and followed poorly, or add no value over the model
without it. These runners use this repository's fixtures and formats; they are
not the interchangeable input formats of `skill-creator` or `claude plugin eval`.
The official [evaluation guidance](https://code.claude.com/docs/en/skills#evaluate-and-iterate-on-a-skill)
describes baseline comparisons and those alternatives.

## Offline checks

```bash
python3 -m unittest discover -s evals -p 'test_*.py' -v
python3 vault-memory/scripts/test_vault.py
python3 evals/run_outcome_evals.py --list
```

The harness tests replace Claude with a local executable and exercise real
fixtures, grading, reports, failed sessions and unknown costs. They make no
model calls and do not claim that Claude follows the skills.

## Trigger evaluations

`*.json` contains 50 scenarios across 12 skills. The first expectation's
`Invokes` or `Does not invoke` prefix determines the score; behavioral-only
cases are skipped. Subsequent expectations remain useful for transcript review.

```bash
bash evals/build_fixture.sh /tmp/skill-evals
python3 evals/run_trigger_evals.py /tmp/skill-evals sonnet managed-audit --max-budget-usd 0.50
```

This runner evaluates **installed** skills with the user's normal configuration.
Each case gets disposable fixture state and synthetic memory. It writes a unique
`.artifacts/trigger-evals-*.jsonl`, or a new `--report <path>`, with calls, turns,
reported costs, usage, timing and errors. It does not retain full transcripts.

`--max-turns` defaults to `EVAL_MAX_TURNS` or 6; `--timeout` to 400 seconds.
`--max-budget-usd` or `EVAL_MAX_BUDGET_USD` is optional and applies per case.
Errors and failed-session costs stay visible. Cost per completed eval includes
reported failed-session cost and is omitted when any executed case lacks cost.
The exit status is nonzero for failed expectations, errors or no scored cases.

## Paired outcome evaluations

This runner evaluates a **snapshot of the selected skill in this checkout**,
without installing it. It requires an authenticated Claude Code >= 2.1.300,
Python 3, Git, and Node with SQLite FTS5 for the memory case.

```bash
python3 evals/run_outcome_evals.py --list
python3 evals/run_outcome_evals.py --model sonnet --case memory-recall --max-budget-usd 0.75
python3 evals/run_outcome_evals.py --model sonnet --output /tmp/my-skill-outcomes
```

Omit `--case` for all four cases; repeat it to select several. Each case runs
sequentially in two fresh sessions with identical synthetic starting state and
prompt. The selected skill is frozen once under `candidates/`, copied to project scope
in both workspaces and
set to `on` or `off` through session-only `skillOverrides`. Case order alternates
which arm runs first. The runner copies no repository standing instructions,
so the disabled baseline is not taught the skill's procedure through AGENTS.md.

| Case | Observable checks |
|---|---|
| `assigned-worktree` | Keep the assigned branch/worktree, fetch the local origin, retain the current base, correct calendar results and leave the main checkout untouched. |
| `audit-scope` | Leave source unchanged, identify the actual validation failure with a location and reproduction, and disclose unavailable delegation. |
| `memory-recall` | Retrieve the current decision and constraint, cite its dated source, avoid adopting superseded advice and use bounded retrieval. |
| `query-evidence` | Preserve the implementation, retain and execute a replayable probe, show actual SQL traces reducing six queries to one, and preserve all six customer names. |

The output defaults to a new private `/tmp/skill-outcomes-<timestamp>/` directory.
An explicit `--output` must be new and outside Git worktrees to avoid inheriting
project instructions. Keep it until review is finished. It contains:

- `run.json`: CLI version, selected model, limits, source revision/working-tree
  state and candidate content hashes. `candidates/` freezes the exact skill
  content used by both arms, even if the source checkout changes during a run.
- `report.jsonl` and `summary.json`: separate per-arm scores, paired pass-rate
  difference, elapsed time, main-loop token totals and reported costs. Raw
  `usage` and `modelUsage` are
  retained per arm, including the resolved model information the CLI reports.
- `<case>/<arm>/`: synthetic project, selected skill snapshot, local origin or
  vault when applicable, request, `session.jsonl`, stderr and `grading.json`.
  Grading evidence includes the checked state, artifact contents and replay
  output. Worktree metadata remains valid because the workspace stays in place.

`--max-turns` defaults to 16, `--timeout` to 180 seconds, and `--max-budget-usd`
to $0.75 **per arm**: eight arms for the full suite, with a nominal total of $6.
The CLI may exceed a spend cap; reported estimated costs are not subscription
billing. Both runners run without automatic case retries. Outcome errors are
unscored, invalidate that pair's comparison, and cause a nonzero exit. Reported
costs from failed sessions are included; missing costs remain unknown. The
outcome exit status also fails for an enabled-arm rubric failure or no complete
comparison. A passing disabled arm is expected and does not fail the run.

## Interpretation and limits

These are small, deterministic rubrics, not a proof of complete workflow
compliance or a statistical benchmark. They check the documented observable
contract. They do not establish every reasoning step, absence of fabricated
claims elsewhere, or resistance to a model deliberately gaming the rubric.
Review retained transcripts and artifacts for consequential claims. A zero
pass-rate difference is a valid result: do not invent a benefit or tune the
baseline to fail. Repeat comparisons only when a change or an unresolved
question warrants the additional usage.

The paired runner disables hooks, auto memory, bundled skills and user/local
settings sources; it loads no external MCP servers or browser integration. It
restricts built-in tools to local reading, editing, shell and Skill use, with
explicit command approvals and no permission bypass. This measures a direct
single-session workflow; `managed-audit` is deliberately tested with delegation
unavailable, not with fabricated specialists. Some reserved built-in skills can still appear in the CLI listing; the runner
records the loaded skills/plugins and checks that the selected skill is visible
only in the enabled arm. CLI/system policy and any remaining client context
can still affect results. The fixture directory is
not an operating-system sandbox: run only trusted skills and review the command
in `request.json`. Use disposable credentials and an OS sandbox when evaluating
untrusted content.

Outcome artifacts include full synthetic session output, unlike trigger
reports. Keep them private and inspect them before sharing. Hooks are disabled
and the configured vault/cache are synthetic, so the runner does not intentionally
read or archive real vault notes. It does not modify global skill installation,
personal settings or credentials. Delete only the run directory you created
when its evidence is no longer needed.
