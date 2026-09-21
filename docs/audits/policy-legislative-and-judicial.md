# Audit — the legislative and judicial amendments

AUDIT subject: `bf81be0` (policy/legislative-rules) and `6bf527f` (policy/judicial-process)
base: `f9c70cc` · policy ref: `main` (f9c70cc) · date: 2026-09-20
RESULT: **NO-FINDING against either amendment. FINDING against the machinery they would govern.**

## Jurisdiction, evidence and disqualification

Both subjects are **proposed, not enacted**. `main` is at `f9c70cc`; each sits on its own unmerged
branch, which is what their records say their state should be. An earlier reading of `git log` from HEAD
suggested they had merged; that was wrong and is corrected here.

The branches form a linear stack, not three parallel proposals:

```
f9c70cc (main)
 └─ bf81be0  policy/legislative-rules
     └─ 6bf527f  policy/judicial-process        ← based on unenacted legislation
         └─ 3398cbd chore/executive-delivery    ← based on an unenacted judicial procedure
```

Evidence: the two change records, the diffs against `f9c70cc`, the trees at each subject, and gate runs
performed for this audit. Tooling: pytest 9.1.1 and ruff 0.16.8 on `PATH` for every run reported here; a
run without ruff reports `masking_ruff NOT_RUN` and makes every subject ineligible, which is an
environment, not a finding.

**Disqualification.** `scripts/gate_checks.py` is the auditor's own work, and the auditor was the
executive in `f9c70cc`, the commit immediately preceding both subjects. Every finding that touches the
verifier was therefore produced by independent instances working from their own fixtures, with a second
instance attempting to refute each one. Only mechanical facts — a gate verdict, a diff, a file's contents
— are reported on the auditor's own authority. Twenty findings were raised; thirteen were put to an
adversarial reproducer; three survived as CONFIRMED, nine as PARTIAL, one was REFUTED.

## Decision on the two subjects

**Both amendments are merge-eligible.** Gated cleanly, each returns 15/15 required PASS with
`verifier_provenance: policy_ref`:

| subject | invocation | verifier_selftest | merge_eligible |
|---|---|---|---|
| bf81be0 | `make gate SUBJECT=… BASE=…` | FAIL | false |
| bf81be0 | plain `make gate` on a checkout | PASS | **true, 15/15** |
| 6bf527f | `gate_checks.py … --branch policy/judicial-process`, clean env | PASS | **true, 15/15** |

The first row is not evidence against the amendment. It is the finding below.

No finding is issued against the text of either amendment. Both are careful documents. Both declare their
own scope limits, both record `TESTS: NOT_RUN` or text-checks-only rather than claiming verification they
did not perform, and both state that their author does not approve them and that independent acceptance
is required. That is the correct posture and it is rare.

## J-1 · The audit procedure's own command fabricates a failure · P0 · machinery

`.claude/skills/audit/SKILL.md` instructs the auditor to recheck with
`make gate SUBJECT=<sha> BASE=<sha> GATE_OUT=…`. GNU make places every command-line variable in the
environment of every recipe. `gate_checks.py` builds the corpus subprocess environment as
`{**os.environ, …}`, popping only two pytest variables. The corpus fixture at
`scripts/tests/test_plumbing_v04.py:90` spawns a nested `make gate` inside a throwaway repository, which
reads the inherited `SUBJECT`/`BASE` as its own inputs — commits that do not exist there — and the
inherited `GATE_OUT`, which redirects the nested write away from the path the fixture then asserts on.

Two independently sufficient causes, isolated by an independent instance: `SUBJECT`+`BASE` alone
reproduces it, and `GATE_OUT` alone reproduces it. The judicial amendment's new instruction to "use an
unused output path" therefore triggers it even if the auditor knows to unset the other two.

Consequence: an auditor following the procedure reports `verifier_selftest FAIL` against **every policy
change**, and no other change type, because `verifier_selftest` runs only for policy. The judiciary's own
tooling produces false refusals selectively against the one branch that can change the judiciary. The
judicial amendment forbids "fabricating a failure to finish an audit"; the procedure fabricates one on
its own.

Attribution: the Makefile, the verifier and the SKILL.md line are all the auditor's work from v0.4.

## LM-1 · A candidate-supplied conftest turns a red suite green · P0 · machinery · CONFIRMED

A `tests/conftest.py` **added** by the change, with an autouse fixture calling
`request.node.add_marker(pytest.mark.xfail(...))`, makes `unit_tests` report PASS while the committed
acceptance is genuinely red. Observed: `14/14 required PASS`, `merge_eligible: true`, with
`tests/test_app.py::test_add` failing `assert 2 == 3` the moment the conftest is removed from the
exported tree.

Three mechanisms combine, none of which the law anticipates:

- `check_h1` inspects statuses `M`/`D`/`R` only, so a status-`A` conftest is invisible to the frozen-set rule
- `harness_integrity` refuses only the nine names in its hook denylist; an autouse fixture is not one
- the masking scan requires a literal `@` before `pytest.mark.xfail`, so `add_marker(...)` passes

Controls both behave correctly: the byte-identical change without the conftest is refused
(`FAIL unit_tests`, 13/14), and the same attack written as a named hook is refused
(`FAIL harness_integrity`, 13/14). So this is a hole in a working rule, not a rule that refuses nothing.

Attribution: pre-existing machinery, byte-identical at `main` and at both subjects. It is the residue the
auditor documented in `docs/agents-policy.md` §7.6 — "a conftest.py that subverts reporting without one of
the listed hooks is not detected." Writing a limitation down does not make it acceptable; an independent
instance turned the documented residue into a working exploit on the first attempt.

