"""Controls for the owner's balance scenarios 3 and 6: legitimate work must pass.

Every other file in this corpus mostly pins what the gate REFUSES. These are controls: each pins that a
piece of legitimate work is NOT refused, so that a verifier which grew stricter in the wrong place — one
that sealed a pinned behaviour forever, or dragged ordinary work into constitutional proceedings — goes
red here instead of looking safer.

Scenario 3 — a pinned verifier behaviour can still be changed by an authorized path, so the corpus can
never seal a behaviour forever.
Scenario 6 — ordinary low-risk work stays cheap: a feature change does not run the corpus machinery, a
dispute in the corpus does not spill over onto unrelated work, and a docs-only chore is not drawn into
the 100% audit set.

Fixtures are minimal on purpose: each copies scripts/tests/_harness.py in and adds only the one or two
tiny corpus files its scenario needs, because a policy gate runs the fixture's corpus. Assertions are on
outcomes, `merge_eligible`, `required` flags and printed markers such as "not selected", never on
sentence wording.
"""
from __future__ import annotations

from _harness import Repo, detail, eligible_or_blocked_only_by, outcome

# Everything that is not masking_ruff must PASS on a legitimate change; ruff may simply be absent.
RUFF_REASON = "masking_ruff NOT_RUN"

MARKER_V1 = "# behaviour-v1"
MARKER_V2 = "# behaviour-v2"

# The corpus test that pins the verifier behaviour: it reads the verifier at the kit root, which is
# whatever scripts/gate_checks.py the corpus is being run against.
PIN_V1 = (
    "from _harness import KIT\n\n\n"
    "def test_behaviour_is_pinned():\n"
    "    lines = (KIT / 'scripts/gate_checks.py').read_text(encoding='utf-8').splitlines()\n"
    f"    assert {MARKER_V1!r} in lines\n"
)
PIN_V1_OR_V2 = (
    "from _harness import KIT\n\n\n"
    "def test_behaviour_is_pinned():\n"
    "    lines = (KIT / 'scripts/gate_checks.py').read_text(encoding='utf-8').splitlines()\n"
    f"    assert {MARKER_V1!r} in lines or {MARKER_V2!r} in lines\n"
)
PIN_V2 = (
    "from _harness import KIT\n\n\n"
    "def test_behaviour_is_pinned():\n"
    "    lines = (KIT / 'scripts/gate_checks.py').read_text(encoding='utf-8').splitlines()\n"
    f"    assert {MARKER_V2!r} in lines\n"
)
TRIVIAL = "def test_unrelated():\n    assert 1 + 1 == 2\n"
FAILING = "def test_a_bad_revision_landed():\n    assert False, 'a disputed counterexample'\n"


def acceptance(old: str, new: str) -> str:
    """A recorded decision in the form the law in force requires for revising protected acceptance."""
    return ("correction; approver:owner-designated-reviewer date:2026-09-25 decision:D-balance-3 | "
            "reason:the pinned behaviour is being changed on purpose | spec v1->v2 | "
            f"old:{old} new:{new} | transition:loosen then tighten | "
            "retained:the earlier pin stays in history")


def entry(result: dict, check_id: str) -> dict:
    """The raw JSON object for one check, so a test can assert on `required` and not only on `outcome`."""
    for c in result["checks"]:
        if c["id"] == check_id:
            return c
    raise AssertionError(f"the gate did not report a check named {check_id!r}")


def with_corpus(r: Repo, files: dict[str, str]) -> None:
    """Put the harness and the given tiny corpus files on the throwaway main."""
    r.copy_from_kit("scripts/tests/_harness.py")
    for rel, body in files.items():
        r.write(rel, body)
    r.commit("chore: a minimal verifier corpus")


def audit_select(r: Repo, salt: str) -> str:
    res = r.run("audit-select", "--subject", "HEAD", "--base", "main", "--policy-ref", "main",
                env={"AUDIT_SALT": salt})
    assert res.returncode == 0, res.stdout + res.stderr
    return res.stdout + res.stderr


# ----------------------------------------------------------------- scenario 3: a pin is not a seal

