"""Measure installed skill triggering in disposable fixtures.

    evals/build_fixture.sh /tmp/skill-evals
    python3 evals/run_trigger_evals.py /tmp/skill-evals [model] [skill ...]

Uses installed skills and default permissions; plan mode suppresses invocation.
Each case has a disposable checkout and AGENT_VAULT. Reports contain metadata,
not full transcripts. Trigger scores do not measure full workflow compliance.
"""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


EVALS = Path(__file__).resolve().parent
RESULT_FIELDS = (
    "session_id", "subtype", "num_turns", "duration_ms", "duration_api_ms",
    "total_cost_usd", "usage", "modelUsage",
)


def positive_number(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return number


def run_case(query, skill, args):
    started = time.monotonic()
    output, error, returncode = "", None, None
    with tempfile.TemporaryDirectory(prefix="skill-eval-") as case_root:
        name = "agent-skills" if skill == "vault-memory" else "webapp"
        cwd = Path(case_root) / name
        shutil.copytree(args.fixture_root / name, cwd)
        vault = cwd if skill == "vault-memory" else Path(case_root) / "vault"
        command = [
            "claude", "-p", query, "--model", args.model,
            "--max-turns", str(args.max_turns),
            "--output-format", "stream-json", "--verbose",
            "--permission-mode", "default",
            "--settings", json.dumps({"env": {"AGENT_VAULT": str(vault)}}),
        ]
        if args.max_budget_usd is not None:
            command += ["--max-budget-usd", str(args.max_budget_usd)]
        try:
            proc = subprocess.run(
                command, cwd=cwd, capture_output=True, text=True,
                timeout=args.timeout,
            )
            output, returncode = proc.stdout, proc.returncode
            if returncode:
                error = "process_exit"
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout or b""
            if isinstance(output, bytes):
                output = output.decode("utf-8", errors="replace")
            error = "timeout"
        except OSError as exc:
            error = type(exc).__name__

    found, result = [], None
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "result":
            result = event
        if event.get("is_api_error_message"):
            error = error or "api_error"
        if event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use" and block.get("name") == "Skill":
                    found.append(block.get("input", {}).get("skill", "?"))
    if result is None:
        error = error or "missing_result"
    elif result.get("is_error") or str(result.get("subtype", "")).startswith("error"):
        error = error or result.get("subtype") or "session_error"
    elif not result.get("num_turns") and not found:
        error = error or "empty_session"

    record = {field: result.get(field) if result else None for field in RESULT_FIELDS}
    record.update(
        invoked=found, error=error, returncode=returncode,
        elapsed_seconds=round(time.monotonic() - started, 3),
    )
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture_root", type=Path)
    parser.add_argument("model", nargs="?", default="sonnet")
    parser.add_argument("skills", nargs="*")
    parser.add_argument("--max-turns", type=int, default=os.environ.get("EVAL_MAX_TURNS", "6"))
    parser.add_argument("--timeout", type=positive_number, default=400)
    parser.add_argument("--max-budget-usd", type=positive_number,
                        default=os.environ.get("EVAL_MAX_BUDGET_USD"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    parser.add_argument("--report", type=Path,
                        default=Path(".artifacts") / f"trigger-evals-{stamp}.jsonl")
    args = parser.parse_args()
    if args.max_turns < 1:
        parser.error("--max-turns must be a positive integer")

    cases = []
    for path in sorted(EVALS.glob("*.json")):
        if args.skills and path.stem not in args.skills:
            continue
        for index, case in enumerate(json.loads(path.read_text()), 1):
            cases.append((path.stem, index, case))
    if not cases:
        parser.error("no matching eval cases")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    counts = dict(passed=0, failed=0, errors=0, skipped=0)
    observed_cost, cost_reported = 0.0, 0
    with args.report.open("x", encoding="utf-8") as report:
        for skill, index, case in cases:
            expected = case["expected_behavior"][0]
            should = (True if expected.startswith("Invokes") else
                      False if expected.startswith("Does not invoke") else None)
            record = dict(type="case", skill=skill, case=index, model=args.model,
                          expected_trigger=should, max_turns=args.max_turns,
                          max_budget_usd=args.max_budget_usd, timeout=args.timeout)
            if should is None:
                counts["skipped"] += 1
                record.update(status="skipped", error="no_trigger_expectation")
            else:
                record.update(run_case(case["query"], skill, args))
                if record["error"]:
                    counts["errors"] += 1
                    record["status"] = "error"
                else:
                    hit = (skill in record["invoked"]) == should
                    counts["passed" if hit else "failed"] += 1
                    record["status"] = "pass" if hit else "fail"
                cost = record["total_cost_usd"]
                if isinstance(cost, (int, float)) and math.isfinite(cost) and cost >= 0:
                    observed_cost += cost
                    cost_reported += 1
            report.write(json.dumps(record) + "\n")
            report.flush()
            detail = record.get("error") or f"got={record.get('invoked') or '-'}"
            print(f"{record['status'].upper():7} {skill:28} {detail} | {case['query'][:55]}", flush=True)

        completed = counts["passed"] + counts["failed"]
        executed = completed + counts["errors"]
        missing = executed - cost_reported
        summary = dict(
            type="summary", **counts, executed=executed, model=args.model,
            observed_cost_usd=round(observed_cost, 8) if cost_reported else None,
            cost_reported_cases=cost_reported, cost_missing_cases=missing,
            cost_per_completed_eval_usd=(round(observed_cost / completed, 8)
                                         if completed and not missing else None),
        )
        report.write(json.dumps(summary) + "\n")
    print(f"\n{counts['passed']}/{completed} trigger expectations met "
          f"({counts['errors']} errored, {counts['skipped']} skipped; model={args.model})")
    cost_label = f"${observed_cost:.6f}" if cost_reported else "unknown"
    print(f"Reported estimated cost: {cost_label}; {missing} cases missing cost. Report: {args.report}")
    return int(bool(counts["failed"] or counts["errors"] or not completed))


if __name__ == "__main__":
    raise SystemExit(main())
