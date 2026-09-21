#!/usr/bin/env python3
"""Merge-gate verifier for AGENTS.md (v0.4).

    gate_checks.py gate  --subject <rev> --base <rev> --policy-ref <rev> [--branch <name>]
                         [--profile enforced|advisory] [--out <path>]
    gate_checks.py check <id|group> <same options>          one check or group, for local feedback
    gate_checks.py audit-select <same options>              draw the post-merge audit sample

Three things must not coincide: the candidate, the verifier, and the tree the verifier reads.

v0.3 separated the first two — every check reads committed objects only (the working tree is never
evidence), and the verifier and the policy come from the trusted ref. v0.4 separates the third: the
candidate also authors the files that tell git what to export, pytest what to collect and how to report,
and ruff what to lint. So the export is verified against the tree, every tool runs with configuration the
candidate cannot reach, the collected test inventory is compared with the base, and the files that
configure the harness are refused outside a policy change.

Outcomes: PASS | FAIL | ERROR | NOT_RUN. Only PASS on every required check, judged by the verifier at the
policy ref under the enforced profile, makes the subject merge_eligible. Exit: 0 eligible · 1 the change was
refused (a required check FAILed) · 3 the run cannot authorize anything — a required check ERRORed or did
not run, the inputs are invalid, or this was the wrong verifier or the wrong profile · 4 usage.
The split matters to a consumer: 1 means fix the change, 3 means fix the run.
Every refusal names the cheapest compliant path — that message is the policy's real interface.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass, field

VERSION = "0.4.0"
TYPES = ("feature", "fix", "refactor", "test", "chore", "renew", "policy")
MANIFESTS = ("pyproject.toml", "setup.cfg", "setup.py", "requirements.txt", "requirements-*.txt",
             "requirements/*.txt")
# Directories whose Python and shell are business code for the masking scan and the linter.
LINT_DIRS = ("src/", "scripts/", "tools/", "tests/")
SUNSET_KINDS = "compat|flag|todo|masks|skip|deprecated|config|vendored"
SHORT_KINDS = ("todo", "masks", "skip")
SUNSET_RE = re.compile(
    r"SUNSET\s+(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<kind>" + SUNSET_KINDS + r")\s+owner:(?P<owner>\S+)"
    r"\s+reason:(?P<reason>.+?)(?:\s+grace:(?P<grace>\d{4}-\d{2}-\d{2}))?\s*$")
# The one sanctioned permanent catch-all: shape-matched, and its body must return or raise (AGENTS.md §2).
BOUNDARY_LINE_RE = re.compile(r"^\s*except\b[^:]*:\s*#\s*noqa:\s*BLE001\s+#\s*boundary:\s*\S.*$")
BOUNDARY_NOTE_RE = re.compile(r"#\s*boundary:\s*\S")
FILE_SUPPRESS_RE = re.compile(r"#\s*(ruff|flake8)\s*:\s*noqa")
POLICY_FILES_FOR_DIGEST = ("AGENTS.md", "policy.mk", "tests/MOCK_ALLOWLIST", "docs/agents-policy.md")

# Files that quote the tag grammar or the denylist as text rather than using them.
DOC_EXCLUDE = ("AGENTS.md", "docs/agents-policy.md", "docs/changes/", "docs/audits/",
               "scripts/gate_checks.py", "scripts/tests/", ".claude/skills/")

# pytest hooks that decide what is collected or how a result is reported (audit CR-03).
# Any pytest hook decides what is collected or how a result is reported, so the test is the `pytest_`
# prefix rather than a list of names. The named forms are kept for the message they produce.
HARNESS_HOOK_RE = re.compile(r"\bdef\s+(pytest_\w+)")
# An autouse fixture needs no hook at all: `request.node.add_marker(pytest.mark.xfail(...))` turned a
# genuinely red suite green and the gate reported 14/14 (audit LM-1). These are the forms that attack
# reproduced with. Scanning cannot close the class — see the scope line the check prints.
HARNESS_VERDICT_RE = re.compile(r"\badd_marker\s*\(|\bpytest\.mark\.(xfail|skip)\b"
                                r"|\b(rep|report)\.outcome\s*=|\bpytest\.(skip|xfail)\s*\(")
HARNESS_KEYS = ("addopts", "testpaths", "norecursedirs", "python_files", "python_classes",
                "python_functions")
HARNESS_SECTION_RE = re.compile(r"^\s*\[\s*(tool\.pytest[^\]]*|tool:pytest|pytest|tool\.ruff[^\]]*)\s*\]")

GROUPS = {
    "type": ["type", "protected_files"],
    "evidence": ["export_integrity", "harness_integrity", "test_inventory"],
    "tests": ["unit_tests", "test_inventory", "red_before_green", "h1", "mocks"],
    "masking": ["masking_markers", "masking_ruff"],
    "sunset": ["sunset"],
    "records": ["records", "deps"],
    "ledger": ["ledger"],
    "selftest": ["verifier_selftest"],
}
ORDER = ["type", "protected_files", "export_integrity", "harness_integrity", "unit_tests",
         "test_inventory", "red_before_green", "h1", "mocks", "masking_markers", "masking_ruff",
         "sunset", "records", "deps", "verifier_selftest", "ledger", "mutation", "searched_replay",
         "renewals_cap"]


class GateError(Exception):
    """An environment or input problem. Reported as ERROR, never as an empty PASS."""


@dataclass
class Check:
    id: str
    required: bool
    outcome: str  # PASS | FAIL | ERROR | NOT_RUN
    detail: list[str] = field(default_factory=list)
    safe_path: str = ""


@dataclass
class Ctx:
    root: str
    subject: str
    base: str
    policy_ref: str
    branch: str | None
    profile: str
    policy: dict[str, str]
    required: set[str]
    protected: list[str]
    type: str | None = None
    record_path: str | None = None
    slug: str | None = None
    record: dict[str, list[str]] = field(default_factory=dict)
    type_problems: list[str] = field(default_factory=list)
    exports: dict[str, str] = field(default_factory=dict)
    tmp: list[str] = field(default_factory=list)
    ini: str | None = None


# ----------------------------------------------------------------------------- git, strictly

def git(root: str, *args: str, ok: tuple[int, ...] = (0,), binary: bool = False) -> subprocess.CompletedProcess:
    res = subprocess.run(["git", "-C", root, *args], capture_output=True, text=not binary)
    if res.returncode not in ok:
        err = res.stderr if isinstance(res.stderr, str) else res.stderr.decode("utf-8", "replace")
        raise GateError(f"git {' '.join(args[:3])}… failed ({res.returncode}): {err.strip()[:300]}")
    return res


def resolve_commit(root: str, rev: str, what: str) -> str:
    if not rev:
        raise GateError(f"{what} is empty; pass an explicit commit (the gate needs a fixed subject and base)")
    res = git(root, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}", ok=(0, 1))
    sha = res.stdout.strip()
    if res.returncode != 0 or not sha:
        raise GateError(f"{what} '{rev}' is not a commit in this repository")
    return sha


def show(root: str, sha: str, path: str, optional: bool = False) -> str | None:
    res = git(root, "show", f"{sha}:{path}", ok=(0, 128))
    if res.returncode != 0:
        if optional:
            return None
        raise GateError(f"{path} does not exist at {sha[:10]}")
    return res.stdout


def ls_tree(ctx: Ctx, sha: str) -> list[str]:
    return [p for p in git(ctx.root, "ls-tree", "-r", "--name-only", sha).stdout.splitlines() if p]


def changed_files(ctx: Ctx, diff_filter: str | None = None, *paths: str) -> list[str]:
    args = ["diff", "--name-only", "--no-renames"]
    if diff_filter:
        args.append(f"--diff-filter={diff_filter}")
    args += [ctx.base, ctx.subject]
    if paths:
        args += ["--", *paths]
    return [p for p in git(ctx.root, *args).stdout.splitlines() if p]


def added_lines(ctx: Ctx, *paths: str) -> list[tuple[str, int, str]]:
    """(path, line_no, text) for every added line between base and subject."""
    args = ["diff", "-U0", "--no-color", "--no-renames", ctx.base, ctx.subject]
    if paths:
        args += ["--", *paths]
    out: list[tuple[str, int, str]] = []
    path, line_no = "", 0
    for raw in git(ctx.root, *args).stdout.splitlines():
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


def hunks(ctx: Ctx, *paths: str) -> list[tuple[str, list[str], list[str]]]:
    """(path, removed, added) per hunk of a -U0 diff — the unit a field-level rule reasons about."""
    args = ["diff", "-U0", "--no-color", "--no-renames", ctx.base, ctx.subject]
    if paths:
        args += ["--", *paths]
    out: list[tuple[str, list[str], list[str]]] = []
    path = ""
    for raw in git(ctx.root, *args).stdout.splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else raw[4:]
        elif raw.startswith("@@"):
            out.append((path, [], []))
        elif raw.startswith("-") and not raw.startswith("---") and out:
            out[-1][1].append(raw[1:])
        elif raw.startswith("+") and not raw.startswith("+++") and out:
            out[-1][2].append(raw[1:])
    return out


def commits_in_range(ctx: Ctx) -> list[str]:
    return git(ctx.root, "rev-list", "--reverse", f"{ctx.base}..{ctx.subject}").stdout.split()


def commit_files(ctx: Ctx, commit: str) -> list[tuple[str, str]]:
    out = []
    for line in git(ctx.root, "show", "--pretty=format:", "--name-status", "--no-renames",
                    commit).stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0]:
            out.append((parts[0][:1], parts[-1]))
    return out


def grep_tree(ctx: Ctx, pattern: str, sha: str, excludes: tuple[str, ...]) -> list[tuple[str, int, str]]:
    args = ["grep", "-n", "-I", "-e", pattern, sha, "--", "."] + [f":(exclude){e}" for e in excludes]
    res = git(ctx.root, *args, ok=(0, 1))  # 1 = no matches
    out = []
    for line in res.stdout.splitlines():
        try:
            _, rest = line.split(":", 1)
            path, lineno, text = rest.split(":", 2)
            out.append((path, int(lineno), text))
        except ValueError:
            raise GateError(f"unparseable git grep line: {line[:120]}")
    return out


def export(ctx: Ctx, sha: str) -> str:
    """Materialize a commit in a temp dir. Tests and linters run there, never in the work tree."""
    if sha in ctx.exports:
        return ctx.exports[sha]
    d = tempfile.mkdtemp(prefix=f"gate-{sha[:10]}-")
    ctx.tmp.append(d)
    res = git(ctx.root, "archive", "--format=tar", sha, binary=True)
    with tarfile.open(fileobj=io.BytesIO(res.stdout)) as tf:
        try:
            tf.extractall(d, filter="data")
        except TypeError:  # Python < 3.12 has no filter argument
            tf.extractall(d)
    ctx.exports[sha] = d
    return d


def export_paths(root: str) -> set[str]:
    out = set()
    for dirpath, _dirnames, filenames in os.walk(root):
        for f in filenames:
            out.add(os.path.relpath(os.path.join(dirpath, f), root))
    return out


# ----------------------------------------------------------------------------- tool isolation

def trusted_ini(ctx: Ctx) -> str:
    """An empty pytest config outside the export: the candidate's addopts/testpaths never apply (CR-02)."""
    if ctx.ini is None:
        d = tempfile.mkdtemp(prefix="gate-cfg-")
        ctx.tmp.append(d)
        p = os.path.join(d, "gate-pytest.ini")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("[pytest]\n")
        ctx.ini = p
    return ctx.ini


