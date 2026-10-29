"""Exercise the runner's CLI with a local Claude stand-in; no model calls."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


RUNNER = Path(__file__).with_name("run_trigger_evals.py")
CLAUDE = '''#!/usr/bin/env python3
import json, os, pathlib, sys, time
args = sys.argv[1:]
query = json.loads(args[args.index("-p") + 1])
settings = json.loads(args[args.index("--settings") + 1])
vault = pathlib.Path(settings["env"]["AGENT_VAULT"])
assert vault.parent.exists()
assert not pathlib.Path("claimed").exists(), "previous case leaked state"
pathlib.Path("claimed").write_text("claimed")
with open(os.environ["CALL_LOG"], "a") as log:
    log.write(json.dumps({"args": args, "vault": str(vault), "cwd": os.getcwd()}) + "\\n")
print("CLI startup notice", flush=True)
for event in query["events"]:
    print(json.dumps(event), flush=True)
if query.get("sleep"):
    time.sleep(5)
sys.exit(query.get("exit", 0))
'''


def result(cost=0.1, **fields):
    return dict(type="result", subtype="success", is_error=False, num_turns=2,
                total_cost_usd=cost, usage={"input_tokens": 100, "output_tokens": 20},
                modelUsage={"test-model": {"inputTokens": 130, "costUSD": cost}},
                session_id="test-session", **fields)


def invocation():
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Skill", "input": {"skill": "demo"}}
    ]}}


class TriggerRunnerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copy2(RUNNER, self.root / RUNNER.name)
        shutil.copy2(RUNNER.with_name("claude_session.py"), self.root / "claude_session.py")
        (self.root / "fixtures" / "webapp").mkdir(parents=True)
        binary = self.root / "bin"
        binary.mkdir()
        claude = binary / "claude"
        claude.write_text(CLAUDE)
        claude.chmod(0o755)
        self.env = {**os.environ, "PATH": f"{binary}{os.pathsep}{os.environ['PATH']}",
                    "CALL_LOG": str(self.root / "calls.jsonl")}
        self.env.pop("EVAL_MAX_BUDGET_USD", None)
        self.env.pop("EVAL_MAX_TURNS", None)

    def run_cases(self, cases, *options):
        (self.root / "demo.json").write_text(json.dumps(cases))
        proc = subprocess.run(
            [sys.executable, str(self.root / RUNNER.name), str(self.root / "fixtures"),
             "test-model", "demo", "--report", str(self.root / "report.jsonl"), *options],
            env=self.env, capture_output=True, text=True, timeout=10,
        )
        report = self.root / "report.jsonl"
        records = [json.loads(line) for line in report.read_text().splitlines()] if report.exists() else []
        return proc, records

    def case(self, events, expected="Invokes the demo skill", **behavior):
        return {"query": json.dumps(dict(events=events, **behavior)),
                "expected_behavior": [expected]}

    def test_counts_failed_work_cost_and_isolates_each_case(self):
        failed = result(0.3)
        failed.update(subtype="error_max_budget_usd", is_error=True)
        proc, records = self.run_cases([
            self.case([invocation(), result(0.1)]),
            self.case([result(0.2)]),
            self.case([failed], exit=1),
            self.case([], expected="Reviews the relevant behavior"),
        ], "--max-budget-usd", "0.5")
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertEqual([r["status"] for r in records[:-1]], ["pass", "fail", "error", "skipped"])
        summary = records[-1]
        self.assertAlmostEqual(summary["observed_cost_usd"], 0.6)
        self.assertAlmostEqual(summary["cost_per_completed_eval_usd"], 0.3)
        self.assertEqual(summary["cost_missing_cases"], 0)
        self.assertEqual(records[0]["usage"]["input_tokens"], 100)
        self.assertEqual(records[0]["modelUsage"]["test-model"]["inputTokens"], 130)
        self.assertEqual(records[2]["subtype"], "error_max_budget_usd")
        calls = [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]
        self.assertEqual(len(calls), 3)
        self.assertEqual(len({c["cwd"] for c in calls}), 3)
        for call in calls:
            args = call["args"]
            self.assertEqual(args[args.index("--max-budget-usd") + 1], "0.5")
            self.assertNotIn("--bare", args)
            self.assertFalse(Path(call["cwd"]).exists())
            self.assertTrue(call["vault"].startswith(str(Path(call["cwd"]).parent)))
        self.assertFalse((self.root / "fixtures" / "webapp" / "claimed").exists())

    def test_missing_result_is_error_even_after_skill_invocation(self):
        rejected = result(0)
        rejected.update(num_turns=0, result="Credit balance is too low")
        proc, records = self.run_cases([
            self.case([invocation()]),
            self.case([result(None)], expected="Does not invoke the demo skill"),
            self.case([rejected], expected="Does not invoke the demo skill", exit=1),
        ])
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(records[0]["error"], "missing_result")
        self.assertEqual(records[1]["status"], "pass")
        self.assertEqual(records[2]["status"], "error")
        self.assertEqual(records[-1]["observed_cost_usd"], 0)
        self.assertIsNone(records[-1]["cost_per_completed_eval_usd"])
        self.assertEqual(records[-1]["cost_missing_cases"], 2)

    def test_timeout_retains_available_result_but_is_not_scored(self):
        proc, records = self.run_cases([self.case([result(0.2)], sleep=True)], "--timeout", "0.5")
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(records[0]["error"], "timeout")
        self.assertEqual(records[-1]["errors"], 1)
        self.assertAlmostEqual(records[-1]["observed_cost_usd"], 0.2)
        self.assertIsNone(records[-1]["cost_per_completed_eval_usd"])

    def test_invalid_budget_cannot_launch_a_session(self):
        for value in ("0", "-1", "nan", "inf"):
            with self.subTest(value=value):
                proc, records = self.run_cases([self.case([result()])], "--max-budget-usd", value)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(records, [])
                self.assertFalse((self.root / "calls.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
