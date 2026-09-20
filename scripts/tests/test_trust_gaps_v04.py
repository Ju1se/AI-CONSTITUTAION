"""v0.4 trust-cluster gap tests: provenance edge cases, the self-test's scope, and the advisory profile.

Written from `v04-spec.md` §2 (verifier provenance and the four merge_eligible conditions), §3.7
(`verifier_selftest`), §3.8 (the frozen set after the added-test rule moved out) and §3.11 (profiles).
`test_trust_core_v04.py` already pins the policy_ref/subject provenance pair, the stub-verifier refusal and
the GATE_PROFILE environment rule; this file covers what that suite leaves open. Each test names the spec
line it pins and the audit finding it traces to, and each refusal is paired with a control.
"""
from __future__ import annotations

from _harness import RUFF, Repo, detail, eligible_or_blocked_only_by, outcome

# Everything that is not masking_ruff must PASS on a legitimate change; ruff may simply be absent.
RUFF_REASON = "masking_ruff NOT_RUN"


def entry(result: dict, check_id: str) -> dict:
    """The raw JSON object for one check, so a test can assert on `required` and not only on `outcome`."""
    for c in result["checks"]:
        if c["id"] == check_id:
            return c
    raise AssertionError(f"the gate did not report a check named {check_id!r}")


def failing_required(result: dict, *ignore: str) -> list[str]:
    """Required checks that are not PASS, ignoring the named ones (ruff on a machine without ruff)."""
    return [c["id"] for c in result["checks"]
            if c["required"] and c["outcome"] != "PASS" and c["id"] not in ignore]


def policy_record(r: Repo, slug: str, msg: str) -> None:
    r.record("policy", slug, WHY="the verifier instead of the docs, because the gate is the contract.",
             TESTS="python -m pytest -q scripts/tests")
    r.commit(msg)


# ----------------------------------------------------------------------------- §2 provenance: "other"

def test_locally_edited_verifier_is_other_and_never_authorizes_s2(tmp_path):
    """§2: a verifier matching neither the policy ref nor the subject is provenance 'other'.

    Pins spec §2 ("`verifier_provenance`: ... else `other`") together with merge_eligible condition 4
    ("`verifier_provenance == "policy_ref"`"). Traces to audit T3 / CMP-07: the gate must not authorize a
    merge it judged with a copy of itself that nobody committed. This is the everyday case — an engineer
    running their working-tree verifier — and `test_trust_core_v04.py` only covers the `subject` copy.
    """
    r = Repo(tmp_path / "r")
    r.legal_feature()
    edited = tmp_path / "locally_edited_gate_checks.py"
    edited.write_text(r.verifier_from("main").read_text(encoding="utf-8")
                      + "\n# local edit: inert, but it is nobody's committed verifier.\n",
                      encoding="utf-8")

    rc, res, out = r.gate("feature/greeting", verifier=edited)
    assert res is not None, out
    assert res["verifier_provenance"] == "other", res["verifier_provenance"]
    # The policy ref does have a verifier, so the field is populated and simply differs from what ran.
    assert isinstance(res["verifier_sha_at_policy_ref"], str)
    assert res["verifier_sha"] != res["verifier_sha_at_policy_ref"]
    # Every check still PASSes: the refusal is provenance alone, not a check failure.
    assert failing_required(res, "masking_ruff") == [], res["checks"]
    assert res["merge_eligible"] is False
    reasons = res.get("ineligible_reasons") or []
    assert any("verifier" in x for x in reasons), reasons
    assert all("verifier" in x or "masking_ruff" in x for x in reasons), reasons
    assert rc != 0


def test_policy_ref_verifier_authorizes_the_same_change_control(tmp_path):
    """CONTROL for §2: the identical change judged by the policy ref's own verifier is eligible.

    Also the task's control case: provenance 'policy_ref', `verifier_sha_at_policy_ref` equal to
    `verifier_sha`, merge_eligible true. Without this, the test above could be passing because
    `legal_feature()` is broken rather than because the verifier copy is unrecognised (audit T3).
    """
    r = Repo(tmp_path / "r")
    r.legal_feature()
    rc, res, out = r.gate("feature/greeting")
    assert res is not None, out
    assert res["verifier_provenance"] == "policy_ref", res["verifier_provenance"]
    assert res["verifier_sha_at_policy_ref"] == res["verifier_sha"]
    if RUFF:
        assert res["merge_eligible"] is True, res.get("ineligible_reasons")
        assert rc == 0, out
    else:
        assert eligible_or_blocked_only_by(res, RUFF_REASON), res.get("ineligible_reasons")


