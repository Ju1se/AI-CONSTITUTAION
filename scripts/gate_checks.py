#!/usr/bin/env python3
"""Mechanical checks for the merge gate described in AGENTS.md.

    gate_checks.py <check>        checks: type h1 mocks masking sunset records deps audit-select

Exit 0 = pass, 1 = refused, 3 = usage or environment problem.
Parts that are not implemented yet print a line containing TEXT-ONLY and do not fail,
so the gate keeps running and the count stays visible (docs/agents-policy.md §7.1).
Configuration arrives as environment variables exported by the Makefile from policy.mk.
Every refusal names the cheapest compliant path — that message is the policy's real interface.
"""
from __future__ import annotations

import datetime as dt
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

TYPES = ("feature", "fix", "refactor", "test", "chore", "renew", "policy")
MANIFESTS = ("pyproject.toml", "setup.cfg", "setup.py", "requirements.txt", "requirements-*.txt",
             "requirements/*.txt", "package.json", "Cargo.toml", "go.mod")
SUNSET_KINDS = "compat|flag|todo|masks|skip|deprecated|config|vendored"
SUNSET_RE = re.compile(
    r"SUNSET\s+(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<kind>" + SUNSET_KINDS + r")\s+owner:(?P<owner>\S+)"
    r"\s+reason:(?P<reason>.+?)(?:\s+grace:(?P<grace>\d{4}-\d{2}-\d{2}))?\s*$")
# Files that quote the tag grammar or the denylist as text rather than using them.
SELF_EXCLUDE = ("AGENTS.md", "docs/agents-policy.md", "docs/changes/_TEMPLATE.md",
                "scripts/gate_checks.py", ".claude/skills/")


# ----------------------------------------------------------------------------- helpers

def sh(*args: str, check: bool = False) -> str:
    res = subprocess.run(args, capture_output=True, text=True)
    if check and res.returncode != 0:
        die(f"command failed: {' '.join(args)}\n{res.stderr.strip()}")
    return res.stdout


def die(msg: str, code: int = 3):
    print(f"gate: {msg}", file=sys.stderr)
    sys.exit(code)


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def env_int(name: str, default: int) -> int:
    try:
        return int(env(name) or default)
    except ValueError:
        die(f"{name} must be an integer (got {env(name)!r})")


def today() -> dt.date:
    return dt.date.today()


def parse_date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


ROOT = sh("git", "rev-parse", "--show-toplevel").strip()
if not ROOT:
    die("not inside a git repository")
os.chdir(ROOT)

BRANCH = env("BRANCH") or sh("git", "rev-parse", "--abbrev-ref", "HEAD").strip()
TYPE = BRANCH.split("/", 1)[0] if "/" in BRANCH else BRANCH
SLUG = BRANCH.replace("/", "-")
BASE = env("BASE")
RECORD = f"docs/changes/{SLUG}.md"
POLICY_FILES = tuple(f for f in env("POLICY_FILES", "AGENTS.md policy.mk tests/MOCK_ALLOWLIST docs/agents-policy.md").split())


def need_base() -> str:
    if not BASE:
        die("cannot determine the merge base; pass BASE=<commit> (the gate runs on a <type>/<slug> branch off MAIN)")
    return BASE


def changed_files(diff_filter: str | None = None, *paths: str) -> list[str]:
    args = ["git", "diff", "--name-only", f"{need_base()}...HEAD"]
    if diff_filter:
        args.insert(3, f"--diff-filter={diff_filter}")
    if paths:
        args += ["--", *paths]
    return [p for p in sh(*args).splitlines() if p]


def added_lines(*paths: str) -> list[tuple[str, int, str]]:
    """(path, line_no, text) for every added line in the change."""
    args = ["git", "diff", "-U0", "--no-color", f"{need_base()}...HEAD"]
    if paths:
        args += ["--", *paths]
    out: list[tuple[str, int, str]] = []
    path, line_no = "", 0
    for raw in sh(*args).splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else raw[4:]
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            line_no = int(m.group(1)) if m else 0
        elif raw.startswith("+") and not raw.startswith("+++"):
            out.append((path, line_no, raw[1:]))
            line_no += 1
        elif not raw.startswith("-"):
            line_no += 1
    return out


def matches_any(path: str, patterns) -> bool:
    return any(path == pat or fnmatch.fnmatch(path, pat) for pat in patterns)


