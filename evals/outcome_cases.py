"""Synthetic fixtures and observable outcome checks for paired skill evaluations."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys



CASES = json.loads((Path(__file__).parent / "outcome_contracts.json").read_text())


def contracts_bytes():
    """Canonical bytes of every case definition, saved with a run and hashed for resume."""
    return (json.dumps(CASES, indent=2, sort_keys=True) + "\n").encode()


def user_prompt(case_id):
    case = CASES[case_id]
    return "\n\n".join(part for part in (case["query"], case["deliverable"]) if part)


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
    elif case_id == "memory-recall":
        vault = root / "vault"
        write(vault, "claude/notes/project/cedar-current.md", "---\ntype: note\nproject: project\ndate: 2026-10-15\n---\n# Cedar sync window\n\nThe current Cedar sync window is 73 seconds. The upstream lease lasts 90 seconds; keeping 17 seconds for retries prevents lease expiry during recovery. This replaced the 120-second window.\n")
        write(vault, "claude/notes/project/cedar-old.md", "---\ntype: note\nproject: project\ndate: 2026-09-01\nstatus: superseded\nsuperseded_by: cedar-current\n---\n# Cedar sync window\n\nThe Cedar sync window is 120 seconds to batch writes.\n")
        context["vault"] = vault
    elif case_id == "stale-main":
        # Held out from new-feature tuning: a plain checkout on main that is behind origin.
        write(cwd, "text_utils.py", "def slugify(title):\n    return '-'.join(title.split())\n")
        write(cwd, ".gitignore", ".claude/\n.artifacts/\n__pycache__/\n")
        identity = ("-c", "user.name=fixture", "-c", "user.email=fixture@example.com")
        git(cwd, "init", "-q", "-b", "main")
        git(cwd, "add", ".")
        git(cwd, *identity, "commit", "-qm", "Add slugify")
        origin = root / "origin.git"
        git(root, "clone", "-q", "--bare", str(cwd), str(origin))
        git(cwd, "remote", "add", "origin", str(origin))
        git(cwd, "fetch", "-q", "origin")
        git(cwd, "branch", "-q", "--set-upstream-to=origin/main", "main")
        teammate = root / "teammate"
        git(root, "clone", "-q", str(origin), str(teammate))
        write(teammate, "CHANGELOG.md", "# Changelog\n\n- Release notes start here.\n")
        git(teammate, "add", ".")
        git(teammate, *identity, "commit", "-qm", "Start changelog")
        git(teammate, "push", "-q", "origin", "main")
        context.update(local_main=git(cwd, "rev-parse", "main"), fresh_base=git(teammate, "rev-parse", "HEAD"))
    elif case_id == "tracking-design":
        # Held out from system-design tuning: a different domain graded by the same rubric.
        write(cwd, "README.md", "# Shipments\n\nInternal shipment tracker for a regional parts distributor. One VM runs "
              "app.py against the existing Postgres database. About 300 shipments are in transit at any time; "
              "each changes status three to five times over two days. Customers check status on the tracking page "
              "about 1,000 times a day. The carrier's tracking API allows 20 requests per second per account "
              "and can send webhooks.\n")
        write(cwd, "app.py", 'import psycopg\n\n\ndef shipment_status(db: psycopg.Connection, shipment_id: int) -> str:\n'
              '    row = db.execute("SELECT status FROM shipments WHERE id = %s", (shipment_id,)).fetchone()\n'
              '    return row[0]\n')
        context["source_hashes"] = {name: digest(cwd / name) for name in ("README.md", "app.py")}
    elif case_id == "design-sizing":
        write(cwd, "README.md", "# Orders\n\nInternal order tracker for a 40-person wholesale team. One VM runs app.py "
              "against the existing Postgres database. About 300 customers place about 500 orders a day, "
              "mostly on weekdays between 08:00 and 18:00. Each order changes status about four times. "
              "IT provides an SMTP relay at smtp.internal that accepts up to 30 messages per second.\n")
        write(cwd, "app.py", 'import psycopg\n\n\ndef set_status(db: psycopg.Connection, order_id: int, status: str) -> None:\n'
              '    with db.transaction():\n'
              '        db.execute("UPDATE orders SET status = %s, updated_at = now() WHERE id = %s", (status, order_id))\n')
        context["source_hashes"] = {name: digest(cwd / name) for name in ("README.md", "app.py")}
    return context


# None of these is needed for about 2,000 status emails or a few hundred tracked shipments a day.
HEAVY_INFRASTRUCTURE = re.compile(
    r"kafka|rabbit|\bsqs\b|\bsns\b|pub/?sub|redis|celery|sidekiq|kubernetes|\bk8s\b|shard"
    r"|micro-?service|cassandra|elasticsearch|kinesis|load balancer|replica", re.I)
# A sentence that mentions heavy infrastructure only to rule it out or defer it is not a recommendation.
DEFERRED = re.compile(r"\b(?:no|not|without|avoid|unnecessary|overkill|later|until|if|when|instead|only)\b"
                      r"|n't\b|don't|do not", re.I)
RATE = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s*(?:emails?|messages?|msgs?|orders?|requests?|req|calls?|sends?|events?|polls?|webhooks?|updates?|shipments?)?\s*"
    r"(?:/|per)\s*(s|sec|second|min|minute|h|hr|hour)\b", re.I)
SECONDS = {"s": 1, "sec": 1, "second": 1, "min": 60, "minute": 60, "h": 3600, "hr": 3600, "hour": 3600}


def rates_per_second(text):
    return [(match.group(0), float(match.group(1).replace(",", "")) / SECONDS[match.group(2).lower()])
            for match in RATE.finditer(text)]


# Sections whose content is, by heading, not the proposed design.
SET_ASIDE = re.compile(r"alternativ|rejected|not (?:chosen|needed|used)|considered|out of scope|non-goal"
                       r"|left out|leave out|deferred|trigger|future|later|scal(?:e|ing) (?:path|step)|10\s*[x×]"
                       r"|what breaks|when to", re.I)
DUPLICATE_SAFETY = re.compile(
    r"idempot|de-?dup|duplicate|double[- ]send|unique|exactly[- ]once|at[- ](?:most|least)[- ]once"
    r"|skip locked|sent_at|message-id", re.I)


ITEM = re.compile(r"\s*(?:[-*+]\s|\d+[.)]\s|\|)")


def chunks(text):
    """Yield (heading, logical line): wrapped lines are joined; headings, list items and table rows stay apart."""
    heading, current = "", []
    for line in text.splitlines() + [""]:
        title = re.match(r"\s*#+\s*(.*)", line)
        if title or not line.strip() or ITEM.match(line):
            if current:
                yield heading, " ".join(part.strip() for part in current)
            current = [line] if line.strip() and not title else []
            heading = title.group(1) if title else heading
        else:
            current.append(line)


def sentences(text):
    return [part for _, chunk in chunks(text) for part in re.split(r"(?<=[.!?])\s+", chunk) if part.strip()]


def proposed_sentences(text):
    """Sentences outside sections headed as alternatives, rejected or deferred options, or future steps."""
    return [part for heading, chunk in chunks(text) if not SET_ASIDE.search(heading)
            for part in re.split(r"(?<=[.!?])\s+", chunk) if part.strip()]


def changed_sources(cwd, hashes):
    return sorted(name for name, value in hashes.items() if digest(cwd / name) != value)


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
    elif case_id == "stale-main":
        branch = git(cwd, "branch", "--show-current")
        check("task branch created", branch not in ("", "main"), {"branch": branch})
        head = git(cwd, "rev-parse", "HEAD")
        fresh = subprocess.run(["git", "merge-base", "--is-ancestor", context["fresh_base"], "HEAD"], cwd=cwd,
                               capture_output=True, timeout=20).returncode == 0
        check("work starts from the fetched origin/main", fresh, {"head": head, "fresh_base": context["fresh_base"]})
        main = git(cwd, "rev-parse", "refs/heads/main")
        check("local main left alone", main == context["local_main"], {"main": main, "expected": context["local_main"]})
        upstream = subprocess.run(["git", "config", f"branch.{branch}.merge"], cwd=cwd, capture_output=True,
                                  text=True, timeout=20).stdout.strip() if branch else ""
        # Working on main already fails "task branch created"; this check is about the task branch's upstream.
        check("task branch does not track main", branch in ("", "main") or upstream != "refs/heads/main",
              {"branch": branch, "merge": upstream})
        probe = subprocess.run([sys.executable, "-I", "-c",
            'import runpy,sys,json; f=runpy.run_path(sys.argv[1])["slugify"]; print(json.dumps(f("Hello Big World")))',
            str(cwd / "text_utils.py")], capture_output=True, text=True, timeout=10)
        check("slug lowercased", probe.stdout.strip() == '"hello-big-world"', {"stdout": probe.stdout, "stderr": probe.stderr})
    elif case_id in ("design-sizing", "tracking-design"):
        changed = changed_sources(cwd, context["source_hashes"])
        check("source unchanged", not changed, {"changed": changed})
        design = cwd / ".artifacts/design.md"
        text = design.read_text() if design.is_file() else ""
        listed = cwd / ".artifacts/components.json"
        components = json.loads(listed.read_text()) if listed.is_file() else None
        valid = isinstance(components, list) and all(
            isinstance(c, dict) and isinstance(c.get("name"), str) and isinstance(c.get("purpose"), str)
            for c in components)
        heavy = [c for c in components if HEAVY_INFRASTRUCTURE.search(c["name"] + " " + c["purpose"])] if valid else None
        recommended = [part.strip() for part in proposed_sentences(text)
                       if HEAVY_INFRASTRUCTURE.search(part) and not DEFERRED.search(part)]
        check("no infrastructure beyond the stated load", valid and not heavy and not recommended,
              {"components": components, "listed": heavy, "recommended_in_design": recommended})
        # Both fixtures need well under 5/s (about 0.06 emails/s; a few tracking events or polls a second at most);
        # a derived peak is a plausible rate stated as a peak or burst. The given relay or API limits (30/s, 20/s)
        # and an average alone are not a peak.
        estimates = [(found, value) for part in sentences(text) if re.search(r"peak|burst", part, re.I)
                     for found, value in rates_per_second(part) if 0.001 <= value <= 5]
        check("peak rate estimated with units", estimates,
              {"peak_rates": estimates, "all_rates": rates_per_second(text)})
        # Document-level: real designs separate the retry schedule from the duplicate guard.
        check("retries cannot send duplicates",
              re.search(r"retr(?:y|ies|ied|ying)|backoff|next_attempt|attempts", text, re.I) and DUPLICATE_SAFETY.search(text),
              text)
        check("external calls time out", re.search(r"time-?outs?\b", text, re.I), text)
        check("rollback path stated", re.search(
            r"roll[- ]?back|revert|kill[- ]switch|feature flag|(?:disable|turn off|switch off) (?:the )?(?:send|email|sender|poll|poller|sync|webhook)",
            text, re.I), text)
    return checks
