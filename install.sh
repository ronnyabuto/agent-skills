#!/usr/bin/env bash
# Installs these skills for Claude Code (and Antigravity, if present):
#   - symlinks every skill folder into ~/.claude/skills/
#   - merges vault-memory's hooks and AGENT_VAULT into ~/.claude/settings.json
#
#   ./install.sh                     interactive: asks for the vault path
#   ./install.sh --vault ~/notes     non-interactive
#   ./install.sh --no-hooks          skills only; leave settings.json alone
#   ./install.sh --dry-run           show what would change, change nothing
#   ./install.sh --uninstall         remove the symlinks and hooks this installs
#
# Safe to re-run: existing links and hooks are left as they are, and
# settings.json is backed up before it's written.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SETTINGS="$CLAUDE_DIR/settings.json"
ANTIGRAVITY_SKILLS="$HOME/.gemini/antigravity/skills"
if [ "$CLAUDE_DIR" = "$HOME/.claude" ]; then
  HOOK_CMD="node ~/.claude/skills/vault-memory/scripts/vault.mjs hook"
else
  HOOK_CMD="node $CLAUDE_DIR/skills/vault-memory/scripts/vault.mjs hook"
fi

VAULT=""
HOOKS=1
DRY=0
UNINSTALL=0

usage() { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --vault) VAULT="${2:?--vault needs a path}"; shift 2 ;;
    --no-hooks) HOOKS=0; shift ;;
    --dry-run) DRY=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

say() { printf '%s\n' "$*"; }
run() { if [ "$DRY" = 1 ]; then say "  [dry-run] $*"; else "$@"; fi; }

