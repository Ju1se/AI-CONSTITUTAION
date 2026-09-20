# Agents policy — design, rationale, enforcement

Status: legislative revision · 2026-09-20 · companion to `/AGENTS.md`. Enforcement, tool-loading and historical sections are retained as prior-version descriptions and require independent reassessment; this revision does not certify implementation or outcomes.

Sections 1–3, 5 and 6 explain the current legislation and its evaluation principles. `AGENTS.md` contains operative duties and `policy.mk` their values; this document creates no additional permissions. Other sections are retained without re-verification in this legislative-only revision.

Contents: 1 Principle · 2 Assumptions · 3 Clauses §1–§7 · 4 Checks on the checkers · 5 Metrics and baselines · 6 Parameters · 7 Enforcement (7.5 what is not yet checked, 7.6 what the gate does not claim) · 8 Loading per tool · 9 Maintenance · 10 Audit response

---

## 1. Principle

The legislation protects authority and truthful evidence while leaving a proportionate path to complete authorized work. `AGENTS.md` states operative duties; `policy.mk` supplies their parameter values. This explanation creates no additional permission. A result supports only what its stated evidence establishes; it cannot supply a missing authorization or change the meaning of an earlier result.

The separation-of-powers analogy, including the concern in *Federalist 51* with checking power rather than relying on goodwill, informs the allocation of decisions. It is not evidence that different agent instances have opposed interests. A branch name, a fresh instance or a role label is insufficient: the person designated to approve a disputed acceptance revision must be able to refuse and must be neither its implementer nor its proposer. Tests are fallible evidence of a specification, not an unamendable constitution.

### Authority, interpretation and change

Hard rules protect the allocation of authority and the integrity of evidence. Ordinary rules govern work within that allocation. Task instructions determine the goal and scope. Explicit task-owner instructions take precedence as stated in `AGENTS.md`; a request to finish, however, does not implicitly amend a rule or authorize an exception. An explicit override is recorded with its clause, scope, reason and duration. An ambiguous conflict pauses the dependent work as `H-CONFLICT`.

Three decisions must remain distinguishable:

- **Interpretation** explains an existing rule and its application; it cannot create a new exception.
- **Exception** uses authority already granted by a clause. Prior written authorization names the clause, exact scope, reason, conditions, effective point and expiry or terminating event. Acceptance revisions also need the independent approval in §3. Expiry is not self-renewal.
- **Amendment** changes a general rule. It uses a `policy/` change, identifies the protected interest and alternatives, and specifies adjacent allowed and refused cases, compliance burden, effective point, pending-work treatment and any trial review or fallback. Its author cannot certify the amendment.

An amendment takes effect on `main` at its recorded effective commit or later named transition. Existing decisions keep their original rule version and outcome. A reconsideration is a new decision, not an erasure of the old one. If a required mechanism rejects an authorized transition, retain that result and refer the mismatch to the designated authority. The new permission does not authorize bypassing the mechanism or relabelling FAIL, ERROR or NOT_RUN as PASS.

Rules bind unless expressly advisory. Creating a tool does not activate an advisory policy. Activation needs an explicit amendment; a trial names its scope, end or review point, benefit and burden measures, and fallback. Repeated similar exceptions are evidence that the general rule needs reconsideration, not a permanent substitute for amendment.

## 2. Assumptions

- A change is one branch merged as one unit. Its committed record names `TYPE:`; filename and branch prefix agree. Records remain available after a branch disappears. `docs/changes/` is allowed in every type.
- The ordinary layout places source in `src/` and acceptance tests in `tests/`; the protected set is authoritative in `policy.mk`. A permitted acceptance revision does not waive path protection or authorize an unrelated change type.
- The task owner states scope, designates independent decision makers, answers blocked questions and grants only explicit authorizations. The implementer proposes and performs work; the acceptance approver decides the exact requested revision. Legislative authors propose general rules and do not adjudicate their own amendments.
- Independence is a requirement on the decision, not a claim that role separation eliminates shared bias. A second instance selected by a proposer has no automatic approval authority. The owner must designate the approver, who may refuse.
- The applicable policy comes from `main` and the recorded effective transition. Pending work does not silently adopt a convenient rule version; the amendment states its scope. Old evidence remains attributable to the policy and specification under which it was produced.
- The enforced profile requires PASS on its required checks. An advisory profile does not authorize a merge. These result conditions coexist with substantive specification and authorization duties; no profile makes an unfulfilled binding duty optional.

## 3. Clauses

### §1 Definition of done — single-subject rule

The single-subject rule separates an implementation decision from a change in the rules used to judge it. `DONE` means the authorized specification is met, binding duties are fulfilled, applicable acceptance is resolved, and every required merge check is PASS. Report a role's completed work separately from decisions still owed by another role. A passing check does not certify unexamined behavior, and an unfinished external decision is not a completed task.

A change normally has one type and adds one record. Corrections to older records preserve the original decision and explain the correction. A `policy/` change touches the protected set plus its record. A `refactor/` changes no acceptance. An ordinary test correction uses `test/`; an independently approved specification migration may coordinate behavior and its exact acceptance revisions within a `feature/` or `fix/`, with tests committed before implementation and in separate commits. Protected acceptance still requires `policy/`.

**Adjacent cases:** changing behavior and exactly the acceptance cases approved for a new specification is permitted as that migration. Editing additional failing cases because they obstruct completion is not. This exception prevents branch separation from making a legitimate transition impossible without turning a feature branch into an unrestricted power to rewrite acceptance.

