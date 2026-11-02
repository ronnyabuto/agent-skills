---
name: current-docs
description: Verify version-sensitive library, framework, SDK, or API behavior against official documentation before implementing uncertain integrations.
---

# Current Docs

Resolve the specific API uncertainty that affects the requested work. Follow explicit user choices and project requirements; do not upgrade dependencies just to match documentation.

- Identify the resolved dependency version from the lockfile or installed package. A manifest range alone is not the installed version.
- Fetch the relevant official documentation for that version. For unpinned new dependencies, use current documentation and record the chosen version.
- Verify consequential field names, limits, defaults and flags against the actual documentation text, tagged source, release notes or type definitions.
- When exact documentation is unavailable, inspect source/types for the installed version. Adjacent-version documentation is a lead, not proof of compatibility. State any unresolved assumption.
- Use the result to implement and run a targeted check. Cite the relevant source when it materially explains a decision.

Skip stable syntax and known behavior when there is no material uncertainty. Stop researching once the implementation question is answered. If offline, use available local evidence and explain any remaining uncertainty rather than inventing a current API.
