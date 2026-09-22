"""The law the gate applies comes from the trusted ref, never from the commit under judgment (M6).

`build_ctx` reads policy.mk at `--policy-ref`, and every parameter the run then applies — the
required-check set, the protected set, the numeric thresholds — comes out of that one read. A
verifier that preferred the subject's own copy ("if the candidate ships one, use it") would let any
branch shrink REQUIRED_CHECKS_ENFORCED to a single check and merge on that, because `result_json`
builds `ineligible_reasons` only from the checks marked required, so every other failure goes quiet:
with that fallback in place the fixture below is reported merge_eligible with no ineligible reason,
while its `type` check is still FAIL.

Where the existing corpus stops. Each statement below was checked against that fallback, in the
sandbox, by running the named cases with the fallback applied:

  * scripts/tests/test_sunset_mocks_gaps_v04.py at :190 and its control at :203 (the m09 pair on
    tests/MOCK_ALLOWLIST) are the nearest neighbours in SHAPE — a subject that ships its own widened
    allowlist, and a control in which the policy ref carries the widening instead. This case is not
    a new shape; it is that shape carried over to policy.mk's own parameters, which the pair does not
    reach: `check_mocks` fetches the allowlist through its own
    `show(ctx.root, ctx.policy_ref, "tests/MOCK_ALLOWLIST")`, a read the fallback does not touch.
    Both stay green under it.
  * scripts/tests/test_gate_checks.py::test_p25_renew_branch_cannot_change_policy_parameters is the
    only existing case whose subject commits a modified policy.mk. It asserts protected_files FAIL,
    merge_eligible False with exit 1, and that `git show main:policy.mk` still holds the old
    MUTATION_MIN. None of those separates the two readings: that subject edits one threshold and
    leaves REQUIRED_CHECKS_ENFORCED intact, so protected_files stays required and still fails
    whichever copy is read, and main's bytes are unchanged either way. It stays green under the
    fallback too.

So the gap is not that the corpus ignores a branch carrying its own policy.mk — it is that no case
observes the parameter VALUES a run applied, which is the only place the two readings differ.

Lands at scripts/tests/test_policy_provenance_j4.py.
"""
from __future__ import annotations

import re

from _harness import Repo, detail, outcome, required_ids

# What a candidate branch would ship if it wanted to write its own law. `:=` rather than `?=` so the
# override is unambiguous to a plain Makefile reader as well as to the gate's parser (last one wins).
CANDIDATE_POLICY = (
    "\n# --- shipped by the branch under judgment, not by the trusted ref ---\n"
    "REQUIRED_CHECKS_ENFORCED := unit_tests\n"
    "PROTECTED_PATHS := docs/nowhere/**\n"
    "MUTATION_MIN := 0.00\n"
)
WEAKENED = {"REQUIRED_CHECKS_ENFORCED": "unit_tests",
            "PROTECTED_PATHS": "docs/nowhere/**",
            "MUTATION_MIN": "0.00"}


def policy_value(text: str, key: str) -> str:
    """The value `key` is assigned in one policy.mk text, whitespace-normalised, trailing comment cut.

    Three keys are read, from one file (`main:policy.mk`), whose assignments are each a single line.
    So this is deliberately not a copy of the gate's own `parse_policy`, and claims no independence
    from it either: it exists only to turn the trusted ref's bytes into the expectation, and it would
    not survive a backslash continuation or a repeated assignment, both of which `parse_policy`
    handles. If policy.mk ever grows either, this helper is what must change.
    """
    m = re.search(rf"^{key}\s*[:?]?=(.*)$", text, re.MULTILINE)
    assert m is not None, f"main:policy.mk assigns no {key}; this fixture can no longer weaken anything"
    return " ".join(m.group(1).split(" #", 1)[0].split())


def protected_detail(res: dict) -> tuple[set[str], list[str]]:
    """(the protected set the run echoed, the other protected_files detail lines).

    Splitting the echoed summary off is what lets a later assertion about a named file mean something:
    the trusted PROTECTED_PATHS itself contains `policy.mk`, so a substring test over the whole blob
    would be satisfied by the summary line alone.
    """
    lines = detail(res, "protected_files").splitlines()
    echoed = [i for i, ln in enumerate(lines) if "protected set:" in ln]
    assert len(echoed) == 1, f"protected_files did not echo the applied set exactly once: {lines}"
    return (set(lines[echoed[0]].split("protected set:", 1)[1].split()),
            [ln.strip() for i, ln in enumerate(lines) if i != echoed[0]])


def branch_shipping_its_own_policy(tmp_path) -> tuple[Repo, dict[str, str]]:
    """A compliant feature change that additionally commits a weakened policy.mk of its own."""
    r = Repo(tmp_path / "r")
    text = r.git("show", "main:policy.mk").stdout
    trusted = {key: policy_value(text, key) for key in WEAKENED}
    for key, weak in WEAKENED.items():
        assert trusted[key] != weak, (
            f"main:policy.mk already assigns {key} = {weak!r}, the value the fixture ships to weaken it; "
            f"nothing here would tell the two copies apart")
    r.legal_feature("greeting")
    r.append("policy.mk", CANDIDATE_POLICY)
    r.commit("feat: bring my own policy.mk")
    return r, trusted


