---
name: no-ai-tells
description: Review changed code for redundant comments, generic scaffolding, and inconsistent naming when asked to polish readability or remove AI-style boilerplate.
---

# Readability Review

Review the requested files or current diff. These are readability heuristics, not evidence of authorship. Do not expand a small polish request into a whole-repository rewrite.

- Remove comments that merely restate obvious code or narrate obsolete changes.
- Keep explanations of non-obvious constraints, API contracts, invariants, live workarounds, license notices, documentation comments and tracked TODOs.
- Match local naming and formatting conventions. Rename only when the meaning becomes clearer; conventional names such as result or item are not inherently bad.
- Remove unfinished scaffolding only when it is unintended. Do not fabricate implementation to hide an intentional stub.
- Examine unnecessary indirection or duplication in context. Extract only when shared semantics are stable and maintenance benefits justify it; repetition alone is not a defect.
- Preserve boundary validation, error recovery and test isolation unless evidence establishes that they are redundant. Coverage and completeness are not suspicious by themselves.

Follow project and user requirements. Use targeted verification for behavior changes; ordinary comment edits need only checks proportionate to their actual effects. Summarize meaningful changes and any material uncertainty.
