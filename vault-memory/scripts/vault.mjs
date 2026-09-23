#!/usr/bin/env node
// Searchable Obsidian-vault memory for coding agents. Zero dependencies:
// needs Node >= 22.5 for node:sqlite (FTS5 + BM25 are compiled in).

import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

// node:sqlite still emits an ExperimentalWarning on Node 24 and hooks surface
// stderr to the user. The listener has to be installed before the module
// loads, which is why this import is dynamic.
process.removeAllListeners("warning");
process.on("warning", (w) => {
  if (w.name !== "ExperimentalWarning") console.error(w);
});
const { DatabaseSync } = await import("node:sqlite");

const VAULT = path.resolve(expandHome(process.env.AGENT_VAULT || "~/agent-vault"));
const AGENT_DIR = "claude";
const SESSIONS_DIR = path.join(AGENT_DIR, "sessions");
const NOTES_DIR = path.join(AGENT_DIR, "notes");
const CACHE_DIR = path.join(
  process.env.XDG_CACHE_HOME || path.join(os.homedir(), ".cache"),
  "vault-memory",
);
const EXCLUDE = (process.env.VAULT_MEMORY_EXCLUDE || "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

const CHUNK_CHARS = 1500;
const RECALL_BUDGET = 1800;

function expandHome(p) {
  return p.startsWith("~") ? path.join(os.homedir(), p.slice(1)) : p;
}

function parseArgs(argv) {
  const positional = [];
  const flags = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) {
      positional.push(a);
      continue;
    }
    const key = a.slice(2);
    const next = argv[i + 1];
    if (next === undefined || next.startsWith("--")) flags[key] = true;
    else flags[key] = argv[++i];
  }
  return { positional, flags };
}

function projectName(cwd) {
  const repo = cwd.split(`${path.sep}.claude${path.sep}worktrees${path.sep}`)[0];
  return path.basename(repo) || "unknown";
}

function isExcluded(cwd) {
  return EXCLUDE.some((part) => cwd.includes(part));
}

