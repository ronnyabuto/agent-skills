# Memory helper

Requires Python 3.10+ and SQLite FTS5. Use CODEX_MEMORY_VAULT or the selected vault stored in ~/.config/ronny-codex-skills/memory.json (XDG_CONFIG_HOME is respected). The script refuses to create an implicit default vault. Set MEMORY to this skill's installed scripts/memory.py path.

```bash
python3 "$MEMORY" search "refresh race"
python3 "$MEMORY" read codex/notes/project-id/note.md --lines 10:35
python3 "$MEMORY" recent --limit 5
python3 "$MEMORY" note --title "Retry ownership" --body-file /tmp/decision.md
python3 "$MEMORY" supersede codex/notes/project-id/old.md --by codex/notes/project-id/new.md
python3 "$MEMORY" import-session /absolute/path/to/selected-codex-session.jsonl
```

Run from the repository being recalled. --cwd can specify the repository explicitly. Search/recent defaults to that project; --all-projects permits broader recall when the task warrants it. Superseded notes are hidden unless --include-superseded is used. Search emits line references with bounded snippets; read caps output at 6,000 characters by default and permits at most 12,000.

Import handles Codex response_item messages/function_call names and compacted summaries, with event_msg user_message fallback when no response_item user messages exist. It does not preserve raw tool arguments, outputs or reasoning. Unknown formats fail instead of producing a misleading empty archive. Transcripts must be regular .jsonl files and are capped at 32 MiB. Import can include sensitive prose that patterns miss: review the source and resulting archive according to the user's confidentiality requirements.

The optional user-level hooks require Codex lifecycle-hook support and trust review
through `/hooks`. They archive only the transcript path supplied by Codex,
respect CODEX_MEMORY_EXCLUDE, and update one snapshot per session. They tolerate
an unfinished final JSONL record while retaining strict parsing for explicit
imports. Archive errors are reported to stderr and do not block compaction or
shutdown. SessionStart returns JSON additionalContext with a short recall
pointer. Codex transcript formats are not a stable hook interface; a future
format change may require updating the importer. No fallback scans personal
session directories or Claude archives.

Notes use unique filenames and atomic writes; two identical titles cannot silently overwrite. The helper rejects traversal and symlinks that escape the vault. Markdown indexes are rebuilt incrementally with a content hash, so same-size/same-timestamp edits are detected. The cache is local SQLite; search uses parameterized FTS queries. An index contains note text and must be treated as sensitive too.
