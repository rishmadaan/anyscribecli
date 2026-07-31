#!/usr/bin/env bash
#
# rehearse-migration.sh — the migration safety net.
#
# Builds a realistic fake anyscribecli user inside a THROWAWAY $HOME, installs
# the local renamed package into a throwaway venv, runs the real
# `anyscribe migrate`, and asserts nothing was lost. This is the harness that
# would have caught the two real-home escapes this project already suffered.
#
# Rish will read this to decide whether to trust the migration — keep it plain.
#
set -euo pipefail

# Repo root = the worktree this script lives in (the renamed package we install).
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --- MANDATORY SAFETY GUARD ------------------------------------------------
# Everything below runs against $HOME, and migrate() MOVES ~/.anyscribecli and
# writes ~/.claude. A bug here would destroy the real user's API keys. So the
# fake HOME is a mktemp dir, and we refuse to proceed unless HOME is inside it.
REAL_HOME="$HOME"
FAKE_ROOT="$(mktemp -d)"
trap 'rm -rf "$FAKE_ROOT"' EXIT
export HOME="$FAKE_ROOT"

case "$HOME" in
  /tmp/*|/var/folders/*|/private/var/folders/*|/private/tmp/*) : ;;
  *) echo "ABORT: HOME=$HOME is not a temp dir — refusing to run"; exit 1 ;;
esac
[ "$HOME" != "$REAL_HOME" ] || { echo "ABORT: HOME did not change"; exit 1; }
[ -d "$HOME" ] || { echo "ABORT: HOME is not a directory"; exit 1; }
echo "safe HOME: $HOME"

# --- throwaway venv with the local renamed package -------------------------
# Isolation is by real environment, not monkeypatch: a venv under the fake HOME.
# We never install into the system/user env.
VENV="$FAKE_ROOT/venv"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet "$REPO"
echo "installed $REPO into $VENV"

# --- assertion plumbing ----------------------------------------------------
FAILS=0
check() {  # check "description" <command...>  — command's exit status is the verdict
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "PASS: $desc"
  else
    echo "FAIL: $desc"
    FAILS=$((FAILS + 1))
  fi
}

# Recognizable fake keys — asserted present with IDENTICAL values after migrate.
KEY1="AS_FAKE_OPENAI_KEY=sk-fake-openai-111"
KEY2="AS_FAKE_DEEPGRAM_KEY=dg-fake-222"
KEY3="AS_FAKE_ELEVENLABS_KEY=el-fake-333"
CUSTOM_WS="$FAKE_ROOT/my-custom-vault"   # non-default workspace_path

seed_legacy() {  # seed_legacy <home> — build a populated ~/.anyscribecli + ~/.claude
  local h="$1"
  mkdir -p "$h/.anyscribecli/sessions" "$h/.anyscribecli/downloads/audio" "$h/.claude/skills/scribe"
  printf '%s\n%s\n%s\n' "$KEY1" "$KEY2" "$KEY3" > "$h/.anyscribecli/.env"
  printf 'workspace_path: %s\nquality: balanced\n' "$CUSTOM_WS" > "$h/.anyscribecli/config.yaml"
  local i
  for i in 1 2 3 4 5 6 7 8; do echo '{}' > "$h/.anyscribecli/sessions/session-$i.json"; done
  echo "fake audio" > "$h/.anyscribecli/downloads/audio/clip.mp3"
  echo "# stale scribe skill" > "$h/.claude/skills/scribe/SKILL.md"
  cat > "$h/.claude.json" <<'JSON'
{
  "mcpServers": {
    "scribe": {"command": "scribe-mcp", "args": []}
  },
  "projects": {
    "/some/project": {
      "mcpServers": {
        "scribe": {"command": "scribe-mcp", "args": []}
      }
    }
  }
}
JSON
}

# Validates ~/.claude.json: still parseable, and every mcpServers block uses the
# "anyscribe" key, never the old "scribe" key. Exact key match (dict membership),
# so "anyscribe" is not mistaken for containing "scribe".
claude_json_ok() {
  "$VENV/bin/python" - "$1" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
def blocks(node):
    if isinstance(node, dict):
        s = node.get("mcpServers")
        if isinstance(s, dict):
            yield s
        for v in node.values():
            yield from blocks(v)
    elif isinstance(node, list):
        for v in node:
            yield from blocks(v)
bs = list(blocks(data))
ok = bool(bs) and all("anyscribe" in b and "scribe" not in b for b in bs)
sys.exit(0 if ok else 1)
PY
}

# ===========================================================================
# CASE 1 — clean upgrade: populated legacy dir, no new dir yet. Full assertions.
# ===========================================================================
echo
echo "== CASE 1: clean upgrade (populated ~/.anyscribecli, no ~/.anyscribe) =="
export HOME="$FAKE_ROOT/home1"
mkdir -p "$HOME"
seed_legacy "$HOME"
"$VENV/bin/anyscribe" migrate

check "3 keys land in ~/.anyscribe/.env, value 1 identical" grep -qxF "$KEY1" "$HOME/.anyscribe/.env"
check "3 keys land in ~/.anyscribe/.env, value 2 identical" grep -qxF "$KEY2" "$HOME/.anyscribe/.env"
check "3 keys land in ~/.anyscribe/.env, value 3 identical" grep -qxF "$KEY3" "$HOME/.anyscribe/.env"
check "workspace_path preserved" grep -qF "workspace_path: $CUSTOM_WS" "$HOME/.anyscribe/config.yaml"
sess=$(find "$HOME/.anyscribe/sessions" -maxdepth 1 -type f | wc -l | tr -d ' ')
check "all 8 session files present (found $sess)" [ "$sess" = "8" ]
check "audio download carried over" [ -f "$HOME/.anyscribe/downloads/audio/clip.mp3" ]
check "stale ~/.claude/skills/scribe removed" [ ! -e "$HOME/.claude/skills/scribe" ]
check "new ~/.claude/skills/anyscribe installed" [ -f "$HOME/.claude/skills/anyscribe/SKILL.md" ]
check "~/.claude.json valid JSON, mcp is anyscribe not scribe" claude_json_ok "$HOME/.claude.json"
check "legacy ~/.anyscribecli no longer present" [ ! -e "$HOME/.anyscribecli" ]
for c in anyscribe scribe ascli; do
  check "command '$c' resolves on venv PATH" [ -x "$VENV/bin/$c" ]
done

# ===========================================================================
# CASE 2 — both-dirs stranding: an EMPTY ~/.anyscribe next to a populated legacy
# dir. This is the exact shape that strands keys. Assert they still arrive.
# ===========================================================================
echo
echo "== CASE 2: both dirs exist (empty ~/.anyscribe + populated legacy) =="
export HOME="$FAKE_ROOT/home2"
mkdir -p "$HOME"
seed_legacy "$HOME"
mkdir -p "$HOME/.anyscribe"          # the empty new home that would strand keys
"$VENV/bin/anyscribe" migrate

check "keys still arrive despite empty new home, value 1" grep -qxF "$KEY1" "$HOME/.anyscribe/.env"
check "keys still arrive despite empty new home, value 2" grep -qxF "$KEY2" "$HOME/.anyscribe/.env"
check "keys still arrive despite empty new home, value 3" grep -qxF "$KEY3" "$HOME/.anyscribe/.env"

# --- verdict ---------------------------------------------------------------
echo
if [ "$FAILS" -eq 0 ]; then
  echo "PASS — migration preserved everything across both cases."
  exit 0
else
  echo "FAIL — $FAILS assertion(s) failed. Do NOT trust the migration."
  exit 1
fi
