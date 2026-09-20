"""v0.4 regression tests for the trust core: verifier provenance, the self-test, the frozen set, profiles.

Written from `v04-spec.md` before the implementation exists (§2, §3.7, §3.8, §3.11). These tests are
expected to FAIL against the v0.3 verifier; each one names the finding id it pins down.
"""
from __future__ import annotations

import json

from _harness import RUFF, Repo, detail, eligible_or_blocked_only_by, outcome, required_ids

# A five-line verifier that authorizes everything — the P0-3 / EV-01 substitution, verbatim in spirit.
STUB_VERIFIER = (
    "import json\n"
    "import sys\n"
    "print('all checks PASS')\n"
    "json.dump({'merge_eligible': True, 'checks': []}, open(sys.argv[-1], 'w'))\n"
    "sys.exit(0)\n"
)

GREETING_TEST = "from src.greeting import greet\n\n\ndef test_greet():\n    assert greet('a') == 'hello, a'\n"
GREETING_SRC = "def greet(name):\n    return f'hello, {name}'\n"
ROOT_CONFTEST = "import pytest\n\n\n@pytest.fixture\ndef sample():\n    return 1\n"


def policy_change(r: Repo, slug: str, msg: str) -> None:
    """Commit the record for a policy/ change already staged in the work tree."""
    r.record("policy", slug, WHY="the verifier instead of the docs, because the gate is the contract.",
             TESTS="python -m pytest -q scripts/tests")
    r.commit(msg)


def repo_with_root_conftest(tmp_path) -> Repo:
    """A repository whose `conftest.py` (repository root, not tests/) is already committed on main."""
    r = Repo(tmp_path / "r")
    r.write("conftest.py", ROOT_CONFTEST)
    r.commit("chore: committed root conftest")
    return r


# ----------------------------------------------------------------- §3.7 / §3.8 the judge and its case law

def test_stub_verifier_with_deleted_selftests_is_refused_ev01(tmp_path):
    """§3.7+§3.8: a policy/ change that swaps in a stub verifier and deletes scripts/tests must be refused."""
    r = Repo(tmp_path / "r", with_selftests=True)
    r.branch("policy/verifier-rewrite")
    r.write("scripts/gate_checks.py", STUB_VERIFIER)
    r.rm("scripts/tests/test_gate_checks.py")
    r.write("scripts/tests/test_trivial.py", "def test_ok():\n    assert True\n")
    policy_change(r, "verifier-rewrite", "policy: simplify the verifier")
    rc, res, out = r.gate("policy/verifier-rewrite")
    assert res is not None, out
    # §3.7: the trusted corpus is restored over the candidate's and judges the stub.
    assert outcome(res, "verifier_selftest") == "FAIL", detail(res, "verifier_selftest")
    # §3.8: scripts/tests/** is frozen; deleting a committed test is a FAIL on policy/ too.
    assert outcome(res, "h1") == "FAIL", detail(res, "h1")
    assert "scripts/tests/test_gate_checks.py" in detail(res, "h1")
    assert res["merge_eligible"] is False
    assert rc != 0


def test_broken_candidate_verifier_fails_selftest_cmp17(tmp_path):
    """§3.7: a candidate verifier that does not compile is a py_compile FAIL, not a pile of test failures."""
    r = Repo(tmp_path / "r", with_selftests=True)
    r.branch("policy/syntax")
    r.append("scripts/gate_checks.py", "\ndef (broken syntax\n")
    policy_change(r, "syntax", "policy: edit the verifier")
    rc, res, out = r.gate("policy/syntax")
    assert res is not None, out
    assert outcome(res, "verifier_selftest") == "FAIL", detail(res, "verifier_selftest")
    assert "compile" in detail(res, "verifier_selftest").lower(), detail(res, "verifier_selftest")
    assert res["merge_eligible"] is False
    assert rc != 0


def test_legitimate_policy_change_keeps_selftest_passing_control(tmp_path):
    """CONTROL for §3.7/§3.8: widening the allowlist with scripts/tests intact must PASS, not be refused."""
    r = Repo(tmp_path / "r", with_selftests=True)
    r.branch("policy/allowlist")
    r.append("tests/MOCK_ALLOWLIST", "boto3.\n")
    policy_change(r, "allowlist", "policy: allow boto3 mocks")
    rc, res, out = r.gate("policy/allowlist")
    assert res is not None, out
    assert outcome(res, "verifier_selftest") == "PASS", detail(res, "verifier_selftest")
    assert outcome(res, "h1") == "PASS", detail(res, "h1")
    if RUFF:
        assert outcome(res, "masking_ruff") == "PASS", detail(res, "masking_ruff")
    assert eligible_or_blocked_only_by(res, "masking_ruff NOT_RUN"), res.get("ineligible_reasons")


# ----------------------------------------------------------------- §2 verifier provenance

def test_policy_ref_verifier_is_reported_as_provenance_s2(tmp_path):
    """§2: the normal run (judged by the policy ref's verifier) reports provenance policy_ref and may be eligible."""
    r = Repo(tmp_path / "r")
    r.legal_feature()
    rc, res, out = r.gate("feature/greeting")
    assert res is not None, out
    assert res.get("verifier_provenance") == "policy_ref", res.get("verifier_provenance")
    sha = res.get("verifier_sha_at_policy_ref")
    assert isinstance(sha, str) and len(sha) == 64, sha
    assert all(ch in "0123456789abcdef" for ch in sha), sha
    assert eligible_or_blocked_only_by(res, "masking_ruff NOT_RUN"), res.get("ineligible_reasons")


