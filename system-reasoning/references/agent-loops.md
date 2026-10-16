# Recurring agent work

First measure a representative run: productive actions, unchanged polls,
retries, tokens, elapsed time, and completed outcomes. Improve the recurring
decision that actually wastes work; do not add a classifier by default.

## Admit work once

Prefer events or a background watcher when available. Otherwise poll in code
with a suitable interval and backoff. Compare identifiers, versions, hashes,
and timestamps before invoking a model. An unchanged queue needs no semantic
decision. A check inside a model prompt still pays for that prompt.

Give each item a stable identity and content version. Claim it atomically
before launching a worker; record the job/session ID and outcome. Handle an
expired claim explicitly so a crash neither loses the item nor launches two
workers. Recheck freshness before acting on an earlier classification.

## Bound execution and establish completion

Define the permitted deliverable, observable acceptance criteria, and terminal
outcomes: completed, blocked, failed, or budget exhausted. Have code check exact
conditions, such as exit codes and required artifacts. Semantic evaluation
needs the requirement and actual results, not the worker's assertion of success.

Set attempt, elapsed-time, and spending limits in the launching application.
Retry transient failures within that allowance; retry an unsuccessful task only
with a recorded reason, such as changed evidence or a corrected approach.
Preserve partial results and require an explicit decision after exhaustion.

In Claude Code, prefer `/goal` for a session completion condition and `/loop`
for interval-based checks. The goal evaluator sees conversation evidence; it
does not independently inspect files. A time/turn clause in a goal is a
model-evaluated instruction, not a hard process limit. For print-mode workers,
`--max-turns` and `--max-budget-usd` supplement a launcher timeout. The spend cap
uses an estimate and may be exceeded; reserve headroom. Check support in the
installed version before relying on these controls.

Use custom Stop hooks only when their checks add value. Respect
`stop_hook_active` and maintain a task-scoped attempt limit; built-in loop
protections are not an overall task budget. Keep these hooks opt-in to the
workflow rather than changing every session's stopping behavior.

## Add semantic routing only when it earns its cost

Compare ordinary code, a native Claude feature, and a separate classifier
against the measured workload. Include latency, maintenance, external data
handling, missed work, and correction/review effort. A returned probability is
not evidence of accuracy on this workload or authorization to execute an action.
Keep permission enforcement independent of classification.

If classification is justified, start in shadow mode on representative labeled
items, including ambiguous and adversarial inputs. Measure incorrect admissions
and missed eligible work on held-out examples. Pin the evaluated model and
question versions; route errors and uncertainty to a recoverable review queue.
Keep a bypass so the previous workflow can resume without losing pending work.

Track item/version, model/question version, decision, worker outcome, retries,
tokens, and estimated cost. Include failed and rejected work in total cost;
divide by successfully completed tasks. Distinguish subscription usage from
incremental billed spend and mark missing usage as unknown. Re-evaluate only
when the workload, routing criteria, or model changes enough to warrant it.

## Sources

Checked 2026-10-16; verify version-sensitive behavior when implementing:

- [Claude goals](https://code.claude.com/docs/en/goal)
- [Scheduling and event alternatives](https://code.claude.com/docs/en/scheduled-tasks)
- [Hooks and Stop behavior](https://code.claude.com/docs/en/hooks#stop)
- [CLI limits](https://code.claude.com/docs/en/cli-reference)
- [Usage and cost accounting](https://code.claude.com/docs/en/costs)
