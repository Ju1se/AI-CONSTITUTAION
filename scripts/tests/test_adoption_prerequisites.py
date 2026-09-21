"""The four defects the audit of the two proposed amendments confirmed, as fixtures.

Each test is the reproduction from `docs/audits/policy-legislative-and-judicial.md`, with its control.
Written after the fix rather than before it — the repository's test-first rule binds feature and fix
changes, not a policy change to the verifier, but the order is worth stating rather than implying.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest
from _harness import RUFF, Repo, detail, outcome

BASE_SRC = "def value():\n    return 1\n"
BASE_TEST = "from src.core import value\n\n\ndef test_value():\n    assert value() == 1\n"
APPROVAL = ("correction; approver:owner-designated-reviewer date:2026-09-20 decision:D-17 | "
            "reason:the spec now requires 2 | spec v1->v2 | old:value()==1 new:value()==2 | "
            "transition:this commit | retained:the v1 case stays in history")


# ----------------------------------------------------------------- LM-1 · the conftest verdict rewrite

CONFTEST_XFAIL = (
    "import pytest\n\n\n"
    "@pytest.fixture(autouse=True)\n"
    "def _soften(request):\n"
    "    request.node.add_marker(pytest.mark.xfail(strict=False, reason='flaky'))\n"
)


def _red_suite_change(r: Repo, branch: str, slug: str, conftest: str | None) -> None:
    """A fix/ change that genuinely breaks the committed acceptance, optionally shipping a conftest."""
    r.branch(branch)
    r.write("tests/test_new.py", "from src.core import value\n\n\ndef test_is_int():\n    assert isinstance(value(), int)\n")
    if conftest is not None:
        r.write("tests/conftest.py", conftest)
    r.commit("test: a new case")
    r.write("src/core.py", "def value():\n    return 2\n")   # breaks tests/test_core.py
    r.record("fix", slug, WHY="2 instead of 1, because the spec changed.", TESTS="python -m pytest -q tests")
    r.commit("fix: value")


def test_conftest_that_rewrites_the_verdict_is_refused_lm01(tmp_path):
    """LM-1: an autouse fixture marking every test xfail made a red suite report PASS at 14/14."""
    r = Repo(tmp_path / "r")
    _red_suite_change(r, "fix/soften", "soften", CONFTEST_XFAIL)
    _, res, out = r.gate("fix/soften")
    assert res is not None, out
    assert outcome(res, "harness_integrity") == "FAIL", detail(res, "harness_integrity")
    assert "tests/conftest.py" in detail(res, "harness_integrity")
    assert res["merge_eligible"] is False


def test_the_same_red_suite_without_the_conftest_is_refused_by_unit_tests_control(tmp_path):
    """Control: the byte-identical change minus the conftest must fail on the suite, not on the harness."""
    r = Repo(tmp_path / "r")
    _red_suite_change(r, "fix/plain", "plain", None)
    _, res, out = r.gate("fix/plain")
    assert res is not None, out
    assert outcome(res, "harness_integrity") == "PASS", detail(res, "harness_integrity")
    assert outcome(res, "unit_tests") == "FAIL", detail(res, "unit_tests")


def test_an_ordinary_conftest_fixture_is_still_allowed_control(tmp_path):
    """Control: a conftest with a plain fixture and no verdict machinery must not be refused."""
    r = Repo(tmp_path / "r")
    r.branch("feature/fixtures")
    r.write("tests/conftest.py", "import pytest\n\n\n@pytest.fixture\ndef sample():\n    return 7\n")
    r.write("tests/test_sample.py", "from src.core import double\n\n\ndef test_double(sample):\n    assert double(sample) == 14\n")
    r.commit("test: sample fixture")
    r.write("src/core.py", BASE_SRC + "\n\ndef double(x):\n    return 2 * x\n")
    r.record("feature", "fixtures", WHY="a fixture instead of a literal, because two cases need it.",
             SEARCHED='rg -n "double" src/ → 0 hits | NONE-FITS: n/a', TESTS="python -m pytest -q tests")
    r.commit("feat: double")
    _, res, out = r.gate("feature/fixtures")
    assert res is not None, out
    assert outcome(res, "harness_integrity") == "PASS", detail(res, "harness_integrity")
    assert "cannot close the class" in detail(res, "harness_integrity")


# ----------------------------------------------------------------- LM-2 · the unconditional test exemption

def _revise_acceptance(r: Repo, slug: str, acceptance: str | None) -> None:
    r.branch(f"test/{slug}")
    r.write("tests/test_core.py", "from src.core import value\n\n\ndef test_value():\n    assert value() == 2\n")
    fields = {"ACCEPTANCE": acceptance} if acceptance else {}
    r.record("test", slug, **fields)
    r.commit("test: revise the acceptance")


def test_a_test_change_revising_acceptance_without_a_recorded_decision_is_refused_lm02(tmp_path):
    """LM-2: declaring TYPE: test disabled the frozen-test rule outright; §3 requires a decision."""
    r = Repo(tmp_path / "r")
    _revise_acceptance(r, "silent", None)
    _, res, out = r.gate("test/silent")
    assert res is not None, out
    assert outcome(res, "h1") == "FAIL", detail(res, "h1")
    assert "ACCEPTANCE" in detail(res, "h1") or "ACCEPTANCE" in next(
        c["safe_path"] for c in res["checks"] if c["id"] == "h1")
    assert res["merge_eligible"] is False


def test_a_test_change_with_a_recorded_decision_is_allowed_and_audited_control(tmp_path):
    """Control for LM-2: §3's route must work, and the change must land in the 100% audit set."""
    r = Repo(tmp_path / "r")
    _revise_acceptance(r, "decided", APPROVAL)
    _, res, out = r.gate("test/decided")
    assert res is not None, out
    assert outcome(res, "h1") == "PASS", detail(res, "h1")
    assert "100% audit set" in detail(res, "h1")
    assert "independent" in detail(res, "h1")   # the scope the gate does not check
    rc, sel = r.check("type", branch="test/decided")  # sanity: the record resolved
    assert rc == 0, sel
    res2 = r.run("audit-select", "--subject", "HEAD", "--base", "main", "--policy-ref", "main",
                 "--branch", "test/decided", env={"AUDIT_SALT": "fixed-salt-for-this-test"})
    assert "acceptance revision" in res2.stdout, res2.stdout + res2.stderr


