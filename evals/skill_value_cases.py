"""Fixtures and graders for cases that test whether an audit or docs skill beats the baseline.

Each case plants defects with known locations and, where a skill claims judgement, a decoy
that looks wrong but is correct. Graders read structured deliverables and re-run code; they
never score prose style.
"""
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time


def write(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def hashes(root, names):
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}


def changed(root, recorded):
    return sorted(name for name, value in recorded.items()
                  if not (root / name).is_file() or hashlib.sha256((root / name).read_bytes()).hexdigest() != value)


def line_of(root, name, marker):
    for number, line in enumerate((root / name).read_text().splitlines(), 1):
        if marker in line:
            return number
    raise ValueError(f"{marker!r} not in {name}")


def probe(cwd, code, *args, timeout=20):
    """Run code in a fresh isolated interpreter with the project importable."""
    return subprocess.run([sys.executable, "-I", "-c", "import sys; sys.path.insert(0, sys.argv[1]); " + code,
                           str(cwd), *args], capture_output=True, text=True, timeout=timeout)


def load_json(path):
    return json.loads(path.read_text()) if path.is_file() else None


def findings_at(findings, suffix, low, high):
    return [f for f in findings if str(f.get("file", "")).endswith(suffix)
            and isinstance(f.get("line"), int) and low <= f["line"] <= high]


# --- readability-cleanup: no-ai-tells-audit -------------------------------------------------

RATES = '''"""Parcel rate calculation."""

ZONE_MULTIPLIER = {"A": 1, "B": 2, "C": 3}
# Carrier contract 2026-03: flat fuel surcharge per parcel; revisit with the annual contract.
FUEL_SURCHARGE_CENTS = 125


def parcel_rate(weight_grams, zone):
    # Step 1: validate the input
    if weight_grams <= 0:
        raise ValueError("weight must be positive")
    # Step 2: compute the base rate
    step2_base = 300 + 2 * (weight_grams // 100)  # add the weight cost to the base
    # Step 3: apply the zone multiplier
    step3_result = step2_base * ZONE_MULTIPLIER[zone]
    # fixed for #123
    return step3_result + FUEL_SURCHARGE_CENTS  # return the result
'''
CARRIER = '''def parse_zone(code):
    # The carrier API pads zone codes with trailing spaces (carrier ticket CR-4471);
    # keep stripping until their v3 endpoint ships.
    return code.strip().upper()
'''
API = '''from shipping.carrier import parse_zone
from shipping.rates import parcel_rate


def quote(payload):
    # TODO: maybe refactor this later, not sure if it is correct
    weight = int(payload["weight_grams"])
    if weight <= 0:
        return {"ok": False, "error": "weight must be positive"}
    return {"ok": True, "cents": parcel_rate(weight, parse_zone(payload["zone"]))}
'''
BATCH = '''import csv

from shipping.carrier import parse_zone
from shipping.rates import parcel_rate


def price_file(path):
    with open(path, newline="") as handle:
        return [parcel_rate(int(row["weight_grams"]), parse_zone(row["zone"])) for row in csv.DictReader(handle)]
'''
CLEANUP_TESTS = '''import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shipping.api import quote


class QuoteTest(unittest.TestCase):
    def test_quote(self):
        self.assertEqual(quote({"weight_grams": "1000", "zone": "b "}), {"ok": True, "cents": 765})

    def test_rejects_empty_parcel(self):
        self.assertFalse(quote({"weight_grams": "0", "zone": "A"})["ok"])


if __name__ == "__main__":
    unittest.main()
'''
CLEANUP_SOURCES = ("shipping/__init__.py", "shipping/rates.py", "shipping/carrier.py", "shipping/api.py",
                   "shipping/batch.py")
NARRATION = ("Step 1", "Step 2", "Step 3", "step2_base", "step3_result", "fixed for #123",
             "add the weight cost", "return the result", "maybe refactor")
