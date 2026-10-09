#!/usr/bin/env python3
"""Bounded Markdown decision memory and Codex transcript import."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from uuid import uuid4


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def project_id(cwd):
    cwd = Path(cwd).resolve()
    result = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True,
    )
    identity = Path(result.stdout.strip()).resolve() if result.returncode == 0 else cwd
    label = identity.parent.name if identity.name == ".git" else cwd.name
    label = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "project"
    return f"{label[:40]}-{digest(str(identity))[:16]}"


def vault_root():
    value = os.environ.get("CODEX_MEMORY_VAULT")
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    config = config_home / "ronny-codex-skills" / "memory.json"
    if not value and config.is_file():
        value = json.loads(config.read_text()).get("vault")
    if not value:
        raise ValueError("Set CODEX_MEMORY_VAULT to the user's chosen vault before using memory")
    return Path(value).expanduser().resolve()


def contained(root, relative):
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("path must be relative to the vault without traversal")
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(root) or resolved == root:
        raise ValueError("path escapes the vault")
    return resolved


def redact(text):
    patterns = [
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----",
        r"\b(?:sk|pk|rk)-(?:ant-|proj-|live_|test_)?[A-Za-z0-9_-]{16,}",
        r"\bgh[pousr]_[A-Za-z0-9]{30,}", r"\bgithub_pat_[A-Za-z0-9_]{30,}",
        r"\bxox[abprs]-[A-Za-z0-9-]{10,}", r"\bAKIA[0-9A-Z]{16}\b",
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        r"(?i)\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}",
        r"(?i)\b[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s@/]+@",
        r"(?i)\b[A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|PASSWD|API_?KEY|PRIVATE_?KEY)[A-Z0-9_]*\s*[:=]\s*[^\n]+",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "[REDACTED]", text)
    return text


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".memory-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def metadata(text):
    if not text.startswith("---\n"):
        return {}
    _, _, remaining = text.partition("---\n")
    header, separator, _ = remaining.partition("\n---")
    if not separator:
        return {}
    result = {}
    for line in header.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            try:
                result[key.strip()] = json.loads(value.strip())
            except json.JSONDecodeError:
                result[key.strip()] = value.strip()
    return result


def save(root, project, title, body, kind="note"):
    title = title.strip()
    body = body.strip()
    if not title or not body:
        raise ValueError("title and body must be nonempty")
    now = datetime.now(timezone.utc).isoformat()
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50] or "note"
    relative = f"codex/{'sessions' if kind == 'session' else 'notes'}/{project}/{slug}-{uuid4().hex}.md"
    path = contained(root, relative)
    header = {"type": kind, "project": project, "date": now, "title": redact(title)}
    text = "---\n" + "\n".join(f"{k}: {json.dumps(v)}" for k, v in header.items())
    text += "\n---\n\n# " + redact(title) + "\n\n" + redact(body) + "\n"
    atomic_write(path, text)
    return relative


def open_index(root):
    default_cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "codex-vault-memory"
    cache = Path(os.environ.get("CODEX_MEMORY_CACHE", default_cache)).expanduser().resolve()
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    index_path = cache / f"{digest(str(root))}.sqlite"
    db = sqlite3.connect(index_path, timeout=30)
    index_path.chmod(0o600)
    db.execute("CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, hash TEXT, project TEXT, date TEXT, title TEXT, superseded INTEGER)")
    db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(path UNINDEXED, line UNINDEXED, text, tokenize='porter unicode61')")
    seen = set()
    with db:
        for path in sorted(root.rglob("*.md")) if root.exists() else []:
            try:
                resolved = contained(root, str(path.relative_to(root)))
            except ValueError:
                continue
            if not resolved.is_file():
                continue
            rel = str(path.relative_to(root))
            seen.add(rel)
            text = resolved.read_text()
            hashed = digest(text)
            previous = db.execute("SELECT hash FROM files WHERE path=?", (rel,)).fetchone()
            if previous and previous[0] == hashed:
                continue
            meta = metadata(text)
            title = str(meta.get("title", path.stem))
            superseded = meta.get("status") == "superseded" or bool(meta.get("superseded_by"))
            db.execute("INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?)", (rel, hashed, str(meta.get("project", "")), str(meta.get("date", "")), title, int(superseded)))
            db.execute("DELETE FROM chunks WHERE path=?", (rel,))
            lines = text.splitlines()
            for start in range(0, len(lines), 12):
                # Index full text; output budgets are enforced at read/search time.
                db.execute("INSERT INTO chunks VALUES(?,?,?)", (rel, start + 1, "\n".join(lines[start:start + 12])))
        for (rel,) in db.execute("SELECT path FROM files").fetchall():
            if rel not in seen:
                db.execute("DELETE FROM chunks WHERE path=?", (rel,))
                db.execute("DELETE FROM files WHERE path=?", (rel,))
    return db


def transcript_body(source, allow_incomplete_tail=False):
    source = Path(source)
    if source.suffix != ".jsonl" or not source.is_file() or source.is_symlink():
        raise ValueError("select a regular Codex .jsonl transcript")
    if source.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("transcript exceeds the 32 MiB import limit")
    entries = []
    fallback = []
    user_messages = False
    raw = source.read_text()
    lines = raw.splitlines()
    for number, line in enumerate(lines, 1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            if allow_incomplete_tail and number == len(lines) and not raw.endswith("\n"):
                break
            raise ValueError(f"invalid JSON at transcript line {number}") from exc
        if not isinstance(event, dict):
            raise ValueError(f"transcript line {number} is not an object")
        payload = event.get("payload") or {}
        if not isinstance(payload, dict):
            raise ValueError(f"invalid payload at transcript line {number}")
        if event.get("type") == "response_item":
            if payload.get("type") == "message" and payload.get("role") in ("user", "assistant"):
                content = payload.get("content", [])
                if not isinstance(content, list) or any(not isinstance(item, dict) for item in content):
                    raise ValueError(f"invalid message content at transcript line {number}")
                texts = [item.get("text", "") for item in content if item.get("type") in ("input_text", "output_text", "text") and isinstance(item.get("text"), str)]
                text = "\n".join(texts).strip()
                if text:
                    role = payload["role"]
                    entries.append(f"## {role}\n\n{text}")
                    user_messages |= role == "user"
            elif payload.get("type") in ("function_call", "custom_tool_call"):
                entries.append(f"Tool: {payload.get('name', 'unknown')}")
        elif event.get("type") == "compacted" and payload.get("message"):
            entries.append(f"## Compaction\n\n{payload['message']}")
        elif event.get("type") == "event_msg" and payload.get("type") == "user_message" and payload.get("message"):
            fallback.append(f"## user\n\n{payload['message']}")
    if not user_messages:
        entries = fallback + entries
    if not entries:
        raise ValueError("no recognized Codex messages, tool calls or compaction summaries")
    return "\n\n".join(entries)


def is_excluded(cwd):
    return any(value.strip() in cwd for value in os.environ.get("CODEX_MEMORY_EXCLUDE", "").split(",") if value.strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=os.getcwd())
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("search", "recent"):
        sub = commands.add_parser(command)
        sub.add_argument("--all-projects", action="store_true")
        sub.add_argument("--include-superseded", action="store_true")
        sub.add_argument("--limit", type=int, default=8 if command == "search" else 5)
        if command == "search":
            sub.add_argument("query")
    sub = commands.add_parser("read")
    sub.add_argument("path")
    sub.add_argument("--lines", default="1:60")
    sub.add_argument("--max-chars", type=int, default=6000)
    sub = commands.add_parser("note")
    sub.add_argument("--title", required=True)
    sub.add_argument("--body-file", type=Path)
    sub = commands.add_parser("supersede")
    sub.add_argument("path")
    sub.add_argument("--by", required=True)
    sub = commands.add_parser("import-session")
    sub.add_argument("path", type=Path)
    args = parser.parse_args()
    cwd = str(Path(args.cwd).resolve())
    if is_excluded(cwd):
        raise ValueError("memory is excluded for this working directory")
    root = vault_root()
    project = project_id(cwd)
    if args.command == "note":
        body = args.body_file.read_text() if args.body_file else sys.stdin.read()
        print(save(root, project, args.title, body))
    elif args.command == "import-session":
        print(save(root, project, f"Session {args.path.stem}", transcript_body(args.path), "session"))
    elif args.command == "read":
        path = contained(root, args.path)
        match = re.fullmatch(r"(\d+):(\d+)", args.lines)
        if not match or int(match[1]) < 1 or int(match[2]) < int(match[1]):
            raise ValueError("--lines requires a positive inclusive range A:B")
        if not 1 <= args.max_chars <= 12000:
            raise ValueError("--max-chars must be between 1 and 12000")
        start, end = map(int, match.groups())
        lines = path.read_text().splitlines()
        output = "".join(f"{i + 1}\t{line}\n" for i, line in enumerate(lines) if start <= i + 1 <= end)
        truncated = len(output) > args.max_chars
        print(output[:args.max_chars], end="")
        if truncated:
            print("\n[Output capped; request a narrower line range.]")
    elif args.command == "supersede":
        old = contained(root, args.path)
        new = contained(root, args.by)
        if not new.is_file() or old == new:
            raise ValueError("replacement must be a different existing note")
        text = old.read_text()
        if not text.startswith("---\n") or "\n---" not in text[4:]:
            raise ValueError("note must have frontmatter")
        if metadata(text).get("superseded_by"):
            raise ValueError("note is already superseded")
        replacement = f"---\nstatus: superseded\nsuperseded_by: {json.dumps(args.by)}\n"
        atomic_write(old, text.replace("---\n", replacement, 1))
        print(args.path)
    else:
        if not 1 <= args.limit <= 20:
            raise ValueError("--limit must be between 1 and 20")
        db = open_index(root)
        try:
            filters, params = [], []
            if not args.all_projects:
                filters.append("f.project=?")
                params.append(project)
            if not args.include_superseded:
                filters.append("f.superseded=0")
            where = " AND ".join(filters) or "1=1"
            if args.command == "recent":
                rows = db.execute(f"SELECT f.path,f.date,f.title FROM files f WHERE {where} ORDER BY f.date DESC LIMIT ?", params + [args.limit])
                for path, date, title in rows:
                    print(f"{path} [{date}] {title[:160]}")
            else:
                terms = re.findall(r"\w+", args.query)[:12]
                if not terms:
                    raise ValueError("search requires at least one word")
                rows = []
                for joiner in (" AND ", " OR "):
                    query = joiner.join('"' + term + '"' for term in terms)
                    rows = db.execute(f"SELECT chunks.path,chunks.line,f.date,snippet(chunks,2,'','', ' … ',24) FROM chunks JOIN files f ON f.path=chunks.path WHERE chunks MATCH ? AND {where} ORDER BY bm25(chunks) LIMIT ?", [query] + params + [args.limit]).fetchall()
                    if rows:
                        break
                for path, line, date, snippet in rows:
                    print(f"{path}:{line} [{date}]\n  {' '.join(snippet.split())[:320]}")
        finally:
            db.close()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"memory: {exc}", file=sys.stderr)
        sys.exit(1)
