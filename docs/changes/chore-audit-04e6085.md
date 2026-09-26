TYPE: chore
WHY: the audit report for `04e6085` filed as a repository artifact instead of left in a session, because §7 draws every policy change into the 100% audit set and the last two that merged have no report — audit JUD-2026-09-21-01 finding J-3 counted them, and this one was on course to be the third.
TESTS: no code changed; `git diff --name-status main` is two added files under docs/. The measurements the report rests on are recorded in it, command by command: 15 measurements, 12 mutants, 2 full-corpus runs (147 passed each), 2 two-arm end-to-end gate exploits.

# What this files

`docs/audits/policy-judicial-selftest-coverage.md` — the adjudicated audit of the merged policy change
`04e6085`, drawn by `make audit-select` on a triple trigger (policy change; protected set changed; random
draw 0.119 < 0.20).

Result: **FINDING — 8 findings; the merge stands.** The change's own counterexamples reproduce count for
count and it edits nothing frozen; one finding (X-3) lands on it and owes a `test/` task. The other seven
are against the machinery around it, two of them raised by the adjudicator and by nobody earlier:

- **N-2 (CRITICAL)** — an added `scripts/tests/conftest.py` neutralises `verifier_selftest` on a policy
  change: measured `merge_eligible: true`, 15/15 required PASS, on a candidate shipping a deliberately
  weakened judge. Independently reproduced by a second, separately-tasked agent in the same hour.
- **N-1 / A-1 (HIGH)** — `MAKEFLAGS` carries the run's identity past `run_in`'s stripping, so the RECHECK
  command the audit procedure itself prescribes (`make gate SUBJECT=… BASE=…`) false-reds a correct
  subject. Reproduced here at the mechanism level with a control: identity passed as environment variables
  leaves `MAKEFLAGS` clean and the nested `make` sees nothing; passed as command-line overrides it is
  reconstructed inside the child despite the strip.

# On independence, stated plainly

The auditor, the three attackers and the adjudicator are the same model as the author of the subject, on
prompts that author wrote. That is **fresh context, not independence**; "four agents agree" is one model run
four times, not four judgments. The report says so at the top and marks every item it could not re-measure
as accepted on corroboration. An independent appointment remains unavailable in this repository — LM-5.

HANDOFF: the eight findings are not scheduled here; filing the report is. N-2 is the one that should not
wait — it is a live path to a merge-eligible weakened judge on `main` as of `65f857b`.
