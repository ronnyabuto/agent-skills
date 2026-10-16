# Choose tests that protect behavior

Verification and permanent test code are separate decisions. Start with the
requested behavior, affected boundary, existing coverage, and plausible failure.
Run the smallest relevant existing checks first. Keep a new automated test when
it protects a meaningful contract, recurring regression, or consequential risk
that existing coverage misses. For a reversible, low-impact change, a focused
probe or manual check can suffice; scratch checks need not become repository
files. Follow required project checks without inventing coverage quotas.

Before retaining a test, be able to name the user-visible failure or invariant
it detects. Expected results must come from the requirement, a known incident,
or an independent oracle. Copying the implementation's answer into the test,
asserting that a mock returns its configured value, or snapshotting incidental
structure provides little protection. Do not weaken an assertion or replace an
expected value merely to make a failure green.

## Represent real use, with reproducible outcomes

Use representative, sanitized inputs and state transitions through the public
interface involved: browser, CLI, API, file format, or domain boundary. For a
UI flow, act through visible controls, wait for observable state rather than
arbitrary sleeps, and check the resulting saved data or output when relevant.
A success toast alone does not establish that an operation succeeded.

Choose failure and recovery scenarios from actual usage or the changed risk:
expired sessions, interrupted requests, retries, duplicate submissions,
permissions, locale, existing data, or simultaneous users. Do not mechanically
add all of them to every change. A normal successful journey is useful too;
happy-path-only coverage is the problem, not successful outcomes themselves.

Use a few integration/journey checks where components interact and focused
unit tests for rules whose combinations are cheaper and clearer to exercise
directly. Realism does not require every test to drive a browser or contact
production. Use isolated state and controlled substitutes at unavailable,
costly, or destructive external boundaries; retain contract/integration checks
for assumptions those substitutes cannot verify.

Dynamic testing can vary inputs, operation order, retries, or concurrency while
asserting a stable invariant. Record the seed, input, and relevant schedule or
trace so a failure can be reproduced. Property-based or stateful tests help
when there is a meaningful invariant; unseeded randomness and timing guesses
add noise. For a bug fix, show that the check detects the original fault when
feasible, then passes after correction. A passing generated test alone is weak
evidence that it could detect a defect.

## Maintain coverage by behavior, not age

Keep old tests that still protect supported behavior or a past incident.
Replace a test when its contract changed or another check demonstrably covers
the same meaningful failure with less brittleness or cost. Before deleting,
map its scenario and assertions to the replacement; preserve distinctive edge
cases, recovery paths, and invariants. A new broad journey does not necessarily
replace focused boundary cases.

Remove exact duplication and tests for retired behavior with a stated reason.
Investigate flaky tests: fix their isolation, synchronization, or environment;
if temporarily quarantined, retain a tracked owner and recovery condition.
Do not delete tests because they are old, generated, failing, or inconvenient.
Report obsolete expectations separately from actual regressions.

## Control agent effort

Keep one short standing preference in project instructions: use proportionate
checks, retain tests for meaningful uncovered behavior, and stop when the
requested work is verified. Avoid stacking multiple mandatory review loops or
carrying model-specific verification nudges forward without re-evaluation.
Choose model and effort using task outcomes, elapsed time, tokens, and rework.
Higher effort can add review rounds; lower effort can skip needed verification.

For skill evals, invocation is only one signal. Review outcomes and relevant
transcripts against realistic tasks, including cases where a skill should not
run. Keep failed sessions and missing usage visible. Repeat trials when
non-determinism could change the decision; do not rerun until a preferred result
appears. A synthetic CLI stand-in checks the harness, not the model's behavior.

## Sources

Checked 2026-10-16. These motivate the policy; they do not impose a fixed model
or effort setting on every task:

- [Claude Code verification and task scope](https://code.claude.com/docs/en/best-practices)
- [Fable 5.1: scope and committed tests](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1#keep-changes-and-tests-to-what-the-task-asks-for)
- [Sonnet 5.5: scope, effort, and verification](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5)
- [Model-specific verification guidance](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- [Agent eval outcomes and regression suites](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
