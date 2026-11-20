"""Offline CLI checks: real fixtures and graders, with a local Claude stand-in."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from claude_session import limit_signal
import outcome_cases
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
    log.write(json.dumps({"args": args, "cwd": str(pathlib.Path.cwd()), "arm": arm, "effort": os.environ.get("CLAUDE_CODE_EFFORT_LEVEL")}) + "\\n")
print(json.dumps(dict(type="system", subtype="init", model="fake-model", skills=([skill] if arm == "enabled" and mode != "hidden" else []) + (["new-feature"] if mode == "extra-skill" else []) + ["doctor"])))
if mode == "limit":
    print(json.dumps(dict(type="system", subtype="api_retry", attempt=10, max_retries=10, retry_delay_ms=0, error_status=429, error="rate_limit")))
    print(json.dumps(dict(type="result", subtype="success", is_error=True, api_error_status=429, num_turns=0, result="You've hit your session limit", total_cost_usd=0.0, usage={"input_tokens":0}, modelUsage={}, session_id="fake-session")))
    sys.exit(1)
def call(name, **fields):
    print(json.dumps({"type":"assistant", "message":{"content":[{"type":"tool_use", "name":name, "input":fields}]}}))
if arm == "enabled":
    call("Skill", skill=skill)
pathlib.Path(".artifacts").mkdir(exist_ok=True)
if case == "assigned-worktree":
    subprocess.run(["git", "fetch", "origin"], check=True, capture_output=True)
    p = pathlib.Path("calendar_app.py")
    p.write_text(p.read_text().replace(" + 1", ""))
elif case == "memory-recall":
    pathlib.Path(".artifacts/recall.md").write_text("73 seconds; 90-second lease, 17 seconds for retries. Source: claude/notes/project/cedar-current.md dated 2026-10-15.")
    call("Read", file_path=str(pathlib.Path(os.environ["AGENT_VAULT"]) / "claude/notes/project/cedar-current.md"), offset=1, limit=20)
elif case == "stale-main":
    for command in (["git", "fetch", "-q", "origin"], ["git", "switch", "-q", "--no-track", "-c", "agent/slug", "origin/main"]):
        subprocess.run(command, check=True, capture_output=True)
    pathlib.Path("text_utils.py").write_text("def slugify(title):\\n    return '-'.join(title.lower().split())\\n")
elif case == "tracking-design":
    pathlib.Path(".artifacts/design.md").write_text("About 1,200 status changes a day; peak about 2 webhooks per minute. Each webhook upserts by (shipment_id, event_id), so retried deliveries are idempotent and duplicates are ignored. Carrier API calls use a 5 s timeout. Roll back by disabling the webhook and returning to manual refresh.")
    pathlib.Path(".artifacts/components.json").write_text(json.dumps([{"name": "carrier_webhook endpoint", "purpose": "receive status events"}]))
elif case == "design-sizing":
    pathlib.Path(".artifacts/design.md").write_text("About 2,000 status emails a day; peak about 0.3 emails per minute. Send from an outbox table with retry and backoff; a unique (order_id, status) key prevents duplicates. SMTP calls use a 10 s timeout. Roll back by disabling the sender.")
    pathlib.Path(".artifacts/components.json").write_text(json.dumps([{"name": "email_outbox table", "purpose": "durable send state"}]))
if mode == "fail" and case == "memory-recall":
    pathlib.Path(".artifacts/recall.md").write_text("The Cedar sync window is 120 seconds to batch writes.")
if mode == "file-read":
    call("Read", file_path=str(pathlib.Path.cwd().parents[2] / "candidates" / skill / "SKILL.md"), limit=10)
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
        target = [] if "--resume" in args else ["--output", str(self.root / "run")]
        proc = subprocess.run([sys.executable, str(RUNNER), *target, *args],
                              capture_output=True, text=True, env=env, timeout=30)
        report = self.root / "run/report.jsonl"
        records = [json.loads(line) for line in report.read_text().splitlines()] if report.exists() else []
        return proc, records

    def test_pairs_grade_real_artifacts_and_retain_replayable_fixtures(self):
        proc, records = self.run_evals()
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        cases = [r for r in records if r["type"] == "case"]
        self.assertEqual(len(cases), 2 * len(CASES))
        self.assertTrue(all(r["status"] == "pass" for r in cases))
        summary = records[-1]
        self.assertEqual(summary["comparable_pairs"], len(CASES))
        self.assertIsNone(records[0]["requested_effort"])
        overhead = records[-1]["paired_overhead"]
        self.assertEqual(len(overhead), len(CASES))
        self.assertTrue(all(row["turn_delta"] == 0 for row in overhead))
        self.assertTrue(all(row["token_delta"] is None for row in overhead))
        saved = self.root / "run/outcome-contracts.json"
        self.assertTrue(saved.is_file())
        self.assertEqual(len(records[0]["contracts_sha256"]), 64)
        contracts = json.loads(saved.read_text())
        for record in (r for r in records if r["type"] == "case"):
            request = json.loads((Path(record["artifacts"]) / "request.json").read_text())
            definition = contracts[record["case"]]
            expected = "\n\n".join(part for part in (definition["query"], definition["deliverable"]) if part)
            self.assertEqual(request["query"], expected)
            self.assertTrue(any(expected in arg for arg in request["command"]))
        self.assertEqual(summary["pass_rate_delta"], 0)
        self.assertEqual(summary["total_cost_usd"], round(0.2 * len(CASES), 8))
        self.assertEqual(summary["main_loop_tokens"]["enabled"]["input_tokens"], 100 * len(CASES))
        self.assertIsNone(summary["main_loop_tokens"]["enabled"]["output_tokens"])
        calls = [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]
        self.assertEqual(len({c["cwd"] for c in calls}), 2 * len(CASES))
        for call in calls:
            args = call["args"]
            self.assertNotIn("--effort", args)
            settings = json.loads(args[args.index("--settings") + 1])
            self.assertTrue(settings["disableAllHooks"])
            self.assertTrue(settings["disableBundledSkills"])
            self.assertEqual(settings["pluginConfigs"]["cc-plugin-agents-md@builtin"]["options"]["instructionFiles"], "managed-only")
            self.assertIn("**/CLAUDE.md", settings["claudeMdExcludes"])
            self.assertIn("**/AGENTS.md", settings["claudeMdExcludes"])
            enabled = [name for name, value in settings["skillOverrides"].items() if value == "on"]
            self.assertEqual(len(enabled), 1 if call["arm"] == "enabled" else 0)
            case = Path(call["cwd"]).parent.parent.name
            others = {name: value for name, value in settings["skillOverrides"].items() if name != CASES[case]["skill"]}
            self.assertIn("vault-memory", settings["skillOverrides"])
            self.assertEqual(set(others.values()), {"off"})
            self.assertEqual(args[args.index("--setting-sources") + 1], "project")
            self.assertIn("--strict-mcp-config", args)
            self.assertNotIn("--dangerously-skip-permissions", args)
            approved = args[args.index("--allowedTools") + 1:]
            self.assertIn("Bash", approved, "prefix-only Bash rules deny loops and pipes in both arms")
            self.assertTrue(Path(call["cwd"]).is_dir())
        for record in cases:
            artifacts = Path(record["artifacts"])
            self.assertTrue((artifacts / "session.jsonl").exists())
            self.assertEqual(len(record["candidate_sha256"]), 64)
            self.assertEqual(record["candidate_sha256"], records[0]["candidate_sha256"][record["skill"]])
            self.assertEqual(record["resolved_model"], "fake-model")
            artifacts = Path(record["artifacts"])
            project = "assigned" if record["case"] == "assigned-worktree" else "project"
            entry = artifacts / project / ".claude/skills" / record["skill"] / "SKILL.md"
            self.assertEqual(entry.exists(), record["arm"] == "enabled")
            self.assertEqual(len(record["available_sha256"]), 64)
        assigned = self.root / "run/assigned-worktree/enabled/assigned"
        self.assertEqual(subprocess.run(["git", "branch", "--show-current"], cwd=assigned,
                                       capture_output=True, text=True).stdout.strip(), "agent/assigned")

    def test_errors_are_unscored_and_failed_run_cost_is_included(self):
        proc, records = self.run_evals("--case", "memory-recall", outcomes={
            "memory-recall:enabled": "fail", "memory-recall:disabled": "error",
        })
        self.assertEqual(proc.returncode, 1)
        self.assertEqual([r["status"] for r in records if r["type"] == "case"], ["fail", "error"])
        self.assertEqual(records[-1]["comparable_pairs"], 0)
        self.assertIsNone(records[-1]["pass_rate_delta"])
        self.assertEqual(records[-1]["total_cost_usd"], 0.2)

    def test_invalid_artifacts_fail_and_missing_cost_stays_unknown(self):
        proc, records = self.run_evals("--case", "memory-recall", outcomes={
            "memory-recall:enabled": "fail", "memory-recall:disabled": "missing-cost",
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

    def test_disabled_skill_file_read_invalidates_apparently_successful_outcome(self):
        proc, records = self.run_evals("--case", "memory-recall", outcomes={"memory-recall:disabled": "file-read"})
        self.assertEqual(proc.returncode, 1)
        disabled = next(r for r in records if r.get("arm") == "disabled")
        self.assertEqual(disabled["error"], "disabled_skill_read")
        entry = Path(disabled["artifacts"]) / "project/.claude/skills/vault-memory/SKILL.md"
        self.assertFalse(entry.exists())
        self.assertEqual(records[-1]["comparable_pairs"], 0)

    def test_naming_the_deleted_entrypoint_is_not_a_read(self):
        # A real baseline ran `cat .claude/skills/vault-memory/SKILL.md 2>/dev/null` in the disabled arm.
        from run_outcome_evals import skill_entry_referenced
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory, "project")
            (cwd / ".claude/skills/vault-memory").mkdir(parents=True)
            frozen = Path(directory, "candidates/vault-memory")
            frozen.mkdir(parents=True)
            (frozen / "SKILL.md").write_text("instructions")
            bash = lambda command: {"name": "Bash", "input": {"command": command}}
            self.assertFalse(skill_entry_referenced(
                bash("cat .claude/skills/vault-memory/SKILL.md 2>/dev/null | head -60"), "vault-memory", cwd))
            self.assertTrue(skill_entry_referenced(
                bash("head -40 ../candidates/vault-memory/SKILL.md"), "vault-memory", cwd))
            self.assertTrue(skill_entry_referenced(
                {"name": "Read", "input": {"file_path": str(frozen / "SKILL.md")}}, "vault-memory", cwd))

    def test_client_provided_skills_are_recorded_without_invalidating(self):
        proc, records = self.run_evals("--case", "memory-recall")
        arms = [r for r in records if r.get("type") == "case"]
        self.assertTrue(all(r["error"] is None for r in arms))
        self.assertTrue(all(r["other_visible_skills"] == ["doctor"] for r in arms))


    def test_existing_output_is_not_overwritten_or_used_for_model_calls(self):
        output = self.root / "run"
        output.mkdir()
        marker = output / "preserve.txt"
        marker.write_text("existing evidence")
        proc, records = self.run_evals("--case", "memory-recall")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("output already exists", proc.stderr)
        self.assertEqual(marker.read_text(), "existing evidence")
        self.assertFalse((self.root / "calls.jsonl").exists())

    def test_skill_visibility_mismatch_invalidates_apparently_successful_outcome(self):
        # Hidden candidate in the enabled arm, or another collection skill visible beside it.
        for mode in ("hidden", "extra-skill"):
            with self.subTest(mode=mode):
                shutil.rmtree(self.root / "run", ignore_errors=True)
                proc, records = self.run_evals("--case", "memory-recall", outcomes={"memory-recall:enabled": mode})
                self.assertEqual(proc.returncode, 1)
                self.assertEqual(records[1]["error"], "skill_visibility_mismatch")
                self.assertEqual(records[1]["checks"], [])
                self.assertEqual(records[-1]["comparable_pairs"], 0)
    def test_list_never_starts_a_model(self):
        proc, records = self.run_evals("--list")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(set(json.loads(proc.stdout)), set(CASES))
        self.assertEqual(records, [])
        self.assertFalse((self.root / "calls.jsonl").exists())
    def test_explicit_model_and_effort_reach_both_arms(self):
        self.env["CLAUDE_CODE_EFFORT_LEVEL"] = "high"
        proc, records = self.run_evals("--case", "memory-recall", "--model", "claude-opus-5-5",
                                       "--effort", "medium")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(records[0]["model"], "claude-opus-5-5")
        self.assertEqual(records[0]["requested_effort"], "medium")
        calls = [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]
        self.assertEqual({c["arm"] for c in calls}, {"enabled", "disabled"})
        for call in calls:
            self.assertEqual(call["effort"], "medium")
            self.assertEqual(call["args"][call["args"].index("--model") + 1], "claude-opus-5-5")
            self.assertEqual(call["args"][call["args"].index("--effort") + 1], "medium")

    def test_runs_repeat_fresh_pairs_and_count_passes_per_case(self):
        proc, records = self.run_evals("--case", "design-sizing", "--case", "memory-recall", "--runs", "3",
                                       outcomes={"memory-recall:enabled": "fail"})
        self.assertEqual(proc.returncode, 1, proc.stderr)
        arms = [r for r in records if r["type"] == "case"]
        self.assertEqual(sorted((r["case"], r["run"], r["arm"]) for r in arms),
                         sorted((c, n, a) for c in ("design-sizing", "memory-recall") for n in (1, 2, 3)
                                for a in ("enabled", "disabled")))
        self.assertEqual(len({r["artifacts"] for r in arms}), 12)
        self.assertEqual(records[0]["runs"], 3)
        summary = records[-1]
        self.assertEqual(summary["comparable_pairs"], 6)
        self.assertEqual(summary["per_case"]["memory-recall"],
                         {"comparable_runs": 3, "enabled_passes": 0, "disabled_passes": 3})
        self.assertEqual(summary["per_case"]["design-sizing"],
                         {"comparable_runs": 3, "enabled_passes": 3, "disabled_passes": 3})
        first = [(r["case"], r["arm"]) for r in arms if r["run"] == 1][:1]
        second = [(r["case"], r["arm"]) for r in arms if r["run"] == 2][:1]
        self.assertNotEqual(first, second, "arm order alternates between rounds")


    def test_resume_completes_a_limited_repetition(self):
        proc, records = self.run_evals("--case", "memory-recall", "--runs", "2",
                                       outcomes={"memory-recall:disabled": "limit"})
        self.assertEqual(proc.returncode, 75, proc.stderr)
        proc, records = self.run_evals("--resume", str(self.root / "run"), "--runs", "3")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--runs", proc.stderr)
        self.env["FAKE_OUTCOMES"] = "{}"
        proc, records = self.run_evals("--resume", str(self.root / "run"))
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        resume = next(r for r in records if r["type"] == "resume")
        self.assertEqual(resume["pending"], ["memory-recall:disabled", "memory-recall:disabled-2",
                                             "memory-recall:enabled-2"])
        self.assertEqual(records[-1]["comparable_pairs"], 2)
        self.assertTrue((self.root / "run/memory-recall/disabled.limited-1").is_dir())


    def calls(self):
        log = self.root / "calls.jsonl"
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def test_limit_stops_the_run_and_resume_runs_only_unfinished_arms(self):
        proc, records = self.run_evals("--case", "memory-recall", "--case", "design-sizing",
                                       outcomes={"memory-recall:disabled": "limit"})
        self.assertEqual(proc.returncode, 75, proc.stderr)
        self.assertIn("--resume", proc.stderr)
        arms = [r for r in records if r["type"] == "case"]
        self.assertEqual([(r["arm"], r["status"], r["error"]) for r in arms],
                         [("enabled", "pass", None), ("disabled", "error", "limit_reached")])
        self.assertEqual(arms[1]["limit_evidence"], "api_error_status 429")
        self.assertEqual(records[-1]["unfinished_arms"], 3)
        self.assertEqual(len(self.calls()), 2)

        proc, records = self.run_evals("--resume", str(self.root / "run"))
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertEqual(len(self.calls()), 5)
        resume = next(r for r in records if r["type"] == "resume")
        self.assertEqual(resume["pending"], ["memory-recall:disabled", "design-sizing:disabled",
                                             "design-sizing:enabled"])
        summary = records[-1]
        self.assertEqual(summary["comparable_pairs"], 2)
        self.assertEqual(summary["unfinished_arms"], 0)
        self.assertTrue((self.root / "run/memory-recall/disabled.limited-1/session.jsonl").is_file())
        self.assertEqual(json.loads((self.root / "run/summary.json").read_text()), summary)

    def test_resume_refuses_changed_inputs_and_overriding_flags(self):
        self.run_evals("--case", "memory-recall", outcomes={"memory-recall:enabled": "limit"})
        before = len(self.calls())
        proc, _ = self.run_evals("--resume", str(self.root / "run"), "--model", "opus")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--model", proc.stderr)
        (self.root / "run/candidates/vault-memory/SKILL.md").write_text("edited after the run started")
        proc, _ = self.run_evals("--resume", str(self.root / "run"))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("frozen candidate", proc.stderr)
        self.assertEqual(len(self.calls()), before)

    def test_resume_with_nothing_unfinished_starts_no_model(self):
        self.run_evals("--case", "memory-recall")
        before = len(self.calls())
        proc, _ = self.run_evals("--resume", str(self.root / "run"))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("nothing to resume", proc.stderr)
        self.assertEqual(len(self.calls()), before)

REJECTED_ALTERNATIVES = (Path(__file__).parent / "fixtures/graders/design-sizing-rejected-alternatives.md").read_text()


def failing(results):
    return {check["name"] for check in results if not check["passed"]}


class GraderNearMissTest(unittest.TestCase):
    """Each check must reject a plausible near miss while the case's other checks still pass."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="grader-tests-")
        self.addCleanup(self.temp.cleanup)
        self.count = 0

    def grade(self, case_id, files, events=(), edit=None):
        self.count += 1
        root = Path(self.temp.name) / str(self.count)
        root.mkdir()
        context = prepare(case_id, root)
        for name, content in files.items():
            (context["cwd"] / name).write_text(content if isinstance(content, str) else json.dumps(content))
        if edit:
            edit(context)
        return grade(case_id, context, list(events))

    def assertNearMisses(self, case_id, good, misses):
        self.assertEqual(failing(self.grade(case_id, good)), set(), "the reference answer must pass")
        for label, (files, expected) in misses.items():
            with self.subTest(case=case_id, miss=label):
                self.assertEqual(failing(self.grade(case_id, {**good, **files})), {expected})

    def test_design_sizing(self):
        part = dict(peak="About 2,000 status emails a day; peak about 10 emails per minute.",
                    retry=" Send from an outbox table and retry failures with exponential backoff;",
                    dedupe=" a unique (order_id, status) key prevents duplicate sends.",
                    timeout=" Each SMTP call has a 10 s timeout.",
                    rollback=" Roll back by disabling the sender flag.",
                    deferred=" Consider Redis only if the outbox backlog stays above 1,000 rows for an hour.")
        design = lambda **changes: "".join({**part, **changes}.values())
        broker = "\n- A message broker (RabbitMQ/Redis/SQS): extra infrastructure to run for ~2k emails/day.\n"
        good = {".artifacts/design.md": design(),
                ".artifacts/components.json": [{"name": "email_outbox table", "purpose": "durable send state"}]}
        self.assertEqual(failing(self.grade("design-sizing", {**good, ".artifacts/design.md":
                                                              design() + "\n## Rejected alternatives" + broker})), set())
        self.assertNearMisses("design-sizing", good, {
            "relay limit copied as the estimate": (
                {".artifacts/design.md": design(peak="The relay accepts 30 messages per second.")},
                "peak rate estimated with units"),
            "average without a peak": (
                {".artifacts/design.md": design(peak="About 2,000 emails a day, roughly 200/hour on average.")},
                "peak rate estimated with units"),
            "heavy component listed": (
                {".artifacts/components.json": [{"name": "Kafka cluster", "purpose": "status event stream"}]},
                "no infrastructure beyond the stated load"),
            "heavy component only in the prose": (
                {".artifacts/design.md": design() + "\nPublish status events to Redis streams for the mailer."},
                "no infrastructure beyond the stated load"),
            "broker listed outside a rejected section": (
                {".artifacts/design.md": design() + "\n## Messaging" + broker},
                "no infrastructure beyond the stated load"),
            "retries with no duplicate guard": (
                {".artifacts/design.md": design(dedupe=" the relay sends them.")}, "retries cannot send duplicates"),
            "no timeout on the relay call": ({".artifacts/design.md": design(timeout="")}, "external calls time out"),
            "no way back": ({".artifacts/design.md": design(rollback="")}, "rollback path stated"),
            "code edited during a design-only task": ({"app.py": "# changed"}, "source unchanged"),
        })
        # A real Opus 5.5 baseline: the earlier keyword grader wrongly failed its rejected-alternatives
        # section and its duplicate guard; the gaps it really has are an average without a peak,
        # no timeout on the relay call and no rollback path.
        self.assertEqual(failing(self.grade("design-sizing", {**good, ".artifacts/design.md": REJECTED_ALTERNATIVES})),
                         {"peak rate estimated with units", "external calls time out", "rollback path stated"})
        # Excerpts from later real answers that earlier versions of the grader misread.
        wrapped_burst = ("2,000 emails/day is about 0.06 messages/second on average. Even a 10× burst is\n"
                         "under 1 msg/s, far below the relay's 30 msg/s.")
        deferral_table = ("## What is deliberately left out, and the trigger to add it\n\n| Component | Trigger |\n|---|---|\n"
                          "| Message broker / queue service (RabbitMQ, SQS, Redis) | Sustained enqueue rate above ~50/s |\n")
        for label, text in (("peak sentence wrapped across lines", design(peak=wrapped_burst)),
                            ("broker deferred behind a trigger", design() + "\n\n" + deferral_table)):
            with self.subTest(real=label):
                self.assertEqual(failing(self.grade("design-sizing", {**good, ".artifacts/design.md": text})), set())
        with self.assertRaises(ValueError):
            self.grade("design-sizing", {**good, ".artifacts/components.json": "not json"})


    def test_memory_recall(self):
        answer = ("73 seconds; 90-second lease, 17 seconds for retries. "
                  "Source: claude/notes/project/cedar-current.md dated 2026-10-15.")
        read = lambda limit: {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {
            "file_path": "/vault/claude/notes/project/cedar-current.md", "limit": limit}}]}}
        self.assertEqual(failing(self.grade("memory-recall", {".artifacts/recall.md": answer}, [read(20)])), set())
        for label, text, events, expected in (
                ("unbounded read", answer, [read(None)], "bounded source retrieval observed"),
                ("superseded value presented", answer + " The window is 120 seconds.", [read(20)],
                 "superseded decision excluded"),
                ("source without date", answer.replace(" dated 2026-10-15", ""), [read(20)], "source and date cited")):
            with self.subTest(miss=label):
                self.assertEqual(failing(self.grade("memory-recall", {".artifacts/recall.md": text}, events)), {expected})

    def test_assigned_worktree(self):
        def session(*steps):
            def run(context):
                cwd = context["cwd"]
                if "fetch" in steps:
                    subprocess.run(["git", "fetch", "-q", "origin"], cwd=cwd, check=True)
                if "fix" in steps:
                    source = cwd / "calendar_app.py"
                    source.write_text(source.read_text().replace(" + 1", ""))
                if "switch" in steps:
                    subprocess.run(["git", "switch", "-q", "-c", "agent/other"], cwd=cwd, check=True)
                if "touch-main" in steps:
                    (context["main"] / "calendar_app.py").write_text("# edited in the wrong checkout")
            return run
        self.assertEqual(failing(self.grade("assigned-worktree", {}, edit=session("fetch", "fix"))), set())
        for steps, expected in ((("fix",), "fresh base retained"),
                                (("fetch",), "calendar outcomes corrected"),
                                (("fetch", "fix", "switch"), "assigned branch and worktree preserved"),
                                (("fetch", "fix", "touch-main"), "main checkout untouched")):
            with self.subTest(steps=steps):
                self.assertEqual(failing(self.grade("assigned-worktree", {}, edit=session(*steps))), {expected})



    def test_stale_main(self):
        def session(*steps):
            def run(context):
                cwd = context["cwd"]
                if "fetch" in steps:
                    subprocess.run(["git", "fetch", "-q", "origin"], cwd=cwd, check=True)
                if "pull-main" in steps:
                    subprocess.run(["git", "merge", "-q", "--ff-only", "origin/main"], cwd=cwd, check=True)
                base = "origin/main" if "fetch" in steps else "main"
                if "branch" in steps:
                    subprocess.run(["git", "switch", "-q", "--no-track", "-c", "agent/slug", base], cwd=cwd, check=True)
                if "tracking-branch" in steps:
                    subprocess.run(["git", "switch", "-q", "-c", "agent/slug", "--track", "origin/main"], cwd=cwd, check=True)
                (cwd / "text_utils.py").write_text("def slugify(title):\n    return '-'.join(title.lower().split())\n")
            return run
        self.assertEqual(failing(self.grade("stale-main", {}, edit=session("fetch", "branch"))), set())
        for steps, expected in ((("fetch",), {"task branch created", "work starts from the fetched origin/main"}),
                                (("branch",), {"work starts from the fetched origin/main"}),
                                (("fetch", "pull-main", "branch"), {"local main left alone"}),
                                (("fetch", "tracking-branch"), {"task branch does not track main"})):
            with self.subTest(steps=steps):
                self.assertEqual(failing(self.grade("stale-main", {}, edit=session(*steps))), expected)

    def test_tracking_design_uses_the_design_rubric(self):
        good = {".artifacts/design.md": ("About 1,200 status changes a day; peak about 2 webhooks per minute. Each "
                                         "webhook upserts by (shipment_id, event_id), so retried deliveries are "
                                         "idempotent. Carrier API calls use a 5 s timeout. Roll back by disabling "
                                         "the webhook and returning to polling."),
                ".artifacts/components.json": [{"name": "webhook endpoint", "purpose": "receive status events"}]}
        self.assertNearMisses("tracking-design", good, {
            "carrier limit copied as the estimate": (
                {".artifacts/design.md": good[".artifacts/design.md"].replace(
                    "peak about 2 webhooks per minute", "the API allows 20 requests per second")},
                "peak rate estimated with units"),
            "queue cluster added": (
                {".artifacts/components.json": [{"name": "Kafka topic", "purpose": "status events"}]},
                "no infrastructure beyond the stated load"),
            "no way back": ({".artifacts/design.md": good[".artifacts/design.md"].split(" Roll back")[0]},
                            "rollback path stated"),
        })



class LimitSignalTest(unittest.TestCase):
    def test_only_error_text_or_rate_limit_retries_count(self):
        answer = {"type": "result", "subtype": "success", "is_error": False,
                  "result": "The rates client ignores the upstream rate limit."}
        self.assertIsNone(limit_signal([answer], answer))
        failed = dict(answer, is_error=True, result="You've hit your weekly limit · resets Mon 12:00am")
        self.assertEqual(limit_signal([failed], failed), "hit your weekly limit")
        retry = {"type": "system", "subtype": "api_retry", "error": "rate_limit", "error_status": 429}
        crashed = {"type": "result", "subtype": "error_during_execution", "is_error": True, "errors": []}
        self.assertEqual(limit_signal([retry, crashed], crashed), "api_retry rate_limit")
        overloaded = dict(retry, error="overloaded", error_status=529)
        self.assertIsNone(limit_signal([overloaded, crashed], crashed))


if __name__ == "__main__":
    unittest.main()
