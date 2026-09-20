"""v0.4 regression tests for `mocks` (§3.6), `records` (§3.9) and `audit-select` (§3.10).

Written from `v04-spec.md` before the implementation exists: the tests that pin down new behaviour are
expected to FAIL against the v0.3 verifier. Every refusal here is paired with the nearly identical
legitimate case that must PASS, so a check that refuses everything cannot look correct.
"""
from __future__ import annotations

from _harness import Repo, detail, outcome

# A local stand-in for the `requests` I/O boundary, committed on main so the export can import it.
REQUESTS_STUB = "def get(url, timeout=None):\n    raise RuntimeError('no network in the fixture')\n"

RECORD_FIELDS = {
    "WHY": "a stub instead of the real call, because determinism.",
    "SEARCHED": 'rg -n "run" src/ → 0 hits | NONE-FITS: n/a',
    "TESTS": "python -m pytest -q tests",
}


def mock_change(r: Repo, test_src: str, src_files: dict[str, str] | None = None, slug: str = "mocked"):
    """A compliant feature branch (tests committed first, then src + record) carrying `test_src`."""
    r.branch(f"feature/{slug}")
    r.write(f"tests/test_{slug}.py", test_src)
    r.commit("test: the mocked path")
    r.write(f"src/{slug}.py", "def run():\n    return 2\n")
    for rel, body in (src_files or {}).items():
        r.write(rel, body)
    r.record("feature", slug, **RECORD_FIELDS)
    r.commit("feat: the mocked path")
    return r.gate(f"feature/{slug}", env={"DEPS_OFFLINE": "1"})


def audit_select(r: Repo, paths: list[str], type_: str = "feature", slug: str = "auth"):
    """Commit a change touching `paths` and return audit-select's exit code and output."""
    r.branch(f"{type_}/{slug}")
    for p in paths:
        r.write(p, "def check(token):\n    return bool(token)\n")
    r.write(f"tests/test_{slug}.py", "def test_placeholder():\n    assert True\n")
    r.record(type_, slug, **RECORD_FIELDS)
    r.commit(f"{type_}: {slug}")
    res = r.run("audit-select", "--subject", "HEAD", "--base", "main", "--policy-ref", "main",
                env={"AUDIT_SALT": "x"})
    return res.returncode, res.stdout + res.stderr


def deps_change(r: Repo, recorded: list[str]):
    """A compliant feature that adds two requirements, with a DEP line only for each name in `recorded`."""
    r.legal_feature()
    r.write("requirements.txt", "requests==2.31.0\nhttpx==0.27.0\n")
    lines = ["TYPE: feature", "WHY: pinned clients instead of urllib, because retries.",
             'SEARCHED: rg -n "greet" src/ → 0 hits | NONE-FITS: n/a']
    lines += [f"DEP: {d} lookup:pip index versions {d.split('==')[0]} published:2024-01-01"
              f" | REASON: http client | INSTEAD-OF: urllib" for d in recorded]
    lines.append("TESTS: python -m pytest -q tests")
    r.write("docs/changes/feature-greeting.md", "\n".join(lines) + "\n")
    r.commit("feat: pin the clients")
    return r.gate("feature/greeting", env={"DEPS_OFFLINE": "1"})


# ----------------------------------------------------------------------------- mocks (§3.6)

def test_object_form_monkeypatch_names_the_resolved_target_cmp11(tmp_path):
    """§3.6: `monkeypatch.setattr(core, "value", ...)` after `from src import core` resolves to the
    in-repo target src.core.value and must FAIL naming it (audit P14 / CMP-11)."""
    r = Repo(tmp_path / "r")
    _, res, _ = mock_change(r, "from src import core\n\n\n"
                               "def test_value_is_mocked(monkeypatch):\n"
                               '    monkeypatch.setattr(core, "value", lambda: 99)\n'
                               "    assert core.value() == 99\n")
    assert res is not None
    assert outcome(res, "mocks") == "FAIL"
    assert "core.value" in detail(res, "mocks")  # not the truncated bare object name 'core'


