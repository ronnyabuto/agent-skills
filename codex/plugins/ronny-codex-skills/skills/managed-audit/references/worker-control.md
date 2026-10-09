# Worker assignments and handoffs

Define an assignment before dispatch: question, scope, relevant role/station, necessary context, allowed tools/actions, expected evidence, acceptance criteria and budget. Set a total budget for the current station/assignment as well as each worker's allocation. Review any replacement against the remaining total; restarting does not reset the budget.

Use operating targets unless the user chooses others:

| Elapsed time | Evidence expected | Manager response |
|---|---|---|
| 15 minutes | Relevant path, first observation/reproduction, or specific blocker | Narrow drifting exploration |
| 30 minutes | Supported finding, reproduction, measurement or meaningful artifact | Continue, redirect or stop based on evidence |
| 45 minutes | Remaining work and verification status | Prepare a handoff if unlikely to finish |
| 60 minutes | Supported result or preserved partial work and handoff | End the allocation and reassess |

A commit is not a requirement for an audit. Superficial files, large prose reports or activity counts do not establish progress. A supported diagnosis or proof that an alleged defect is absent can be a successful result. A slow build, queued tool or missing access should be identified, not automatically treated as reasoning failure.

Use clocks and short bounded waits when available. Check and steer workers at observable boundaries; do not claim exact enforcement from instructions alone. If a worker repeats the same investigation without new evidence, redirect before the next time target. Adjust budgets openly for an unusually expensive observation; do not silently extend a stalled assignment.

Default to at most one replacement for a given assignment without a fresh manager assessment of the cause and remaining budget. A replacement should receive evidence and failed approaches, not just the original vague request. If no useful new approach or affordable scope exists, report the unresolved issue and ask the specific decision needed. Do not launch an endless replacement chain.

Before stopping a worker, request a concise handoff when possible. Preserve artifacts and unfinished work; distinguish a graceful stop from forceful termination. Do not discard branches, changes or evidence just because the allocation ended.

The handoff includes:

- Objective and acceptance criteria.
- Environment, worktree/branch/revision and uncommitted changes when applicable.
- Supported findings with artifact paths.
- Checks performed, outcomes and untested claims.
- Attempted approaches and why they failed.
- Blockers, remaining work and the next concrete action.

On completion, the manager verifies consequential evidence, resolves disagreements and synthesizes recommendations. Worker agreement is not independent proof. Keep reports narrow enough for the successor to act without rereading the whole investigation.
