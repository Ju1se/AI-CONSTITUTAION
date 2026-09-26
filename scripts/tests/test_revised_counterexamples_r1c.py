"""A counterexample a policy change revises must hold against the verifier it ships (plan item R1(c)).

For a `policy` change, verifier_selftest runs the corpus as it stands at the policy ref over the
candidate verifier, then runs the scripts/tests/test_*.py files the change ADDS. A corpus file the change
MODIFIES was never run at its new content, so a revision that cannot hold on the shipped verifier merged,
and the next unrelated policy change was the one refused.

Each fixture below puts one small counterexample on `main` (CASE_PATH, which drives the verifier through
the harness), branches `policy/...`, and commits a record carrying an ACCEPTANCE line so the frozen-set
rule does not stop the change before verifier_selftest judges it. The spec lines pinned:

  S1  every scripts/tests/ path present at the policy ref and at the subject with different bytes is
      revised; a revised test_*.py runs at its subject content, and a revised helper makes every trusted
      test_*.py run with the revised paths in place; a failure is verifier_selftest FAIL naming the file.
  S2  a path present at the policy ref and absent at the subject is named in verifier_selftest's detail;
      the outcome does not change.
  S3  under the ACCEPTANCE exemption h1 still scans the frozen set and names every entry in its detail
      (a modified path as well as a deleted one, with its commit); the outcome stays PASS.
  S4  a revision that still holds on the shipped verifier (a docstring-only edit) passes; and a
      revision that holds only on the candidate verifier the same change ships passes too, so the
      revision is judged against the candidate, not against the policy-ref verifier.

Fixture corpora are minimal: each throwaway repository is built without the kit's own self-tests and
carries only scripts/tests/_harness.py plus the counterexamples its scenario needs. The kit's
test_gate_checks.py runs 27 nested gates, and a policy fixture's gate runs its trusted corpus once more for
each revision, so copying it into every fixture cost minutes per test and pushed this file past the gate's
UNIT_TESTS_TIMEOUT when the gate ran it as an added counterexample. The guard test, which needs the trusted
corpus to refuse a stub verifier, carries one small sentinel (SENTINEL_PATH: a nested gate on a failing
change must end h1 FAIL) and revises that sentinel where the full-corpus version revised test_gate_checks.py.

Assertions are on outcomes, file names and paths, never on the wording of a detail sentence.
"""
from __future__ import annotations

from _harness import Repo, detail, eligible_or_blocked_only_by, outcome

RUFF_REASON = "masking_ruff NOT_RUN"
APPROVAL = ("correction; approver:owner-designated-reviewer date:2026-09-25 decision:D-31 | "
            "reason:the counterexample is restated | spec v1->v2 | old:h1 PASS new:as revised | "
            "transition:this commit | retained:the v1 case stays in history")

CASE_PATH = "scripts/tests/test_r1c_case.py"
CASE_DOC = '"""A counterexample the policy ref carries: a compliant feature change keeps h1 PASS."""\n'
CASE_BODY = (
    "from _harness import Repo, outcome\n\n\n"
    "def test_a_compliant_feature_keeps_h1_passing(tmp_path):\n"
    "    r = Repo(tmp_path / 'r')\n"
    "    r.legal_feature()\n"
    "    _rc, res, out = r.gate('feature/greeting')\n"
    "    assert res is not None, out\n"
    "    assert outcome(res, 'h1') == 'PASS', out\n"
)
CASE = CASE_DOC + CASE_BODY

RETIRED_PATH = "scripts/tests/test_r1c_retired.py"
RETIRED = '"""A trivially true case the policy ref carries, for a change to delete."""\n\n\ndef test_retired():\n    assert True\n'

HARNESS_PATH = "scripts/tests/_harness.py"

SENTINEL_PATH = "scripts/tests/test_r1c_sentinel.py"
SENTINEL = (
    '"""A counterexample the policy ref carries: a change that edits an existing test ends h1 FAIL."""\n'
    "from _harness import BASE_TEST, Repo, outcome\n\n\n"
    "def test_an_edited_existing_test_fails_h1(tmp_path):\n"
    "    r = Repo(tmp_path / 'r')\n"
    "    r.branch('feature/edit-test')\n"
    "    r.write('tests/test_core.py', BASE_TEST + '\\n\\ndef test_extra():\\n    assert True\\n')\n"
    "    r.commit('test: edit an existing test')\n"
    "    _rc, res, out = r.gate('feature/edit-test')\n"
    "    assert res is not None, out\n"
    "    assert outcome(res, 'h1') == 'FAIL', out\n"
    "    assert res['merge_eligible'] is False, out\n"
)


