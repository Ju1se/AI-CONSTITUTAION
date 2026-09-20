"""Shared fixture harness for the verifier's own regression tests.

Every test builds a throwaway git repository from the kit's own files and runs the verifier the way CI
does: the copy at the policy ref judges the subject. Nothing here touches the real repository.

    from _harness import Repo, outcome, detail, RUFF

    def test_something(tmp_path):
        r = Repo(tmp_path / "r")
        r.branch("feature/x")
        r.write("tests/test_x.py", "...")
        r.commit("test: x")
        r.write("src/x.py", "...")
        r.record("feature", "x", WHY="a instead of b, because c.", TESTS="pytest -q")
        r.commit("feat: x")
        rc, res, out = r.gate("feature/x")
        assert outcome(res, "unit_tests") == "PASS"
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
RUFF = shutil.which("ruff") is not None

KIT_FILES = ["policy.mk", "AGENTS.md", "Makefile", "tests/MOCK_ALLOWLIST", "docs/changes/_TEMPLATE.md",
             "docs/agents-policy.md", "scripts/gate_checks.py"]
SELFTEST_FILES = ["scripts/tests/_harness.py", "scripts/tests/test_gate_checks.py"]

BASE_SRC = "def value():\n    return 1\n"
BASE_TEST = "from src.core import value\n\n\ndef test_value():\n    assert value() == 1\n"

GIT_ENV = {
    "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
    "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}


class Repo:
    """A throwaway repository carrying the kit on `main`, plus a trivial src/ and tests/."""

    def __init__(self, path: Path, with_selftests: bool = False, baseline: bool = True):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.env = {**os.environ, **GIT_ENV}
        self.git("init", "-q", "-b", "main")
        for rel in KIT_FILES + (SELFTEST_FILES if with_selftests else []):
            self.copy_from_kit(rel)
        if baseline:
            self.write("src/__init__.py", "")
            self.write("src/core.py", BASE_SRC)
            self.write("tests/test_core.py", BASE_TEST)
        self.commit("chore: baseline")

    # ---------------------------------------------------------------- plumbing
    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        res = subprocess.run(["git", "-C", str(self.path), *args], env=self.env,
                             capture_output=True, text=True)
        if check and res.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} failed: {res.stderr}")
        return res

    def copy_from_kit(self, rel: str) -> None:
        dst = self.path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(KIT / rel, dst)

    def write(self, rel: str, content: str) -> None:
        p = self.path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def append(self, rel: str, content: str) -> None:
        self.write(rel, self.read(rel) + content)

    def read(self, rel: str) -> str:
        return (self.path / rel).read_text(encoding="utf-8")

    def rm(self, rel: str) -> None:
        self.git("rm", "-q", "-r", rel)

    def commit(self, msg: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg, "--allow-empty")
        return self.rev("HEAD")

    def rev(self, ref: str = "HEAD") -> str:
        return self.git("rev-parse", ref).stdout.strip()

    def branch(self, name: str) -> None:
        self.git("checkout", "-q", "-b", name)

    def record(self, type_: str, slug: str, **fields: str) -> str:
        """Write docs/changes/<type>-<slug>.md. Field order is TYPE first, then as given."""
        lines = [f"TYPE: {type_}"] + [f"{k}: {v}" for k, v in fields.items()]
        rel = f"docs/changes/{type_}-{slug}.md"
        self.write(rel, "\n".join(lines) + "\n")
        return rel

    # ---------------------------------------------------------------- the gate
    def verifier_from(self, ref: str) -> Path:
        """Extract scripts/gate_checks.py from `ref`, the way CI and `make gate` do."""
        out = self.path / ".verifiers" / f"{ref.replace('/', '_')}.py"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.git("show", f"{ref}:scripts/gate_checks.py").stdout, encoding="utf-8")
        return out

    def run(self, *args: str, verifier: Path | str | None = None,
            env: dict | None = None) -> subprocess.CompletedProcess:
        v = Path(verifier) if verifier else self.verifier_from("main")
        return subprocess.run([sys.executable, str(v), *args], cwd=self.path,
                              env={**self.env, **(env or {})}, capture_output=True, text=True)

    def gate(self, branch: str | None = None, subject: str = "HEAD", base: str = "main",
             policy_ref: str = "main", profile: str = "enforced", out: str = ".gate/result.json",
             verifier: Path | str | None = None, env: dict | None = None):
        """Run the full gate. Returns (returncode, result dict or None, stdout+stderr)."""
        target = self.path / out
        if target.exists():
            target.unlink()
        cmd = ["gate", "--subject", subject, "--base", base, "--policy-ref", policy_ref,
               "--profile", profile, "--out", str(target)]
        if branch is not None:
            cmd += ["--branch", branch]
        res = self.run(*cmd, verifier=verifier, env=env)
        result = json.loads(target.read_text(encoding="utf-8")) if target.exists() else None
        return res.returncode, result, res.stdout + res.stderr

    def check(self, what: str, branch: str | None = None, subject: str = "HEAD", base: str = "main",
              policy_ref: str = "main", profile: str = "enforced",
              verifier: Path | str | None = None, env: dict | None = None):
        """Run one check or group. Returns (returncode, stdout+stderr)."""
        cmd = ["check", what, "--subject", subject, "--base", base, "--policy-ref", policy_ref,
               "--profile", profile]
        if branch is not None:
            cmd += ["--branch", branch]
        res = self.run(*cmd, verifier=verifier, env=env)
        return res.returncode, res.stdout + res.stderr

    # ---------------------------------------------------------------- shorthands
    def legal_feature(self, slug: str = "greeting") -> None:
        """The compliant path: tests committed first, then the implementation and the record."""
        self.branch(f"feature/{slug}")
        self.write(f"tests/test_{slug}.py",
                   f"from src.{slug} import greet\n\n\ndef test_greet():\n"
                   f"    assert greet('a') == 'hello, a'\n")
        self.commit("test: greet")
        self.write(f"src/{slug}.py", "def greet(name):\n    return f'hello, {name}'\n")
        self.record("feature", slug, WHY="an f-string instead of concatenation, because readability.",
                    SEARCHED='rg -n "greet" src/ → 0 hits | NONE-FITS: n/a',
                    TESTS="python -m pytest -q tests")
        self.commit("feat: greet")


def outcome(result: dict, check_id: str) -> str:
    """The outcome of one check, or 'ABSENT' when the gate did not report it."""
    for c in result["checks"]:
        if c["id"] == check_id:
            return c["outcome"]
    return "ABSENT"


def detail(result: dict, check_id: str) -> str:
    """The joined detail lines of one check, for substring assertions."""
    for c in result["checks"]:
        if c["id"] == check_id:
            return "\n".join(c["detail"])
    return ""


def required_ids(result: dict) -> set:
    return {c["id"] for c in result["checks"] if c["required"]}


def eligible_or_blocked_only_by(result: dict, *allowed_reasons: str) -> bool:
    """True when the change is eligible, or ineligible only for the given environmental reasons.

    Lets a test assert 'nothing in this scenario blocks the merge' on a machine that lacks ruff.
    """
    if result["merge_eligible"]:
        return True
    reasons = result.get("ineligible_reasons") or []
    return bool(reasons) and all(any(a in r for a in allowed_reasons) for r in reasons)