def pytest_argv(ctx: Ctx, exp: str, *targets: str, collect_only: bool = False) -> list[str]:
    args = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
            "-c", trusted_ini(ctx), "--override-ini=addopts=", "--rootdir", exp]
    if collect_only:
        args.append("--collect-only")
    return args + list(targets)


# This run's own identity. `make` puts every command-line variable into the recipe environment, so a
# gate invoked as `make gate SUBJECT=… BASE=…` would hand those to every process it spawns — including
# the corpus, whose fixtures start nested gates that would read them as their own inputs and resolve
# them against a different repository. Stripped, not merely overridden: a nested gate must be told what
# to judge, never inherit it (audit J-1).
INHERITED_IDENTITY = ("SUBJECT", "BASE", "BRANCH", "MAIN", "POLICY_REF", "VERIFIER_REF", "GATE_OUT",
                      "GATE_PROFILE", "PYTEST_ADDOPTS", "PYTEST_PLUGINS")


def run_in(ctx: Ctx, exp: str, cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": exp, "PYTHONDONTWRITEBYTECODE": "1"}
    for name in INHERITED_IDENTITY:
        env.pop(name, None)
    return subprocess.run(cmd, cwd=exp, env=env, capture_output=True, text=True, timeout=timeout)


def pytest_outcome(res: subprocess.CompletedProcess) -> tuple[str, list[str]]:
    tail = [ln for ln in (res.stdout + res.stderr).splitlines() if ln.strip()][-6:]
    outcome = {0: "PASS", 1: "FAIL"}.get(res.returncode, "ERROR")
    if res.returncode == 5:
        tail.append("pytest collected no tests")
    return outcome, tail


def collect_ids(ctx: Ctx, sha: str, timeout: int) -> set[str]:
    """The set of test ids pytest collects at a commit, under trusted configuration."""
    exp = export(ctx, sha)
    if not os.path.isdir(os.path.join(exp, "tests")):
        return set()
    res = run_in(ctx, exp, pytest_argv(ctx, exp, "tests", collect_only=True), timeout)
    if res.returncode not in (0, 5):
        tail = "\n".join((res.stdout + res.stderr).splitlines()[-6:])
        raise GateError(f"collecting tests at {sha[:10]} failed (pytest exit {res.returncode}):\n{tail}")
    return {ln.strip() for ln in res.stdout.splitlines() if "::" in ln and not ln.startswith(" ")}


# ----------------------------------------------------------------------------- policy, identity

def parse_policy(text: str) -> dict[str, str]:
    """Read make variable assignments, honouring backslash continuations.

    A truncated value is how a required check silently becomes advisory, so the continuation is joined
    before the assignment is parsed, never after.
    """
    joined: list[str] = []
    buf = ""
    for line in text.splitlines():
        buf += line
        if buf.rstrip().endswith("\\"):
            buf = buf.rstrip()[:-1] + " "
            continue
        joined.append(buf)
        buf = ""
    if buf:
        joined.append(buf)
    policy: dict[str, str] = {}
    for line in joined:
        m = re.match(r"^\s*([A-Z][A-Z0-9_]*)\s*[:?]?=\s*(.*?)\s*$", line)
        if m:
            policy[m.group(1)] = " ".join(m.group(2).split(" #", 1)[0].split())
    return policy


def policy_int(ctx: Ctx, name: str) -> int:
    try:
        return int(ctx.policy[name])
    except KeyError:
        raise GateError(f"policy.mk at {ctx.policy_ref[:10]} lacks {name}")
    except ValueError:
        raise GateError(f"policy.mk {name} must be an integer (got {ctx.policy[name]!r})")


def sha256(*chunks: bytes) -> str:
    h = hashlib.sha256()
    for c in chunks:
        h.update(c)
    return h.hexdigest()


def policy_digest(ctx: Ctx) -> str:
    parts = []
    for p in POLICY_FILES_FOR_DIGEST:
        content = show(ctx.root, ctx.policy_ref, p, optional=True)
        parts.append(f"{p}\0{content or ''}\0".encode())
    return sha256(*parts)


def tool_version(*cmd: str) -> str | None:
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return (res.stdout or res.stderr).strip().splitlines()[0] if res.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return None


def environment() -> dict[str, str | None]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git": tool_version("git", "--version"),
        "ruff": tool_version("ruff", "--version"),
        "pytest": tool_version(sys.executable, "-m", "pytest", "--version"),
    }


def verifier_sha() -> str:
    with open(os.path.abspath(__file__), "rb") as fh:
        return sha256(fh.read())


def provenance(ctx: Ctx) -> tuple[str, str | None]:
    """Which copy of the verifier is running (audit T3, CMP-07)."""
    mine = verifier_sha()
    at_policy = show(ctx.root, ctx.policy_ref, "scripts/gate_checks.py", optional=True)
    at_subject = show(ctx.root, ctx.subject, "scripts/gate_checks.py", optional=True)
    ref_sha = sha256(at_policy.encode()) if at_policy is not None else None
    if ref_sha is not None and mine == ref_sha:
        return "policy_ref", ref_sha
    if at_subject is not None and mine == sha256(at_subject.encode()):
        return "subject", ref_sha
    return "other", ref_sha


# ----------------------------------------------------------------------------- paths

def under(path: str, prefix: str) -> bool:
    return path.startswith(prefix)


def glob_re(pat: str) -> re.Pattern:
    """A glob where `**` matches zero or more directories, so src/**/auth* matches src/auth.py (CR-05)."""
    out = []
    segs = pat.split("/")
    for i, seg in enumerate(segs):
        last = i == len(segs) - 1
        if seg == "**":
            out.append(r"(?:[^/]+/)*")
        else:
            body = re.escape(seg).replace(r"\*", "[^/]*").replace(r"\?", "[^/]")
            out.append(body + ("" if last else "/"))
    return re.compile("^" + "".join(out) + "$")


def matches_any(path: str, patterns) -> bool:
    return any(glob_re(pat).match(path) for pat in patterns)


def is_protected(path: str, protected: list[str]) -> bool:
    for p in protected:
        if path == p or (p.endswith("/") and path.startswith(p)) or glob_re(p).match(path):
            return True
        if not p.startswith("/") and "/" not in p and os.path.basename(path) == p:
            return True  # a bare name such as .gitattributes protects it at every depth
    return False


def doc_excluded(path: str) -> bool:
    return any(path == x or path.startswith(x) for x in DOC_EXCLUDE)


def is_code(path: str) -> bool:
    return path.endswith((".py", ".sh", ".bash"))


def is_conftest(path: str) -> bool:
    return os.path.basename(path) == "conftest.py"


def is_frozen_test(path: str) -> bool:
    """Where a committed test lives: tests/, the verifier's own suite, and every conftest (spec §3.8)."""
    if path == "tests/MOCK_ALLOWLIST":
        return False
    return under(path, "tests/") or under(path, "scripts/tests/") or is_conftest(path)


PLACEHOLDER_RE = re.compile(r"<[^<>]{0,60}>")


def is_placeholder(value: str) -> bool:
    """An unfilled template slot, not any line that happens to contain a `<`.

    The old test was `"<" in value`, which refused a truthful record whose WHY carried a bound such as
    `n <= 3` and reprinted the template line without naming the cause (audit LM-8). A placeholder is an
    angle-bracket token; a comparison is not.
    """
    return not value or bool(PLACEHOLDER_RE.search(value))


def code_part(line: str) -> str:
    """The text of a line before its SUNSET tag, comment marker stripped."""
    i = line.find("SUNSET")
    head = line[:i] if i >= 0 else line
    return re.sub(r"\s*(#|//|--)\s*$", "", head).rstrip()