def test_deleting_a_committed_test_is_still_refused_even_with_a_decision(tmp_path):
    """A recorded decision revises acceptance; it does not license losing a case silently."""
    r = Repo(tmp_path / "r")
    r.branch("test/drop")
    r.rm("tests/test_core.py")
    r.record("test", "drop", ACCEPTANCE=APPROVAL)
    r.commit("test: drop the case")
    _, res, out = r.gate("test/drop")
    assert res is not None, out
    assert outcome(res, "test_inventory") == "FAIL", detail(res, "test_inventory")
    assert res["merge_eligible"] is False


# ----------------------------------------------------------------- LM-8 · `<` is not a placeholder

def test_a_truthful_why_containing_a_comparison_is_accepted_lm08(tmp_path):
    """LM-8: `is_placeholder` was `"<" in value`, so a bound such as n <= 3 read as an unfilled slot."""
    r = Repo(tmp_path / "r")
    r.legal_feature("bounded")
    r.record("feature", "bounded",
             WHY="a bound of n <= 3 instead of unbounded retry, because §2 refuses an unbounded loop.",
             SEARCHED='rg -n "greet" src/ → 0 hits | NONE-FITS: n/a',
             TESTS="python -m pytest -q tests 2>&1 | tail -1")
    r.commit("docs: record with a comparison in it")
    _, res, out = r.gate("feature/bounded")
    assert res is not None, out
    assert outcome(res, "records") == "PASS", detail(res, "records")


def test_an_unfilled_template_slot_is_still_refused_control(tmp_path):
    """Control for LM-8: the angle-bracket token must still be caught."""
    r = Repo(tmp_path / "r")
    r.legal_feature("unfilled")
    r.record("feature", "unfilled", WHY="<decision> instead of <alternative>, because <one clause>.",
             TESTS="python -m pytest -q tests")
    r.commit("docs: leave the template unfilled")
    _, res, out = r.gate("feature/unfilled")
    assert res is not None, out
    assert outcome(res, "records") == "FAIL", detail(res, "records")


# ----------------------------------------------------------------- J-1 · the gate's identity must not leak

@pytest.mark.skipif(shutil.which("make") is None, reason="make is not installed")
def test_the_gate_does_not_hand_its_own_subject_to_what_it_spawns_j01(tmp_path):
    """J-1: `make gate SUBJECT=… BASE=…` exported them, and nested gates read them as their own inputs.

    Driven at the level the defect lives at: a child process started by `run_in` must not see them.
    """
    r = Repo(tmp_path / "r")
    r.legal_feature()
    poisoned = {"SUBJECT": "deadbeef", "BASE": "cafebabe", "BRANCH": "policy/not-this-one",
                "GATE_OUT": "/tmp/not-here.json", "GATE_PROFILE": "advisory"}
    _, res, out = r.gate("feature/greeting", env=poisoned)
    assert res is not None, out
    # The run judged what it was told on the command line, not what the environment claimed.
    assert res["subject_sha"] == r.rev("HEAD"), res["subject_sha"]
    assert res["branch"] == "feature/greeting"
    assert res["profile"] == "enforced"


def test_a_spawned_process_sees_no_inherited_identity_j01(tmp_path):
    """The mechanism itself: run_in must strip the identity variables from the child environment."""
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "gc_under_test", Path(__file__).resolve().parents[1] / "gate_checks.py")
    gc = importlib.util.module_from_spec(spec)
    sys.modules["gc_under_test"] = gc
    spec.loader.exec_module(gc)
    for name in ("SUBJECT", "BASE", "BRANCH", "MAIN", "POLICY_REF", "VERIFIER_REF", "GATE_OUT",
                 "GATE_PROFILE"):
        assert name in gc.INHERITED_IDENTITY, f"{name} would leak into every spawned process"
    env = {**os.environ, "SUBJECT": "deadbeef", "BASE": "cafebabe", "GATE_OUT": "/tmp/x.json"}
    seen = subprocess.run([sys.executable, "-c",
                           "import os;print(','.join(k for k in ('SUBJECT','BASE','GATE_OUT') "
                           "if k in os.environ))"],
                          env={k: v for k, v in env.items() if k not in gc.INHERITED_IDENTITY},
                          capture_output=True, text=True)
    assert seen.stdout.strip() == "", f"leaked: {seen.stdout!r}"
