"""Offline CLI checks: real fixtures and graders, with a local Claude stand-in."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from outcome_cases import CASES, grade, prepare


RUNNER = Path(__file__).with_name("run_outcome_evals.py")
CLAUDE = '''#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys
if "--version" in sys.argv:
    print("2.1.300 (Claude Code)")
    sys.exit(0)
args = sys.argv[1:]
settings = json.loads(args[args.index("--settings") + 1])
skill = next(pathlib.Path(".claude/skills").iterdir()).name
arm = "enabled" if settings["skillOverrides"][skill] == "on" else "disabled"
case = pathlib.Path.cwd().parent.parent.name
mode = json.loads(os.environ.get("FAKE_OUTCOMES", "{} ")).get(case + ":" + arm, "pass")
with open(os.environ["CALL_LOG"], "a") as log:
    log.write(json.dumps({"args": args, "cwd": str(pathlib.Path.cwd()), "arm": arm}) + "\\n")
print(json.dumps(dict(type="system", subtype="init", model="fake-model", skills=[skill] if arm == "enabled" and mode != "hidden" else [])))
def call(name, **fields):
    print(json.dumps({"type":"assistant", "message":{"content":[{"type":"tool_use", "name":name, "input":fields}]}}))
if arm == "enabled":
    call("Skill", skill=skill)
pathlib.Path(".artifacts").mkdir(exist_ok=True)
if case == "assigned-worktree":
    subprocess.run(["git", "fetch", "origin"], check=True, capture_output=True)
    p = pathlib.Path("calendar_app.py")
    p.write_text(p.read_text().replace(" + 1", ""))
elif case == "audit-scope":
    pathlib.Path(".artifacts/audit.md").write_text("api.py:5 accepts an empty email. parse_request({'email': ''}) returns ok True. Specialist delegation unavailable; inspected directly.")
elif case == "memory-recall":
    pathlib.Path(".artifacts/recall.md").write_text("73 seconds; 90-second lease, 17 seconds for retries. Source: claude/notes/project/cedar-current.md dated 2026-10-15.")
    call("Read", file_path=str(pathlib.Path(os.environ["AGENT_VAULT"]) / "claude/notes/project/cedar-current.md"), offset=1, limit=20)
elif case == "query-evidence":
    script = pathlib.Path(".artifacts/probe.py")
    script.write_text("import json, sys\\nfrom pathlib import Path\\nsys.path.insert(0, str(Path(__file__).resolve().parents[1]))\\nimport app\\nout = {}\\nfor name in ('before', 'after'):\\n    db = app.connect()\\n    queries = []\\n    db.set_trace_callback(queries.append)\\n    names = getattr(app, name)(db)\\n    out[name] = dict(query_count=len(queries), queries=queries, names=names)\\n    db.close()\\nprint(json.dumps(out))\\n")
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=True)
    pathlib.Path(".artifacts/probe-output.json").write_text(result.stdout)
    call("Bash", command="python3 .artifacts/probe.py")
if mode == "fail":
    if case == "audit-scope":
        pathlib.Path("api.py").write_text("# unauthorized fix")
    elif case == "query-evidence":
        pathlib.Path(".artifacts/probe-output.json").write_text("invalid JSON")
if mode == "contaminated":
    call("Skill", skill=skill)
print(json.dumps(dict(type="result", subtype="success" if mode != "error" else "error_max_budget_usd", is_error=mode == "error", num_turns=3, total_cost_usd=None if mode == "missing-cost" else 0.1, usage={"input_tokens":100}, modelUsage={"fake-model":{"costUSD":0.1}}, session_id="fake-session")))
'''


class OutcomeRunnerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="outcome-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        binary = self.root / "bin"
        binary.mkdir()
        (binary / "claude").write_text(CLAUDE)
        (binary / "claude").chmod(0o755)
        self.env = dict(os.environ, PATH=f"{binary}{os.pathsep}{os.environ['PATH']}",
                        CALL_LOG=str(self.root / "calls.jsonl"))

    def run_evals(self, *args, outcomes=None):
        env = dict(self.env, FAKE_OUTCOMES=json.dumps(outcomes or {}))
        proc = subprocess.run([sys.executable, str(RUNNER), "--output", str(self.root / "run"),
                               *args], capture_output=True, text=True, env=env, timeout=30)
        report = self.root / "run/report.jsonl"
        records = [json.loads(line) for line in report.read_text().splitlines()] if report.exists() else []
        return proc, records

    def test_pairs_grade_real_artifacts_and_retain_replayable_fixtures(self):
        proc, records = self.run_evals()
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        cases = [r for r in records if r["type"] == "case"]
        self.assertEqual(len(cases), 8)
        self.assertTrue(all(r["status"] == "pass" for r in cases))
        summary = records[-1]
        self.assertEqual(summary["comparable_pairs"], 4)
        self.assertEqual(summary["pass_rate_delta"], 0)
        self.assertEqual(summary["total_cost_usd"], 0.8)
        self.assertEqual(summary["main_loop_tokens"]["enabled"]["input_tokens"], 400)
        self.assertIsNone(summary["main_loop_tokens"]["enabled"]["output_tokens"])
        calls = [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]
        self.assertEqual(len({c["cwd"] for c in calls}), 8)
        for call in calls:
            args = call["args"]
            settings = json.loads(args[args.index("--settings") + 1])
            self.assertTrue(settings["disableAllHooks"])
            self.assertTrue(settings["disableBundledSkills"])
            self.assertEqual(args[args.index("--setting-sources") + 1], "project")
            self.assertIn("--strict-mcp-config", args)
            self.assertNotIn("--dangerously-skip-permissions", args)
            self.assertTrue(Path(call["cwd"]).is_dir())
        for record in cases:
            artifacts = Path(record["artifacts"])
            self.assertTrue((artifacts / "session.jsonl").exists())
            self.assertEqual(len(record["candidate_sha256"]), 64)
            self.assertEqual(record["candidate_sha256"], records[0]["candidate_sha256"][record["skill"]])
            self.assertEqual(record["resolved_model"], "fake-model")
        assigned = self.root / "run/assigned-worktree/enabled/assigned"
        self.assertEqual(subprocess.run(["git", "branch", "--show-current"], cwd=assigned,
                                       capture_output=True, text=True).stdout.strip(), "agent/assigned")

    def test_errors_are_unscored_and_failed_run_cost_is_included(self):
        proc, records = self.run_evals("--case", "audit-scope", outcomes={
            "audit-scope:enabled": "fail", "audit-scope:disabled": "error",
        })
        self.assertEqual(proc.returncode, 1)
        self.assertEqual([r["status"] for r in records if r["type"] == "case"], ["fail", "error"])
        self.assertEqual(records[-1]["comparable_pairs"], 0)
        self.assertIsNone(records[-1]["pass_rate_delta"])
        self.assertEqual(records[-1]["total_cost_usd"], 0.2)

    def test_invalid_artifacts_fail_and_missing_cost_stays_unknown(self):
        proc, records = self.run_evals("--case", "query-evidence", outcomes={
            "query-evidence:enabled": "fail", "query-evidence:disabled": "missing-cost",
        })
        self.assertEqual(proc.returncode, 1)
        case = records[1]
        self.assertEqual(case["status"], "fail")
        self.assertFalse(case["checks"][0]["passed"])
        self.assertEqual(records[-1]["cost_missing_runs"], 1)
        self.assertIsNone(records[-1]["total_cost_usd"])
        self.assertEqual(records[-1]["observed_cost_usd"], 0.1)

    def test_disabled_skill_invocation_invalidates_pair(self):
        proc, records = self.run_evals("--case", "memory-recall", outcomes={
            "memory-recall:disabled": "contaminated",
        })
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(records[2]["error"], "disabled_skill_invoked")
        self.assertEqual(records[-1]["comparable_pairs"], 0)

    def test_existing_output_is_not_overwritten_or_used_for_model_calls(self):
        output = self.root / "run"
        output.mkdir()
        marker = output / "preserve.txt"
        marker.write_text("existing evidence")
        proc, records = self.run_evals("--case", "audit-scope")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("output already exists", proc.stderr)
        self.assertEqual(marker.read_text(), "existing evidence")
        self.assertFalse((self.root / "calls.jsonl").exists())

    def test_missing_skill_visibility_invalidates_apparently_successful_outcome(self):
        proc, records = self.run_evals("--case", "audit-scope", outcomes={
            "audit-scope:enabled": "hidden",
        })
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(records[1]["error"], "skill_visibility_mismatch")
        self.assertEqual(records[1]["checks"], [])
        self.assertEqual(records[-1]["comparable_pairs"], 0)

    def test_list_and_invalid_limits_never_start_a_model(self):
        proc, records = self.run_evals("--list")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(set(json.loads(proc.stdout)), set(CASES))
        self.assertEqual(records, [])
        for value in ("0", "-1", "nan", "inf"):
            proc, records = self.run_evals("--max-budget-usd", value)
            self.assertEqual(proc.returncode, 2)
            self.assertEqual(records, [])
        self.assertFalse((self.root / "calls.jsonl").exists())

    def test_grader_rejects_claimed_query_reduction_without_matching_replay(self):
        context = prepare("query-evidence", self.root)
        cwd = context["cwd"]
        (cwd / ".artifacts/probe.py").write_text('print("{}")')
        (cwd / ".artifacts/probe-output.json").write_text(json.dumps({
            "before": {"query_count": 6, "queries": ["SELECT name"] * 6, "names": []},
            "after": {"query_count": 1, "queries": ["SELECT name"], "names": []},
        }))
        checks = grade("query-evidence", context, [])
        self.assertFalse(next(c["passed"] for c in checks if c["name"].startswith("actual SQL")))
        self.assertFalse(next(c["passed"] for c in checks if c["name"].startswith("customer")))


if __name__ == "__main__":
    unittest.main()
