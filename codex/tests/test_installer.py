import importlib.util
import hashlib
import json
import os
from pathlib import Path
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parents[1] / "scripts/install_local.py"
spec = importlib.util.spec_from_file_location("installer", SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="codex-install-test-")
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.folder = self.home / ".agents/skills/current-docs"
        self.folder.mkdir(parents=True)

    def test_modified_duplicate_refused(self):
        (self.folder / "SKILL.md").write_text("Local custom instructions")
        with self.assertRaisesRegex(RuntimeError, "modified skill"):
            installer.candidate_duplicates(self.home)
        self.assertTrue(self.folder.exists())

    def test_symlink_duplicate_refused(self):
        self.folder.rmdir()
        target = self.home / "custom-skill"
        target.mkdir()
        self.folder.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, "unfamiliar"):
            installer.candidate_duplicates(self.home)

    def test_failed_enable_keeps_duplicates_and_claude_settings(self):
        (self.folder / "SKILL.md").write_text("preserve me")
        claude = self.home / ".claude/settings.json"
        claude.parent.mkdir()
        claude.write_text('{"hooks":{"Existing":[]}}')
        plugin = self.home / ".codex/plugins/cache/ronny-local/ronny-codex-skills/local"
        def fake_cli(*args):
            if args == ("marketplace", "list"):
                return {"marketplaces": []}
            if args[0] == "add":
                return {"installedPath": str(plugin)}
            return {"installed": []}
        environment = {key: value for key, value in os.environ.items() if key not in ("CODEX_HOME", "XDG_CONFIG_HOME")}
        with patch.object(Path, "home", return_value=self.home), patch.dict(os.environ, environment, clear=True), patch.object(sys, "argv", [str(SCRIPT), "--migrate-duplicates"]), patch.object(installer, "candidate_duplicates", return_value=[self.folder]), patch.object(installer, "cli", side_effect=fake_cli):
            with self.assertRaisesRegex(RuntimeError, "not verified enabled"):
                installer.main()
        self.assertEqual((self.folder / "SKILL.md").read_text(), "preserve me")
        self.assertEqual(claude.read_text(), '{"hooks":{"Existing":[]}}')

    def test_dry_run_does_not_write(self):
        environment = {key: value for key, value in os.environ.items() if key not in ("CODEX_HOME", "XDG_CONFIG_HOME")}
        with patch.object(Path, "home", return_value=self.home), patch.dict(os.environ, environment, clear=True), patch.object(sys, "argv", [str(SCRIPT), "--dry-run", "--vault", str(self.home / "chosen-vault")]), patch("builtins.print"):
            installer.main()
        self.assertFalse((self.home / ".codex").exists())
        self.assertFalse((self.home / "chosen-vault").exists())

    def test_local_upgrade_preserves_configuration_and_avoids_git_refresh(self):
        source = self.home / ".codex/local-marketplaces" / installer.NAME
        source.mkdir(parents=True)
        old = source / "previous.txt"
        old.write_text("Previous release")
        (source / "release-files.json").write_text(json.dumps({"previous.txt": hashlib.sha256(old.read_bytes()).hexdigest()}))
        claude = self.home / ".claude/settings.json"
        claude.parent.mkdir()
        claude.write_text('{"hooks":{"Existing":[]}}')
        config = self.home / ".config/ronny-codex-skills/memory.json"
        config.parent.mkdir(parents=True)
        config.write_text('{"vault":"/fixture/selected-vault"}')
        installed = self.home / ".codex/plugins/cache/ronny-local/ronny-codex-skills/1.1.0"
        calls = []
        def fake_cli(*args):
            calls.append(args)
            if args == ("marketplace", "list"):
                return {"marketplaces": [{"name": installer.MARKETPLACE, "root": str(source)}]}
            if args[0] == "add":
                shutil.copytree(source / "plugins" / installer.NAME, installed)
                return {"installedPath": str(installed)}
            if args == ("list",):
                return {"installed": [{"name": installer.NAME, "marketplaceName": installer.MARKETPLACE, "enabled": True}]}
            raise AssertionError(f"Unexpected CLI command: {args}")
        environment = {key: value for key, value in os.environ.items() if key not in ("CODEX_HOME", "XDG_CONFIG_HOME")}
        with patch.object(Path, "home", return_value=self.home), patch.dict(os.environ, environment, clear=True), patch.object(sys, "argv", [str(SCRIPT)]), patch.object(installer, "cli", side_effect=fake_cli), patch("builtins.print"):
            installer.main()
        self.assertEqual(config.read_text(), '{"vault":"/fixture/selected-vault"}')
        self.assertEqual(claude.read_text(), '{"hooks":{"Existing":[]}}')
        self.assertTrue((installed / "skills/managed-audit/SKILL.md").is_file())
        self.assertEqual(len(list((installed / "skills").iterdir())), 12)
        self.assertTrue(list((self.home / ".codex/backups").rglob("previous.txt")))
        self.assertNotIn(("marketplace", "upgrade", installer.MARKETPLACE), calls)

    def test_guidance_preserves_existing_text_and_updates_its_own_block(self):
        target, source = self.home / "AGENTS.md", self.home / "guidance.md"
        target.write_text("Existing user instructions\n")
        source.write_text("First guidance\n")
        installer.merge_agent_guidance(target, source)
        source.write_text("Updated guidance\n")
        installer.merge_agent_guidance(target, source)
        self.assertIn("Existing user instructions", target.read_text())
        self.assertIn("Updated guidance", target.read_text())
        self.assertNotIn("First guidance", target.read_text())
        self.assertEqual(target.read_text().count("<!-- ronny-codex-skills:start -->"), 1)

    def test_malformed_guidance_block_is_preserved(self):
        target, source = self.home / "AGENTS.md", self.home / "guidance.md"
        target.write_text("<!-- ronny-codex-skills:start -->\nUnfinished block")
        source.write_text("New guidance")
        before = target.read_text()
        with self.assertRaisesRegex(RuntimeError, "Malformed"):
            installer.merge_agent_guidance(target, source)
        self.assertEqual(target.read_text(), before)

    def test_hooks_preserve_unrelated_handlers_and_are_idempotent(self):
        target = self.home / "hooks.json"
        target.write_text(json.dumps({"description": "Existing hooks", "hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "existing-command"}]}]}}))
        script = self.home / "space in path/hooks.py"
        installer.merge_memory_hooks(target, script)
        installer.merge_memory_hooks(target, script)
        data = json.loads(target.read_text())
        self.assertEqual(data["description"], "Existing hooks")
        self.assertEqual(len(data["hooks"]["SessionStart"]), 2)
        self.assertEqual(data["hooks"]["SessionStart"][0]["hooks"][0]["command"], "existing-command")
        self.assertEqual(data["hooks"]["SessionEnd"][0]["hooks"][0]["timeout"], 3)
        self.assertIn("'", data["hooks"]["PreCompact"][0]["hooks"][0]["command"])


if __name__ == "__main__":
    unittest.main()
