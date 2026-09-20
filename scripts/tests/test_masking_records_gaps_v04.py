"""Gap-closing tests for masking (spec §3.2 / §3.3) and records / audit-select (§3.9 / §3.10).

The v0.4 suite is green, but reviewers of it named requirements of `v04-spec.md` that no test pins down.
Each test here states, in its docstring, the spec line it pins and the audit finding it traces to, and
each refusal is paired with the control that must still PASS, so a check that refuses everything cannot
look correct. Assertions are on the result JSON — the outcome of the *specific* check plus a semantic
fragment (a path, a scope, a record) the spec fixes — never on incidental wording.

Gaps closed: the scanned-path set of masking_markers (M06 scripts/, M07 tools/); the exact SHAPE of the
`# boundary:` exemption (P0-1); the two marker kinds a boundary note may not launder that no other test
covers (P0-1); the lint scope of masking_ruff (M11 scripts/ and tools/) and its no-Python-at-all branch
(M08); the two untested record-selection branches (RT-08); and the negative control of audit-select,
without which "selected" proves nothing (P0-10 / CR-05).
"""
from __future__ import annotations

import pytest
from _harness import RUFF, Repo, detail, outcome

# The one shape §3.2 sanctions: the whole line, `# noqa: BLE001` and a non-empty boundary note.
SANCTIONED = "    except Exception as e:  # noqa: BLE001  # boundary: returns Failure for the caller\n"
RECORD = {"WHY": "an f-string instead of concatenation, because readability.",
          "SEARCHED": 'rg -n "greet" src/ → 0 hits | NONE-FITS: n/a',
          "TESTS": "python -m pytest -q tests"}


def chore(r: Repo, files: dict[str, str], slug: str = "tooling") -> tuple:
    """A chore branch that commits `files` with its own record, then runs the gate."""
    r.branch(f"chore/{slug}")
    for rel, body in files.items():
        r.write(rel, body)
    r.record("chore", slug, WHY="a helper script instead of a make target, because CI shells out to it.",
             TESTS="sh -n scripts/deploy.sh")
    r.commit(f"chore: {slug}")
    return r.gate(f"chore/{slug}", env={"DEPS_OFFLINE": "1"})


def feature(r: Repo, src_body: str, test_body: str | None = None, slug: str = "greeting") -> tuple:
    """The compliant feature shape — test committed first, then the implementation and the record."""
    r.branch(f"feature/{slug}")
    r.write(f"tests/test_{slug}.py", test_body or
            f"from src.{slug} import greet\n\n\ndef test_greet():\n    assert greet('a') == 'hello, a'\n")
    r.commit("test: greet")
    r.write(f"src/{slug}.py", src_body)
    r.record("feature", slug, **RECORD)
    r.commit("feat: greet")
    return r.gate(f"feature/{slug}", env={"DEPS_OFFLINE": "1"})


def guarded(handler_line: str, body: str) -> str:
    """A src/ module whose only interesting lines are a catch-all handler and its body."""
    return ("class Failure(Exception):\n    pass\n\n\ndef greet(name):\n    return 'hello, ' + name\n\n\n"
            "def guarded(fn):\n    try:\n        return fn()\n" + handler_line + body)


# ------------------------------------------------------- §3.2 scanned paths: scripts/ and tools/ (M06, M07)

def test_scripts_and_tools_are_scanned_for_masking_m06_m07(tmp_path):
    """§3.2 ("every added line in a file whose name ends .py, .sh or .bash, anywhere in the repository …
    In particular scripts/, tools/"): v0.2 scanned scripts/, v0.3 dropped it (audit M06) and never
    scanned tools/ (M07). A chore change hiding a swallowed handler, a `|| true` and a bare `# noqa`
    in those two directories must FAIL masking_markers, naming each file."""
    r = Repo(tmp_path / "r")
    _, res, _ = chore(r, {
        "scripts/helper.py": "def load(p):\n    try:\n        return open(p).read()\n"
                             "    except Exception:\n        pass\n",
        "scripts/deploy.sh": "#!/bin/sh\nmigrate || true\n",
        "tools/verify.py": "def verify(rows):\n    total = sum(rows)  # noqa\n    return total\n",
    })
    assert res is not None
    assert outcome(res, "masking_markers") == "FAIL", detail(res, "masking_markers")
    d = detail(res, "masking_markers")
    for path in ("scripts/helper.py", "scripts/deploy.sh", "tools/verify.py"):
        assert path in d, f"{path} was not scanned: {d}"


