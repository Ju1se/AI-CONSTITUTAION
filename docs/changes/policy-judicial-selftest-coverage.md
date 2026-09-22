TYPE: policy
WHY: three counterexamples pinning where the gate reads its inputs instead of leaving those properties to review, because `verifier_selftest` is the only mechanical limit on a change to the judge, so a property with no counterexample is a property an amendment may remove in silence.
SEARCHED: rg -n "policy_ref|INHERITED_IDENTITY|merge_eligible" scripts/tests/ → 3 nearest cases: test_gate_checks.py:206 (asserts main's policy.mk bytes are unchanged, never the values a run applied), test_adoption_prerequisites.py:183 (asserts membership of the INHERITED_IDENTITY constant, then re-implements the stripping in the test instead of calling run_in), test_sunset_mocks_gaps_v04.py:190 (the same shape for tests/MOCK_ALLOWLIST, which check_mocks reads through its own show() call) | NONE-FITS: each stays green under the mutation it appears to cover — measured, see TESTS.
TESTS: python -m pytest -q scripts/tests/test_policy_provenance_j4.py scripts/tests/test_identity_isolation_j4.py scripts/tests/test_required_set_effect_j4.py → 7 passed. Kill power, each mutation applied to a copy at a single asserted occurrence: policy.mk read from the subject → test_policy_provenance_j4 1 failed; run_in's stripping loop emptied → test_identity_isolation_j4 2 failed; a required check dropped from the tally in result_json → test_required_set_effect_j4 1 failed. Refactor tolerance, applied without any mutation: sorting the echoed protected set, formatting MUTATION_MIN through float(), adding a required field to Ctx, rewording ineligible_reasons → all three files stay green. ruff check --isolated --line-length 110 on the three files → clean. Full corpus regression: see HANDOFF.

# Why these three

Audit JUD-2026-09-21-01 (docs/audits, pending publication) measured what the corpus actually constrains:
21 targeted weakenings of the judge and of the law were run against the full corpus. It refused 11 of 14
verifier mutations and 4 of 7 law mutations. Three verifier mutations survived, and they are not ordinary
gaps — each one removes a property the separation of powers is defined by:

- **M6** — read policy.mk from the commit under judgment instead of the trusted ref. Reproduced end to end:
  once merged, an ordinary feature branch ships `REQUIRED_CHECKS_ENFORCED := unit_tests`, the required set
  drops from 15 to 1, and a change that rewrites a committed test is reported merge_eligible.
- **M9** — stop stripping the run's own identity from spawned processes (audit J-1's mechanism).
- **M13** — score a check that policy.mk marks required as if it were advisory, so `required` in
  result.json becomes a label with no effect.

Each of the three files below is red under exactly one of those mutations and green without it.

# What they deliberately do not do

They add files; they modify none. `test_a_spawned_process_sees_no_inherited_identity_j01` stays exactly as
it is — it still uniquely covers membership of the INHERITED_IDENTITY constant, which the new case does not
assert. Removing it would be an H1 violation and would lose real coverage.

HANDOFF: the required whole-tree gate has not been run on this branch — the author is also the auditor who
raised the finding these tests close, and the recheck was handed to a role with whole-tree authority
(see HANDOFF-gate-recheck). What that recheck must show: `verifier_selftest` passing the trusted corpus AND
its added files, the second half proving these three ran. The tests were written by three separate agents,
each self-verified, then rejected by an independent corpus-admission reviewer for over-fitting (a benign
refactor of the verifier turned them red), reworked, and re-verified by three further agents in fresh
sandboxes. Three nits were accepted and recorded rather than fixed: a diagnosability trade-off in
test_identity_isolation_j4 (under M9 the headline failure is now the reordered unit_tests assertion), a
`None` ctx passed to run_in (an AttributeError rather than a clean failure if run_in ever reads ctx), and a
docstring in test_required_set_effect_j4 whose probed tuple orders do not match the gate's emission order.
