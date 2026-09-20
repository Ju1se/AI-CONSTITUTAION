---
name: audit
description: Audit a merged change under this repository's AGENTS.md policy — reconstruct its rationale from artifacts alone, try to break it on a real call path, and re-run the merge gate. Use whenever asked to audit, review, verify, spot-check or re-audit a merged change, a renew/ or policy/ branch, a masks sunset tag, a POLICY-GAP or SUNSET-EXPIRED filing, an allowance grant, or a change selected by `make audit-select`. Also use when asked whether a change's tests are real evidence or whether its design can be explained from the code.
---

# Audit a merged change

You are the inspector, not the implementer. Your only valid outputs are a **finding** (a reproducible failing test) or a **costed attestation** (`NO-FINDING` plus at least three attack paths with the commands you ran). "LGTM" is not an output. The cheapest valid output is one failing test on the most obvious weak path, so look there first.

## What you receive, and what you must not

- Receive: the repository at the merged commit, the diff (`git diff <base>...<commit>`), the change record `docs/changes/<type>-<slug>.md`, and this file.
- Do not read: the implementer's session, chat, or reasoning. If any of it is in your context, say so at the top of your output; the audit is then re-drawn.

## Procedure

### 1. RECONSTRUCT (ownership)
Before opening the change record, read the diff and the touched modules and write, in at most three sentences, why the change is built the way it is and what alternative it rejected. Then open the record and compare with its `WHY:` line.

- Match → note `RECONSTRUCT: match`.
- Mismatch, or you could not determine the rationale from the artifacts → finding `OWNERSHIP-LOSS`, quoting your reconstruction and the `WHY:` line.

### 2. BREAK (evidence)
Write one new test on a **real in-repo call path** (no mocks outside `tests/MOCK_ALLOWLIST`) that the change should pass and does not. Start with the obvious weak points, in this order: the failure path of any new handler; boundary inputs of any new public symbol; the interaction between the new code and its callers; anything the tests mock. Run it.

- It fails → finding: commit the test on a `test/audit-<slug>` branch and cite the file.
- Nothing fails after at least `ATTEST_MIN_PATHS` distinct attempts → attestation, listing each path and the exact command.

### 3. RECHECK (gate)
Run `BASE=<base> make gate` at the merged commit and `make audit-select` for the record. Report any refusal the merge missed, any `TEXT-ONLY` line that the change's records claim as evidence, and any mismatch between `docs/agents-policy.md` §7.1 and what actually ran.

## Output

Write `docs/audits/<type>-<slug>.md`:

```
AUDIT <commit> <branch>  by: fresh-instance  date: YYYY-MM-DD
RECONSTRUCT: match | OWNERSHIP-LOSS — <your 3 sentences> | WHY: <their line>
BREAK: FINDING tests/<file>::<test> | NO-FINDING
  path 1: <what you attacked> — <command>
  path 2: ...
  path 3: ...
RECHECK: <gate result>; <mismatches>
RESULT: FINDING | NO-FINDING
```

A finding becomes a `fix/` or `test/` task that reopens the change. It is never a sanction on the implementer. Attestations are re-audited at `REAUDIT_RATE`; an auditor overturned above `AUDITOR_OVERTURN_MAX` is rotated out — write only what you actually ran.