skills() {
  for d in "$REPO"/*/; do
    [ -f "$d/SKILL.md" ] && basename "$d"
  done
}

node_ok() {
  command -v node >/dev/null 2>&1 || return 1
  node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>22||(a===22&&b>=5)?0:1)'
}

link_skills() {
  local target_dir="$1" label="$2"
  run mkdir -p "$target_dir"
  for s in $(skills); do
    local dest="$target_dir/$s"
    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$REPO/$s" ]; then
      say "  ok      $label/$s"
    elif [ -L "$dest" ]; then
      say "  skip    $label/$s -> $(readlink "$dest") (links elsewhere; remove it to relink)"
    elif [ -e "$dest" ]; then
      say "  skip    $label/$s (a real folder is already there; not overwriting)"
    else
      run ln -s "$REPO/$s" "$dest"
      say "  linked  $label/$s"
    fi
  done
}

unlink_skills() {
  local target_dir="$1" label="$2"
  for s in $(skills); do
    local dest="$target_dir/$s"
    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$REPO/$s" ]; then
      run rm "$dest"
      say "  removed $label/$s"
    fi
  done
}

# Edits settings.json as JSON (never with sed) so every other key survives.
# Our hooks are recognised by their command string, which makes re-runs and
# uninstall exact.
edit_settings() {
  local mode="$1"
  SETTINGS="$SETTINGS" HOOK_CMD="$HOOK_CMD" VAULT="${VAULT:-}" MODE="$mode" DRY="$DRY" \
  HOOKS_FILE="$REPO/vault-memory/references/hooks.json" node <<'EOF'
const fs = require("fs");
const { SETTINGS, HOOK_CMD, VAULT, MODE, DRY, HOOKS_FILE } = process.env;

let settings = {};
if (fs.existsSync(SETTINGS)) {
  try {
    settings = JSON.parse(fs.readFileSync(SETTINGS, "utf8"));
  } catch (err) {
    console.error(`  ${SETTINGS} isn't valid JSON (${err.message}); not touching it.`);
    process.exit(1);
  }
}
const before = JSON.stringify(settings);
// Match on the script path, not the exact string, so hooks added by hand
// (absolute path, ~ path, different node binary) count as already installed.
const ours = (h) =>
  h && h.type === "command" && /vault-memory\/scripts\/vault\.mjs hook\s*$/.test(h.command ?? "");

if (MODE === "install") {
  const template = JSON.parse(fs.readFileSync(HOOKS_FILE, "utf8")).hooks;
  settings.hooks ??= {};
  for (const [event, groups] of Object.entries(template)) {
    const existing = settings.hooks[event] ?? [];
    if (existing.some((g) => (g.hooks ?? []).some(ours))) {
      console.log(`  ok      ${event} hook`);
      continue;
    }
    const added = groups.map((g) => ({ ...g, hooks: g.hooks.map((h) => ({ ...h, command: HOOK_CMD })) }));
    settings.hooks[event] = [...existing, ...added];
    console.log(`  added   ${event} hook`);
  }
  settings.env ??= {};
  if (settings.env.AGENT_VAULT && settings.env.AGENT_VAULT !== VAULT) {
    console.log(`  kept    AGENT_VAULT=${settings.env.AGENT_VAULT} (already set; edit settings.json to change it)`);
  } else {
    if (settings.env.AGENT_VAULT !== VAULT) console.log(`  set     AGENT_VAULT=${VAULT}`);
    else console.log(`  ok      AGENT_VAULT=${VAULT}`);
    settings.env.AGENT_VAULT = VAULT;
  }
} else {
  for (const [event, groups] of Object.entries(settings.hooks ?? {})) {
    const kept = groups
      .map((g) => ({ ...g, hooks: (g.hooks ?? []).filter((h) => !ours(h)) }))
      .filter((g) => g.hooks.length);
    if (kept.length !== groups.length) console.log(`  removed ${event} hook`);
    if (kept.length) settings.hooks[event] = kept;
    else delete settings.hooks[event];
  }
  if (settings.hooks && !Object.keys(settings.hooks).length) delete settings.hooks;
  // AGENT_VAULT stays: it points at the user's notes, which uninstall doesn't touch.
}

if (JSON.stringify(settings) === before) {
  console.log("  settings.json unchanged");
} else if (DRY === "1") {
  console.log(`  [dry-run] would write ${SETTINGS}`);
} else {
  if (fs.existsSync(SETTINGS)) {
    const backup = `${SETTINGS}.bak-${new Date().toISOString().replace(/[:.]/g, "-")}`;
    fs.copyFileSync(SETTINGS, backup);
    console.log(`  backup  ${backup}`);
  }
  fs.mkdirSync(require("path").dirname(SETTINGS), { recursive: true });
  fs.writeFileSync(SETTINGS, JSON.stringify(settings, null, 2) + "\n");
  console.log(`  wrote   ${SETTINGS}`);
}
EOF
}

if [ "$UNINSTALL" = 1 ]; then
  say "Removing skill links that point into $REPO"
  unlink_skills "$CLAUDE_DIR/skills" "~/.claude/skills"
  [ -d "$ANTIGRAVITY_SKILLS" ] && unlink_skills "$ANTIGRAVITY_SKILLS" "antigravity"
  if [ -f "$SETTINGS" ] && command -v node >/dev/null 2>&1; then
    say "Removing vault-memory hooks from $SETTINGS"
    edit_settings uninstall
  fi
  say "Done. Vault notes and AGENT_VAULT were left in place."
  exit 0
fi

say "Linking skills from $REPO"
link_skills "$CLAUDE_DIR/skills" "~/.claude/skills"
if [ -d "$(dirname "$ANTIGRAVITY_SKILLS")" ]; then
  link_skills "$ANTIGRAVITY_SKILLS" "antigravity"
fi

if [ "$HOOKS" = 0 ]; then
  say "Skipping hooks (--no-hooks). vault-memory still works when asked, but won't archive sessions automatically."
  exit 0
fi

if ! node_ok; then
  say "vault-memory needs Node >= 22.5 (found: $(node --version 2>/dev/null || echo none))."
  say "Skills are linked; hooks were NOT installed. Install Node 22.5+ and re-run ./install.sh."
  exit 1
fi

if [ -z "$VAULT" ]; then
  default="$HOME/agent-vault"
  if [ -t 0 ]; then
    say ""
    say "vault-memory archives each Claude Code session as Markdown in a vault folder."
    say "Any folder works; an existing Obsidian vault is fine (Obsidian itself is optional)."
    read -r -p "Vault path [$default]: " VAULT
  fi
  VAULT="${VAULT:-$default}"
fi
VAULT="${VAULT/#\~/$HOME}"
case "$VAULT" in /*) ;; *) VAULT="$PWD/$VAULT" ;; esac

say "Configuring vault-memory in $SETTINGS"
edit_settings install

# Session archives can hold anything that was said in a session. If the vault
# sits inside a git repo, make sure they can't be committed by accident.
if git -C "$VAULT" rev-parse --show-toplevel >/dev/null 2>&1; then
  top="$(git -C "$VAULT" rev-parse --show-toplevel)"
  rel="$(realpath --relative-to="$top" "$VAULT/claude" 2>/dev/null || echo claude)"
  if ! git -C "$top" check-ignore -q "$rel/" 2>/dev/null; then
    say ""
    say "WARNING: the vault is inside the git repo $top, and $rel/ is not ignored."
    say "Session archives could be committed and pushed. Add this line to $top/.gitignore:"
    say "  $rel/"
  fi
fi

say ""
say "Done. Start a new Claude Code session (or run /hooks) to load the hooks."
say "Optional: open $VAULT in Obsidian to browse archived sessions."
