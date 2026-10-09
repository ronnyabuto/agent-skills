---
name: understand-before-changing
description: Investigate existing behavior before removing code, changing risky logic, or replacing an unfamiliar workaround whose purpose is uncertain.
---

# Understand Before Changing

Preserve meaningful constraints while making the requested change. Scale investigation to risk: a small addition that follows a visible pattern needs local context, not a history excavation.

For uncertain behavior or a proposed removal, inspect callers, tests and nearby documentation. Use targeted history, issue discussion or decision notes when they can explain a surprising constraint. Do not search every source by default.

Distinguish evidence that the behavior remains necessary, evidence that it is obsolete or wrong, and absence of evidence. Unknown history is a legitimate result: do not invent the original author's reasoning. Describe consequential uncertainty in the result without mandatory labels for routine edits.

Preserve valid constraints, change demonstrably wrong behavior, and choose a conservative scoped fix when the purpose is unknown. Do not let an aesthetic cleanup remove access checks, boundary validation, compatibility workarounds or recovery behavior without assessing their effects. Verify behavior proportionally to the change. Explicit user requirements and project conventions lead.