def under(path: str, prefix: str) -> bool:
    return path == prefix.rstrip("/") or path.startswith(prefix)


def refuse(header: str, items: list[str], safe_path: str) -> int:
    print(f"REFUSED {header}", file=sys.stderr)
    for item in items:
        print(f"  {item}", file=sys.stderr)
    print(f"  Safe path: {safe_path}", file=sys.stderr)
    return 1


def ok(msg: str) -> int:
    print(f"ok    {msg}")
    return 0


def text_only(msg: str) -> None:
    print(f"TEXT-ONLY {msg}")


def read_record() -> dict[str, list[str]] | None:
    if not os.path.exists(RECORD):
        return None
    rec: dict[str, list[str]] = {}
    with open(RECORD, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^(TYPE|WHY|SEARCHED|DEP|TESTS|ALLOWANCE|BLOCKED)\b\s*(.*)$", line.strip())
            if m:
                rec.setdefault(m.group(1), []).append(m.group(2).lstrip(": ").strip())
    return rec


def is_placeholder(value: str) -> bool:
    return not value or "<" in value


# ----------------------------------------------------------------------------- checks

def check_type() -> int:
    if TYPE not in TYPES:
        return refuse(f"branch '{BRANCH}' has no change type",
                      [f"branches are <type>/<slug> with type in {', '.join(TYPES)}"],
                      "git checkout -b feature/<slug>  (or fix/, refactor/, test/, chore/, renew/, policy/)")
    files = [f for f in changed_files() if not under(f, "docs/changes/")]
    bad: list[str] = []
    for f in files:
        in_src, in_tests = under(f, "src/"), under(f, "tests/")
        is_policy = f in POLICY_FILES
        is_manifest = matches_any(f, MANIFESTS)
        allowed = {
            "feature": in_src or in_tests or is_manifest,
            "fix": in_src or in_tests or is_manifest,
            "refactor": in_src,
            "test": in_tests and not is_policy,
            "chore": not (in_src or in_tests or is_policy),
            "renew": True,  # checked line-wise below
            "policy": is_policy or under(f, "scripts/") or under(f, ".claude/") or f == "Makefile",
        }[TYPE]
        if not allowed:
            bad.append(f)
    if bad:
        return refuse(f"a {TYPE}/ branch may not touch", bad,
                      "split the change: one branch per type (a feature that needs a policy change is two branches)")
    if TYPE == "renew":
        stray = []
        for raw in sh("git", "diff", "-U0", "--no-color", f"{need_base()}...HEAD", "--", ".", ":!docs/changes").splitlines():
            if raw[:1] in "+-" and not raw.startswith(("+++", "---")) and "SUNSET" not in raw:
                stray.append(raw[:100])
        if stray:
            return refuse("a renew/ branch may change only SUNSET tag lines", stray[:10],
                          "move the other edits to their own branch; renew edits the tag line only")
    return ok(f"check-type: {TYPE}/ branch touches only its allowed paths ({len(files)} files)")


def check_h1() -> int:
    if TYPE in ("feature", "fix", "refactor"):
        # Per commit, not against the base: a test added early in the branch and rewritten after the
        # implementation is the "tests generated from the implementation" pattern H1 exists to stop.
        touched = []
        for commit in sh("git", "rev-list", "--reverse", f"{need_base()}..HEAD").split():
            for line in sh("git", "show", "--pretty=format:", "--name-status", commit).splitlines():
                parts = line.split("\t")
                if len(parts) >= 2 and parts[0][:1] in "MDR" and any(under(p, "tests/") for p in parts[1:]):
                    touched.append(f"{commit[:10]}: {parts[0][:1]} {parts[-1]}")
        if touched:
            return refuse("H1: implementation branches may not modify, delete or rename a test once it is committed", touched,
                          "file BLOCKED TEST-DEFECT (3 lines); a test/ branch adjudicates. New assertions go in a new test file")
    if TYPE == "refactor":
        touched = changed_files("AMDR", "tests/")
        if touched:
            return refuse("refactor/ branches change no tests", touched,
                          "if behavior changed this is a feature/ or fix/; if the tests were wrong, BLOCKED TEST-DEFECT")
    if TYPE in ("feature", "fix"):
        mixed = []
        for commit in sh("git", "rev-list", "--reverse", f"{need_base()}..HEAD").split():
            files = sh("git", "show", "--pretty=format:", "--name-only", commit).split()
            if any(under(f, "src/") for f in files) and any(under(f, "tests/") for f in files):
                mixed.append(f"{commit[:10]}: touches src/ and tests/ in one commit")
        if mixed:
            return refuse("H1/BLIND: tests are committed before the implementation, never alongside it", mixed,
                          "commit tests first (git add tests && git commit -m 'test: <what>'), then implement")
    text_only("red-before-green (new tests must fail on the parent commit) is not automated yet")
    text_only(f"mutation score on touched lines >= {env('MUTATION_MIN', '0.70')} is not automated yet (suggest mutmut)")
    return ok("check-tests/H1: no existing test modified; tests and src never share a commit")


def check_mocks() -> int:
    allow_path = "tests/MOCK_ALLOWLIST"
    prefixes: list[str] = []
    if os.path.exists(allow_path):
        with open(allow_path, encoding="utf-8") as fh:
            prefixes = [ln.split("#", 1)[0].strip() for ln in fh]
            prefixes = [p for p in prefixes if p]
    pat = re.compile(r"(?:mock\.|mocker\.|^|\W)patch(?:\.object)?\(\s*(?:['\"](?P<s>[^'\"]+)['\"]|(?P<o>[A-Za-z_][\w.]*))"
                     r"|monkeypatch\.setattr\(\s*['\"](?P<m>[^'\"]+)['\"]")
    bad = []
    for path, no, text in added_lines("tests/"):
        for m in pat.finditer(text):
            target = m.group("s") or m.group("o") or m.group("m")
            if target and not any(target == p or target.startswith(p) for p in prefixes):
                bad.append(f"{path}:{no}: mocks '{target}' (not in {allow_path})")
    if bad:
        return refuse("§3: only I/O boundaries in tests/MOCK_ALLOWLIST may be mocked", bad,
                      "test the real in-repo call path; if no harness exists, BLOCKED NO-HARNESS; widening the allowlist is a policy/ change")
    return ok("check-tests/mocks: every mock target is on the allowlist")


def check_masking() -> int:
    marker = re.compile(r"#\s*(noqa|type:\s*ignore|pylint:\s*disable|pragma:\s*no cover)|@(?:pytest\.mark\.)?(?:skip|xfail)\b|@unittest\.skip|pytest\.skip\(")
    shell = re.compile(r"\|\|\s*true\b|2>\s*/dev/null")
    blind = re.compile(r"^\s*except(\s*:|\s+(Exception|BaseException)\b[^:]*:)\s*(#.*)?$")
    swallow = re.compile(r"^\s*(pass|continue|return\s*(None)?|\.\.\.)\s*(#.*)?$")
    lines = added_lines("src/", "tests/", "scripts/")
    by_pos = {(p, n): t for p, n, t in lines}
    bad = []
    for path, no, text in lines:
        if any(path.startswith(x) or path == x for x in SELF_EXCLUDE):
            continue
        if "SUNSET" in text:
            continue
        if marker.search(text):
            bad.append(f"{path}:{no}: suppression/skip marker added: {text.strip()[:80]}")
        if path.endswith((".sh", ".bash")) and shell.search(text):
            bad.append(f"{path}:{no}: shell failure masked: {text.strip()[:80]}")
        if blind.match(text):
            nxt = by_pos.get((path, no + 1), "")
            if swallow.match(nxt):
                bad.append(f"{path}:{no}: catch-all followed by '{nxt.strip()}' (error masked)")
    if bad:
        return refuse("§2: error-masking constructs", bad,
                      "re-raise with context, return a typed failure, or file BLOCKED FAILURE-SEMANTICS; a deliberate stopgap carries a `masks` SUNSET tag on the same line")
    return ok("check-masking: no masking constructs or suppression markers added")


def check_sunset() -> int:
    short, long_, max_, grace_days = (env_int("SUNSET_SHORT", 30), env_int("SUNSET_LONG", 90),
                                      env_int("SUNSET_MAX", 180), env_int("SUNSET_GRACE", 7))
    now = today()
    malformed, expired, too_long, live = [], [], [], 0
    for path in sh("git", "ls-files").splitlines():
        if any(path.startswith(x) or path == x for x in SELF_EXCLUDE):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        if "SUNSET" not in content:
            continue
        for no, line in enumerate(content.splitlines(), 1):
            if "SUNSET" not in line or "SUNSET <" in line:
                continue
            m = SUNSET_RE.search(line)
            if not m:
                if re.search(r"SUNSET\s+\d{4}", line):
                    malformed.append(f"{path}:{no}: {line.strip()[:100]}")
                continue
            live += 1
            date = parse_date(m.group("date"))
            if (date - now).days > max_:
                too_long.append(f"{path}:{no}: expires {date}, more than {max_} days out")
            if date < now:
                grace = m.group("grace")
                if grace and parse_date(grace) <= now and (now - parse_date(grace)).days <= grace_days:
                    print(f"note  sunset: {path}:{no} expired {date}, in grace until "
                          f"{parse_date(grace) + dt.timedelta(days=grace_days)} (BLOCKED SUNSET-EXPIRED filed)")
                else:
                    expired.append(f"{path}:{no}: {m.group('kind')} expired {date} owner:{m.group('owner')}")
    if malformed:
        return refuse("§5: malformed SUNSET tags", malformed,
                      f"# SUNSET YYYY-MM-DD <{SUNSET_KINDS}> owner:<task-id> reason:<one line> [grace:YYYY-MM-DD]")
    if too_long:
        return refuse(f"§5: sunset terms are {short} days (todo/masks/skip), {long_} otherwise, {max_} max", too_long,
                      "shorten the date; a stopgap that needs longer is a permanent abstraction (record + ledger debit)")
    if expired:
        return refuse("H3/§5: expired sunset tags in the tree", expired,
                      "delete the tagged code and run the suite (green: done, -2 credit); if that breaks the suite, "
                      "revert, file BLOCKED SUNSET-EXPIRED naming the failing test, append grace:<today> to the tag; "
                      "renewals happen on a renew/ branch")
    untagged = []
    if BASE:
        todo = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
        for path, no, text in added_lines("src/", "tests/", "scripts/"):
            if any(path.startswith(x) or path == x for x in SELF_EXCLUDE):
                continue
            if todo.search(text) and "SUNSET" not in text:
                untagged.append(f"{path}:{no}: {text.strip()[:80]}")
    else:
        text_only("untagged-TODO scan skipped (no BASE)")
    if untagged:
        return refuse("§5: temporary markers need a sunset tag", untagged,
                      f"# SUNSET {now + dt.timedelta(days=short)} todo owner:{SLUG} reason:<one line>  — or just do it now")
    text_only(f"renewal count per tag <= {env('RENEWALS_MAX', '2')} is not automated yet")
    return ok(f"check-sunset: {live} live tags, none expired, no untagged temporary markers added")


def check_records() -> int:
    rec = read_record()
    if rec is None:
        return refuse(f"§6: change record missing: {RECORD}", [],
                      f"cp docs/changes/_TEMPLATE.md {RECORD} && fill TYPE/WHY as you go")
    problems = []
    rtype = (rec.get("TYPE") or [""])[0]
    if rtype != TYPE:
        problems.append(f"TYPE: is '{rtype}', branch says '{TYPE}'")
    if TYPE in ("feature", "fix") and all(is_placeholder(w) for w in rec.get("WHY", [""])):
        problems.append("WHY: one sentence — <decision> instead of <alternative>, because <clause>")
    if TYPE in ("feature", "fix", "refactor") and all(is_placeholder(t) for t in rec.get("TESTS", [""])):
        problems.append("TESTS: the exact test commands you ran")
    new_src = changed_files("A", "src/")
    if new_src and all(is_placeholder(s) for s in rec.get("SEARCHED", [""])):
        problems.append(f"SEARCHED: required — new files under src/: {', '.join(new_src[:5])}")
    manifest_changed = [f for f in changed_files("AM") if matches_any(f, MANIFESTS)]
    manifest_added = [p for p, _, t in added_lines(*manifest_changed) if t.strip() and not t.strip().startswith("#")] if manifest_changed else []
    if manifest_added and all(is_placeholder(d) for d in rec.get("DEP", [""])):
        problems.append(f"DEP: required — dependency manifest changed: {', '.join(manifest_changed)}")
    if problems:
        return refuse(f"§6: {RECORD} is incomplete", problems,
                      "each line is one sentence or one command; write it at the moment of the decision")
    if rec.get("SEARCHED"):
        text_only("SEARCHED re-run on the base commit is not automated yet")
    if rec.get("ALLOWANCE"):
        print("note  records: ALLOWANCE grant present — this change is in the 100% audit set")
    return ok(f"check-records: {RECORD} has TYPE" + (", WHY" if rec.get("WHY") else "") + (", SEARCHED" if rec.get("SEARCHED") else "") + (", DEP" if rec.get("DEP") else ""))


def check_deps() -> int:
    rec = read_record() or {}
    deps = [d for d in rec.get("DEP", []) if not is_placeholder(d)]
    if not deps:
        return ok("check-records/deps: no DEP lines to verify")
    if env("DEPS_OFFLINE") == "1":
        text_only("DEP registry check skipped explicitly (DEPS_OFFLINE=1)")
        return 0
    min_age = env_int("DEP_MIN_AGE", 30)
    bad = []
    for d in deps:
        m = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s|]+)", d)
        if not m:
            bad.append(f"'{d[:60]}' is not <name>==<version>")
            continue
        name, version = m.groups()
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:  # registry lookup only (H4 allows registries)
                data = json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                bad.append(f"{name}=={version}: not on PyPI at that version (hallucinated name or version?)")
                continue
            die(f"registry returned HTTP {e.code} for {name}; rerun with network or set DEPS_OFFLINE=1 to skip explicitly")
        except (urllib.error.URLError, TimeoutError) as e:
            die(f"registry unreachable ({e}); rerun with network or set DEPS_OFFLINE=1 to skip explicitly")
        uploads = [u.get("upload_time_iso_8601", "") for u in data.get("urls", [])]
        if not uploads:
            bad.append(f"{name}=={version}: no files published for this version")
            continue
        first = min(dt.datetime.fromisoformat(u.replace("Z", "+00:00")) for u in uploads).date()
        age = (today() - first).days
        if age < min_age:
            bad.append(f"{name}=={version}: published {first}, {age} days ago (< {min_age}; slopsquatting window)")
    if bad:
        return refuse("§6: dependency records failed the registry check", bad,
                      "use the version `pip index versions <pkg>` actually lists, or the stdlib/existing dependency named in INSTEAD-OF")
    return ok(f"check-records/deps: {len(deps)} dependency record(s) exist on the registry and are >= {min_age} days old")


