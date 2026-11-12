# Vault Memory — setup and internals

## Setup (once per machine)

If `~/.claude/settings.json` has no hook running `vault.mjs hook`, sessions
aren't being archived. The repo's `install.sh` does steps 1–2 (ask the user before running it — it
edits their global settings):

1. Merge [hooks.json](hooks.json) into
   `~/.claude/settings.json`. Hooks declared in skill frontmatter only
   register after the skill is invoked, so session-wide archiving has to
   live in settings.
2. Set `AGENT_VAULT` in that file's `env` block (default `~/agent-vault`).
   Keep this folder outside source trees; `.gitignore` does not exclude it
   from zip/tar or workspace shares. The installer preserves an existing
   `AGENT_VAULT`; change that setting directly when relocating memory.
   Settings `env` reaches hooks however Claude Code was launched; a shell
   profile export doesn't reach the desktop app or IDE sessions. An
   existing Obsidian vault works; open the folder as a vault in Obsidian to
   browse, link, and graph the archives.
3. Set `VAULT_MEMORY_EXCLUDE` for projects whose transcripts must never
   leave Claude Code's own directory (e.g. `visitflow,other`), matched as
   substrings of the session's working directory. Excluded projects are
   neither archived nor recalled.
   Use it for projects with regulated data, and keep the vault out of public sync.
4. Optional: `node vault.mjs index` to build the index up front. Otherwise
   the first hook or search builds it (~7 s per 3,000 notes, once; after
   that each call re-indexes only changed files, ~120 ms total).

The index lives in `~/.cache/vault-memory/`, outside the vault, so it never
syncs or shows up in Obsidian.

## Concurrency

- **Concurrent indexing** uses WAL and serialized write transactions. WAL
  initialization retries only `SQLITE_BUSY` for up to five seconds; indexing
  transactions retain a five-second busy timeout. Persistent locks still fail;
  hooks log the error without interrupting the Claude session.
- **Concurrent sessions** write separate archive files (keyed by session
  id), but two sessions filing a note with the same title overwrite each
  other — last write wins.

## Repository identity and legacy notes

New notes and archives use a readable label plus a hash of the absolute Git
common-directory path, so linked worktrees share identity and unrelated
same-named repositories do not. Outside Git, the resolved directory is hashed.
Moving a repository changes its identity; existing files are never migrated or
deleted automatically. Use an explicit `--project <old-id>` to recall them.

Legacy basename notes remain searchable with their original `--project <name>`
and readable at their original paths. Hooks report a legacy group separately
without injecting its note titles or assuming ownership. Verify its sources
before using it: legacy notes contain no reliable repository identity.
