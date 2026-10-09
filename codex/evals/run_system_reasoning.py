#!/usr/bin/env python3
"""Run five isolated Codex cases and retain evidence for human review."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

CASES = [
    ("caching", True, "Our dashboard is slow. Assess whether Redis addresses the bottleneck before changing anything.",
     {"requirements.json": json.dumps({"target_ms": 200, "freshness": "immediate", "observed_ms": 1200, "database_ms": 1100, "plan": "SCAN orders", "rows": 1000000, "query": "SELECT * FROM orders WHERE customer_id = ?", "indexes": []})}),
    ("duplicate-payments", True, "Customers sometimes get charged twice despite disabling the submit button. Investigate the root cause before proposing a fix.",
     {"payments.py": "charges = []\ndef pay(order_id):\n    charges.append(order_id)\n    return {'status': 'paid', 'order': order_id}\nif __name__ == '__main__':\n    pay('order-17')\n    pay('order-17')\n    print({'charges': len(charges), 'orders': charges})\n",
      "README.md": "A client retries POST /pay with the same order after an acknowledgement timeout. The endpoint calls pay(order_id). Requirement: at most one charge per order. Run python3 payments.py for the observed retry scenario. The UI disables the button after the first click.\n"}),
    ("queue-capacity", True, "Background jobs fall behind during bursts. Should another synchronous endpoint move onto the queue? Assess capacity and failure behavior first.",
     {"workload.json": json.dumps({"observed_arrivals_per_second": 120, "workers": 4, "observed_jobs_per_second_per_worker": 15, "burst_seconds": 60, "normal_arrivals_per_second": 30, "queue_age_slo_seconds": 10, "proposed_extra_jobs_per_second": 20})}),
    ("routine-crud", False, "Assess adding a conventional CRUD endpoint for a display-name field following the existing adequate handler pattern.",
     {"handlers.py": "def update_name(database, user_id, name):\n    if not isinstance(name, str) or not name.strip():\n        raise ValueError('name required')\n    database[user_id]['name'] = name\n",
      "README.md": "Existing endpoints use handlers.py validation and per-user database ownership checks in the router. Only a display-name field is requested.\n"}),
    ("known-local-bug", False, "The date picker adds an erroneous +1 to the calendar day count. Explain the targeted correction and checks for leap and non-leap February.",
     {"dates.py": "import calendar\ndef days_in_month(year, month):\n    return calendar.monthrange(year, month)[1] + 1\n"}),
]


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and ".git" not in p.parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--case", choices=[case[0] for case in CASES])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    reports = []
    for name, expected, query, files in CASES:
        if args.case and args.case != name:
            continue
        fixture = args.output / name
        fixture.mkdir()
        for filename, content in files.items():
            (fixture / filename).write_text(content)
        subprocess.run(["git", "init", "-q", "-b", "main", str(fixture)], check=True)
        before = hashes(fixture)
        command = ["codex", "--no-daemon", "exec", "--json", "--ephemeral", "--sandbox", "read-only", "-C", str(fixture)]
        command += [query + "\nRead-only assessment: inspect the supplied fixture, run harmless probes if useful, and do not modify files or delegate."]
        result = subprocess.run(command, capture_output=True, text=True, timeout=240)
        (args.output / (fixture.name + ".jsonl")).write_text(result.stdout)
        (args.output / (fixture.name + ".stderr")).write_text(result.stderr)
        events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
        finals = [event["item"].get("text", "") for event in events if event.get("type") == "item.completed" and event.get("item", {}).get("type") == "agent_message"]
        (args.output / (fixture.name + ".answer.md")).write_text("\n\n".join(finals))
        error = result.returncode != 0 or any(event.get("type") in ("error", "turn.failed") for event in events)
        commands = [event["item"].get("command", "") for event in events if event.get("type") == "item.completed" and event.get("item", {}).get("type") == "command_execution"]
        invoked = any("system-reasoning/SKILL.md" in command for command in commands)
        report = {"case": name, "error": error, "expected_trigger": expected, "skill_read": invoked, "fixture_unchanged": before == hashes(fixture), "behavior_review": "pending", "usage": [event.get("usage") for event in events if event.get("type") == "turn.completed"]}
        reports.append(report)
        print(json.dumps(report), flush=True)
    (args.output / "summary.json").write_text(json.dumps(reports, indent=2) + "\n")


if __name__ == "__main__":
    main()