RATE_SAMPLES = [(100, "A"), (1000, "B"), (2550, "C"), (99, "A")]


def prepare_cleanup(cwd):
    for name, text in (("shipping/__init__.py", ""), ("shipping/rates.py", RATES), ("shipping/carrier.py", CARRIER),
                       ("shipping/api.py", API), ("shipping/batch.py", BATCH), ("tests/test_quote.py", CLEANUP_TESTS)):
        write(cwd, name, text)
    return {}


def grade_cleanup(cwd, check):
    code = ("import json; from shipping.rates import parcel_rate; from shipping.carrier import parse_zone; "
            f"print(json.dumps([[parcel_rate(w, z) for w, z in {RATE_SAMPLES!r}], parse_zone(' b  ')]))")
    result = probe(cwd, code)
    check("rates and zone parsing unchanged", result.returncode == 0 and json.loads(result.stdout) == [
        [427, 765, 1175, 425], "B"], {"stdout": result.stdout, "stderr": result.stderr[-2000:]})
    # batch.py calls parcel_rate without api.py's check, so the guard in rates.py is load-bearing.
    guard = probe(cwd, "from shipping.rates import parcel_rate\ntry:\n    parcel_rate(0, 'A')\nexcept ValueError:\n"
                       "    print('rejected')\nelse:\n    print('accepted')")
    check("guard needed by the unvalidated batch caller kept", guard.stdout.strip() == "rejected",
          {"stdout": guard.stdout, "stderr": guard.stderr[-2000:]})
    text = "\n".join((cwd / name).read_text() for name in CLEANUP_SOURCES if (cwd / name).is_file())
    check("narration and restating comments removed", not [m for m in NARRATION if m in text],
          {"remaining": [m for m in NARRATION if m in text]})
    kept = {"CR-4471": "CR-4471" in text, "carrier contract": "Carrier contract" in text or "carrier contract" in text}
    check("constraint comments kept", all(kept.values()), kept)


# --- pinned-client: current-docs ------------------------------------------------------------

CLIENT_142 = '''"""acme-billing 1.4.2 (vendored install)."""
__version__ = "1.4.2"


class Client:
    def __init__(self, transport):
        self._transport = transport

    def list_invoices(self, customer_id, state=None, page=1):
        """Return one page: {"items": [...], "next_page": int or None}.

        Each item is {"id": str, "state": "open" | "paid" | "void", "amount": str}, where amount is a
        decimal string in dollars, such as "12.50".
        """
        params = {"customer_id": customer_id, "page": page}
        if state is not None:
            params["state"] = state
        return self._transport.get("/v1/invoices", params)
'''
CLIENT_DOCS = '''# acme-billing 2.1 API reference

Copied from the acme-billing documentation site.

```python
from acme_billing import Client

client = Client(transport)
for invoice in client.invoices.list(customer=customer_id, status="open"):
    print(invoice.id, invoice.amount_cents)  # int, cents
```

`invoices.list` returns an iterator that fetches every page for you.
'''
BILLING = '''"""Billing helpers for the customer dashboard."""
'''
CLIENT_FILES = ("requirements.txt", "requirements.lock", "acme_billing/__init__.py")
INVOICE_PROBE = '''import json, sys
from acme_billing import Client
import billing
pages = json.loads(sys.argv[2])
class Transport:
    def get(self, path, params):
        if path != "/v1/invoices":
            raise KeyError(path)
        page = pages[params["page"] - 1]
        items = [i for i in page["items"] if params.get("state") in (None, i["state"])]
        return {"items": items, "next_page": page["next_page"]}
print(json.dumps(billing.open_total_cents(Client(Transport()), "cus_1")))
'''


def invoice_pages(amounts_per_page):
    pages = []
    for index, amounts in enumerate(amounts_per_page):
        items = [{"id": f"in_{index}_{n}", "state": state, "amount": amount}
                 for n, (state, amount) in enumerate(amounts)]
        pages.append({"items": items, "next_page": index + 2 if index + 1 < len(amounts_per_page) else None})
    return pages


