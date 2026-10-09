---
name: code-structure
description: Decide module placement or extract duplicated operational logic when a change raises a concrete code ownership or abstraction question.
---

# Code Structure

Fit the requested change into the project's existing architecture. Read the owning code and callers before choosing a location. Do not introduce an actions/service-layer design into a project that uses different boundaries.

For architectural choices or unclear root causes, use `system-reasoning` to
establish requirements and evidence before settling implementation placement.

- Extend the module that owns the behavior when cohesion stays clear. Create a module when project conventions, a distinct concern, complexity or reuse justify it.
- Build the requested behavior and the validation/error handling it actually requires. Avoid speculative configurability and unrelated refactors.
- Extract repeated mechanics when the shared behavior is stable or duplicated fixes are costly. Two or three copies prompt examination, not an automatic extraction threshold. Similar-looking blocks with different policy may belong separately.
- Where orchestration and shared operations are distinct, keep business policy at its established owner and expose clear inputs, results and failure behavior from reusable operations.
- Persistence may legitimately belong in repositories or services. A single-implementation interface may serve a real boundary or test seam; judge its purpose rather than its count.
- Prefer a small coherent abstraction over a universal helper with many flags. Migrate callers incrementally and verify the affected flows.

Explain a non-obvious placement decision when it matters to review. User scope and local architectural rules override generic preferences.
