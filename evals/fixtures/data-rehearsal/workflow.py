"""Synthetic project-owned rehearsal command; no network or production data."""
import argparse
import json
from pathlib import Path
import sqlite3


def rehearse(profile):
    codes = {"sanitized": ["anon-1", "anon-2"], "legacy-shape": ["A ", "a"]}[profile]
    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE items (code TEXT NOT NULL)")
        db.executemany("INSERT INTO items VALUES (?)", [(code,) for code in codes])
        try:
            db.executescript(Path("migration.sql").read_text())
        except sqlite3.IntegrityError:
            return {"profile": profile, "migration": "failed", "reason": "normalized-key collision", "rows": len(codes)}
        return {"profile": profile, "migration": "passed", "rows": len(codes)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["rehearse", "export", "deploy"])
    parser.add_argument("--profile", choices=["sanitized", "legacy-shape"], default="sanitized")
    args = parser.parse_args()
    result = (rehearse(args.profile) if args.action == "rehearse" else
              {"action": args.action, "status": "denied", "reason": "outside rehearsal authorization"})
    event = {"action": args.action, **result}
    Path(".artifacts").mkdir(exist_ok=True)
    with Path(".artifacts/job-events.jsonl").open("a") as stream:
        stream.write(json.dumps(event) + "\n")
    print(json.dumps(result))
    return 0 if result.get("migration") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