def test_object_form_allowlisted_io_boundaries_pass_cmp05(tmp_path):
    """§3.6 control: `patch.object(requests, "get")` and `monkeypatch.setattr(time, "sleep", ...)`
    resolve to allowlisted prefixes and must PASS; v0.3 truncates them to 'requests'/'time' and refuses."""
    r = Repo(tmp_path / "r")
    r.write("requests.py", REQUESTS_STUB)
    r.commit("chore: local http stub for the fixture")
    _, res, _ = mock_change(r, "import time\nfrom unittest.mock import patch\n\nimport requests\n\n\n"
                               "def test_io_boundaries(monkeypatch):\n"
                               '    monkeypatch.setattr(time, "sleep", lambda s: None)\n'
                               '    with patch.object(requests, "get") as get:\n'
                               '        get.return_value = "stub"\n'
                               '        assert requests.get("http://x") == "stub"\n'
                               "    time.sleep(0)\n")
    assert res is not None
    assert outcome(res, "mocks") == "PASS", detail(res, "mocks")


def test_string_form_allowlisted_patch_still_passes_control(tmp_path):
    """§3.6 control: the v0.3 string form `patch("requests.get")` is allowlisted and must keep PASSing."""
    r = Repo(tmp_path / "r")
    r.write("requests.py", REQUESTS_STUB)
    r.commit("chore: local http stub for the fixture")
    _, res, _ = mock_change(r, "from unittest.mock import patch\n\n\n"
                               "def test_http_is_stubbed():\n"
                               '    with patch("requests.get") as get:\n'
                               '        get.return_value = "stub"\n'
                               "        assert get() == \"stub\"\n")
    assert res is not None
    assert outcome(res, "mocks") == "PASS", detail(res, "mocks")


def test_src_helper_patching_an_in_repo_target_fails_mocks_m09(tmp_path):
    """§3.6: the scan covers src/ as well as tests/, so a patch helper hidden in src/testing.py
    patching src.core.value must FAIL (M09)."""
    r = Repo(tmp_path / "r")
    helper = "from unittest.mock import patch\n\n\ndef patched_value(v):\n" \
             '    return patch("src.core.value", return_value=v)\n'
    _, res, _ = mock_change(r, "from src.testing import patched_value\n\n\n"
                               "def test_helper_patches_the_repo():\n"
                               "    with patched_value(5):\n"
                               "        from src.core import value\n"
                               "        assert value() == 5\n",
                            src_files={"src/testing.py": helper})
    assert res is not None
    assert outcome(res, "mocks") == "FAIL"
    assert "src/testing.py" in detail(res, "mocks") and "src.core.value" in detail(res, "mocks")


def test_patch_dict_and_setattr_on_an_imported_module_fail_mocks_m10(tmp_path):
    """§3.6: `patch.dict(core.__dict__, ...)` and bare `setattr(core, "value", ...)` are mock forms the
    v0.3 regex cannot see; on an in-repo module they must FAIL (M10)."""
    r = Repo(tmp_path / "r")
    _, res, _ = mock_change(r, "from unittest.mock import patch\n\nfrom src import core\n\n\n"
                               "def test_two_hidden_forms():\n"
                               '    with patch.dict(core.__dict__, {"value": lambda: 7}):\n'
                               "        assert core.value() == 7\n"
                               "    original = core.value\n"
                               '    setattr(core, "value", lambda: 9)\n'
                               "    assert core.value() == 9\n"
                               "    core.value = original\n")
    assert res is not None
    assert outcome(res, "mocks") == "FAIL", detail(res, "mocks")
    assert "core" in detail(res, "mocks")


def test_dynamic_patch_target_is_reported_unresolved_m10(tmp_path):
    """§3.6: a target computed at runtime (`patch(TARGET)`) must be reported as unresolved in the
    detail, never silently passed (M10, §5)."""
    r = Repo(tmp_path / "r")
    _, res, _ = mock_change(r, "from unittest.mock import patch\n\n"
                               'TARGET = "src.core.value"\n\n\n'
                               "def test_dynamic_target():\n"
                               "    with patch(TARGET, return_value=8):\n"
                               "        from src.core import value\n"
                               "        assert value() == 8\n")
    assert res is not None
    assert "unresolved" in detail(res, "mocks").lower()


# ----------------------------------------------------------------------------- records (§3.9)

