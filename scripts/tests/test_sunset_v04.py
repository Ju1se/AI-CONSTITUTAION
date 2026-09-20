"""v0.4 regression tests for the renew field-level diff (§3.4) and the sunset rules (§3.5).

Written from `v04-spec.md` before the implementation exists; these pin down behaviour the v0.3
verifier does not have yet. Every date is computed from `datetime.date.today()` so the suite does
not rot. Each refusal is paired with the nearly identical legitimate case that must still pass.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from _harness import Repo, detail, eligible_or_blocked_only_by, outcome

TODAY = dt.date.today()


def days(n: int) -> dt.date:
    """A date n days from today; never hard-code one, or the suite rots."""
    return TODAY + dt.timedelta(days=n)


def price_src(factor: str, date: dt.date, kind: str = "compat", owner: str = "renew-px",
              reason: str = "old api", extra: str = "") -> str:
    """A tagged code line: the code part and the SUNSET tag live on the same line (§3.4)."""
    return (f"def discount(price):\n    return price * {factor}"
            f"  # SUNSET {date} {kind} owner:{owner} reason:{reason}\n{extra}")


def legacy_src(date: dt.date, grace: str = "", owner: str = "team-b", kind: str = "compat") -> str:
    tag = f"# SUNSET {date} {kind} owner:{owner} reason:old api"
    if grace:
        tag += f" grace:{grace}"
    return f"def legacy():\n    return 1  {tag}\n"


def repo_with(path: Path, rel: str, content: str) -> Repo:
    """A repo whose BASE (main) already carries `content` at `rel` — a pre-existing tag."""
    r = Repo(path)
    r.write(rel, content)
    r.commit("chore: shim carrying a sunset tag")
    return r


def renew_change(r: Repo, content: str) -> tuple[int, dict, str]:
    """A renew/ branch that rewrites the tagged pricing line to `content`."""
    r.branch("renew/px")
    r.write("src/pricing.py", content)
    r.record("renew", "px")
    r.commit("renew: extend the pricing shim")
    return r.gate("renew/px")


def file_the_grace(r: Repo, **extra: str) -> None:
    """Rewrite the feature record produced by `legal_feature`, adding the given fields."""
    r.record("feature", "greeting", WHY="a shim instead of a rewrite, because callers remain.",
             SEARCHED='rg -n "greet" src/ → 0 hits | NONE-FITS: n/a',
             TESTS="python -m pytest -q tests", **extra)


# ----------------------------------------------------------------- §3.4 renew is a field-level diff

def test_renew_changing_code_on_the_tag_line_fails_type_p0_6(tmp_path):
    """§3.4: the code part before the tag must be byte-identical; halving a price under cover of a
    renewal (audit P08 / P0-6) must FAIL type, even when no test covers the function."""
    r = repo_with(tmp_path / "r", "src/pricing.py", price_src("0.9", days(10)))
    _, res, out = renew_change(r, price_src("0.5", days(80), reason="old api v2"))
    assert res is not None, out
    assert outcome(res, "type") == "FAIL", detail(res, "type")
    assert "code changed alongside the tag" in detail(res, "type").lower()
    assert "0.5" in detail(res, "type")  # the offending line is quoted


def test_renew_changing_only_the_tag_passes_type_p0_6(tmp_path):
    """CONTROL for §3.4: the same branch moving only the date is what renew/ is for — type PASS."""
    r = repo_with(tmp_path / "r", "src/pricing.py", price_src("0.9", days(10)))
    _, res, out = renew_change(r, price_src("0.9", days(80)))
    assert res is not None, out
    assert outcome(res, "type") == "PASS", detail(res, "type")
    assert outcome(res, "sunset") == "PASS", detail(res, "sunset")


def test_renew_hunk_with_unequal_line_counts_fails_type_p0_6(tmp_path):
    """§3.4: for each hunk the removed and added line counts must be equal, so a renewal cannot
    smuggle an extra line in beside the pair it renews."""
    r = repo_with(tmp_path / "r", "src/pricing.py", price_src("0.9", days(10)))
    extra = f"# SUNSET {days(80)} compat owner:renew-px reason:second note\n"
    _, res, out = renew_change(r, price_src("0.9", days(80), extra=extra))
    assert res is not None, out
    assert outcome(res, "type") == "FAIL", detail(res, "type")


def test_renew_changing_kind_or_owner_fails_type_p0_6(tmp_path):
    """§3.4: in a paired hunk `kind` and `owner` must be unchanged — a renewal may move the date,
    not reclassify the debt or hand it to someone else."""
    for i, (kind, owner) in enumerate([("flag", "renew-px"), ("compat", "somebody-else")]):
        r = repo_with(tmp_path / f"r{i}", "src/pricing.py", price_src("0.9", days(10)))
        _, res, out = renew_change(r, price_src("0.9", days(80), kind=kind, owner=owner))
        assert res is not None, out
        assert outcome(res, "type") == "FAIL", f"kind={kind} owner={owner}: {detail(res, 'type')}"


# ----------------------------------------------------------------- §3.5 tag edits off renew/

def test_feature_redating_another_owners_tag_fails_sunset_p0_7(tmp_path):
    """§3.5: an added tag line paired with a removed one is a tag edit; off renew/ that is FAIL
    (audit P12 / P0-7: a legitimate feature quietly pushes someone else's tag 20 → 89 days out)."""
    r = repo_with(tmp_path / "r", "src/legacy.py", legacy_src(days(20)))
    r.legal_feature("greeting")
    r.write("src/legacy.py", legacy_src(days(89)))
    r.commit("feat: also re-date the legacy tag")
    _, res, out = r.gate("feature/greeting")
    assert res is not None, out
    assert outcome(res, "sunset") == "FAIL", detail(res, "sunset")
    assert "tag edited on a feature/ branch" in detail(res, "sunset").lower()


def test_feature_leaving_the_tag_alone_passes_sunset_p0_7(tmp_path):
    """CONTROL for §3.5: the identical feature that does not touch the foreign tag must PASS —
    the refusal is about editing the tag, not about the tag existing."""
    r = repo_with(tmp_path / "r", "src/legacy.py", legacy_src(days(20)))
    r.legal_feature("greeting")
    _, res, out = r.gate("feature/greeting")
    assert res is not None, out
    assert outcome(res, "sunset") == "PASS", detail(res, "sunset")
    assert outcome(res, "type") == "PASS", detail(res, "type")


# ----------------------------------------------------------------- §3.5 term: added lines vs the tree

def test_preexisting_long_todo_tag_does_not_block_a_chore_rt04(tmp_path):
    """§3.5 (RT-04): the per-kind term applies only to lines added or edited here. A pre-existing
    todo tag 100 days out is under SUNSET_MAX, so it must not freeze an unrelated chore/ change."""
    r = repo_with(tmp_path / "r", "src/legacy.py", legacy_src(days(100), kind="todo"))
    r.branch("chore/readme")
    r.write("README.md", "# project\n\nA docs-only chore.\n")
    r.record("chore", "readme")
    r.commit("chore: readme")
    _, res, out = r.gate("chore/readme")
    assert res is not None, out
    assert outcome(res, "sunset") == "PASS", detail(res, "sunset")
    assert eligible_or_blocked_only_by(res, "masking_ruff NOT_RUN"), res.get("ineligible_reasons")


def test_preexisting_tag_over_sunset_max_still_fails_tree_wide_rt04(tmp_path):
    """CONTROL for RT-04: SUNSET_MAX (180) still applies tree-wide, so a pre-existing tag 200 days
    out blocks the same unrelated chore/ change. Relaxing the term is not disarming the ceiling."""
    r = repo_with(tmp_path / "r", "src/legacy.py", legacy_src(days(200)))
    r.branch("chore/readme")
    r.write("README.md", "# project\n\nA docs-only chore.\n")
    r.record("chore", "readme")
    r.commit("chore: readme")
    _, res, out = r.gate("chore/readme")
    assert res is not None, out
    assert outcome(res, "sunset") == "FAIL", detail(res, "sunset")
    assert "180" in detail(res, "sunset")


def test_newly_added_todo_tag_over_its_term_still_fails_rt04(tmp_path):
    """CONTROL for RT-04: the 30-day todo term still bites on lines ADDED in this change — the
    relaxation is for the tree at BASE only (§3.5)."""
    r = Repo(tmp_path / "r")
    r.branch("test/later")
    r.write("tests/test_later.py",
            "def test_later():\n"
            f"    assert True  # SUNSET {days(100)} todo owner:test-later reason:finish it\n")
    r.record("test", "later")
    r.commit("test: a case with a long todo tag")
    _, res, out = r.gate("test/later")
    assert res is not None, out
    assert outcome(res, "sunset") == "FAIL", detail(res, "sunset")
    assert "30" in detail(res, "sunset")


# ----------------------------------------------------------------- §3.5 grace: once, seven days, filed here

def test_grace_filed_in_the_changes_own_record_passes_p0_8(tmp_path):
    """CONTROL for §3.5 grace: an expired tag newly granted grace:<today>, with a BLOCKED
    SUNSET-EXPIRED line in the change's OWN record and no grace at BASE, is tolerated."""
    r = repo_with(tmp_path / "r", "src/legacy.py", legacy_src(days(-40)))
    r.legal_feature("greeting")
    r.write("src/legacy.py", legacy_src(days(-40), grace=str(TODAY)))
    file_the_grace(r, BLOCKED="SUNSET-EXPIRED: deleting the shim breaks tests/test_core.py")
    r.commit("feat: file the grace")
    _, res, out = r.gate("feature/greeting")
    assert res is not None, out
    assert outcome(res, "sunset") == "PASS", detail(res, "sunset")


def test_grace_filed_only_in_an_older_record_fails_p0_8(tmp_path):
    """§3.5 grace: the filing must be in the change's own record; a BLOCKED SUNSET-EXPIRED line
    sitting in someone else's older, untouched record does not license this change's grace."""
    r = repo_with(tmp_path / "r", "src/legacy.py", legacy_src(days(-40)))
    r.write("docs/changes/chore-old.md",
            "TYPE: chore\nBLOCKED: SUNSET-EXPIRED: deleting the shim breaks tests/test_core.py\n")
    r.commit("chore: an older record that filed the block")
    r.legal_feature("greeting")
    r.write("src/legacy.py", legacy_src(days(-40), grace=str(TODAY)))
    r.commit("feat: claim grace on someone else's filing")
    _, res, out = r.gate("feature/greeting")
    assert res is not None, out
    assert outcome(res, "sunset") == "FAIL", detail(res, "sunset")


def test_second_grace_on_a_tag_that_already_had_one_fails_p0_8(tmp_path):
    """§3.5 grace is once: the tag already carried a grace: at BASE, so re-dating it to today —
    even with a fresh BLOCKED SUNSET-EXPIRED filing — must FAIL (v0.3 renews it forever)."""
    r = repo_with(tmp_path / "r", "src/legacy.py", legacy_src(days(-40), grace=str(days(-3))))
    r.legal_feature("greeting")
    r.write("src/legacy.py", legacy_src(days(-40), grace=str(TODAY)))
    file_the_grace(r, BLOCKED="SUNSET-EXPIRED: deleting the shim breaks tests/test_core.py")
    r.commit("feat: a second grace on the same tag")
    _, res, out = r.gate("feature/greeting")
    assert res is not None, out
    assert outcome(res, "sunset") == "FAIL", detail(res, "sunset")
    assert "grace" in detail(res, "sunset").lower()


# ----------------------------------------------------------------- CMP-16 / EV-10 impossible date

def test_impossible_date_is_a_malformed_tag_not_a_crash_cmp16(tmp_path):
    """§3.5 / CMP-16 / EV-10: `2026-13-45` matches the digit pattern but is not a date; it must be
    reported as a malformed tag (sunset FAIL) with a result written, never an unhandled crash."""
    bad = "def legacy():\n    return 1  # SUNSET 2026-13-45 todo owner:x reason:bad date\n"
    r = repo_with(tmp_path / "r", "src/legacy.py", bad)
    r.branch("chore/readme")
    r.write("README.md", "# project\n\nA docs-only chore.\n")
    r.record("chore", "readme")
    r.commit("chore: readme")
    rc, res, out = r.gate("chore/readme")
    assert res is not None, out  # a result JSON is written even for a hostile tag
    assert "Traceback (most recent call last)" not in out
    assert outcome(res, "sunset") == "FAIL", detail(res, "sunset")
    assert "malformed" in detail(res, "sunset").lower()
    assert rc == 1  # a required check FAILed — not 3 (crashed) and not 0
