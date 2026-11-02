"""Offline regression checks: python3 vault-memory/scripts/test_vault.py."""
import json
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
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

    def run_cli(self, *args, input=None, check=True, cwd=None):
        result = subprocess.run(["node", str(SCRIPT), *args], input=input, capture_output=True,
                                text=True, env=self.env, timeout=30, cwd=cwd)
        if check:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def database(self):
        return sqlite3.connect(next((self.root / "cache" / "vault-memory").glob("*.sqlite")))

    def start_cli(self, *args):
        worker = subprocess.Popen(["node", str(SCRIPT), *args], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, env=self.env)
        def cleanup():
            if worker.poll() is None:
                worker.kill()
            worker.communicate()
        self.addCleanup(cleanup)
        return worker

    def locked_database(self):
        key = hashlib.sha1(str(self.vault).encode()).hexdigest()[:12]
        cache = self.root / "cache" / "vault-memory"
        cache.mkdir(parents=True)
        db = sqlite3.connect(cache / f"{key}.sqlite")
        self.addCleanup(db.close)
        db.execute("CREATE TABLE blocker (id INTEGER)")
        db.commit()
        db.execute("BEGIN")
        db.execute("SELECT * FROM blocker").fetchall()
        return db

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
        workers = [self.start_cli("index") for _ in range(8)]
        results = [worker.communicate(timeout=30) for worker in workers]
        for worker, (_, err) in zip(workers, results):
            self.assertEqual(worker.returncode, 0, err)
        with self.database() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM files").fetchone()[0], 100)
            self.assertEqual(db.execute("SELECT count(*) FROM chunks").fetchone()[0], 100)
            self.assertEqual(db.execute("PRAGMA journal_mode").fetchone()[0], "wal")

    def test_wal_initialization_recovers_after_reader_releases_lock(self):
        (self.vault / "note.md").write_text("# recoverable\nbody")
        db = self.locked_database()
        worker = self.start_cli("index")
        time.sleep(0.3)
        self.assertIsNone(worker.poll(), "indexing should wait for the reader")
        db.rollback()
        _, err = worker.communicate(timeout=10)
        self.assertEqual(worker.returncode, 0, err)
        with self.database() as index:
            self.assertEqual(index.execute("SELECT title FROM files").fetchone()[0], "recoverable")
            self.assertEqual(index.execute("PRAGMA journal_mode").fetchone()[0], "wal")

    def test_persistent_lock_fails_within_budget_then_recovers(self):
        (self.vault / "note.md").write_text("# recoverable\nbody")
        db = self.locked_database()
        start = time.monotonic()
        result = self.run_cli("index", check=False)
        elapsed = time.monotonic() - start
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("database is locked", result.stderr)
        self.assertGreaterEqual(elapsed, 4.5)
        self.assertLess(elapsed, 10)
        db.rollback()
        self.run_cli("index")
        with self.database() as index:
            self.assertEqual(index.execute("SELECT count(*) FROM files").fetchone()[0], 1)

    def test_corrupt_index_is_not_retried_or_overwritten_and_hook_is_nonfatal(self):
        (self.vault / "note.md").write_text("# note\nbody")
        self.run_cli("index")
        cache = next((self.root / "cache" / "vault-memory").glob("*.sqlite"))
        cache.write_bytes(b"not a SQLite database")
        start = time.monotonic()
        result = self.run_cli("index", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a database", result.stderr)
        self.assertLess(time.monotonic() - start, 4)
        result = self.run_cli("hook", input=json.dumps({
            "hook_event_name": "SessionStart", "cwd": "/tmp/synthetic-project", "source": "startup",
        }))
        self.assertIn("vault-memory:", result.stderr)
        self.assertEqual(cache.read_bytes(), b"not a SQLite database")

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

    def test_repository_identity_separates_names_and_unifies_worktrees(self):
        first, second = (self.root / name / "api" for name in ("first", "second"))
        for repo in (first, second):
            repo.mkdir(parents=True)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(first), "-c", "user.name=Fixture", "-c",
                        "user.email=fixture@example.invalid", "commit", "--allow-empty", "-qm", "Fixture"], check=True)
        trees = [self.root / ".worktrees/task", first / ".claude/worktrees/task"]
        for index, tree in enumerate(trees):
            subprocess.run(["git", "-C", str(first), "worktree", "add", "-q", "-b",
                            f"task-{index}", str(tree)], check=True)
        paths = [self.run_cli("note", "--title", "Identity", input="bounded decision", cwd=repo).stdout.strip()
                 for repo in (first, *trees, second)]
        self.assertEqual(paths[0].split()[-1], paths[1].split()[-1])
        self.assertEqual(paths[0].split()[-1], paths[2].split()[-1])
        self.assertNotEqual(paths[0].split()[-1], paths[3].split()[-1])
        hook = self.run_cli("hook", input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(first)}))
        project = next(self.vault.glob("claude/notes/*/identity.md")).parent.name
        self.assertIn("api-", hook.stdout)
        self.assertTrue(project.startswith("api-"))

    def test_separate_git_directory_worktrees_share_identity(self):
        repo, tree = self.root / "app", self.root / "task"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "--separate-git-dir", str(self.root / "git-storage"), str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                        "commit", "--allow-empty", "-qm", "Fixture"], check=True)
        subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", "-b", "task", str(tree)], check=True)
        paths = [self.run_cli("note", "--title", "Identity", input="decision", cwd=cwd).stdout.split()[-1]
                 for cwd in (repo, tree)]
        self.assertEqual(paths[0], paths[1])

    def test_legacy_recall_is_preserved_without_assuming_ownership(self):
        repo = self.root / "api"
        repo.mkdir()
        old = self.vault / "claude/notes/api/old.md"
        old.parent.mkdir(parents=True)
        old.write_text("---\nproject: api\ntype: note\n---\n# PRIVATE LEGACY TITLE\nCedar legacy decision\n")
        before = old.read_bytes()
        hook = self.run_cli("hook", input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(repo)}))
        self.assertIn("unverified repository ownership", hook.stdout)
        self.assertIn('--project "api"', hook.stdout)
        self.assertNotIn("PRIVATE LEGACY TITLE", hook.stdout)
        self.assertIn("old.md", self.run_cli("search", "Cedar", "--project", "api").stdout)
        self.assertEqual(old.read_bytes(), before)

    def test_supersede_preserves_body_and_filters_search(self):
        old, new = (self.vault / name for name in ("old.md", "new.md"))
        old.write_text("---\nproject: api\nstatus: current\n---\n# Cedar old\nOld decision\n")
        new.write_text("---\nproject: api\n---\n# Cedar new\nCurrent decision\n")
        self.run_cli("supersede", "old.md", "--by", "new.md")
        text = old.read_text()
        self.assertIn("# Cedar old\nOld decision", text)
        self.assertNotIn("status: current", text)
        self.assertNotIn("old.md", self.run_cli("search", "Cedar").stdout)
        self.assertIn("old.md", self.run_cli("search", "Cedar", "--all").stdout)
        self.assertNotEqual(self.run_cli("supersede", "old.md", "--by", "new.md", check=False).returncode, 0)
        self.assertEqual(old.read_text(), text)

    def test_supersede_rejects_escape_missing_and_same_file(self):
        old = self.vault / "old.md"
        old.write_text("---\nproject: api\n---\n# Original\n")
        outside = self.root / "outside.md"
        outside.write_text("---\n---\nOutside\n")
        (self.vault / "alias.md").symlink_to(outside)
        before = old.read_bytes()
        for target in ("../outside.md", "alias.md", "missing.md", "old.md"):
            result = self.run_cli("supersede", "old.md", "--by", target, check=False)
            self.assertNotEqual(result.returncode, 0, target)
            self.assertEqual(old.read_bytes(), before)



if __name__ == "__main__":
    unittest.main()
