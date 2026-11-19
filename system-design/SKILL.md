---
name: system-design
description: Design or re-architect a service, data flow or integration for its expected load before building it. Use when asked to design, architect or plan how a system or feature should work, or whether it will cope at a given scale. Not for explaining concepts in general or for small code fixes.
---

# System Design

Size the design from written requirements and a load estimate, not from a
default architecture. Adding a component the load doesn't need is a defect:
every queue, cache, replica, shard or separate service costs operations,
failure modes and money.

1. **Scope.** Establish the features in scope, who uses them, current and
   expected volume, latency and availability needs, data retention, and the
   existing stack and services that can be reused. Read the project and its
   docs first. Ask only when an answer would change the design; otherwise
   state the assumption and continue.
2. **Estimate.** Write each assumption with units, then derive average and
   peak rates (per second), storage over the retention period and bandwidth
   where relevant. Round freely; show the arithmetic. Compare peak load with
   what the existing components handle, using measurements or cited limits
   rather than remembered benchmarks. Include limits imposed by third-party
   APIs.
3. **Design the simplest thing that fits.** Start from the existing stack.
   For each component you add, name the requirement or estimate that needs
   it. For each one you leave out, state the measurable trigger that would
   justify it later (for example, sustained queue depth, p95 latency, or
   writes per second). If the user is collaborating, agree the outline before
   detailing it.
4. **Go deep only where risk is.** Detail the one or two components most
   likely to fail or to limit growth: their data model, API or contract, and
   consistency needs.
5. **Failure and operations.** For each external call, cover timeouts,
   retries with backoff and jitter, and idempotency so a retry cannot repeat
   a side effect. Then cover what happens when a dependency is down, what to
   monitor and alert on, and how to roll out and roll back.
6. **Next scale step.** Say what breaks first at about 10× the estimated peak
   and what would change then. Don't build that now.

## Deliverable

Requirements and assumptions; the estimate; the design with a justification
for each added component; failure handling; monitoring and rollout; the 10×
bottleneck; and open questions. Use a diagram only when it carries
structure that the text doesn't.

A design is a proposal. Implement it only when that is part of the request.