def test_a_pinned_verifier_behaviour_has_an_authorized_transition_path(tmp_path):
    """Scenario 3: a legitimate change to a pinned verifier behaviour has an authorized path.

    The throwaway main carries a verifier behaviour (the marker line) and a corpus test pinning it.
    Step 1, a policy change recorded with an ACCEPTANCE line, loosens the pin to accept v1 or v2; it must
    be merge-eligible, and it is merged. Step 2, a policy change recorded with an ACCEPTANCE line, moves
    the verifier to v2 and tightens the pin to v2 only; it must be merge-eligible too.

    This pins that SOME authorized two-step path exists — not that it is the only one. The ACCEPTANCE form
    here is whatever the law in force requires, so this fixture changes when the law does. Deletion
    routes are deliberately not pinned (the enacted policy row says cases are added, never removed), and
    no test here pins that any other route is refused.
    """
    r = Repo(tmp_path / "r")
    # The gate leaves its extracted verifier and its result in the work tree; a second commit after a
    # gate run must not sweep them into the change under judgment. Local to this clone, never committed.
    (r.path / ".git/info/exclude").write_text(".verifiers/\n.gate/\n", encoding="utf-8")
    r.append("scripts/gate_checks.py", f"\n{MARKER_V1}\n")
    with_corpus(r, {"scripts/tests/test_pin.py": PIN_V1, "scripts/tests/test_unrelated.py": TRIVIAL})

    # Step 1: loosen the pin, the verifier unchanged.
    r.branch("policy/pin-widen")
    r.write("scripts/tests/test_pin.py", PIN_V1_OR_V2)
    r.record("policy", "pin-widen",
             WHY="a pin accepting v1 or v2 instead of v1 only, because the behaviour is about to move.",
             TESTS="python -m pytest -q scripts/tests",
             ACCEPTANCE=acceptance("v1 only", "v1 or v2"))
    r.commit("policy: loosen the behaviour pin")
    _, res, out = r.gate("policy/pin-widen")
    assert res is not None, out
    assert outcome(res, "verifier_selftest") == "PASS", detail(res, "verifier_selftest")
    assert eligible_or_blocked_only_by(res, RUFF_REASON), res.get("ineligible_reasons")

    r.git("checkout", "-q", "main")
    r.git("merge", "-q", "--no-ff", "policy/pin-widen", "-m", "merge policy/pin-widen")

    # Step 2: move the behaviour and tighten the pin to the new behaviour only.
    r.branch("policy/behaviour-v2")
    r.write("scripts/gate_checks.py", r.read("scripts/gate_checks.py").replace(
        f"{MARKER_V1}\n", f"{MARKER_V2}\n"))
    r.write("scripts/tests/test_pin.py", PIN_V2)
    r.record("policy", "behaviour-v2",
             WHY="behaviour v2 with a v2-only pin instead of keeping v1, because v1 is being retired.",
             TESTS="python -m pytest -q scripts/tests",
             ACCEPTANCE=acceptance("v1 or v2", "v2 only"))
    r.commit("policy: move the behaviour to v2")
    assert MARKER_V2 in r.read("scripts/gate_checks.py").splitlines()
    _, res, out = r.gate("policy/behaviour-v2")
    assert res is not None, out
    assert outcome(res, "verifier_selftest") == "PASS", detail(res, "verifier_selftest")
    assert eligible_or_blocked_only_by(res, RUFF_REASON), res.get("ineligible_reasons")


# ----------------------------------------------------------------- scenario 6: ordinary work stays cheap

def test_a_legal_feature_does_not_run_the_corpus_machinery_6a(tmp_path):
    """Scenario 6a: a legal feature change is merge-eligible, and verifier_selftest is NOT_RUN and not
    required for it — the corpus machinery belongs to policy changes, not to ordinary work."""
    r = Repo(tmp_path / "r")
    with_corpus(r, {"scripts/tests/test_unrelated.py": TRIVIAL})
    r.legal_feature()
    _, res, out = r.gate("feature/greeting")
    assert res is not None, out
    st = entry(res, "verifier_selftest")
    assert st["outcome"] == "NOT_RUN", st
    assert st["required"] is False, st
    assert eligible_or_blocked_only_by(res, RUFF_REASON), res.get("ineligible_reasons")


def test_a_dispute_in_the_corpus_does_not_spill_over_onto_a_feature_6b(tmp_path):
    """Scenario 6b: the throwaway main carries a corpus test that FAILS, as if a bad revision had landed.
    A legal feature change on that repository is still merge-eligible: a dispute over the verifier's
    case law is settled in a policy change, not charged to unrelated work."""
    r = Repo(tmp_path / "r")
    with_corpus(r, {"scripts/tests/test_disputed.py": FAILING})
    r.legal_feature()
    _, res, out = r.gate("feature/greeting")
    assert res is not None, out
    assert eligible_or_blocked_only_by(res, RUFF_REASON), res.get("ineligible_reasons")


def test_a_docs_only_chore_is_cheap_and_has_no_audit_trigger_6c(tmp_path):
    """Scenario 6c: a docs-only chore is merge-eligible, and audit-select names no 100%-audit trigger for
    it. Salts are tried in order, as the audit-select negative control in
    test_masking_records_gaps_v04.py does: the subject sha is fresh every run, so only a draw above
    AUDIT_RATE can leave it unselected, and with 12 candidates all of them drawing has probability
    0.2**12."""
    r = Repo(tmp_path / "r")
    r.branch("chore/notes")
    r.write("docs/notes.md", "# Notes\n\nA plain page of prose.\n")
    r.record("chore", "notes", WHY="a docs page instead of a README section, because it stands alone.",
             TESTS="none: documentation only")
    r.commit("chore: add notes")
    _, res, out = r.gate("chore/notes")
    assert res is not None, out
    assert eligible_or_blocked_only_by(res, RUFF_REASON), res.get("ineligible_reasons")

    quiet, sel = None, ""
    for salt in [f"balance-{i}" for i in range(12)]:
        sel = audit_select(r, salt)
        if "not selected" in sel:
            quiet = salt
            break
    assert quiet is not None, f"no salt left this docs-only chore unselected: {sel}"
