"""v0.4 regression tests for the boundary-masking cluster (spec §3.2 masking_markers, §3.3 masking_ruff).

Written from `scratchpad/v04-spec.md` before the implementation exists: most of these must FAIL against the
v0.3 verifier. Findings: P0-1 (a `# boundary:` note launders every forbidden marker), M05 (the promised
handler body is never checked), P0-4 / M06 / M07 (masking scans only `src/` and `tests/`), P0-5 / M08
(`tests/` is never linted), P0-2 (candidate ruff configuration disables its own lint).
"""
from __future__ import annotations

import datetime as dt

import pytest
from _harness import RUFF, Repo, detail, outcome

TODAY = dt.date.today()

SANCTIONED = ("    except Exception as e:  # noqa: BLE001  # boundary: returns Failure so the caller "
              "must match it\n")


def feature_with_src(r: Repo, src_body: str, slug: str = "greeting") -> None:
    """The compliant feature shape (test committed first), with `src_body` as the implementation file."""
    r.branch(f"feature/{slug}")
    r.write(f"tests/test_{slug}.py",
            f"from src.{slug} import greet\n\n\ndef test_greet():\n    assert greet('a') == 'hello, a'\n")
    r.commit("test: greet")
    r.write(f"src/{slug}.py", src_body)
    r.record("feature", slug, WHY="an f-string instead of concatenation, because readability.",
             SEARCHED='rg -n "greet" src/ → 0 hits | NONE-FITS: n/a',
             TESTS="python -m pytest -q tests")
    r.commit("feat: greet")


def guarded_src(handler_body: str, preamble: str = "") -> str:
    """A src/ module whose only interesting line is a `# boundary:` catch-all with the given body."""
    return (preamble + "class Failure(Exception):\n    pass\n\n\ndef greet(name):\n"
            "    return 'hello, ' + name\n\n\ndef guarded(fn):\n    try:\n        return fn()\n"
            + SANCTIONED + handler_body)


# --------------------------------------------------------------- §3.2 P0-1: the boundary note launders nothing

def test_boundary_note_does_not_exempt_a_skipped_test_p0_1(tmp_path):
    """§3.2: a `@pytest.mark.skip` is never exempted by a boundary note, so the change must be refused."""
    r = Repo(tmp_path / "r")
    r.branch("feature/greeting")
    r.write("tests/test_greeting.py",
            "import pytest\n\nfrom src.greeting import greet\n\n\n"
            '@pytest.mark.skip(reason="later")  # boundary: not a crash barrier at all\n'
            "def test_greet():\n    assert greet('a') == 'TOTALLY WRONG'\n")
    r.commit("test: greet")
    r.write("src/greeting.py", "def greet(name):\n    return 'hello, ' + name\n")
    r.record("feature", "greeting", WHY="an f-string instead of concatenation, because readability.",
             SEARCHED='rg -n "greet" src/ → 0 hits | NONE-FITS: n/a', TESTS="python -m pytest -q tests")
    r.commit("feat: greet")
    rc, res, _ = r.gate("feature/greeting")
    assert outcome(res, "masking_markers") == "FAIL"
    assert "tests/test_greeting.py" in detail(res, "masking_markers")
    assert res["merge_eligible"] is False and rc != 0


@pytest.mark.parametrize("marker", ["# type: ignore", "# pragma: no cover", "# noqa"])
def test_boundary_note_does_not_exempt_other_markers_p0_1(tmp_path, marker):
    """§3.2: only `except ...: # noqa: BLE001 # boundary: <text>` is exempt; every other marker still FAILs."""
    r = Repo(tmp_path / "r")
    feature_with_src(r, "def greet(name):\n"
                        f"    prefix = 'hello, '  {marker}  # boundary: whatever\n"
                        "    return prefix + name\n")
    _, res, _ = r.gate("feature/greeting")
    assert outcome(res, "masking_markers") == "FAIL", f"{marker} was exempted by a boundary note"
    assert "src/greeting.py" in detail(res, "masking_markers")


