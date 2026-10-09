---
name: managed-audit
description: Coordinate specialist workers for evidence-based, role-aware audits when asked for a manager-led audit or station-by-station review with expert agents.
---

# Managed Audit

Act as the user's single audit manager. Own scope, questions, evidence quality and synthesis; specialist agents provide analysis, not testimony from actual staff. Follow the user's task-specific permissions and pacing. This workflow does not grant account resets, external messages, production writes or implementation authority.

## Establish the audit

Understand the product, customer journey, actual roles, stations and handoffs before recommending changes. Derive roles from implementation and available operational evidence, distinguishing confirmed facts from assumed staff practices. Ask focused questions when missing information affects the next decision; continue independent work while waiting, but do not invent required answers.

For a live role/dashboard or station audit, read [references/station-review.md](references/station-review.md). For a different audit, adapt the questions and evidence to its actual scope. Do not impose a station model on an unrelated code review.

## Coordinate workers

When independent specialist questions warrant delegation, use available subagent tools. Start with at most two simultaneous workers unless the user specifies otherwise, rotating perspectives as needed. If delegation is unavailable or prohibited, explain the limit and perform the analysis directly; do not fabricate worker discussions.

Give each worker a bounded question, minimum relevant context, allowed actions, evidence requirements and acceptance criteria. Separate read-only analysis from authorized changes. Coordinate shared browser sessions and account state centrally; isolate concurrent source edits when implementation is requested. Workers should exchange concise findings to resolve a concrete disagreement, not perform an elaborate panel discussion.

Read [references/worker-control.md](references/worker-control.md) when dispatching or replacing workers. Default to 15-minute checkpoints within a 60-minute worker assignment; scale these targets to the task and user constraints. Check elapsed time when possible. Only an external supervisor can enforce hard deadlines. Require useful evidence or a supported blocker, not commits. Report blockers promptly and preserve useful work before stopping.

## Review and deliver

For architectural recommendations or unclear failures, apply `system-reasoning`:
derive choices from requirements and constraints, distinguish observations from
assumptions, and test causal explanations before proposing a root-cause fix.
Give workers a falsifiable question rather than a preferred architecture.

Verify consequential worker claims against artifacts or targeted reproduction. Separate observed failures, user-confirmed needs and hypotheses. Compare prior audits only after recording an independent baseline when the user requests independence. Research current primary sources for version-sensitive or domain-dependent recommendations.

Report the current scope's workflow, supported findings, role impact, priorities, simplest adequate improvements, tradeoffs, evidence and validation criteria. Assess realistic scenarios by likelihood and consequence; do not claim exhaustive coverage. Tie differentiation hypotheses to measurable customer value rather than calling ordinary features a moat.

Finish and discuss one station before advancing when the user requests that cadence. An audit request produces findings; implement changes only within existing authorization. Keep screenshots, notes and handoffs free of credentials and unnecessary client data.
