"""J-1, pinned at the mechanism: `run_in` is what must strip the gate's own identity.

Mutation JUD-2026-09-21-01/M9 empties the stripping loop in `run_in` (`for name in INHERITED_IDENTITY:`
becomes `for name in []:`). What follows about the pre-existing coverage was checked in a sandbox, not
assumed:

  * `grep -n "run_in(" scripts/tests/*.py` finds no call site outside this file. The only other mentions
    of the name in the corpus are prose — a docstring line and a comment in test_adoption_prerequisites.py.
  * With the loop emptied, the whole of scripts/tests/test_adoption_prerequisites.py — the file carrying
    the corpus's J-1 cases — still passes. Its
    `test_a_spawned_process_sees_no_inherited_identity_j01` asserts that eight specific names are members
    of `INHERITED_IDENTITY` and then re-implements the filtering inside the test
    (`env={k: v for k, v in env.items() if k not in gc.INHERITED_IDENTITY}`) before spawning, so it
    exercises the constant and never the loop.

No claim is made here about the rest of the corpus; only the file above was re-run under the mutation.
That existing case is deliberately left in place: it is the only one pinning membership of particular
names, which neither case below can see.

The two cases below reach the loop. One calls `run_in` directly; one runs a real gate whose spawned pytest
carries a committed probe that reports its own environment back. Both take their names from
`INHERITED_IDENTITY` instead of listing them, so a name added to the constant is exercised the day it is
added, and neither constructs a `Ctx`, so the shape of that dataclass is not part of what they pin.

Lands at scripts/tests/test_identity_isolation_j4.py — a new file; nothing existing is edited.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from _harness import Repo, detail, outcome

VERIFIER = Path(__file__).resolve().parents[1] / "gate_checks.py"

# A committed test that reports, rather than guesses, what the gate handed it. It writes to an absolute
# path outside the export so the report survives whatever pytest then decides about the run.
PROBE = '''\
import json
import os

NAMES = {names!r}
DUMP = {dump!r}


def test_the_gate_did_not_hand_me_its_own_identity():
    leaked = sorted(n for n in NAMES if n in os.environ)
    # Appended, not truncated: if the gate ever runs this suite more than once, every run stays on the
    # record instead of only the last one.
    with open(DUMP, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(leaked) + "\\n")
    assert leaked == [], f"these names are set in this process's environment: {{leaked}}"
'''


def load_verifier():
    """The verifier under test, imported as a module so `run_in` can be called for real."""
    spec = importlib.util.spec_from_file_location("gc_run_in_under_test", VERIFIER)
    gc = importlib.util.module_from_spec(spec)
    sys.modules["gc_run_in_under_test"] = gc
    spec.loader.exec_module(gc)
    return gc


def test_run_in_strips_every_inherited_identity_name_from_the_child_m9(tmp_path, monkeypatch):
    """The mechanism: every INHERITED_IDENTITY name set on the gate must be gone inside `run_in`'s child.

    Asserted on `run_in`'s own behavior — nothing here reproduces the filtering, so emptying the loop is
    visible here and not in a case that rebuilds the filter itself.
    """
    gc = load_verifier()
    names = list(gc.INHERITED_IDENTITY)
    assert names, "INHERITED_IDENTITY is empty"

    exp = tmp_path / "export"
    exp.mkdir()
    for name in names:
        monkeypatch.setenv(name, f"leaked-{name.lower()}")

    # `run_in` reads exp, cmd, timeout and os.environ; its body never touches `ctx`, so passing None keeps
    # this case off the `Ctx` constructor signature and out of the way of fields added to that dataclass.
    # A plain Python child, not pytest: the report is then about the environment, not about tooling that
    # happens to read some of these names itself.
    res = gc.run_in(None, str(exp), [
        sys.executable, "-c",
        "import json, os, sys; print(json.dumps(sorted(n for n in sys.argv[1:] if n in os.environ)))",
        *names], 60)

    assert res.returncode == 0, (
        f"the child exited {res.returncode} instead of 0.\nstdout: {res.stdout}\nstderr: {res.stderr}")
    lines = res.stdout.strip().splitlines()
    assert lines, f"the child exited 0 and printed nothing on stdout.\nstderr: {res.stderr}"

    seen = json.loads(lines[-1])
    assert seen == [], (
        f"every INHERITED_IDENTITY name was set in this process's environment before the call, and the "
        f"child that run_in() spawned still saw {seen}. Expected none of them (audit J-1).")


def test_a_real_gate_run_hands_no_identity_variable_to_the_tests_it_runs_m9(tmp_path):
    """End to end: a gate invoked with every identity variable set must still spawn clean children.

    The subject repository carries a committed test that reports its own environment, so the assertions
    are about what `run_in` did on the real call path, not about a reconstruction of it.
    """
    gc = load_verifier()
    names = list(gc.INHERITED_IDENTITY)
    dump = tmp_path / "leaked.jsonl"

    r = Repo(tmp_path / "r")
    r.write("tests/test_gate_environment.py", PROBE.format(names=names, dump=str(dump)))
    r.commit("chore: a committed probe of the environment the gate spawns tests in")
    r.legal_feature("greeting")

    # An empty value is still an entry in the environment, and it keeps the child's own pytest usable when
    # run_in does not strip, so the probe can name every leak instead of dying on PYTEST_ADDOPTS first.
    # DEPS_OFFLINE follows the corpus's convention for full-gate cases.
    poisoned = {n: ("" if n.startswith("PYTEST_") else f"leaked-{n.lower()}") for n in names}
    poisoned["DEPS_OFFLINE"] = "1"
    _, res, out = r.gate("feature/greeting", env=poisoned)
    assert res is not None, out

    lines = dump.read_text(encoding="utf-8").splitlines() if dump.exists() else []
    reports = [json.loads(ln) for ln in lines if ln.strip()]
    leaked = sorted({n for rep in reports for n in rep})
    unit = outcome(res, "unit_tests")
    observed = (f"the committed probe ran {len(reports)} time(s) and reported {leaked}" if reports
                else f"no report was written at {dump}")

    assert unit == "PASS", (
        f"the gate's unit_tests check was {unit}; {observed}.\n{detail(res, 'unit_tests')}")
    assert reports, (
        f"the gate's unit_tests check was {unit} and {observed}, so this run observed nothing about the "
        f"environment of the processes the gate spawned.\n{detail(res, 'unit_tests')}")
    assert leaked == [], (
        f"the gate was started with every INHERITED_IDENTITY name set, and {observed} — those names were "
        f"still set in the environment of the pytest process the gate spawned. Expected none of them "
        f"(audit J-1). unit_tests was {unit}.")