def test_clean_scripts_and_tools_still_pass_masking_m06_m07(tmp_path):
    """CONTROL for the test above, §3.2: widening the scan back to scripts/ and tools/ must not refuse
    ordinary tooling — a handler that re-raises, a shell script that does not mask, plain Python."""
    r = Repo(tmp_path / "r")
    _, res, _ = chore(r, {
        "scripts/helper.py": "def load(p):\n    try:\n        return open(p).read()\n"
                             "    except OSError as e:\n        raise RuntimeError(p) from e\n",
        "scripts/deploy.sh": "#!/bin/sh\nset -eu\nmigrate\n",
        "tools/verify.py": "def verify(rows):\n    total = sum(rows)\n    return total\n",
    })
    assert res is not None
    assert outcome(res, "masking_markers") == "PASS", detail(res, "masking_markers")


# ------------------------------------------------------------- §3.2 the SHAPE of the exemption (P0-1, M05)

@pytest.mark.parametrize("name,handler,body,expect", [
    ("sanctioned", SANCTIONED, "        return Failure(str(e))\n", "PASS"),
    ("no_noqa", "    except Exception:  # boundary: the process boundary\n", "        pass\n", "FAIL"),
    ("empty_note", "    except Exception as e:  # noqa: BLE001  # boundary:\n",
     "        return Failure(str(e))\n", "FAIL"),
])
def test_only_the_full_boundary_shape_is_exempt_p0_1(tmp_path, name, handler, body, expect):
    """§3.2 ("the exemption applies only to a line matching, as a whole,
    `except <expr>:  # noqa: BLE001  # boundary: <non-empty text>` … Any other line carrying
    `# boundary:` is not exempt"). An `except` line with a boundary note but no `# noqa: BLE001` keeps
    no exemption, so its swallowing body is still refused; a `# boundary:` with nothing after it is not
    a note at all, so the `# noqa` on that line is an unpriced suppression. The first case is the
    control: the whole shape, with a terminating body, must keep PASSing. Audit P0-1 (a boundary note
    laundering anything), M05 (the body is the other half of the shape)."""
    r = Repo(tmp_path / "r")
    _, res, _ = feature(r, guarded(handler, body))
    assert res is not None
    assert outcome(res, "masking_markers") == expect, f"{name}: {detail(res, 'masking_markers')}"
    if expect == "FAIL":
        assert "src/greeting.py" in detail(res, "masking_markers")


# ------------------------------------------- §3.2 the marker kinds no other test covers: xfail, pylint (P0-1)

@pytest.mark.parametrize("name,src,test,expect", [
    ("xfail", "def greet(name):\n    return 'hello, ' + name\n",
     "import pytest\n\nfrom src.greeting import greet\n\n\n"
     '@pytest.mark.xfail(reason="the upstream API is down")  # boundary: not a crash barrier\n'
     "def test_greet():\n    assert greet('a') == 'TOTALLY WRONG'\n", "FAIL"),
    ("pylint", "def greet(name):\n    prefix = 'hello, '  # pylint: disable=broad-except  # boundary: x\n"
               "    return prefix + name\n", None, "FAIL"),
    ("plain_comment", "def greet(name):\n    prefix = 'hello, '  # the layer boundary lives here\n"
                      "    return prefix + name\n", None, "PASS"),
])
def test_boundary_note_launders_neither_xfail_nor_pylint_disable_p0_1(tmp_path, name, src, test, expect):
    """§3.2 ("A @pytest.mark.skip, @xfail, # type: ignore, # pragma: no cover, # pylint: disable or a
    bare # noqa is never exempted by a boundary note"). The other four kinds are pinned by
    test_masking_v04.py; `@pytest.mark.xfail` and `# pylint: disable=` are not. The third case is the
    control: an ordinary added comment that merely says the word boundary is not a marker at all.
    Audit P0-1."""
    r = Repo(tmp_path / "r")
    _, res, _ = feature(r, src, test)
    assert res is not None
    assert outcome(res, "masking_markers") == expect, f"{name}: {detail(res, 'masking_markers')}"
    if expect == "FAIL":
        assert ("tests/test_greeting.py" if name == "xfail" else "src/greeting.py") \
            in detail(res, "masking_markers")


