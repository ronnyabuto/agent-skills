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
fixtures, grading, reports, failed sessions and unknown costs. Each grader
check has a near-miss test: a reference answer passes, and a plausible
answer missing only that check's behavior fails only that check. They make no
model calls and do not claim that Claude follows the skills.

## Trigger evaluations

`*.json` contains 20 scenarios across 4 skills. The first expectation's
`Invokes` or `Does not invoke` prefix determines the score; behavioral-only
cases are skipped. Subsequent expectations remain useful for transcript review.

```bash
bash evals/build_fixture.sh /tmp/skill-evals
python3 evals/run_trigger_evals.py /tmp/skill-evals sonnet system-design --max-budget-usd 0.50
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

`--runs N` repeats every selected case as N separate fresh pairs, in rounds, with arm
order alternating between rounds. `summary.json` adds `per_case` pass counts for each arm.
One run per arm cannot separate a tie from noise; use at least three before removing or
keeping a skill on the result. `--resume` keeps the run's recorded `--runs`.

For a reproducible Opus 5.5 comparison, select the exact model and effort:

```bash
python3 evals/run_outcome_evals.py --model claude-opus-5-5 --effort medium --case design-sizing
```

Both runners accept optional `--effort low|medium|high|xhigh|max`. When supplied,
the runner passes `--effort` and sets `CLAUDE_CODE_EFFORT_LEVEL` in the child
environment so an inherited effort variable cannot override the requested level.
Reports record `requested_effort`; it is null when omitted and existing client
selection remains unchanged. The paired runner records it in `run.json` and the
trigger runner in case/summary records. This is a requested setting, not proof
of the server's effective effort: check model support and any managed cap.
The existing default model remains `sonnet`; `--model` selects the paired model,
and the trigger runner takes the model as its positional argument. Compare both
arms at the same explicit model and effort. Live commands consume model usage.

Omit `--case` for every case whose skill this collection ships; repeat it to select
several. `audit-scope` and `routine-control` stay in the shared contracts for the
Codex collection's `managed-audit` and `current-docs`. Each case runs
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
| `audit-scope` (Codex only) | Leave source unchanged, identify the actual validation failure with a location and reproduction, and disclose unavailable delegation. |
| `memory-recall` | Retrieve the current decision and constraint, cite its dated source, avoid adopting superseded advice and use bounded retrieval. |
| `query-evidence` | Preserve the implementation, retain and execute a replayable probe, show actual SQL traces reducing six queries to one, and preserve all six customer names. |
| `data-rehearsal` | Use the approved local job; expose a normalization collision hidden by sanitization; preserve the candidate and workflow; report failed readiness without attempting export or deployment. |
| `routine-control` (Codex only) | Correct simple arithmetic without invoking the unrelated current-docs skill. |
| `design-sizing` | Leave source unchanged; neither list nor recommend infrastructure (broker, cache, cluster, shard, separate service) that about 2,000 emails a day doesn't need; state a peak or burst rate that is plausible (0.001–5/s after unit conversion, so neither an average nor the relay's given 30/s counts); guard retries against duplicate sends; time out external calls; state a rollback path. |
| `stale-main` | Held out for `new-feature`: on a checkout whose main is behind origin, fix the bug on a task branch that contains the fetched origin/main, doesn't track main, and leaves local main where it was. |
| `tracking-design` | Held out for `system-design`: the `design-sizing` rubric applied to keeping shipment statuses current from a carrier API (20 requests/s limit, webhooks available). |

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
- `<case>/<arm>/` (and `<arm>-<n>/` for later runs): synthetic project, selected skill snapshot, local origin or
  vault when applicable, request, `session.jsonl`, stderr and `grading.json`.
  Grading evidence includes the checked state, artifact contents and replay
  output. Worktree metadata remains valid because the workspace stays in place.

`--max-turns` defaults to 16, `--timeout` to 180 seconds, and `--max-budget-usd`
to $0.75 **per arm**: fourteen arms for the full suite, with a nominal total of $10.50.
The CLI may exceed a spend cap; reported estimated costs are not subscription
billing. Both runners run without automatic case retries; Claude Code itself
retries transient 429/529 responses with backoff. Outcome errors are
unscored, invalidate that pair's comparison, and cause a nonzero exit. Reported
costs from failed sessions are included; missing costs remain unknown. The
outcome exit status also fails for an enabled-arm rubric failure or no complete
comparison. A passing disabled arm is expected and does not fail the run.

## Usage and rate limits

A session that fails on a plan usage limit, spend limit or exhausted rate-limit
retries is recorded as `limit_reached` with its `limit_evidence` (an
`api_error_status` of 429, the CLI's limit message, or a final `api_retry` event
with `error: "rate_limit"`). It is unscored, like other errors. Both runners
then stop instead of paying for sessions that would fail the same way, and exit
with status 75.

Continue a paired run after the limit resets:

```bash
python3 evals/run_outcome_evals.py --resume /tmp/skill-outcomes-<timestamp>
```

Resume runs only arms with no recorded result or a `limit_reached` result. It
reuses the recorded model, effort, limits and frozen candidates, and refuses to
continue when the Claude Code version, harness, case definitions or a frozen
candidate changed, or when other run flags are passed. A limited arm's directory
is kept as `<arm>.limited-<n>`. `report.jsonl` gains a `resume` record and a new
summary; `summary.json` describes the latest result for every arm, with
`unfinished_arms` counting any still missing. The trigger runner stops at a
limit but has no resume; rerun the remaining skills afterwards.

## Interpretation and limits

Both arms suppress personal/project standing instructions. This runner tests the
selected skill, not a global communication or tool-use policy. A policy comparison
must deliberately control its injection in otherwise equivalent sessions; changing
your personal CLAUDE.md does not make it part of these paired cases.

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
restricts built-in tools to local reading, editing, shell and Skill use, without a permission bypass. Shell commands are approved
without prompting: command-prefix rules denied ordinary loops, pipes and heredocs
in both arms and scored that noise as model failures. Some reserved built-in skills can still appear in the CLI listing; the runner
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
deliverables and hidden check names.
It is shared with the Codex collection; `outcome_contracts.claude.json` holds
cases only this collection runs: `design-sizing`, and the held-out `stale-main` and
`tracking-design`. The runner merges both,
rejects duplicate case names, and saves and hashes the merged definitions.
The sibling check compares only the shared file. Only the request and deliverable reach the
agent. No prompt tells it to fetch origin, disclose missing delegation, reject
superseded notes, or use bounded reads. File names and the query probe JSON
interface remain explicit so deterministic graders can replay the evidence; this
is still a constrained artifact-delivery evaluation, not unconstrained chat.
The request does not give expected counts or customer names.

`design-sizing` states the traffic in the fixture README, not the request, and the
`components.json` format names only what to list, not how to size it. Heavy
infrastructure fails the case whether it is listed or recommended in the prose;
sentences that rule it out or defer it behind a trigger are allowed. These are
deterministic text checks, not judgments of design quality: review the design
before concluding that a sizing decision was justified.

The peak, timeout and rollback checks were added after an Opus 5.5 baseline
sized the design correctly but omitted them; the guidance was trimmed to those
gaps. On 2026-11-19 (Opus 5.5, medium effort) three baselines failed (no
timeout on external calls 3/3, no rollback 2/3, no derived peak 1/3) and both
trimmed-skill arms passed, at similar cost per session. Two pairs is a small
sample. Each grader fix made after a run came from a false flag found by
reading the artifact; the excerpts are retained as regression tests.

On 2026-11-20 (Opus 5.5, medium effort, three paired runs per case, whole shell
commands approved; artifacts read before scoring) the results were:

| Case | Skill | Without | Reading of the artifacts |
|---|---|---|---|
| `assigned-worktree`, `stale-main` (held out) | 6/6 | 0/6 | Baselines never fetched or branched from a fresh origin/main. |
| `tracking-design` (held out) | 3/3 | 0/3 | No baseline design had a timeout or a rollback. |
| `design-sizing` | 1/3 | 1/3 | Baselines now include timeouts and rollback; the peak check misses wording such as "busiest times" in both arms. |
| `data-rehearsal`, `query-evidence` | 6/6 | 6/6 | Tie. `data-rehearsal` failed without the skill on 2026-11-12, when command-prefix rules still blocked ordinary shell use. |
| `memory-recall` | 0/3 | 0/3 | Both arms recalled the decision, date and source; both read the whole six-line note, failing only the bounded-retrieval check. Without SKILL.md the baseline used the vault's helper scripts. |

Three disabled `memory-recall` arms were first voided because `cat` named the deleted
SKILL.md; the runner now flags only a SKILL.md path that exists, such as the
run's frozen `candidates/` copy, and they were regraded from saved transcripts.

In the Codex collection, `routine-control` asks for a standard-library-free arithmetic correction with
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
