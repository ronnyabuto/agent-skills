#!/usr/bin/env python3
"""Validate this local package's supported manifest and skill subset."""
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "ronny-codex-skills"
RECORDER_SHA = "d246b499991d495bf2f972f852d2dae0851b5bff2b5a64347f610242808ae8eb"


def validate():
    portable = json.loads((PLUGIN / "plugin.json").read_text())
    compat = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())
    assert portable["name"] == compat["name"] == "ronny-codex-skills"
    assert portable["version"] == compat["version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", portable["version"])
    assert compat["skills"] == "./skills/"
    assert portable["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
    assert marketplace["name"] == "ronny-local"
    entry = marketplace["plugins"][0]
    assert entry["name"] == portable["name"]
    assert entry["source"] == {"source": "local", "path": "./plugins/ronny-codex-skills"}
    assert entry["policy"]["installation"] == "AVAILABLE"
    names = []
    for skill in sorted((PLUGIN / "skills").iterdir()):
        text = (skill / "SKILL.md").read_text()
        assert text.startswith("---\n"), skill
        frontmatter = text.split("---\n", 2)[1]
        name = re.search(r"^name: ([a-z0-9-]+)$", frontmatter, re.M).group(1)
        description = re.search(r"^description: (.+)$", frontmatter, re.M).group(1)
        assert name == skill.name and len(name) <= 64
        assert "--" not in name and not name.startswith("-") and not name.endswith("-")
        assert 1 <= len(description) <= 1024
        assert len(text.split()) < 500, (name, "entrypoint too long")
        names.append(name)
    assert set(names) == {"code-structure", "current-docs", "evidence-driven-testing", "managed-audit", "new-feature", "no-ai-tells", "no-ai-tells-audit", "project-audit", "understand-before-changing", "ux-speed-audit", "vault-memory", "system-reasoning"}
    assert len(names) == len(set(names))
    for file in ROOT.rglob("*.md"):
        for reference in re.findall(r"\]\(([^)]+)\)", file.read_text()):
            if "://" in reference or reference.startswith("#"):
                continue
            target = (file.parent / reference.split("#")[0]).resolve()
            assert target.is_relative_to(ROOT) and target.is_file(), (file, reference)
    for file in ROOT.rglob("*.py"):
        ast.parse(file.read_text(), filename=str(file))
    for file in ROOT.rglob("*.json"):
        json.loads(file.read_text())
    recorder = PLUGIN / "skills/evidence-driven-testing/scripts/evidence.py"
    assert hashlib.sha256(recorder.read_bytes()).hexdigest() == RECORDER_SHA
    hooks_path = PLUGIN / "skills/vault-memory/references/hooks.json"
    assert "hooks" not in compat
    hooks = json.loads(hooks_path.read_text())["hooks"]
    assert set(hooks) == {"SessionStart", "PreCompact", "SessionEnd"}
    for event, entries in hooks.items():
        handler = entries[0]["hooks"][0]
        assert handler["type"] == "command"
        assert handler["command"] == 'python3 "<installed-marketplace>/plugins/ronny-codex-skills/skills/vault-memory/scripts/hooks.py"'
        assert handler["timeout"] <= (3 if event == "SessionEnd" else 30)
    print(f"Validated portable/Codex manifests, marketplace, {len(names)} skills, references, Python syntax, and recorder provenance.")


if __name__ == "__main__":
    validate()