### §2 Terminal states — BLOCKED preserves the decision

`BLOCKED` is a valid, non-punitive filing, not abandonment of the task or a requirement to stop unrelated work. Its three lines identify the dependent scope, the smallest missing decision and its decision maker, and the state of work. Persist it in the change record before handoff. Independent work already within scope may continue.

The task owner must answer, designate a decision maker, revise scope or explicitly defer. Silence is not consent. Retain the filing and record its disposition; an answer resolves only the scope it names. No failed-code demonstration is required to establish that an authorization, specification or external obligation is missing. A `SPEC-AMBIGUOUS` filing is appropriate when two plausible readings change observable acceptance and no authorized default resolves them, not for every routine implementation choice.

Error handling must preserve what the caller needs to know: re-raise with context, return a typed failure the caller must match, or log at ERROR with the exception under a complete `masks` sunset tag. The narrow permanent boundary form in `AGENTS.md` is separately permitted when it returns or raises the named typed failure; it does not require a `masks` tag. A complete temporary tag and a permanent boundary authorize only their stated forms, never an unrelated skip, suppression or fallback. Review applies those same exceptions.

**Adjacent cases:** pausing a behavior decision while completing unrelated, authorized documentation preserves both caution and progress. Choosing an acceptance meaning merely because the owner has not replied does not.

### §3 Evidence — authority over acceptance revisions

H1 prohibits an implementer from unilaterally changing the standard used to judge their work. Existing acceptance includes `tests/`, `scripts/tests/` and every `conftest.py`. The protection is not a declaration that every old assertion is correct. Two revision grounds must be recorded separately:

1. **Correction:** evidence shows an existing case is inconsistent with the current governing specification.
2. **Migration:** the owner explicitly authorizes a new specification whose observable behavior changes acceptance.

Before editing acceptance, the owner designates an approver other than the implementer or revision proposer, with authority to refuse. The `ACCEPTANCE` decision records the decision maker, date, reason, governing specification versions, exact old and new cases, effective transition and retained evidence. It identifies which obligations remain and which are superseded. The approval is specific; it does not authorize weakening neighboring assertions or deciding a broader migration after observing failures.

Ordinary corrections use `test/`. A migration may use the exact `feature/` or `fix/` exception in §1, preserving test-before-implementation commit separation. Protected acceptance requires `policy/`. Existing policy counterexamples remain binding unless the approved decision explicitly supersedes them and identifies their replacement obligations. Preserve old specifications, tests and outcomes in committed history. Approval never converts an earlier failure into a pass; mechanisms that reject the transition must be referred for a separately authorized resolution.

BLIND means tests are authored from the authorized specification before implementation. A separate-role author receives the specification and public interface rather than the implementation diff. Evidence includes new cases failing on the recorded pre-change base, newly collected cases and a real in-repository call path. Report an import error as an import error rather than as demonstrated behavioral failure. A feature/fix adds a new test file. A missing real-path harness is `NO-HARNESS`; an unapproved acceptance revision pauses as `TEST-DEFECT` or `H-CONFLICT`. Mocks remain limited to the authorized I/O boundaries, never an owned module. The mutation target of 0.70 is advisory; record a measured result or why it was not measured.

**Adjacent cases:** the designated approver authorizes a specific mistaken assertion against an unchanged specification, preserving the old evidence. That is a correction. The implementer replaces the same assertion solely to make their new code pass, without that decision. That is unauthorized. Changing the specification requires the migration route, even when changing the test text would look identical.

### §4 PAYGO — an advisory complexity ledger

The ledger is an observation proposal, not a current merge condition or a source of spendable rights. Its target is net debits minus credits at most 2, with a proposed bank cap of 6. Report available evidence truthfully; an unavailable score is not zero. Tool availability alone does not activate the ledger, and no task must delete unrelated code to meet its target.

The proposed weights price modules, public symbols, abstraction layers, configuration surfaces and dependencies, with corresponding retirement credits. These are hypotheses about maintenance cost. Hiding a public responsibility as private, dividing related work across branches or deleting lines without retiring an obligation does not demonstrate less complexity. Zero static references do not establish absence of external callers, reflection, serialized data or other contracts.

An activation amendment must define counting and overlap, bank ownership, related-change aggregation, legitimate counterexamples, measured benefit versus burden, and its effective transition. Safe retirement remains necessary whether or not a deletion earns a credit. A trial can be withdrawn or revised when those measures do not support it.

### §5 Sunset — expiry requires a disposition

A sunset makes a temporary responsibility due for review; it is not permission to destroy an existing contract. Temporary compatibility layers, shims and adapters require tags. A stable boundary responsibility may be recorded as permanent from inception with its contract, owner and reason. A tag never independently authorizes a violation of H1 or the error-handling rules.

The binding terms are 30 days for todo/masks/skip and 90 days otherwise on newly added or renewed tags, with a tree-wide 180-day maximum. Expired obligations require a disposition. Renewal changes the tag only, states its reason and retirement condition, and is limited to two renewals. Protected-path and acceptance permissions continue to apply.

Choose **delete** only after establishing no remaining internal or external obligation and a green suite; **renew** when the temporary responsibility remains justified; or **promote** to a recorded permanent responsibility with a contract and owner. Every path has a change record. Complexity effects remain advisory. A green local suite alone is not evidence that an external contract has ended, and a risky deletion is not a required proof exercise.

