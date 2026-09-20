# Merge gate. `make gate` loads the verifier from VERIFIER_REF (the trusted branch) and lets it judge
# SUBJECT against BASE, reading committed objects only. The candidate never evaluates itself:
# a change to scripts/, policy.mk or this file takes effect only after it is merged (docs/agents-policy.md §7).
# Individual `make check-*` targets run the working copy's verifier for fast local feedback; they are
# not the merge decision — CI's gate job (.github/workflows/gate.yml) is.

include policy.mk

SHELL       := /bin/bash
PY          ?= python3
SUBJECT     ?= HEAD
VERIFIER_REF ?= $(shell git rev-parse -q --verify "$(MAIN)^{commit}" >/dev/null 2>&1 && echo "$(MAIN)" || echo "origin/$(MAIN)")
BASE        ?= $(shell git merge-base "$(SUBJECT)" "$(VERIFIER_REF)" 2>/dev/null)
# The branch only cross-checks the record's TYPE. When SUBJECT is not HEAD the checked-out branch says
# nothing about the change being judged, so it is not passed (audit EV-05): the type comes from the record.
ifeq ($(SUBJECT),HEAD)
BRANCH      ?= $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null)
else
BRANCH      ?=
endif
GATE_OUT    ?= .gate/result.json
GC_ARGS      = --subject "$(SUBJECT)" --base "$(BASE)" --policy-ref "$(VERIFIER_REF)" $(if $(BRANCH),--branch "$(BRANCH)")

.PHONY: test selftest gate gate-advisory credits audit-select \
        check-type check-evidence check-tests check-masking check-sunset check-records check-ledger check-selftest

## test: the business suite (working tree; the gate runs it on the committed subject instead)
test:
	$(PY) -m pytest -q tests

## selftest: the verifier's own regression corpus (the audit's counterexamples are fixtures here)
selftest:
	$(PY) -m pytest -q scripts/tests

# Load the trusted verifier into $(1). `set -o pipefail` is written out because GNU make 3.81 — the macOS
# default — ignores .SHELLFLAGS, so without it a failed `git archive` is hidden by tar's exit 0 (audit T4).
define load_verifier
set -o pipefail; \
if ! git archive --format=tar "$(VERIFIER_REF)" scripts/gate_checks.py | tar -xf - -C "$(1)"; then \
  echo "ERROR   gate: cannot load the verifier from $(VERIFIER_REF) — fetch $(MAIN) first, or pass VERIFIER_REF=<ref>" >&2; \
  rm -rf "$(1)"; exit 3; \
fi
endef

## gate: the merge decision — trusted verifier from VERIFIER_REF judges SUBJECT; exit 0 only if merge_eligible
gate:
	@tmp=$$(mktemp -d); \
	$(call load_verifier,$$tmp); \
	$(PY) "$$tmp/scripts/gate_checks.py" gate $(GC_ARGS) --profile enforced --out "$(GATE_OUT)"; \
	rc=$$?; rm -rf "$$tmp"; exit $$rc

## gate-advisory: the same run against the advisory required set — informational, never authorizes a merge
gate-advisory:
	@tmp=$$(mktemp -d); \
	$(call load_verifier,$$tmp); \
	$(PY) "$$tmp/scripts/gate_checks.py" gate $(GC_ARGS) --profile advisory --out "$(GATE_OUT:.json=-advisory.json)"; \
	rc=$$?; rm -rf "$$tmp"; exit $$rc

## check-<group>: one group with the working copy's verifier (type, evidence, tests, masking, sunset, records, ledger, selftest)
check-type check-evidence check-tests check-masking check-sunset check-records check-ledger check-selftest:
	@$(PY) scripts/gate_checks.py check $(subst check-,,$@) $(GC_ARGS) --profile enforced

## credits: deletion candidates that earn ledger credit (§4) — vulture output only, not a policy-scored list
credits:
	@command -v vulture >/dev/null || echo "NOT_RUN credits: install vulture for zero-reference candidates; duplicate blocks need jscpd or pylint --enable=duplicate-code"
	-@command -v vulture >/dev/null && vulture src/ --min-confidence 80   # exits 1 when it finds candidates: that is the output, not an error

## audit-select: draw the audit sample for SUBJECT (§7); needs AUDIT_SALT from outside the repo
audit-select:
	@$(PY) scripts/gate_checks.py audit-select $(GC_ARGS) --profile enforced