# --------------------------------------------------------------- §3.3 the lint scope of masking_ruff (M11)

@pytest.mark.skipif(not RUFF, reason="ruff is not installed; masking_ruff is NOT_RUN here")
@pytest.mark.parametrize("name,handler,expect", [
    ("blind", "    except Exception as e:\n        print(e)\n        return None\n", "FAIL"),
    ("typed", "    except OSError as e:\n        raise RuntimeError(p) from e\n", "PASS"),
])
def test_masking_ruff_lints_tools_too_m11(tmp_path, name, handler, expect):
    """§3.3 ("lint every directory that exists at the subject among src/, scripts/, tools/, tests/").
    A blind `except Exception` handler in tools/helper.py on a chore change must FAIL masking_ruff —
    an implementation that hard-codes src/ and tests/ reports it clean. masking_markers does not see
    this handler (its body logs rather than swallows), so the refusal can only come from the widened
    lint scope. The typed case is the control. Audit M11 / P0-5."""
    r = Repo(tmp_path / "r")
    _, res, _ = chore(r, {"tools/helper.py": "def load(p):\n    try:\n        return open(p).read()\n"
                                             + handler}, slug="tools")
    assert res is not None
    assert outcome(res, "masking_markers") == "PASS", detail(res, "masking_markers")
    assert outcome(res, "masking_ruff") == expect, detail(res, "masking_ruff")
    if expect == "FAIL":
        assert "tools/helper.py" in detail(res, "masking_ruff")


@pytest.mark.skipif(not RUFF, reason="ruff is not installed; masking_ruff is NOT_RUN here")
def test_no_python_at_all_passes_masking_ruff_stating_the_scope_m08(tmp_path):
    """§3.3 ("No Python at all at the subject → PASS stating that scope"). The repository is built
    without the src/ and tests/ baseline and the kit's own scripts/ is removed, so not one of the four
    lint directories exists; a docs-only change there must PASS — not ERROR on an empty ruff argv, and
    not PASS silently: the detail has to name the scope that was looked for. Audit M08."""
    r = Repo(tmp_path / "r", baseline=False)
    r.branch("chore/notes")
    r.rm("scripts")
    r.rm("tests")
    r.write("docs/notes.md", "# notes\n\nProse only: `|| true` and `except Exception: pass` as examples.\n")
    r.record("chore", "notes", WHY="a docs note instead of a code comment, because it is process guidance.",
             TESTS="none: documentation only")
    r.commit("chore: notes in a repository with no Python")
    _, res, _ = r.gate("chore/notes", env={"DEPS_OFFLINE": "1"})
    assert res is not None
    d = detail(res, "masking_ruff")
    assert outcome(res, "masking_ruff") == "PASS", d
    for scope in ("src/", "scripts/", "tools/", "tests/"):
        assert scope in d, f"the PASS detail does not state the scope it looked for: {d}"


# ------------------------------------------------------- §3.9 the two untested record-selection branches

def test_single_modified_record_is_the_change_record_rt08(tmp_path):
    """§3.9 ("if none was added and exactly one was modified, that one"). A chore change that adds no
    record and modifies exactly one previously merged chore record must take its change_type and
    record_path from it — the branch name (chore/followup) matches no record, so only this branch of
    the selection rule can produce a record. Audit RT-08."""
    r = Repo(tmp_path / "r")
    r.record("chore", "tidy", WHY="one helper instead of three, because duplication.",
             TESTS="none: tidy-up only")
    r.commit("chore: an earlier tidy-up")
    r.branch("chore/followup")
    r.write("docs/changes/chore-tidy.md",
            "TYPE: chore\nWHY: one helper instead of three, because duplication.\n"
            "TESTS: none: tidy-up only — corrected wording\n")
    r.commit("chore: correct the earlier record")
    _, res, _ = r.gate("chore/followup", env={"DEPS_OFFLINE": "1"})
    assert res is not None
    assert res["record_path"] == "docs/changes/chore-tidy.md", res["record_path"]
    assert res["change_type"] == "chore"
    assert outcome(res, "type") == "PASS", detail(res, "type")
    assert outcome(res, "records") == "PASS", detail(res, "records")