When safe retirement cannot be established within scope, file `BLOCKED SUNSET-EXPIRED` identifying each tag and the unmet condition, including external obligations. A corresponding `grace:<today>` defers that tag once for at most seven days. A general filing does not cover unspecified tags. Grace defers only the sunset obligation, not failing acceptance or other duties.

**Adjacent cases:** retain a documented permanent protocol adapter because its contract remains part of the system. Do not label a temporary workaround permanent merely to avoid its review. Conversely, do not delete a still-promised compatibility path solely because its date has arrived.

### §6 The record — reasons, authority and effect

The record is committed evidence of decisions, not an authorization created by filling a template. `TYPE:` identifies the change; `WHY:` explains the chosen decision and alternative; `TESTS:` records commands actually run. Searches precede new modules, helpers, wrappers and base classes, and `SEARCHED:` reports their results honestly. Replaying the search is advisory; the search and truthful record are duties.

Every added dependency has its own `DEP` entry identifying the actual package and version, existence evidence, publication date, reason and rejected alternative. The default minimum age is 30 days. A prior written task-owner exception may waive age alone for an exact package/version and change, with necessity, alternatives, withdrawal plan and expiry. It does not waive existence, record or other authority requirements. A mechanism that refuses the exception is referred rather than bypassed.

Use `ACCEPTANCE`, `EXCEPTION`, `EFFECTIVE` and `REVIEW` when the corresponding decision or trial applies. An amendment records its protected interest, affected clauses, adjacent allowed/refused cases, expected compliance burden, alternatives, effective point and treatment of pending work. A trial also states the review point, success and burden measures, and fallback. Corrections to old records retain the original decision and explain the new entry.

**Adjacent cases:** authorize an exact young dependency version for a named necessity under the age exception, while preserving existence evidence and an expiry. A general instruction to finish quickly is not that exception. Repeated similar requests call for reconsidering the general age rule.

### §7 Audit — bounded independent judgment

The legislative obligation covers a 20% sample of merged changes and all policy/renew changes, acceptance revisions, exceptions, masks/boundary exemptions, `NONE-FITS` with hits, `POLICY-GAP`/`SUNSET-EXPIRED` filings and the configured sensitive paths. This states what requires independent judgment, not what any present mechanism performs. Legislative authors do not adjudicate their own amendments.

Permitted decisions are **FINDING**, supported by reproducible evidence or a located contract defect; **NO-FINDING**, with at least three examined attack paths, commands and limitations; and **INCONCLUSIVE**, identifying missing evidence and the next required decision. Inconclusive is neither approval nor proof of a defect. Findings and unresolved questions retain separate records. A refusal to certify insufficient evidence must not force a fabricated failure or an unsupported clean attestation.

The proposed re-audit and accountability parameters are advisory until expressly activated. Neither a finding quota nor a raw count of attestations establishes quality. Evaluate decisions together with subsequent corrections, missed problems, coverage and the burden of review. A different instance can still share the same blind spots; these are limits of the analogy, not grounds to give the original author unilateral approval power.


## 4. Checks on the checkers

*Analog: judicial review and a free press.* Every mechanism creates a predictable shortcut of its own; each is priced.

| Mechanism | Predictable exploit | Guard |
|---|---|---|
| The verifier itself | edit it, or its parameters, on the candidate branch and let it approve you | loaded from `main`, never from the candidate; protected set (`policy/` only); its own regression suite runs on every `policy/` change; CODEOWNERS |
| Gate outcomes | count "not run" as passed | four outcomes; only PASS authorizes; NOT_RUN and ERROR block an enforced merge |
| Evidence source | edit the working tree after committing | every read is `git show`/`git grep`/`git archive` on the subject or the trusted ref |
| BLOCKED (§2) | file it on everything | round trip, not exit; frivolous `NEED`s are a metric on specs |
| BLIND tests (§3) | commit a trivial test, then "implement" | added-test rule; red-before-green and mutation (phase 2); BREAK step of the audit |
| Mock allowlist (§3) | add in-repo modules to it | read from the trusted ref; protected set |
| PAYGO (§4) | delete the wrong thing; split to fake credit | advisory until calibrated; zero-reference proof + green suite; new public symbols debit |
| Sunset (§5) | renew by editing the date; claim grace | tag edits on `renew/` only (field diff: phase 2); grace requires the filed record |
| SEARCHED / DEP (§6) | paste a fake search; invent a package | DEP bound to manifest additions and checked on PyPI; SEARCHED replay phase 2 |
| Audit (§7) | rubber-stamp; hunt trivia | no LGTM output; minimum risk surface; re-audit; judged on overturns and escapes |
| The export | ship a `.gitattributes` so the frozen test is not in the tree the gate tests | `export_integrity` compares the export with `git ls-tree`; `.gitattributes` is in the protected set |
| The test harness | ship a `conftest.py` hook, an `addopts`, a `pyproject` ruff table or a `# ruff: noqa` so the gate's own tools report what you want | tools run with the gate's configuration (`-c`, `--override-ini`, `--isolated`); `harness_integrity` refuses the files off a policy change; `test_inventory` compares the collected ids with the base |
| The verifier's corpus | change the judge and delete the counterexample that would fail it | `verifier_selftest` restores `scripts/tests` **from the policy ref** over the candidate's and runs that; `scripts/tests/` is frozen under H1 |
| The audit sample | land the sensitive change on a path the glob does not reach | `**` matches zero or more directories, and every protected-set change is a 100% trigger |

## 5. Metrics and baselines (for E-series evaluation)

