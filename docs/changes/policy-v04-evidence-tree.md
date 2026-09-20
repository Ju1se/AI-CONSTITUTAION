# Change record — policy/v04-evidence-tree

TYPE: policy
WHY: separate the evidence tree from the candidate instead of hardening each tool that reads it, because the independent review of v0.3 (`docs/audits/agents-kit-v0.3-review.md`) reproduced four distinct ways the candidate configured its own judgment — `.gitattributes`, `addopts`, a `conftest.py` hook and a ruff table — and patching them one at a time would have left the next one open.
TESTS: python -m pytest -q scripts/tests   (95 tests: the v0.3 corpus of 21 plus 74 written blind from the spec before this implementation existed)
TESTS: python /tmp/.../scratchpad/smoke.py   (13 end-to-end scenarios: every v0.3 P0 refused, three controls still eligible)

## What this change is

v0.4 of the merge gate. The starting point is the v0.3 kit that arrived under `AI Policy/`; its architecture
is kept, the mechanisms the second implementation had are ported in, and every reproduced finding of the
review is closed or explicitly scoped.

## How it was built

The verifier's acceptance criteria were written first, as `v04-spec.md`, and six instances wrote 74 tests
from that specification alone, without seeing the implementation — which did not exist when they started.
Every one of those tests failed against v0.3. When the implementation landed they passed, except seven.
Five of the seven were defects in the implementation and were fixed:

- a boundary handler whose body was `return None` was accepted; `return None` is the fallback value §2 refuses
- `except AssertionError: pass` was not treated as a swallowing handler, because the rule matched only catch-alls
- `patch(TARGET)` where `TARGET` is a local variable was reported as a resolved target named "TARGET"
- the sunset refusal named the branch type without the slash the policy writes it with
- `REQUIRED_CHECKS_ENFORCED` was backslash-continued in `policy.mk`, and the parser read only the first line,
  so nine required checks silently became advisory — the same failure mode as the audit's "not run counted as
  passed", found by a test that simply grepped the file

Two of the seven were defects in the specification, corrected there and in the test:

- §4.2 said an unloadable verifier is "exit 3"; GNU make returns 2 for any failed recipe, so the recipe's own
  3 appears only in make's report line
- §4.1 said to remove the shallow fetch; the test grepped for the literal flag, which the explanatory comment
  still contained

## Scope

- `scripts/gate_checks.py`: four new required checks (`export_integrity`, `harness_integrity`,
  `test_inventory`, `red_before_green`); tool isolation for pytest and ruff; verifier provenance in the
  result and in `merge_eligible`; AST mock resolution; field-level renew diff; tag edits off renew refused;
  per-kind term on added lines with the maximum tree-wide; grace bound to the own record, the window and
  once per tag; the trusted corpus restored over the candidate's for `verifier_selftest`; record selection
  that allows correcting a merged record; a recursive glob for `AUDIT_ALWAYS_PATHS`; the profile taken from
  the flag only.
- `policy.mk`: `.gitattributes` protected; the enforced required set on one physical line.
- `Makefile`: `set -o pipefail` inside the recipe (GNU make 3.81 ignores `.SHELLFLAGS`); no `--branch` when
  SUBJECT is not HEAD; `gate-advisory` as its own target.
- `.github/workflows/gate.yml`: the shallow fetch removed, and the base asserted non-empty.
- `.claude/hooks/h1-test-source-separation.sh`: a renew may edit `src/`; the frozen set widened to
  `scripts/tests/` and every `conftest.py`; a path whose parent does not exist yet is still normalized.
- `.claude/skills/audit/SKILL.md`: RECHECK writes to its own file and does not inject the auditor's branch.
- `AGENTS.md` (134 lines, 14.0 KB), `docs/agents-policy.md`: H6 added; §2, §3, §5, §6, §7 rewritten to match;
  §7.5 states what the gate does not claim.
- `scripts/tests/`: `_harness.py` plus seven test files.

## Removed

- `agents-kit.zip` (the v0.2 archive; recoverable from git history at 996a184).
- `tests/gate/` and `docs/changes/policy-trusted-gate.md`: the second implementation's layout. Its
  mechanisms are in this change; its file locations are superseded by `scripts/tests/`.
- `AI Policy/`: the staging folder the v0.3 kit arrived in. Its contents are this repository's files now,
  verified byte-identical to `agents-kit-v0.3.zip` before installation.

## Two corrections to the v0.3 self-tests

`test_advisory_profile_requires_only_its_listed_checks` asserted that the advisory profile yields
`merge_eligible: true` — the review listed it as a test that pinned a defect in place. It is now
`test_advisory_profile_never_authorizes_a_merge`. `test_p10_short_term_is_enforced_per_kind` asserted a
verbatim sentence rather than the rule; it now asserts the term.

## Not in this change

Phase 3 of the original audit: deciding by experiment which of PAYGO, sunset and sampling audit earns its
cost. `ledger`, `mutation`, `searched_replay` and `renewals_cap` remain NOT_RUN and advisory. The residue
the gate cannot cover is in `docs/agents-policy.md` §7.5, not left implicit.
