"""v0.4 regression tests for the non-verifier plumbing (spec §4) and the v0.3 behaviour it must keep.

These tests are written from `v04-spec.md` before the implementation exists. The §4 tests are static
assertions about shipped files (`.github/workflows/gate.yml`, `Makefile`, `policy.mk`) plus two
executable ones (`make gate`, the H1 hook driven on stdin); the last four pin down v0.3 behaviour that a
v0.4 rewrite must not silently drop.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from _harness import Repo, detail, outcome

KIT = Path(__file__).resolve().parents[2]
WORKFLOW = KIT / ".github/workflows/gate.yml"
MAKEFILE = KIT / "Makefile"
POLICY_MK = KIT / "policy.mk"
HOOK = KIT / ".claude/hooks/h1-test-source-separation.sh"
HAVE_MAKE = shutil.which("make") is not None


def run_make(repo: Repo, *overrides: str) -> subprocess.CompletedProcess:
    """Run `make gate` in a fixture repo with this interpreter as PY."""
    return subprocess.run(["make", "gate", f"PY={sys.executable}", *overrides],
                          cwd=str(repo.path), env=repo.env, capture_output=True, text=True)


def run_hook(repo: Repo, rel: str, payload: str | None = None) -> subprocess.CompletedProcess:
    """Drive the PreToolUse hook the way Claude Code does: the tool call as JSON on stdin."""
    root = os.path.realpath(str(repo.path))
    if payload is None:
        payload = json.dumps({"tool_input": {"file_path": os.path.join(root, rel)}, "cwd": root})
    return subprocess.run(["bash", str(HOOK)], input=payload, cwd=root,
                          env=repo.env, capture_output=True, text=True)


# ----------------------------------------------------------------------------- §4.1 CI workflow

def test_workflow_does_not_shallow_fetch_the_base_branch_t1():
    """§4.1/T1: the `--depth=1` fetch truncates main, so `git merge-base` returns empty and CI fails red."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "--depth=1" not in text, "gate.yml still shallow-fetches main (T1): merge-base returns empty"
    assert "fetch-depth: 0" in text, "the checkout must still bring the full history"
    assert "origin/main" in text, "the gate must still resolve the base against a full origin/main"


# ----------------------------------------------------------------------------- §4.2 Makefile

def test_makefile_does_not_take_the_profile_from_the_environment_t5():
    """§4.2/T5: GATE_PROFILE must not be env-overridable; the gate target passes --profile enforced."""
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "GATE_PROFILE ?=" not in text and "GATE_PROFILE?=" not in text, \
        "`GATE_PROFILE ?=` lets the environment downgrade the merge decision to advisory"
    assert "--profile enforced" in text, "the gate recipe must name the enforced profile literally"
    assert "gate-advisory" in text, "the advisory profile needs its own target, not an env var"


@pytest.mark.skipif(not HAVE_MAKE, reason="make is not installed")
def test_make_gate_reports_an_unloadable_verifier_as_exit_3_t4(tmp_path):
    """§4.2/T4: GNU make 3.81 ignores .SHELLFLAGS, so a failed `git archive` must be caught in-recipe."""
    r = Repo(tmp_path / "r")
    r.legal_feature()
    res = run_make(r, "VERIFIER_REF=does-not-exist")
    out = res.stdout + res.stderr
    # GNU make exits 2 for any failed recipe, so the recipe's own 3 shows up in make's report line,
    # never as make's exit status. The spec said "exit 3"; that was wrong about make, and the gate job
    # in CI calls the verifier directly, where the 3 is the process exit code.
    assert res.returncode != 0, out
    assert "Error 3" in out, f"the recipe must fail with the documented code 3: {out}"
    assert "cannot load the verifier" in out, out
    assert "Traceback" not in out and "can't open file" not in out, \
        "the missing verifier must be named, not surface as a Python error"


@pytest.mark.skipif(not HAVE_MAKE, reason="make is not installed")
def test_make_gate_control_loads_the_verifier_from_a_real_ref_t4(tmp_path):
    """Control for §4.2/T4: with a valid VERIFIER_REF the recipe must load the verifier and judge."""
    r = Repo(tmp_path / "r")
    r.legal_feature()
    res = run_make(r, "VERIFIER_REF=main")
    out = res.stdout + res.stderr
    assert "cannot load the verifier" not in out, out
    assert (r.path / ".gate/result.json").exists(), f"the gate did not run: {out}"


# ----------------------------------------------------------------------------- §4.3 policy.mk

def test_policy_mk_protects_gitattributes_and_requires_the_new_checks():
    """§4.3: .gitattributes joins the protected set (CR-01) and the four new checks become required."""
    text = POLICY_MK.read_text(encoding="utf-8")
    protected = next(ln for ln in text.splitlines() if ln.startswith("PROTECTED_PATHS"))
    required = next(ln for ln in text.splitlines() if ln.startswith("REQUIRED_CHECKS_ENFORCED"))
    assert ".gitattributes" in protected, "a candidate could ship export-ignore and delete the gate's evidence"
    for cid in ("export_integrity", "harness_integrity", "test_inventory", "red_before_green"):
        assert cid in required, f"{cid} must be required in the enforced profile"