Evaluation must be capable of finding the legislation itself costly or mistaken. Define scope, comparison, denominators, review point and fallback before a trial. State conclusions for the observed repository, task family, model set and period; do not treat a metaphor, outside correlation or one successful task as calibration of a binding threshold. This legislative revision establishes no empirical result.

Assess substantive completion, preservation of authorized acceptance and maintenance outcomes together with refusal costs and human burden. A rule can reduce a prohibited action by preventing useful work altogether; a metric that omits that cost cannot justify the rule. Preserve unanswered and deferred tasks in the denominator rather than treating them as invisible successes.

| Question | Evidence to consider together | Misleading shortcut to avoid |
|---|---|---|
| Does the rule improve completion? | authorized specification met, unresolved decisions, later regressions, maintenance-task outcomes | equating PASS or a completed branch with completed work |
| Does acceptance remain legitimate? | unauthorized changes, approved corrections/migrations, retained old evidence, reasons for overturned decisions | counting every test edit as tampering or every freeze as correctness |
| Does BLOCKED obtain needed decisions? | affected scope, owner response/disposition, wait time, independent work completed | rewarding few filings or penalizing truthful dissent |
| Is a restriction proportionate? | legitimate cases refused, compliance work, token/time/tool costs, human interventions | reporting prohibited cases caught without lawful neighboring cases |
| Does the ledger measure maintenance burden? | related-change complexity, external obligations, later maintenance cost, deletion regressions | optimizing deletion counts, private names or branch counts |
| Do sunsets retire debt safely? | safe deletion, justified renewal, stable responsibility, unresolved internal/external contracts | treating expired dates as proof that obligations disappeared |
| Are dependency choices justified? | verified existence, alternatives, exception reasons and recurrence, later withdrawal burden | treating package age alone as safety or justified necessity |
| Is independent judgment useful? | evidence quality, scope examined, corrected decisions, escaped problems, review burden | quotas for findings, assurances or overturned decisions |

Complexity, deletion totals, mock prevalence and mutation scores are secondary indicators, not substitutes for authorized behavior. An observed improvement is a reason to consider an activation amendment, not automatic activation. A trial that fails its stated benefit-versus-burden test follows its recorded fallback. Repeated exceptions or refusals are grounds to reconsider a rule, without presuming that every refusal was wrong.

## 6. Parameters

`policy.mk` at the applicable trusted revision is authoritative for values; `AGENTS.md` states their legal effect. Updating a value is a `policy/` amendment that also updates its operative description and records its effective transition. An environment choice, available tool or measured value does not itself amend a rule. Starting values are not established calibration.

Required checks are necessary merge conditions, not an exhaustive statement of substantive duties. Conversely, a target expressly marked advisory cannot block work merely because it is unmet or unmeasured. Advisory parameters acquire binding force only through an explicit activation amendment with scope, legitimate counterexamples, benefit and burden measures, and treatment of pending work.

| Parameter | Value | Legislative effect |
|---|---|---|
| `PROTECTED_PATHS` | `AGENTS.md policy.mk tests/MOCK_ALLOWLIST docs/agents-policy.md Makefile scripts/ .claude/ .github/ .gate/ .gitattributes` | binding path authority under H5; acceptance revisions also need §3 approval |
| `REQUIRED_CHECKS_ENFORCED` | `type protected_files export_integrity harness_integrity unit_tests test_inventory red_before_green h1 mocks masking_markers masking_ruff sunset records deps verifier_selftest` | required PASS conditions; no claim here that this revision has run them |
| `REQUIRED_CHECKS_ADVISORY` | `type protected_files unit_tests` | observation profile; never permission to merge |
| `UNIT_TESTS_TIMEOUT` | 900 s | bound for the specified execution; timeout is not evidence of a pass |
| `ALLOWANCE_DEFAULT` / `BANK_CAP` | 2 / 6 | advisory target and proposed cap; no current merge limit or spendable rights |
| `MUTATION_MIN` | 0.70 | advisory target; honestly report measured or unmeasured |
| `SUNSET_SHORT` / `SUNSET_LONG` / `SUNSET_MAX` / `SUNSET_GRACE` | 30 / 90 / 180 / 7 days | binding terms; grace is once per identified tag and defers only that obligation |
| `RENEWALS_MAX` | 2 | binding renewal limit; missing automatic evidence does not waive the duty |
| `DEP_MIN_AGE` | 30 days | binding default; only the exact prior written age exception in §6 may waive it |
| `AUDIT_RATE` | 0.20 | sampling duty, alongside the mandatory categories in AGENTS.md §7 |
| `REAUDIT_RATE` / `ATTEST_MIN_PATHS` / `AUDITOR_OVERTURN_MAX` | 0.10 / 3 / 0.20 | proposed accountability parameters, advisory until activated; AGENTS.md §7 separately fixes the current three-path NO-FINDING minimum |
| `AUDIT_ALWAYS_PATHS` | `src/**/auth* src/**/secret* src/**/subprocess* src/**/net* src/**/sql* src/**/serial*` | binding sensitive-path categories; amendment is needed to change their scope |

SEARCHED replay is advisory even though the prior search and honest record remain binding. The same distinction separates a proposed accountability metric from the independent decision duties already stated in §3 and §7. No parameter authorizes its own exception or revises the historical meaning of an existing result.


## 7. Enforcement

### 7.1 Trust model

