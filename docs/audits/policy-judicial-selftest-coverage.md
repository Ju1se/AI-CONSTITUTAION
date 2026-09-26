# Adjudication — `04e6085` "policy: pin the three trust properties the corpus left open"

```
ADJUDICATION subject:04e6085 base/policy-ref:e0a3ee2 merge:65f857b (PR #1) type:policy
  by: fresh-instance (NOT an independent appointment — see below)   date: 2026-09-22
PROCEDURE EXECUTED: blob 7fa35fc82382442b2b5fcf5b668119668a509e22
  (`git show main:.claude/skills/audit/SKILL.md`) — verified first-hand, not taken on report
INPUTS ADJUDICATED: 1 auditor report, 3 attack reports, all four the same model as the author
VERDICT ON THE CHANGE: the merge stands. Its three properties are genuinely pinned, its kill-power
  claims reproduce count for count, it edits nothing frozen, and it measurably closes what it claims.
RESULT: FINDING — 8 findings, 1 of which lands on the change itself (X-3)
SEVERITY: CRITICAL N-2 · HIGH X-1, A-1 · MED-HIGH A-2 · MED X-2, N-1 · LOW X-3, X-4, A-3
```

Two of the eight findings are new to this adjudication and were raised by nobody in the chain: **N-2**, a
complete bypass of `verifier_selftest` on a policy change, which I measured end to end; and **N-1**, a defect
in the audit procedure's own RECHECK command. Two of the six inherited findings I **corrected** rather than
ratified: I rejected half of A-3, and I **overturned the auditor's `BREAK: NO-FINDING`** — attacker 2's
brittleness result is a finding under the standard this repository actually applied to these files, and the
auditor tested it against the wrong standard.

---

## Independence — stated as the task requires

I am a **fresh context, not an independent appointment**. I am the same model as the author of the change
under audit, as the auditor whose report I am adjudicating, and as the three attackers whose results I am
weighing. My opening prompt was written by that author. I have not seen the author's session or reasoning;
I reconstructed judgment from artifacts and from my own measurements alone. This is **fresh context, not
independence**, and it should be read that way — in particular, *"four agents agree"* is not four independent
judgments. It is one model run four times on prompts written by the party with an interest in the outcome.
Where I could re-measure instead of relying on that agreement, I did; where I could not, the verdict below
says "accepted on corroboration" and the item appears in UNCOVERED.

**Procedure on duty.** I verified both blobs myself: main's audit SKILL is
`7fa35fc82382442b2b5fcf5b668119668a509e22`; the working tree's is
`c9743c015e99dd645e3936c6b76328b9c2378b43`, from the unmerged branch
`policy/judicial-accountability-federalist` (HEAD `db149c4`, branched from `e0a3ee2`, never merged). **The
audit skill description loaded into my own session is the unmerged version's** — it speaks of reviewing "a
disputed audit decision" and "judicial accountability under an authorized mandate", language absent from
main's `7fa35fc`. I read main's blob explicitly and adjudicated under it; nothing from the unmerged amendment
was applied. This is **audit JUD-2026-09-21-01 finding J-1 reproducing itself for the fifth recorded time**,
in my session as much as in the auditor's: the procedure on duty is decided by the checkout, not by the ref
in force.

**Sandbox discipline.** No tracked file modified, nothing committed, no branch checked out, nothing pushed.
Final `git status --porcelain` empty; HEAD still `db149c4` on `policy/judicial-accountability-federalist`.
All experiments ran on `git archive` exports of main under
`/private/tmp/claude-501/-Users-scottxie-Desktop-AI-CONSTITUTAION/04901109-5ac8-4371-a5de-e1ba9b8af493/scratchpad/audit-sandbox/adjudicator/`
(below: `$SB`). I wrote nothing into `.gate/` and did not touch the artifacts already there.

**Filing.** The procedure's Output step asks for `docs/audits/policy-judicial-selftest-coverage.md`. That path
is tracked and I was instructed not to modify tracked files, so this is delivered as text. See **issue 16**.

---

## What I measured myself

Every verdict below rests on one of these, not on the reports. Toolchain throughout: `PATH` prefixed with the
scratchpad venv — Python 3.13.14, pytest 9.1.1, ruff 0.16.8, all present, so the procedure's environmental
escape clause is never in play.