## LM-2 · `TYPE: test` disables H1 entirely · P0 · machinery · CONFIRMED

`check_h1` skips the frozen-set rule whenever the change type is `test`. A change whose record declares
`TYPE: test` deleted two of three assertions from a committed test with no approver, no `ACCEPTANCE:`
entry and no approval of any kind, and the gate returned `14/14 required PASS`, reporting
`PASS h1 — "no committed test modified"`. The byte-identical edit declared `TYPE: fix` is refused
(`FAIL h1`, `test_inventory`, `red_before_green`).

The only residual protection is pytest node-id survival: deleting the whole file is caught by
`test_inventory`; hollowing out its assertions is not.

This is the point at which the legislative amendment and the machinery diverge most sharply. The new H1
says revisions "require §3 approval", and §3 requires an approver designated before the edit, other than
the implementer or the proposer. The machinery has no representation of any of that: `parse_record`
recognises `TYPE|WHY|SEARCHED|DEP|TESTS|ALLOWANCE|BLOCKED`, so an `ACCEPTANCE:` line is never read. The
law's safeguard is invisible and the law's exemption is unconditional.

Attribution: pre-existing machinery. Under the prior law a `test/` branch was the adjudicating forum and
the exemption was defensible. The amendment changes what `test/` means without the machinery following.

## LM-3 and LM-4 · The law grants two powers no branch can exercise · P1 · both · PARTIAL

Each was reproduced with its control; both verifiers reduced the severity from P0 because the effect is a
dead end rather than an authorization, and that reduction is accepted.

**Revising a verifier counterexample.** The amendment routes protected acceptance, "including
`scripts/tests/` and harness policy", to `policy/`. The `policy/` route is refused by `h1`
(`is_frozen_test` covers `scripts/tests/`, and the exemption is only for type `test`), whose printed safe
path says "a test/ branch adjudicates"; the `test/` route is then refused by `type` and
`protected_files`, because `scripts/` is protected. No branch type can modify a file under
`scripts/tests/`. Control: the same `policy/` branch *adding* a corpus file passes.

**Harness policy outside the protected set.** §1's new policy row grants "protected set **and harness
policy under H6**". For the H6 items not in `PROTECTED_PATHS` — `pyproject.toml` / `setup.cfg` /
`pytest.ini` sections, a root `conftest.py` — a `chore/` change is refused by `harness_integrity`, whose
safe path says "move this to a policy/ branch"; the `policy/` change is then refused by `type` and
`protected_files`, because `pyproject.toml` is not a policy file. Control: a `policy/` branch changing
`SUNSET_GRACE` in `policy.mk` passes.

Both are circular refusals in which each check's safe path names the route the other check closes.

## LM-8 · One character invalidates a truthful record · P1 · machinery · CONFIRMED

`is_placeholder` is `not value or "<" in value`. Any record value containing an ASCII `<` is treated as an
unfilled template placeholder. A complete, truthful `WHY:` containing a bound such as "n <= 3" fails
`records`, and the refusal reprints the template line without naming the character. The byte-identical
line with "at most 3" passes. The union law is full of comparison language an author would reproduce
naturally. Attribution: pre-existing machinery.

## What the audit establishes about the separation instruction

Both amendments were drafted under an instruction forbidding their authors to read the other branches,
and both say so. The legislative record: "No implementation, test, CI, hook, audit procedure or audit
result was read or assessed." The judicial record: "No legislative document, implementation, verifier
source, existing test, or historical audit finding was read."

Of the three lenses in this audit, two were confined to a single layer and one was given the whole tree
and asked only whether the enacted law matches the enforced law. **All three CONFIRMED findings came from
that third lens.** The two single-layer lenses produced careful observations and no confirmed P0.

That is the empirical result, and it supports a distinction the instruction elides: separation of powers
restricts who may **exercise** a power, not who may **read** the law. A judge who reads the statute is not
legislating. Federalist 47's concern is the accumulation of power in the same hands; reading accumulates
knowledge, not power. Enforced as a reading ban, the separation produced two internally careful
amendments that could not be checked against each other or against the machinery that would enforce them
— and the checking, when finally performed by an unrestricted reader, found three P0s in an afternoon.

## Disposition

- **The amendments:** no finding. Both are merge-eligible. Their own records correctly state that
  enactment requires an independent acceptance, and this audit is a read, not that acceptance — the
  repository has no designated approver and no field in which one could be recorded, which is itself
  finding LM-5 (PARTIAL: every "independent approval" clause in the union law is honour-based).
- **Before enactment**, the three machinery defects above should be resolved or the amendments' matching
  clauses marked as pending, because enacting LM-2's text while `TYPE: test` remains an unconditional
  exemption puts a safeguard in the constitution that the gate reports as satisfied when it is not.
- **The stack** should be rebased onto `main` as three independent changes. As it stands, the executive
  change at the top carries both policy changes in its diff against `main` and cannot pass as a `chore`.
- **J-1 is the auditor's own defect** and blocks the audit of every future policy change. It should be
  fixed before this procedure is used again.

## Where this audit has nowhere to go

Twenty findings were produced. `docs/audits/` will hold this file, and nothing reads it. No check consumes
a finding, no parameter counts one, `REAUDIT_RATE`, `ATTEST_MIN_PATHS` and `AUDITOR_OVERTURN_MAX` are read
by no code, and every gate verdict this audit relied on was written into `.gate/`, which is ignored by
`*`. The judiciary decides and discards. That is the missing first step of any correction loop: not the
absence of a proposal channel, but the absence of a record of what the rules actually did.
