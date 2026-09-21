# Change record — policy/adoption-prerequisites

TYPE: policy
WHY: close the four confirmed findings that stand between the two proposed amendments and adoption,
instead of adopting the amendments first, because two of the findings are of the class where the machinery
certifies a violation as compliance and enacting §3 over them would put a safeguard in the constitution
that the gate reports as satisfied when nothing checks it.

TESTS: python -m pytest -q scripts/tests  → 140 passed (130 existing plus the 10 new fixtures below)
TESTS: ruff check --isolated --select E722,BLE001,S110,S112,S113 scripts/  → clean

HANDOFF: this change installs the route §3 needs for revising a frozen acceptance, and deliberately does
not use it. An earlier draft did: it reworded harness_integrity's scope line, which made one assertion in
scripts/tests/test_evidence_tree.py stale, and revised that assertion under an ACCEPTANCE line reading
"granted-by: none". The gate refused it three ways, and correctly — the verifier that judges a policy
change is loaded from main, so the route did not exist yet in law. Rather than force it, the scope line
was rewritten to be accurate under the new behaviour while remaining true to what the committed assertion
pins. The first change to use the route will be judged by a main that already contains it. That the route
would have passed on a self-granted approval is finding LM-5, unfixed: the gate can read that a decision
was recorded, not that the approver was independent.

## What is fixed

| finding | fix |
|---|---|
| J-1 · the audit's own recheck command fabricated a `verifier_selftest` failure on every policy change | `run_in` strips the run's identity (`SUBJECT`, `BASE`, `BRANCH`, `MAIN`, `POLICY_REF`, `VERIFIER_REF`, `GATE_OUT`, `GATE_PROFILE`) from every process the gate spawns. A nested gate must be told what to judge, never inherit it. |
| LM-2 · `TYPE: test` disabled the frozen-test rule outright | the exemption is now conditional on an `ACCEPTANCE:` line in the record, and such a change lands in the 100% audit set. |
| LM-3 · no branch type could revise a counterexample under `scripts/tests/` | `policy` is now the forum for protected acceptance, as §3 already says, on the same recorded-decision condition. The hook was aligned with it. The route is installed, not exercised — see HANDOFF. |
| LM-8 · any `<` in a record value read as an unfilled template slot | a placeholder is an angle-bracket token, so a truthful `WHY` carrying a bound such as `n <= 3` is accepted. |
| LM-1 (partial) · an autouse fixture rewriting verdicts made a red suite report PASS | `harness_integrity` now refuses any pytest hook in a conftest, and the marker and outcome forms the reproduced attack used. |
| LM-7 · an acceptance revision or a recorded exception was not always audited | both are 100% audit triggers. |

The five record fields the legislative amendment introduces — `ACCEPTANCE`, `EXCEPTION`, `EFFECTIVE`,
`READ`, `HANDOFF` — are now parsed. Before this change the verifier read seven keys and none of them.

## What is not fixed

LM-1 is closed for the form that was reproduced, not for the class. The gate runs code the candidate
wrote; a conftest or an imported module can still reach the verdict by a route no pattern anticipates, and
`harness_integrity` now says so on every run instead of naming one example. Closing the class needs the
acceptance that judges a change to come from the trusted ref, which is a different change.

LM-4 — harness policy outside `PROTECTED_PATHS` (`pyproject.toml` sections, a root `conftest.py`) is
refused on every branch type, each check's safe path naming the route the other closes — is untouched.
LM-5 — the approval clauses are honour-based — is untouched and is demonstrated above.