| # | What | Result |
|---|---|---|
| 1 | Procedure blobs | main `7fa35fc8…`; working copy `c9743c01…`; read main's, followed it |
| 2 | Kill power M6 / M9 / M13 against the three new files | 1 failed·1 passed / 2 failed / 1 failed·2 passed — matches the record exactly |
| 3 | H1: `git diff --name-status e0a3ee2 04e6085` | 4× `A`; `--diff-filter=MDRTUXB` empty; `git diff 04e6085 65f857b` empty |
| 4 | Judge byte-identity | `scripts/gate_checks.py` = `f5c3f11a…` at all three commits; `policy.mk`, `docs/agents-policy.md` likewise |
| 5 | MAKEFLAGS minimal repro | `MAKEFLAGS='GATE_OUT=… BASE=… SUBJECT=…'` survives `run_in`; nested make reads all three back |
| 6 | The exact fixture A-1 names | clean env → **1 passed**; `MAKEFLAGS=…` alone → **1 failed**, *"SUBJECT '04e6085' is not a commit in this repository"* |
| 7 | A-1's remedy vs. the subject's own case | `+MAKEFLAGS, MFLAGS` → `test_identity_isolation_j4.py` **2 passed** — remedy unblocked |
| 8 | Hardening with `GIT_DIR` | **1 failed**, *"fatal: not a git repository: 'leaked-git_dir'"* |
| 9 | `check_red_before_green` neutered to always PASS, **full corpus** | **147 passed in 699.12s** — the mutant survives everything |
| 10 | Corpus grep for `red_before_green` | 2 hits: a `policy.mk` text assertion, and an explicit *exclusion* |
| 11 | `PYTEST_ADDOPTS` dropped from the constant | 3 j4 files + the `j01` membership case → **8 passed** |
| 12 | The `PYTEST_ADDOPTS` **exploit** | **merge_eligible=True, rc=0, ineligible_reasons=[]** on a change that breaks a committed test |
| 13 | `type` dropped from the tally | 3 j4 files **7 passed**; `test_gate_checks.py` **21 passed** |
| 14 | Attacker 2 cases A / B / M / C | all four reproduce; M **misdiagnoses** as an M6 violation |
| 15 | **Added `scripts/tests/conftest.py` on a policy branch** | **verifier_selftest PASS, 15/15, merge_eligible=True, rc=0** on a gutted judge |

---

## Findings ledger

| ID | Finding | Verdict | Class | Task |
|---|---|---|---|---|
| **N-2** | An added `scripts/tests/conftest.py` neutralises `verifier_selftest` on a policy change | **CONFIRMED · CRITICAL** | pre-existing, unrelated in origin — but voids the subject's premise | fix/ + test/ + policy/ |
| **X-1** | `PYTEST_ADDOPTS` / `PYTEST_PLUGINS` membership pinned by nothing; exploitable to full merge authorisation | **CONFIRMED · HIGH** | pre-existing, **not covered** by the subject | test/ |
| **A-1** | `MAKEFLAGS` carries the gate's identity past `run_in` | **CONFIRMED · HIGH** | pre-existing, **not covered** by the subject | fix/ + test/ |
| **A-2** | §7.2's `red_before_green` row; the check has zero counterexample coverage | **CONFIRMED · MED-HIGH** | pre-existing, unrelated | policy/ + test/ |
| **X-2** | 13 of 15 required checks droppable from the tally in silence | **CONFIRMED · MEDIUM** | pre-existing, **disclosed**, narrowed by 2 | test/ |
| **N-1** | RECHECK's prescribed command judges a merged policy change by a corpus containing it | **CONFIRMED · MEDIUM** | procedure defect | policy/ |
| **X-3** | Rendering coupling in `test_policy_provenance_j4.py` | **CONFIRMED · LOW-MED** | **defect of this change** | test/ (or policy/ + ACCEPTANCE) |
| **X-4** | The poisoning design reds when a name the gate itself reads is added | **CONFIRMED, NARROWED · LOW** | **defect of this change** | fold into X-3 |
| ~~A-3b~~ | "`verifier_selftest`'s added-files fixtures are uncredited" | **REJECTED** | — | — |
| **A-3** | §7.2's `verifier_selftest` row omits the added-files half from its *scope sentence* | **CONFIRMED IN PART · LOW** | pre-existing, documentation only | policy/ |

**Findings are not a score.** Three of the four agents' attacks failed on their primary axis, and those
failures are the best evidence in this file that the subject is sound: attacker 3 pressed five vacuity
hypotheses and got none; attacker 1 tried to weaken the provenance property and proved it tight; the
auditor's six paths found nothing in the diff. I say so as a result, not as a consolation.

---

## The verdict on the change itself

