# policy.mk — parameters for the merge gate. Protected by H5: change only on a policy/ branch.
# Mirror any change in AGENTS.md (the literal numbers there) and docs/agents-policy.md §6.

MAIN                 ?= main

ALLOWANCE_DEFAULT    ?= 2
BANK_CAP             ?= 6
MUTATION_MIN         ?= 0.70

SUNSET_SHORT         ?= 30
SUNSET_LONG          ?= 90
SUNSET_MAX           ?= 180
SUNSET_GRACE         ?= 7
RENEWALS_MAX         ?= 2

DEP_MIN_AGE          ?= 30

AUDIT_RATE           ?= 0.20
REAUDIT_RATE         ?= 0.10
ATTEST_MIN_PATHS     ?= 3
AUDITOR_OVERTURN_MAX ?= 0.20

# Changes touching these globs are always audited. Adapt to the repository layout.
AUDIT_ALWAYS_PATHS   ?= src/**/auth* src/**/secret* src/**/subprocess* src/**/net* src/**/sql* src/**/serial*

# Files only a policy/ branch may touch.
POLICY_FILES         := AGENTS.md policy.mk tests/MOCK_ALLOWLIST docs/agents-policy.md
