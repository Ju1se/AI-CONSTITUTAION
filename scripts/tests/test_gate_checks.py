"""Regression tests for the merge-gate verifier.

Each test builds a throwaway git repository from the kit's own files, commits a scenario, and runs the
verifier the way CI does. The scenario ids (C01, P01, P03, …) are the audit's counterexamples; the
verifier is not trusted until every one of them produces the outcome the audit asked for:
a violation is FAIL, an environment problem is ERROR, an explicit skip is NOT_RUN, and none of the
three ever yields merge_eligible.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[2]
KIT_FILES = ["policy.mk", "AGENTS.md", "Makefile", "tests/MOCK_ALLOWLIST", "docs/changes/_TEMPLATE.md",
             "docs/agents-policy.md", "scripts/gate_checks.py"]
TODAY = dt.date.today()


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=check)


def write(repo: Path, rel: str, content: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def commit_all(repo: Path, msg: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def record(repo: Path, type_: str, slug: str, **fields: str) -> None:
    lines = [f"TYPE: {type_}"] + [f"{k}: {v}" for k, v in fields.items()]
    write(repo, f"docs/changes/{type_}-{slug}.md", "\n".join(lines) + "\n")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "user.email", "t@t")
    git(r, "config", "user.name", "t")
    for rel in KIT_FILES:
        dst = r / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(KIT / rel, dst)
    write(r, "src/__init__.py", "")
    write(r, "src/core.py", "def value():\n    return 1\n")
    write(r, "tests/test_core.py", "from src.core import value\n\n\ndef test_value():\n    assert value() == 1\n")
    commit_all(r, "chore: baseline")
    return r


def run_gate(repo: Path, branch: str | None = None, subject: str = "HEAD", base: str = "main",
             policy_ref: str = "main", profile: str = "enforced", env_extra: dict | None = None):
    out = repo / ".gate" / "result.json"
    if out.exists():
        out.unlink()
    cmd = [sys.executable, str(repo / "scripts/gate_checks.py"), "gate", "--subject", subject, "--base", base,
           "--policy-ref", policy_ref, "--profile", profile, "--out", str(out)]
    if branch:
        cmd += ["--branch", branch]
    res = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, env={**os.environ, **(env_extra or {})})
    result = json.loads(out.read_text()) if out.exists() else None
    return res, result


def outcome(result: dict, cid: str) -> str:
    return next(c["outcome"] for c in result["checks"] if c["id"] == cid)


def feature_branch(repo: Path, name: str = "greeting") -> None:
    """C01: a legitimate test-first feature — tests committed, then implementation, record committed."""
    git(repo, "checkout", "-q", "-b", f"feature/{name}")
    write(repo, f"tests/test_{name}.py",
          f"from src.{name} import greet\n\n\ndef test_greet():\n    assert greet('a') == 'hello, a'\n")
    commit_all(repo, "test: greet")
    write(repo, f"src/{name}.py", "def greet(name):\n    return f'hello, {name}'\n")
    record(repo, "feature", name, WHY="an f-string instead of concatenation, because readability.",
           SEARCHED='rg -n "greet" src/ → 0 hits | NONE-FITS: n/a', TESTS="python -m pytest -q tests")
    commit_all(repo, "feat: greet")


def expect_blocked_ruff_or(result: dict, res: subprocess.CompletedProcess) -> None:
    """When ruff is absent the required masking_ruff check is NOT_RUN and blocks the merge — by design."""
    if shutil.which("ruff"):
        assert res.returncode == 0, res.stdout + res.stderr
        assert result["merge_eligible"] is True
    else:
        assert res.returncode == 3
        assert outcome(result, "masking_ruff") == "NOT_RUN"
        assert result["merge_eligible"] is False


# ----------------------------------------------------------------------------- C01 and the trust core

def test_c01_legitimate_feature_is_eligible(repo):
    feature_branch(repo)
    res, result = run_gate(repo, branch="feature/greeting")
    assert result is not None
    assert outcome(result, "unit_tests") == "PASS"
    assert outcome(result, "h1") == "PASS"
    assert outcome(result, "records") == "PASS"
    assert outcome(result, "ledger") == "NOT_RUN"  # advisory, reported, not authorizing
    assert result["change_type"] == "feature"
    assert result["subject_sha"] == git(repo, "rev-parse", "HEAD").stdout.strip()
    expect_blocked_ruff_or(result, res)


def test_result_identity_fields_are_bound(repo):
    feature_branch(repo)
    _, result = run_gate(repo, branch="feature/greeting")
    assert result["base_sha"] == git(repo, "rev-parse", "main").stdout.strip()
    assert result["policy_ref_sha"] == result["base_sha"]
    assert len(result["verifier_sha"]) == 64 and len(result["policy_digest"]) == 64 and len(result["environment_digest"]) == 64
    assert {c["id"] for c in result["checks"]} >= {"type", "protected_files", "unit_tests", "h1", "records", "deps"}


def test_p01_failing_business_tests_block_merge(repo):
    git(repo, "checkout", "-q", "-b", "fix/value")
    write(repo, "tests/test_value_two.py", "from src.core import value\n\n\ndef test_type():\n    assert isinstance(value(), int)\n")
    commit_all(repo, "test: type")
    write(repo, "src/core.py", "def value():\n    return 2\n")  # breaks the frozen test_core.py
    record(repo, "fix", "value", WHY="2 instead of 1, because the spec changed.", TESTS="python -m pytest -q tests")
    commit_all(repo, "fix: value")
    res, result = run_gate(repo, branch="fix/value")
    assert outcome(result, "unit_tests") == "FAIL"
    assert result["merge_eligible"] is False
    assert res.returncode == 1


def test_p03_invalid_base_is_error_not_empty_success(repo):
    feature_branch(repo)
    res, result = run_gate(repo, branch="feature/greeting", base="DOES_NOT_EXIST")
    assert res.returncode == 3
    assert result is None  # no result is written for an invalid subject/base pair
    assert "not a commit" in res.stderr


def test_base_must_be_ancestor_of_subject(repo):
    feature_branch(repo)
    git(repo, "checkout", "-q", "main")
    write(repo, "README.md", "unrelated\n")
    other = commit_all(repo, "chore: unrelated on main")
    res, result = run_gate(repo, subject="feature/greeting", base=other)
    assert res.returncode == 3 and result is None
    assert "not an ancestor" in res.stderr


def test_p04_uncommitted_allowlist_edit_does_not_change_the_verdict(repo):
    git(repo, "checkout", "-q", "-b", "test/mock")
    write(repo, "tests/test_mock.py",
          "from unittest.mock import patch\n\n\ndef test_m():\n    with patch('src.core.value') as v:\n        v.return_value = 1\n")
    record(repo, "test", "mock")
    commit_all(repo, "test: in-repo mock")
    _, before = run_gate(repo, branch="test/mock")
    assert outcome(before, "mocks") == "FAIL"
    with open(repo / "tests/MOCK_ALLOWLIST", "a") as fh:  # uncommitted working-tree edit
        fh.write("src.\n")
    _, after = run_gate(repo, branch="test/mock")
    assert outcome(after, "mocks") == "FAIL"
    assert after["policy_digest"] == before["policy_digest"]


def test_p05_uncommitted_tag_removal_does_not_change_the_verdict(repo):
    feature_branch(repo)
    write(repo, "src/greeting.py",
          "def greet(name):\n    return f'hello, {name}'\n\n# SUNSET 2026-01-01 todo owner:feature-greeting reason:remove shim\n")
    commit_all(repo, "feat: expired tag")
    _, before = run_gate(repo, branch="feature/greeting")
    assert outcome(before, "sunset") == "FAIL"
    write(repo, "src/greeting.py", "def greet(name):\n    return f'hello, {name}'\n")  # uncommitted
    res, after = run_gate(repo, branch="feature/greeting")
    assert outcome(after, "sunset") == "FAIL"
    assert res.returncode == 1


def test_p16_uncommitted_record_is_not_evidence(repo):
    git(repo, "checkout", "-q", "-b", "feature/norecord")
    write(repo, "tests/test_n.py", "from src.n import n\n\n\ndef test_n():\n    assert n() == 1\n")
    commit_all(repo, "test: n")
    write(repo, "src/n.py", "def n():\n    return 1\n")
    commit_all(repo, "feat: n")
    res, result = run_gate(repo, branch="feature/norecord")
    assert outcome(result, "type") == "FAIL" and outcome(result, "records") == "FAIL"
    record(repo, "feature", "norecord", WHY="x instead of y, because z.", TESTS="pytest")  # uncommitted
    res, result = run_gate(repo, branch="feature/norecord")
    assert outcome(result, "records") == "FAIL"
    assert result["merge_eligible"] is False and res.returncode == 1


# ----------------------------------------------------------------------------- protected set (F04 / P25 / P06)

def test_p25_renew_branch_cannot_change_policy_parameters(repo):
    git(repo, "checkout", "-q", "-b", "renew/params")
    text = (repo / "policy.mk").read_text().replace("MUTATION_MIN         ?= 0.70", "MUTATION_MIN         ?= 0 # SUNSET")
    write(repo, "policy.mk", text)
    record(repo, "renew", "params")
    commit_all(repo, "renew: loosen")
    res, result = run_gate(repo, branch="renew/params")
    assert outcome(result, "protected_files") == "FAIL"
    assert result["merge_eligible"] is False and res.returncode == 1
    main_policy = git(repo, "show", "main:policy.mk").stdout
    assert "MUTATION_MIN         ?= 0.70" in main_policy  # the policy in force is the trusted ref's


def test_p06_chore_branch_cannot_modify_the_verifier(repo):
    git(repo, "checkout", "-q", "-b", "chore/verifier")
    with open(repo / "scripts/gate_checks.py", "a") as fh:
        fh.write("\n# candidate edit\n")
    record(repo, "chore", "verifier")
    commit_all(repo, "chore: touch verifier")
    res, result = run_gate(repo, branch="chore/verifier")
    assert outcome(result, "protected_files") == "FAIL"
    assert res.returncode == 1


def test_policy_change_is_not_eligible_without_verifier_selftests(repo):
    git(repo, "checkout", "-q", "-b", "policy/allowlist")
    with open(repo / "tests/MOCK_ALLOWLIST", "a") as fh:
        fh.write("boto3.\n")
    record(repo, "policy", "allowlist")
    commit_all(repo, "policy: allow boto3 mocks")
    res, result = run_gate(repo, branch="policy/allowlist")
    assert outcome(result, "protected_files") == "PASS"
    assert outcome(result, "verifier_selftest") == "ERROR"  # no scripts/tests in the fixture: ERROR, not PASS
    assert result["merge_eligible"] is False and res.returncode == 3


# ----------------------------------------------------------------------------- change type from the record (F09)

def test_type_comes_from_the_committed_record_when_no_branch_is_known(repo):
    feature_branch(repo)
    res, result = run_gate(repo)  # post-merge style: no --branch
    assert result["change_type"] == "feature"
    assert outcome(result, "type") == "PASS"


def test_branch_prefix_must_match_the_record(repo):
    feature_branch(repo)
    _, result = run_gate(repo, branch="fix/greeting")
    assert outcome(result, "type") == "FAIL"
    assert result["merge_eligible"] is False


def test_unrelated_docs_change_on_chore_is_not_misjudged(repo):
    git(repo, "checkout", "-q", "-b", "chore/readme")
    write(repo, "README.md", "# project\n\nA blank line change should not look like a dependency or a test.\n")
    record(repo, "chore", "readme")
    commit_all(repo, "chore: readme")
    res, result = run_gate(repo, branch="chore/readme")
    assert outcome(result, "type") == "PASS" and outcome(result, "records") == "PASS"
    assert outcome(result, "deps") == "PASS"
    expect_blocked_ruff_or(result, res)


# ----------------------------------------------------------------------------- outcome semantics

def test_deps_offline_is_not_run_and_blocks(repo):
    feature_branch(repo)
    write(repo, "requirements.txt", "requests==2.31.0\n")
    record(repo, "feature", "greeting", WHY="a instead of b, because c.", TESTS="pytest",
           SEARCHED='rg -n "greet" src/ → 0 hits | NONE-FITS: n/a',
           DEP="requests==2.31.0 lookup:pip index versions requests published:2023-05-22 | REASON: http | INSTEAD-OF: urllib")
    commit_all(repo, "feat: dep")
    res, result = run_gate(repo, branch="feature/greeting", env_extra={"DEPS_OFFLINE": "1"})
    assert outcome(result, "deps") == "NOT_RUN"
    assert result["merge_eligible"] is False and res.returncode == 3


def test_added_dependency_without_dep_line_fails_records(repo):
    feature_branch(repo)
    write(repo, "requirements.txt", "requests==2.31.0\n")
    commit_all(repo, "feat: dep without record line")
    res, result = run_gate(repo, branch="feature/greeting", env_extra={"DEPS_OFFLINE": "1"})
    assert outcome(result, "records") == "FAIL"
    assert any("requests" in d for c in result["checks"] if c["id"] == "records" for d in c["detail"])


def test_advisory_profile_never_authorizes_a_merge(repo):
    """v0.4: the advisory profile narrows the required set and never sets merge_eligible (audit EV-02).

    The v0.3 version of this test asserted the opposite and so pinned the defect in place; the audit
    listed it under 'tests that assert less than their names'.
    """
    feature_branch(repo)
    res, result = run_gate(repo, branch="feature/greeting", profile="advisory")
    required = {c["id"] for c in result["checks"] if c["required"]}
    assert required == {"type", "protected_files", "unit_tests"}
    assert result["merge_eligible"] is False
    assert any("advisory" in r for r in result["ineligible_reasons"])
    assert res.returncode != 0


# ----------------------------------------------------------------------------- sunset (P09 / P10 / P11)

def test_p09_partial_sunset_tag_exempts_nothing(repo):
    git(repo, "checkout", "-q", "-b", "test/skip")
    write(repo, "tests/test_skip.py",
          "import pytest\n\n\n@pytest.mark.skip(reason='later')  # SUNSET\ndef test_later():\n    assert False\n")
    record(repo, "test", "skip")
    commit_all(repo, "test: skip with partial tag")
    _, result = run_gate(repo, branch="test/skip")
    assert outcome(result, "masking_markers") == "FAIL"
    assert outcome(result, "sunset") == "FAIL"


def test_p10_short_term_is_enforced_per_kind(repo):
    feature_branch(repo)
    far = TODAY + dt.timedelta(days=100)
    write(repo, "src/greeting.py",
          f"def greet(name):\n    return f'hello, {{name}}'\n\n# SUNSET {far} todo owner:feature-greeting reason:later\n")
    commit_all(repo, "feat: long todo")
    _, result = run_gate(repo, branch="feature/greeting")
    assert outcome(result, "sunset") == "FAIL"
    # The message names the term for the kind; assert the term, not the incidental wording.
    assert any("todo tag runs 30 days" in d for c in result["checks"] if c["id"] == "sunset" for d in c["detail"])


def test_p11_grace_requires_a_filed_blocked_record(repo):
    feature_branch(repo)
    tag = f"# SUNSET 2026-01-01 compat owner:feature-greeting reason:old callers grace:{TODAY}\n"
    write(repo, "src/greeting.py", "def greet(name):\n    return f'hello, {name}'\n\n" + tag)
    commit_all(repo, "feat: grace without filing")
    _, result = run_gate(repo, branch="feature/greeting")
    assert outcome(result, "sunset") == "FAIL"
    record(repo, "feature", "greeting", WHY="a instead of b, because c.", TESTS="pytest",
           SEARCHED='rg -n "greet" src/ → 0 hits | NONE-FITS: n/a',
           BLOCKED="SUNSET-EXPIRED: deleting the compat shim breaks tests/test_old.py")
    commit_all(repo, "feat: file the grace")
    _, result = run_gate(repo, branch="feature/greeting")
    assert outcome(result, "sunset") == "PASS"


# ----------------------------------------------------------------------------- the two sanctioned catch-all shapes

def test_boundary_exemption_passes_and_is_reported_but_bare_noqa_fails(repo):
    feature_branch(repo)
    write(repo, "src/greeting.py",
          "class Failure(Exception):\n    pass\n\n\ndef greet(name):\n    return f'hello, {name}'\n\n\n"
          "def guarded(fn):\n    try:\n        return fn()\n"
          "    except Exception as e:  # noqa: BLE001  # boundary: returns Failure so the caller must match it\n"
          "        return Failure(str(e))\n")
    commit_all(repo, "feat: boundary")
    _, result = run_gate(repo, branch="feature/greeting")
    assert outcome(result, "masking_markers") == "PASS"
    assert any("boundary exemption" in d for c in result["checks"] if c["id"] == "masking_markers" for d in c["detail"])
    write(repo, "src/greeting.py",
          "def greet(name):\n    return f'hello, {name}'\n\n\ndef risky():\n    x = 1  # noqa\n    return x\n")
    commit_all(repo, "feat: bare noqa")
    _, result = run_gate(repo, branch="feature/greeting")
    assert outcome(result, "masking_markers") == "FAIL"
