---
name: system-design
description: Design or re-architect a service, data flow or integration for its expected load before building it. Use when asked to design, architect or plan how a system or feature should work, or whether it will cope at a given scale. Not for explaining concepts in general or for small code fixes.
---

# System Design

Size the design from the expected load, starting from the existing stack.

- **Derive the peak.** Write assumptions with units and show the arithmetic
  from daily volume to a peak rate per second, including bursts. Compare it
  with known limits (upstream quotas, relay or API caps, measured capacity).
- **Justify additions, and give deferrals a trigger.** Each added component
  names the estimate that needs it. Each component left out gets the
  measurable signal that would justify it later, such as backlog age, p95
  latency or sustained writes per second.
- **Bound every external call.** Give each network, SMTP or database call a
  timeout. Retry only transient errors, with backoff and jitter, and make a
  retried side effect unable to repeat.
- **Say how to undo it.** Include a staged rollout and the rollback step,
  noting anything that cannot be reversed.
- **State the 10× bottleneck** in a line or two; don't build for it.

Keep the write-up proportional: a small load needs a short design. A design is
a proposal; implement it only when the request includes that.