**The merge stands.** Independently of the reports I confirmed that the three counterexamples are red under
exactly the mutations they name and green without them, that the change edits nothing frozen and the merge
smuggled nothing, and that its scope limits are stated rather than papered over. The auditor's end-to-end
pair — a verifier that reads its own law from the commit under judgment was `merge_eligible` **before** this
change and refused **after** it — is the strongest single piece of evidence for the change; I did not
re-run it, and it is corroborated by the existence of the mechanism it turns on
(`test_trust_gaps_v04.py:118`) and by three agents independently reproducing the same kill power.

One finding lands on the change (X-3, with X-4 in its train). Under the procedure's closing sentence — *"A
finding becomes a `fix/` or `test/` task that reopens the change"* — 04e6085 is reopened **in that procedural
sense only**: a `test/` task is owed. Nothing about its verdict, its evidence, or its merge is disturbed.

---

## The three findings worth reading in full

### N-2 — two lines neutralise the only mechanical limit on a change to the judge

Both arms are a `policy/` branch shipping a deliberately weakened judge (`check_type` rewritten to return
PASS unconditionally), which the trusted corpus does catch.

| arm | added file | `verifier_selftest` | verdict |
|---|---|---|---|
| A | — | **FAIL** | `merge_eligible False`, rc 1 |
| B | `scripts/tests/conftest.py` (2 lines) | **PASS** — *"compiles, passes the trusted corpus"* | **`merge_eligible True`, rc 0, `ineligible_reasons []`** |

```python
# scripts/tests/conftest.py — the whole of arm B's addition
def pytest_sessionfinish(session, exitstatus):
    session.exitstatus = 0
```

Every guard misses it, and I confirmed each by reading the code:

* `check_verifier_selftest` restores **only the paths listed at the policy ref**, so a `conftest.py` absent
  there is neither overwritten nor removed — and pytest auto-loads it from the rootdir chain, so it decides
  the outcome of the trusted-corpus run.
* The added-files half never sees it: `added` is filtered to basenames starting with `test_`.
* `check_h1` does not fire — adding a file is not `M`, `D` or `R`.
* `check_protected_files` does not fire — `scripts/` is protected, and `policy` is the one type permitted to
  touch protected paths.
* `check_harness_integrity`, whose denylist `\bdef\s+(pytest_\w+)` **would** catch this conftest on any other
  branch, returns PASS at its first line for `ctx.type == "policy"`.

The design knows the class exists. On a policy change the check prints *"the harness files are the protected
set's business"* and concedes that *"a conftest or an imported module reaching the verdict by a route no
pattern anticipates is not detected here; **the audit BREAK step is the compensating control**"*. What is
disclosed nowhere is that `verifier_selftest` — the mechanism that is supposed to *be* the policy-change
guard — falls to the same route. §7.2's row tells a reader the corpus is restored over whatever the candidate
ships and is therefore authoritative. It is not.

**And the nominated compensating control is not operating.** `docs/audits/` on main holds no report for
`policy-judicial-selftest-coverage`, `policy-adoption-prerequisites`, `policy-gate-dir` or
`policy-v04-evidence-tree` (finding J-3); and A-1 together with N-1 mean an auditor who follows RECHECK
literally on a policy change gets a red result on a correct subject, for two independent reasons. A control
that is skipped, and that false-reds when performed, is not a control. **The three findings compose into a
complete failure mode**, and that composition — not any one of them — is the most important thing in this
report.

### X-1 — the two names nobody pins, and what they are worth

`INHERITED_IDENTITY` holds ten names. `test_adoption_prerequisites.py:192` asserts membership of **eight**,
omitting `PYTEST_ADDOPTS` and `PYTEST_PLUGINS`. The only occurrence of either name anywhere in
`scripts/tests/` is a **prose comment** at `test_identity_isolation_j4.py:118`. Drop `PYTEST_ADDOPTS` from
the constant and the three new files plus the `j01` membership case are **8 passed**.

I did not accept attacker 1's severity claim; I tested it, and found their own demonstration weaker than
stated and the true exploit stronger. Their fixture breaks the change's *own new test*, which flips
`unit_tests` FAIL → PASS but leaves `merge_eligible` **False**, because deselecting the new test also makes
`red_before_green`'s base run collect nothing. The complete exploit breaks an **already-committed** test:

```
[main, unmutated]        plain → merge_eligible=False rc=1 ;  +PYTEST_ADDOPTS → merge_eligible=False rc=1
[PYTEST_ADDOPTS dropped] plain → merge_eligible=False rc=1 ;  +PYTEST_ADDOPTS → merge_eligible=True  rc=0
                                                               required-non-PASS=[]  reasons=[]
```

Full merge authorisation, silently, on a change that breaks committed acceptance — available to anyone who
can set the gate process's environment, the day an amendment tidies either name out of the tuple.

