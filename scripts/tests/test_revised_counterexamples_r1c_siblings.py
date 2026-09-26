"""A revised counterexample is judged with every trusted sibling test around it (R1(c) follow-up, amended S1).

Amended S1: after the trusted-corpus run passes, if any scripts/tests/ path present at the policy ref
differs at the subject, EVERY trusted test_*.py (every such path present at the policy ref) runs with every
revised path at its subject content and every other path as in the trusted run (deleted paths stay
restored, per S2). Any nonzero pytest exit other than a timeout is verifier_selftest FAIL naming the
revised paths; a timeout is ERROR.

The reason for the amendment: a test_*.py can serve a sibling test as a helper (the sibling imports a name
from it). Running only the revised file lets a revision that breaks a sibling pass this verdict and fail
the next unrelated one. The fixtures below put a small library-like corpus file (LIB_PATH) and a sibling
that imports from it (USER_PATH) on `main`, then revise LIB_PATH on a `policy/...` branch whose record
carries an ACCEPTANCE line, so the frozen-set rule does not stop the change before verifier_selftest
judges it. Two pins keep the earlier review fixes holding under the amendment: a revised file that fails
to import is FAIL (not ERROR), and an emptied revision nothing depends on is not refused.

Fixture corpora are minimal: each throwaway repository is built without the kit's own self-tests and
carries only scripts/tests/_harness.py plus LIB_PATH, USER_PATH and SOLO_PATH. The kit's test_gate_checks.py
runs 27 nested gates, and a policy fixture's gate runs its trusted corpus once more for each revision, so
copying it into every fixture cost minutes per test and pushed these files past the gate's
UNIT_TESTS_TIMEOUT when the gate ran them as added counterexamples. No scenario here needs it: every
refusal and control is decided by the three small files alone.

Assertions are on outcomes, file names and paths, never on the wording of a detail sentence.
"""
from __future__ import annotations

from _harness import Repo, detail, eligible_or_blocked_only_by, outcome

RUFF_REASON = "masking_ruff NOT_RUN"
APPROVAL = ("correction; approver:owner-designated-reviewer date:2026-09-25 decision:D-32 | "
            "reason:the counterexample is restated | spec v1->v2 | old:as on main new:as revised | "
            "transition:this commit | retained:the v1 case stays in history")

LIB_PATH = "scripts/tests/test_r1c_sib_lib.py"
LIB_DOC = '"""A corpus file that also serves its sibling as a helper: it defines SIBLING_EXPECTED."""\n'
LIB = (
    LIB_DOC
    + "\nSIBLING_EXPECTED = 'PASS'\n\n\n"
    "def test_lib_value():\n"
    "    assert SIBLING_EXPECTED == 'PASS'\n"
)

USER_PATH = "scripts/tests/test_r1c_sib_user.py"
USER = (
    '"""A corpus file that imports a name from its sibling test file and asserts on it."""\n'
    "from test_r1c_sib_lib import SIBLING_EXPECTED\n\n\n"
    "def test_sibling_value_is_pass():\n"
    "    assert SIBLING_EXPECTED == 'PASS'\n"
)

SOLO_PATH = "scripts/tests/test_r1c_solo.py"
SOLO = '"""A corpus file nothing imports."""\n\n\ndef test_solo():\n    assert 1 + 1 == 2\n'


HARNESS_PATH = "scripts/tests/_harness.py"


def repo_with_siblings(tmp_path) -> Repo:
    """A minimal kit: _harness.py, LIB_PATH, USER_PATH and SOLO_PATH committed on main."""
    r = Repo(tmp_path / "r")
    r.copy_from_kit(HARNESS_PATH)
    r.write(LIB_PATH, LIB)
    r.write(USER_PATH, USER)
    r.write(SOLO_PATH, SOLO)
    r.commit("policy: the harness and three counterexamples on main")
    return r


def replace_once(r: Repo, rel: str, old: str, new: str) -> None:
    text = r.read(rel)
    assert text.count(old) == 1, f"{rel} no longer contains {old!r} exactly once; the fixture is stale"
    r.write(rel, text.replace(old, new))


def policy_change_with_acceptance(r: Repo, slug: str, msg: str) -> None:
    r.record("policy", slug, WHY="the verifier instead of the docs, because the gate is the contract.",
             ACCEPTANCE=APPROVAL, TESTS="python -m pytest -q scripts/tests")
    r.commit(msg)


