"""Run bounded Claude sessions and preserve errors separately from outcome scores."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import time


EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")


RESULT_FIELDS = (
    "session_id", "subtype", "num_turns", "duration_ms", "duration_api_ms",
    "total_cost_usd", "usage", "modelUsage", "api_error_status",
)

# Plan, spend and API rate limits end a session without saying anything about the
# skill. Claude Code already retries transient 429/529 with backoff, so a session
# that still fails on one is resumable later, not a scored outcome.
LIMIT_ERROR = "limit_reached"
LIMIT_TEXT = re.compile(
    r"hit your [\w-]+ limit|usage limit|spend limit|credit balance is too low"
    r"|request rejected \(429\)|temporarily limiting requests|rate limit", re.I)


def limit_signal(events, result):
    """Return evidence that a failed session stopped at a usage or rate limit."""
    if result and result.get("api_error_status") == 429:
        return "api_error_status 429"
    texts = []
    # A normal answer can discuss rate limits; only error text is evidence.
    if result and result.get("is_error"):
        texts += [str(result.get("result") or "")] + [str(e) for e in result.get("errors") or []]
    for event in events:
        if event.get("is_api_error_message"):
            texts += [str(block.get("text", "")) for block in event.get("message", {}).get("content", [])]
    for text in texts:
        match = LIMIT_TEXT.search(text)
        if match:
            return match.group(0)
    retries = [e for e in events if e.get("type") == "system" and e.get("subtype") == "api_retry"]
    if retries and retries[-1].get("error") == "rate_limit":
        return "api_retry rate_limit"
    return None


def positive_number(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return number


def run_session(command, *, cwd, timeout, env=None, output_dir=None):
    started = time.monotonic()
    output, stderr, error, returncode = "", "", None, None
    try:
        with subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True,
                              start_new_session=os.name == "posix") as proc:
            try:
                output, stderr = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    proc.kill()
                output, stderr = proc.communicate()
                error = "timeout"
            returncode = proc.returncode
            if returncode:
                error = error or "process_exit"
    except OSError as exc:
        error, stderr = type(exc).__name__, str(exc)

    events, found, result, initialization = [], [], None, {}
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        events.append(event)
        if event.get("type") == "system" and event.get("subtype") == "init":
            initialization = event
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
        subtype = str(result.get("subtype", ""))
        error = error or (subtype if subtype.startswith("error") else "session_error")
    elif not result.get("num_turns") and not found:
        error = error or "empty_session"
    limit = limit_signal(events, result) if error and error != "timeout" else None
    if limit:
        error = LIMIT_ERROR

    if output_dir is not None:
        Path(output_dir, "session.jsonl").write_text(output, encoding="utf-8")
        Path(output_dir, "stderr.txt").write_text(stderr, encoding="utf-8")
    record = {field: result.get(field) if result else None for field in RESULT_FIELDS}
    record.update(invoked=found, error=error, returncode=returncode, limit_evidence=limit,
                  error_detail=result.get("result") if result and error else None,
                  resolved_model=initialization.get("model"),
                  loaded_skills=initialization.get("skills"),
                  loaded_plugins=initialization.get("plugins"),
                  elapsed_seconds=round(time.monotonic() - started, 3))
    return record, events
