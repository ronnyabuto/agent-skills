# Provenance and use

This separate Codex adaptation is based on the workflow ideas reviewed in ronnyabuto/agent-skills at b51bd621b292c347f443c7ff98407a3d974123c8 (2026-10-02 review). The original Claude skill folders, root instructions, installer and settings have not been edited.

The ten skill entry points were rewritten for focused Codex workflows. scripts/memory.py is a new Python helper, not a port of the upstream Node implementation. The optional evidence-driven-testing/scripts/evidence.py is retained unchanged from that reviewed revision. Its SHA-256 is recorded in the release file inventory.

The source collection identifies itself as a trimmed fork of michaelshimeles/skills and explicitly states that upstream material has no root license and is retained for personal use. This package does not relicense that material or claim ownership. Keep this local personal package private; obtain appropriate permission or replace retained material before redistribution. There is deliberately no invented blanket open-source license.

Primary packaging and skill guidance checked during implementation:

Version 1.2.0 adds original system-reasoning instructions based on the design
and root-cause workflow added to ronnyabuto/agent-skills in PR #3. It also adds
the Python Codex lifecycle adapter and user-level installation guidance. The
prior Codex adaptation is now maintained under this repository's codex/ folder;
the Claude and Codex entrypoints and memory implementations remain separate.

Additional primary guidance checked for this release:

- https://learn.chatgpt.com/docs/build-skills
- https://learn.chatgpt.com/docs/agent-configuration/agents-md
- https://learn.chatgpt.com/docs/hooks

Prior implementation sources:

- https://developers.openai.com/plugins/build/plugins
- https://learn.chatgpt.com/docs/developer-commands
- https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra
- https://developers.openai.com/blog/eval-skills
- https://agentskills.io/specification
