# Claude Code compatibility

Reviewed on 2026-10-29 with Claude Code **2.1.300**, Node **24.14.1** and
Python **3.14.4**. The offline checks exercise the helper scripts and evaluation
harness; live outcome reports record their own CLI version, candidate hashes,
resolved model usage and results. A successful harness check alone does not
establish model compliance. No older Claude Code minimum is asserted for the
Markdown skills; the paired outcome runner requires **2.1.300 or later** for
its tested session controls.

## Portable format and Claude extensions

The skills use the Agent Skills directory format: `SKILL.md` frontmatter,
instructions and optional references/scripts. Anthropic's October 22, 2026
[announcement](https://www.anthropic.com/news/donating-agent-skills-to-the-agentic-ai-foundation)
that the standard is moving to the Agentic AI Foundation does not require a
format migration. Runtime behavior remains platform-specific: Claude's
`${CLAUDE_SKILL_DIR}` expansion, settings hooks, Agent tool and worktree support
are not made portable by sharing the Markdown files.

The [skills reference](https://code.claude.com/docs/en/skills) documents optional
Claude frontmatter such as invocation control, tool permissions and forked
execution. This collection keeps ordinary coding skills automatically
discoverable. Optional fields are added only when the workflow needs them.
For example, `context: fork` would remove a managed audit from the main
conversation where its coordination belongs. `allowed-tools` pre-approves
permissions; it does not establish a read-only sandbox.

Vault archiving stays in settings-level hooks. Skill-scoped hooks register only
when the skill loads and cannot provide session-wide archiving on their own.
The installer still links folders and preserves other settings; this update
does not require rerunning it or changing global configuration.

## Cooperating with bundled workflows

| Existing workflow | What this collection adds |
|---|---|
| `/run`, `/verify`, project launch skills | `evidence-driven-testing` reuses their launch recipes and completed checks, then retains assertions, measurements or captures needed to substantiate the claim. |
| `/code-review` | `project-audit` covers the requested project health scope; `managed-audit` coordinates specialists only when explicitly requested. Do not repeat a review that already answers the question. |
| `/simplify` | `no-ai-tells` applies local readability conventions while preserving meaningful constraints and useful tests. |
| Built-in auto memory | `vault-memory` provides an explicit local Markdown archive and keyword search across sessions and decision notes. It requires its own hooks and privacy configuration. |

See the [bundled skills documentation](https://code.claude.com/docs/en/skills#bundled-skills)
for availability on the installed client. Bundled prompts evolve with Claude
Code; a similar name or capability alone is not a reason to remove a local
skill. Evaluate its incremental value with fresh enabled/disabled sessions.

## Optional diagnostics and visibility

In an interactive Claude Code session:

- `/skill-doctor` reports skill listing cost and observed usage. It needs
  2.1.252 or later and is unavailable when feature-flag fetching is skipped.
- `/doctor prompt-audit` can propose changes to outdated or conflicting
  instructions (2.1.283 or later). Review the proposed changes before applying.
- `/skills` lets you change visibility through `skillOverrides` without editing
  this checkout. `on` lists a skill normally, `name-only` omits its description,
  `user-invocable-only` keeps it manual, and `off` hides it. Overrides do not
  control plugin-provided skills; manage those through `/plugin`.

These are optional personal choices. Making a skill manual can prevent natural
language requests from automatically selecting it; hiding its description also
changes discovery. The eval runner uses session-only overrides and never writes
these choices into personal settings.

When checking a newer client, read the official
[changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
and rerun the affected checks. As of this review it lists 2.1.312, including a
fix for discovering per-directory skills after changing directories. Updating
Claude itself is separate from installing or editing this collection.