# ----------------------------------------------------------------------------- §4.4 the H1 hook

def test_hook_allows_a_renew_branch_to_edit_src_rt07(tmp_path):
    """§4.4/RT-07: a SUNSET tag lives on a code line, so renew/ must be able to edit src/ (v0.3 exits 2)."""
    r = Repo(tmp_path / "r")
    r.branch("renew/shim")
    res = run_hook(r, "src/shim.py")
    assert res.returncode == 0, f"the only legal renew/ workflow is still blocked: {res.stderr}"


def test_hook_still_refuses_a_chore_branch_editing_src(tmp_path):
    """Control for §4.4: widening renew/ must not open src/ to chore/ branches."""
    r = Repo(tmp_path / "r")
    r.branch("chore/tidy")
    res = run_hook(r, "src/core.py")
    assert res.returncode == 2, res.stdout + res.stderr
    assert "chore" in res.stderr and "src/core.py" in res.stderr


def test_hook_refuses_editing_an_existing_verifier_test_p0_3(tmp_path):
    """§4.4/§3.8/P0-3: scripts/tests/** is frozen too — editing a committed one off test/ is H1."""
    r = Repo(tmp_path / "r", with_selftests=True)
    r.branch("feature/x")
    res = run_hook(r, "scripts/tests/test_gate_checks.py")
    assert res.returncode == 2, "a committed verifier test may be edited freely (P0-3)"
    assert "H1" in res.stderr


def test_hook_control_allows_a_new_verifier_test_file(tmp_path):
    """Control for P0-3: the frozen set covers existing files; adding a new test must stay allowed."""
    r = Repo(tmp_path / "r", with_selftests=True)
    r.branch("feature/x")
    res = run_hook(r, "scripts/tests/test_brand_new_v04.py")
    assert res.returncode == 0, res.stdout + res.stderr


def test_hook_refuses_invalid_json_on_stdin_p21(tmp_path):
    """P21 (v0.3, must survive): an unreadable tool call is refused, never waved through."""
    r = Repo(tmp_path / "r")
    res = run_hook(r, "src/core.py", payload="{not json")
    assert res.returncode == 2, res.stdout + res.stderr
    assert "not valid JSON" in res.stderr


# ----------------------------------------------------------------------------- v0.3 behaviour that must survive

def test_p03_invalid_base_is_exit_3_with_no_result(tmp_path):
    """§0 (v0.3 P03): an invalid base is exit 3 and writes no result — never an empty success."""
    r = Repo(tmp_path / "r")
    r.legal_feature()
    rc, res, out = r.gate("feature/greeting", base="DOES_NOT_EXIST")
    assert rc == 3 and res is None, out
    assert "DOES_NOT_EXIST" in out


def test_p04_uncommitted_allowlist_edit_does_not_change_the_verdict(tmp_path):
    """§0 (v0.3 P04): policy is read from --policy-ref, so a working-tree allowlist edit buys nothing."""
    r = Repo(tmp_path / "r")
    r.branch("test/mock")
    r.write("tests/test_mock.py", "from unittest.mock import patch\n\n\ndef test_m():\n"
                                  "    with patch('src.core.value') as v:\n        v.return_value = 1\n")
    r.record("test", "mock")
    r.commit("test: in-repo mock")
    _, before, _ = r.gate("test/mock")
    assert outcome(before, "mocks") == "FAIL"
    r.append("tests/MOCK_ALLOWLIST", "src.\n")  # uncommitted
    _, after, out = r.gate("test/mock")
    assert outcome(after, "mocks") == "FAIL", out
    assert after["policy_digest"] == before["policy_digest"]


def test_p16_uncommitted_record_is_not_evidence(tmp_path):
    """§0 (v0.3 P16): the record must be committed; a working-tree file is not evidence."""
    r = Repo(tmp_path / "r")
    r.branch("feature/norecord")
    r.write("tests/test_n.py", "from src.n import n\n\n\ndef test_n():\n    assert n() == 1\n")
    r.commit("test: n")
    r.write("src/n.py", "def n():\n    return 1\n")
    r.commit("feat: n")
    _, before, _ = r.gate("feature/norecord")
    assert outcome(before, "records") == "FAIL"
    r.record("feature", "norecord", WHY="a instead of b, because c.", TESTS="pytest -q")  # uncommitted
    rc, after, out = r.gate("feature/norecord")
    assert outcome(after, "records") == "FAIL", out
    assert after["merge_eligible"] is False and rc == 1


def test_p25_renew_branch_editing_policy_mk_fails_protected_files(tmp_path):
    """§0 (v0.3 P25): policy parameters are policy/ only — a renew/ branch may not loosen them."""
    r = Repo(tmp_path / "r")
    r.branch("renew/params")
    r.write("policy.mk", r.read("policy.mk").replace("MUTATION_MIN         ?= 0.70",
                                                     "MUTATION_MIN         ?= 0 # SUNSET"))
    r.record("renew", "params")
    r.commit("renew: loosen")
    rc, res, out = r.gate("renew/params")
    assert outcome(res, "protected_files") == "FAIL", out
    assert "policy.mk" in detail(res, "protected_files")
    assert res["merge_eligible"] is False and rc == 1