def test_subject_own_verifier_never_authorizes_s2(tmp_path):
    """§2: judged by the SUBJECT's own verifier, merge_eligible is false even when every check PASSes."""
    r = Repo(tmp_path / "r", with_selftests=True)
    r.branch("policy/annotate")
    r.append("scripts/gate_checks.py", "\n# provenance fixture: an inert trailing comment.\n")
    policy_change(r, "annotate", "policy: annotate the verifier")
    rc, res, out = r.gate("policy/annotate", verifier=r.verifier_from("HEAD"))
    assert res is not None, out
    assert res.get("verifier_provenance") == "subject", res.get("verifier_provenance")
    assert outcome(res, "h1") == "PASS", detail(res, "h1")
    assert res["merge_eligible"] is False
    reasons = res.get("ineligible_reasons") or []
    # The provenance alone refuses: nothing else in this scenario blocks (ruff may be absent).
    assert any("verifier" in x for x in reasons), reasons
    assert all("verifier" in x or "masking_ruff" in x for x in reasons), reasons


# ----------------------------------------------------------------- §3.11 profiles

def violating_feature(r: Repo) -> None:
    """One change that violates h1 (edits a committed test), mocks (in-repo target) and sunset (untagged TODO)."""
    r.branch("feature/broken")
    r.write("tests/test_new.py",
            "from unittest.mock import patch\n\n\ndef test_new():\n"
            "    with patch('src.core.value') as p:\n        p.return_value = 2\n"
            "        assert p.return_value == 2\n")
    r.commit("test: new")
    r.append("tests/test_core.py", "\n\ndef test_extra():\n    assert True\n")
    r.append("src/core.py", "\n\n# TODO: tidy this up later\n")
    r.record("feature", "broken", WHY="a stub instead of the call, because speed.", TESTS="python -m pytest -q tests")
    r.commit("feat: broken")


def test_advisory_profile_never_authorizes_ev02(tmp_path):
    """§3.11+§2: advisory reports every outcome but never sets merge_eligible; it authorizes nothing."""
    r = Repo(tmp_path / "r")
    violating_feature(r)
    rc, res, out = r.gate("feature/broken", profile="advisory")
    assert res is not None, out
    # The individual outcomes are still reported (fixture sanity: all three violations are seen).
    assert outcome(res, "h1") == "FAIL", detail(res, "h1")
    assert outcome(res, "mocks") == "FAIL", detail(res, "mocks")
    assert outcome(res, "sunset") == "FAIL", detail(res, "sunset")
    assert res["profile"] == "advisory"
    assert res["merge_eligible"] is False
    assert any("advisory" in reason.lower() for reason in (res.get("ineligible_reasons") or [])), \
        res.get("ineligible_reasons")


def test_gate_profile_environment_variable_is_ignored_cmp06(tmp_path):
    """§3.11: the profile comes only from the command line; GATE_PROFILE in the environment is ignored."""
    r = Repo(tmp_path / "r")
    r.legal_feature()
    rc, res, out = r.gate("feature/greeting", env={"GATE_PROFILE": "advisory"})
    assert res is not None, out
    assert res["profile"] == "enforced"  # the explicit flag already wins; this must stay true
    target = r.path / ".gate" / "env-profile.json"
    proc = r.run("gate", "--subject", "HEAD", "--base", "main", "--policy-ref", "main",
                 "--branch", "feature/greeting", "--out", str(target), env={"GATE_PROFILE": "advisory"})
    assert target.exists(), proc.stdout + proc.stderr
    env_res = json.loads(target.read_text(encoding="utf-8"))
    assert env_res["profile"] == "enforced", env_res["profile"]
    assert required_ids(env_res) >= {"h1", "mocks", "sunset"}, required_ids(env_res)


# ----------------------------------------------------------------- §3.8 conftest.py is frozen

def test_modifying_a_committed_root_conftest_fails_h1_p03(tmp_path):
    """§3.8: the frozen set includes any conftest.py, so a feature/ change may not edit a committed one."""
    r = repo_with_root_conftest(tmp_path)
    r.branch("feature/greeting")
    r.write("tests/test_greeting.py", GREETING_TEST)
    r.commit("test: greet")
    r.write("src/greeting.py", GREETING_SRC)
    r.append("conftest.py", "\n\n@pytest.fixture\ndef other():\n    return 2\n")
    r.record("feature", "greeting", WHY="an f-string instead of concatenation, because readability.",
             SEARCHED='rg -n "greet" src/ → 0 hits | NONE-FITS: n/a', TESTS="python -m pytest -q tests")
    r.commit("feat: greet")
    rc, res, out = r.gate("feature/greeting")
    assert res is not None, out
    assert outcome(res, "h1") == "FAIL", detail(res, "h1")
    assert "conftest.py" in detail(res, "h1")
    assert res["merge_eligible"] is False
    assert rc != 0


def test_untouched_root_conftest_does_not_block_a_feature_control(tmp_path):
    """CONTROL for §3.8: a conftest.py merely existing must not refuse an ordinary test-first feature."""
    r = repo_with_root_conftest(tmp_path)
    r.legal_feature()
    rc, res, out = r.gate("feature/greeting")
    assert res is not None, out
    assert outcome(res, "h1") == "PASS", detail(res, "h1")
    assert eligible_or_blocked_only_by(res, "masking_ruff NOT_RUN"), res.get("ineligible_reasons")