**This is not the subject's defect.** The gap is identical before and after, the file's docstring says `j01`
"asserts that **eight specific names** are members", and eight-of-ten is arithmetic the procedure's own
diff-first reading surfaces. Attacker 1's charge of *misleading by omission* is **rejected**. The record's
looser sentence — `j01` "still uniquely covers membership of the `INHERITED_IDENTITY` constant" — is
imprecise, but "uniquely" is about *which fixture* covers membership, not how much of it, and the
co-committed docstring in the same diff carries the true number. **Not OWNERSHIP-LOSS.**

### X-3 — where I overturn the auditor

The auditor ran attacker 2's experiment as its own path 5, got the same red, and filed it under UNCOVERED
rather than as a finding, reasoning that *"the record's refactor-tolerance claim lists four specific
refactors and does not claim tolerance to this one, so the record does not overclaim."*

That tests the record for **honesty**, which it passes. But honesty of the record is not the standard this
repository applied to these files. The standard is in the change's own HANDOFF: they were *"rejected by an
independent corpus-admission reviewer for over-fitting (**a benign refactor of the verifier turned them
red**), reworked, and re-verified."* Three of the four repaired refactors live in or feed the **same two
helpers** attacker 2 broke. **The repair reached the comparisons and stopped at the extraction**, so the
defect the reviewer rejected the draft for is still present in the same helpers, in a form the four
enumerated refactors happen to miss. Applying the record-honesty test to a defect the admission test governs
is the wrong test — and it is why the auditor reported `BREAK: NO-FINDING`.

I reproduced the coupling in four directions, one line each:

| edit at `gate_checks.py` | effect |
|---|---|
| `"protected set:"` → `"protected paths:"` (label matches the parameter it echoes) | **2 failed** — both tests, *control included* |
| per-file FAIL line → `f"in the protected set: {f}"` | 1 failed, `assert 2 == 1` |
| `' '.join(…)` → `', '.join(…)` | 1 failed, and it **misdiagnoses**: reports *"the run applied […]; the trusted ref assigns […]"* — the exact shape of an M6 violation, caused by a comma |
| reword the **advisory** `mutation` NOT_RUN string | 1 failed, *"the mutation check quoted no threshold"* |

`git grep` confirms the exposure is unshared: `"protected set:"` appears in `scripts/tests/` **only** in this
file, and `"mutation score"` only in this file. **The cost is what makes it a finding.** `verifier_selftest`
is required for every policy change, so a one-word reword of a detail line yields `verifier_selftest FAIL`
and `merge_eligible: false`. Unblocking means reverting the cosmetic change — or editing `scripts/tests/`,
which `check_h1` treats as **protected acceptance**: a `policy/` branch carrying an `ACCEPTANCE:` line naming
an approver the owner designated *before* the edit, with reason, exact old and new cases, and retained
evidence. **The price of renaming a printed label is a protected-acceptance revision.** That is exactly the
pressure under which a counterexample gets deleted as noise, in a repository that has already lost policy
changes to unaudited merges.

---

## Corrections to the inputs

* **Auditor, `BREAK: NO-FINDING` → overturned.** See X-3 above.
* **Auditor, A-3.** *"Fixtures for it exist and are simply not credited."* **Rejected.** The row's Evidence
  reads "EV-01, **CMP-17**, the policy-positive control", and `test_trust_gaps_v04.py:122` says in terms
  *"Traces to audit P0-3 / CMP-17"*. The table cites fixtures by audit-case id throughout; on its own
  convention the fixtures **are** credited. Only the scope-sentence omission survives.
* **Auditor, A-2.** *"Two of the three fixtures do not exist."* **Too strong.** `C01` exists; the scenario the
  row calls "no-new-test" exists as `test_trust_gaps_v04.py:180` — which builds exactly the fixture
  `red_before_green`'s FAIL branch was written for and then writes
  `failing_required(res, "masking_ruff", "red_before_green") == ["test_inventory"]`, deliberately looking
  away. The accurate charge is sharper: **the corpus constructs the scenario and asserts nothing about the
  check.** My full-corpus run proves the consequence rather than inferring it.
* **Auditor, A-1 scope.** Narrowed: only a nested **`make`** is affected (`MAKEFLAGS` is inert to a nested
  python gate), and the failing fixture is `skipif`'d where `make` is absent.
* **Auditor, policy-ref default.** Correctly observed as a fact about RUN A; **elevated** by me to N-1, a
  located defect in the procedure text.
* **Attacker 1, finding 1 severity.** Their demonstration showed `unit_tests` FAIL → PASS, not merge
  authorisation; I built the construction that does flip `merge_eligible`. **Strengthened.**