def audit_select() -> int:
    salt = env("AUDIT_SALT")
    if not salt:
        die("set AUDIT_SALT in the environment (kept outside the repository) so implementers cannot predict the draw")
    commit = env("AUDIT_COMMIT") or sh("git", "rev-parse", "HEAD").strip()
    rate = float(env("AUDIT_RATE", "0.20"))
    reasons = []
    if TYPE in ("renew", "policy"):
        reasons.append(f"{TYPE}/ change")
    rec = read_record() or {}
    blob = " ".join(v for vs in rec.values() for v in vs)
    if "POLICY-GAP" in blob or "SUNSET-EXPIRED" in blob:
        reasons.append("POLICY-GAP or SUNSET-EXPIRED filing in the record")
    if rec.get("ALLOWANCE"):
        reasons.append("allowance grant")
    for s in rec.get("SEARCHED", []):
        m = re.search(r"→\s*(\d+)\s+hits?", s)
        if "NONE-FITS" in s and m and int(m.group(1)) > 0:
            reasons.append("NONE-FITS with hits")
    if BASE:
        if any("masks" in t and "SUNSET" in t for _, _, t in added_lines()):
            reasons.append("masks sunset tag added")
        always = env("AUDIT_ALWAYS_PATHS").split()
        hits = [f for f in changed_files() if any(fnmatch.fnmatch(f, g) for g in always)]
        if hits:
            reasons.append(f"AUDIT_ALWAYS_PATHS: {', '.join(hits[:3])}")
    draw = int(hashlib.sha256(f"{commit}:{salt}".encode()).hexdigest()[:8], 16) / 2**32
    if draw < rate:
        reasons.append(f"random draw {draw:.3f} < {rate}")
    if reasons:
        print(f"AUDIT selected {commit[:10]} ({BRANCH}): " + "; ".join(reasons))
        print(f"  auditor: fresh instance, run .claude/skills/audit/SKILL.md, write docs/audits/{SLUG}.md")
    else:
        print(f"AUDIT not selected {commit[:10]} ({BRANCH}): draw {draw:.3f} >= {rate}, no 100% trigger")
    return 0


CHECKS = {"type": check_type, "h1": check_h1, "mocks": check_mocks, "masking": check_masking,
          "sunset": check_sunset, "records": check_records, "deps": check_deps, "audit-select": audit_select}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in CHECKS:
        die(__doc__.strip())
    sys.exit(CHECKS[sys.argv[1]]())
