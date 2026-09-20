# policy.mk — parameters for the merge gate. Protected (H5): changes only on a policy/ branch.
# The verifier reads this file from VERIFIER_REF (the trusted branch), never from the candidate,
# so editing it on a feature/ or renew/ branch changes nothing and is refused by protected_files.
# Mirror any change in AGENTS.md (the literal numbers there) and docs/agents-policy.md §6.

MAIN                 ?= main

# ---- files only a policy/ branch may touch (a trailing / is a prefix; a bare name matches at any depth) ----
# .gitattributes is here because it decides what `git archive` puts in the tree the gate tests (audit CR-01).
PROTECTED_PATHS      ?= AGENTS.md policy.mk tests/MOCK_ALLOWLIST docs/agents-policy.md Makefile scripts/ .claude/ .github/ .gate/ .gitattributes

# ---- which checks must PASS for merge_eligible, per profile ----
# Outcomes are PASS | FAIL | ERROR | NOT_RUN; only PASS on every required check authorizes a merge.
# Checks not listed still run and are reported (advisory). Unimplemented checks report NOT_RUN.
REQUIRED_CHECKS_ENFORCED ?= type protected_files export_integrity harness_integrity unit_tests test_inventory red_before_green h1 mocks masking_markers masking_ruff sunset records deps verifier_selftest
# The advisory profile is for watching a mechanism before it binds. It NEVER sets merge_eligible (audit EV-02).
REQUIRED_CHECKS_ADVISORY ?= type protected_files unit_tests

UNIT_TESTS_TIMEOUT   ?= 900

# ---- ledger (advisory until the ledger tool exists) ----
ALLOWANCE_DEFAULT    ?= 2
BANK_CAP             ?= 6
MUTATION_MIN         ?= 0.70

# ---- sunset ----
SUNSET_SHORT         ?= 30
SUNSET_LONG          ?= 90
SUNSET_MAX           ?= 180
SUNSET_GRACE         ?= 7
RENEWALS_MAX         ?= 2

# ---- dependencies ----
DEP_MIN_AGE          ?= 30

# ---- audit ----
AUDIT_RATE           ?= 0.20
REAUDIT_RATE         ?= 0.10
ATTEST_MIN_PATHS     ?= 3
AUDITOR_OVERTURN_MAX ?= 0.20
# Changes touching these globs are always audited. Adapt to the repository layout.
AUDIT_ALWAYS_PATHS   ?= src/**/auth* src/**/secret* src/**/subprocess* src/**/net* src/**/sql* src/**/serial*