const SECRET_PATTERNS = [
  /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g,
  /\b(?:sk|pk|rk)-(?:ant-|proj-|live_|test_)?[A-Za-z0-9_-]{16,}/g,
  /\bgh[pousr]_[A-Za-z0-9]{30,}/g,
  /\bgithub_pat_[A-Za-z0-9_]{30,}/g,
  /\bxox[abprs]-[A-Za-z0-9-]{10,}/g,
  /\bAKIA[0-9A-Z]{16}\b/g,
  /\bAIza[0-9A-Za-z_-]{35}\b/g,
  /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/g,
  /\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{16,}/gi,
  /\b[a-z][a-z0-9+.-]*:\/\/[^\s:/@]+:[^\s@/]+@/gi,
];
const SECRET_ASSIGNMENT =
  /\b([A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|PASSWD|API_?KEY|PRIVATE_?KEY|CREDENTIALS?|CONSUMER_KEY|PASSKEY)[A-Z0-9_]*)(\s*[:=]\s*)(["']?)([^\s"']{6,})\3/gi;

// The key names above also appear in prose and metrics ("context_tokens:
// 182340", "password: required"), so only redact values shaped like a secret:
// never pure numbers, and plain words only when long enough to be a passphrase.
function looksSecret(value) {
  if (/^\d+$/.test(value)) return false;
  if (/^[A-Za-z]+$/.test(value)) return value.length >= 16;
  return value.length >= 8;
}

function redact(text) {
  let out = text;
  for (const re of SECRET_PATTERNS) out = out.replace(re, "[REDACTED]");
  return out.replace(SECRET_ASSIGNMENT, (match, key, sep, quote, value) =>
    looksSecret(value) ? `${key}${sep}${quote}[REDACTED]${quote}` : match,
  );
}

function locateTranscript(payload) {
  if (payload.transcript_path && fs.existsSync(payload.transcript_path)) {
    return payload.transcript_path;
  }
  // PreCompact has shipped with an empty transcript_path before
  // (anthropics/claude-code#13668), so fall back to the known layout.
  const root = path.join(os.homedir(), ".claude", "projects");
  const name = `${payload.session_id}.jsonl`;
  if (!payload.session_id || !fs.existsSync(root)) return null;
  for (const dir of fs.readdirSync(root)) {
    const candidate = path.join(root, dir, name);
    if (fs.existsSync(candidate)) return candidate;
  }
  return null;
}

function userText(content) {
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return content
    .filter((c) => c.type === "text")
    .map((c) => c.text)
    .join("\n");
}

function cleanPrompt(text) {
  return text
    .replace(/<system-reminder>[\s\S]*?<\/system-reminder>/g, "")
    .replace(/<local-command-(?:stdout|stderr|caveat)>[\s\S]*?<\/local-command-(?:stdout|stderr|caveat)>/g, "")
    .replace(/<command-(?:message|args)>[\s\S]*?<\/command-(?:message|args)>/g, "")
    .replace(/<command-name>([\s\S]*?)<\/command-name>/g, "$1")
    .trim();
}

function describeTool(block) {
  const input = block.input || {};
  const target =
    input.file_path ||
    input.path ||
    input.description ||
    input.pattern ||
    input.query ||
    input.url ||
    input.skill ||
    input.command ||
    "";
  const oneLine = String(target).replace(/\s+/g, " ").slice(0, 140);
  return oneLine ? `${block.name}: ${oneLine}` : block.name;
}

function condenseTranscript(file) {
  const rows = [];
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    if (!line) continue;
    try {
      rows.push(JSON.parse(line));
    } catch {
      // the harness writes the transcript asynchronously; a torn final line is expected
    }
  }

  const meta = { started: null, ended: null, branch: null, title: null, compactions: 0 };
  const summaries = [];
  const turns = [];
  let tools = [];

  const flushTools = () => {
    if (tools.length) turns.push(tools.map((t) => `- ${t}`).join("\n"));
    tools = [];
  };

  for (const r of rows) {
    if (r.timestamp) {
      meta.started ??= r.timestamp;
      meta.ended = r.timestamp;
    }
    if (r.gitBranch) meta.branch = r.gitBranch;
    if (r.type === "ai-title" && r.aiTitle) meta.title = r.aiTitle;
    if (r.isSidechain) continue;

    if (r.isCompactSummary) {
      meta.compactions++;
      summaries.push(userText(r.message?.content));
      continue;
    }
    if (r.type === "user" && !r.isMeta) {
      const text = cleanPrompt(userText(r.message?.content));
      if (!text) continue;
      flushTools();
      turns.push(`**User:** ${text}`);
    } else if (r.type === "assistant" && Array.isArray(r.message?.content)) {
      for (const block of r.message.content) {
        if (block.type === "tool_use") tools.push(describeTool(block));
        else if (block.type === "text" && block.text.trim()) {
          flushTools();
          turns.push(`**Claude:** ${block.text.trim()}`);
        }
      }
    }
  }
  flushTools();
  return { meta, summaries, turns };
}

function yamlString(s) {
  return JSON.stringify(String(s));
}

function archiveSession(payload) {
  const cwd = payload.cwd || process.cwd();
  if (isExcluded(cwd)) return null;
  const transcript = locateTranscript(payload);
  if (!transcript) return null;

  const { meta, summaries, turns } = condenseTranscript(transcript);
  if (!turns.length) return null;

  const project = projectName(cwd);
  const day = (meta.started || new Date().toISOString()).slice(0, 10);
  const shortId = String(payload.session_id).slice(0, 8);
  const rel = path.join(SESSIONS_DIR, project, `${day}-${shortId}.md`);
  const title = meta.title || turns[0].replace(/^\*\*User:\*\* /, "").slice(0, 80);

  const body = [
    "---",
    "type: session",
    `project: ${yamlString(project)}`,
    `session_id: ${yamlString(payload.session_id)}`,
    `branch: ${yamlString(meta.branch || "")}`,
    `started: ${meta.started || ""}`,
    `ended: ${meta.ended || ""}`,
    `compactions: ${meta.compactions}`,
    `tags: [claude-session, ${project}]`,
    "---",
    "",
    `# ${title.replace(/\n/g, " ")}`,
    "",
    ...(summaries.length
      ? ["## Compaction summaries", "", ...summaries.map((s, i) => `### Compaction ${i + 1}\n\n${s.trim()}\n`)]
      : []),
    "## Transcript",
    "",
    turns.join("\n\n"),
    "",
  ].join("\n");

  const abs = path.join(VAULT, rel);
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(abs, redact(body));
  return rel;
}

function openIndex() {
  fs.mkdirSync(CACHE_DIR, { recursive: true });
  const key = createHash("sha1").update(VAULT).digest("hex").slice(0, 12);
  const db = new DatabaseSync(path.join(CACHE_DIR, `${key}.sqlite`));
  db.exec(`
    CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, mtime REAL, size INTEGER,
      title TEXT, type TEXT, project TEXT, date TEXT, superseded INTEGER);
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
      path UNINDEXED, title, heading, body, line UNINDEXED,
      tokenize = 'porter unicode61');
  `);
  return db;
}

function walk(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith(".")) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, out);
    else if (entry.name.endsWith(".md")) out.push(full);
  }
  return out;
}

