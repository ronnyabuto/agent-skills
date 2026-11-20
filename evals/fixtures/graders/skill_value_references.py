"""Reference answers for skill_value_cases: they must pass every check, and tests derive near misses from them."""
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

CLEAN_RATES = '''"""Parcel rate calculation."""

ZONE_MULTIPLIER = {"A": 1, "B": 2, "C": 3}
# Carrier contract 2026-03: flat fuel surcharge per parcel; revisit with the annual contract.
FUEL_SURCHARGE_CENTS = 125


def parcel_rate(weight_grams, zone):
    if weight_grams <= 0:
        raise ValueError("weight must be positive")
    base = 300 + 2 * (weight_grams // 100)
    return base * ZONE_MULTIPLIER[zone] + FUEL_SURCHARGE_CENTS
'''
BILLING = '''"""Billing helpers for the customer dashboard."""
from decimal import Decimal


def open_total_cents(client, customer_id):
    total, page = Decimal(0), 1
    while page:
        result = client.list_invoices(customer_id, state="open", page=page)
        total += sum(Decimal(item["amount"]) for item in result["items"] if item["state"] == "open")
        page = result["next_page"]
    return int(total * 100)
'''


def call(name, **fields):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": fields}]}}


def line(cwd, name, marker):
    return next(n for n, text in enumerate((cwd / name).read_text().splitlines(), 1) if marker in text)


def answer(case, cwd):
    """Write the reference deliverable into cwd and return the tool-call events it implies."""
    cwd = Path(cwd)
    artifacts = cwd / ".artifacts"
    artifacts.mkdir(exist_ok=True)
    if case == "readability-cleanup":
        (cwd / "shipping/rates.py").write_text(CLEAN_RATES)
        api = cwd / "shipping/api.py"
        api.write_text(api.read_text().replace("    # TODO: maybe refactor this later, not sure if it is correct\n", ""))
        return []
    if case == "pinned-client":
        (cwd / "billing.py").write_text(BILLING)
        return []
    if case == "delegated-audit":
        findings = [
            {"file": "service/invoices.py", "line": line(cwd, "service/invoices.py", "return {"),
             "title": "Invoice returned without an owner check", "severity": "High", "evidence": "owner_id unused"},
            {"file": "service/search.py", "line": line(cwd, "service/search.py", "LIKE"),
             "title": "SQL injection through term", "severity": "High", "evidence": "f-string query"},
            {"file": "service/pages.py", "line": line(cwd, "service/pages.py", "start ="),
             "title": "Page 1 skips the first page", "severity": "Medium", "evidence": "1-based page times size"},
        ]
        (artifacts / "findings.json").write_text(json.dumps(findings))
        return [call("Agent", description="Security specialist", prompt="Inspect service/ for access control")]
    if case == "project-health":
        report = {"findings": [
            {"severity": "Critical", "file": "shop/config.py", "line": line(cwd, "shop/config.py", "PAYMENT_API_SECRET"),
             "scenario": "Anyone with repository access can charge cards", "fix": "Rotate; load from the environment"},
            {"severity": "High", "file": "shop/orders.py", "line": line(cwd, "shop/orders.py", "refunded_cents +="),
             "scenario": "refund(Order(1000), 5000) refunds more than was paid", "fix": "Cap at the remaining amount"},
            {"severity": "High", "file": "requirements.txt", "line": 1,
             "scenario": "PyYAML 5.3 FullLoader allows code execution (CVE-2020-1747)", "fix": "Use safe_load; upgrade"},
            {"severity": "Low", "file": "tests/test_orders.py", "line": 11,
             "scenario": "README says all tests pass; test_coupon_rounds_discount_up fails", "fix": "Decide rounding"},
        ], "test_run": {"command": "python3 -m unittest discover -s tests", "passed": 2, "failed": 1}}
        (artifacts / "audit.json").write_text(json.dumps(report))
        return [call("Bash", command="python3 -m unittest discover -s tests")]
    if case == "cli-startup":
        samples = []
        for _ in range(5):
            start = time.perf_counter()
            subprocess.run([sys.executable, "tool.py", "version"], cwd=cwd, capture_output=True, check=True)
            samples.append(time.perf_counter() - start)
        report = {"command": "python3 tool.py version", "runs": 5, "median_seconds": statistics.median(samples),
                  "findings": [{"file": "tool.py", "line": line(cwd, "tool.py", "from reports"),
                                "cause": "version imports reports, which builds the forecast table",
                                "fix": "Import reports inside the report branch"}]}
        (artifacts / "speed.json").write_text(json.dumps(report))
        return [call("Bash", command="for i in 1 2 3 4 5; do /usr/bin/time -f %e python3 tool.py version; done")]
    raise KeyError(case)
