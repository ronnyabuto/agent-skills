---
name: system-reasoning
description: Derives system designs and bug fixes from requirements, invariants, and evidence instead of assuming a familiar pattern fits. Use for architectural tradeoffs, scaling or reliability constraints, unexplained performance bottlenecks, recurring or unclear bugs, concurrency failures, and failures across component boundaries; also when explicitly asked for first-principles reasoning or root-cause analysis. Skip routine CRUD, boilerplate, and local bugs with an already-established cause.
---

# System Reasoning

Start from what the system must accomplish and what the evidence establishes.
Use established patterns when their assumptions fit. Scale the investigation
to the uncertainty and consequences; a small bug does not need a design study.

## Establish the problem

- State the expected outcome and a measurable success criterion. For a bug,
  identify the violated requirement or invariant, not just the visible symptom.
- Bound the relevant system: callers, data flow, dependencies, state owners,
  and failure boundaries. Follow the path involved in the decision or failure.
- Separate verified facts, required constraints, assumptions, and unknowns.
  Include compatibility, budget, staffing, deadlines, and migration costs
  alongside latency, capacity, consistency, and hardware limits.
- Investigate why existing behavior exists before challenging it
  (`understand-before-changing`). Past decisions (`vault-memory`) and verified
  version-specific behavior (`current-docs`) can supply evidence. A convention
  is neither proof of necessity nor permission to remove it.

## Root-cause debugging

Reproduce the failure with the relevant inputs, state, timing, and environment.
If reproduction is unavailable, use traces or other observations and state
the limits; do not label an untested explanation as a confirmed root cause.

Trace where actual behavior first diverges from expected behavior. Form
plausible competing explanations and choose a test or probe that distinguishes
them. Use logs, controlled reproductions, profiling, or state inspection as
appropriate. A correlation or a patch that hides the symptom is insufficient
to establish causation.

Explain the supported causal chain: trigger → faulty transition or assumption
→ violated invariant → observed failure. There may be several contributing
conditions rather than one cause. Record what supports the explanation and
what remains uncertain.

Fix the cause where the relevant behavior or invariant is owned. Prefer the
smallest sufficient correction; first-principles reasoning does not justify
an unrelated rewrite. When immediate containment is necessary, distinguish it
from the durable correction and state the remaining failure path.

Verify that the reproduction fails before the fix and passes after it when
feasible. Add a regression check at the causal boundary and exercise relevant
adjacent conditions, such as retries or concurrent callers. If a before/after
check cannot be run, report that limitation rather than claiming proof.

Example: duplicate payments might result from double-clicks, request retries,
or concurrent workers. Disabling a button addresses one entry path. Determine
which path actually fails and whether the payment boundary enforces the
required idempotency before choosing the correction.

## Architecture and bottlenecks

Derive the needed capabilities from requirements before naming technologies.
For performance decisions, measure the relevant resources and workload;
separate service time, waiting, and downstream latency. Use a simple capacity
or latency model where useful, labeling estimates and their assumptions.

Compare the current approach, the smallest sufficient change, and meaningful
alternatives. Assess correctness, failure behavior, operational effort, cost,
and migration risk against the actual requirements. For example, investigate
query cost, request volume, and freshness requirements before choosing Redis;
an index or query correction may meet the same goal with less operational work.

Recommend an option with the evidence supporting it, its tradeoffs, and a
validation plan. Explain which assumption or threshold would change the
recommendation. Include migration and rollback considerations when relevant.
Use `code-structure` for implementation placement once the design is settled.

## Result

Give a concise decision rationale: the problem or invariant, evidence and
unknowns, supported cause or design choice, correction, and verification.
Use `evidence-driven-testing` when reproducible measurements or captures are
needed. Stop expanding the investigation once the evidence supports a
sufficient solution; retain uncertainty explicitly when it does not.

## Sources

- [First Principles Thinking](https://lawsofsoftwareengineering.com/laws/first-principles-thinking/): framing constraints versus assumptions.
- [NASA System Design Processes](https://www.nasa.gov/reference/4-0-system-design-processes/): requirements, decomposition, and alternative designs.
- [The USE Method](https://www.brendangregg.com/usemethod.html): utilization, saturation, and errors for resource bottlenecks.
