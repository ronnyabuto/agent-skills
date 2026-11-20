# Setup check

If you're an agent working in this repo, check once, with a single command,
whether these skills are installed: does `~/.claude/skills/vault-memory`
exist? If it does — pointing at this checkout, another clone, or a worktree
of this repo — they're installed; say nothing about setup. If it's missing,
tell the user the skills aren't installed and offer to run `./install.sh`. It
links the skills and adds vault-memory's hooks to `~/.claude/settings.json`,
so:

- Ask before running it — it changes the user's global configuration.
- Ask where the vault should live (default `~/agent-vault`; an existing
  Obsidian vault is fine) and pass it as `./install.sh --vault <path>`.
- Show the output, including any warning, and say that a new session (or
  `/hooks`) is needed for the hooks to load.

Skip this when the skills are already linked here, or when the user is
clearly just editing the skills themselves.

# Working in this collection

Keep the skills on demand; don't add procedures to standing instructions. Read a
skill and the files that reference it (other skills, evals, docs) before changing
its behavior. Keep platform-specific hooks and capture helpers with their owners.

A skill earns its place by changing outcomes against a no-skill baseline, not by
restating good practice. Propose a new skill or section only after a baseline run
has shown the failure it fixes, and write the smallest text that fixes it. Measure
with the paired outcome runner (paid; run only when asked) at `--runs 3` or more,
including a held-out case the skill was not tuned on, and remove guidance that
shows no effect. Re-run the suite when the default model changes.

Offline verification:

```bash
python3 -m unittest discover -s evals -p 'test_*.py' -v
python3 vault-memory/scripts/test_vault.py
```

Do not run paid model evaluations or install global hooks as an offline check.
