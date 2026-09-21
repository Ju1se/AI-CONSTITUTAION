# Change record — chore/audit-policy-amendments

TYPE: chore
WHY: keep the audit of the two proposed amendments in the repository rather than outside it, because both
amendments' records say they require an independent assessment and this is the only written one.

TESTS: none — documentation only. The gate run on this branch is the evidence that a docs-only change is
a complete change.

HANDOFF: the report's three CONFIRMED findings are against the machinery, not the amendments, and two of
them (LM-1 conftest, LM-2 the TYPE: test exemption) are in scripts/gate_checks.py. They are unfixed. Do
not read the amendments' merge-eligibility as a clean bill for the system they would govern.