def repo_with_case(tmp_path, sentinel: bool = False) -> Repo:
    """A minimal kit: _harness.py, CASE_PATH and RETIRED_PATH (and SENTINEL_PATH if asked) on main."""
    r = Repo(tmp_path / "r")
    r.copy_from_kit(HARNESS_PATH)
    r.write(CASE_PATH, CASE)
    r.write(RETIRED_PATH, RETIRED)
    if sentinel:
        r.write(SENTINEL_PATH, SENTINEL)
    r.commit("policy: the harness and the counterexamples on main")
    return r


def replace_once(r: Repo, rel: str, old: str, new: str) -> None:
    text = r.read(rel)
    assert text.count(old) == 1, f"{rel} no longer contains {old!r} exactly once; the fixture is stale"
    r.write(rel, text.replace(old, new))


def policy_change_with_acceptance(r: Repo, slug: str, msg: str) -> None:
    r.record("policy", slug, WHY="the verifier instead of the docs, because the gate is the contract.",
             ACCEPTANCE=APPROVAL, TESTS="python -m pytest -q scripts/tests")
    r.commit(msg)


def test_a_revised_counterexample_that_cannot_hold_is_refused_s1(tmp_path):
    """S1: a corpus test revised so it fails on the shipped verifier makes verifier_selftest FAIL.

    The verifier itself is unchanged; the revision flips the expected h1 outcome of a compliant change,
    which the shipped verifier cannot produce. Today the trusted copy is restored over it, so it is
    never run at its new content and the change is merge_eligible.
    """
    r = repo_with_case(tmp_path)
    r.branch("policy/revise-case")
    replace_once(r, CASE_PATH, "== 'PASS', out", "== 'FAIL', out")
    policy_change_with_acceptance(r, "revise-case", "policy: revise a counterexample")
    rc, res, out = r.gate("policy/revise-case")
    assert res is not None, out
    assert outcome(res, "verifier_selftest") == "FAIL", detail(res, "verifier_selftest")
    assert "test_r1c_case.py" in detail(res, "verifier_selftest"), detail(res, "verifier_selftest")
    assert res["merge_eligible"] is False
    assert rc != 0


def test_a_revised_helper_is_run_under_every_trusted_test_s1(tmp_path):
    """S1: a revised non-test path (_harness.py) makes every trusted test_*.py run with it in place.

    The helper's `outcome` is revised to lower-case what it returns, so CASE_PATH (unchanged by the
    change) can no longer hold. The refusal must name the revised helper.
    """
    r = repo_with_case(tmp_path)
    r.branch("policy/revise-helper")
    replace_once(r, HARNESS_PATH, 'return c["outcome"]', 'return c["outcome"].lower()')
    policy_change_with_acceptance(r, "revise-helper", "policy: revise a corpus helper")
    rc, res, out = r.gate("policy/revise-helper")
    assert res is not None, out
    assert outcome(res, "verifier_selftest") == "FAIL", detail(res, "verifier_selftest")
    assert "_harness.py" in detail(res, "verifier_selftest"), detail(res, "verifier_selftest")
    assert res["merge_eligible"] is False
    assert rc != 0


def test_a_docstring_only_revision_still_passes_control_s4(tmp_path):
    """S4 control: a revision that still holds on the shipped verifier keeps verifier_selftest PASS.

    Without it, the refusals above would also pass against a verifier that refuses every revision.
    """
    r = repo_with_case(tmp_path)
    r.branch("policy/reword-case")
    replace_once(r, CASE_PATH, CASE_DOC,
                 '"""A counterexample on main: a compliant feature change must keep h1 at PASS."""\n')
    policy_change_with_acceptance(r, "reword-case", "policy: reword a counterexample")
    _rc, res, out = r.gate("policy/reword-case")
    assert res is not None, out
    assert outcome(res, "verifier_selftest") == "PASS", detail(res, "verifier_selftest")
    assert outcome(res, "h1") == "PASS", detail(res, "h1")
    assert eligible_or_blocked_only_by(res, RUFF_REASON), res.get("ineligible_reasons")


def test_a_revised_counterexample_is_named_by_h1_with_its_commit_s3(tmp_path):
    """S3: under the ACCEPTANCE exemption h1 still names a modified (M) frozen-set entry and its commit.

    The same docstring-only edit as the S4 control, so the outcome stays PASS; what is pinned is that
    the scan's entry reaches h1's detail with its path (a modified path, not only a deleted one) and
    its commit (any abbreviation of 7 or more characters of the subject sha).
    """
    r = repo_with_case(tmp_path)
    r.branch("policy/reword-case-h1")
    replace_once(r, CASE_PATH, CASE_DOC,
                 '"""A counterexample on main: a compliant feature change must keep h1 at PASS."""\n')
    policy_change_with_acceptance(r, "reword-case-h1", "policy: reword a counterexample")
    _rc, res, out = r.gate("policy/reword-case-h1")
    assert res is not None, out
    assert outcome(res, "h1") == "PASS", detail(res, "h1")
    assert CASE_PATH in detail(res, "h1"), detail(res, "h1")
    assert res["subject_sha"][:7] in detail(res, "h1"), detail(res, "h1")


