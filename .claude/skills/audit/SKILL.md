---
name: audit
description: Audit a merged change under this repository's AGENTS.md policy — reconstruct its rationale from artifacts alone, try to break it on a real call path, and re-run the merge gate on the recorded subject. Use whenever asked to audit, review, verify, spot-check or re-audit a merged change, a renew/ or policy/ change, a masks sunset tag, a POLICY-GAP or SUNSET-EXPIRED filing, an allowance grant, or a change selected by `make audit-select`. Also use when asked whether a change's tests are real evidence or whether its design can be explained from the code.
---

# Audit a merged change

You are the inspector, not the implementer. Your valid outputs are a **finding** (a reproducible failing test, or a located contract defect), a **costed attestation** (`NO-FINDING` plus at least three attack paths with the commands you ran), or `INCONCLUSIVE` with what was missing. "LGTM" is not an output. The cheapest valid output is one failing test on the most obvious weak path, so look there first — then cover the minimum risk surface below before attesting.

## Inputs — verified, not guessed

The audit is bound to a subject, not to a branch (the branch is gone after the merge):

- `SUBJECT` — the merged commit's SHA; `BASE` — the merge base it was gated against. Both come from the gate result (`gate-result.json` / `.gate/result.json`: `subject_sha`, `base_sha`) or from the selector's output; never from "whatever is checked out".
- The change record `docs/changes/<type>-<slug>.md` **as committed at SUBJECT** (`git show SUBJECT:docs/changes/...`); the change type is its `TYPE:` line.
- The diff: `git diff BASE SUBJECT`.
- Do not read: the implementer's session, chat, or reasoning. If any of it is in your context, say so at the top; the audit is then re-drawn.

## Procedure

### 1. RECONSTRUCT (ownership)
Before opening the change record, read the diff and the touched modules and write, in at most three sentences, what the change does and why it is built that way. Then open the record and compare with its `WHY:` line.

- The record's `WHY:` is sufficient to explain what you see → `RECONSTRUCT: adequate`.
- You could not tell what the change is for from the artifacts, or the `WHY:` contradicts the code → finding `OWNERSHIP-LOSS`, quoting your reconstruction and the `WHY:` line. Not being able to guess the *rejected alternative* is not a finding; an unexplainable design is.

### 2. BREAK (evidence) — minimum risk surface first
Write one new test on a **real in-repo call path** (no mocks outside `tests/MOCK_ALLOWLIST`) that the change should pass and does not. Cover, in this order, and record each even if it passes: the failure path of any new handler; boundary inputs of any new public symbol; the interaction between the new code and its callers; anything the change's tests mock. Then look wherever the diff makes you uneasy.

- A test fails → finding: commit it on a `test/audit-<slug>` branch and cite the file.
- Nothing fails after at least `ATTEST_MIN_PATHS` distinct paths → attestation listing each path and the exact command.
- The harness needed does not exist → `INCONCLUSIVE`, naming what is missing (this becomes a `test/` task).

### 3. RECHECK (gate)
Run the trusted verifier on the recorded pair, writing somewhere of your own so the pair you were given is not overwritten:

```
make gate SUBJECT=<sha> BASE=<sha> GATE_OUT=.gate/recheck-<slug>.json
```

`SUBJECT` is not `HEAD`, so the Makefile passes no `--branch` and the change type comes from the committed record — the audit branch you are standing on does not enter the verdict.

Run it with the same toolchain CI uses, or the recheck measures your machine instead of the change. Every tool a required check needs must be on `PATH` (`ruff`, `pytest`) and `PY` must point at the interpreter that has them. A required check reported `NOT_RUN` because a tool is missing makes `merge_eligible` false for every subject you look at; that is your environment, not a finding, and reporting it as one is the cheapest way to be overturned. If you cannot assemble the toolchain, the recheck is `INCONCLUSIVE` — say so and say which tool was missing.

Report: `verifier_provenance` (anything but `policy_ref` means the change was judged by its own copy of the judge), every required check that is not PASS **and that is not NOT_RUN for a missing tool**, every `NOT_RUN` the record leans on as evidence (`TESTS:` claiming a check the gate could not run), and any mismatch between `docs/agents-policy.md` §7.2 and what the result says actually ran.

## Output

Write `docs/audits/<type>-<slug>.md`:

```
AUDIT subject:<sha> base:<sha> type:<type>  by: fresh-instance  date: YYYY-MM-DD
RECONSTRUCT: adequate | OWNERSHIP-LOSS — <your 3 sentences> | WHY: <their line>
BREAK: FINDING tests/<file>::<test> | NO-FINDING | INCONCLUSIVE <what is missing>
  path 1: <what you attacked> — <command> — <passed|failed>
  path 2: ...
  path 3: ...
RECHECK: <gate result: n/m required PASS>; <NOT_RUN relied upon>; <table mismatches>
SEVERITY: <what the finding would have cost if merged unnoticed> | UNCOVERED: <paths you did not try>
RESULT: FINDING | NO-FINDING | INCONCLUSIVE
```

A finding becomes a `fix/` or `test/` task that reopens the change; a contract defect becomes a `policy/` task. Neither is a sanction on the implementer. Attestations are re-audited at `REAUDIT_RATE`, and an auditor is judged on overturned attestations and on regressions that escaped, not on the number of findings — write only what you actually ran.
