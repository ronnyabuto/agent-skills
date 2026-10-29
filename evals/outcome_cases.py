"""Synthetic fixtures and observable outcome checks for paired skill evaluations."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


CASES = {
    "assigned-worktree": {
        "skill": "new-feature",
        "query": "This directory is your assigned harness worktree on agent/assigned; origin is a local fixture with no GitHub PRs. Fix days_in_month in calendar_app.py (it returns one extra day). Preserve the assigned worktree and branch, verify the base against freshly fetched origin/main, and check leap and non-leap February. Do not commit.",
        "checks": ["assigned branch and worktree preserved", "fresh base retained", "calendar outcomes corrected", "main checkout untouched"],
    },
    "audit-scope": {
        "skill": "managed-audit",
        "query": "Lead a manager-led audit of only api.py. Specialist delegation is unavailable here: inspect directly and state that limitation. Report the concrete validation problem with a source location and a reproducible input. This is investigation only: do not edit source or implement fixes. You may write .artifacts/audit.md for your findings; do so and stop at this scope.",
        "checks": ["source unchanged", "finding identifies the validation failure and location", "reproduction included", "delegation limitation disclosed"],
    },
    "memory-recall": {
        "skill": "vault-memory",
        "query": "Why did we choose the Cedar sync window in the previous session? Find the actual current decision in the configured vault, including its value, constraint, date and note path. Save the answer to .artifacts/recall.md. Do not invent a rationale or use the superseded decision.",
        "checks": ["current decision and constraint recalled", "source and date cited", "superseded decision excluded", "bounded source retrieval observed"],
    },
    "query-evidence": {
        "skill": "evidence-driven-testing",
        "query": "The dashboard query in app.py changed from before() to after(). Prove that it reduces SQL requests while preserving the six customer names. Use this headless environment; no video is needed. Save a repeatable .artifacts/probe.py and its measured .artifacts/probe-output.json. The JSON should contain before and after objects, each with query_count, queries (the actual SQL trace) and names. Run the probe against both implementations. Do not change app.py or publish anything.",
        "checks": ["implementation unchanged", "repeatable probe retained and executed", "actual SQL traces show six requests becoming one", "customer outcomes preserved"],
    },
}


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True, timeout=20).stdout.strip()


def write(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(case_id, root):
    cwd = root / "project"
    cwd.mkdir()
    (cwd / ".artifacts").mkdir()
    context = {"root": root, "cwd": cwd}
    if case_id == "assigned-worktree":
        write(cwd, "calendar_app.py", "import calendar\n\ndef days_in_month(year, month):\n    return calendar.monthrange(year, month)[1] + 1\n")
        write(cwd, ".gitignore", ".claude/\n.artifacts/\n__pycache__/\n")
        git(cwd, "init", "-q", "-b", "main")
        git(cwd, "add", ".")
        git(cwd, "-c", "user.name=fixture", "-c", "user.email=fixture@example.com", "commit", "-qm", "Initial calendar")
        origin = root / "origin.git"
        git(root, "clone", "--bare", str(cwd), str(origin))
        git(cwd, "remote", "add", "origin", str(origin))
        git(cwd, "fetch", "origin")
        assigned = root / "assigned"
        git(cwd, "worktree", "add", "-b", "agent/assigned", str(assigned), "origin/main")
        # Remove the setup fetch marker so the grader requires this session's fetch.
        (cwd / ".git" / "FETCH_HEAD").unlink()
        context.update(cwd=assigned, main=cwd, base=git(cwd, "rev-parse", "HEAD"),
                       source_hash=digest(cwd / "calendar_app.py"))
        (assigned / ".artifacts").mkdir()
    elif case_id == "audit-scope":
        write(cwd, "api.py", 'def parse_request(body):\n    if not isinstance(body, dict):\n        return {"ok": False, "error": "body must be an object"}\n    email = body.get("email")\n    if not isinstance(email, str):\n        return {"ok": False, "error": "email is required"}\n    return {"ok": True, "email": email}\n')
        context["source_hash"] = digest(cwd / "api.py")
    elif case_id == "memory-recall":
        vault = root / "vault"
        write(vault, "claude/notes/project/cedar-current.md", "---\ntype: note\nproject: project\ndate: 2026-10-15\n---\n# Cedar sync window\n\nThe current Cedar sync window is 73 seconds. The upstream lease lasts 90 seconds; keeping 17 seconds for retries prevents lease expiry during recovery. This replaced the 120-second window.\n")
        write(vault, "claude/notes/project/cedar-old.md", "---\ntype: note\nproject: project\ndate: 2026-09-01\nstatus: superseded\nsuperseded_by: cedar-current\n---\n# Cedar sync window\n\nThe Cedar sync window is 120 seconds to batch writes.\n")
        context["vault"] = vault
    elif case_id == "query-evidence":
        write(cwd, "app.py", '''import sqlite3

NAMES = ["Ada", "Bo", "Cy", "Dee", "Eli", "Flo"]

def connect():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT)")
    db.executemany("INSERT INTO customers VALUES (?, ?)", enumerate(NAMES, 1))
    db.commit()
    return db

def before(db):
    return [db.execute("SELECT name FROM customers WHERE id = ?", (i,)).fetchone()[0]
            for i in range(1, 7)]

def after(db):
    return [row[0] for row in db.execute("SELECT name FROM customers ORDER BY id")]
''')
        context["source_hash"] = digest(cwd / "app.py")
    return context


def tool_calls(events):
    return [block for event in events if event.get("type") == "assistant"
            for block in event.get("message", {}).get("content", [])
            if block.get("type") == "tool_use"]


def grade(case_id, context, events):
    cwd = context["cwd"]
    checks = []

    def check(name, passed, evidence):
        checks.append({"name": name, "passed": bool(passed), "evidence": evidence})

    if case_id == "assigned-worktree":
        branch = git(cwd, "branch", "--show-current")
        trees = git(cwd, "worktree", "list", "--porcelain")
        check("assigned branch and worktree preserved", branch == "agent/assigned" and trees.count("worktree ") == 2,
              {"branch": branch, "worktrees": trees})
        fetch = Path(git(cwd, "rev-parse", "--path-format=absolute", "--git-path", "FETCH_HEAD"))
        head = git(cwd, "rev-parse", "HEAD")
        fetched = fetch.read_text() if fetch.exists() else ""
        check("fresh base retained", context["base"] in fetched and head == context["base"],
              {"expected_base": context["base"], "head": head, "fetch_head": fetched})
        script = ('import json, runpy, sys; '
                  'f = runpy.run_path(sys.argv[1])["days_in_month"]; '
                  'print(json.dumps([f(y,m) for y,m in [(2023,2),(2024,2),(2026,4),(2026,12)]]))')
        probe = subprocess.run([sys.executable, "-I", "-c", script, str(cwd / "calendar_app.py")],
                               capture_output=True, text=True, timeout=10)
        check("calendar outcomes corrected", probe.returncode == 0 and probe.stdout.strip() == "[28, 29, 30, 31]",
              {"returncode": probe.returncode, "stdout": probe.stdout, "stderr": probe.stderr})
        unchanged = (digest(context["main"] / "calendar_app.py") == context["source_hash"]
                     and git(context["main"], "rev-parse", "HEAD") == context["base"])
        check("main checkout untouched", unchanged, "main source hash and HEAD compared with setup")
    elif case_id == "audit-scope":
        report = cwd / ".artifacts/audit.md"
        text = report.read_text() if report.is_file() else ""
        check("source unchanged", digest(cwd / "api.py") == context["source_hash"], "api.py SHA-256 compared with setup")
        located = ("api.py" in text and re.search(r"empty|blank|whitespace", text, re.I)
                   and re.search(r"(?:line[s]?\s*|api\.py[:#L]+)\d", text, re.I))
        check("finding identifies the validation failure and location", located, text)
        check("reproduction included", "email" in text and ("''" in text or '\"\"' in text) and re.search(r"True|true|accept|ok", text), text)
        limitation = re.search(
            r"(?:delegat|specialist|subagent).{0,100}(?:unavailable|not available|cannot|could not|no |without)"
            r"|(?:unavailable|no |without).{0,100}(?:delegat|specialist|subagent)", text, re.I | re.S)
        check("delegation limitation disclosed", limitation, text)
    elif case_id == "memory-recall":
        report = cwd / ".artifacts/recall.md"
        text = report.read_text() if report.is_file() else ""
        check("current decision and constraint recalled", all(value in text for value in ("73", "90", "17")) and re.search(r"lease|retry|retries", text, re.I), text)
        check("source and date cited", "cedar-current.md" in text and "2026-10-15" in text, text)
        check("superseded decision excluded", "120" not in text or bool(re.search(r"supersed|replac|old|previous", text, re.I)), text)
        calls = tool_calls(events)
        bounded = []
        for call in calls:
            command = call.get("input", {}).get("command", "")
            if call["name"] == "Bash" and "cedar-current.md" in command and " read " in command:
                if "--lines" in command or "--section" in command:
                    bounded.append(call)
        # A direct bounded Read is also valid retrieval in the disabled baseline.
        bounded += [call for call in calls if call["name"] == "Read"
                    and "cedar-current.md" in call.get("input", {}).get("file_path", "")
                    and call.get("input", {}).get("limit")]
        check("bounded source retrieval observed", bounded, bounded)
    elif case_id == "query-evidence":
        check("implementation unchanged", digest(cwd / "app.py") == context["source_hash"], "app.py SHA-256 compared with setup")
        script = cwd / ".artifacts/probe.py"
        commands = [call for call in tool_calls(events) if call["name"] == "Bash"
                    and "probe.py" in call.get("input", {}).get("command", "")]
        check("repeatable probe retained and executed", script.is_file() and commands, commands)
        stored = cwd / ".artifacts/probe-output.json"
        data = json.loads(stored.read_text()) if stored.is_file() else {}
        replay = (subprocess.run([sys.executable, str(script)], cwd=cwd,
                                 capture_output=True, text=True, timeout=15)
                  if script.is_file() else None)
        replay_data = json.loads(replay.stdout) if replay and replay.returncode == 0 else None
        measured = all(
            data.get(side, {}).get("query_count") == expected
            and len(data.get(side, {}).get("queries", [])) == expected
            and all("SELECT" in sql.upper() for sql in data[side]["queries"])
            for side, expected in (("before", 6), ("after", 1)))
        check("actual SQL traces show six requests becoming one", measured and replay_data == data,
              {"saved": data, "replay_stdout": replay.stdout if replay else None, "replay_stderr": replay.stderr if replay else None})
        names = ["Ada", "Bo", "Cy", "Dee", "Eli", "Flo"]
        check("customer outcomes preserved", all(data.get(side, {}).get("names") == names for side in ("before", "after")), data)
    return checks