VERIFIER_PATH = "scripts/gate_checks.py"
CANDIDATE_MARKER = "# r1c-candidate-marker"


def test_a_revision_that_holds_only_on_the_candidate_verifier_passes_control_s1(tmp_path):
    """S1 control: the revision is judged against the candidate verifier, not the policy-ref one.

    One policy commit changes the verifier (a marker comment appended to scripts/gate_checks.py) and
    revises CASE_PATH to require that change: the nested Repo copies gate_checks.py from its own KIT,
    which is the export under test. The revision fails on the policy-ref verifier and holds only on
    the candidate, so an implementation that ran revisions on the policy-ref verifier would refuse this
    legitimate change (verifier and its counterexample updated together).
    """
    r = repo_with_case(tmp_path)
    r.branch("policy/verifier-and-case")
    r.append(VERIFIER_PATH, f"\n{CANDIDATE_MARKER}\n")
    replace_once(r, CASE_PATH, "    r.legal_feature()\n",
                 f"    assert {CANDIDATE_MARKER!r} in r.read({VERIFIER_PATH!r})\n    r.legal_feature()\n")
    policy_change_with_acceptance(r, "verifier-and-case", "policy: change the verifier and its counterexample")
    _rc, res, out = r.gate("policy/verifier-and-case")
    assert res is not None, out
    assert outcome(res, "verifier_selftest") == "PASS", detail(res, "verifier_selftest")
    assert eligible_or_blocked_only_by(res, RUFF_REASON), res.get("ineligible_reasons")


def test_a_deleted_counterexample_is_named_by_h1_and_selftest_s2_s3(tmp_path):
    """S2 + S3: deleting a corpus file under ACCEPTANCE keeps h1 PASS and both checks name the path.

    h1's detail names the deleted path (the frozen-set scan still runs under the exemption, S3);
    verifier_selftest's detail names it as absent at the subject and restored for this verdict (S2),
    and its outcome is unchanged: the restored trusted corpus still holds.
    """
    r = repo_with_case(tmp_path)
    r.branch("policy/retire-case")
    r.rm(RETIRED_PATH)
    policy_change_with_acceptance(r, "retire-case", "policy: retire a counterexample")
    _rc, res, out = r.gate("policy/retire-case")
    assert res is not None, out
    assert outcome(res, "h1") == "PASS", detail(res, "h1")
    assert RETIRED_PATH in detail(res, "h1"), detail(res, "h1")
    assert res["subject_sha"][:7] in detail(res, "h1"), detail(res, "h1")
    assert outcome(res, "verifier_selftest") == "PASS", detail(res, "verifier_selftest")
    assert RETIRED_PATH in detail(res, "verifier_selftest"), detail(res, "verifier_selftest")


STUB_VERIFIER = (
    "import json\n"
    "import sys\n"
    "print('all checks PASS')\n"
    "json.dump({'merge_eligible': True, 'checks': []}, open(sys.argv[-1], 'w'))\n"
    "sys.exit(0)\n"
)
TRIVIAL_TEST = "def test_ok():\n    assert True\n"


def test_a_stub_verifier_with_every_counterexample_weakened_is_refused_guard_s1(tmp_path):
    """S1 guard: the trusted copy of a revised path is still run first, so weakening it cannot rescue a stub.

    The change replaces the verifier with a stub and revises (does not delete) SENTINEL_PATH, the
    fixture's stand-in for the kit's test_gate_checks.py, and CASE_PATH to a trivially true test. An
    implementation that ran the revision in place of the trusted copy would let this merge. This is a
    guard and green by design: it passes on today's verifier.
    """
    r = repo_with_case(tmp_path, sentinel=True)
    r.branch("policy/weaken-and-stub")
    r.write(VERIFIER_PATH, STUB_VERIFIER)
    r.write(SENTINEL_PATH, TRIVIAL_TEST)
    r.write(CASE_PATH, TRIVIAL_TEST)
    policy_change_with_acceptance(r, "weaken-and-stub", "policy: simplify the verifier and its corpus")
    _rc, res, out = r.gate("policy/weaken-and-stub")
    assert res is not None, out
    assert outcome(res, "h1") == "PASS", detail(res, "h1")
    assert outcome(res, "verifier_selftest") == "FAIL", detail(res, "verifier_selftest")
    assert res["merge_eligible"] is False
