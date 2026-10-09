---
name: system-reasoning
description: Derive system designs and root-cause fixes from requirements, invariants, and evidence. Use for architectural tradeoffs, scaling or reliability constraints, unexplained bottlenecks, recurring or unclear bugs, concurrency failures, failures across component boundaries, or explicit first-principles/root-cause analysis. Skip routine CRUD and local bugs with an established cause.
---

# System Reasoning

Scale investigation to uncertainty and consequences. Established patterns are
appropriate when their assumptions fit; first principles do not require
reinventing standard solutions.

## Establish the problem

Define the expected outcome, system boundary, and measurable success criterion.
For a bug, identify the violated requirement or invariant. Trace relevant
callers, data flow, dependencies, state ownership, and failure boundaries.

Separate verified facts, required constraints, assumptions, and unknowns.
Include compatibility, staffing, budget, deadlines, and migration costs
alongside resource limits, latency, capacity, and consistency. Investigate
existing decisions before challenging them (`understand-before-changing`);
use scoped memory or current official docs when they answer an actual unknown.

## Root-cause debugging

Reproduce the failure with relevant inputs, state, timing, and environment.
When reproduction is unavailable, use traces or other observations and state
the limits. Do not call an untested explanation a confirmed root cause.

Locate the first divergence from expected behavior. Test plausible competing
explanations with a distinguishing probe, controlled reproduction, profiling,
or state inspection. Correlation and symptom suppression alone do not prove
causation. Explain the supported chain: trigger → faulty transition or
assumption → violated invariant → observed failure. Several conditions may
contribute; preserve uncertainty explicitly.

Correct the cause where the behavior or invariant is owned, with the smallest
sufficient change. Separate immediate containment from a durable correction
and state any remaining failure path. Verify the reproduction fails before
and passes after the fix where feasible; add a regression check at the causal
boundary and exercise relevant adjacent conditions. Report unavailable checks.

For duplicate payments, distinguish double-clicks, retries, and concurrent
workers before choosing a correction. A disabled button addresses one entry
path; inspect the required idempotency at the payment boundary.

## Design and bottlenecks

Derive capabilities before selecting technologies. Measure the workload and
relevant resources; distinguish service time, waiting, and downstream latency.
Label estimates and assumptions in any capacity or latency model.

Compare the current approach, the smallest sufficient change, and meaningful
alternatives against correctness, failure behavior, operational effort, cost,
and migration risk. For Redis proposals, investigate query cost, request
volume, freshness, and invalidation; a query or index correction may suffice.

Recommend an option with evidence, tradeoffs, validation, and the assumptions
or thresholds that would change it. Include migration/rollback considerations
where relevant. Use `code-structure` for implementation placement afterward.

Give a concise decision rationale, supported cause or design choice, correction,
verification, and unknowns. Stop when evidence supports a sufficient solution.