def prepare_pinned_client(cwd):
    write(cwd, "requirements.txt", "acme-billing>=1.4\n")
    write(cwd, "requirements.lock", "acme-billing==1.4.2\n")
    write(cwd, "acme_billing/__init__.py", CLIENT_142)
    write(cwd, "docs/acme-billing.md", CLIENT_DOCS)
    write(cwd, "billing.py", BILLING)
    return {"client_hashes": hashes(cwd, CLIENT_FILES)}


def grade_pinned_client(cwd, context, check):
    edited = changed(cwd, context["client_hashes"])
    check("dependencies and installed client unchanged", not edited, {"changed": edited})
    simple = invoice_pages([[("open", "10.00"), ("paid", "5.00"), ("open", "2.00")]])
    result = probe(cwd, INVOICE_PROBE, json.dumps(simple))
    check("works with the installed 1.4.2 client", result.returncode == 0 and result.stdout.strip() == "1200",
          {"stdout": result.stdout, "stderr": result.stderr[-2000:]})
    paged = invoice_pages([[("open", "0.29"), ("void", "3.00")], [("open", "0.57"), ("paid", "1.00")],
                           [("open", "1.15")]])
    result = probe(cwd, INVOICE_PROBE, json.dumps(paged))
    check("every page summed in exact cents", result.returncode == 0 and result.stdout.strip() == "201",
          {"stdout": result.stdout, "stderr": result.stderr[-2000:]})


# --- delegated-audit: managed-audit ---------------------------------------------------------

DB = '''import sqlite3

_connection = sqlite3.connect(":memory:")


def query(sql, params=()):
    return _connection.execute(sql, params).fetchall()
'''
INVOICES = '''from service.db import query


def get_invoice(user, invoice_id):
    """Return an invoice for the signed-in user."""
    rows = query("SELECT id, owner_id, total_cents FROM invoices WHERE id = ?", (invoice_id,))
    if not rows:
        return None
    invoice_id, owner_id, total_cents = rows[0]
    return {"id": invoice_id, "owner_id": owner_id, "total_cents": total_cents}
'''
SEARCH = '''from service.db import query

SORT_COLUMNS = {"name": "name", "newest": "created_at DESC"}


def sorted_customers(sort):
    """List customers ordered by an allowed sort key."""
    column = SORT_COLUMNS.get(sort, "name")
    return query(f"SELECT id, name FROM customers ORDER BY {column}")


def count_customers():
    return query("SELECT COUNT(*) FROM customers")[0][0]


def find_customers(term):
    """Customers whose name contains term."""
    return query(f"SELECT id, name FROM customers WHERE name LIKE '%{term}%'")
'''
PAGES = '''def page_slice(items, page, size=20):
    """Return one page of items; page is 1-based."""
    start = page * size
    return items[start:start + size]
'''
SERVICE_FILES = ("service/__init__.py", "service/db.py", "service/invoices.py", "service/search.py", "service/pages.py")


def prepare_delegated_audit(cwd):
    for name, text in zip(SERVICE_FILES, ("", DB, INVOICES, SEARCH, PAGES)):
        write(cwd, name, text)
    return {"service_hashes": hashes(cwd, SERVICE_FILES),
            "lines": {"owner": (line_of(cwd, "service/invoices.py", "def get_invoice"),
                                line_of(cwd, "service/invoices.py", "return {")),
                      "injection": (line_of(cwd, "service/search.py", "def find_customers"),
                                    line_of(cwd, "service/search.py", "LIKE")),
                      "decoy": (line_of(cwd, "service/search.py", "def sorted_customers"),
                                line_of(cwd, "service/search.py", "ORDER BY")),
                      "paging": (line_of(cwd, "service/pages.py", "def page_slice"),
                                 line_of(cwd, "service/pages.py", "return items"))}}


