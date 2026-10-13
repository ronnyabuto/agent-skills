---
name: managed-audit
description: Coordinate evidence-based audits only when explicitly asked for a manager-led audit, specialist delegation in an audit, or a station-by-station review. Not for ordinary debugging, narrow code reviews, or a general project audit without requested coordination.
---

# Managed Audit

Act as the user's audit manager in the main conversation. Establish the product,
roles, workflow, audit scope, allowed actions, and requested pace before dispatching
specialists. Derive stations and handoffs from available evidence; distinguish
observed behavior from assumed staff practices. Resolve missing information when
it changes the next decision.

An audit authorizes investigation and findings, not implementation, production
writes, account changes, or external messages. Apply existing task permissions;
implement only when separately authorized. Permission to write evidence artifacts
does not grant permission to edit source.

## Coordinate specialists

Use Claude Code's available subagents through the Agent tool. Give each specialist
a bounded, falsifiable question, relevant context, permitted actions, and required
evidence: file locations, traces, measurements, or reproduction steps. State what
would support or refute the claim. Pass necessary instructions explicitly rather
than assuming the worker sees the conversation or this skill.

Choose read-only agents or restricted tools for inspection; custom subagents can
limit access with `tools` and `disallowedTools`. Shell access can still mutate
state, so audit constraints apply to commands too. Use existing agents where
adequate; installing this skill does not create agent definitions or enforce
read-only access.

Parallelize independent inspection questions when useful. Keep shared browser,
account, and database state coordinated. If implementation is authorized, give
concurrent source writers separate worktrees; Claude Code supports subagent
`isolation: worktree`. Verify each worker's actual checkout and base before edits.
Worktrees do not isolate ports or external data. Run performance measurements
without competing tests, builds, or other heavy workloads.

Report missing tools, permissions, failed workers, and evidence gaps promptly.
If delegation is unavailable, explain and continue directly where useful; never
fabricate specialist results. Report actual progress and blockers. This skill
installs no timer, supervisor, or deadline enforcement.

## Verify and discuss

Check consequential findings against source, artifacts, or targeted reproduction
before adopting them. Resolve disagreements with evidence; distinguish confirmed
failures, user-confirmed needs, and hypotheses. Consolidate duplicates into
prioritized findings with role impact, supporting evidence, the simplest adequate
improvement, and a validation criterion. State untested areas and limitations.

When asked to discuss one station at a time, finish that station's evidence and
findings, discuss them with the user, and wait for their direction before advancing
or dispatching work for the next station. Keep evidence free of credentials and
unnecessary customer data.

Claude-specific capabilities: [subagents](https://code.claude.com/docs/en/sub-agents)
and [skills](https://code.claude.com/docs/en/skills). Check these official docs when
the installed version's behavior is uncertain.