def test_the_policy_in_force_is_the_trusted_refs_not_the_subjects_m6(tmp_path):
    """M6: the gate reads policy.mk at --policy-ref even when the subject commits its own copy.

    Four observations, each a place the run would visibly differ if the subject's copy were obeyed:
    the required-check set, the protected set, a numeric threshold echoed in a detail line, and the
    verdict those produce. They are collected and reported together, so a run that deviates on
    several of them says so rather than stopping at the first.

    Each observation compares meaning, not rendering — sets rather than word order, numbers rather
    than formatted text — so that reordering or reformatting what the gate prints cannot turn this
    red while the law in force is unchanged.
    """
    r, trusted = branch_shipping_its_own_policy(tmp_path)
    _, res, out = r.gate("feature/greeting")
    assert res is not None, out

    applied_protected, flagged = protected_detail(res)
    quoted = re.search(r"mutation score >= (\S+)", detail(res, "mutation"))
    assert quoted is not None, f"the mutation check quoted no threshold: {detail(res, 'mutation')}"
    try:
        applied_min: float | None = float(quoted.group(1))
    except ValueError:
        applied_min = None

    expected_required = set(trusted["REQUIRED_CHECKS_ENFORCED"].split())
    enforced = required_ids(res)
    reported = {c["id"] for c in res["checks"]}
    # A check the gate itself declined to run (verifier_selftest outside a policy change) may drop its
    # required flag; a check that ran and was still not enforced may not.
    ran_unenforced = sorted(cid for cid in (expected_required & reported) - enforced
                            if outcome(res, cid) != "NOT_RUN")

    observed: list[str] = []
    if ran_unenforced:
        observed.append(
            f"required checks: the trusted ref lists {sorted(expected_required)}; the run enforced "
            f"{sorted(enforced)}, and {ran_unenforced} ran without being enforced")
    if enforced - expected_required:
        observed.append(
            f"required checks: the run enforced {sorted(enforced - expected_required)}, which the "
            f"trusted ref does not list")

    if applied_protected != set(trusted["PROTECTED_PATHS"].split()):
        observed.append(
            f"protected set: the run applied {sorted(applied_protected)}; the trusted ref assigns "
            f"{sorted(trusted['PROTECTED_PATHS'].split())}")
    if applied_protected == set(WEAKENED["PROTECTED_PATHS"].split()):
        observed.append(
            f"protected set: the run applied exactly what the subject's own copy assigns, "
            f"{sorted(applied_protected)}")
    if outcome(res, "protected_files") != "FAIL":
        observed.append(
            f"protected_files: outcome {outcome(res, 'protected_files')}, on a feature branch whose "
            f"commit edits policy.mk; its detail lines beside the echoed set are {flagged}")
    elif not any("policy.mk" in ln for ln in flagged):
        observed.append(
            f"protected_files: FAIL, but no detail line beside the echoed set names policy.mk, the file "
            f"this branch appended its own policy to; those lines are {flagged}")

    if applied_min is None:
        observed.append(
            f"mutation threshold: the run quoted {quoted.group(1)!r}, which does not read as a number; "
            f"the trusted ref assigns MUTATION_MIN = {trusted['MUTATION_MIN']!r}")
    else:
        if applied_min != float(trusted["MUTATION_MIN"]):
            observed.append(
                f"mutation threshold: the run quoted {quoted.group(1)!r}; the trusted ref assigns "
                f"MUTATION_MIN = {trusted['MUTATION_MIN']!r}")
        if applied_min == float(WEAKENED["MUTATION_MIN"]):
            observed.append(
                f"mutation threshold: the run quoted {quoted.group(1)!r}, the value the subject's own "
                f"copy assigns")

    if res["merge_eligible"] is not False:
        observed.append(
            f"verdict: merge_eligible is {res['merge_eligible']!r} with ineligible_reasons "
            f"{res.get('ineligible_reasons')}")

    assert not observed, (
        "the subject's own policy.mk assigns "
        + ", ".join(f"{k} = {v!r}" for k, v in sorted(WEAKENED.items()))
        + ". The run was observed as:\n  " + "\n  ".join(observed))


def test_the_same_policy_mk_does_weaken_the_gate_when_it_is_the_trusted_ref_control(tmp_path):
    """Control: point --policy-ref at that branch and the weakened parameters do take effect.

    Without this, the case above would stay green if the appended assignments silently stopped being
    parsed — it would then be observing that nothing changed nothing.
    """
    r, trusted = branch_shipping_its_own_policy(tmp_path)
    _, res, out = r.gate("feature/greeting", policy_ref="feature/greeting")
    assert res is not None, out
    assert required_ids(res) == set(WEAKENED["REQUIRED_CHECKS_ENFORCED"].split()), (
        f"with --policy-ref at the branch, the run enforced {sorted(required_ids(res))}; that branch's "
        f"policy.mk assigns REQUIRED_CHECKS_ENFORCED = {WEAKENED['REQUIRED_CHECKS_ENFORCED']!r}")
    assert required_ids(res) != set(trusted["REQUIRED_CHECKS_ENFORCED"].split()), (
        f"with --policy-ref at the branch, the run enforced the trusted ref's set "
        f"{sorted(required_ids(res))}")
    applied_protected, _ = protected_detail(res)
    assert applied_protected == set(WEAKENED["PROTECTED_PATHS"].split()), (
        f"with --policy-ref at the branch, the run applied the protected set {sorted(applied_protected)}; "
        f"that branch's policy.mk assigns PROTECTED_PATHS = {WEAKENED['PROTECTED_PATHS']!r}")
