"""v0.4 regression tests: the candidate must not control the tree the gate reads as evidence.

Written from `v04-spec.md` §1.1 (`export_integrity`), §1.2 (`harness_integrity`), §1.3 (`test_inventory`)
and §3.1 (tool isolation), before the implementation exists. Every refusal here is paired with the
nearly identical legitimate case, so a check that refuses everything cannot look correct.
"""
from __future__ import annotations

from _harness import RUFF, Repo, detail, eligible_or_blocked_only_by, outcome

NEW_TEST = "from src.core import value\n\n\ndef test_is_int():\n    assert isinstance(value(), int)\n"
BROKEN_SRC = "def value():\n    return 2\n"  # tests/test_core.py asserts value() == 1


def broken_fix(r: Repo, slug: str = "value", extra: dict[str, str] | None = None) -> None:
    """A fix/ branch that adds one passing test, ships `extra`, and breaks the frozen tests/test_core.py.

    The honest verdict for every scenario built on this helper is: the suite is red, the merge is blocked.
    """
    r.branch(f"fix/{slug}")
    r.write("tests/test_value_two.py", NEW_TEST)
    for rel, body in (extra or {}).items():
        r.write(rel, body)
    r.commit("test: value is an int")  # tests only: never shares a commit with src/
    r.write("src/core.py", BROKEN_SRC)
    r.record("fix", slug, WHY="2 instead of 1, because the spec changed.",
             TESTS="python -m pytest -q tests")
    r.commit("fix: value")


def second_frozen_test(r: Repo) -> None:
    """Add a second committed test on main, so a later deletion can lose an id without emptying tests/."""
    r.write("tests/test_extra.py", "from src.core import value\n\n\ndef test_extra():\n    assert value() > 0\n")
    r.commit("test: a second frozen test")


# ----------------------------------------------------------------------------- the clean control

def test_clean_feature_keeps_the_evidence_tree_checks_passing(tmp_path):
    """§1.1/§1.2/§1.3: on a compliant change the three new required checks PASS and state their counts."""
    r = Repo(tmp_path / "r")
    r.legal_feature()
    rc, result, out = r.gate("feature/greeting")
    assert result is not None, out
    assert outcome(result, "export_integrity") == "PASS", detail(result, "export_integrity")
    assert outcome(result, "harness_integrity") == "PASS", detail(result, "harness_integrity")
    assert outcome(result, "test_inventory") == "PASS", detail(result, "test_inventory")
    assert any(ch.isdigit() for ch in detail(result, "export_integrity"))  # §1.1: "paths verified"
    assert any(ch.isdigit() for ch in detail(result, "test_inventory"))    # §1.3: both counts
    if RUFF:
        assert rc == 0 and result["merge_eligible"] is True, out
    else:
        assert eligible_or_blocked_only_by(result, "masking_ruff NOT_RUN")


# ----------------------------------------------------------------------------- CR-01 export-ignore

def test_export_ignore_removes_a_frozen_test_cr01(tmp_path):
    """§1.1/§1.3: a committed `export-ignore` deletes the frozen test from the gate's own evidence tree."""
    r = Repo(tmp_path / "r")
    broken_fix(r, extra={"tests/.gitattributes": "test_core.py export-ignore\n"})
    _rc, result, out = r.gate("fix/value")
    assert result is not None, out
    assert outcome(result, "export_integrity") == "FAIL", detail(result, "export_integrity")
    assert "tests/test_core.py" in detail(result, "export_integrity")
    assert outcome(result, "test_inventory") == "FAIL", detail(result, "test_inventory")
    assert "test_core" in detail(result, "test_inventory")  # the lost id is named
    assert result["merge_eligible"] is False


def test_export_ignore_line_is_refused_by_harness_integrity_cr01(tmp_path):
    """§1.2: any added `.gitattributes` line containing export-ignore is refused off a policy/ branch."""
    r = Repo(tmp_path / "r")
    broken_fix(r, extra={"tests/.gitattributes": "test_core.py export-ignore\n"})
    _rc, result, out = r.gate("fix/value")
    assert result is not None, out
    assert outcome(result, "harness_integrity") == "FAIL", detail(result, "harness_integrity")
    assert "export-ignore" in detail(result, "harness_integrity")
    assert ".gitattributes" in detail(result, "harness_integrity")
    assert result["merge_eligible"] is False


# ----------------------------------------------------------------------------- CR-02 candidate pytest config

def test_addopts_ignore_cannot_hide_the_red_suite_cr02(tmp_path):
    """§1.2/§3.1: a candidate `addopts = --ignore=...` is refused, and isolation makes unit_tests see red."""
    r = Repo(tmp_path / "r")
    broken_fix(r, extra={"pyproject.toml":
                         '[tool.pytest.ini_options]\naddopts = "--ignore=tests/test_core.py"\n'})
    _rc, result, out = r.gate("fix/value")
    assert result is not None, out
    assert outcome(result, "harness_integrity") == "FAIL", detail(result, "harness_integrity")
    assert "addopts" in detail(result, "harness_integrity")
    assert outcome(result, "unit_tests") == "FAIL", detail(result, "unit_tests")
    assert result["merge_eligible"] is False


def test_addopts_k_filter_cannot_hide_the_red_suite_cr02(tmp_path):
    """§3.1: `--override-ini=addopts=` neutralizes a `-k` deselection of the frozen test too.

    Isolation restores the id, so test_inventory is silent here; harness_integrity and unit_tests carry it.
    """
    r = Repo(tmp_path / "r")
    broken_fix(r, extra={"pyproject.toml":
                         "[tool.pytest.ini_options]\naddopts = '-k \"not test_value or test_is_int\"'\n"})
    _rc, result, out = r.gate("fix/value")
    assert result is not None, out
    assert outcome(result, "harness_integrity") == "FAIL", detail(result, "harness_integrity")
    assert "addopts" in detail(result, "harness_integrity")
    assert outcome(result, "unit_tests") == "FAIL", detail(result, "unit_tests")
    assert result["merge_eligible"] is False