function parseFrontmatter(text) {
  const fm = {};
  const m = text.match(/^---\n([\s\S]*?)\n---\n?/);
  if (!m) return { fm, bodyStart: 0, offsetLines: 0 };
  for (const line of m[1].split("\n")) {
    const kv = line.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (kv) fm[kv[1]] = kv[2].replace(/^["']|["']$/g, "");
  }
  return { fm, bodyStart: m[0].length, offsetLines: m[0].split("\n").length - 1 };
}

function chunkMarkdown(text, offsetLines) {
  const chunks = [];
  let heading = "";
  let buf = [];
  let bufLine = offsetLines + 1;
  let size = 0;
  const lines = text.split("\n");

  const flush = () => {
    const body = buf.join("\n").trim();
    if (body) chunks.push({ heading, body, line: bufLine });
    buf = [];
    size = 0;
  };

  lines.forEach((line, i) => {
    const lineNo = offsetLines + i + 1;
    const h = line.match(/^#{1,4}\s+(.*)/);
    if (h || size > CHUNK_CHARS) {
      flush();
      bufLine = lineNo;
      if (h) heading = h[1].trim();
    }
    buf.push(line);
    size += line.length + 1;
  });
  flush();
  return chunks;
}

function syncIndex(db, { rebuild = false } = {}) {
  if (!fs.existsSync(VAULT)) return { indexed: 0, removed: 0, total: 0 };
  if (rebuild) db.exec("DELETE FROM files; DELETE FROM chunks;");

  const known = new Map(db.prepare("SELECT path, mtime, size FROM files").all().map((r) => [r.path, r]));
  const seen = new Set();
  const delChunks = db.prepare("DELETE FROM chunks WHERE path = ?");
  const delFile = db.prepare("DELETE FROM files WHERE path = ?");
  const putFile = db.prepare(
    "INSERT OR REPLACE INTO files (path, mtime, size, title, type, project, date, superseded) VALUES (?,?,?,?,?,?,?,?)",
  );
  const putChunk = db.prepare("INSERT INTO chunks (path, title, heading, body, line) VALUES (?,?,?,?,?)");
  let indexed = 0;

  db.exec("BEGIN");
  for (const abs of walk(VAULT)) {
    const rel = path.relative(VAULT, abs);
    seen.add(rel);
    const st = fs.statSync(abs);
    const prev = known.get(rel);
    if (prev && prev.mtime === st.mtimeMs && prev.size === st.size) continue;

    const text = fs.readFileSync(abs, "utf8");
    const { fm, bodyStart, offsetLines } = parseFrontmatter(text);
    const body = text.slice(bodyStart);
    const title = body.match(/^#\s+(.+)$/m)?.[1]?.trim() || path.basename(rel, ".md");
    const date = (fm.ended || fm.date || fm.started || new Date(st.mtimeMs).toISOString()).slice(0, 10);
    const superseded = fm.status === "superseded" || Boolean(fm.superseded_by) ? 1 : 0;

    delChunks.run(rel);
    putFile.run(rel, st.mtimeMs, st.size, title, fm.type || "note", fm.project || "", date, superseded);
    for (const c of chunkMarkdown(body, offsetLines)) putChunk.run(rel, title, c.heading, c.body, c.line);
    indexed++;
  }
  let removed = 0;
  for (const rel of known.keys()) {
    if (seen.has(rel)) continue;
    delChunks.run(rel);
    delFile.run(rel);
    removed++;
  }
  db.exec("COMMIT");
  return { indexed, removed, total: seen.size };
}

function toMatchExpr(query, joiner) {
  const terms = query.match(/[\p{L}\p{N}_]+/gu) || [];
  return terms.map((t) => `"${t}"`).join(joiner);
}

function search(db, query, { limit = 8, project, type, all = false } = {}) {
  const filters = [];
  const params = [];
  if (!all) filters.push("f.superseded = 0");
  if (project) {
    filters.push("f.project = ?");
    params.push(project);
  }
  if (type) {
    filters.push("f.type = ?");
    params.push(type);
  }
  const where = filters.length ? `AND ${filters.join(" AND ")}` : "";
  const sql = `
    SELECT c.path, c.heading, c.line, f.date, f.type, f.title,
           bm25(chunks, 0, 6, 3, 1) AS score,
           snippet(chunks, 3, '**', '**', ' … ', 18) AS snip
    FROM chunks c JOIN files f ON f.path = c.path
    WHERE chunks MATCH ? ${where}
    ORDER BY score LIMIT ?`;
  const stmt = db.prepare(sql);

  // AND first for precision; fall back to OR so a single unmatched term
  // doesn't zero out an otherwise relevant query.
  for (const joiner of [" ", " OR "]) {
    const expr = toMatchExpr(query, joiner);
    if (!expr) return [];
    const rows = stmt.all(expr, ...params, limit * 4);
    if (!rows.length) continue;
    const perFile = new Map();
    const picked = [];
    for (const r of rows) {
      const n = perFile.get(r.path) || 0;
      if (n >= 2) continue;
      perFile.set(r.path, n + 1);
      picked.push(r);
      if (picked.length >= limit) break;
    }
    return picked;
  }
  return [];
}

function readStdin() {
  try {
    return fs.readFileSync(0, "utf8");
  } catch {
    return "";
  }
}

function cmdSearch({ positional, flags }) {
  const query = positional.join(" ");
  if (!query) throw new Error("usage: vault.mjs search <query> [--limit N] [--project P] [--type session|note] [--all]");
  const db = openIndex();
  syncIndex(db);
  const rows = search(db, query, {
    limit: Number(flags.limit) || 8,
    project: flags.project,
    type: flags.type,
    all: Boolean(flags.all),
  });
  if (!rows.length) {
    console.log(`no matches for "${query}" in ${VAULT}`);
    return;
  }
  for (const r of rows) {
    const where = r.heading ? ` § ${r.heading}` : "";
    console.log(`${r.path}:${r.line}  [${r.type} ${r.date}]${where}`);
    console.log(`  ${r.snip.replace(/\s+/g, " ").trim()}`);
  }
}

function cmdRead({ positional, flags }) {
  const rel = positional[0];
  if (!rel) throw new Error("usage: vault.mjs read <path> [--lines A:B] [--section heading] [--max-chars N]");
  const abs = path.resolve(VAULT, rel);
  if (!abs.startsWith(VAULT + path.sep)) throw new Error("path escapes the vault");
  const lines = fs.readFileSync(abs, "utf8").split("\n");
  const maxChars = Number(flags["max-chars"]) || 6000;

  let from = 1;
  let to = lines.length;
  if (flags.lines) {
    const [a, b] = String(flags.lines).split(":").map(Number);
    from = Math.max(1, a || 1);
    to = Math.min(lines.length, b || from + 60);
  } else if (flags.section) {
    const want = String(flags.section).toLowerCase();
    const start = lines.findIndex((l) => /^#{1,6}\s/.test(l) && l.toLowerCase().includes(want));
    if (start === -1) throw new Error(`no heading containing "${flags.section}"`);
    const level = lines[start].match(/^#+/)[0].length;
    const end = lines.findIndex((l, i) => i > start && new RegExp(`^#{1,${level}}\\s`).test(l));
    from = start + 1;
    to = end === -1 ? lines.length : end;
  }

  let out = "";
  let last = from - 1;
  for (let i = from; i <= to; i++) {
    const next = `${i}\t${lines[i - 1]}\n`;
    if (out.length + next.length > maxChars) break;
    out += next;
    last = i;
  }
  process.stdout.write(out);
  if (last < to) console.log(`[truncated at line ${last} of ${to}; continue with --lines ${last + 1}:${to}]`);
}

function cmdRecent({ flags }) {
  const db = openIndex();
  syncIndex(db);
  const params = [];
  let where = "WHERE superseded = 0";
  if (flags.project) {
    where += " AND project = ?";
    params.push(flags.project);
  }
  if (flags.type) {
    where += " AND type = ?";
    params.push(flags.type);
  }
  const rows = db
    .prepare(`SELECT path, title, type, date FROM files ${where} ORDER BY date DESC, mtime DESC LIMIT ?`)
    .all(...params, Number(flags.limit) || 10);
  for (const r of rows) console.log(`${r.path}  [${r.type} ${r.date}]  ${r.title}`);
}

function cmdNote({ flags }) {
  const title = flags.title;
  if (!title || title === true) throw new Error('usage: echo "body" | vault.mjs note --title "..." [--project P] [--tags a,b]');
  const body = readStdin().trim();
  if (!body) throw new Error("note body is empty; pipe it on stdin");
  const project = flags.project && flags.project !== true ? flags.project : projectName(process.cwd());
  const tags = ["claude-note", project, ...String(flags.tags || "").split(",").filter(Boolean)];
  const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60);
  const rel = path.join(NOTES_DIR, project, `${slug}.md`);
  const abs = path.join(VAULT, rel);
  const today = new Date().toISOString().slice(0, 10);

  fs.mkdirSync(path.dirname(abs), { recursive: true });
  const existed = fs.existsSync(abs);
  const doc = [
    "---",
    "type: note",
    `project: ${yamlString(project)}`,
    `date: ${today}`,
    `tags: [${tags.join(", ")}]`,
    "---",
    "",
    `# ${title}`,
    "",
    body,
    "",
  ].join("\n");
  fs.writeFileSync(abs, redact(doc));
  console.log(`${existed ? "updated" : "wrote"} ${rel}`);
}

function recallBlock(payload) {
  const cwd = payload.cwd || process.cwd();
  if (!fs.existsSync(VAULT) || isExcluded(cwd)) return "";
  const project = projectName(cwd);
  const db = openIndex();
  syncIndex(db);

  const recent = db
    .prepare(
      `SELECT path, title, type, date FROM files
       WHERE project = ? AND superseded = 0 ORDER BY date DESC, mtime DESC LIMIT 5`,
    )
    .all(project);
  const total = db.prepare("SELECT COUNT(*) AS n FROM files WHERE project = ?").get(project).n;
  // An empty pointer still steers the model into searching; say nothing instead.
  if (total === 0) return "";
  // argv[1] keeps the symlinked install path; import.meta resolves through it
  // to wherever the checkout happens to live.
  const script = path.resolve(process.argv[1]);

  const lines = [
    `Vault memory: ${VAULT} (${total} notes for project "${project}"). Search it only when the task depends on an earlier session — a past decision, a prior attempt, or detail lost to compaction:`,
    `  node ${script} search "<terms>" --project ${project}`,
    `  node ${script} read <path> --lines A:B`,
  ];
  if (payload.source === "compact") {
    const archived = recent.find((r) => r.path.includes(String(payload.session_id).slice(0, 8)));
    if (archived) {
      lines.push(
        `This session was just compacted. The full pre-compaction transcript (prompts, replies, tool calls) is archived at ${archived.path}; search it for specifics the summary dropped instead of redoing the work.`,
      );
    }
  }
  if (recent.length) {
    lines.push("Recent notes:");
    for (const r of recent) lines.push(`  ${r.path} [${r.type} ${r.date}] ${r.title}`);
  }
  let out = lines.join("\n");
  if (out.length > RECALL_BUDGET) out = `${out.slice(0, RECALL_BUDGET)}\n[recall truncated]`;
  return out;
}

function cmdHook() {
  const raw = readStdin();
  let payload;
  try {
    payload = JSON.parse(raw);
  } catch {
    return;
  }
  // A hook must never break the session it runs in; report and exit 0.
  try {
    switch (payload.hook_event_name) {
      case "PreCompact":
      case "SessionEnd":
        archiveSession(payload);
        break;
      case "SessionStart": {
        const block = recallBlock(payload);
        if (block) process.stdout.write(block + "\n");
        break;
      }
    }
  } catch (err) {
    console.error(`vault-memory: ${err.message}`);
  }
}

function cmdIndex({ flags }) {
  const db = openIndex();
  const r = syncIndex(db, { rebuild: Boolean(flags.rebuild) });
  console.log(`vault ${VAULT}: ${r.total} files, ${r.indexed} (re)indexed, ${r.removed} removed`);
}

function cmdArchive({ positional }) {
  const file = positional[0];
  if (!file) throw new Error("usage: vault.mjs archive <transcript.jsonl> [cwd]");
  const session_id = path.basename(file, ".jsonl");
  const rel = archiveSession({ transcript_path: file, session_id, cwd: positional[1] || process.cwd() });
  console.log(rel ? `archived ${rel}` : "nothing archived (excluded, missing, or empty)");
}

const commands = {
  search: cmdSearch,
  read: cmdRead,
  recent: cmdRecent,
  note: cmdNote,
  index: cmdIndex,
  archive: cmdArchive,
  hook: cmdHook,
};

const [name, ...rest] = process.argv.slice(2);
const command = commands[name];
if (!command) {
  console.error(`usage: vault.mjs <${Object.keys(commands).join("|")}> ...`);
  process.exit(2);
}
try {
  command(parseArgs(rest));
} catch (err) {
  console.error(err.message);
  process.exit(1);
}