def strip_grace(line: str) -> str:
    return re.sub(r"\s+grace:\d{4}-\d{2}-\d{2}\s*$", "", line).rstrip()


def parse_record(text: str) -> dict[str, list[str]]:
    rec: dict[str, list[str]] = {}
    for line in text.splitlines():
        m = re.match(r"^(TYPE|WHY|SEARCHED|DEP|TESTS|ALLOWANCE|BLOCKED|ACCEPTANCE|EXCEPTION|EFFECTIVE"
                     r"|READ|HANDOFF)\b\s*(.*)$", line.strip())
        if m:
            rec.setdefault(m.group(1), []).append(m.group(2).lstrip(": ").strip())
    return rec


# ----------------------------------------------------------------------------- context

def build_ctx(args: argparse.Namespace) -> Ctx:
    root = git(".", "rev-parse", "--show-toplevel").stdout.strip()
    if not root:
        raise GateError("not inside a git repository")
    subject = resolve_commit(root, args.subject, "SUBJECT")
    policy_ref = resolve_commit(root, args.policy_ref, "POLICY_REF")
    base = resolve_commit(root, args.base, "BASE")
    if base == subject:
        raise GateError("BASE equals SUBJECT: nothing to gate (on a merged commit pass BASE explicitly)")
    if git(root, "merge-base", "--is-ancestor", base, subject, ok=(0, 1)).returncode != 0:
        raise GateError(f"BASE {base[:10]} is not an ancestor of SUBJECT {subject[:10]}")
    policy_text = show(root, policy_ref, "policy.mk")
    policy = parse_policy(policy_text or "")
    profile = (args.profile or "enforced").lower()
    key = f"REQUIRED_CHECKS_{profile.upper()}"
    if key not in policy:
        raise GateError(f"policy.mk at {policy_ref[:10]} has no {key}")
    ctx = Ctx(root=root, subject=subject, base=base, policy_ref=policy_ref,
              branch=(args.branch or None), profile=profile, policy=policy,
              required=set(policy[key].split()),
              protected=policy.get("PROTECTED_PATHS", "").split())
    resolve_type(ctx)
    return ctx


def resolve_type(ctx: Ctx) -> None:
    """The change type comes from the committed record, cross-checked with the branch prefix (audit F09).

    The record is the one this change ADDS; failing that, the single one it modifies; and when a branch of
    the form <type>/<slug> is given, the record matching it even if other records were also touched.
    Correcting a previously merged record alongside your own is allowed (audit RT-08).
    """
    added = [f for f in changed_files(ctx, "A", "docs/changes/") if f != "docs/changes/_TEMPLATE.md"]
    touched = [f for f in changed_files(ctx, "AM", "docs/changes/") if f != "docs/changes/_TEMPLATE.md"]
    branch_slug = ctx.branch.replace("/", "-", 1) if ctx.branch and "/" in ctx.branch else None
    by_branch = [f for f in touched if branch_slug and f == f"docs/changes/{branch_slug}.md"]

    if by_branch:
        ctx.record_path = by_branch[0]
    elif len(added) == 1:
        ctx.record_path = added[0]
    elif not added and len(touched) == 1:
        ctx.record_path = touched[0]
    else:
        ctx.type_problems.append(
            f"cannot tell which record belongs to this change: {len(added)} added, {len(touched)} touched"
            + (f" ({', '.join(touched[:5])})" if touched else "")
            + "; add exactly one docs/changes/<type>-<slug>.md, or name the branch <type>/<slug>")
        return

    text = show(ctx.root, ctx.subject, ctx.record_path, optional=True)
    if text is None:
        ctx.type_problems.append(f"{ctx.record_path} is not committed at the subject")
        return
    ctx.record = parse_record(text)
    rtype = (ctx.record.get("TYPE") or [""])[0]
    m = re.match(r"^docs/changes/([a-z]+)-(.+)\.md$", ctx.record_path)
    if rtype not in TYPES:
        ctx.type_problems.append(f"{ctx.record_path}: TYPE: must be one of {', '.join(TYPES)} (got {rtype!r})")
    if not m:
        ctx.type_problems.append(f"{ctx.record_path}: record files are docs/changes/<type>-<slug>.md")
    elif m.group(1) != rtype:
        ctx.type_problems.append(f"{ctx.record_path}: filename says '{m.group(1)}', TYPE: says '{rtype}'")
    else:
        ctx.slug = f"{m.group(1)}-{m.group(2)}"
    if ctx.branch and "/" in ctx.branch and ctx.branch.split("/", 1)[0] != rtype:
        ctx.type_problems.append(
            f"branch '{ctx.branch}' has prefix '{ctx.branch.split('/', 1)[0]}', record TYPE: is '{rtype}'")
    if rtype in TYPES and not ctx.type_problems:
        ctx.type = rtype


# ----------------------------------------------------------------------------- checks: identity

def check_type(ctx: Ctx) -> Check:
    c = Check("type", "type" in ctx.required, "PASS")
    if ctx.type is None:
        c.outcome, c.detail = "FAIL", list(ctx.type_problems)
        c.safe_path = ("commit docs/changes/<type>-<slug>.md (cp docs/changes/_TEMPLATE.md …) with TYPE: matching "
                       "the filename and the branch prefix; branches are <type>/<slug>")
        return c
    files = [f for f in changed_files(ctx) if not under(f, "docs/changes/")]
    bad = []
    for f in files:
        in_src, in_tests = under(f, "src/"), under(f, "tests/")
        prot = is_protected(f, ctx.protected)
        allowed = {
            "feature": (in_src or in_tests or matches_any(f, MANIFESTS)) and not prot,
            "fix": (in_src or in_tests or matches_any(f, MANIFESTS)) and not prot,
            "refactor": in_src and not prot,
            "test": in_tests and not prot,
            "chore": not (in_src or in_tests or prot),
            "renew": not prot,  # field-level check below
            "policy": prot,
        }[ctx.type]
        if not allowed:
            bad.append(f)
    if bad:
        c.outcome, c.detail = "FAIL", [f"a {ctx.type} change may not touch {f}" for f in bad]
        c.safe_path = "split the change: one branch and one record per type"
        return c
    if ctx.type == "renew":
        problems = renew_violations(ctx)
        if problems:
            c.outcome = "FAIL"
            c.detail = ["a renew change alters the SUNSET tag and nothing else:"] + problems[:10]
            c.safe_path = ("keep the code before the tag byte-identical and the kind and owner unchanged; change "
                           "the date, the reason or the grace only. Other edits go on their own branch")
            return c
    c.detail.append(f"{ctx.type} change touches {len(files)} file(s) within its allowed set")
    return c


def renew_violations(ctx: Ctx) -> list[str]:
    """A renew is a field-level edit of a tag line, not 'a line that happens to say SUNSET' (audit P08)."""
    problems: list[str] = []
    for path, removed, added in hunks(ctx, ".", ":(exclude)docs/changes"):
        if len(removed) != len(added):
            problems.append(f"{path}: {len(removed)} line(s) removed, {len(added)} added — "
                            f"a renew edits tag lines in place")
            continue
        for old, new in zip(removed, added):
            mo, mn = SUNSET_RE.search(old), SUNSET_RE.search(new)
            if not mo or not mn:
                problems.append(f"{path}: not a tag-to-tag edit: {new.strip()[:80]}")
            elif code_part(old) != code_part(new):
                problems.append(f"{path}: code changed alongside the tag: {new.strip()[:80]}")
            elif mo.group("kind") != mn.group("kind"):
                problems.append(f"{path}: kind changed {mo.group('kind')} → {mn.group('kind')}: {new.strip()[:80]}")
            elif mo.group("owner") != mn.group("owner"):
                problems.append(f"{path}: owner changed {mo.group('owner')} → {mn.group('owner')}: {new.strip()[:80]}")
    return problems


def check_protected_files(ctx: Ctx) -> Check:
    c = Check("protected_files", "protected_files" in ctx.required, "PASS")
    touched = [f for f in changed_files(ctx) if is_protected(f, ctx.protected)]
    if ctx.type != "policy" and touched:
        c.outcome = "FAIL"
        c.detail = [f"protected: {f}" for f in touched]
        c.safe_path = ("only a policy change may touch the verifier, the policy files, hooks or CI; open a policy/ "
                       "branch for that part (it is always audited)")
    elif ctx.type == "policy":
        outside = [f for f in changed_files(ctx)
                   if not is_protected(f, ctx.protected) and not under(f, "docs/changes/")]
        if outside:
            c.outcome, c.detail = "FAIL", [f"policy change touches non-policy file {f}" for f in outside]
            c.safe_path = "a policy change touches the protected set only"
    c.detail.append(f"protected set: {' '.join(ctx.protected)}")
    return c


# ----------------------------------------------------------------------------- checks: the evidence tree

def check_export_integrity(ctx: Ctx) -> Check:
    """The tree the gate reads must be the commit — not what a .gitattributes decided to export (CR-01)."""
    c = Check("export_integrity", "export_integrity" in ctx.required, "PASS")
    exp = export(ctx, ctx.subject)
    in_tree = set(ls_tree(ctx, ctx.subject))
    in_export = export_paths(exp)
    missing = sorted(in_tree - in_export)
    extra = sorted(in_export - in_tree)
    if missing or extra:
        c.outcome = "FAIL"
        c.detail += [f"committed but absent from the gate's export: {p}" for p in missing[:10]]
        c.detail += [f"in the export but not in the commit: {p}" for p in extra[:10]]
        c.safe_path = ("remove the export-ignore attribute: the tree the gate tests must be the tree you committed. "
                       "Attribute changes belong on a policy/ branch")
        return c
    c.detail.append(f"the export matches the commit: {len(in_tree)} path(s)")
    return c