# ----------------------------------------------------------------------------- CR-03 reporting hooks

def test_conftest_makereport_hook_is_refused_cr03(tmp_path):
    """§1.2: a conftest.py defining pytest_runtest_makereport is refused, naming the denylisted hook."""
    r = Repo(tmp_path / "r")
    hook = ("import pytest\n\n\n@pytest.hookimpl(hookwrapper=True)\n"
            "def pytest_runtest_makereport(item, call):\n"
            "    report = (yield).get_result()\n"
            "    if report.outcome == 'failed':\n"
            "        report.outcome = 'passed'\n")
    broken_fix(r, extra={"tests/conftest.py": hook})
    _rc, result, out = r.gate("fix/value")
    assert result is not None, out
    assert outcome(result, "harness_integrity") == "FAIL", detail(result, "harness_integrity")
    assert "pytest_runtest_makereport" in detail(result, "harness_integrity")
    assert result["merge_eligible"] is False


def test_ordinary_conftest_fixture_passes_and_states_the_scope_limit_cr03(tmp_path):
    """§1.2 last paragraph: a conftest.py with no denylisted hook PASSes, and the PASS states the residue."""
    r = Repo(tmp_path / "r")
    r.legal_feature()
    r.write("tests/conftest.py", "import pytest\n\n\n@pytest.fixture\ndef sample():\n    return 1\n")
    r.commit("test: a shared fixture")
    _rc, result, out = r.gate("feature/greeting")
    assert result is not None, out
    assert outcome(result, "harness_integrity") == "PASS", detail(result, "harness_integrity")
    said = detail(result, "harness_integrity").lower()
    assert "not detected" in said and "audit" in said  # the BREAK step is the compensating control
    assert outcome(result, "test_inventory") == "PASS", detail(result, "test_inventory")


# ----------------------------------------------------------------------------- P0-2 file-level suppression

def test_file_level_ruff_noqa_header_is_refused_p0_2(tmp_path):
    """§1.2: an added `# ruff: noqa` file header suppresses the linter wholesale and is refused."""
    r = Repo(tmp_path / "r")
    r.legal_feature()
    r.write("src/shim.py", "# ruff: noqa\n\n\ndef shim():\n    return 1\n")
    r.commit("feat: shim")
    _rc, result, out = r.gate("feature/greeting")
    assert result is not None, out
    assert outcome(result, "harness_integrity") == "FAIL", detail(result, "harness_integrity")
    assert "ruff: noqa" in detail(result, "harness_integrity")
    assert result["merge_eligible"] is False


# ----------------------------------------------------------------------------- CR-04 inventory, not filenames

def test_inert_test_file_is_not_a_collected_test_cr04(tmp_path):
    """§1.3: a feature adding only an inert tests/helpers.py collects no new id and must FAIL."""
    r = Repo(tmp_path / "r")
    r.branch("feature/sentinel")
    r.write("tests/helpers.py", "SENTINEL = 1\n")
    r.commit("test: helper module")
    r.write("src/sentinel.py", "def sentinel():\n    return 1\n")
    r.record("feature", "sentinel", WHY="a constant instead of a literal, because reuse.",
             SEARCHED='rg -n "sentinel" src/ → 0 hits | NONE-FITS: n/a', TESTS="python -m pytest -q tests")
    r.commit("feat: sentinel")
    _rc, result, out = r.gate("feature/sentinel")
    assert result is not None, out
    assert outcome(result, "test_inventory") == "FAIL", detail(result, "test_inventory")
    said = detail(result, "test_inventory").lower()
    assert "collected" in said and ("new" in said or "at least one" in said), said
    assert result["merge_eligible"] is False


# ----------------------------------------------------------------------------- refactor: the sets must be equal

def test_refactor_that_changes_no_test_ids_passes_cr04(tmp_path):
    """§1.3: for refactor the id sets must be equal — a behaviour-preserving change PASSes."""
    r = Repo(tmp_path / "r")
    r.branch("refactor/value")
    r.write("src/core.py", "def value():\n    result = 1\n    return result\n")
    r.record("refactor", "value", TESTS="python -m pytest -q tests")
    r.commit("refactor: name the result")
    rc, result, out = r.gate("refactor/value")
    assert result is not None, out
    assert outcome(result, "test_inventory") == "PASS", detail(result, "test_inventory")
    assert outcome(result, "export_integrity") == "PASS", detail(result, "export_integrity")
    if RUFF:
        assert rc == 0 and result["merge_eligible"] is True, out
    else:
        assert eligible_or_blocked_only_by(result, "masking_ruff NOT_RUN")


def test_refactor_that_loses_a_test_id_fails_cr01(tmp_path):
    """§1.3: an id collected at BASE and absent at SUBJECT is a FAIL naming the lost id, however it vanished."""
    r = Repo(tmp_path / "r")
    second_frozen_test(r)
    r.branch("refactor/value")
    r.rm("tests/test_extra.py")
    r.record("refactor", "value", TESTS="python -m pytest -q tests")
    r.commit("refactor: drop a test")
    _rc, result, out = r.gate("refactor/value")
    assert result is not None, out
    assert outcome(result, "test_inventory") == "FAIL", detail(result, "test_inventory")
    assert "test_extra" in detail(result, "test_inventory")
    assert result["merge_eligible"] is False
