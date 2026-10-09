import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parents[1] / "plugins/ronny-codex-skills/skills/vault-memory/scripts/memory.py"
spec = importlib.util.spec_from_file_location("memory", SCRIPT)
memory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memory)


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="codex-memory-test-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "vault"
        self.root.mkdir()
        self.cwd = self.base / "project"
        self.cwd.mkdir()
        self.env = dict(os.environ, CODEX_MEMORY_VAULT=str(self.root), CODEX_MEMORY_CACHE=str(self.base / "cache"), CODEX_MEMORY_EXCLUDE="", XDG_CONFIG_HOME=str(self.base / "config"))

    def cli(self, *args, body=None, cwd=None, env=None, success=True):
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--cwd", str(cwd or self.cwd), *args], input=body, capture_output=True, text=True, env=env or self.env)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def test_note_search_read_and_redaction(self):
        path = self.cli("note", "--title", "Refresh ownership", body="Refresh race stays in the caller. API_TOKEN=very-secret-value").stdout.strip()
        text = self.cli("read", path).stdout
        self.assertNotIn("very-secret-value", text)
        self.assertIn("[REDACTED]", text)
        hit = self.cli("search", "refresh race").stdout
        self.assertIn(path + ":", hit)
        self.assertLess(len(hit), 1500)

    def test_vault_required_and_project_exclusion(self):
        env = dict(self.env)
        env.pop("CODEX_MEMORY_VAULT")
        self.cli("note", "--title", "Decision", body="Reason", env=env, success=False)
        env = dict(self.env, CODEX_MEMORY_EXCLUDE="project")
        self.cli("note", "--title", "Decision", body="Reason", env=env, success=False)
        self.assertEqual(list(self.root.rglob("*.md")), [])

    def test_explicit_saved_vault_configuration(self):
        config = self.base / "config" / "ronny-codex-skills" / "memory.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"vault": str(self.root)}))
        env = dict(self.env)
        env.pop("CODEX_MEMORY_VAULT")
        path = self.cli("note", "--title", "Configured", body="Explicit location", env=env).stdout.strip()
        self.assertTrue((self.root / path).is_file())

    def test_escape_and_symlink_rejected(self):
        outside = self.base / "outside.md"
        outside.write_text("OUTSIDE FIXTURE")
        (self.root / "alias.md").symlink_to(outside)
        self.cli("read", "../outside.md", success=False)
        self.cli("read", "alias.md", success=False)
        self.cli("read", str(outside), success=False)
        self.assertNotIn("OUTSIDE FIXTURE", self.cli("search", "OUTSIDE", "--all-projects").stdout)
        directory = self.root / "codex"
        directory.symlink_to(self.base / "elsewhere", target_is_directory=True)
        self.cli("note", "--title", "Escape", body="Must stay in vault", success=False)

    def test_same_titles_concurrently_do_not_overwrite(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            paths = list(pool.map(lambda i: self.cli("note", "--title", "Same title", body=f"Distinct decision {i}").stdout.strip(), range(8)))
        self.assertEqual(len(set(paths)), 8)
        self.assertEqual(len(list(self.root.rglob("*.md"))), 8)
        for index, path in enumerate(paths):
            self.assertIn(f"Distinct decision {index}", (self.root / path).read_text())

    def test_repositories_separate_and_worktrees_share_identity(self):
        first = self.base / "first" / "app"
        second = self.base / "second" / "app"
        for path in (first, second):
            path.mkdir(parents=True)
            subprocess.run(["git", "init", "-q", str(path)], check=True)
        self.assertNotEqual(memory.project_id(first), memory.project_id(second))
        subprocess.run(["git", "-C", str(first), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--allow-empty", "-qm", "Fixture"], check=True)
        worktree = self.base / "worktree"
        subprocess.run(["git", "-C", str(first), "worktree", "add", "-q", "-b", "fixture-branch", str(worktree)], check=True)
        self.assertEqual(memory.project_id(first), memory.project_id(worktree))
        path = self.cli("note", "--title", "Owner", body="Repository one", cwd=first).stdout.strip()
        self.assertIn(path, self.cli("search", "Repository", cwd=worktree).stdout)
        self.assertEqual(self.cli("search", "Repository", cwd=second).stdout, "")

    def test_content_hash_freshness_and_deleted_notes(self):
        path = self.cli("note", "--title", "Index", body="alpha-key").stdout.strip()
        self.assertIn(path, self.cli("search", "alpha").stdout)
        file = self.root / path
        stat = file.stat()
        file.write_text(file.read_text().replace("alpha-key", "omega-key"))
        os.utime(file, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertIn(path, self.cli("search", "omega").stdout)
        self.assertEqual(self.cli("search", "alpha").stdout, "")
        file.unlink()
        self.assertEqual(self.cli("search", "omega").stdout, "")

    def test_superseded_notes_hidden(self):
        old = self.cli("note", "--title", "Old", body="Old race policy").stdout.strip()
        new = self.cli("note", "--title", "New", body="New race policy").stdout.strip()
        self.cli("supersede", old, "--by", new)
        self.assertNotIn(old, self.cli("search", "race").stdout)
        self.assertIn(new, self.cli("search", "race").stdout)
        self.assertIn(old, self.cli("search", "race", "--include-superseded").stdout)

    def test_output_bounds_and_search_punctuation(self):
        path = self.cli("note", "--title", "Large", body="\n".join("bounded text " * 100 for _ in range(80))).stdout.strip()
        output = self.cli("read", path, "--lines", "1:100", "--max-chars", "200").stdout
        self.assertLess(len(output), 260)
        self.cli("read", path, "--max-chars", "999999", success=False)
        self.cli("search", '" OR *'); self.cli("search", "!!!", success=False)

    def test_codex_transcript_import_omits_reasoning_outputs_arguments(self):
        rows = [
            {"type": "event_msg", "payload": {"type": "user_message", "message": "User decision"}},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "User decision"}]}},
            {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Keep retry ownership"}]}},
            {"type": "response_item", "payload": {"type": "function_call", "name": "exec_command", "arguments": "ARGUMENT_SENTINEL"}},
            {"type": "response_item", "payload": {"type": "function_call_output", "output": "OUTPUT_SENTINEL"}},
            {"type": "response_item", "payload": {"type": "reasoning", "text": "REASONING_SENTINEL"}},
            {"type": "compacted", "payload": {"message": "A compacted decision"}},
        ]
        source = self.base / "session.jsonl"
        source.write_text("\n".join(json.dumps(row) for row in rows))
        path = self.cli("import-session", str(source)).stdout.strip()
        text = (self.root / path).read_text()
        self.assertEqual(text.count("User decision"), 1)
        self.assertIn("exec_command", text)
        self.assertIn("A compacted decision", text)
        for sentinel in ("ARGUMENT_SENTINEL", "OUTPUT_SENTINEL", "REASONING_SENTINEL"):
            self.assertNotIn(sentinel, text)
        source.write_text(json.dumps({"type": "unknown"}))
        self.cli("import-session", str(source), success=False)
        source.write_text("not json")
        self.cli("import-session", str(source), success=False)


if __name__ == "__main__":
    unittest.main()