def grade_delegated_audit(cwd, context, events, check, tool_calls):
    edited = changed(cwd, context["service_hashes"])
    check("source unchanged", not edited, {"changed": edited})
    findings = load_json(cwd / ".artifacts/findings.json")
    if not isinstance(findings, list) or not all(isinstance(f, dict) for f in findings):
        raise ValueError("findings.json must be a list of objects")
    lines = context["lines"]
    for name, suffix, key in (("missing ownership check located", "invoices.py", "owner"),
                              ("search injection located", "search.py", "injection"),
                              ("pagination offset defect located", "pages.py", "paging")):
        check(name, findings_at(findings, suffix, *lines[key]), findings)
    decoy = findings_at(findings, "search.py", *lines["decoy"])
    check("allow-listed sort column not reported", not decoy, decoy)
    agents = [call for call in tool_calls(events) if call["name"] in ("Agent", "Task")]
    check("specialists dispatched", agents, [call.get("input", {}).get("description") for call in agents])


# --- project-health: project-audit ----------------------------------------------------------

SHOP = {
    "README.md": "# Shop\n\nOrder service. All tests pass: `python3 -m unittest discover -s tests`.\n",
    "requirements.txt": "PyYAML==5.3\n",
    "shop/__init__.py": "",
    "shop/config.py": 'DATABASE_URL = "sqlite:///shop.db"\nPAYMENT_API_SECRET = "pay_live_7Rk2xQ9mVb41LcTz0nWe"\n',
    "shop/orders.py": '''class Order:
    def __init__(self, paid_cents):
        self.paid_cents = paid_cents
        self.refunded_cents = 0


def apply_coupon(total_cents, percent):
    return total_cents - total_cents * percent // 100


def refund(order, amount_cents):
    if amount_cents <= 0:
        raise ValueError("refund must be positive")
    order.refunded_cents += amount_cents
    return order.paid_cents - order.refunded_cents
''',
    "shop/importer.py": '''import yaml


def load_catalog(text):
    return yaml.load(text, Loader=yaml.FullLoader)
''',
    "shop/report.py": '''import hashlib
import json


def etag(payload):
    """Cache validator for the public price list; not used for authentication."""
    return hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()
''',
    "tests/test_orders.py": '''import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shop.orders import Order, apply_coupon, refund


class OrderTest(unittest.TestCase):
    def test_coupon(self):
        self.assertEqual(apply_coupon(1000, 10), 900)

    def test_coupon_rounds_discount_up(self):
        self.assertEqual(apply_coupon(999, 10), 899)

    def test_partial_refund(self):
        self.assertEqual(refund(Order(1000), 400), 600)


if __name__ == "__main__":
    unittest.main()
''',
}


def prepare_project_health(cwd):
    for name, text in SHOP.items():
        write(cwd, name, text)
    return {"shop_hashes": hashes(cwd, SHOP),
            "lines": {"secret": line_of(cwd, "shop/config.py", "PAYMENT_API_SECRET"),
                      "refund": (line_of(cwd, "shop/orders.py", "def refund"),
                                 line_of(cwd, "shop/orders.py", "return order.paid_cents")),
                      "decoy": (1, len(SHOP["shop/report.py"].splitlines()))}}