* **Attacker 1, finding 2 mechanism.** *"exit_code still walks the full required list"* is true of the code
  and unreachable: `exit_code` opens with `if eligible: return 0`. The escape is silent in the exit status
  too. **Strengthened.**
* **Attacker 2, finding 2 scope.** *"It penalises hardening"* is **over-general**. I tested the hardening
  this audit actually calls for — `+MAKEFLAGS, MFLAGS` — and the file stays **green (2 passed)**. The defect
  is narrower: *adding a name the **gate's own process** reads* reds the file. **A-1's remedy is not blocked
  by X-4.**
* **Attacker 1, on the task prompt.** Removing `POLICY_REF` — the example the prompt itself suggested — *is*
  caught by the existing `j01` case. Useful correction to the prompt.

---

## Remedies, in the order I would take them

| # | Finding | Type | Sufficiently resolved when | Executor |
|---|---|---|---|---|
| 1 | **N-2** | fix/ + test/ + policy/ | `verifier_selftest` removes or neutralises any `scripts/tests/` file absent at the policy ref and not an added `test_*`; arm B is refused, arm A still is, an ordinary added counterexample still passes; §7.2's row states the residue | fix/ + test/ branches; the §7.2 edit is policy/ and always audited |
| 2 | **A-1** | fix/ + test/ | `MAKEFLAGS`/`MFLAGS` stripped (measured compatible with the subject's own case); a counterexample runs the gate under `make … SUBJECT=<sha>` and asserts a nested make sees no inherited `SUBJECT` | any agent; **workaround today:** invoke the verifier directly with explicit `--policy-ref`, or pass identity as env vars |
| 3 | **X-1** | test/ | dropping *any single name* from `INHERITED_IDENTITY` reds the corpus; ideally the end-to-end form — a change breaking a committed test, gated with `PYTEST_ADDOPTS` set, stays `merge_eligible False` | test/ branch; adds a file, touches nothing frozen |
| 4 | **A-2** | policy/ + test/ | the always-PASS `check_red_before_green` mutant no longer survives the corpus; the row's Status marks it inapplicable off feature/fix | test/ + policy/ |
| 5 | **N-1** | policy/ | RECHECK prescribes the policy ref explicitly (`VERIFIER_REF=<base>`; the Makefile already supports it) and requires the report to say which question the run answers | policy/ — and note **issue 1**: the amended file is not on duty for any checkout that predates the merge |
| 6 | **X-2** | test/ | dropping any single id from `result_json`'s tally reds the corpus — cheapest via a fixture asserting the tally is derived from the reported required set rather than filtered by id | test/ |
| 7 | **X-3 + X-4** | test/, or policy/ + `ACCEPTANCE:` | all four Case A/B/M/C edits leave the file green while M6 still reds it; adding `GIT_DIR` leaves it green while M9 still reds it | expect the protected-acceptance route |
| 8 | **A-3** | policy/ | a reader of §7.2 alone learns the added-files run exists | policy/ |
| 9 | **issue 16** | chore/ | `docs/audits/policy-judicial-selftest-coverage.md` exists at main with the RESULT line and this ledger | **the repository owner** — nobody in this chain had write authority |

---

## Verdict

```
RESULT: FINDING — 8 confirmed, 1 rejected, 1 downgraded.
  Defects OF this change:            X-3 (rendering coupling), X-4 (poisoning design)
  Pre-existing, NOT COVERED by it:   A-1 (MAKEFLAGS), X-1 (PYTEST_* membership), X-2 (tally family)
  Pre-existing, UNRELATED to it:     N-2 (conftest bypass), A-2 (red_before_green), A-3, N-1

SEVERITY: N-2 is the only finding that lets a BAD change through — merge_eligible=true, exit 0,
  15/15 required PASS on a judge that has been gutted — and it voids the premise this change's own
  WHY rests on. X-1 is the same shape one amendment away. A-1 and N-1 disable the audit that N-2's
  own code nominates as its compensating control, in a repository that has already skipped four.
  The composition is the finding: the guard is bypassable, the backstop is unperformed, and the
  procedure for performing it false-reds on correct subjects.

THE CHANGE ITSELF: correct. Its counterexamples reproduce count for count, it edits nothing frozen,
  and it measurably closes the three holes it names. X-3 reopens it only in the procedural sense
  that a test/ task is owed. Nothing here disturbs the merge of 04e6085.
```

*Attestation cost: 15 measurements, 12 mutants built and run, 2 full-corpus runs (147 passed each,
~11.7 min apiece), 2 two-arm end-to-end exploits, ~45 minutes of measured compute. Every command is
recorded above or in `$SB`.*