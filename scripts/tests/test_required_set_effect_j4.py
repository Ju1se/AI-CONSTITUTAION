"""The scoring link the corpus never pinned: a required check that is not PASS must refuse the merge.

Case JUD-2026-09-21-01 (finding J-4) recorded this mutant of `result_json` as surviving the
counterexample corpus. It rewrites the one line that decides who gets a vote:

    required = [c for c in checks if c.required]                      # main
    required = [c for c in checks if c.required and c.id != "h1"]     # the mutant

Under the mutant h1 is still *reported* as `required: true` and still FAILs, but it is left out of the
tally, so `ineligible_reasons` comes back empty, `merge_eligible` comes back true and the gate exits 0.
The `required` flag in result.json becomes decoration.

Why the corpus did not already catch this — measured in a sandbox copy of the kit, not inferred:

  * Exactly four counterexamples assert an h1 FAIL: `..._lm02` in test_adoption_prerequisites.py,
    and `..._ev01`, `..._ev02`, `..._p03` in test_trust_core_v04.py. All four go on to assert
    `res["merge_eligible"] is False`. So the missing ingredient was NOT "nobody asserted
    merge_eligible after an h1 FAIL" — every one of them does.
  * The three that run the enforced profile survive because their fixtures break a second required
    check as well. Probed verdicts on main: p03 -> required non-PASS [('h1','FAIL'), ('type','FAIL')];
    lm02 -> [('h1','FAIL'), ('unit_tests','FAIL')]; ev01 -> [('h1','FAIL'),
    ('verifier_selftest','FAIL')]. Drop h1 from the tally and the remaining offender still refuses the
    merge — for a reason other than the one the test is named after, which is why the assertion stays
    green and says nothing. The fourth, ev02, runs the advisory profile, whose required set is
    {type, protected_files, unit_tests}: h1 is not scored there at all, and the reason "the advisory
    profile never authorizes a merge" refuses on its own.
  * The new ingredient is therefore fixture isolation: a change in which the required check under test
    is the ONLY one that is not PASS. That is what makes `assert_is_the_only_required_failure` below
    load-bearing rather than decorative — without it these tests would pass under the mutant too.

Scope, stated plainly so the next reader does not over-trust this file: it pins two members of the
family, `h1` and `mocks`, because it has an isolating fixture for each. A mutant that drops `sunset`,
`records`, `type`, ... from the same tally still survives here (verified: the `sunset` variant leaves
this file green), because no fixture here makes those the sole required non-PASS check. The helper is
written over whatever the gate reports, so a new isolating fixture extends the coverage for free; the
generality of the wording is not by itself generality of coverage.

Failure messages below state what result.json says and stop there. They deliberately do not diagnose a
cause: a verifier that names the check in a differently worded reason, or refuses for another reason,
is a different fault from the one this file was written against, and the message must not pre-judge
which one happened.

Lands at scripts/tests/test_required_set_effect_j4.py.
"""
from __future__ import annotations

from _harness import RUFF, Repo, detail, eligible_or_blocked_only_by, outcome

GREETING_TEST = "from src.greeting import greet\n\n\ndef test_greet():\n    assert greet('a') == 'hello, a'\n"
GREETING_SRC = "def greet(name):\n    return f'hello, {name}'\n"
# The committed acceptance, rewritten in place so it can no longer fail: value() == 1 -> value() is not None.
WEAKENED_CORE_TEST = "from src.core import value\n\n\ndef test_value():\n    assert value() is not None\n"
# tests/MOCK_ALLOWLIST is I/O boundaries only, so a patch of a module this repository owns is a mocks FAIL.
MOCKING_GREETING_TEST = (
    "from unittest.mock import patch\n\n"
    "from src.greeting import greet\n\n\n"
    "def test_greet():\n"
    "    assert greet('a') == 'hello, a'\n\n\n"
    "def test_greet_is_patchable():\n"
    "    with patch('src.greeting.greet', return_value='x') as p:\n"
    "        assert p() == 'x'\n"
)

# A required check may be non-PASS for a reason that is about this machine rather than about the change.
# masking_ruff is NOT_RUN wherever ruff is absent, so it is excluded from the isolation assertions there
# and nowhere else. On a machine with ruff the exclusion is empty and every required check is in scope.
ENVIRONMENTAL = () if RUFF else ("masking_ruff",)


def required_non_pass(result: dict) -> list:
    """Every check the gate itself reports as required and not PASS, as (id, outcome) pairs."""
    return [(c["id"], c["outcome"]) for c in result["checks"]
            if c["required"] and c["outcome"] != "PASS"]


def substantive_non_pass(result: dict) -> list:
    """The same, minus the checks this machine cannot run at all."""
    return [(cid, oc) for cid, oc in required_non_pass(result) if cid not in ENVIRONMENTAL]


def assert_required_failures_refuse_the_merge(result: dict) -> None:
    """The invariant: whatever the gate reports as required and not PASS must block, and must be named.

    Two halves, and both matter. A verdict that lists a reason but stays eligible is a verdict nobody
    can act on; a verdict that refuses without naming the check gives the author nothing to fix.
    Only the presence of the check id in some reason is asserted, never the wording around it.
    """
    offenders = required_non_pass(result)
    reasons = result.get("ineligible_reasons") or []
    for cid, oc in offenders:
        assert any(cid in reason for reason in reasons), (
            f"result.json reports check {cid!r} with required=true and outcome {oc}, and no entry of "
            f"ineligible_reasons contains {cid!r}: {reasons}")
    if offenders:
        assert result["merge_eligible"] is False, (
            f"result.json reports required non-PASS check(s) {offenders} and "
            f"merge_eligible={result['merge_eligible']!r}, ineligible_reasons={reasons}")