def check_harness_integrity(ctx: Ctx) -> Check:
    """The candidate must not ship the configuration that decides how it is judged (CR-01, CR-02, CR-03)."""
    c = Check("harness_integrity", "harness_integrity" in ctx.required, "PASS")
    scope = ("scope: a denylist over added lines — any pytest hook in a conftest, the marker and outcome "
             "forms an autouse fixture uses, harness config sections and keys, export-ignore, file-level "
             "lint suppression. It cannot close the class. The gate runs code the candidate wrote, so a "
             "conftest or an imported module reaching the verdict by a route no pattern anticipates is "
             "not detected here; the audit BREAK step is the compensating control")
    if ctx.type == "policy":
        c.detail.append("policy change: the harness files are the protected set's business")
        c.detail.append(scope)
        return c
    bad: list[str] = []
    for path, no, text in added_lines(ctx):
        stripped = text.strip()
        if os.path.basename(path) == ".gitattributes" and "export-ignore" in text:
            bad.append(f"{path}:{no}: export-ignore removes files from the gate's own evidence: {stripped[:70]}")
        if is_conftest(path):
            hook = HARNESS_HOOK_RE.search(text)
            if hook:
                bad.append(f"{path}:{no}: defines the pytest hook {hook.group(1)}, which decides what is "
                           f"collected or how a result is reported")
            elif HARNESS_VERDICT_RE.search(text):
                bad.append(f"{path}:{no}: changes a test's verdict from inside the run: {stripped[:70]}")
        if path.endswith((".ini", ".cfg", ".toml")):
            m = HARNESS_SECTION_RE.match(text)
            if m:
                bad.append(f"{path}:{no}: adds a [{m.group(1)}] section — that is the gate's own tool configuration")
                continue
            key = re.match(r"^\s*([A-Za-z_]+)\s*=", text)
            if key and key.group(1) in HARNESS_KEYS:
                bad.append(f"{path}:{no}: sets {key.group(1)}, which selects what the gate collects")
        if path.endswith(".py") and FILE_SUPPRESS_RE.search(text):
            bad.append(f"{path}:{no}: file-level lint suppression: {stripped[:70]}")
    if bad:
        c.outcome, c.detail = "FAIL", bad
        c.safe_path = ("the harness is policy: move this to a policy/ branch (always audited). A test that needs "
                       "setup uses an ordinary fixture, never a reporting or collection hook")
        return c
    c.detail.append("this change adds no harness configuration")
    c.detail.append(scope)
    return c


def check_test_inventory(ctx: Ctx) -> Check:
    """Compare the tests pytest actually collects at base and at subject (CR-01, CR-02, CR-04)."""
    c = Check("test_inventory", "test_inventory" in ctx.required, "PASS")
    timeout = policy_int(ctx, "UNIT_TESTS_TIMEOUT")
    try:
        base_ids = collect_ids(ctx, ctx.base, timeout)
        subj_ids = collect_ids(ctx, ctx.subject, timeout)
    except subprocess.TimeoutExpired:
        c.outcome, c.detail = "ERROR", [f"collection exceeded UNIT_TESTS_TIMEOUT={timeout}s"]
        return c
    lost = sorted(base_ids - subj_ids)
    gained = sorted(subj_ids - base_ids)
    if lost:
        c.outcome = "FAIL"
        c.detail = [f"collected at the base commit and gone at the subject: {i}" for i in lost[:10]]
        c.safe_path = ("a committed test may not disappear — not by deletion, not by export-ignore, not by an "
                       "addopts --ignore, not by a collection hook. If the test is wrong, file BLOCKED TEST-DEFECT "
                       "and let a test/ branch adjudicate")
        return c
    if ctx.type in ("feature", "fix") and not gained:
        c.outcome = "FAIL"
        c.detail = [f"{len(subj_ids)} test(s) collected at the subject, none of them new"]
        c.safe_path = ("write the test from the spec first and commit it before src/; a file that collects no test "
                       "is not a test. No harness → BLOCKED NO-HARNESS")
        return c
    if ctx.type == "refactor" and gained:
        c.outcome = "FAIL"
        c.detail = [f"a refactor adds no tests; new: {i}" for i in gained[:10]]
        c.safe_path = "if behavior changed this is a feature or a fix"
        return c
    c.detail.append(f"{len(base_ids)} collected at base, {len(subj_ids)} at subject, {len(gained)} new, none lost")
    return c


def check_unit_tests(ctx: Ctx) -> Check:
    c = Check("unit_tests", "unit_tests" in ctx.required, "PASS")
    exp = export(ctx, ctx.subject)
    if not os.path.isdir(os.path.join(exp, "tests")):
        c.detail.append("no tests/ directory at the subject commit; nothing to run (stated, not assumed)")
        return c
    timeout = policy_int(ctx, "UNIT_TESTS_TIMEOUT")
    try:
        res = run_in(ctx, exp, pytest_argv(ctx, exp, "tests"), timeout)
    except subprocess.TimeoutExpired:
        c.outcome, c.detail = "ERROR", [f"pytest exceeded UNIT_TESTS_TIMEOUT={timeout}s"]
        return c
    if res.returncode == 5:
        c.detail.append("pytest collected no tests at the subject (see test_inventory)")
        return c
    c.outcome, c.detail = pytest_outcome(res)
    c.detail.append("run with the gate's own pytest configuration, not the candidate's")
    if c.outcome == "FAIL":
        c.safe_path = ("fix the implementation; a test that looks wrong is BLOCKED TEST-DEFECT (H1 forbids "
                       "editing it)")
    return c


def check_red_before_green(ctx: Ctx) -> Check:
    """The change's new tests must fail on the parent commit, or they tested nothing the change did."""
    c = Check("red_before_green", "red_before_green" in ctx.required, "PASS")
    if ctx.type not in ("feature", "fix"):
        c.detail.append(f"not applicable to a {ctx.type} change (feature and fix only)")
        return c
    new_tests = [f for f in changed_files(ctx, "A", "tests/")
                 if f.endswith(".py") and not is_conftest(f)]
    if not new_tests:
        c.outcome, c.detail = "FAIL", ["no new test file under tests/ (see test_inventory)"]
        c.safe_path = "write the tests first, from the spec, and commit them before src/"
        return c
    stage = tempfile.mkdtemp(prefix="gate-red-")
    ctx.tmp.append(stage)
    shutil.copytree(export(ctx, ctx.base), stage, dirs_exist_ok=True)
    for f in new_tests:
        dst = os.path.join(stage, f)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(show(ctx.root, ctx.subject, f) or "")
    timeout = policy_int(ctx, "UNIT_TESTS_TIMEOUT")
    try:
        res = run_in(ctx, stage, pytest_argv(ctx, stage, *new_tests), timeout)
    except subprocess.TimeoutExpired:
        c.outcome, c.detail = "ERROR", [f"the new tests exceeded UNIT_TESTS_TIMEOUT={timeout}s on the base commit"]
        return c
    tail = [ln for ln in (res.stdout + res.stderr).splitlines() if ln.strip()][-5:]
    if res.returncode in (1, 2):
        c.detail.append(f"{len(new_tests)} new test file(s) fail on the base commit (pytest exit {res.returncode})")
        c.detail.append("scope: the reason for the red is not classified — an unrelated ImportError also passes")
        return c
    if res.returncode in (0, 5):
        c.outcome = "FAIL"
        c.detail = [f"the new tests pass, or collect nothing, on the base commit: {', '.join(new_tests[:5])}"] + tail
        c.safe_path = "assert the behavior the change introduces; a test green before the change is not evidence"
        return c
    c.outcome, c.detail = "ERROR", [f"pytest exit {res.returncode} on the base commit"] + tail
    return c


# ----------------------------------------------------------------------------- checks: H1 and mocks