def test_branch_name_selects_among_two_modified_records_rt08(tmp_path):
    """§3.9 ("if a branch of the form <type>/<slug> is given, the record whose name matches it, even
    when other records were also modified"). Two previously merged records are modified and none is
    added: ambiguous without the branch, resolved by it. Audit RT-08."""
    r = Repo(tmp_path / "r")
    r.record("fix", "alpha", WHY="a guard instead of a retry, because the input was malformed.",
             TESTS="python -m pytest -q tests")
    r.record("chore", "beta", WHY="a rename instead of a comment, because the name was wrong.",
             TESTS="none: rename only")
    r.commit("chore: two earlier records")
    r.branch("fix/alpha")
    r.write("docs/changes/fix-alpha.md",
            "TYPE: fix\nWHY: a guard instead of a retry, because the input was malformed.\n"
            "TESTS: python -m pytest -q tests tests/test_core.py\n")
    r.write("docs/changes/chore-beta.md",
            "TYPE: chore\nWHY: a rename instead of a comment, because the name was wrong.\n"
            "TESTS: none: rename only (typo fixed)\n")
    r.commit("fix: correct my record and a typo in a merged one")
    _, res, _ = r.gate("fix/alpha", env={"DEPS_OFFLINE": "1"})
    assert res is not None
    assert res["record_path"] == "docs/changes/fix-alpha.md", res["record_path"]
    assert res["change_type"] == "fix"
    assert outcome(res, "type") == "PASS", detail(res, "type")
    assert outcome(res, "records") == "PASS", detail(res, "records")


# ------------------------------------------------------------- §3.10 audit-select: the negative control

def audit_select(r: Repo, salt: str) -> str:
    res = r.run("audit-select", "--subject", "HEAD", "--base", "main", "--policy-ref", "main",
                env={"AUDIT_SALT": salt})
    assert res.returncode == 0, res.stdout + res.stderr
    return res.stdout + res.stderr


def test_unselected_change_is_possible_then_triggers_are_named_p0_10(tmp_path):
    """§3.10 (the 100% triggers, and by implication everything else drawn at AUDIT_RATE). Without this
    control, "selected" proves nothing: a matcher that fires on every path, or a protected-set test
    that is really the random draw, looks identical. A feature touching only src/greeting.py, tests/
    and its own record has no 100% trigger, so only the draw can select it; the salts are tried in
    order (the subject sha is fresh in every run, so no single salt can be fixed in advance) until one
    draws above AUDIT_RATE=0.20 — with 12 candidates, all of them firing has probability 0.2**12.
    Then the same salt on src/auth.py and on a protected file must name its trigger. Audit P0-10 /
    CR-05."""
    neutral = Repo(tmp_path / "neutral")
    neutral.legal_feature()
    quiet, out = None, ""
    for salt in [f"gap-{i}" for i in range(12)]:
        out = audit_select(neutral, salt)
        if "not selected" in out:
            quiet = salt
            break
    assert quiet is not None, f"no salt left this untriggered change unselected: {out}"
    assert "src/greeting.py" not in out and "protected" not in out.lower()

    sensitive = Repo(tmp_path / "sensitive")
    sensitive.branch("feature/auth")
    sensitive.write("tests/test_auth.py", "from src.auth import check\n\n\n"
                                          "def test_check():\n    assert check('t') is True\n")
    sensitive.commit("test: auth")
    sensitive.write("src/auth.py", "def check(token):\n    return bool(token)\n")
    sensitive.record("feature", "auth", WHY="a boolean check instead of a parse, because the caller only "
                                            "needs presence.",
                     SEARCHED='rg -n "check" src/ → 0 hits | NONE-FITS: n/a',
                     TESTS="python -m pytest -q tests")
    sensitive.commit("feat: auth")
    auth_out = audit_select(sensitive, quiet)
    assert "not selected" not in auth_out, auth_out
    assert "src/auth.py" in auth_out, auth_out

    protected = Repo(tmp_path / "protected")
    protected.branch("chore/build")
    protected.append("Makefile", "\n# a harmless comment in a protected file\n")
    protected.record("chore", "build", WHY="a comment instead of a target, because documentation.",
                     TESTS="none: comment only")
    protected.commit("chore: touch a protected file")
    prot_out = audit_select(protected, quiet)
    assert "not selected" not in prot_out, prot_out
    assert "protected" in prot_out.lower(), prot_out
