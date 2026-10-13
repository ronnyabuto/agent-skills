"""Offline regression checks: python3 vault-memory/scripts/test_vault.py."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("vault.mjs")


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vault-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vault = self.root / "vault"
        self.vault.mkdir()
        self.env = dict(os.environ, AGENT_VAULT=str(self.vault), XDG_CACHE_HOME=str(self.root / "cache"))

    def run_cli(self, *args, input=None, check=True):
        result = subprocess.run(["node", str(SCRIPT), *args], input=input, capture_output=True,
                                text=True, env=self.env, timeout=30)
        if check:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def database(self):
        return sqlite3.connect(next((self.root / "cache" / "vault-memory").glob("*.sqlite")))

    def test_archive_redacts_keys_passwords_and_notifications(self):
        text = ("sk_live_" + "A" * 24 + " rk_live_" + "B" * 24 +
                " PASSWORD=abcdefghijk context_tokens: 182340 " +
                "<task-notification>internal notification</task-notification>")
        transcript = self.root / "synthetic.jsonl"
        transcript.write_text(json.dumps({"type": "user", "message": {"content": text}}) + "\n")
        self.run_cli("archive", str(transcript), "/tmp/synthetic-project")
        body = next(self.vault.rglob("*.md")).read_text()
        for value in ["sk_live_", "rk_live_", "abcdefghijk", "internal notification"]:
            self.assertNotIn(value, body)
        self.assertIn("PASSWORD=[REDACTED]", body)
        self.assertIn("context_tokens: 182340", body)

    def test_search_keeps_other_files_and_boolean_before_query(self):
        (self.vault / "archive.md").write_text("# oauth race\n" + "\n".join(
            f"## part {i}\nshort body" for i in range(50)))
        for i in range(8):
            (self.vault / f"note{i}.md").write_text("# ordinary note\n" + "filler " * 80 + "oauth race")
        result = self.run_cli("search", "--all", "oauth race", "--limit", "8")
        paths = [line.split(":", 1)[0] for line in result.stdout.splitlines() if line and not line.startswith(" ")]
        self.assertEqual(len(paths), 8)
        self.assertGreaterEqual(len(set(paths)), 7)
        self.assertLessEqual(paths.count("archive.md"), 2)

    def test_fenced_comments_do_not_become_headings(self):
        for i, marker in enumerate(["```", "~~~", "````"]):
            shorter = "```\n# still code\n" if marker != "```" else ""
            (self.vault / f"fence{i}.md").write_text(
                "# Real\n" + marker + "bash\n# shell comment\n" + shorter + marker + "\n## Outside\nbody")
        self.run_cli("index")
        with self.database() as db:
            headings = {r[0] for r in db.execute("SELECT heading FROM chunks")}
        self.assertEqual(headings, {"Real", "Outside"})

    def test_concurrent_indexing_has_no_duplicate_chunks(self):
        for i in range(100):
            (self.vault / f"note{i}.md").write_text(f"# note {i}\nbody\n")
        workers = [subprocess.Popen(["node", str(SCRIPT), "index"], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, env=self.env) for _ in range(8)]
        for worker in workers:
            _, err = worker.communicate(timeout=30)
            self.assertEqual(worker.returncode, 0, err)
        with self.database() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM files").fetchone()[0], 100)
            self.assertEqual(db.execute("SELECT count(*) FROM chunks").fetchone()[0], 100)
            self.assertEqual(db.execute("PRAGMA journal_mode").fetchone()[0], "wal")

    def test_failed_rebuild_preserves_previous_index(self):
        note = self.vault / "note.md"
        note.write_text("# preserved\nbody")
        self.run_cli("index")
        note.chmod(0)
        try:
            if os.access(note, os.R_OK):
                self.skipTest("this platform cannot make the fixture unreadable")
            result = self.run_cli("index", "--rebuild", check=False)
            self.assertNotEqual(result.returncode, 0)
            with self.database() as db:
                self.assertEqual(db.execute("SELECT title FROM files").fetchone()[0], "preserved")
                self.assertEqual(db.execute("SELECT count(*) FROM chunks").fetchone()[0], 1)
        finally:
            note.chmod(0o600)
        self.run_cli("index")


if __name__ == "__main__":
    unittest.main()