def check_h1(ctx: Ctx) -> Check:
    c = Check("h1", "h1" in ctx.required, "PASS")
    if ctx.type is None:
        c.outcome, c.detail = "FAIL", ["change type unresolved (see type)"]
        return c
    # Acceptance is revised in one of two forums and never silently. A `test` change adjudicates ordinary
    # acceptance; a `policy` change is the only forum for protected acceptance — `scripts/tests/`, the
    # verifier's own counterexamples. Either way the decision §3 requires must be in the record. The
    # exemption used to be unconditional for `test` and absent for `policy`, so the gate reported "no
    # committed test modified" while assertions were deleted (audit LM-2) and no branch type could revise
    # a counterexample at all (audit LM-3). A revision on `policy` is safe to allow because
    # verifier_selftest restores the corpus from the policy ref: the change is still judged by the
    # counterexamples as they stand on main, and its own revision takes effect only once merged.
    revision = [a for a in ctx.record.get("ACCEPTANCE", []) if not is_placeholder(a)]
    exempt = ctx.type in ("test", "policy") and bool(revision)
    if not exempt:
        frozen = []
        for commit in commits_in_range(ctx):
            for status, path in commit_files(ctx, commit):
                if status in "MDR" and is_frozen_test(path):
                    frozen.append(f"{commit[:10]}: {status} {path}")
        if frozen:
            c.outcome = "FAIL"
            c.detail = ["H1: a committed test may not be modified, deleted or renamed:"] + frozen
            if ctx.type in ("test", "policy"):
                c.safe_path = (f"a {ctx.type} change may revise committed acceptance only with the decision §3 "
                               "requires: an ACCEPTANCE: line in the record naming the approver the owner "
                               "designated before the edit, the reason, the exact old and new cases, and the "
                               "retained evidence. Protected acceptance (scripts/tests/) goes on policy/, "
                               "ordinary acceptance on test/")
            else:
                c.safe_path = ("file BLOCKED TEST-DEFECT (3 lines); a test/ branch adjudicates with a recorded "
                               "ACCEPTANCE: decision. New assertions go in a new test file. The frozen set is "
                               "tests/, scripts/tests/ and every conftest.py")
            return c
    if ctx.type == "refactor":
        touched = changed_files(ctx, "AMD", "tests/")
        if touched:
            c.outcome, c.detail = "FAIL", ["a refactor changes no tests:"] + touched
            c.safe_path = ("if behavior changed this is a feature or a fix; if the tests were wrong, "
                           "BLOCKED TEST-DEFECT")
            return c
    if ctx.type in ("feature", "fix"):
        mixed = []
        for commit in commits_in_range(ctx):
            files = [p for _, p in commit_files(ctx, commit)]
            if any(under(f, "src/") for f in files) and any(under(f, "tests/") for f in files):
                mixed.append(f"{commit[:10]} touches src/ and tests/ in one commit")
        if mixed:
            c.outcome, c.detail = "FAIL", ["H1/BLIND: tests are committed before the implementation:"] + mixed
            c.safe_path = "commit tests first (git add tests && git commit -m 'test: <what>'), then implement"
            return c
    if exempt:
        c.detail += ["acceptance revised under a recorded decision — in the 100% audit set:"] + revision
        c.detail.append("scope: the gate reads that a decision was recorded; whether the named approver was "
                        "independent of the proposer is for the audit, not for a check")
    else:
        c.detail.append("no committed test modified; src and tests never share a commit")
    c.detail.append("scope: commit order is a proxy — red_before_green carries the parent-commit evidence")
    return c


