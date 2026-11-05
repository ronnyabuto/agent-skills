"""Exercise the installer settings merger against disposable synthetic files."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MERGER = (ROOT / "install.sh").read_text().split("node <<'EOF'\n", 1)[1].split("\nEOF", 1)[0]


class InstallHookTests(unittest.TestCase):
    def merge(self, settings, directory):
        target = directory / "settings.json"
        target.write_text(json.dumps(settings))
        result = subprocess.run(["node"], input=MERGER, text=True, capture_output=True, timeout=15,
                                env=dict(os.environ, SETTINGS=str(target), HOOK_CMD="node /synthetic/vault-memory/scripts/vault.mjs hook",
                                         VAULT=str(directory / "vault"), MODE="install", DRY="0",
                                         HOOKS_FILE=str(ROOT / "vault-memory/references/hooks.json")))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(target.read_text())

    def test_default_start_hook_includes_forks_and_upgrade_is_idempotent(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name)
            fresh = self.merge({}, directory)
            self.assertNotIn("matcher", fresh["hooks"]["SessionStart"][0])
            legacy = {"matcher": "startup|resume|clear|compact", "hooks": [{"type": "command", "command": "node /synthetic/vault-memory/scripts/vault.mjs hook", "timeout": 30}]}
            settings = self.merge({"hooks": {"SessionStart": [legacy]}}, directory)
            start = settings["hooks"]["SessionStart"]
            self.assertEqual(len(start), 1)
            self.assertTrue(re.search(start[0].get("matcher", ".*"), "fork"))
            self.assertEqual(self.merge(settings, directory), settings)

    def test_custom_and_mixed_groups_keep_their_filters(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name)
            handler = {"type": "command", "command": "node /synthetic/vault-memory/scripts/vault.mjs hook"}
            groups = [{"matcher": "resume", "hooks": [handler]},
                      {"matcher": "startup|resume|clear|compact", "hooks": [handler, {"type": "command", "command": "other-handler"}]}]
            settings = self.merge({"hooks": {"SessionStart": groups}}, directory)
            self.assertEqual(settings["hooks"]["SessionStart"], groups)
