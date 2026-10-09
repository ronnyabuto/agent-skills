import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/ronny-codex-skills/skills/vault-memory/scripts/hooks.py"
MEMORY = SCRIPT.with_name("memory.py")


class HookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="codex-hook-test-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.cwd = self.base / "project"
        self.cwd.mkdir()
        self.vault = self.base / "vault"
        self.env = dict(os.environ, CODEX_MEMORY_VAULT=str(self.vault), CODEX_MEMORY_CACHE=str(self.base / "cache"), CODEX_MEMORY_EXCLUDE="")
        self.source = self.base / "session.jsonl"
        self.rows = [
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "causal-boundary-marker API_TOKEN=secret-fixture"}]}},
            {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Keep the invariant at its owner."}]}},
            {"type": "response_item", "payload": {"type": "reasoning", "text": "PRIVATE_REASONING"}},
            {"type": "response_item", "payload": {"type": "function_call_output", "output": "PRIVATE_TOOL_OUTPUT"}},
        ]
        self.source.write_text("\n".join(map(json.dumps, self.rows)) + "\n")

    def hook(self, event, **overrides):
        payload = dict(session_id="session-fixture", cwd=str(self.cwd), transcript_path=str(self.source), hook_event_name=event)
        payload.update(overrides)
        result = subprocess.run([sys.executable, "-B", str(SCRIPT)], input=json.dumps(payload), text=True, capture_output=True, env=self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_archive_search_read_and_compaction_recall(self):
        self.assertEqual(self.hook("PreCompact").stderr, "")
        self.assertEqual(self.hook("SessionEnd").stderr, "")
        files = list(self.vault.rglob("*.md"))
        self.assertEqual(len(files), 1)
        text = files[0].read_text()
        self.assertIn("causal-boundary-marker", text)
        for secret in ("secret-fixture", "PRIVATE_REASONING", "PRIVATE_TOOL_OUTPUT"):
            self.assertNotIn(secret, text)
        search = subprocess.run([sys.executable, "-B", str(MEMORY), "--cwd", str(self.cwd), "search", "causal boundary"], env=self.env, text=True, capture_output=True, check=True)
        relative = str(files[0].relative_to(self.vault))
        self.assertIn(relative, search.stdout)
        read = subprocess.run([sys.executable, "-B", str(MEMORY), "read", relative, "--lines", "1:30"], env=self.env, text=True, capture_output=True, check=True)
        self.assertIn("causal-boundary-marker", read.stdout)
        output = json.loads(self.hook("SessionStart", source="compact").stdout)
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn(relative, context)
        self.assertLess(len(context), 1500)

    def test_later_event_updates_existing_snapshot(self):
        self.hook("PreCompact")
        self.source.write_text(self.source.read_text() + json.dumps({"type": "compacted", "payload": {"message": "Later compacted summary"}}) + "\n")
        self.hook("SessionEnd")
        files = list(self.vault.rglob("*.md"))
        self.assertEqual(len(files), 1)
        self.assertIn("Later compacted summary", files[0].read_text())

    def test_exclusion_and_empty_start_produce_no_context(self):
        self.assertEqual(self.hook("SessionStart").stdout, "")
        self.env["CODEX_MEMORY_EXCLUDE"] = "project"
        self.assertEqual(self.hook("PreCompact").stderr, "")
        self.assertEqual(list(self.vault.rglob("*.md")), [])
        self.assertEqual(self.hook("SessionStart").stdout, "")

    def test_torn_tail_allowed_only_for_hook(self):
        self.source.write_text(self.source.read_text() + '{"type":')
        self.assertEqual(self.hook("PreCompact").stderr, "")
        result = subprocess.run([sys.executable, "-B", str(MEMORY), "import-session", str(self.source)], env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)

    def test_invalid_format_is_reported_without_blocking(self):
        self.source.write_text('{"type":"unknown"}\n')
        self.assertIn("no recognized", self.hook("PreCompact").stderr)
        self.assertEqual(list(self.vault.rglob("*.md")), [])

    def test_missing_transcript_does_not_scan_other_sessions(self):
        self.assertEqual(self.hook("SessionEnd", transcript_path=None).stderr, "")
        self.assertEqual(list(self.vault.rglob("*.md")), [])


if __name__ == "__main__":
    unittest.main()
