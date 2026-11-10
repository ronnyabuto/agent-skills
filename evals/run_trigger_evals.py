"""Trigger evals: does a fresh headless Claude Code session invoke the expected
skill for each query in evals/<skill>.json?

    evals/build_fixture.sh /tmp/skill-evals
    python3 evals/run_trigger_evals.py /tmp/skill-evals [model] [skill ...]

Tests the skills installed in ~/.claude/skills, so merge description changes
before measuring them. Each case gets its own disposable repo copy.
Each session gets a throwaway AGENT_VAULT through
--settings (settings-file env outranks the process environment), so eval
sessions never archive into the real vault. Sessions run in default
permission mode inside the disposable fixture: plan mode suppresses skill
invocation and would understate triggering. Set EVAL_MAX_TURNS to calibrate
the turn budget for chained workflows.
"""
import json, os, shutil, subprocess, sys, tempfile

EVALS = os.path.dirname(os.path.abspath(__file__))
fixture_root = sys.argv[1]
model = sys.argv[2] if len(sys.argv) > 2 else "sonnet"
only = set(sys.argv[3:])
MAX_TURNS = os.environ.get("EVAL_MAX_TURNS", "6")
if not MAX_TURNS.isdecimal() or int(MAX_TURNS) < 1:
    raise ValueError("EVAL_MAX_TURNS must be a positive integer")


def workspace(skill, case_root):
    name = "agent-skills" if skill == "vault-memory" else "webapp"
    cwd = os.path.join(case_root, name)
    shutil.copytree(os.path.join(fixture_root, name), cwd)
    vault = cwd if skill == "vault-memory" else os.path.join(case_root, "vault")
    return cwd, vault


def skills_invoked(query, skill):
    with tempfile.TemporaryDirectory(prefix="skill-eval-") as case_root:
        cwd, vault = workspace(skill, case_root)
        try:
            proc = subprocess.run(
                ["claude", "-p", query, "--model", model, "--max-turns", MAX_TURNS,
                 "--output-format", "stream-json", "--verbose", "--permission-mode", "default",
                 "--settings", json.dumps({"env": {"AGENT_VAULT": vault}})],
                cwd=cwd, capture_output=True, text=True, timeout=400,
            )
        except subprocess.TimeoutExpired:
            return None
    found, turns, failed = [], 0, proc.returncode != 0
    for line in proc.stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            turns = ev.get("num_turns") or 0
            failed = failed or bool(ev.get("is_error"))
        if ev.get("is_api_error_message"):
            failed = True
        if ev.get("type") != "assistant":
            continue
        for block in ev.get("message", {}).get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == "Skill":
                found.append(block.get("input", {}).get("skill", "?"))
    # API failures may report a synthetic turn; neither those nor sessions
    # that never ran provide evidence about skill triggering.
    return None if failed or (turns == 0 and not found) else found


passed = total = errors = 0
for name in sorted(os.listdir(EVALS)):
    if not name.endswith(".json"):
        continue
    skill = name.removesuffix(".json")
    if only and skill not in only:
        continue
    for case in json.load(open(os.path.join(EVALS, name))):
        should = case["expected_behavior"][0].startswith("Invokes")
        got = skills_invoked(case["query"], skill)
        if got is None:
            errors += 1
            print(f"ERROR {skill:28} session did not run  | {case['query'][:55]}", flush=True)
            continue
        hit = (skill in got) if should else (skill not in got)
        passed += hit
        total += 1
        want = "trigger" if should else "no-trigger"
        print(f"{'PASS' if hit else 'FAIL'}  {skill:28} {want:10} got={got or '-'}  | {case['query'][:55]}", flush=True)

print(f"\n{passed}/{total} trigger expectations met ({errors} errored; model={model}, max_turns={MAX_TURNS})")
