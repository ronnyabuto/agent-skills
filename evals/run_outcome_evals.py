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
import sys
import tempfile

from claude_session import EFFORT_LEVELS, LIMIT_ERROR, positive_number, run_session
from outcome_cases import CASES, contracts_bytes, grade, prepare, tool_calls, user_prompt


SKILLS_ROOT = Path(__file__).resolve().parent.parent
MIN_VERSION = (2, 1, 300)
# Files whose changes would alter prompts, grading or classification of a resumed run.
HARNESS_FILES = ("run_outcome_evals.py", "outcome_cases.py", "data_workflow_case.py", "claude_session.py")
EX_TEMPFAIL = 75


def snapshot_hash(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            digest.update(str(path.relative_to(root)).encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def session_command(args, query, settings):
    command = [
        "claude", "-p", query, "--model", args.model,
        "--max-turns", str(args.max_turns), "--max-budget-usd", str(args.max_budget_usd),
        "--output-format", "stream-json", "--verbose", "--no-session-persistence",
        "--setting-sources", "project", "--settings", json.dumps(settings),
        "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--no-chrome",
        "--permission-mode", "default", "--permission-prompts", "none",
        "--tools", "Read,Write,Edit,Glob,Grep,Bash,Skill",
        # Plain Bash: python3 already runs arbitrary code, and prefix rules denied ordinary loops,
        # pipes and heredocs in both arms, which scored permission noise as model failures.
        "--allowedTools", "Read", "Write", "Edit", "Glob", "Grep", "Skill", "Bash",
    ]
    if args.effort is not None:
        command += ["--effort", args.effort]
    return command


def run_arm(case_id, run, arm, args, destination):
    case = CASES[case_id]
    skill = case["skill"]
    destination.mkdir(parents=True)
    context = prepare(case_id, destination)
    cwd = context["cwd"]
    skill_dir = cwd / ".claude" / "skills" / skill
    shutil.copytree(args.skills_root / skill, skill_dir,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    candidate_hash = snapshot_hash(skill_dir)
    if arm == "disabled":
        (skill_dir / "SKILL.md").unlink()
    available_hash = snapshot_hash(skill_dir)
    vault = context.get("vault", destination / "vault")
    vault.mkdir(exist_ok=True)
    settings = {
        "disableAllHooks": True, "autoMemoryEnabled": False, "disableBundledSkills": True,
        "skillOverrides": {entry.parent.name: "off" for entry in SKILLS_ROOT.glob("*/SKILL.md")},
        "pluginConfigs": {"cc-plugin-agents-md@builtin": {"options": {"instructionFiles": "managed-only"}}},
        "claudeMdExcludes": ["**/CLAUDE.md", "**/CLAUDE.local.md", "**/AGENTS.md", "**/.claude/rules/**"],
        "env": {"AGENT_VAULT": str(vault), "VAULT_MEMORY_EXCLUDE": "",
                "XDG_CACHE_HOME": str(destination / "cache")},
    }
    settings["skillOverrides"][skill] = "on" if arm == "enabled" else "off"
    command = session_command(args, user_prompt(case_id), settings)
    (destination / "request.json").write_text(json.dumps({"query": user_prompt(case_id), "command": command}, indent=2) + "\n")
    env = dict(os.environ, **settings["env"])
    if args.effort is not None:
        env["CLAUDE_CODE_EFFORT_LEVEL"] = args.effort
    record, events = run_session(command, cwd=cwd, timeout=args.timeout, env=env,
                                 output_dir=destination)
    usage = record.get("usage") or {}
    fields = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    values = [usage.get(field) for field in fields]
    record["reported_tokens"] = sum(values) if all(type(v) is int and v >= 0 for v in values) else None
    calls = tool_calls(events)
    read = any(
        call["name"] == "Read" and f"/{skill}/SKILL.md" in call.get("input", {}).get("file_path", "")
        or call["name"] == "Bash" and f"/{skill}/SKILL.md" in call.get("input", {}).get("command", "")
        for call in calls)
    record.update(type="case", case=case_id, run=run, skill=skill, arm=arm, skill_read=read,
                  artifacts=str(destination), candidate_sha256=candidate_hash, available_sha256=available_hash)
    if snapshot_hash(skill_dir) != available_hash:
        record["error"] = record["error"] or "skill_snapshot_changed"
    if arm == "disabled" and skill in record["invoked"]:
        record["error"] = record["error"] or "disabled_skill_invoked"
    if arm == "disabled" and read:
        record["error"] = record["error"] or "disabled_skill_read"
    if record["loaded_skills"] is not None:
        collection = {entry.parent.name for entry in SKILLS_ROOT.glob("*/SKILL.md")} | {skill}
        expected = [skill] if arm == "enabled" else []
        # Client-provided skills are recorded, not rejected; only this collection's skills are controlled per arm.
        record["other_visible_skills"] = sorted(set(record["loaded_skills"]) - collection)
        if sorted(set(record["loaded_skills"]) & collection) != expected:
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
    for key in dict.fromkeys((r["case"], r.get("run", 1)) for r in records):
        pair = {r["arm"]: r for r in records if (r["case"], r.get("run", 1)) == key}
        if len(pair) == 2 and all(r["status"] != "error" for r in pair.values()):
            pairs.append(pair)
    per_case = {}
    for pair in pairs:
        row = per_case.setdefault(pair["enabled"]["case"], {"comparable_runs": 0, "enabled_passes": 0,
                                                            "disabled_passes": 0})
        row["comparable_runs"] += 1
        for arm in ("enabled", "disabled"):
            row[f"{arm}_passes"] += pair[arm]["status"] == "pass"
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
    overhead = []
    for pair in pairs:
        enabled, disabled = pair["enabled"], pair["disabled"]
        def difference(field):
            values = [record.get(field) for record in (enabled, disabled)]
            return values[0] - values[1] if all(type(v) in (int, float) for v in values) else None
        overhead.append(dict(case=enabled["case"], run=enabled.get("run", 1), elapsed_seconds_delta=difference("elapsed_seconds"),
                             token_delta=difference("reported_tokens"), turn_delta=difference("num_turns")))
    return dict(type="summary", counts=counts, paired_overhead=overhead, comparable_pairs=len(pairs), pass_rates=rates,
                per_case=per_case,
                main_loop_tokens=tokens,
                pass_rate_delta=(rates["enabled"] - rates["disabled"] if pairs else None),
                observed_cost_usd=round(sum(reported), 8) if reported else None,
                cost_missing_runs=len(costs) - len(reported),
                total_cost_usd=round(sum(reported), 8) if len(reported) == len(costs) else None,
                elapsed_seconds={arm: round(sum(r["elapsed_seconds"] for r in records if r["arm"] == arm), 3)
                                 for arm in counts})


def planned_arms(cases, runs=1):
    # Repetitions run in rounds so a slow period affects every case; arm order alternates to
    # reduce a consistent first-run/cache bias.
    return [(case_id, run, arm) for run in range(1, runs + 1) for index, case_id in enumerate(cases)
            for arm in (("enabled", "disabled") if (index + run) % 2 == 1 else ("disabled", "enabled"))]


def arm_dir(output, case_id, run, arm):
    return output / case_id / (arm if run == 1 else f"{arm}-{run}")


def harness_hash():
    digest = hashlib.sha256()
    for name in HARNESS_FILES:
        digest.update(name.encode() + b"\0" + Path(__file__).with_name(name).read_bytes() + b"\0")
    return digest.hexdigest()


def load_resume(parser, args):
    """Restore a run's frozen settings and refuse anything that would change the comparison."""
    output = args.resume.resolve()
    try:
        metadata = json.loads((output / "run.json").read_text())
        lines = (output / "report.jsonl").read_text().splitlines()
    except (OSError, ValueError) as exc:
        parser.error(f"cannot resume {output}: {exc}")
    if metadata.get("harness_sha256") != harness_hash():
        parser.error("cannot resume: the eval harness changed since this run started")
    if metadata.get("contracts_sha256") != hashlib.sha256(contracts_bytes()).hexdigest():
        parser.error("cannot resume: outcome case definitions changed since this run started")
    for skill, expected in metadata["candidate_sha256"].items():
        if snapshot_hash(output / "candidates" / skill) != expected:
            parser.error(f"cannot resume: frozen candidate {skill} changed")
    args.model, args.effort = metadata["model"], metadata["requested_effort"]
    args.max_turns, args.timeout = metadata["max_turns"], metadata["timeout"]
    args.max_budget_usd, args.skills_root = metadata["max_budget_usd_per_arm"], output / "candidates"
    args.runs = metadata.get("runs", 1)
    latest = {}
    for line in lines:
        record = json.loads(line)
        if record.get("type") == "case":
            latest[(record["case"], record.get("run", 1), record["arm"])] = record
    return output, metadata, latest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", choices=CASES, dest="cases")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--effort", choices=EFFORT_LEVELS,
                        help="Pin requested effort for both arms; otherwise keep client defaults")
    parser.add_argument("--skills-root", type=Path, default=SKILLS_ROOT)
    parser.add_argument("--max-turns", type=int, default=16)
    parser.add_argument("--timeout", type=positive_number, default=180)
    parser.add_argument("--max-budget-usd", type=positive_number, default=0.75)
    parser.add_argument("--runs", type=int, default=1,
                        help="Repetitions per arm; each repetition is a separate fresh pair")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resume", type=Path, metavar="RUN_DIR",
                        help="Run only the arms an earlier run did not reach or that stopped at a usage or rate limit")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.max_turns < 1:
        parser.error("--max-turns must be positive")
    if args.runs < 1:
        parser.error("--runs must be positive")
    if args.list:
        print(json.dumps(CASES, indent=2))
        return 0
    if args.resume:
        flags = dict(cases="--case", model="--model", effort="--effort", skills_root="--skills-root",
                     max_turns="--max-turns", timeout="--timeout", max_budget_usd="--max-budget-usd",
                     output="--output", runs="--runs")
        fixed = [flag for name, flag in flags.items() if getattr(args, name) != parser.get_default(name)]
        if fixed:
            parser.error("--resume reuses the run's recorded settings; remove " + ", ".join(fixed))
    else:
        args.skills_root = args.skills_root.resolve()
        # Shared contracts also define cases for skills only the Codex collection still ships.
        selected = list(dict.fromkeys(args.cases or [case_id for case_id in CASES
                                                     if (args.skills_root / CASES[case_id]["skill"] / "SKILL.md").is_file()]))
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
    if args.resume:
        output, metadata, latest = load_resume(parser, args)
        if metadata["claude_version"] != version:
            parser.error(f"cannot resume: run used {metadata['claude_version']}, installed is {version}")
        selected = metadata["cases"]
        pending = [key for key in planned_arms(selected, args.runs)
                   if key not in latest or latest[key].get("error") == LIMIT_ERROR]
        if not pending:
            parser.error(f"nothing to resume in {output}: every arm has a recorded result")
        for case_id, run, arm in pending:
            previous = arm_dir(output, case_id, run, arm)
            if previous.exists():
                # Keep the limited attempt's evidence beside the rerun.
                attempt = 1
                while previous.with_name(f"{previous.name}.limited-{attempt}").exists():
                    attempt += 1
                previous.rename(previous.with_name(f"{previous.name}.limited-{attempt}"))
        report = (output / "report.jsonl").open("a", encoding="utf-8")
        report.write(json.dumps(dict(type="resume", claude_version=version,
                                     resumed_at=datetime.now(timezone.utc).isoformat(),
                                     pending=[f"{c}:{a}" if r == 1 else f"{c}:{a}-{r}"
                                              for c, r, a in pending])) + "\n")
    else:
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
        contract_bytes = contracts_bytes()
        (output / "outcome-contracts.json").write_bytes(contract_bytes)
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
        metadata = dict(contracts_sha256=hashlib.sha256(contract_bytes).hexdigest(), type="run", claude_version=version, model=args.model,
                        requested_effort=args.effort, skills_root=str(source_root), cases=selected,
                        revision=revision.stdout.strip() if revision.returncode == 0 else None,
                        working_tree=tree.stdout if tree.returncode == 0 else None,
                        max_turns=args.max_turns, timeout=args.timeout, runs=args.runs,
                        max_budget_usd_per_arm=args.max_budget_usd, harness_sha256=harness_hash(),
                        candidate_sha256={CASES[c]["skill"]: snapshot_hash(args.skills_root / CASES[c]["skill"]) for c in selected})
        (output / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
        report = (output / "report.jsonl").open("x", encoding="utf-8")
        report.write(json.dumps(metadata) + "\n")
        latest, pending = {}, planned_arms(selected, args.runs)
    limited = None
    with report:
        for case_id, run, arm in pending:
            record = run_arm(case_id, run, arm, args, arm_dir(output, case_id, run, arm))
            latest[(case_id, run, arm)] = record
            report.write(json.dumps(record) + "\n")
            report.flush()
            print(f"{record['status'].upper():5} {case_id:20} {run:3} {arm:8} {record['error'] or ''}", flush=True)
            if record["error"] == LIMIT_ERROR:
                # Every later arm would hit the same limit; stop instead of paying for failures.
                limited = record
                break
        records = [latest[key] for key in planned_arms(selected, args.runs) if key in latest]
        summary = summarize(records)
        summary["unfinished_arms"] = sum(key not in latest or latest[key]["error"] == LIMIT_ERROR
                                         for key in planned_arms(selected, args.runs))
        report.write(json.dumps(summary) + "\n")
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"Artifacts: {output}")
    if limited:
        print(f"Stopped at a usage or rate limit ({limited['limit_evidence']}). After it resets, run:\n"
              f"  python3 {Path(__file__).resolve()} --resume {output}", file=sys.stderr)
        return EX_TEMPFAIL
    failed = any(r["status"] == "error" or (r["arm"] == "enabled" and r["status"] == "fail")
                 for r in records)
    return int(failed or not summary["comparable_pairs"])


if __name__ == "__main__":
    raise SystemExit(main())
