# Change record — policy/balance-controls

TYPE: policy
WHY: four control fixtures pinning that legitimate work passes, for the owner's balance scenarios 3 and 6, instead of leaving the corpus with refusals only, because a corpus that pins only what the gate refuses cannot tell a stricter verifier from a correct one, and a verifier that sealed a pinned behaviour forever or charged ordinary work with constitutional proceedings would pass every refusal test.
TESTS: python -m pytest -q -p no:cacheprovider scripts/tests/test_balance_controls.py → 4 passed in ~10 s serially, against this branch's verifier and against PR #3's (scripts/gate_checks.py replaced by `git show HEAD:scripts/gate_checks.py` from policy/revised-counterexamples-hold, in a scratch copy).
TESTS: ruff check --isolated --line-length 110 scripts/tests/test_balance_controls.py → clean.
TESTS: probes run once and not kept (python, in the same fixtures): moving the verifier to v2 without revising the pin → verifier_selftest FAIL, so the pin has teeth; loosening the pin with no ACCEPTANCE line → h1 FAIL, so the recorded decision is load-bearing in step 1.
TESTS: mutation (reviewer), each mutant applied alone to main's scripts/gate_checks.py in a full scratch copy of the worktree (.git excluded, so the harness KIT points at the mutant), then `python -m pytest -q -p no:cacheprovider -p no:xdist scripts/tests/test_balance_controls.py`:
| Mutant | Exact replacement in scripts/gate_checks.py | Killed by | Failure observed |
|---|---|---|---|
| K1 | `exempt = ctx.type in ("test", "policy") and bool(revision)` -> `exempt = ctx.type in ("test",) and bool(revision)` | test_a_pinned_verifier_behaviour_has_an_authorized_transition_path (step 1) | ineligible_reasons == ['h1 FAIL'] |
| K1b | same line -> `exempt = False` | test_a_pinned_verifier_behaviour_has_an_authorized_transition_path | h1 FAIL |
| K2 | the "Restore the trusted corpus" comment line -> a block that FAILs verifier_selftest when any trusted counterexample differs between subject and policy_ref ("the corpus is sealed") | test_a_pinned_verifier_behaviour_has_an_authorized_transition_path (step 1) | verifier_selftest FAIL, not PASS |
| K3 | the `if ctx.type != "policy":` NOT_RUN early return -> `c.required = True` | 6a, 6b, 6c | 6a: selftest required with PASS instead of NOT_RUN; 6b: ['verifier_selftest FAIL'] (disputed corpus spilled over); 6c: ['verifier_selftest ERROR'] on a docs chore |
| K4 | `reasons = []` before the renew/policy trigger -> `reasons = ["mutant: every change is a 100% trigger"]` | test_a_docs_only_chore_is_cheap_and_has_no_audit_trigger_6c | none of the 12 salts printed "not selected" |
Score: 5/5 killed (4/4 required mutants plus the K1b variant), each for the scenario-intended reason.
TESTS: python -m pytest -q -p no:cacheprovider scripts/tests/test_balance_controls.py → 4 passed in 10.11s (finisher run).
TESTS: python -m pytest -q -p no:cacheprovider -n 8 scripts/tests → 151 passed in 101.73s.
READ: the spec named scenario 3's transition but not which route counts; I pinned only the loosen-then-tighten route (accept v1 or v2, merge, then move to v2 and accept v2 only). Deletion routes are not pinned, because the enacted policy row says counterexamples are added, never removed; nothing here pins that any other route is refused. The ACCEPTANCE line in the fixture is written in whatever form the law in force requires, not in a form this change chooses; granted-by:none.
HANDOFF: scenario 1 (a self-written ACCEPTANCE line lifts protection) is open and legislative, and no test here touches it — the scenario-3 fixture passes on a self-authored approval because the law in force accepts one. When the law changes the authorization form, the `acceptance()` helper in scripts/tests/test_balance_controls.py must follow it; a scenario-3 failure after such a change means the fixture is stale, not that the transition path is gone — check that first.
