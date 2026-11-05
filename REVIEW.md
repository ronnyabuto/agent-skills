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