def assert_is_the_only_required_failure(result: dict, cid: str, expected: str = "FAIL") -> None:
    """Fixture sanity: `cid` is reported required with `expected`, and is the only required non-PASS check.

    Without this the tests below would also pass on a verifier that dropped `cid` from the tally, since
    some other failing required check would keep the merge refused (which is how the four existing h1
    counterexamples survive the mutant).
    """
    reported = [c for c in result["checks"] if c["id"] == cid]
    assert reported, f"result.json reports no check {cid!r}; it reports {[c['id'] for c in result['checks']]}"
    c = reported[0]
    assert c["required"] is True, f"result.json reports check {cid!r} with required={c['required']!r}"
    assert c["outcome"] == expected, f"result.json reports check {cid!r} with outcome {c['outcome']}"
    assert substantive_non_pass(result) == [(cid, expected)], (
        f"this fixture must leave {cid!r} as the only required check that is not PASS; result.json "
        f"reports required non-PASS checks {required_non_pass(result)} "
        f"(ids excluded as environmental on this machine: {list(ENVIRONMENTAL)})")


def weakened_committed_assertion(r: Repo) -> None:
    """A feature change that is compliant in every respect but one: it weakens a committed test.

    Test-first, implementation after, record filled in — so h1 is the only required check it breaks.
    """
    r.branch("feature/greeting")
    r.write("tests/test_greeting.py", GREETING_TEST)
    r.commit("test: greet")
    r.write("src/greeting.py", GREETING_SRC)
    r.write("tests/test_core.py", WEAKENED_CORE_TEST)
    r.record("feature", "greeting", WHY="an f-string instead of concatenation, because readability.",
             SEARCHED='rg -n "greet" src/ → 0 hits | NONE-FITS: n/a',
             TESTS="python -m pytest -q tests")
    r.commit("feat: greet")


def mocked_own_module(r: Repo) -> None:
    """The same compliant feature, except that its new test patches a module this repository owns.

    Nothing else is touched, so mocks is the only required check it breaks — the second isolating
    fixture this file needs to pin a second member of the mutant family.
    """
    r.branch("feature/greeting")
    r.write("tests/test_greeting.py", MOCKING_GREETING_TEST)
    r.commit("test: greet")
    r.write("src/greeting.py", GREETING_SRC)
    r.record("feature", "greeting", WHY="an f-string instead of concatenation, because readability.",
             SEARCHED='rg -n "greet" src/ → 0 hits | NONE-FITS: n/a',
             TESTS="python -m pytest -q tests")
    r.commit("feat: greet")


def test_a_failing_required_check_must_make_the_change_ineligible_j4(tmp_path):
    """J-4: h1 FAILs and is reported required, so it must reach ineligible_reasons and refuse the merge."""
    r = Repo(tmp_path / "r")
    weakened_committed_assertion(r)
    rc, res, out = r.gate("feature/greeting")
    assert res is not None, out

    assert_is_the_only_required_failure(res, "h1")
    assert "tests/test_core.py" in detail(res, "h1"), detail(res, "h1")

    assert_required_failures_refuse_the_merge(res)
    assert rc != 0, (f"the gate exited {rc} on a change it reports as "
                     f"merge_eligible={res['merge_eligible']!r} with "
                     f"ineligible_reasons={res['ineligible_reasons']}")


def test_the_link_holds_for_a_second_required_check_j4(tmp_path):
    """J-4, sibling: the same must hold for mocks, so the tally is not pinned for h1 alone."""
    r = Repo(tmp_path / "r")
    mocked_own_module(r)
    rc, res, out = r.gate("feature/greeting")
    assert res is not None, out

    assert_is_the_only_required_failure(res, "mocks")
    assert "src.greeting.greet" in detail(res, "mocks"), detail(res, "mocks")

    assert_required_failures_refuse_the_merge(res)
    assert rc != 0, (f"the gate exited {rc} on a change it reports as "
                     f"merge_eligible={res['merge_eligible']!r} with "
                     f"ineligible_reasons={res['ineligible_reasons']}")


def test_a_clean_change_is_still_authorized_control(tmp_path):
    """Control: the invariant above must not be satisfiable by refusing everything.

    Every path through this test asserts the positive direction. On a machine without ruff the change
    is blocked, but only by masking_ruff NOT_RUN — which is what `eligible_or_blocked_only_by` is for;
    the test never falls through to asserting nothing about authorization.
    """
    r = Repo(tmp_path / "r")
    r.legal_feature()
    rc, res, out = r.gate("feature/greeting")
    assert res is not None, out

    assert substantive_non_pass(res) == [], (
        f"a compliant test-first feature left required checks not PASS: {required_non_pass(res)} "
        f"(ids excluded as environmental on this machine: {list(ENVIRONMENTAL)})")
    assert eligible_or_blocked_only_by(res, "masking_ruff"), (
        f"result.json reports merge_eligible={res['merge_eligible']!r} with "
        f"ineligible_reasons={res['ineligible_reasons']} on a compliant test-first feature")
    assert_required_failures_refuse_the_merge(res)

    if RUFF:
        assert res["merge_eligible"] is True, res["ineligible_reasons"]
        assert res["ineligible_reasons"] == [], res["ineligible_reasons"]
        assert rc == 0, out[-2000:]
    else:
        assert outcome(res, "masking_ruff") == "NOT_RUN", detail(res, "masking_ruff")
        assert res["merge_eligible"] is False, res["ineligible_reasons"]
        assert rc != 0, out[-2000:]