Four things that must not coincide: the **candidate** (a branch and its record), the **verifier** (`scripts/gate_checks.py` plus `policy.mk` and `tests/MOCK_ALLOWLIST`, always read from `main`), the **host** that runs the verifier (CI, from `.github/workflows/gate.yml`, or a human's `make gate`), and the **evidence tree** the verifier reads.

The fourth is v0.4's addition and the one v0.3 missed. The candidate authors the tree, so it also authors the files that tell git what to export, pytest what to collect and how to report, and ruff what to lint. The rule is that no input to the judgment comes from the party being judged: the export is compared with `git ls-tree`, every tool is started with configuration written by the verifier outside the export, the collected test ids are compared with the base, and the harness files themselves are in the protected set. What remains is stated rather than hidden (§7.5). The candidate cannot change the verifier or the policy that judges it: those paths are in the protected set, so a non-`policy` change touching them fails `protected_files`, and even a `policy` change is judged by the *current* verifier and must pass its own regression suite before it can become the next one. Branch protection with CODEOWNERS and the required `gate` status check is what makes this hold on the hosting platform; without them the protected set is a convention.

Every result binds: `subject_sha`, `base_sha`, `policy_ref_sha`, `verifier_sha` (sha256 of the running verifier), `verifier_sha_at_policy_ref`, `verifier_provenance`, `policy_digest` (sha256 over the policy files at the trusted ref), `environment_digest`, the profile, the record path, and per check `{id, required, outcome, detail, safe_path}`.

`merge_eligible` is true only when all four hold: the profile is `enforced`; at least one required check ran; every required check is PASS; and `verifier_provenance == "policy_ref"`, meaning the file that ran is byte-identical to the verifier at the trusted ref. `ineligible_reasons` names each condition that failed, so a result never has to be read for an absence. Exit codes: 0 eligible · 1 the change was refused (a required check FAILed) · 3 the run cannot authorize anything — a required check ERRORed or did not run, the inputs are invalid, or the verifier or the profile was wrong · 4 usage. The split is what a CI consumer needs: 1 means fix the change, 3 means fix the run. Invalid subject/base (not a commit, not an ancestor, base == subject) is exit 3 with no result written.

### 7.2 Check inventory — guarantee scope, status, evidence

Three columns, because "live" hides partial coverage. "Evidence" names the fixture in `scripts/tests/`;
a row that claims more than its fixtures show is itself a finding (§9).

| Check | Guarantee scope (what a PASS actually means) | Status | Evidence |
|---|---|---|---|
| `type` | exactly one record selected for this change; TYPE = filename prefix = branch prefix; diff paths within the type's set; a `renew` is a field-level tag edit | live | C01, P16, branch mismatch, no-branch, P0-6 and its tag-only control |
| `protected_files` | no protected path touched off a policy change; a policy change touches nothing else | live | P25, P06, policy-positive |
| `export_integrity` | the export the gate tests has exactly the paths of `git ls-tree -r <subject>` | live | CR-01 and its control |
| `harness_integrity` | off a policy change, this change adds no `export-ignore`, no collection/reporting hook in a `conftest.py`, no pytest/ruff config section or key, no file-level `# ruff: noqa` | live — **denylist, not a proof**: a `conftest.py` that subverts reporting without one of the listed hooks is not detected | CR-01, CR-02 (and its `-k` variant), CR-03, the ordinary-fixture control |
| `unit_tests` | `pytest tests` exits 0 on the export, under the gate's own configuration | live | C01, P01, CR-02 |
| `test_inventory` | no test id collected at the base is missing at the subject; a feature/fix adds ≥ 1 collected id; a refactor adds none | live | CR-01, CR-02, CR-04, refactor control |
| `red_before_green` | the change's new test files fail (pytest exit 1 or 2) on a clean export of the base | live — the reason for the red is not classified: an unrelated ImportError also passes | C01, the vacuous-test case, no-new-test |
| `h1` | no commit in `base..subject` modifies, deletes or renames a file in the frozen set (`tests/`, `scripts/tests/`, any `conftest.py`); a refactor touches no tests; feature/fix never mix `src/` and `tests/` in one commit | live — commit-order proxy only | C01, P01, EV-01, the conftest case |
| `mocks` | AST targets of `patch`/`patch.object`/`patch.dict`/`monkeypatch.setattr`/`setattr` on added lines under `tests/` and `src/`, resolved through each file's imports, ⊆ the allowlist at the trusted ref | live — a target computed at run time is reported unresolved, not allowed | CMP-11, CMP-05 control, M09, M10 |
| `masking_markers` | added `.py`/`.sh`/`.bash` lines anywhere: no suppression or skip marker, no handler followed by a swallow, no shell masking, no file-level suppression — unless the line carries a complete `SUNSET` tag, or is the boundary shape in full with a body that raises or returns a non-`None` value | live — pattern-based | P0-1 and its parametrized marker kinds, M05 body cases, M06/M07 paths, P0-5 |
| `masking_ruff` | ruff `E722 BLE001 S110 S112 S113`, `--isolated`, over every source directory present at the subject | live; NOT_RUN if ruff absent, which blocks | C01 both branches, P0-2, the tests/ and tools/ cases |
| `sunset` | tags parse; per-kind term on added and renewed lines; the 180-day maximum tree-wide; no expired tag without a filed, first, in-window grace; no tag edit off a renew; no untagged TODO added | live | P05, P09, P10, P11, P0-7, P0-8, RT-04, the impossible date |
| `records` | the change's record is committed and complete for its type; every added manifest dependency has its own `DEP` line | live | P16, dep-without-record, chore-docs, RT-08 |
| `deps` | each `DEP` exists on PyPI at that version and is ≥ 30 days old | live; NOT_RUN when `DEPS_OFFLINE=1`; ERROR when unreachable | P19 |
| `verifier_selftest` | the candidate verifier compiles and passes the `scripts/tests` corpus **as it stands at the policy ref**, restored over whatever the candidate ships | live for a policy change; NOT_RUN and not required otherwise | EV-01, CMP-17, the policy-positive control |
| verifier provenance | the file that ran is byte-identical to the verifier at the policy ref; anything else is recorded and cannot be eligible | live (report-level) | the subject-copy case, the control |
| `ledger` · `mutation` · `searched_replay` · `renewals_cap` | — | NOT_RUN (advisory) | advisory-profile test |
| H1 hook | edit-time refusals: `src/` while `tests/` is dirty; a committed test off a `test/` branch; `chore`/`policy` outside their sets; paths normalized, including a file in a directory that does not exist yet; unparseable input refuses | live (Claude Code); matcher `Edit|Write|MultiEdit` only — a shell write is not covered | P20, P21, P23, RT-07 |
| H4 | no paid / provider / non-registry network runs | configure per tool: Claude Code `permissions.deny` + sandbox; Codex sandbox; CI holds no credentials | — |

### 7.3 CI

`.github/workflows/gate.yml` checks out the PR head with full history, fetches `origin/main` **without a depth limit** — v0.3's `--depth=1` marked the repository shallow and truncated main, so `git merge-base` returned nothing whenever main had advanced past the branch point, which is the normal case and made the job fail red on almost every PR (audit T1) — extracts `scripts/gate_checks.py` from `origin/main`, computes the merge base, and runs the gate with `--policy-ref origin/main`. The result JSON is uploaded as an artifact.

The workflow file is not itself the trust anchor: for a `pull_request` event GitHub evaluates the definition from the PR's own ref, so a PR could rewrite this job. Branch protection on `main` — required CODEOWNERS review plus this required status check — is what anchors the chain, and it lives in repository settings, outside the repository (audit T7).

Locally, `make gate` does the same with `VERIFIER_REF` (default `main`, else `origin/main`). `make gate SUBJECT=<sha> BASE=<sha>` passes no `--branch`, so re-judging a merged commit takes its type from the record and does not fail on the branch the auditor happens to be standing on (audit EV-05). `make check-<group>` runs the working copy's verifier for feedback and is not a merge decision.

### 7.4 The H1 hook

`.claude/settings.json` registers `.claude/hooks/h1-test-source-separation.sh` on `PreToolUse` for `Edit|Write|MultiEdit`. Exit 2 blocks the call and feeds stderr back to the model. Rules: `src/` edit while `tests/` has uncommitted changes → refuse; edit to a committed file of the frozen set (`tests/`, `scripts/tests/`, any `conftest.py`) off a `test/` branch → refuse; `chore` editing `src/` or `tests/` → refuse; `policy` editing anything under those trees but the allowlist and the verifier's corpus → refuse. A `renew` branch may edit `src/` and `tests/`, because a SUNSET tag lives on a code line and v0.3's blanket refusal made the only legitimate renew workflow impossible (audit RT-07); the gate then enforces that only the tag changed. Paths are normalized before matching; an unparseable tool input refuses. The hook is fast feedback: the gate re-checks committed history, and the repository's file permissions are the real boundary. Keep the hook where the implementer cannot edit it (organization-managed settings or a role-specific machine) — the copy in `.claude/settings.json` is protected by CODEOWNERS only.

### 7.5 The branch that is not yet checked

The gate judges changes. Nothing judges the judge's other half.

`REAUDIT_RATE`, `ATTEST_MIN_PATHS` and `AUDITOR_OVERTURN_MAX` are in `policy.mk` and are read by no code.
They are the parameters of auditor accountability — how often an attestation is re-audited, what an
attestation must cost, and at what overturn rate an auditor is rotated out. Without them the judiciary can
refuse a change but cannot itself be held to anything, and `.claude/skills/audit/SKILL.md`'s closing
sentence — "an auditor is judged on overturned attestations and on regressions that escaped" — describes
a measurement that does not exist.

Two further asymmetries in the same place:

- **The gate cannot find a statute defective.** A `POLICY-GAP` filing is only an audit trigger. Nothing
  counts how often a rule refuses a change that a human then waves through, so a rule that mostly
  false-blocks accumulates no evidence against itself. A judiciary whose cases are largely "this cannot be
  adjudicated" — four of nineteen checks are permanently NOT_RUN — pushes the work back to the executive.
- **The legislature and the task owner are the same party.** `BLOCKED` is the weaker branch's defensive
  weapon, but the `NEED` that answers it comes from whoever set the goal and wants it fast.

These are structural, not cosmetic, and they are the reason the next piece of work is a measurement rather
than another clause: whether separating the roles changes behaviour under pressure is an empirical question,
and the parameters above are what an answer would have to be expressed in.

### 7.6 What the gate does not claim

The gate runs code the candidate wrote — the tests, and the `src/` those tests import. No arrangement of
checks makes that safe in general, so the residue is named here and in each check's own PASS detail rather
than left for the next review to find:

- A `conftest.py`, or an imported `src/` module, that subverts pytest **without** one of the hooks in
  `harness_integrity`'s denylist is not detected. `test_inventory` catches anything that changes which tests
  are collected; it does not catch something that changes what a result reports. The audit's BREAK step is
  the compensating control, and this is the reason a policy change is always audited by a human.
- Commit order is not proof that the tests were written first; `red_before_green` proves only that they fail
  on the base commit, for a reason the gate does not classify.
- The mock scan covers the AST forms listed in §3; a target computed at run time is reported unresolved.
- The masking scan is a pattern list, not a semantic analysis of whether an error is handled.
- `scripts/gate_checks.py` is excluded from the pattern scan, because it quotes the denylist as string literals and would flag itself on every line. Ruff still lints it (`scripts/` is in the lint set), and its one crash barrier is the sanctioned shape with a body the AST rule accepts — the verifier is held to the rule it enforces, by the tool that cannot be confused by quoting.
- The mock scan attributes a call to its first line, so a multi-line call whose opening line a change did not touch is out of its scope.
- One `BLOCKED SUNSET-EXPIRED` line in a record covers every tag that change defers; the filing is per change, not per tag. Binding a filing to a tag needs the stable tag ids that `renewals_cap` also waits on.
- An expired tag left by someone else still blocks an unrelated change, while a merely long-dated one no longer does. That asymmetry is deliberate: an expired tag is a live breach, a long one is not.
- `ledger`, `mutation`, `searched_replay` and `renewals_cap` are NOT_RUN and advisory.

## 8. Loading and verification per tool

Claude Code (v2.1.277+): reads `AGENTS.md` directly only when no `CLAUDE.md` or `CLAUDE.local.md` exists in the working directory or above it; it does not list `AGENTS.md` in `/memory` or `/context` — look for the `AGENTS.md loaded: …` line at session start. If a `CLAUDE.md` is ever added, put `@AGENTS.md` on its first line. Subdirectory `AGENTS.md` files load when Claude reads a file in that directory.

Codex: builds the instruction chain once at start — `~/.codex/AGENTS.md`, then every `AGENTS.md`/`AGENTS.override.md` from the project root down to the current working directory, concatenated root-first — and stops adding files at `project_doc_max_bytes` (32 KiB default). The root file is 14.0 KB. Verify with `codex --ask-for-approval never "Summarize the current instructions."` Nested files are read by directory position, not by edited file, so binding rules stay in the root.

Both: explicit user chat prompts override the file. H-conflicts are handled by `BLOCKED H-CONFLICT` and by tooling, not by a precedence claim.

## 9. Maintenance

- Every reproduced counterexample becomes a fixture under `scripts/tests/` before the fix lands; the audit ids stay in the test names. The corpus is what a candidate verifier is judged against, so it is loaded from the trusted ref, and a change to the judge may add cases but never remove them.
- Write the corpus from the specification, before the implementation exists, and have someone who has not seen the implementation write it. v0.4 was built that way: six instances wrote 74 tests from `v04-spec.md` alone; every one failed against v0.3 and passed against the implementation they had not read. Where a test and the implementation disagreed, the disagreement was a defect in one of them — that is the whole value of the arrangement, and it found five.
- Add a line to `AGENTS.md` when the gate refuses agents for a reason the file does not state, or when the same correction is typed twice. Remove a line when its check goes live and the text becomes redundant.
- Every `POLICY-GAP` filing is a policy defect: resolve it on a `policy/` branch and record the gap and the fix in §10.
- Budget: `AGENTS.md` ≤ 150 lines and ≤ 14 KB (leaves Codex ≥ 18 KB for global and nested files). It is 134 lines and 14.0 KB.
- §7.2 is re-derived from the test suite on every `policy/` change; a row that claims more than its fixtures show is itself a finding.
- Codex's `AGENTS.override.md` and Claude Code's `.claude/rules/` are not used, so one file carries the same rules to both tools.

## 10. Audit response

### 10.1 v0.2 → v0.3

Phase 1 of the first audit's fix order: trustworthy results, not more rules. Status of each finding:

| Finding | v0.3 | Fixture |
|---|---|---|
| F01 gate does not run tests; unimplemented → exit 0 | **fixed**: `unit_tests` required; four outcomes; NOT_RUN/ERROR never authorize; profiles | P01, DEPS_OFFLINE, policy-without-tests |
| F02 git failures → empty success | **fixed**: every git call checks its exit code; subject/base validated as commits and as ancestor/descendant; ERROR exit 3 with no result | P03, non-ancestor base |
| F03 working tree vs HEAD | **fixed**: all reads via `git show`/`git grep`/`git archive` on the subject or trusted ref; result binds five identities | P04, P05, P16 |
| F04 candidate can change verifier/params | **fixed**: protected set enforced before type rules; verifier and policy loaded from `main`; `policy/` judged by current verifier + must pass own suite; CI anchors it | P25, P06, sabotage scenario |
| F05 H1 proves order, not test-first | **partial**: added-test rule; guarantee scope stated; red-before-green NOT_RUN | phase 2 |
| F06 sunset gaps | **partial**: P09 partial tags exempt nothing; P10 terms per kind; P11 grace requires filed record. Open: P08/P12 field-level `renew` diff, stable tag ids, renewal count | P09, P10, P11 |
| F07 hook | **partial**: P20 normalization, P21 parse-failure refuses, P23 allowlist exemption. Open: Bash/PowerShell writes are outside the matcher | manual |
| F08 mock scan coverage | **scoped**: guarantee stated on every run; review rules carry the rest. Open: AST-based scan | phase 2 |
| F09 post-merge identity | **fixed for the gate**: type and record from the committed subject; audit skill takes subject/base from the result | no-branch test |
| F10 records/deps binding | **partial**: DEP bound to manifest additions by name; `DEPS_OFFLINE` → NOT_RUN. Open: SEARCHED replay, per-helper SEARCHED, `credits` scoring | dep-without-record, DEPS_OFFLINE |
| §4 text conflicts | **partly**: H1 restated (frozen acceptance, `test/` adjudicates); grace and BLOCKED reconciled (defer once, filed); sunset default is re-evaluation; audit outputs widened. Open: delete-needs-no-record vs record-per-change; "never audited" deletions vs security paths | phase 2 |
| §6 metric misreadings | **fixed**: 23%/13% is test activity; 36%/26% is over test commits; local metric is unauthorized weakening | §5 |

Phase 2 (narrow and implement precisely) and phase 3 (decide by experiment which of PAYGO, sunset and sampling audit to keep) remain. Nothing above is evidence about agent behavior; it is evidence that the checker now refuses what the audit showed it accepting.

### 10.2 v0.3 → v0.4

The independent review of v0.3 raised 66 findings; 44 were reproduced from scratch by instances that had not
seen the reasoning behind them, and none was refuted. The report is `docs/audits/agents-kit-v0.3-review.md`.

| Finding | v0.4 | Fixture |
|---|---|---|
| CR-01 `.gitattributes export-ignore` deletes the frozen test from the gate's evidence | **fixed**: `export_integrity`; `.gitattributes` protected; `test_inventory` sees the lost id | CR-01 and its control |
| CR-02 the candidate's `addopts` deselects the frozen test from the gate's own run | **fixed**: pytest runs with the gate's ini and `--override-ini=addopts=`; `harness_integrity` refuses the key | CR-02, `-k` variant |
| CR-03 `tests/conftest.py` rewrites the gate's results | **fixed for the listed hooks**: `harness_integrity`. Residue stated in §7.5 | CR-03, ordinary-fixture control |
| CR-04 "a new test file" is satisfied by an empty `.py` | **fixed**: `test_inventory` requires a newly *collected* id | CR-04 |
| CR-05 `fnmatch` means `src/**/auth*` never matches `src/auth.py` | **fixed**: recursive matcher; protected-set changes are a trigger | audit-select cases |
| P0-1 a `# boundary:` note launders every suppression marker | **fixed**: shape match plus an AST check that the body raises or returns a typed failure | P0-1 parametrized, M05 |
| P0-2 `# ruff: noqa` header and the candidate's ruff config disable the linter | **fixed**: `--isolated`; the header is refused | P0-2 |
| P0-3 a policy change replaces the judge and deletes its corpus | **fixed**: the corpus is restored from the policy ref; `scripts/tests/` is frozen under H1 | EV-01, CMP-17 |
| P0-4 / P0-5 the masking scan skips `scripts/`, `tools/`, `conftest.py`, and never lints `tests/` | **fixed**: every added `.py`/`.sh` line; ruff over every source directory | M06, M07, P0-5 |
| P0-6 a renew changes behaviour on the tagged line (audit P08) | **fixed**: field-level renew diff | P0-6 and control |
| P0-7 a feature re-dates someone else's tag (audit P12) | **fixed**: a tag edit off a renew is refused | P0-7 and control |
| P0-8 grace is bound to the current record, so it can be renewed forever | **fixed**: own record, in-window, and not already graced at the base | the four grace cases |
| P0-9 the advisory profile writes `merge_eligible: true`, selectable by an environment variable | **fixed**: the profile comes from the flag only and advisory never authorizes | the advisory test, corrected from the v0.3 version that asserted the defect |
| P0-10 `src/auth.py` never triggers the 100% audit | **fixed**: see CR-05 | audit-select cases |
| T1 CI shallow-fetches main, so merge-base is empty on almost every PR | **fixed**: no depth limit; the job asserts a non-empty base | static assertion on the workflow |
| T3 / CMP-07 the result cannot say which verifier ran | **fixed**: `verifier_provenance` and `verifier_sha_at_policy_ref`; anything but `policy_ref` is ineligible | provenance cases |
| T4 the Makefile hides a failed verifier load on GNU make 3.81 | **fixed**: `set -o pipefail` inside the recipe | the unloadable-verifier case |
| EV-05 the audit's own RECHECK false-blocks and clobbers the recorded pair | **fixed**: no `--branch` when SUBJECT is not HEAD; a distinct `GATE_OUT` in the skill | verified by hand on a merged commit |
| RT-04 a legal pre-existing tag freezes the repository | **fixed**: per-kind term on added and renewed lines only | RT-04 |
| RT-07 the hook blocks the only legitimate renew workflow | **fixed**: a renew may edit `src/` | hook cases |
| RT-08 "exactly one record" makes merged records uneditable | **fixed**: record selection by added / modified / branch | RT-08 |
| CMP-11 the object form `monkeypatch.setattr(core, …)` is unscanned; CMP-05 the same form on an allowlisted boundary is falsely refused | **fixed**: AST scan with import resolution, both directions | CMP-11, CMP-05 |
| RT-06 a missing `tests/MOCK_ALLOWLIST` at the policy ref crashes after the checks ran | **fixed**: the digest reads it optionally | — |
| EV-03 / EV-04 §7.2 cites fixtures that do not exist | **fixed**: the table above is re-derived from the suite, and the suite is 95 tests | the suite |
| F05 commit order is not test-first; F08 the mock scan is syntactic | **still partial**, stated in §7.5 rather than implied | — |

Phase 3 remains: decide by experiment which of PAYGO, sunset and sampling audit earns its cost. Nothing here
is evidence about agent behaviour; it is evidence that the gate now refuses what two reviews showed it
accepting, and that the mechanism which found the second round of defects — an independent instance with its
own fixtures — is the one worth keeping.
