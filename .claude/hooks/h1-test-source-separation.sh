#!/usr/bin/env bash
# H1 at edit time (AGENTS.md, Hard rules). Registered in .claude/settings.json as a PreToolUse hook
# for Edit|Write|MultiEdit. Reads the tool call as JSON on stdin; exit 2 blocks the call and sends
# stderr back to the model, so every refusal below names the cheapest compliant path.
set -u

input=$(cat)
# Parse the tool call with jq, or python3 when jq is absent. With neither, refuse loudly rather than wave edits through.
if command -v jq >/dev/null; then
  file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.path // empty')
  cwd=$(printf '%s' "$input" | jq -r '.cwd // empty')
elif command -v python3 >/dev/null; then
  file=$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); t=d.get("tool_input") or {}; print(t.get("file_path") or t.get("path") or "")')
  cwd=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("cwd") or "")')
else
  printf 'H1 hook cannot run: needs jq or python3 on PATH.\n' >&2; exit 2
fi
[ -z "$file" ] && exit 0
[ -n "$cwd" ] && cd "$cwd"

root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
case "$file" in "$root"/*) rel=${file#"$root"/} ;; *) rel=$file ;; esac
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0
type=${branch%%/*}

refuse() { printf 'H1 hook refused editing %s\n%s\n' "$rel" "$1" >&2; exit 2; }

case "$rel" in
  src/*|tests/*)
    case "$type" in
      chore|renew|policy)
        refuse "A $type/ branch may not touch src/ or tests/. Safe path: git checkout -b feature/<slug> (or fix/, refactor/, test/)." ;;
    esac ;;
esac

case "$rel" in
  src/*)
    if [ -n "$(git status --porcelain -- tests/ 2>/dev/null)" ]; then
      refuse "tests/ has uncommitted changes. Tests are committed before the implementation (BLIND registration).
Safe path: git add tests && git commit -m 'test: <what the tests pin down>' — then edit src/."
    fi ;;
  tests/*)
    if [ "$type" != "test" ] && git cat-file -e "HEAD:$rel" 2>/dev/null; then
      refuse "$rel already exists; modifying an existing test is H1.
Safe path: if the test is wrong, file BLOCKED TEST-DEFECT (3 lines) and a test/ branch adjudicates.
If you need a new test, create a new file under tests/ instead."
    fi ;;
esac

exit 0
