---
name: project-audit
description: Use when asked to audit, review, or assess the health of a whole project/codebase — architecture, security, dependencies, test coverage, correctness risk. Use when the user says "audit this project," "review the codebase," "how healthy is this repo," or wants a prioritized findings report rather than a narrow code review of one diff.
---

# Project Audit

Full-codebase health audit. Not a diff review (use `code-review` for that) — this
looks at the project as a whole and reports what's actually wrong, ranked by how
much it matters.

## Before starting

Orient first, don't assume a stack: read `package.json` / `pyproject.toml` /
`go.mod` / equivalent, the README, and skim the directory structure. Note the
stack, the entry points, and anything the README claims that you should verify
rather than trust.

## Audit sections

Work through these in order. Stop and report after each section rather than
silently rolling everything into one wall of text at the end.

1. **Architecture** — where does domain logic live vs. shared/reusable mechanics?
   Flag duplicated operational logic across features and god-object services. If
   the `code-structure` skill is loaded, apply its actions-vs-service-layer lens
   explicitly.
2. **Correctness risk** — read the actual recent commits and the hottest paths
   (auth, payments, data writes) for logic bugs, not just style issues.
3. **Security** — OWASP top 10 pass: injection, auth/session handling, secrets in
   code or env files, SSRF, insecure deserialization, missing input validation
   at trust boundaries.
4. **Dependencies** — outdated/vulnerable packages (run the ecosystem's audit
   tool: `npm audit`, `pip-audit`, `cargo audit`, etc.), unused dependencies, and
   anything pinned to a version with a known CVE.
5. **Test coverage** — what's actually tested vs. what only looks tested. Run
   the suite and report the real pass/fail, never an assumed one.
6. **Simplification/efficiency** — dead code, premature abstraction, N+1
   patterns, anything a bug fix would need to touch in three places instead of
   one.
7. **Operational readiness** — logging, error handling at boundaries,
   config/secrets management, CI status if present.

## Deliverable

A prioritized findings list — Critical / High / Medium / Low — each with:

- `file:line`
- A concrete failure scenario (inputs/state → wrong output or crash), not "this
  could be an issue"
- A one-line fix direction

Don't pad the list with stylistic nitpicks to hit a count — an empty severity
tier is a valid, honest result. End with the 3 highest-leverage fixes if the
user only has time for a few.
