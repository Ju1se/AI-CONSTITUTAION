"""Revisions and deletions are attributed to the change under test only (R1(c) audit fixes F1, F2).

F1 attribution: verifier_selftest derives the revised and deleted scripts/tests/ paths from the change's
own diff (`git diff --no-renames --name-status <base> <subject> -- scripts/tests/`), not from comparing
the policy ref with the subject. A revised path is present at the policy ref, modified (or added, when the
policy ref also has it) by that diff, and differs at the subject from the policy ref; a deleted path is
present at the policy ref and deleted by that diff. A path that differs between the policy ref and the
subject only because main moved on after the branch forked is neither, and is not named as such.

F2 pin: the note naming a deleted path (absent at the subject, restored for the verdict) also appears
when verifier_selftest ends in ERROR on a timeout (implemented in 60008f6; pinned here).

F3 (the three helpers made private, the added-files filter reusing the helper) is a refactor with no
observable outcome; the whole corpus passing after it is its evidence, not a test in this file.

Fixture corpora are minimal: each throwaway repository is built without the kit's own self-tests and
carries only scripts/tests/_harness.py plus the counterexamples its scenario names. The kit's
test_gate_checks.py runs 27 nested gates, and a policy fixture's gate runs its trusted corpus at least once,
so copying it into every fixture cost minutes per test and pushed these files past the gate's
UNIT_TESTS_TIMEOUT when the gate ran them as added counterexamples. No scenario here needs it: each is
decided by which small corpus files are named and by the outcome they produce.

Assertions are on outcomes, file names and paths, never on the wording of a detail sentence.
"""
from __future__ import annotations

from _harness import Repo, detail, eligible_or_blocked_only_by, outcome

RUFF_REASON = "masking_ruff NOT_RUN"
APPROVAL = ("correction; approver:owner-designated-reviewer date:2026-09-25 decision:D-33 | "
            "reason:the counterexample is restated | spec v1->v2 | old:as on main new:as revised | "
            "transition:this commit | retained:the v1 case stays in history")

X_PATH = "scripts/tests/test_r1c_attr_revised_on_main.py"
X_NAME = "test_r1c_attr_revised_on_main.py"
X_V1 = '"""A corpus file main carries before the branch forks."""\n\n\ndef test_x():\n    assert 2 * 2 == 4\n'
X_V2 = '"""A corpus file main revised after the branch forked; it still holds."""\n\n\ndef test_x():\n    assert 2 * 2 == 4\n'

Z_PATH = "scripts/tests/test_r1c_attr_added_on_main.py"
Z_NAME = "test_r1c_attr_added_on_main.py"
Z = '"""A corpus file main added after the branch forked."""\n\n\ndef test_z():\n    assert 3 + 3 == 6\n'

SLOW_PATH = "scripts/tests/test_r1c_attr_slow.py"
SLOW = ('"""A corpus file that outlasts the policy ref\'s test timeout."""\nimport time\n\n\n'
        "def test_slow():\n    time.sleep(8)\n    assert True\n")

RETIRED_PATH = "scripts/tests/test_r1c_attr_retired.py"
RETIRED = '"""A trivially true case the policy ref carries, for a change to delete."""\n\n\ndef test_retired():\n    assert True\n'

HARNESS_PATH = "scripts/tests/_harness.py"


def minimal_repo(tmp_path) -> Repo:
    """A minimal kit: the throwaway repository with only _harness.py in its corpus (not yet committed)."""
    r = Repo(tmp_path / "r")
    r.copy_from_kit(HARNESS_PATH)
    return r


def append_blind(r: Repo, rel: str, content: str) -> None:
    """Append to a file in the throwaway repository without reading it."""
    with open(r.path / rel, "a", encoding="utf-8") as fh:
        fh.write(content)


def policy_change(r: Repo, slug: str, msg: str, **extra: str) -> None:
    r.record("policy", slug, WHY="the verifier instead of the docs, because the gate is the contract.",
             **extra, TESTS="python -m pytest -q scripts/tests")
    r.commit(msg)


def test_a_stale_branch_is_not_charged_with_mains_later_revision_and_addition_f1(tmp_path):
    """F1: main revised X and added Z after the branch forked; neither is this change's revision or deletion.

    The throwaway main carries X; the branch under test forks there. Main then merges a legal policy
    change (ACCEPTANCE line) that revises X, which keeps holding, and adds Z. The branch makes an
    unrelated legal policy change of its own (it widens the mock allowlist). Gated with base = the fork
    commit (main is no longer an ancestor) and policy_ref = main: X differs between the policy ref and
    the subject and Z is absent at the subject only because main moved on, so the detail must name
    neither. Expected to FAIL on the current HEAD, whose detail names Z as absent at the subject (and
    counts X among the revised files without naming it; the next test makes that misattribution
    observable by outcome).
    """
    r = minimal_repo(tmp_path)
    r.write(X_PATH, X_V1)
    fork = r.commit("policy: a counterexample on main")

    r.branch("policy/main-moves-on")
    r.write(X_PATH, X_V2)
    r.write(Z_PATH, Z)
    policy_change(r, "main-moves-on", "policy: revise one counterexample and add another",
                  ACCEPTANCE=APPROVAL)
    r.git("checkout", "-q", "main")
    r.git("merge", "--no-ff", "-q", "-m", "merge policy/main-moves-on", "policy/main-moves-on")

    r.git("checkout", "-q", "-b", "policy/unrelated", fork)
    append_blind(r, "tests/MOCK_ALLOWLIST", "boto3.\n")
    policy_change(r, "unrelated", "policy: allow boto3 mocks")
    assert r.read(X_PATH) == X_V1 and not (r.path / Z_PATH).exists(), "the fixture did not fork before main moved"

    _rc, res, out = r.gate("policy/unrelated", base=fork, policy_ref="main")
    assert res is not None, out
    selftest = detail(res, "verifier_selftest")
    assert outcome(res, "verifier_selftest") == "PASS", selftest
    assert X_NAME not in selftest, selftest
    assert Z_NAME not in selftest, selftest
    assert eligible_or_blocked_only_by(res, RUFF_REASON), res.get("ineligible_reasons")


