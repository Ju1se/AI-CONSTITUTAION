"""Gap-closing tests for the grace conditions (§3.5), the renew field diff (§3.4) and `mocks` (§3.6).

These pin spec clauses that the green v0.4 suite leaves untested: the two halves of the grace date
window, the requirement that a grace refusal *names which condition failed*, the renew fields that
must stay editable, the policy-ref reading of the mock allowlist, the added-lines scope of the mock
scan, and two mock forms listed in §3.6 that no test exercises.

Every refusal below is paired with the nearly identical case that must still pass, so a check that
refused everything could not make this file green. Dates come from `datetime.date.today()`.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from _harness import Repo, detail, outcome

TODAY = dt.date.today()

FEATURE_FIELDS = {
    "WHY": "a shim instead of a rewrite, because callers remain.",
    "SEARCHED": 'rg -n "greet" src/ → 0 hits | NONE-FITS: n/a',
    "TESTS": "python -m pytest -q tests",
}
FILING = "SUNSET-EXPIRED: deleting the shim breaks tests/test_core.py"
REQUESTS_STUB = "def get(url, timeout=None):\n    raise RuntimeError('no network in the fixture')\n"


def days(n: int) -> dt.date:
    return TODAY + dt.timedelta(days=n)


def legacy_src(date: dt.date, grace: str = "", owner: str = "team-b", kind: str = "compat",
               reason: str = "old api") -> str:
    tag = f"# SUNSET {date} {kind} owner:{owner} reason:{reason}"
    if grace:
        tag += f" grace:{grace}"
    return f"def legacy():\n    return 1  {tag}\n"


def repo_with(path: Path, rel: str, content: str) -> Repo:
    """A repo whose BASE (main) already carries `content` at `rel` — a pre-existing tag."""
    r = Repo(path)
    r.write(rel, content)
    r.commit("chore: shim carrying a sunset tag")
    return r


def claim_grace(path: Path, grace: str, base_grace: str = "", file_it: bool = True):
    """A feature that appends `grace:` to an expired tag, optionally filing BLOCKED in its own record."""
    r = repo_with(path, "src/legacy.py", legacy_src(days(-40), grace=base_grace))
    r.legal_feature("greeting")
    r.write("src/legacy.py", legacy_src(days(-40), grace=grace))
    fields = dict(FEATURE_FIELDS)
    if file_it:
        fields["BLOCKED"] = FILING
    r.record("feature", "greeting", **fields)
    r.commit("feat: claim grace on the legacy shim")
    return r.gate("feature/greeting", env={"DEPS_OFFLINE": "1"})


# --------------------------------------------------------------- §3.5 grace: the date window, both ends

def test_grace_dated_in_the_future_fails_sunset_p0_8(tmp_path):
    """§3.5 grace requires `date <= today`: a grace dated three days ahead is not yet in force, so the
    expired tag is not tolerated even though the BLOCKED SUNSET-EXPIRED filing is correct and the tag
    carried no grace at BASE. Its control is the in-window case below (P0-8, audit EV-10).
    """
    ahead = str(days(3))
    _, res, out = claim_grace(tmp_path / "r", ahead)
    assert res is not None, out
    assert outcome(res, "sunset") == "FAIL", detail(res, "sunset")
    d = detail(res, "sunset")
    assert "grace" in d.lower() and ahead in d  # the offending grace date is named


def test_grace_older_than_the_window_fails_sunset_p0_8(tmp_path):
    """§3.5 grace requires `today - date <= SUNSET_GRACE` (7): a grace back-dated ten days has run out,
    so a correctly filed, never-before-graced tag still FAILs. Control: the in-window case below.
    """
    stale = str(days(-10))
    _, res, out = claim_grace(tmp_path / "r", stale)
    assert res is not None, out
    assert outcome(res, "sunset") == "FAIL", detail(res, "sunset")
    d = detail(res, "sunset")
    assert "grace" in d.lower() and ("7" in d or stale in d)  # the window, or the date that left it


def test_grace_inside_the_window_passes_sunset_p0_8(tmp_path):
    """CONTROL for both refusals above: the same change with `grace:<today-2>` satisfies every §3.5
    condition — in force, inside the 7-day window, filed here, not graced at BASE — and must PASS.
    """
    _, res, out = claim_grace(tmp_path / "r", str(days(-2)))
    assert res is not None, out
    assert outcome(res, "sunset") == "PASS", detail(res, "sunset")


def test_grace_refusal_names_which_condition_failed_p0_8(tmp_path):
    """§3.5: "Otherwise FAIL, naming which condition failed." Two changes fail for different reasons and
    the details must not be interchangeable: the unfiled one must point at the record / the BLOCKED
    SUNSET-EXPIRED line (the condition it broke), and the twice-graced one must point at the tag having
    been in grace already — and must NOT claim a missing filing, because it filed correctly (P0-8).
    """
    _, unfiled, out1 = claim_grace(tmp_path / "unfiled", str(TODAY), file_it=False)
    _, second, out2 = claim_grace(tmp_path / "second", str(TODAY), base_grace=str(days(-3)))
    assert unfiled is not None and second is not None, out1 + out2
    assert outcome(unfiled, "sunset") == "FAIL", detail(unfiled, "sunset")
    assert outcome(second, "sunset") == "FAIL", detail(second, "sunset")
    du, ds = detail(unfiled, "sunset").lower(), detail(second, "sunset").lower()
    # §3.5 condition two: "the change's own record (record_path) contains a BLOCKED SUNSET-EXPIRED line".
    assert "blocked sunset-expired" in du or "record" in du
    # §3.5 condition three: the tag "did not already carry a grace: at BASE" — a once-only deferral.
    assert "already" in ds or "once" in ds or "base" in ds
    # The two refusals must be distinguishable: the filed change is not accused of failing to file.
    assert "no blocked sunset-expired" not in ds


# --------------------------------------------------------------- §3.4 what a renew may still change

def price_src(factor: str, date: dt.date, reason: str = "old api", grace: str = "",
              head: str = "def discount(price):") -> str:
    tag = f"# SUNSET {date} compat owner:renew-px reason:{reason}"
    if grace:
        tag += f" grace:{grace}"
    return f"{head}\n    return price * {factor}  {tag}\n"


def renew(r: Repo, content: str, **record_fields: str):
    r.branch("renew/px")
    r.write("src/pricing.py", content)
    r.record("renew", "px", **record_fields)
    r.commit("renew: the pricing shim")
    return r.gate("renew/px", env={"DEPS_OFFLINE": "1"})


def test_renew_changing_only_the_reason_passes_type_p0_6(tmp_path):
    """CONTROL for §3.4: the field diff freezes the code part, `kind` and `owner` — and nothing else.
    A renew that rewrites only `reason:` must leave `type` PASS; without this a verifier that froze
    every field (or the whole line) would pass every §3.4 refusal test and still be wrong (P0-6/P08).
    """
    r = repo_with(tmp_path / "r", "src/pricing.py", price_src("0.9", days(10)))
    _, res, out = renew(r, price_src("0.9", days(10), reason="old api, callers listed in RT-09"))
    assert res is not None, out
    assert outcome(res, "type") == "PASS", detail(res, "type")


def test_renew_appending_only_grace_passes_type_p0_6(tmp_path):
    """CONTROL for §3.4: appending `grace:<today>` to an expired tag (with the BLOCKED SUNSET-EXPIRED
    filing §3.5 requires) changes no frozen field, so `type` must PASS. The grace path must stay open
    on the one branch type that exists to renew tags (P0-6 with §3.5).
    """
    r = repo_with(tmp_path / "r", "src/pricing.py", price_src("0.9", days(-40)))
    _, res, out = renew(r, price_src("0.9", days(-40), grace=str(TODAY)), BLOCKED=FILING)
    assert res is not None, out
    assert outcome(res, "type") == "PASS", detail(res, "type")


def test_renew_pair_with_no_tag_at_all_fails_type_p0_6(tmp_path):
    """§3.4: "both lines must carry a parseable SUNSET tag". An equal-count hunk whose pair carries no
    tag on either side is an ordinary code edit wearing a renew/ branch name, and must FAIL `type` —
    the line-count rule alone would wave it through (P0-6, audit P08).
    """
    r = repo_with(tmp_path / "r", "src/pricing.py", price_src("0.9", days(10)))
    _, res, out = renew(r, price_src("0.9", days(10), head="def discount(price, *, vat=0):"))
    assert res is not None, out
    assert outcome(res, "type") == "FAIL", detail(res, "type")
    assert "vat" in detail(res, "type")  # the untagged line is quoted


# ------------------------------------------------------- §3.6 the allowlist is read at the policy ref

MOCKING_TEST = ('from src import core\n\n\n'
                'def test_value_is_mocked(monkeypatch):\n'
                '    monkeypatch.setattr(core, "value", lambda: 99)\n'
                '    assert core.value() == 99\n')


def mock_feature(r: Repo, test_src: str, slug: str = "mocked", widen: str = ""):
    r.branch(f"feature/{slug}")
    r.write(f"tests/test_{slug}.py", test_src)
    r.commit("test: the mocked path")
    r.write(f"src/{slug}.py", "def run():\n    return 2\n")
    if widen:
        r.append("tests/MOCK_ALLOWLIST", widen)
    r.record("feature", slug, **FEATURE_FIELDS)
    r.commit("feat: the mocked path")
    return r.gate(f"feature/{slug}", env={"DEPS_OFFLINE": "1"})


def test_self_widened_allowlist_does_not_allow_the_mock_m09(tmp_path):
    """§3.6: "allowed when it equals, or starts with, a prefix in `tests/MOCK_ALLOWLIST` **at the policy
    ref**". A change that ships its own widened allowlist adding `src.` must still FAIL `mocks` — the
    check reads the policy ref, not the subject. (The same change also fails protected_files; asserting
    `mocks` specifically is the point, since protection is not what makes the mock illegal.)
    """
    r = Repo(tmp_path / "r")
    _, res, out = mock_feature(r, MOCKING_TEST, widen="src.\n")
    assert res is not None, out
    assert outcome(res, "mocks") == "FAIL", detail(res, "mocks")
    assert "src.core.value" in detail(res, "mocks")


def test_allowlist_widened_at_the_policy_ref_allows_the_mock_m09(tmp_path):
    """CONTROL for the above: the identical mock PASSes once `src.` is in the allowlist *at the policy
    ref*. Together the pair shows the check consults the policy ref's copy, rather than refusing every
    in-repo target no matter what the allowlist says (§3.6).
    """
    r = Repo(tmp_path / "r")
    r.append("tests/MOCK_ALLOWLIST", "src.\n")
    r.commit("policy: widen the allowlist on main")
    _, res, out = mock_feature(r, MOCKING_TEST)
    assert res is not None, out
    assert outcome(res, "mocks") == "PASS", detail(res, "mocks")


# --------------------------------------------------------------- §3.6 the scan's scope is ADDED lines

PREEXISTING_MOCK = ('from unittest.mock import patch\n\n\n'
                    'def test_legacy_mock():\n'
                    '    with patch("src.core.value", return_value=5):\n'
                    '        from src.core import value\n'
                    '        assert value() == 5\n\n\n'
                    'def test_unrelated():\n'
                    '    assert 1 == 1\n')


def edit_unrelated_line(path: Path, base_body: str, new_body: str):
    r = Repo(path)
    r.write("tests/test_legacy.py", base_body)
    r.commit("test: a case merged long ago")
    r.branch("test/tweak")
    r.write("tests/test_legacy.py", new_body)
    r.record("test", "tweak", WHY="a tighter assertion instead of a loose one, because precision.",
             TESTS="python -m pytest -q tests")
    r.commit("test: tighten an unrelated assertion")
    return r.gate("test/tweak", env={"DEPS_OFFLINE": "1"})


def test_mocks_scope_is_added_lines_not_the_whole_file_m09(tmp_path):
    """§3.6: "Scan added lines under tests/ and src/". A non-allowlisted mock merged long ago is not
    this change's defect, so editing an unrelated line of the same file must leave `mocks` PASS.
    Control (second repo): the same edit that *adds* the mock line FAILs, so the PASS is scope, not
    blindness.
    """
    tightened = PREEXISTING_MOCK.replace("assert 1 == 1", "assert 1 + 1 == 2")
    _, res, out = edit_unrelated_line(tmp_path / "pre", PREEXISTING_MOCK, tightened)
    assert res is not None, out
    assert outcome(res, "mocks") == "PASS", detail(res, "mocks")

    clean = PREEXISTING_MOCK.replace('    with patch("src.core.value", return_value=5):\n'
                                     '        from src.core import value\n'
                                     '        assert value() == 5\n',
                                     "    assert True\n")
    _, ctl, out2 = edit_unrelated_line(tmp_path / "adds", clean, PREEXISTING_MOCK)
    assert ctl is not None, out2
    assert outcome(ctl, "mocks") == "FAIL", detail(ctl, "mocks")
    assert "src.core.value" in detail(ctl, "mocks")


# --------------------------------------------------------------- §3.6 two listed forms with no test

DELATTR_AND_ATTR_PATCH = ('from unittest.mock import patch\n\n'
                          'from src import core\n\n\n'
                          'def test_delattr_form(monkeypatch):\n'
                          '    monkeypatch.delattr(core, "value")\n'
                          '    assert not hasattr(core, "value")\n\n\n'
                          'def test_attribute_expression_form():\n'
                          '    with patch(core.value):\n'
                          '        pass\n')

ALLOWLISTED_SAME_FORMS = ('import time\nfrom unittest.mock import patch\n\n'
                          'import requests\n\n\n'
                          'def test_delattr_form(monkeypatch):\n'
                          '    monkeypatch.delattr(time, "sleep", raising=False)\n'
                          '    assert True\n\n\n'
                          'def test_attribute_expression_form():\n'
                          '    with patch(requests.get):\n'
                          '        pass\n')


def test_delattr_and_attribute_expression_patch_are_both_named_m10(tmp_path):
    """§3.6 lists `monkeypatch.delattr` and `patch(obj.attr)` among the forms the scan must see. Both
    target src.core.value here, so both must be named in the FAIL detail — two findings, not one: a
    verifier that handled only `setattr` and only the string form would still FAIL the check on the
    other line and look correct (M10 / CMP-11).
    """
    r = Repo(tmp_path / "r")
    _, res, out = mock_feature(r, DELATTR_AND_ATTR_PATCH, slug="forms")
    assert res is not None, out
    assert outcome(res, "mocks") == "FAIL", detail(res, "mocks")
    named = [ln for ln in detail(res, "mocks").splitlines() if "src.core.value" in ln]
    assert len(named) >= 2, detail(res, "mocks")


def test_the_same_two_forms_on_allowlisted_targets_pass_m10(tmp_path):
    """CONTROL for the above: `monkeypatch.delattr(time, "sleep")` and `patch(requests.get)` resolve,
    through the file's own imports, to allowlisted I/O boundaries and must PASS. Recognising a form is
    not the same as refusing it (§3.6, CMP-05).
    """
    r = Repo(tmp_path / "r")
    r.write("requests.py", REQUESTS_STUB)
    r.commit("chore: local http stub for the fixture")
    _, res, out = mock_feature(r, ALLOWLISTED_SAME_FORMS, slug="okforms")
    assert res is not None, out
    assert outcome(res, "mocks") == "PASS", detail(res, "mocks")