# ----------------------------------------------------------------------------- §2 provenance: null sha

def test_verifier_sha_at_policy_ref_is_null_when_the_ref_has_no_verifier_s2(tmp_path):
    """§2: `verifier_sha_at_policy_ref` is null when the policy ref carries no scripts/gate_checks.py.

    Pins spec §2 ("sha256 of `<policy_ref>:scripts/gate_checks.py`, or null when absent") and, with it,
    that an absent verifier at the ref can never satisfy merge_eligible condition 4. Traces to audit T3:
    a half-implementation that hashes the empty string, or that crashes on the missing blob, would both
    look like a policy_ref match here.
    """
    r = Repo(tmp_path / "r")
    r.rm("scripts/gate_checks.py")
    r.commit("chore: a base commit without the verifier")
    r.branch("policy/introduce-verifier")
    r.copy_from_kit("scripts/gate_checks.py")
    policy_record(r, "introduce-verifier", "policy: introduce the verifier")

    rc, res, out = r.gate("policy/introduce-verifier", verifier=r.verifier_from("HEAD"))
    assert res is not None, out
    assert rc != 0, out
    assert res["verifier_sha_at_policy_ref"] is None, res["verifier_sha_at_policy_ref"]
    assert res["verifier_provenance"] != "policy_ref", res["verifier_provenance"]
    assert res["merge_eligible"] is False
    assert any("verifier" in x for x in (res.get("ineligible_reasons") or [])), \
        res.get("ineligible_reasons")


# ----------------------------------------------------------------------------- §3.7 verifier_selftest

def test_added_failing_selftest_fails_verifier_selftest_p03(tmp_path):
    """§3.7 bullet 3: an ADDED scripts/tests file that fails must FAIL verifier_selftest.

    Pins "Then run any additional test files the candidate adds under `scripts/tests`". Traces to audit
    P0-3 / CMP-17: restoring the trusted corpus is only half the control — a candidate that also ships a
    new, failing counterexample must not be waved through because the trusted files happened to pass.
    """
    r = Repo(tmp_path / "r", with_selftests=True)
    r.branch("policy/extra-case")
    r.write("scripts/tests/test_added_case.py",
            "def test_candidate_added_case():\n"
            "    assert False, 'the case the candidate itself added does not hold'\n")
    policy_record(r, "extra-case", "policy: add a verifier case")

    rc, res, out = r.gate("policy/extra-case")
    assert res is not None, out
    assert outcome(res, "verifier_selftest") == "FAIL", detail(res, "verifier_selftest")
    assert "test_added_case" in detail(res, "verifier_selftest"), detail(res, "verifier_selftest")
    assert res["merge_eligible"] is False
    assert rc != 0


def test_added_passing_selftest_is_accepted_control(tmp_path):
    """CONTROL for §3.7: the same shape of change with a PASSING added file must PASS verifier_selftest.

    Without it the test above would also pass against an implementation that fails every policy change
    that touches scripts/tests at all (audit P0-3's over-correction).
    """
    r = Repo(tmp_path / "r", with_selftests=True)
    r.branch("policy/extra-case")
    r.write("scripts/tests/test_added_case.py",
            "def test_candidate_added_case():\n    assert True\n")
    policy_record(r, "extra-case", "policy: add a verifier case")

    _rc, res, out = r.gate("policy/extra-case")
    assert res is not None, out
    assert outcome(res, "verifier_selftest") == "PASS", detail(res, "verifier_selftest")
    assert outcome(res, "h1") == "PASS", detail(res, "h1")
    assert eligible_or_blocked_only_by(res, RUFF_REASON), res.get("ineligible_reasons")


def test_verifier_selftest_is_not_run_and_not_required_off_policy_s37(tmp_path):
    """§3.7: "Runs for `policy` changes only (NOT_RUN and not required otherwise)".

    Pins both halves on a feature change: the outcome is NOT_RUN and the JSON's `required` flag is false.
    Traces to audit EV-02 — a required check left NOT_RUN is exit 3 and would block every ordinary change,
    so a half-implementation that skips the run but keeps the flag is indistinguishable by outcome alone.
    """
    r = Repo(tmp_path / "r", with_selftests=True)
    r.legal_feature()
    _rc, res, out = r.gate("feature/greeting")
    assert res is not None, out
    st = entry(res, "verifier_selftest")
    assert st["outcome"] == "NOT_RUN", st
    assert st["required"] is False, st
    assert res["change_type"] == "feature"
    # And it must not be the thing blocking the merge.
    assert "verifier_selftest" not in " ".join(res.get("ineligible_reasons") or [])
    assert eligible_or_blocked_only_by(res, RUFF_REASON), res.get("ineligible_reasons")