def test_boundary_note_does_not_exempt_shell_masking_p0_1(tmp_path):
    """§3.2: `|| true` in a .sh file carrying `# noqa  # boundary:` is not a sanctioned crash barrier."""
    r = Repo(tmp_path / "r")
    r.branch("test/migrations")
    r.write("tests/run_migrations.sh", "#!/bin/sh\nmigrate || true  # noqa  # boundary: x\n")
    r.record("test", "migrations", WHY="a shell helper instead of a fixture, because the tool is external.",
             TESTS="sh tests/run_migrations.sh")
    r.commit("test: migration helper")
    _, res, _ = r.gate("test/migrations")
    assert outcome(res, "masking_markers") == "FAIL"
    assert "tests/run_migrations.sh" in detail(res, "masking_markers")


def test_sanctioned_boundary_shape_still_passes_p0_1(tmp_path):
    """CONTROL, §3.2: the one authorized shape — a typed-failure return — must keep passing."""
    r = Repo(tmp_path / "r")
    feature_with_src(r, guarded_src("        return Failure(str(e))\n"))
    _, res, _ = r.gate("feature/greeting")
    assert outcome(res, "masking_markers") == "PASS", detail(res, "masking_markers")
    assert "boundary exemption" in detail(res, "masking_markers")


@pytest.mark.parametrize("body,preamble", [
    ("        pass\n", ""),
    ("        logging.warning(e)\n        return None\n", "import logging\n\n\n"),
])
def test_boundary_body_must_return_or_raise_m05(tmp_path, body, preamble):
    """§3.2 / M05: the exemption holds only when the handler body returns the typed failure it promises."""
    r = Repo(tmp_path / "r")
    feature_with_src(r, guarded_src(body, preamble))
    _, res, _ = r.gate("feature/greeting")
    assert outcome(res, "masking_markers") == "FAIL", "a swallowing boundary body kept its exemption"
    assert "src/greeting.py" in detail(res, "masking_markers")


def test_well_formed_masks_sunset_tag_still_exempts_p0_1(tmp_path):
    """CONTROL, §3.2: a well-formed SUNSET tag remains an exemption, unchanged from v0.3."""
    r = Repo(tmp_path / "r")
    soon = TODAY + dt.timedelta(days=20)
    feature_with_src(r, "def greet(name):\n"
                        f"    prefix = 'hello, '  # noqa  # SUNSET {soon} masks owner:feature-greeting "
                        "reason:the linter trips on the shim\n"
                        "    return prefix + name\n")
    _, res, _ = r.gate("feature/greeting")
    assert outcome(res, "masking_markers") == "PASS", detail(res, "masking_markers")


# --------------------------------------------------- §3.2 P0-4 / M06 / M07: every .py and .sh path is scanned

def test_chore_tooling_and_root_conftest_are_scanned_p0_4(tmp_path):
    """§3.2: masking scans every .py/.sh path, so tools/ and a root conftest.py can no longer hide it."""
    r = Repo(tmp_path / "r")
    r.branch("chore/deploy-tools")
    r.write("tools/deploy.sh", "#!/bin/sh\nmigrate || true\nstatus 2>/dev/null\n")
    r.write("tools/helper.py", "def load(p):\n    try:\n        return open(p).read()\n"
                               "    except Exception:\n        pass\n")
    r.write("conftest.py", "import pytest\n\n\n@pytest.fixture(autouse=True)\ndef _quiet():\n"
                           "    try:\n        yield\n    except Exception:\n        pass\n")
    r.record("chore", "deploy-tools", WHY="a shell deploy helper instead of a Makefile target, because CI calls it.",
             TESTS="sh -n tools/deploy.sh")
    r.commit("chore: deploy tooling")
    _, res, _ = r.gate("chore/deploy-tools")
    d = detail(res, "masking_markers")
    assert outcome(res, "masking_markers") == "FAIL"
    assert "tools/deploy.sh" in d and "tools/helper.py" in d and "conftest.py" in d