def test_own_record_plus_typo_fix_in_a_merged_record_passes_rt08(tmp_path):
    """§3.9: the change's own added record is selected even when a previously merged record is also
    modified — a typo fix is not a second change (RT-08)."""
    r = Repo(tmp_path / "r")
    r.write("docs/changes/feature-old.md", "TYPE: feature\nWHY: a instead of b, becuse c.\nTESTS: pytest -q\n")
    r.commit("feat: an earlier change")
    r.branch("chore/cleanup")
    r.write("docs/changes/feature-old.md", "TYPE: feature\nWHY: a instead of b, because c.\nTESTS: pytest -q\n")
    r.record("chore", "cleanup", WHY="fixing the typo in place, because the record is the evidence.")
    r.commit("chore: fix a typo in a merged record")
    _, res, _ = r.gate("chore/cleanup", env={"DEPS_OFFLINE": "1"})
    assert res is not None
    assert outcome(res, "type") == "PASS", detail(res, "type")
    assert outcome(res, "records") == "PASS", detail(res, "records")
    assert res["record_path"] == "docs/changes/chore-cleanup.md"


def test_change_with_no_record_at_all_still_fails_records_rt08(tmp_path):
    """§3.9 control: widening selection must not excuse a change with zero records added or modified —
    that is still a FAIL (RT-08 keeps the zero case refused)."""
    r = Repo(tmp_path / "r")
    r.branch("chore/readme")
    r.write("README.md", "# project\n\nNo record for this change.\n")
    r.commit("chore: readme with no record")
    _, res, _ = r.gate("chore/readme", env={"DEPS_OFFLINE": "1"})
    assert res is not None
    assert outcome(res, "records") == "FAIL"
    assert res["merge_eligible"] is False


def test_dep_binding_is_by_package_name_rt08(tmp_path):
    """§3.9: v0.3's DEP-by-name binding is kept — two added requirements with one DEP line FAIL records
    naming the unrecorded package; recording both PASSes (control)."""
    unrecorded = Repo(tmp_path / "unrecorded")
    _, res, _ = deps_change(unrecorded, ["requests==2.31.0"])
    assert res is not None
    assert outcome(res, "records") == "FAIL"
    assert "httpx" in detail(res, "records")
    both = Repo(tmp_path / "both")
    _, res2, _ = deps_change(both, ["requests==2.31.0", "httpx==0.27.0"])
    assert res2 is not None
    assert outcome(res2, "records") == "PASS", detail(res2, "records")


# ----------------------------------------------------------------------------- audit-select (§3.10)

def test_audit_always_paths_match_a_top_level_auth_file_p0_10(tmp_path):
    """§3.10: `**` matches zero directories, so `src/**/auth*` must trigger AUDIT_ALWAYS_PATHS for
    src/auth.py — today fnmatch requires an intervening directory (P0-10 / CR-05)."""
    rc, out = audit_select(Repo(tmp_path / "r"), ["src/auth.py"])
    assert rc == 0, out
    assert "AUDIT_ALWAYS_PATHS" in out and "src/auth.py" in out


def test_audit_always_paths_still_match_a_nested_auth_file_p0_10(tmp_path):
    """§3.10 control: the recursive matcher must keep triggering for src/a/b/auth.py, which v0.3
    already catches (P0-10)."""
    rc, out = audit_select(Repo(tmp_path / "r"), ["src/a/b/auth.py"])
    assert rc == 0, out
    assert "AUDIT_ALWAYS_PATHS" in out and "src/a/b/auth.py" in out


def test_protected_set_change_is_a_hundred_percent_audit_trigger_cr05(tmp_path):
    """§3.10: "protected set changed" is a new 100% trigger, so a change touching the Makefile must be
    selected for that reason and not by the random draw (CR-05)."""
    r = Repo(tmp_path / "r")
    r.branch("chore/build")
    r.append("Makefile", "\n# a harmless comment in a protected file\n")
    r.record("chore", "build", WHY="a comment instead of a target, because documentation.")
    r.commit("chore: touch a protected file")
    res = r.run("audit-select", "--subject", "HEAD", "--base", "main", "--policy-ref", "main",
                env={"AUDIT_SALT": "x"})
    assert res.returncode == 0, res.stdout + res.stderr
    assert "protected" in (res.stdout + res.stderr).lower()
