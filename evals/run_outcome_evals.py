"""Compare skill outcomes with fresh enabled/disabled sessions on synthetic fixtures.

Runs cost model usage. Use --list to inspect cases without starting Claude.
Artifacts include synthetic workspaces, transcripts, rubric evidence and metrics.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from claude_session import positive_number, run_session
from outcome_cases import CASES, grade, prepare


SKILLS_ROOT = Path(__file__).resolve().parent.parent
MIN_VERSION = (2, 1, 300)


def snapshot_hash(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            digest.update(str(path.relative_to(root)).encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def session_command(args, query, settings):
    return [
        "claude", "-p", query, "--model", args.model,
        "--max-turns", str(args.max_turns), "--max-budget-usd", str(args.max_budget_usd),
        "--output-format", "stream-json", "--verbose", "--no-session-persistence",
        "--setting-sources", "project", "--settings", json.dumps(settings),
        "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--no-chrome",
        "--permission-mode", "default", "--permission-prompts", "none",
        "--tools", "Read,Write,Edit,Glob,Grep,Bash,Skill",
        "--allowedTools", "Read", "Write", "Edit", "Glob", "Grep", "Skill",
        "Bash(git *)", "Bash(python3 *)", "Bash(node *)", "Bash(ls *)",
        "Bash(cat *)", "Bash(pwd)", "Bash(rg *)", "Bash(mkdir *)",
    ]


def run_arm(case_id, arm, args, destination):
    case = CASES[case_id]
    skill = case["skill"]
    destination.mkdir(parents=True)
    context = prepare(case_id, destination)
    cwd = context["cwd"]
    skill_dir = cwd / ".claude" / "skills" / skill
    shutil.copytree(args.skills_root / skill, skill_dir,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    candidate_hash = snapshot_hash(skill_dir)
    vault = context.get("vault", destination / "vault")
    vault.mkdir(exist_ok=True)
    settings = {
        "disableAllHooks": True, "autoMemoryEnabled": False, "disableBundledSkills": True,
        "skillOverrides": {definition["skill"]: "off" for definition in CASES.values()},
        "env": {"AGENT_VAULT": str(vault), "VAULT_MEMORY_EXCLUDE": "",
                "XDG_CACHE_HOME": str(destination / "cache")},
    }
    settings["skillOverrides"][skill] = "on" if arm == "enabled" else "off"
    command = session_command(args, case["query"], settings)
    (destination / "request.json").write_text(json.dumps({"query": case["query"], "command": command}, indent=2) + "\n")
    env = dict(os.environ, **settings["env"])
    record, events = run_session(command, cwd=cwd, timeout=args.timeout, env=env,
                                 output_dir=destination)
    record.update(type="case", case=case_id, skill=skill, arm=arm,
                  artifacts=str(destination), candidate_sha256=candidate_hash)
    if snapshot_hash(skill_dir) != candidate_hash:
        record["error"] = record["error"] or "skill_snapshot_changed"
    if arm == "disabled" and skill in record["invoked"]:
        record["error"] = record["error"] or "disabled_skill_invoked"
    if record["loaded_skills"] is not None:
        visible = skill in record["loaded_skills"]
        if visible != (arm == "enabled"):
            record["error"] = record["error"] or "skill_visibility_mismatch"
    else:
        record["error"] = record["error"] or "missing_initialization"
    if record["error"]:
        record.update(status="error", checks=[])
    else:
        try:
            checks = grade(case_id, context, events)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            checks = [{"name": "gradeable outcome artifacts", "passed": False,
                       "evidence": f"{type(exc).__name__}: {exc}"}]
        record.update(checks=checks, status="pass" if checks and all(c["passed"] for c in checks) else "fail")
    (destination / "grading.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def summarize(records):
    costs = [r.get("total_cost_usd") for r in records]
    reported = [v for v in costs if isinstance(v, (int, float)) and not isinstance(v, bool)
                and math.isfinite(v) and v >= 0]
    counts = {arm: {status: sum(r["arm"] == arm and r["status"] == status for r in records)
                    for status in ("pass", "fail", "error")} for arm in ("enabled", "disabled")}
    pairs = []
    for case_id in dict.fromkeys(r["case"] for r in records):
        pair = {r["arm"]: r for r in records if r["case"] == case_id}
        if len(pair) == 2 and all(r["status"] != "error" for r in pair.values()):
            pairs.append(pair)
    rates = {arm: sum(p[arm]["status"] == "pass" for p in pairs) / len(pairs) if pairs else None
             for arm in counts}
    tokens = {}
    for arm in counts:
        runs = [r for r in records if r["arm"] == arm]
        tokens[arm] = {}
        for field in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            values = [(r.get("usage") or {}).get(field) for r in runs]
            known = [v for v in values if isinstance(v, int) and not isinstance(v, bool) and v >= 0]
            tokens[arm][field] = sum(known) if len(known) == len(values) else None
    return dict(type="summary", counts=counts, comparable_pairs=len(pairs), pass_rates=rates,
                main_loop_tokens=tokens,
                pass_rate_delta=(rates["enabled"] - rates["disabled"] if pairs else None),
                observed_cost_usd=round(sum(reported), 8) if reported else None,
                cost_missing_runs=len(costs) - len(reported),
                total_cost_usd=round(sum(reported), 8) if len(reported) == len(costs) else None,
                elapsed_seconds={arm: round(sum(r["elapsed_seconds"] for r in records if r["arm"] == arm), 3)
                                 for arm in counts})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", choices=CASES, dest="cases")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--skills-root", type=Path, default=SKILLS_ROOT)
    parser.add_argument("--max-turns", type=int, default=16)
    parser.add_argument("--timeout", type=positive_number, default=180)
    parser.add_argument("--max-budget-usd", type=positive_number, default=0.75)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.max_turns < 1:
        parser.error("--max-turns must be positive")
    if args.list:
        print(json.dumps(CASES, indent=2))
        return 0
    args.skills_root = args.skills_root.resolve()
    selected = list(dict.fromkeys(args.cases or CASES))
    for case_id in selected:
        if not (args.skills_root / CASES[case_id]["skill"] / "SKILL.md").is_file():
            parser.error(f"missing skill for {case_id} in {args.skills_root}")
    try:
        version = subprocess.run(["claude", "--version"], capture_output=True, text=True, check=True, timeout=15).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        parser.error(f"cannot check Claude Code version: {exc}")
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match or tuple(map(int, match.groups())) < MIN_VERSION:
        parser.error("outcome evals require Claude Code >= 2.1.300 (skillOverrides and session controls)")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = (args.output or Path(tempfile.gettempdir()) / f"skill-outcomes-{stamp}").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run(["git", "-C", str(output.parent), "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=15)
    if probe.returncode == 0:
        parser.error("--output must be outside Git worktrees so project instructions cannot contaminate the comparison")
    if output.exists():
        parser.error(f"output already exists: {output}")
    output.mkdir(mode=0o700)
    source_root = args.skills_root
    candidates = output / "candidates"
    for skill in dict.fromkeys(CASES[c]["skill"] for c in selected):
        shutil.copytree(source_root / skill, candidates / skill,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    args.skills_root = candidates
    revision = subprocess.run(["git", "-C", str(source_root), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=15)
    tree = subprocess.run(["git", "-C", str(source_root), "status", "--short"],
                          capture_output=True, text=True, timeout=15)
    records = []
    with (output / "report.jsonl").open("x", encoding="utf-8") as report:
        metadata = dict(type="run", claude_version=version, model=args.model,
                        skills_root=str(source_root), cases=selected,
                        revision=revision.stdout.strip() if revision.returncode == 0 else None,
                        working_tree=tree.stdout if tree.returncode == 0 else None,
                        max_turns=args.max_turns, timeout=args.timeout,
                        max_budget_usd_per_arm=args.max_budget_usd,
                        candidate_sha256={CASES[c]["skill"]: snapshot_hash(args.skills_root / CASES[c]["skill"]) for c in selected})
        (output / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
        report.write(json.dumps(metadata) + "\n")
        for index, case_id in enumerate(selected):
            # Alternate order to reduce a consistent first-run/cache bias.
            arms = ("enabled", "disabled") if index % 2 == 0 else ("disabled", "enabled")
            for arm in arms:
                record = run_arm(case_id, arm, args, output / case_id / arm)
                records.append(record)
                report.write(json.dumps(record) + "\n")
                report.flush()
                print(f"{record['status'].upper():5} {case_id:20} {arm:8} {record['error'] or ''}", flush=True)
        summary = summarize(records)
        report.write(json.dumps(summary) + "\n")
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"Artifacts: {output}")
    failed = any(r["status"] == "error" or (r["arm"] == "enabled" and r["status"] == "fail")
                 for r in records)
    return int(failed or not summary["comparable_pairs"])


if __name__ == "__main__":
    raise SystemExit(main())