def test_docs_only_chore_still_passes_masking_p0_4(tmp_path):
    """CONTROL, §3.2: widening the scan must not refuse a chore/ change that touches no code."""
    r = Repo(tmp_path / "r")
    r.branch("chore/notes")
    r.write("docs/notes.md", "# notes\n\nA `|| true` and an `except Exception: pass` quoted in prose.\n")
    r.record("chore", "notes", WHY="a docs note instead of a code comment, because it is process guidance.",
             TESTS="none: documentation only")
    r.commit("chore: notes")
    _, res, _ = r.gate("chore/notes")
    assert outcome(res, "masking_markers") == "PASS", detail(res, "masking_markers")


def test_test_branch_swallowing_its_assertions_fails_p0_5(tmp_path):
    """§3.2 / M08: a test/ change that wraps its assertions in `except AssertionError: pass` is masking."""
    r = Repo(tmp_path / "r")
    r.branch("test/swallow")
    r.write("tests/test_swallow.py",
            "from src.core import value\n\n\ndef test_value():\n    try:\n        assert value() == 2\n"
            "    except AssertionError:\n        pass\n")
    r.record("test", "swallow", WHY="a second assertion instead of a new module, because it adjudicates value().",
             TESTS="python -m pytest -q tests")
    r.commit("test: swallow")
    _, res, _ = r.gate("test/swallow")
    assert outcome(res, "masking_markers") == "FAIL"
    assert "tests/test_swallow.py" in detail(res, "masking_markers")


# ------------------------------------------------------------------------------------ §3.3 masking_ruff

BLIND_HANDLER = ("import logging\n\n\ndef load(p):\n    try:\n        return open(p).read()\n"
                 "    except Exception as e:\n        logging.warning(e)\n        return None\n")


@pytest.mark.skipif(not RUFF, reason="ruff is not installed; masking_ruff is NOT_RUN here")
def test_masking_ruff_lints_tests_too_p0_5(tmp_path):
    """§3.3: ruff lints tests/ (and scripts/, tools/), not only src/, so a blind handler in a test FAILs."""
    r = Repo(tmp_path / "r")
    r.branch("test/blind")
    r.write("tests/test_blind.py",
            "import logging\n\nfrom src.core import value\n\n\ndef test_value():\n    try:\n"
            "        assert value() == 1\n    except Exception as e:\n        logging.warning(e)\n")
    r.record("test", "blind", WHY="a guarded assertion instead of a plain one, because the import is flaky.",
             TESTS="python -m pytest -q tests")
    r.commit("test: blind handler")
    _, res, _ = r.gate("test/blind")
    assert outcome(res, "masking_ruff") == "FAIL", detail(res, "masking_ruff")
    assert "tests/test_blind.py" in detail(res, "masking_ruff")


@pytest.mark.skipif(not RUFF, reason="ruff is not installed; masking_ruff is NOT_RUN here")
def test_candidate_ruff_config_no_longer_silences_the_lint_p0_2(tmp_path):
    """§3.3 / §3.1: ruff runs `--isolated`, so a candidate pyproject [tool.ruff] ignore table is not read."""
    r = Repo(tmp_path / "r")
    feature_with_src(r, BLIND_HANDLER + "\n\ndef greet(name):\n    return 'hello, ' + name\n")
    r.write("pyproject.toml",
            '[tool.ruff.lint]\nignore = ["E722", "BLE001", "S110", "S112", "S113"]\n\n'
            '[tool.ruff.lint.per-file-ignores]\n"src/*" = ["E722", "BLE001", "S110", "S112", "S113"]\n')
    r.commit("feat: ruff config")
    _, res, _ = r.gate("feature/greeting", env={"DEPS_OFFLINE": "1"})
    assert outcome(res, "masking_ruff") == "FAIL", detail(res, "masking_ruff")
    assert "src/greeting.py" in detail(res, "masking_ruff")


def test_clean_change_still_passes_masking_ruff(tmp_path):
    """CONTROL, §3.3: a clean feature must pass masking_ruff — NOT_RUN only when ruff is absent."""
    r = Repo(tmp_path / "r")
    r.legal_feature()
    _, res, _ = r.gate("feature/greeting")
    assert outcome(res, "masking_ruff") == ("PASS" if RUFF else "NOT_RUN"), detail(res, "masking_ruff")
    assert outcome(res, "masking_markers") == "PASS", detail(res, "masking_markers")