PIN_PATH = "scripts/tests/test_r1c_attr_pin.py"
PIN_NAME = "test_r1c_attr_pin.py"
PIN_V1 = (
    '"""A corpus file pinning that the helper main later adds is not in the corpus yet."""\n'
    "from pathlib import Path\n\n\n"
    "def test_helper_not_yet_added():\n"
    f"    assert not (Path(__file__).parent / {Z_NAME!r}).exists()\n"
)
PIN_V2 = (
    '"""A corpus file revised with the addition: the helper main added is in the corpus."""\n'
    "from pathlib import Path\n\n\n"
    "def test_helper_added():\n"
    f"    assert (Path(__file__).parent / {Z_NAME!r}).exists()\n"
)


def test_a_stale_branch_is_not_refused_for_a_revision_main_made_f1(tmp_path):
    """F1, by outcome: a corpus file main revised after the fork is not run at the branch's stale content.

    Main carries PIN_PATH, which holds only while Z is absent; the branch under test forks there. Main
    then adds Z and revises PIN_PATH to match (ACCEPTANCE line). The branch makes an unrelated legal
    policy change. The branch did not revise PIN_PATH, so the trusted corpus (with Z and the revised
    PIN_PATH) is what judges it: verifier_selftest PASS, and neither file named. The first test's X
    assertion cannot tell the attributions apart when the stale content still holds (a PASS detail may
    count revisions without naming them); this one makes the misattribution a refusal naming the file.
    Expected to FAIL on the current HEAD, which runs the fork's PIN_PATH next to main's Z.
    """
    r = minimal_repo(tmp_path)
    r.write(PIN_PATH, PIN_V1)
    fork = r.commit("policy: a counterexample on main")

    r.branch("policy/main-adds-helper")
    r.write(PIN_PATH, PIN_V2)
    r.write(Z_PATH, Z)
    policy_change(r, "main-adds-helper", "policy: add a corpus file and revise its pin",
                  ACCEPTANCE=APPROVAL)
    r.git("checkout", "-q", "main")
    r.git("merge", "--no-ff", "-q", "-m", "merge policy/main-adds-helper", "policy/main-adds-helper")

    r.git("checkout", "-q", "-b", "policy/unrelated", fork)
    append_blind(r, "tests/MOCK_ALLOWLIST", "boto3.\n")
    policy_change(r, "unrelated", "policy: allow boto3 mocks")
    assert r.read(PIN_PATH) == PIN_V1 and not (r.path / Z_PATH).exists(), "the fixture did not fork before main moved"

    _rc, res, out = r.gate("policy/unrelated", base=fork, policy_ref="main")
    assert res is not None, out
    selftest = detail(res, "verifier_selftest")
    assert outcome(res, "verifier_selftest") == "PASS", selftest
    assert PIN_NAME not in selftest, selftest
    assert Z_NAME not in selftest, selftest
    assert eligible_or_blocked_only_by(res, RUFF_REASON), res.get("ineligible_reasons")


def test_a_deletion_is_named_when_the_selftest_times_out_pin_f2(tmp_path):
    """F2 pin: a timed-out verifier_selftest is ERROR and still names the path the change deleted.

    The throwaway main sets UNIT_TESTS_TIMEOUT = 3 in its policy.mk and carries a corpus test that
    sleeps 8 seconds, so the trusted-corpus run times out. The branch deletes another corpus file under
    an ACCEPTANCE line. Green on the current HEAD by design (60008f6 implemented the note on the timeout
    branches); this pins it, it does not drive a change.
    """
    r = minimal_repo(tmp_path)
    append_blind(r, "policy.mk", "\nUNIT_TESTS_TIMEOUT = 3\n")
    r.write(SLOW_PATH, SLOW)
    r.write(RETIRED_PATH, RETIRED)
    r.commit("policy: a short timeout, a slow counterexample and one to retire")

    r.branch("policy/retire-under-timeout")
    r.rm(RETIRED_PATH)
    policy_change(r, "retire-under-timeout", "policy: retire a counterexample", ACCEPTANCE=APPROVAL)
    _rc, res, out = r.gate("policy/retire-under-timeout")
    assert res is not None, out
    assert outcome(res, "verifier_selftest") == "ERROR", detail(res, "verifier_selftest")
    assert RETIRED_PATH in detail(res, "verifier_selftest"), detail(res, "verifier_selftest")
