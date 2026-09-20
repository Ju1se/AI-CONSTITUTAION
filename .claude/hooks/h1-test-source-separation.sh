#!/usr/bin/env bash
# H1 at edit time (AGENTS.md, Hard rules). Registered in .claude/settings.json as a PreToolUse hook
# for Edit|Write|MultiEdit. Reads the tool call as JSON on stdin; exit 2 blocks the call and sends
# stderr back to the model, so every refusal below names the cheapest compliant path.
# This hook is fast feedback, not the merge decision: the gate (scripts/gate_checks.py) re-checks the
# committed history, and file permissions / branch protection are the real boundary. Its matcher sees
# Edit|Write|MultiEdit only, so a shell write is not covered.
set -u

refuse() { printf 'H1 hook refused: %s\n' "$1" >&2; exit 2; }

input=$(cat)
# Parse the tool call with jq, or python3 when jq is absent. A parse failure refuses (audit P21):
# an unreadable request is never waved through.
if command -v jq >/dev/null; then
  file=$(printf '%s' "$input" | jq -er '.tool_input.file_path // .tool_input.path // ""') || refuse "tool input is not valid JSON"
  cwd=$(printf '%s' "$input" | jq -er '.cwd // ""') || refuse "tool input is not valid JSON"
elif command -v python3 >/dev/null; then
  file=$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); t=d.get("tool_input") or {}; print(t.get("file_path") or t.get("path") or "")') || refuse "tool input is not valid JSON"
  cwd=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("cwd") or "")') || refuse "tool input is not valid JSON"
else
  refuse "needs jq or python3 on PATH"
fi
[ -z "$file" ] && exit 0
[ -n "$cwd" ] && { cd "$cwd" || refuse "cannot enter cwd $cwd"; }

root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
root=$(cd "$root" && pwd -P)
# Normalize the path (audit P20): resolve ., .. and symlinks in the parent so /./ or ../ cannot dodge a
# rule. When the parent does not exist yet, walk up to the nearest one that does, so a new file in a new
# directory is still judged (audit EV-08).
case "$file" in /*) abs=$file ;; *) abs=$PWD/$file ;; esac
name=$(basename "$abs"); dir=$(dirname "$abs")
while [ ! -d "$dir" ] && [ "$dir" != "/" ]; do name=$(basename "$dir")/$name; dir=$(dirname "$dir"); done
abs=$(cd "$dir" 2>/dev/null && pwd -P)/$name
case "$abs" in "$root"/*) rel=${abs#"$root"/} ;; *) exit 0 ;; esac   # outside the repository: not ours to judge
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0
type=${branch%%/*}

# The frozen set the gate enforces: tests/, the verifier's own corpus, and every conftest.py.
# tests/MOCK_ALLOWLIST is a policy file, not a test (audit P23).
is_test_file() {
  case "$1" in
    tests/MOCK_ALLOWLIST) return 1 ;;
    tests/*|scripts/tests/*) return 0 ;;
    conftest.py|*/conftest.py) return 0 ;;
    *) return 1 ;;
  esac
}

case "$rel" in
  src/*|tests/*)
    case "$type" in
      chore)
        refuse "a chore change may not touch src/ or tests/ ($rel).
Safe path: git checkout -b feature/<slug> (or fix/, refactor/, test/)." ;;
      policy)
        # A policy change owns the protected set; under tests/ that is the allowlist and the gate's corpus.
        case "$rel" in
          tests/MOCK_ALLOWLIST|scripts/tests/*) ;;
          *) refuse "a policy change touches the protected set only ($rel).
Safe path: git checkout -b feature/<slug> (or fix/, refactor/, test/) for src/ and tests/." ;;
        esac ;;
      renew)
        # A SUNSET tag lives on a code line, so a renew necessarily edits src/ or tests/ (audit RT-07).
        # The gate checks that only the tag changed; the hook does not stand in its way.
        : ;;
    esac ;;
esac

if [ "${rel#src/}" != "$rel" ]; then
  if [ -n "$(git status --porcelain -- tests/ ':!tests/MOCK_ALLOWLIST' 2>/dev/null)" ]; then
    refuse "editing $rel while tests/ has uncommitted changes. Tests are committed before the implementation (BLIND registration).
Safe path: git add tests && git commit -m 'test: <what the tests pin down>' — then edit src/."
  fi
elif is_test_file "$rel"; then
  if [ "$type" != "test" ] && git cat-file -e "HEAD:$rel" 2>/dev/null; then
    refuse "$rel already exists; modifying a committed test is H1.
Safe path: if the test is wrong, file BLOCKED TEST-DEFECT (3 lines) and a test/ branch adjudicates.
If you need a new test, create a new file under tests/ instead."
  fi
fi

exit 0
