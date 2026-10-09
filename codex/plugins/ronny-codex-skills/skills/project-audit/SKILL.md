---
name: project-audit
description: Assess whole-project correctness, security, architecture, dependencies, tests, and operations; report prioritized findings when a codebase health audit is requested.
---

# Project Audit

Audit the requested project scope and report actionable findings. A request to review one diff does not require a whole-project audit. Follow the user's scope and existing authorization; an audit does not authorize fixes or deployments.

Orient using manifests, entry points, project instructions and the relevant architecture. Record the revision and working-tree state. Prioritize behavior with the greatest consequence: authentication, ownership, writes, payments, concurrency and failure recovery.

Investigate these concerns as relevant to the actual product:

- Correctness: trace concrete inputs and states to observable failures.
- Security: trust boundaries, access checks, sensitive data, injection, supply chain and fail-open handling. Use current applicable primary standards; do not imply that a checklist establishes complete security coverage.
- Architecture: changes that must be repeated across callers, tangled boundaries and abstractions that obscure real behavior. Evaluate against this project's architecture.
- Dependencies: installed versions, known advisories, lockfiles and third-party install/CI execution. Run available ecosystem audit tooling; report unavailable tools or advisory access.
- Tests: run relevant permitted checks; distinguish passing checks from untested behavior. Avoid executing live production writes or tests with unknown external side effects.
- Operations: configuration, error handling, useful logging, migration and recovery paths.

For each finding give severity, file and line, evidence, a concrete failure scenario and a fix direction. Separate confirmed failures from hypotheses needing verification. Report coverage and checks actually performed, including failed or skipped checks. Do not manufacture findings or pad the report with style preferences. Select the few fixes with greatest practical impact.