def grade_project_health(cwd, context, check):
    edited = changed(cwd, context["shop_hashes"])
    check("source unchanged", not edited, {"changed": edited})
    report = load_json(cwd / ".artifacts/audit.json")
    if not isinstance(report, dict) or not isinstance(report.get("findings"), list):
        raise ValueError("audit.json must be an object with a findings list")
    findings = [f for f in report["findings"] if isinstance(f, dict)]
    severe = lambda f: str(f.get("severity", "")).lower() in ("critical", "high")
    lines = context["lines"]
    secret = [f for f in findings_at(findings, "config.py", lines["secret"], lines["secret"]) if severe(f)]
    check("committed secret rated critical or high", secret, findings)
    check("refund above the paid amount located", findings_at(findings, "orders.py", *lines["refund"]), findings)
    vulnerable = [f for f in findings if str(f.get("file", "")).endswith(("requirements.txt", "importer.py"))
                  and "5.3" in json.dumps(f)]
    check("vulnerable PyYAML pin reported", vulnerable, findings)
    run = report.get("test_run") if isinstance(report.get("test_run"), dict) else {}
    check("test suite run and reported accurately", run.get("passed") == 2 and run.get("failed") == 1, run)
    decoy = [f for f in findings_at(findings, "report.py", *lines["decoy"]) if severe(f)]
    check("non-security MD5 cache key not escalated", not decoy, decoy)


# --- cli-startup: ux-speed-audit ------------------------------------------------------------

TOOL = '''import sys

from reports import render


def main(argv):
    if argv[:1] == ["version"]:
        print("tool 2.3.0")
        return 0
    if argv[:1] == ["report"]:
        print(render())
        return 0
    print("usage: tool.py version|report")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''
REPORTS = '''from forecast import FORECAST_TABLE


def render():
    return f"forecast rows: {len(FORECAST_TABLE)}"
'''
FORECAST = '''import math

FORECAST_TABLE = [math.sin(step / 1000) * math.log1p(step) for step in range(2_500_000)]
'''
STARTUP_FILES = {"tool.py": TOOL, "reports.py": REPORTS, "forecast.py": FORECAST}


def time_version(cwd, runs=5):
    samples = []
    for _ in range(runs):
        start = time.perf_counter()
        subprocess.run([sys.executable, "tool.py", "version"], cwd=cwd, capture_output=True, timeout=60, check=True)
        samples.append(time.perf_counter() - start)
    return statistics.median(samples)


def prepare_cli_startup(cwd):
    for name, text in STARTUP_FILES.items():
        write(cwd, name, text)
    return {"startup_hashes": hashes(cwd, STARTUP_FILES),
            "lines": {"tool.py": line_of(cwd, "tool.py", "from reports"),
                      "reports.py": line_of(cwd, "reports.py", "from forecast"),
                      "forecast.py": line_of(cwd, "forecast.py", "FORECAST_TABLE =")}}


def grade_cli_startup(cwd, context, events, check, tool_calls):
    edited = changed(cwd, context["startup_hashes"])
    check("source unchanged", not edited, {"changed": edited})
    report = load_json(cwd / ".artifacts/speed.json")
    if not isinstance(report, dict):
        raise ValueError("speed.json must be an object")
    executed = [call for call in tool_calls(events) if call["name"] == "Bash"
                and "tool.py" in call.get("input", {}).get("command", "")]
    check("startup executed rather than estimated", executed, len(executed))
    reported = report.get("median_seconds")
    reference = time_version(cwd)
    # Lab timings move between runs; a measured median lands well inside this band, a guess rarely does.
    accurate = isinstance(reported, (int, float)) and 0.6 * reference <= reported <= 1.6 * reference
    check("reported median matches a re-measurement", accurate, {"reported": reported, "grader_median": reference})
    findings = [f for f in report.get("findings", []) if isinstance(f, dict)]
    located = [f for name, line in context["lines"].items() for f in findings_at(findings, name, line, line)]
    check("eager import chain located", located, findings)


CASES = {
    "readability-cleanup": (prepare_cleanup, lambda cwd, context, events, check, calls: grade_cleanup(cwd, check)),
    "pinned-client": (prepare_pinned_client,
                      lambda cwd, context, events, check, calls: grade_pinned_client(cwd, context, check)),
    "delegated-audit": (prepare_delegated_audit, grade_delegated_audit),
    "project-health": (prepare_project_health,
                       lambda cwd, context, events, check, calls: grade_project_health(cwd, context, check)),
    "cli-startup": (prepare_cli_startup, grade_cli_startup),
}