class MockScan(ast.NodeVisitor):
    """Find mock targets and resolve them through the file's own imports (audit CMP-05, CMP-11, M10)."""

    def __init__(self):
        self.alias: dict[str, str] = {}
        self.targets: list[tuple[int, str]] = []
        self.unresolved: list[tuple[int, str]] = []

    def visit_Import(self, node: ast.Import):
        for a in node.names:
            self.alias[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        for a in node.names:
            self.alias[a.asname or a.name] = f"{mod}.{a.name}" if mod else a.name
        self.generic_visit(node)

    def dotted(self, node: ast.AST) -> str | None:
        """The import-resolved dotted name, or None when the root is not something this file imported."""
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if not isinstance(node, ast.Name):
            return None
        parts.append(node.id)
        parts.reverse()
        if parts[0] not in self.alias:
            return None  # a local variable holding the target: the gate cannot resolve it (audit M10)
        parts[0] = self.alias[parts[0]]
        return ".".join(parts)

    def record(self, node: ast.AST, lineno: int, attr: ast.AST | None = None,
               quiet: bool = False) -> None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            self.targets.append((lineno, node.value))
            return
        base = self.dotted(node)
        if base is None:
            if not quiet:
                self.unresolved.append((lineno, ast.unparse(node)[:60]))
            return
        if base.endswith(".__dict__"):
            base = base[: -len(".__dict__")]
        if attr is None:
            self.targets.append((lineno, base))
        elif isinstance(attr, ast.Constant) and isinstance(attr.value, str):
            self.targets.append((lineno, f"{base}.{attr.value}"))
        else:
            self.unresolved.append((lineno, f"{base}.<computed>"))

    def visit_Call(self, node: ast.Call):
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
        owner = ""
        if isinstance(fn, ast.Attribute) and isinstance(fn.value, (ast.Name, ast.Attribute)):
            owner = (self.dotted(fn.value) or "").split(".")[-1]
        args = node.args
        if name == "patch" and args:
            self.record(args[0], node.lineno)
        elif name in ("object", "dict", "multiple") and owner in ("patch", "mock", "mocker") and args:
            self.record(args[0], node.lineno, args[1] if len(args) > 1 and name == "object" else None)
        elif name in ("setattr", "delattr") and args:
            # monkeypatch.setattr is unambiguously mocking, so an unresolvable target is reported.
            # A bare builtin setattr() is ordinary Python; only flag it when it resolves to an import.
            bare = isinstance(fn, ast.Name)
            self.record(args[0], node.lineno, args[1] if len(args) > 1 else None, quiet=bare)
        self.generic_visit(node)


def check_mocks(ctx: Ctx) -> Check:
    c = Check("mocks", "mocks" in ctx.required, "PASS")
    text = show(ctx.root, ctx.policy_ref, "tests/MOCK_ALLOWLIST", optional=True) or ""
    prefixes = [p for p in (ln.split("#", 1)[0].strip() for ln in text.splitlines()) if p]
    touched = {p for p in changed_files(ctx, "AM") if p.endswith(".py")
               and (under(p, "tests/") or under(p, "src/")) and not doc_excluded(p)}
    added_by_path: dict[str, set[int]] = {}
    for p, no, _ in added_lines(ctx):
        added_by_path.setdefault(p, set()).add(no)
    bad, unresolved = [], []
    for path in sorted(touched):
        src = show(ctx.root, ctx.subject, path, optional=True)
        if src is None:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            raise GateError(f"{path} does not parse at the subject: {e}")
        scan = MockScan()
        scan.visit(tree)
        lines = added_by_path.get(path, set())
        for lineno, target in scan.targets:
            if lineno in lines and not any(target == p or target.startswith(p) for p in prefixes):
                bad.append(f"{path}:{lineno}: mocks '{target}' "
                           f"(not in tests/MOCK_ALLOWLIST at {ctx.policy_ref[:10]})")
        for lineno, expr in scan.unresolved:
            if lineno in lines:
                unresolved.append(f"{path}:{lineno}: unresolved mock target '{expr}' — the gate cannot check it")
    if bad:
        c.outcome, c.detail = "FAIL", bad + unresolved
        c.safe_path = ("test the real in-repo call path; if no harness exists, BLOCKED NO-HARNESS; widening the "
                       "allowlist is a policy change")
        return c
    c.detail += unresolved
    c.detail.append("scope: AST forms patch / patch.object / patch.dict / monkeypatch.setattr / setattr under "
                    "tests/ and src/, with names resolved through each file's imports; a call is attributed to "
                    "its first line, so a multi-line call whose opening line this change did not touch is out of "
                    "scope; a target computed at run time is listed above as unresolved")
    return c


# ----------------------------------------------------------------------------- checks: masking

def handler_terminates(src: str) -> dict[int, bool]:
    """Per except-handler line, whether every path of its body returns or raises (AGENTS.md §2)."""
    out: dict[int, bool] = {}
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out

    def terminal(body: list[ast.stmt]) -> bool:
        if not body:
            return False
        last = body[-1]
        if isinstance(last, ast.Raise):
            return True
        if isinstance(last, ast.Return):
            # A bare `return` or `return None` is the fallback value AGENTS.md §2 refuses, not a
            # typed failure the caller must match (audit M05).
            return not (last.value is None
                        or (isinstance(last.value, ast.Constant) and last.value.value is None))
        if isinstance(last, ast.If):
            return terminal(last.body) and terminal(last.orelse)
        if isinstance(last, (ast.With, ast.Try)):
            return terminal(last.body)
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            out[node.lineno] = terminal(node.body)
    return out


def check_masking_markers(ctx: Ctx) -> Check:
    c = Check("masking_markers", "masking_markers" in ctx.required, "PASS")
    marker = re.compile(r"#\s*(noqa|type:\s*ignore|pylint:\s*disable|pragma:\s*no cover)"
                        r"|@(?:pytest\.mark\.)?(?:skip|xfail)\b|@unittest\.skip|pytest\.skip\(")
    shell = re.compile(r"\|\|\s*true\b|2>\s*/dev/null")
    handler = re.compile(r"^\s*except\b[^:]*:\s*(#.*)?$")
    swallow = re.compile(r"^\s*(pass|continue|return\s*(None)?|\.\.\.)\s*(#.*)?$")

    lines = [(p, n, t) for p, n, t in added_lines(ctx) if is_code(p) and not doc_excluded(p)]
    by_pos = {(p, n): t for p, n, t in lines}
    bodies: dict[str, dict[int, bool]] = {}
    bad, boundaries = [], []
    for path, no, text in lines:
        if SUNSET_RE.search(text):  # a complete tag prices the stopgap (audit P09)
            continue
        if BOUNDARY_LINE_RE.match(text):
            if path not in bodies:
                bodies[path] = handler_terminates(show(ctx.root, ctx.subject, path, optional=True) or "")
            if bodies[path].get(no, False):
                boundaries.append(f"{path}:{no}: {text.strip()[:100]}")
            else:
                bad.append(f"{path}:{no}: a boundary handler must return or raise the typed failure it names: "
                           f"{text.strip()[:80]}")
            continue
        if BOUNDARY_NOTE_RE.search(text) or re.match(r"^\s*except\b[^:]*:\s*#\s*boundary\b", text):
            bad.append(f"{path}:{no}: only the full shape is a sanctioned crash barrier — "
                       f"`except …:  # noqa: BLE001  # boundary: <the typed failure>` whose body raises or "
                       f"returns it: {text.strip()[:80]}")
            continue
        if FILE_SUPPRESS_RE.search(text):
            bad.append(f"{path}:{no}: file-level lint suppression disables every rule: {text.strip()[:80]}")
            continue
        if marker.search(text):
            bad.append(f"{path}:{no}: suppression or skip marker without a complete SUNSET tag: {text.strip()[:80]}")
        if path.endswith((".sh", ".bash")) and shell.search(text):
            bad.append(f"{path}:{no}: shell failure masked: {text.strip()[:80]}")
        if handler.match(text) and swallow.match(by_pos.get((path, no + 1), "")):
            bad.append(f"{path}:{no}: handler followed by '{by_pos[(path, no + 1)].strip()}' — it neither "
                       f"re-raises, returns a typed failure, nor logs the exception (error masked)")
    if bad:
        c.outcome, c.detail = "FAIL", bad
        c.safe_path = ("re-raise with context, return a typed failure, or file BLOCKED FAILURE-SEMANTICS. A "
                       "deliberate stopgap is `# noqa: BLE001  # SUNSET <date> masks owner:<id> reason:<why>`; a "
                       "permanent crash barrier is `except …:  # noqa: BLE001  # boundary: <typed failure>` whose "
                       "body returns or raises it — both on one line, both audited")
        return c
    if boundaries:
        c.detail += [f"{len(boundaries)} boundary exemption(s), body verified, in the 100% audit set:"] + boundaries
    c.detail.append(f"scanned every added .py/.sh/.bash line ({len(lines)}), not only src/ and tests/")
    return c


def check_masking_ruff(ctx: Ctx) -> Check:
    c = Check("masking_ruff", "masking_ruff" in ctx.required, "PASS")
    if not shutil.which("ruff"):
        c.outcome = "NOT_RUN"
        c.detail = ["ruff is not installed (pip install ruff); E722/BLE001/S110/S112/S113 were not evaluated"]
        c.safe_path = "install ruff; a required check that could not run does not authorize a merge"
        return c
    exp = export(ctx, ctx.subject)
    dirs = [d for d in LINT_DIRS if os.path.isdir(os.path.join(exp, d))]
    if not dirs:
        c.detail.append("no source directory among " + " ".join(LINT_DIRS) + " at the subject")
        return c
    res = run_in(ctx, exp, ["ruff", "check", "--isolated", "--quiet",
                            "--select", "E722,BLE001,S110,S112,S113", *dirs], 300)
    if res.returncode == 0:
        c.detail.append(f"E722 BLE001 S110 S112 S113 clean on {' '.join(dirs)} "
                        f"(--isolated: the candidate's own ruff configuration does not apply)")
    elif res.returncode == 1:
        c.outcome = "FAIL"
        c.detail = [ln for ln in res.stdout.splitlines() if ln.strip()][:20]
        c.safe_path = "see masking_markers"
    else:
        c.outcome, c.detail = "ERROR", [f"ruff exited {res.returncode}: {res.stderr.strip()[:200]}"]
    return c


# ----------------------------------------------------------------------------- checks: sunset

SUNSET_EXCLUDES = ("AGENTS.md", "docs/agents-policy.md", "docs/changes/", "docs/audits/", "scripts/",
                   ".claude/", ".github/")


def check_sunset(ctx: Ctx) -> Check:
    c = Check("sunset", "sunset" in ctx.required, "PASS")
    short, long_ = policy_int(ctx, "SUNSET_SHORT"), policy_int(ctx, "SUNSET_LONG")
    max_, grace_days = policy_int(ctx, "SUNSET_MAX"), policy_int(ctx, "SUNSET_GRACE")
    today = dt.date.today()
    filed = any("SUNSET-EXPIRED" in b for b in ctx.record.get("BLOCKED", []))

    # Tags already in grace at the base: a second grace on the same tag is not "once" (audit P0-8).
    graced_at_base: set[tuple[str, str]] = set()
    for path, _no, text in grep_tree(ctx, "SUNSET", ctx.base, SUNSET_EXCLUDES):
        m = SUNSET_RE.search(text)
        if m and m.group("grace"):
            graced_at_base.add((path, code_part(text)))

    malformed, expired, too_long, in_grace, live = [], [], [], [], 0
    for path, no, text in grep_tree(ctx, "SUNSET", ctx.subject, SUNSET_EXCLUDES):
        if "SUNSET <" in text:
            continue
        m = SUNSET_RE.search(text)
        if not m:
            if is_code(path) or re.search(r"SUNSET\s+\d{4}", text):
                malformed.append(f"{path}:{no}: {text.strip()[:100]}")
            continue
        try:
            date = dt.date.fromisoformat(m.group("date"))
        except ValueError:
            malformed.append(f"{path}:{no}: {m.group('date')} is not a calendar date: {text.strip()[:70]}")
            continue
        live += 1
        if (date - today).days > max_:
            too_long.append(f"{path}:{no}: expires {date}, beyond the {max_}-day maximum")
        if date >= today:
            continue
        grace = m.group("grace")
        gdate = None
        if grace:
            try:
                gdate = dt.date.fromisoformat(grace)
            except ValueError:
                malformed.append(f"{path}:{no}: grace:{grace} is not a calendar date")
                continue
        if gdate is None:
            expired.append(f"{path}:{no}: {m.group('kind')} expired {date} owner:{m.group('owner')}")
        elif (path, code_part(text)) in graced_at_base:
            expired.append(f"{path}:{no}: this tag was already in grace at the base commit; the deferral is once "
                           f"(expired {date})")
        elif not filed:
            expired.append(f"{path}:{no}: grace:{grace} claimed but {ctx.record_path or 'the change record'} has "
                           f"no BLOCKED SUNSET-EXPIRED line")
        elif gdate > today:
            expired.append(f"{path}:{no}: grace:{grace} is in the future — a deferral starts the day it is filed")
        elif (today - gdate).days > grace_days:
            expired.append(f"{path}:{no}: grace:{grace} ran out {(today - gdate).days - grace_days} day(s) ago "
                           f"(the window is {grace_days} days)")
        else:
            in_grace.append(f"{path}:{no}: expired {date}, in grace until {gdate + dt.timedelta(days=grace_days)}")

    if malformed:
        c.outcome = "FAIL"
        c.detail = ["malformed or partial SUNSET tags (a partial tag exempts nothing):"] + malformed
        c.safe_path = f"# SUNSET YYYY-MM-DD <{SUNSET_KINDS}> owner:<task-id> reason:<one line> [grace:YYYY-MM-DD]"
        return c
    if too_long:
        c.outcome, c.detail = "FAIL", [f"no tag may run past the {max_}-day maximum:"] + too_long
        c.safe_path = ("shorten the date; a stopgap that needs longer is a permanent abstraction "
                       "(record plus ledger debit)")
        return c
    if expired:
        c.outcome, c.detail = "FAIL", ["expired sunset tags at the subject commit:"] + expired
        c.safe_path = ("delete the tagged code and run the suite; if that breaks it, revert, add "
                       "`BLOCKED SUNSET-EXPIRED: …` to your own change record and `grace:<today>` to the tag "
                       "(once); renewals happen on a renew/ branch")
        return c

    # Added or renewed tag lines: the per-kind term, and tag edits only on a renew (audit P10, P12).
    over_term, edited = [], []
    for path, removed, added in hunks(ctx):
        if doc_excluded(path) or any(under(path, e) for e in SUNSET_EXCLUDES if e.endswith("/")):
            continue
        removed_tags = [(code_part(r), SUNSET_RE.search(r), r) for r in removed if SUNSET_RE.search(r)]
        for new in added:
            mn = SUNSET_RE.search(new)
            if not mn:
                continue
            try:
                ndate = dt.date.fromisoformat(mn.group("date"))
            except ValueError:
                continue
            term = short if mn.group("kind") in SHORT_KINDS else long_
            if (ndate - today).days > term:
                over_term.append(f"{path}: a {mn.group('kind')} tag runs {term} days; this one expires {ndate}, "
                                 f"{(ndate - today).days} days out")
            if ctx.type == "renew":
                continue
            for old_code, mo, old_line in removed_tags:
                if old_code != code_part(new) or mo.group("owner") != mn.group("owner"):
                    continue
                if strip_grace(new) != strip_grace(old_line):
                    edited.append(f"{path}: tag edited on a {ctx.type}/ branch: {new.strip()[:80]}")
    if over_term:
        c.outcome, c.detail = "FAIL", [f"terms: {short} days for todo/masks/skip, {long_} otherwise:"] + over_term
        c.safe_path = "shorten the date; a renew/ branch extends it, up to the maximum"
        return c
    if edited:
        c.outcome, c.detail = "FAIL", ["a tag's date, kind or reason changes on a renew/ branch only:"] + edited
        c.safe_path = ("git checkout -b renew/<slug> and change the tag line only (always audited). Appending "
                       "grace:<today> is the one exception, and it needs a BLOCKED SUNSET-EXPIRED line in your "
                       "own record")
        return c

    todo = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
    untagged = [f"{p}:{n}: {t.strip()[:80]}" for p, n, t in added_lines(ctx)
                if is_code(p) and not doc_excluded(p) and todo.search(t) and not SUNSET_RE.search(t)]
    if untagged:
        c.outcome, c.detail = "FAIL", ["temporary markers added without a sunset tag:"] + untagged
        c.safe_path = (f"# SUNSET {today + dt.timedelta(days=short)} todo owner:{ctx.slug or '<task-id>'} "
                       f"reason:<one line> — or do it now")
        return c
    c.detail.append(f"{live} live tag(s), none expired" + (f"; in grace: {len(in_grace)}" if in_grace else ""))
    c.detail += in_grace
    c.detail.append(f"the per-kind term is checked on added and renewed lines; tree-wide only the "
                    f"{max_}-day maximum, so a legal pre-existing tag never blocks an unrelated change")
    c.detail.append(f"renewal count <= {ctx.policy.get('RENEWALS_MAX')} is not automated (renewals_cap NOT_RUN)")
    return c


# ----------------------------------------------------------------------------- checks: records

REQ_SPEC = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*([=<>!~]=?|$)")


def manifest_added_deps(ctx: Ctx) -> list[tuple[str, str]]:
    """(manifest, package-name) for dependency specs added in this change (Python manifests only)."""
    out = []
    for path in changed_files(ctx, "AM"):
        if not matches_any(path, MANIFESTS):
            continue
        for _, _, text in added_lines(ctx, path):
            t = text.strip()
            if not t or t.startswith("#"):
                continue
            if path.endswith(".txt"):
                m = REQ_SPEC.match(t)
                if m and not t.startswith("-"):
                    out.append((path, m.group(1).lower().replace("_", "-")))
            else:
                for q in re.findall(r"[\"']([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*[=<>!~][^\"']*[\"']", t):
                    out.append((path, q.lower().replace("_", "-")))
    return out


def check_records(ctx: Ctx) -> Check:
    c = Check("records", "records" in ctx.required, "PASS")
    if ctx.record_path is None:
        c.outcome, c.detail = "FAIL", list(ctx.type_problems)
        c.safe_path = ("cp docs/changes/_TEMPLATE.md docs/changes/<type>-<slug>.md, fill it as you go, and commit "
                       "it (uncommitted files are not evidence)")
        return c
    rec, t = ctx.record, ctx.type
    problems = []
    if t in ("feature", "fix") and all(is_placeholder(w) for w in rec.get("WHY", [""])):
        problems.append("WHY: one sentence — <decision> instead of <alternative>, because <clause>")
    if t in ("feature", "fix", "refactor") and all(is_placeholder(x) for x in rec.get("TESTS", [""])):
        problems.append("TESTS: the exact test commands you ran")
    new_src = changed_files(ctx, "A", "src/")
    if new_src and all(is_placeholder(s) for s in rec.get("SEARCHED", [""])):
        problems.append(f"SEARCHED: required — new files under src/: {', '.join(new_src[:5])}")
    dep_names = {re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)", d).group(1).lower().replace("_", "-")
                 for d in rec.get("DEP", []) if not is_placeholder(d) and re.match(r"[A-Za-z0-9]", d)}
    for manifest, name in manifest_added_deps(ctx):
        if name not in dep_names:
            problems.append(f"DEP: required for '{name}' added in {manifest} "
                            f"(lookup, published date, REASON, INSTEAD-OF)")
    if problems:
        c.outcome, c.detail = "FAIL", [f"{ctx.record_path} is incomplete:"] + problems
        c.safe_path = "each line is one sentence or one command; write it at the moment of the decision"
        return c
    have = [k for k in ("TYPE", "WHY", "SEARCHED", "DEP", "TESTS") if rec.get(k)]
    c.detail.append(f"{ctx.record_path} committed at {ctx.subject[:10]} with {', '.join(have)}")
    if rec.get("ALLOWANCE"):
        c.detail.append("ALLOWANCE grant present: this change is in the 100% audit set")
    if rec.get("SEARCHED"):
        c.detail.append("SEARCHED replay on the base commit is not automated (searched_replay NOT_RUN)")
    return c


