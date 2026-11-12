# Review — November 12, 2026

Paired outcome runs on Opus 5.5 at medium effort, one run per case unless noted.

| Skill | Enabled | Baseline | Result |
|---|---|---|---|
| vault-memory | correct recall | could not find the decision | keeps clear value |
| evidence-driven-testing (data rehearsal) | pass | failed 3 of 4, attempted unsafe steps | keeps clear value |
| evidence-driven-testing (query probe), managed-audit | pass | pass | no measured difference |
| new-feature (rewritten trigger), 3 runs | 3/3 pass | 0/3 fetched a fresh base | keeps clear value |
| understand-before-changing, code-structure, system-reasoning | not invoked | pass | removed |
| no-ai-tells | invoked, pass | pass | removed |

The four removed skills restated judgment Opus 5.5 already applies; git history
keeps them. The runner now records client-provided skills (Claude Code 2.1.322
ships `design`, `doctor`, `plugin-authoring`) instead of rejecting every arm.
One run per case is evidence, not a statistical benchmark.

# Review — November 5, 2026

I kept the data and migration guidance inside the testing skill. It uses the
project's approved workflow, checks whether sanitization removed the edge case,
and keeps rehearsal separate from deployment permission.

I fixed the Claude eval baseline leaking disabled skill instructions and the
memory hooks skipping forked sessions. Custom hook filters and existing notes
stay intact. There was no reason to rewrite the runtimes or make every skill
manual-only.

All 41 offline tests pass. Native hook delivery and model-performance gains
remain untested.

# Review — November 2, 2026

I checked the review claims against the code, history, offline tests and current
platform docs. The memory collision was real. The worktree and architecture
rules were too broad for small changes, so I narrowed them.

I kept the Node memory adapter and existing notes. New records use repository
identity; old basename notes remain available through explicit search. The
Wayland recorder now requires a protocol probe instead of trusting desktop names.

The evals use shorter requests, separate output contracts and a negative control.
All 32 offline tests pass. Live capture and model-performance gains remain
unverified; I’m not claiming either from these checks.