# ----------------------------------------------------------------------------- §3.8 h1 loses the add rule

def test_fix_without_a_new_test_is_h1_pass_and_test_inventory_fail_cr04(tmp_path):
    """§3.8: "the added-test rule ... is removed from h1" — it lives in test_inventory (§1.3) alone.

    A `fix` that adds no test file must be h1 PASS (it modified no committed test and never mixed src/
    with tests/) while test_inventory FAILs ("a feature/fix adds at least one collected test"). Traces to
    audit CR-04: v0.3 enforced the rule by filename in h1, which both mis-blamed h1 and was satisfied by
    an empty file; the two rules must not silently merge back together.
    """
    r = Repo(tmp_path / "r")
    r.branch("fix/off-by-one")
    r.append("src/core.py", "\n\ndef other():\n    return 2\n")
    r.record("fix", "off-by-one", WHY="an early return instead of a flag, because the branch was unreachable.",
             TESTS="python -m pytest -q tests")
    r.commit("fix: off by one")

    rc, res, out = r.gate("fix/off-by-one")
    assert res is not None, out
    assert outcome(res, "h1") == "PASS", detail(res, "h1")
    assert outcome(res, "test_inventory") == "FAIL", detail(res, "test_inventory")
    # The one required check that refuses is the inventory, not h1.
    assert failing_required(res, "masking_ruff", "red_before_green") == ["test_inventory"], res["checks"]
    assert res["merge_eligible"] is False
    assert any("test_inventory" in x for x in (res.get("ineligible_reasons") or [])), \
        res.get("ineligible_reasons")
    assert rc != 0


def test_fix_with_a_new_collected_test_passes_both_control(tmp_path):
    """CONTROL for §3.8/§1.3: the same fix with one new collected test must PASS h1 and test_inventory."""
    r = Repo(tmp_path / "r")
    r.branch("fix/off-by-one")
    r.write("tests/test_other.py", "from src.core import other\n\n\ndef test_other():\n    assert other() == 2\n")
    r.commit("test: other")
    r.append("src/core.py", "\n\ndef other():\n    return 2\n")
    r.record("fix", "off-by-one", WHY="an early return instead of a flag, because the branch was unreachable.",
             TESTS="python -m pytest -q tests")
    r.commit("fix: off by one")

    _rc, res, out = r.gate("fix/off-by-one")
    assert res is not None, out
    assert outcome(res, "h1") == "PASS", detail(res, "h1")
    assert outcome(res, "test_inventory") == "PASS", detail(res, "test_inventory")
    assert eligible_or_blocked_only_by(res, RUFF_REASON), res.get("ineligible_reasons")


# ----------------------------------------------------------------------------- §3.11 advisory profile

def test_advisory_profile_reports_everything_and_still_refuses_ev02(tmp_path):
    """§3.11+§2: advisory never authorizes, even on a change with nothing wrong with it.

    Pins "The advisory profile never sets `merge_eligible` true" and merge_eligible condition 1 ("the
    profile is `enforced`"), on a fully legitimate change, while §0's per-check reporting survives: the
    checks list is non-empty and type/protected_files/unit_tests are PASS. Traces to audit EV-02 / T5 —
    the advisory run must stay useful as a report, so a half-implementation that refuses by short-circuiting
    before the checks run would satisfy merge_eligible False and still be wrong.
    """
    r = Repo(tmp_path / "r")
    r.legal_feature()
    rc, res, out = r.gate("feature/greeting", profile="advisory")
    assert res is not None, out
    assert res["profile"] == "advisory"
    assert res["checks"], res
    for cid in ("type", "protected_files", "unit_tests"):
        assert outcome(res, cid) == "PASS", detail(res, cid)
    assert failing_required(res) == [], res["checks"]
    assert res["merge_eligible"] is False
    reasons = res.get("ineligible_reasons") or []
    assert any("advisory" in x.lower() for x in reasons), reasons
    assert rc != 0
