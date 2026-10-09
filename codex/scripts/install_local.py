#!/usr/bin/env python3
"""Install this separate local Codex plugin; never target Claude configuration."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
NAME = "ronny-codex-skills"
MARKETPLACE = "ronny-local"
ORIGINALS = {
    "current-docs": "c10e8228a7bfec5a8d87c09844d63571ab392923405ba77d7bfe90e50760ce45",
    "project-audit": "0397dcc176bf95bccec7424c87a2a7ee3bbee0eb5830799ab91583045ff53821",
    "ux-speed-audit": "ad4ed10c0ac2f6053ae43a97ad8d21dc70008ee5b475e6e7e858d209e35d33c0",
}


def cli(*args):
    result = subprocess.run(["codex", "plugin", *args, "--json"], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"codex plugin {' '.join(args)} failed: {result.stderr.strip()}")
    # Remote catalog warnings do not invalidate a verified local result.
    return json.loads(result.stdout)


def claude_state():
    base = Path.home() / ".claude"
    state = {}
    settings = base / "settings.json"
    if settings.is_file():
        state["settings.json"] = hashlib.sha256(settings.read_bytes()).hexdigest()
    skills = base / "skills"
    if skills.exists():
        for entry in sorted(skills.iterdir()):
            state[f"skills/{entry.name}"] = {"symlink": os.readlink(entry) if entry.is_symlink() else None}
            if entry.is_dir():
                for file in sorted(entry.rglob("*")):
                    if file.is_file():
                        state[f"skills/{entry.name}/{file.relative_to(entry)}"] = hashlib.sha256(file.read_bytes()).hexdigest()
    return state


def candidate_duplicates(home):
    candidates = []
    for name, expected in ORIGINALS.items():
        folder = home / ".agents/skills" / name
        if not folder.exists() and not folder.is_symlink():
            continue
        if folder.is_symlink() or not folder.is_dir() or sorted(p.name for p in folder.iterdir()) != ["SKILL.md"]:
            raise RuntimeError(f"Refusing to migrate an unfamiliar skill directory: {folder}")
        if hashlib.sha256((folder / "SKILL.md").read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Refusing to migrate a modified skill: {folder}")
        candidates.append(folder)
    return candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--migrate-duplicates", action="store_true")
    parser.add_argument("--vault", type=Path)
    parser.add_argument("--agent-guidance", action="store_true", help="Merge this package's scoped guidance into global Codex AGENTS.md")
    parser.add_argument("--memory-hooks", action="store_true", help="Install user-level lifecycle hooks for the configured Codex vault")
    args = parser.parse_args()
    home = Path.home()
    codex_home = Path(os.environ.get("CODEX_HOME", home / ".codex")).expanduser().resolve()
    destination = codex_home / "local-marketplaces" / NAME
    duplicates = candidate_duplicates(home) if args.migrate_duplicates else []
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    memory_config = config_home / NAME / "memory.json"
    vault = args.vault.expanduser().resolve() if args.vault else None
    if args.memory_hooks and not (vault or os.environ.get("CODEX_MEMORY_VAULT") or memory_config.is_file()):
        raise RuntimeError("Choose a Codex memory vault before enabling memory hooks")
    if memory_config.exists() and vault:
        if json.loads(memory_config.read_text()).get("vault") != str(vault):
            raise RuntimeError("Existing Codex memory configuration has a different vault; not overwriting")
    if destination.is_symlink():
        raise RuntimeError("Marketplace target is a symlink; refusing to overwrite")
    if destination.exists():
        inventory = destination / "release-files.json"
        if not inventory.is_file():
            raise RuntimeError("Marketplace target already exists without our release inventory")
        expected = json.loads(inventory.read_text())
        actual = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.rglob("*") if p.is_file() and p.name != "release-files.json"}
        if actual != expected:
            raise RuntimeError("Installed marketplace source has local changes; not overwriting")
    if args.dry_run:
        print(json.dumps({"marketplace_target": str(destination), "plugin": f"{NAME}@{MARKETPLACE}", "duplicates_to_backup_after_verification": [str(p) for p in duplicates], "memory_vault": str(vault) if vault else None, "agent_guidance": args.agent_guidance, "memory_hooks": args.memory_hooks, "claude_changes": []}, indent=2))
        return

    before = claude_state()
    marketplaces = cli("marketplace", "list").get("marketplaces", [])
    existing = next((item for item in marketplaces if item["name"] == MARKETPLACE), None)
    if existing and Path(existing["root"]).resolve() != destination:
        raise RuntimeError("Marketplace name belongs to another source; not overwriting")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    backup = codex_home / "backups" / NAME / stamp
    backup.mkdir(parents=True, mode=0o700)
    configuration = codex_home / "config.toml"
    if configuration.is_file():
        shutil.copy2(configuration, backup / "config.toml")
        (backup / "config.toml").chmod(0o600)
    agents = codex_home / "AGENTS.md"
    if args.agent_guidance and agents.exists():
        shutil.copy2(agents, backup / "AGENTS.md")
    hooks_file = codex_home / "hooks.json"
    if args.memory_hooks and hooks_file.exists():
        shutil.copy2(hooks_file, backup / "hooks.json")
    if destination.exists():
        if ROOT.resolve() == destination.resolve():
            raise RuntimeError("Run upgrades from a separately validated package, not the installed source")
        shutil.move(str(destination), backup / "marketplace-source")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if not existing:
        cli("marketplace", "add", str(destination))
    # Local marketplaces are read from their source; marketplace upgrade
    # refreshes Git sources and is unnecessary for this local directory.
    installed = cli("add", f"{NAME}@{MARKETPLACE}")
    listing = cli("list")
    entries = listing.get("installed", [])
    entry = next((item for item in entries if item.get("name") == NAME and item.get("marketplaceName") == MARKETPLACE), None)
    if not entry or not entry.get("enabled"):
        raise RuntimeError("Plugin installation was not verified enabled; standalone skills have been retained")
    installed_path = Path(installed["installedPath"])
    expected_skills = sorted(p.name for p in (destination / "plugins" / NAME / "skills").iterdir())
    actual_skills = sorted(p.name for p in (installed_path / "skills").iterdir())
    if expected_skills != actual_skills:
        raise RuntimeError("Installed skill inventory does not match; standalone skills have been retained")
    for skill in expected_skills:
        source = destination / "plugins" / NAME / "skills" / skill / "SKILL.md"
        if source.read_bytes() != (installed_path / "skills" / skill / "SKILL.md").read_bytes():
            raise RuntimeError("Installed skill content differs; standalone skills have been retained")
    for source in (destination / "plugins" / NAME).rglob("*"):
        if source.is_file():
            cached = installed_path / source.relative_to(destination / "plugins" / NAME)
            if not cached.is_file() or cached.read_bytes() != source.read_bytes():
                raise RuntimeError(f"Installed plugin resource differs: {source.name}")
    if args.agent_guidance:
        merge_agent_guidance(agents, destination / "references/agent-guidance.md")
    if args.memory_hooks:
        merge_memory_hooks(hooks_file, destination / "plugins" / NAME / "skills/vault-memory/scripts/hooks.py")
    if vault:
        vault.mkdir(parents=True, exist_ok=True, mode=0o700)
        memory_config.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not memory_config.exists():
            fd = os.open(memory_config, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write(json.dumps({"vault": str(vault)}, indent=2) + "\n")
    if duplicates:
        duplicate_backup = backup / "standalone-skills"
        duplicate_backup.mkdir()
        # Recheck after installation in case another process changed a skill.
        if candidate_duplicates(home) != duplicates:
            raise RuntimeError("Standalone skill state changed during installation; not migrating")
        for folder in duplicates:
            shutil.move(str(folder), duplicate_backup / folder.name)
    after = claude_state()
    if before != after:
        raise RuntimeError("Claude state changed during installation; investigate concurrent changes")
    print(json.dumps({"plugin": f"{NAME}@{MARKETPLACE}", "enabled": True, "installed_path": str(installed_path), "source": str(destination), "skills": actual_skills, "backup": str(backup), "migrated_duplicate_count": len(duplicates), "memory_vault": str(vault) if vault else None, "agent_guidance": args.agent_guidance, "memory_hooks": args.memory_hooks, "claude_state_unchanged": True, "hooks": "Review and trust installed vault-memory hooks with /hooks in Codex."}, indent=2))


def merge_agent_guidance(target, source):
    start, end = "<!-- ronny-codex-skills:start -->", "<!-- ronny-codex-skills:end -->"
    previous = target.read_text() if target.exists() else ""
    block = start + "\n" + source.read_text().strip() + "\n" + end
    if start in previous or end in previous:
        if previous.count(start) != 1 or previous.count(end) != 1 or previous.index(start) > previous.index(end):
            raise RuntimeError("Malformed managed AGENTS.md block; not overwriting")
        updated = previous[:previous.index(start)] + block + previous[previous.index(end) + len(end):]
    else:
        updated = previous.rstrip() + ("\n\n" if previous.strip() else "") + block + "\n"
    if updated != previous:
        target.write_text(updated)


def merge_memory_hooks(target, script):
    import shlex
    command = "python3 " + shlex.quote(str(script))
    data = json.loads(target.read_text()) if target.exists() else {}
    hooks = data.setdefault("hooks", {})
    for event in ("SessionStart", "PreCompact", "SessionEnd"):
        entries = hooks.setdefault(event, [])
        matching = [handler for entry in entries for handler in entry.get("hooks", []) if handler.get("command") == command]
        if matching:
            continue
        entry = {"hooks": [{"type": "command", "command": command, "timeout": 3 if event == "SessionEnd" else 30}]}
        if event == "SessionStart":
            entry["matcher"] = "startup|resume|clear|compact"
        entries.append(entry)
    text = json.dumps(data, indent=2) + "\n"
    if not target.exists() or target.read_text() != text:
        target.write_text(text)
        target.chmod(0o600)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"install: {exc}", file=sys.stderr)
        sys.exit(1)