def check_deps(ctx: Ctx) -> Check:
    c = Check("deps", "deps" in ctx.required, "PASS")
    deps = [d for d in ctx.record.get("DEP", []) if not is_placeholder(d)]
    if not deps:
        c.detail.append("no DEP lines to verify")
        return c
    if os.environ.get("DEPS_OFFLINE") == "1":
        c.outcome = "NOT_RUN"
        c.detail = [f"{len(deps)} DEP line(s) not verified: DEPS_OFFLINE=1 (an explicit skip is reported, never "
                    f"counted as a pass)"]
        c.safe_path = "rerun with network access; an unchecked dependency record does not authorize a merge"
        return c
    min_age = policy_int(ctx, "DEP_MIN_AGE")
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
            raise GateError(f"the registry returned HTTP {e.code} for {name}; rerun with network access or set "
                            f"DEPS_OFFLINE=1")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise GateError(f"the registry is unreachable ({e}); rerun with network access or set DEPS_OFFLINE=1")
        uploads = [u.get("upload_time_iso_8601", "") for u in data.get("urls", []) if u.get("upload_time_iso_8601")]
        if not uploads:
            bad.append(f"{name}=={version}: no files published for this version")
            continue
        first = min(dt.datetime.fromisoformat(u.replace("Z", "+00:00")) for u in uploads).date()
        age = (dt.date.today() - first).days
        if age < min_age:
            bad.append(f"{name}=={version}: published {first}, {age} days ago (< {min_age}; slopsquatting window)")
    if bad:
        c.outcome, c.detail = "FAIL", bad
        c.safe_path = ("use the version `pip index versions <pkg>` actually lists, or the stdlib or existing "
                       "dependency named in INSTEAD-OF")
        return c
    c.detail.append(f"{len(deps)} dependency record(s) exist on PyPI and are >= {min_age} days old")
    return c


# ----------------------------------------------------------------------------- checks: the verifier itself

def check_verifier_selftest(ctx: Ctx) -> Check:
    """A policy change is judged by the TRUSTED corpus, not by the one it ships (audit EV-01, T2)."""
    c = Check("verifier_selftest", "verifier_selftest" in ctx.required, "PASS")
    if ctx.type != "policy":
        c.outcome, c.detail = "NOT_RUN", ["runs only for a policy change (the candidate verifier's own corpus)"]
        c.required = False
        return c
    exp = export(ctx, ctx.subject)
    if not os.path.isfile(os.path.join(exp, "scripts", "gate_checks.py")):
        c.outcome, c.detail = "ERROR", ["no scripts/gate_checks.py at the subject commit"]
        return c
    comp = run_in(ctx, exp, [sys.executable, "-m", "py_compile", "scripts/gate_checks.py"], 120)
    if comp.returncode != 0:
        c.outcome = "FAIL"
        c.detail = ["the candidate verifier does not compile:"] + comp.stderr.strip().splitlines()[-4:]
        c.safe_path = "a verifier that cannot be imported would block every later change once it is merged"
        return c

    trusted = [p for p in ls_tree(ctx, ctx.policy_ref) if under(p, "scripts/tests/")]
    if not trusted:
        c.outcome = "ERROR"
        c.detail = [f"the policy ref {ctx.policy_ref[:10]} has no scripts/tests corpus to judge a verifier "
                    f"change with"]
        return c
    # Restore the trusted corpus over whatever the candidate ships: a deleted counterexample still runs.
    for p in trusted:
        dst = os.path.join(exp, p)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(show(ctx.root, ctx.policy_ref, p) or "")
    timeout = policy_int(ctx, "UNIT_TESTS_TIMEOUT")
    try:
        res = run_in(ctx, exp, pytest_argv(ctx, exp, *trusted), timeout)
    except subprocess.TimeoutExpired:
        c.outcome, c.detail = "ERROR", [f"the trusted corpus exceeded UNIT_TESTS_TIMEOUT={timeout}s"]
        return c
    outcome, tail = pytest_outcome(res)
    if outcome != "PASS":
        c.outcome = outcome
        c.detail = [f"the candidate verifier fails the corpus at {ctx.policy_ref[:10]} "
                    f"({len(trusted)} file(s), restored over the candidate's):"] + tail
        c.safe_path = ("a change to the judge must keep passing the current counterexamples; you may add cases, "
                       "you may not remove them")
        return c

    # Then the cases this change adds. Reported apart, because "your new test fails" and "you broke an
    # existing counterexample" are different problems with different remedies.
    added = sorted({p for p in ls_tree(ctx, ctx.subject) if under(p, "scripts/tests/")} - set(trusted))
    added = [p for p in added if os.path.basename(p).startswith("test_")]
    if added:
        try:
            res2 = run_in(ctx, exp, pytest_argv(ctx, exp, *added), timeout)
        except subprocess.TimeoutExpired:
            c.outcome, c.detail = "ERROR", [f"the added self-tests exceeded UNIT_TESTS_TIMEOUT={timeout}s"]
            return c
        outcome2, tail2 = pytest_outcome(res2)
        if outcome2 != "PASS":
            c.outcome = outcome2
            c.detail = [f"the self-test(s) this change adds do not pass: {', '.join(added)}"] + tail2
            c.safe_path = "a counterexample you add must hold against the verifier you are shipping"
            return c
    c.detail.append(f"the candidate verifier compiles, passes the trusted corpus ({len(trusted)} file(s))"
                    + (f" and its own {len(added)} added file(s)" if added else ""))
    return c


def not_run(ctx: Ctx, cid: str, why: str) -> Check:
    return Check(cid, cid in ctx.required, "NOT_RUN", [why])


CHECKS = {
    "type": check_type,
    "protected_files": check_protected_files,
    "export_integrity": check_export_integrity,
    "harness_integrity": check_harness_integrity,
    "unit_tests": check_unit_tests,
    "test_inventory": check_test_inventory,
    "red_before_green": check_red_before_green,
    "h1": check_h1,
    "mocks": check_mocks,
    "masking_markers": check_masking_markers,
    "masking_ruff": check_masking_ruff,
    "sunset": check_sunset,
    "records": check_records,
    "deps": check_deps,
    "verifier_selftest": check_verifier_selftest,
    "ledger": lambda ctx: not_run(ctx, "ledger", "the complexity ledger is not implemented (it needs "
                                                 "duplicate-block and zero-reference tooling); advisory"),
    "mutation": lambda ctx: not_run(ctx, "mutation", f"mutation score >= {ctx.policy.get('MUTATION_MIN')} on "
                                                     f"touched lines is not automated"),
    "searched_replay": lambda ctx: not_run(ctx, "searched_replay", "replaying the SEARCHED command on the base "
                                                                   "commit is not automated"),
    "renewals_cap": lambda ctx: not_run(ctx, "renewals_cap", f"renewals <= {ctx.policy.get('RENEWALS_MAX')} per "
                                                             f"tag is not automated (it needs stable tag ids)"),
}


