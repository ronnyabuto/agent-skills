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

`*.json` contains 51 scenarios across 12 skills. The first expectation's
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

Omit `--case` for all six cases; repeat it to select several. Each case runs
sequentially in two fresh sessions with identical synthetic starting state and
prompt. The selected skill is frozen once under `candidates/`, copied to project scope
in both workspaces and
set to `on` or `off` through session-only `skillOverrides`. The disabled arm also
omits `SKILL.md`; its helpers and references remain available. `candidate_sha256`
identifies the frozen skill, and `available_sha256` the actual per-arm directory.
The runner rejects disabled entrypoint reads/invocations and unexpected visible
skills. It hides this collection's other skills, not just those with paired cases.
Case order alternates which arm runs first.

Both arms use session-only `managed-only` instruction loading and
`claudeMdExcludes` for user/project CLAUDE.md, AGENTS.md and rules. These controls
are separate from `--setting-sources`. Managed instructions/policy can still
apply; these settings are not a security sandbox. The runner keeps normal auth:
`--bare` would change authentication and `--safe-mode` would disable the candidate
along with other customizations. No live verification of these loading controls
is claimed by the offline stand-in tests.

| Case | Observable checks |
|---|---|
| `assigned-worktree` | Keep the assigned branch/worktree, fetch the local origin, retain the current base, correct calendar results and leave the main checkout untouched. |
| `audit-scope` | Leave source unchanged, identify the actual validation failure with a location and reproduction, and disclose unavailable delegation. |
| `memory-recall` | Retrieve the current decision and constraint, cite its dated source, avoid adopting superseded advice and use bounded retrieval. |
| `query-evidence` | Preserve the implementation, retain and execute a replayable probe, show actual SQL traces reducing six queries to one, and preserve all six customer names. |
| `data-rehearsal` | Use the approved local job; expose a normalization collision hidden by sanitization; preserve the candidate and workflow; report failed readiness without attempting export or deployment. |
| `routine-control` | Correct simple arithmetic without invoking the unrelated current-docs skill. |

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
to $0.75 **per arm**: ten arms for the full suite, with a nominal total of $7.50.
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

## Natural requests and output contracts

`outcome_contracts.json` separates natural user requests from serialization-only
deliverables and hidden check names. Only the request and deliverable reach the
agent. No prompt tells it to fetch origin, disclose missing delegation, reject
superseded notes, or use bounded reads. File names and the query probe JSON
interface remain explicit so deterministic graders can replay the evidence; this
is still a constrained artifact-delivery evaluation, not unconstrained chat.
The request does not give expected counts or customer names.

`routine-control` asks for a standard-library-free arithmetic correction with
`current-docs` available. It checks correct results and absence of unrelated
skill use. Both arms should pass; it detects unnecessary activation.

Each summary retains enabled-minus-disabled per-pair token, elapsed-time,
native turn deltas, alongside outcome scores. Unknown metrics
stay unknown; error/skipped pairs are excluded. Native turn definitions and
usage accounting differ by client, so compare deltas within a client/model,
not absolute Claude and Codex turn counts. A single run is not a latency
benchmark. Saved contracts and their hash identify the exact prompt definitions.

When both source checkouts are available, run:

```bash
python3 evals/check_sibling_contracts.py /path/to/other-checkout
```

This optional check compares shared outcome definitions and four intentionally
platform-neutral skills plus the shared data-workflow reference. Update both
reviewed copies together; do not generate
one client package from the other. Hook/transcript formats, memory namespaces,
recorders, installers, worktree environments and runtime adapters intentionally
remain separate. No sibling checkout is needed for installation or ordinary
offline tests.

## Data workflow cases

`data-rehearsal` exercises a disposable in-memory SQLite migration through a
project runbook and bounded job output. The grader replays trusted fixture
commands and compares recorded outcomes and protected file hashes. Offline
checks verify the passing sanitized subset, failing legacy shape, denied
export/deploy attempts and incorrect readiness reports. They test the fixture
and grader, not agent compliance, production isolation, sanitizer safety or
production database compatibility. Job logs are observable fixture state, not
a tamper-proof audit trail; inspect transcripts for shortcuts and other actions.

[Data workflow review scenarios](data-workflow-scenarios.json) complement the
paired case with confidentiality, authority and proportionality decisions.
These are manual outcome rubrics, not keyword scores or input to the paired
runner. In a separately authorized live evaluation, give a fresh session only
the request and synthetic project context; review actions and outcomes against
the rubric, including the failure conditions. Mark unexecuted cases untested.
No live results for these new cases are claimed by their offline checks.