def test_a_revision_that_removes_a_name_a_sibling_imports_is_refused_s1(tmp_path):
    """Amended S1: LIB_PATH is revised so SIBLING_EXPECTED is gone; USER_PATH (unchanged) cannot import.

    The revised file still holds on its own (its test follows the rename), so a verifier that runs only
    the revised file passes it. Under the amended spec every trusted test_*.py runs with the revision in
    place, USER_PATH fails to collect, and the refusal names the revised file.
    """
    r = repo_with_siblings(tmp_path)
    r.branch("policy/rename-sibling-name")
    r.write(LIB_PATH, LIB.replace("SIBLING_EXPECTED", "LIB_EXPECTED"))
    policy_change_with_acceptance(r, "rename-sibling-name", "policy: rename a name in a counterexample")
    rc, res, out = r.gate("policy/rename-sibling-name")
    assert res is not None, out
    assert outcome(res, "verifier_selftest") == "FAIL", detail(res, "verifier_selftest")
    assert "test_r1c_sib_lib.py" in detail(res, "verifier_selftest"), detail(res, "verifier_selftest")
    assert res["merge_eligible"] is False
    assert rc != 0


def test_an_emptied_revision_a_sibling_imports_from_is_refused_s1(tmp_path):
    """Amended S1: LIB_PATH is emptied to its docstring, so both the name and its own tests are gone.

    Run alone, the emptied revision collects nothing and holds vacuously (the retired exit-5 carve-out).
    Run with every trusted sibling, USER_PATH fails to import it, which is FAIL naming the revised file.
    """
    r = repo_with_siblings(tmp_path)
    r.branch("policy/empty-sibling")
    r.write(LIB_PATH, LIB_DOC)
    policy_change_with_acceptance(r, "empty-sibling", "policy: empty a counterexample")
    rc, res, out = r.gate("policy/empty-sibling")
    assert res is not None, out
    assert outcome(res, "verifier_selftest") == "FAIL", detail(res, "verifier_selftest")
    assert "test_r1c_sib_lib.py" in detail(res, "verifier_selftest"), detail(res, "verifier_selftest")
    assert res["merge_eligible"] is False
    assert rc != 0


def test_a_revision_that_keeps_the_sibling_name_passes_control_s1(tmp_path):
    """Control: a docstring-only revision of LIB_PATH keeps the import working and verifier_selftest PASS.

    It also shows the sibling import itself resolves in the verifier's runs, so the two refusals above
    are refusals of the revision and not of the fixture; and a verifier that refused every revision of
    an imported file would fail here.
    """
    r = repo_with_siblings(tmp_path)
    r.branch("policy/reword-sibling")
    replace_once(r, LIB_PATH, LIB_DOC,
                 '"""A corpus file its sibling imports from: SIBLING_EXPECTED is defined here."""\n')
    policy_change_with_acceptance(r, "reword-sibling", "policy: reword a counterexample")
    _rc, res, out = r.gate("policy/reword-sibling")
    assert res is not None, out
    assert outcome(res, "verifier_selftest") == "PASS", detail(res, "verifier_selftest")
    assert eligible_or_blocked_only_by(res, RUFF_REASON), res.get("ineligible_reasons")


def test_a_revision_that_fails_to_import_is_fail_not_error_pin(tmp_path):
    """Pin (60008f6, kept under the amendment): a revised corpus file that cannot import is FAIL, not ERROR.

    SOLO_PATH is revised to import a name _harness does not define; nothing else imports SOLO_PATH.
    Green on the current HEAD by design: this pins the earlier review fix, it does not drive a change.
    """
    r = repo_with_siblings(tmp_path)
    r.branch("policy/break-solo-import")
    r.write(SOLO_PATH, '"""A corpus file nothing imports."""\nfrom _harness import no_such_name_r1c\n\n\n'
                       "def test_solo():\n    assert no_such_name_r1c is not None\n")
    policy_change_with_acceptance(r, "break-solo-import", "policy: revise a counterexample")
    rc, res, out = r.gate("policy/break-solo-import")
    assert res is not None, out
    assert outcome(res, "verifier_selftest") == "FAIL", detail(res, "verifier_selftest")
    assert "test_r1c_solo.py" in detail(res, "verifier_selftest"), detail(res, "verifier_selftest")
    assert res["merge_eligible"] is False
    assert rc != 0


def test_an_emptied_revision_nothing_imports_is_not_refused_pin(tmp_path):
    """Pin (60008f6, kept under the amendment): emptying a corpus file no sibling imports is not refused.

    SOLO_PATH is emptied to its docstring. The other trusted tests still collect, so the run exits 0
    without any carve-out; verifier_selftest is PASS and nothing but a missing ruff may block the merge.
    Green on the current HEAD by design.
    """
    r = repo_with_siblings(tmp_path)
    r.branch("policy/empty-solo")
    r.write(SOLO_PATH, '"""A corpus file nothing imports."""\n')
    policy_change_with_acceptance(r, "empty-solo", "policy: empty a counterexample")
    _rc, res, out = r.gate("policy/empty-solo")
    assert res is not None, out
    assert outcome(res, "verifier_selftest") == "PASS", detail(res, "verifier_selftest")
    assert eligible_or_blocked_only_by(res, RUFF_REASON), res.get("ineligible_reasons")