def run_check(ctx: Ctx, cid: str) -> Check:
    try:
        return CHECKS[cid](ctx)
    except GateError as e:
        return Check(cid, cid in ctx.required, "ERROR", [str(e)])
    except Exception:  # noqa: BLE001  # boundary: returns Check(outcome=ERROR) — a verifier that dies must never look like a pass
        return Check(cid, cid in ctx.required, "ERROR",
                     ["the verifier crashed:"] + traceback.format_exc().splitlines()[-4:])


# ----------------------------------------------------------------------------- reporting

def print_check(c: Check) -> None:
    flag = "required" if c.required else "advisory"
    print(f"{c.outcome:<7} {c.id:<18} [{flag}]")
    for d in c.detail:
        print(f"        {d}")
    if c.safe_path and c.outcome in ("FAIL", "ERROR", "NOT_RUN"):
        print(f"        Safe path: {c.safe_path}")


def result_json(ctx: Ctx, checks: list[Check], env: dict, prov: str, ref_sha: str | None) -> dict:
    required = [c for c in checks if c.required]
    reasons = []
    if not required:
        reasons.append("no required check ran")
    reasons += [f"{c.id} {c.outcome}" for c in required if c.outcome != "PASS"]
    if prov != "policy_ref":
        reasons.append(f"the running verifier is the '{prov}' copy, not the one at the policy ref")
    if ctx.profile != "enforced":
        reasons.append(f"the {ctx.profile} profile never authorizes a merge")
    return {
        "verifier_version": VERSION,
        "subject_sha": ctx.subject,
        "base_sha": ctx.base,
        "policy_ref_sha": ctx.policy_ref,
        "verifier_sha": verifier_sha(),
        "verifier_sha_at_policy_ref": ref_sha,
        "verifier_provenance": prov,
        "policy_digest": policy_digest(ctx),
        "environment_digest": sha256(json.dumps(env, sort_keys=True).encode()),
        "environment": env,
        "profile": ctx.profile,
        "branch": ctx.branch,
        "change_type": ctx.type,
        "record_path": ctx.record_path,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "checks": [{"id": c.id, "required": c.required, "outcome": c.outcome, "detail": c.detail,
                    "safe_path": c.safe_path} for c in checks],
        "merge_eligible": not reasons,
        "ineligible_reasons": reasons,
    }


def exit_code(checks: list[Check], eligible: bool) -> int:
    req = [c for c in checks if c.required]
    if eligible:
        return 0
    if not req or any(c.outcome in ("ERROR", "NOT_RUN") for c in req):
        return 3
    if any(c.outcome == "FAIL" for c in req):
        return 1
    return 3  # every required check passed and the run is still not authorized (provenance, profile)


def cmd_gate(args: argparse.Namespace) -> int:
    try:
        ctx = build_ctx(args)
    except GateError as e:
        print(f"ERROR   gate: {e}", file=sys.stderr)
        return 3
    try:
        env = environment()
        prov, ref_sha = provenance(ctx)
        checks = [run_check(ctx, cid) for cid in ORDER]
        for c in checks:
            print_check(c)
        result = result_json(ctx, checks, env, prov, ref_sha)
        if args.out:
            os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as fh:
                json.dump(result, fh, indent=2)
        req = [c for c in checks if c.required]
        n_pass = sum(1 for c in req if c.outcome == "PASS")
        advisory_not_run = sum(1 for c in checks if not c.required and c.outcome == "NOT_RUN")
        print(f"gate: subject {ctx.subject[:10]} base {ctx.base[:10]} policy {ctx.policy_ref[:10]} "
              f"verifier {prov} profile {ctx.profile} · "
              f"merge_eligible={str(result['merge_eligible']).lower()} · "
              f"{n_pass}/{len(req)} required PASS · {advisory_not_run} advisory NOT_RUN"
              + (f" · result {args.out}" if args.out else ""))
        for r in result["ineligible_reasons"]:
            print(f"  not eligible: {r}")
        return exit_code(checks, result["merge_eligible"])
    finally:
        cleanup(ctx)


def cmd_check(args: argparse.Namespace) -> int:
    try:
        ctx = build_ctx(args)
    except GateError as e:
        print(f"ERROR   check: {e}", file=sys.stderr)
        return 3
    try:
        ids = GROUPS.get(args.id, [args.id])
        unknown = [i for i in ids if i not in CHECKS]
        if unknown:
            print(f"unknown check(s): {', '.join(unknown)}; known: {', '.join(ORDER)}; "
                  f"groups: {', '.join(GROUPS)}", file=sys.stderr)
            return 4
        checks = [run_check(ctx, i) for i in ids]
        for c in checks:
            print_check(c)
        worst = max(checks, key=lambda c: {"PASS": 0, "FAIL": 1, "NOT_RUN": 2, "ERROR": 3}[c.outcome])
        return {"PASS": 0, "FAIL": 1, "NOT_RUN": 3, "ERROR": 3}[worst.outcome]
    finally:
        cleanup(ctx)


def cmd_audit_select(args: argparse.Namespace) -> int:
    try:
        ctx = build_ctx(args)
    except GateError as e:
        print(f"ERROR   audit-select: {e}", file=sys.stderr)
        return 3
    try:
        salt = os.environ.get("AUDIT_SALT", "")
        if not salt:
            print("ERROR   audit-select: set AUDIT_SALT in the environment (kept outside the repository) so "
                  "implementers cannot predict the draw", file=sys.stderr)
            return 3
        rate = float(ctx.policy.get("AUDIT_RATE", "0.20"))
        reasons = []
        if ctx.type in ("renew", "policy"):
            reasons.append(f"{ctx.type} change")
        blob = " ".join(v for vs in ctx.record.values() for v in vs)
        if "POLICY-GAP" in blob or "SUNSET-EXPIRED" in blob:
            reasons.append("POLICY-GAP or SUNSET-EXPIRED filing in the record")
        if ctx.record.get("ALLOWANCE"):
            reasons.append("allowance grant")
        if any(not is_placeholder(a) for a in ctx.record.get("ACCEPTANCE", [])):
            reasons.append("acceptance revision")
        if any(not is_placeholder(e) for e in ctx.record.get("EXCEPTION", [])):
            reasons.append("recorded exception")
        for s in ctx.record.get("SEARCHED", []):
            m = re.search(r"→\s*(\d+)\s+hits?", s)
            if "NONE-FITS" in s and m and int(m.group(1)) > 0:
                reasons.append("NONE-FITS with hits")
        adds = added_lines(ctx)
        if any(" masks " in t and SUNSET_RE.search(t) for _, _, t in adds):
            reasons.append("masks sunset tag added")
        if any(BOUNDARY_NOTE_RE.search(t) for p, _, t in adds if is_code(p)):
            reasons.append("boundary exemption added")
        changed = changed_files(ctx)
        always = ctx.policy.get("AUDIT_ALWAYS_PATHS", "").split()
        hits = [f for f in changed if matches_any(f, always)]
        if hits:
            reasons.append(f"AUDIT_ALWAYS_PATHS: {', '.join(hits[:3])}")
        if any(is_protected(f, ctx.protected) for f in changed):
            reasons.append("protected set changed")
        draw = int(sha256(f"{ctx.subject}:{salt}".encode())[:8], 16) / 2**32
        if draw < rate:
            reasons.append(f"random draw {draw:.3f} < {rate}")
        label = ctx.slug or ctx.subject[:10]
        if reasons:
            print(f"AUDIT selected {ctx.subject[:10]} ({label}): " + "; ".join(reasons))
            print(f"  auditor: fresh instance, run .claude/skills/audit/SKILL.md with SUBJECT={ctx.subject} "
                  f"BASE={ctx.base}, write docs/audits/{label}.md")
        else:
            print(f"AUDIT not selected {ctx.subject[:10]} ({label}): draw {draw:.3f} >= {rate}, no 100% trigger")
        return 0
    finally:
        cleanup(ctx)


def cleanup(ctx: Ctx) -> None:
    for d in ctx.tmp:
        shutil.rmtree(d, ignore_errors=True)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="gate_checks.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--subject", default=os.environ.get("SUBJECT", "HEAD"))
        p.add_argument("--base", default=os.environ.get("BASE", ""))
        p.add_argument("--policy-ref", default=os.environ.get("POLICY_REF", os.environ.get("VERIFIER_REF", "")))
        p.add_argument("--branch", default=os.environ.get("BRANCH", ""))
        # The profile selects the required set, so it is never taken from the environment (audit EV-02, T5).
        p.add_argument("--profile", default="enforced", choices=["enforced", "advisory"])

    g = sub.add_parser("gate", help="run every check; write the result JSON")
    common(g)
    g.add_argument("--out", default=os.environ.get("GATE_OUT", ""))
    c = sub.add_parser("check", help="run one check or group")
    c.add_argument("id")
    common(c)
    a = sub.add_parser("audit-select", help="draw the post-merge audit sample")
    common(a)
    args = ap.parse_args(argv)
    return {"gate": cmd_gate, "check": cmd_check, "audit-select": cmd_audit_select}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
