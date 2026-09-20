# Merge gate. Every target here is a check named in AGENTS.md; docs/agents-policy.md §7 says
# which are live and which still print TEXT-ONLY. Parameters come from policy.mk (H5).

include policy.mk

SHELL  := /bin/bash
PY     ?= python3
BRANCH := $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null)
BASE   ?= $(shell git merge-base HEAD $(MAIN) 2>/dev/null || git merge-base HEAD origin/$(MAIN) 2>/dev/null)
GC     := $(PY) scripts/gate_checks.py

export MAIN BRANCH BASE ALLOWANCE_DEFAULT BANK_CAP MUTATION_MIN SUNSET_SHORT SUNSET_LONG SUNSET_MAX \
       SUNSET_GRACE RENEWALS_MAX DEP_MIN_AGE AUDIT_RATE REAUDIT_RATE ATTEST_MIN_PATHS \
       AUDITOR_OVERTURN_MAX AUDIT_ALWAYS_PATHS POLICY_FILES

GATE_TARGETS := check-type check-masking check-tests check-ledger check-sunset check-records

.PHONY: test gate credits audit-select $(GATE_TARGETS)

## test: run the suite
test:
	$(PY) -m pytest -q

## gate: everything CI runs; fails if any live check refuses, and counts the text-only ones so they stay visible
gate:
	@fail=0; text=0; \
	for t in $(GATE_TARGETS); do \
	  out=$$($(MAKE) --no-print-directory $$t 2>&1); rc=$$?; printf '%s\n' "$$out"; \
	  [ $$rc -eq 0 ] || fail=$$((fail+1)); \
	  printf '%s\n' "$$out" | grep -q 'TEXT-ONLY' && text=$$((text+1)); \
	done; \
	echo "gate: $$fail refused; $$text of $(words $(GATE_TARGETS)) targets still contain text-only checks (docs/agents-policy.md §7.1)"; \
	[ $$fail -eq 0 ]

## check-type: branch prefix is the change type; the diff touches only that type's paths (§1, H5)
check-type:
	@$(GC) type

## check-masking: no error-masking constructs or suppression markers added (§2)
check-masking:
	@if command -v ruff >/dev/null; then \
	  ruff check --quiet --select E722,BLE001,S110,S112,S113 src/ && echo "ok    check-masking/ruff: E722 BLE001 S110 S112 S113 clean"; \
	else echo "TEXT-ONLY check-masking/ruff: ruff not installed (pip install ruff)"; fi
	@$(GC) masking

## check-tests: H1 (no existing test modified, tests committed before src), mock allowlist; red-before-green and mutation are text-only (§3)
check-tests:
	@$(GC) h1
	@$(GC) mocks

## check-ledger: complexity ledger from the diff vs allowance (§4, H3) — text-only until the ledger tool exists
check-ledger:
	@echo "TEXT-ONLY check-ledger: ledger not automated yet — debits/credits per AGENTS.md §4, allowance $(ALLOWANCE_DEFAULT), bank cap $(BANK_CAP)"
	@echo "         suggested tools: jscpd or pylint --enable=duplicate-code (duplicate blocks), vulture (zero references), a public-symbol diff"

## check-sunset: tag grammar, tree-wide expiry with grace, untagged TODO/FIXME/HACK on added lines (§5, H3)
check-sunset:
	@$(GC) sunset

## check-records: docs/changes/<type>-<slug>.md has TYPE/WHY/SEARCHED/DEP as required; DEP lines exist on the registry (§6)
check-records:
	@$(GC) records
	@$(GC) deps

## credits: deletion candidates that earn ledger credit (§4)
credits:
	@command -v vulture >/dev/null || echo "TEXT-ONLY credits: install vulture for zero-reference candidates; duplicate blocks need jscpd or pylint --enable=duplicate-code"
	-@command -v vulture >/dev/null && vulture src/ --min-confidence 80   # exits 1 when it finds candidates: that is the output, not an error

## audit-select: draw the audit sample for the current commit (§7); needs AUDIT_SALT from outside the repo
audit-select:
	@$(GC) audit-select
