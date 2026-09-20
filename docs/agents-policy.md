# Agents policy — design, rationale, enforcement

Status: v0.4 · 2026-09-20 · companion to `/AGENTS.md` · responds to the independent review of v0.3 (`docs/audits/agents-kit-v0.3-review.md`).

This document is for humans and for the E-series evaluation. Agents never load it; the operative file is `AGENTS.md` (134 lines, 14.0 KB). Everything here explains, justifies, parameterizes or enforces a line in that file. If a sentence here would change an agent's behavior, it belongs in `AGENTS.md`; if a sentence in `AGENTS.md` only explains, it belongs here.

Contents: 1 Principle · 2 Assumptions · 3 Clauses §1–§7 · 4 Checks on the checkers · 5 Metrics and baselines · 6 Parameters · 7 Enforcement (7.5 what is not yet checked, 7.6 what the gate does not claim) · 8 Loading per tool · 9 Maintenance · 10 Audit response

---

## 1. Principle

The rules assume the knave: an agent takes the shortest path to whatever counts as done. They do not ask it not to. They move "done" so that the shortest path runs through the behavior the repository needs. Each clause has four parts:

- **RULE** — what is binding (in `AGENTS.md`).
- **CHEAPEST PATH** — the least-effort legal route, and why the evasion costs more (one "Safe path" line in `AGENTS.md`; the argument is here).
- **CHECK** — the mechanical gate that refuses completion without it (specified here; implemented in `scripts/gate_checks.py`, the hook, and CI).
- **METRIC** — what is measured afterward (here).

Three facts shape the split between the files. First, both vendors state that instruction files are context, not enforcement: Claude Code says to use a `PreToolUse` hook to block an action regardless of what the model decides, and Codex's review-rule guidance leaves lint and formatting to CI. A rule that exists only as prose is the condition the task-resolution null result measured. Second, both vendors cap what an agent will absorb: Claude Code targets under 200 lines per file; Codex concatenates the global, root and nested `AGENTS.md` files and stops adding at 32 KiB by default. Third — the lesson of both reviews — **the verifier is itself an agent-written artifact and takes the same shortcuts the policy targets**: v0.2 swallowed git errors (`except: pass` in the judiciary), mapped unimplemented checks to exit 0 (`|| true`), and read evidence from the working tree instead of the committed subject. Text did not stop the agent that wrote the checker; an independent instance with a fixed subject and its own fixtures did. So the verifier is protected from the party it constrains (§7), loaded from the trusted branch rather than the candidate, and carries a regression corpus made of both reviews' counterexamples.

v0.3 did that and was reviewed in turn. The finding was that it had separated the candidate from the verifier but not from the *tree the verifier reads*: `git archive` obeyed a candidate `.gitattributes`, pytest read a candidate `addopts`, ruff read a candidate `pyproject.toml`, a candidate `conftest.py` rewrote the gate's own results, and the check meant to stop verifier sabotage ran the candidate's own corpus. Each fix had grown its next exemption: the `# boundary:` note invented so the verifier's crash barrier could be legal laundered every marker in the denylist, including a skip on a failing test. v0.4 therefore adds a fourth identity to the trust model — the evidence tree — and makes the rule that no input to the judgment may come from the party being judged (§7.1).

The two-price problem the policy addresses: generation cost fell to zero and removal cost did not move. The creation price cannot be restored, so the mechanisms make removal cheap (§5) and couple the two prices (§4). Stigmergy is the analogy, with the audit's limit attached: pheromone evaporation is safe because re-laying a trail is cheap; code and published results are not, so expiry triggers re-evaluation, not unconditional deletion.

"Compliance is cheaper" is a design target, not a proven property of any executor. Different runtimes respond to context length, stop conditions, tool-call counts or wall-clock time rather than to a computed future cost, and a current instance need not internalize a later instance's work. The policy therefore lowers the friction of the legal path, mechanically blocks the known illegal paths, and measures the rest (§5).

## 2. Assumptions

- One change = one branch, merged as one unit (PR). The **change type is the `TYPE:` line of the committed record** `docs/changes/<type>-<slug>.md`; the filename and the branch prefix must agree with it. The record, not the branch, is the identity that survives merging (audit F09).
- Source under `src/`, tests under `tests/`. Python tooling is assumed in the shipped `Makefile` (`pytest`, `ruff`, PyPI); the check ids are the contract, the recipes are the adapter. The dependency check is PyPI-only; other manifests are recognized by name but not verified.
- The trusted branch is `main` (`MAIN` in `policy.mk`). The verifier and the policy in force are always loaded from it (`VERIFIER_REF`), never from the candidate.
- Two profiles: `enforced` (default) and `advisory`. `REQUIRED_CHECKS_<PROFILE>` in `policy.mk` lists the checks that must PASS; everything else runs and is reported. Unimplemented checks report NOT_RUN and are in neither required list. The advisory profile is for watching a mechanism before it binds and never sets `merge_eligible`; the profile comes from the command line only, never from the environment.
- The **evidence tree** — the export the gate tests, and the configuration the tools inside it read — is an input to the judgment, so it comes from the commit and from the verifier, never from files the candidate wrote to steer them.

## 3. Clauses

### §1 Definition of done — single-subject rule

*Analog: the single-subject rule in state constitutions, which stops riders.* Here it stops a test edit from riding inside a feature, or a threshold change inside a fix.

CHEAPEST PATH. Pick the type first (it fixes what you may touch), write the test before the code (§3 makes this the cheap route), write each record line at the moment of the decision. "Then stop" is the anti-scope-creep lever: unrequested work is a debit.

CHECK (`type`, `protected_files`). Exactly one record added or modified under `docs/changes/`; `TYPE:` ∈ the seven types, equal to the filename prefix and to the branch prefix when a branch is known. Diff path set ⊆ the type's allowed set. Protected set touched ⇒ type must be `policy`; `policy` touches the protected set only. `renew` diffs contain only `SUNSET` lines (line-wise heuristic; a behavior change on a tagged line is not yet detected — phase 2, audit P08).

METRIC. Share of changes refused by the type gate; should fall toward zero as splitting becomes cheaper than being refused.

### §2 Terminal states — BLOCKED is the cheapest exit

*Analog: Hirschman's "voice."* A system in which dissent is cheaper than corruption gets dissent instead of corruption.

CHEAPEST PATH. Three lines, no code, no test, no review, no penalty. A masked error costs the handler, a test written around it, a `masks` tag whose expiry the agent will meet again, a `WHY:` line, and a guaranteed audit. The round trip (the task owner answers `NEED` and the task returns) is the guard against frivolous filing.

The denylist is a list of constructs, not a principle, because a construct list is what a linter can refuse. Two catch-all shapes are sanctioned, both on one line and both in the 100% audit set: the stopgap (`# noqa: BLE001` paired with a complete `masks` tag; a partial tag exempts nothing, audit P09) and the permanent **boundary** (`# noqa: BLE001  # boundary: <typed failure returned>`) for a crash barrier at a process or check edge whose body returns or raises a typed failure. The second shape was added when the v0.3 verifier was held to its own denylist: its per-check crash barrier is exactly such a boundary, and the v0.2 policy had no legal way to write it — a POLICY-GAP filed by the verifier's own author.

CHECK (`masking_markers`, `masking_ruff`). Diff scan of every added `.py`/`.sh`/`.bash` line anywhere in the tree — `src/`, `tests/`, `scripts/`, `tools/`, a root or `tests/` `conftest.py` — for suppression markers, skip/xfail decorators, any handler followed by `pass`/`continue`/`return`, shell masking, and file-level `# ruff: noqa` headers. Two exemptions and no others: a line carrying a well-formed `SUNSET` tag, and a line matching the boundary shape in full whose handler body is parsed with `ast` and ends every path in a `raise` or a `return` of something other than `None`. A `# boundary:` note anywhere else exempts nothing (audit P0-1). Ruff `E722 BLE001 S110 S112 S113` runs `--isolated` over every source directory present, so the candidate's own ruff configuration does not apply (audit P0-2); ruff absent ⇒ NOT_RUN, which blocks an `enforced` merge rather than passing silently.

METRIC. Error-masking constructs per 1,000 changed lines (reference: +47% in AI-era commits, GitClear 2026). BLOCKED filings per task by TAG. Share of BLOCKED whose `NEED` was already answered in the task — a measure of spec quality, never a sanction.

### §3 Evidence — separation of powers over verification

*Analog: Federalist 51.* The role that writes the code cannot certify it; the role that certifies is not done until it has found something or paid to say it looked.

Definitions. **BLIND** tests are written from the spec and committed before the implementation; the commit is the registered hash. **SEPARATE ROLE** tests are written by a different instance given the spec and public interface, not the diff. **H1** forbids modifying or deleting a test once committed; adding new tests is how BLIND works.

What the gate proves and what it does not (audit F05): the gate proves that no committed test was modified, that no commit touched `src/` and `tests/` together, and that a `feature`/`fix` added at least one test file. It does not prove that the tests were written before the implementation existed somewhere, nor that they fail on the base commit — red-before-green is a separate check, reported NOT_RUN until implemented (phase 2). These are three statements; the record and the metrics keep them apart.

CHEAPEST PATH. Test-first from the spec, commit, implement until green. One motion satisfies BLIND, H1 and the added-test rule with no second agent and no waiting. A spec too vague to test is `BLOCKED SPEC-AMBIGUOUS`, not a reason to reach for a mock. A test that looks wrong is `BLOCKED TEST-DEFECT` — three lines against an H1 refusal plus rework.

CHECK (`export_integrity`, `harness_integrity`, `test_inventory`, `unit_tests`, `red_before_green`, `h1`, `mocks`, hook).

- `export_integrity`: the path set of the export equals `git ls-tree -r <subject>`. A candidate `.gitattributes export-ignore` cannot delete the frozen tests from the gate's own evidence (audit CR-01).
- `harness_integrity`: off a `policy` change, no added line may ship an `export-ignore` attribute, a `conftest.py` hook that touches collection or reporting, a `[tool.pytest…]`/`[tool:pytest]`/`[tool.ruff…]` section, an `addopts`/`testpaths`/`python_files` key, or a file-level `# ruff: noqa` (audit CR-01, CR-02, CR-03).
- `test_inventory`: pytest collects, under the gate's own configuration, at both base and subject. Any id present at base and gone at the subject is a FAIL however it vanished — deletion, `export-ignore`, `--ignore`, a collection hook. A `feature`/`fix` must add at least one *collected* id, which an inert `.py` file does not (audit CR-04).
- `unit_tests`: the suite runs on the export with `-c <the gate's own ini> --override-ini=addopts=`, so the candidate's pytest configuration is not read (audit CR-02).
- `red_before_green`: the change's new test files are copied onto a clean export of the base and run; pytest must exit 1 or 2. Exit 0 or 5 means they tested nothing the change did.
- `h1`: per commit in `base..subject`, no `M`/`D`/`R` in the frozen set — `tests/`, `scripts/tests/`, every `conftest.py`; `refactor` touches no tests; `feature`/`fix` never mix `src/` and `tests/` in one commit.
- `mocks`: an AST scan of added lines under `tests/` **and** `src/` for `patch`, `patch.object`, `patch.dict`, `monkeypatch.setattr/delattr` and `setattr`, resolving each target through the file's own imports, compared with the allowlist **at the trusted ref**. Resolution fixes both halves of the v0.3 defect: the object form `monkeypatch.setattr(core, "value", …)` is now caught, and `patch.object(requests, "get")` is no longer falsely refused. A target computed at run time is reported unresolved, never silently allowed.
- Hook: refuses `src/` edits while `tests/` has uncommitted changes, and edits to committed test files off a `test/` branch; a `renew` branch may edit `src/` because that is where a tag lives (audit RT-07); `tests/MOCK_ALLOWLIST` is a policy file (P23).

METRIC. Unauthorized weakening rate of frozen acceptance (edits to committed tests attempted on implementation branches, caught by hook or gate). Share of **test commits** adding mocks (reference: 36% agent vs 26% non-agent, arXiv:2602.00409 Table 7 — same denominator). Share of commits touching test files (reference: 23% vs 13%, same paper — this measures test activity, not tampering, and should *not* fall). Mutation score and red-before-green once automated.

### §4 PAYGO — the complexity ledger

*Analog: pay-as-you-go budget rules.* New spending must be offset. Here new complexity must be offset by deletion.

Status: advisory. The weights (+1 module, +1 public symbol, +3 dependency) are uncalibrated; pricing public surface and leaving internals free invites the substitution "make it private, split less, hide coupling" (audit §5.2); zero static references do not prove no external caller, plugin entry point, reflection or serialization dependency. The ledger therefore reports NOT_RUN, is not in any required list, and enters the enforced profile only after E-series evidence on maintenance tasks.

CHEAPEST PATH (once live). Over allowance, the least-effort credit is deleting code with zero references; `make credits` lists candidates. Credit must reward verifiable retirement of a responsibility, not "some lines deleted".

CHECK (`ledger`, NOT_RUN). Ledger computed by tooling from the diff, never self-reported; credits require a zero-reference proof plus a green suite and, for public symbols, a statement of who the external callers could be.

METRIC. Net complexity per change; share of `refactor`/net-credit changes (reference: refactoring share −70%, GitClear 2026); duplicated-block delta (+81%, GitClear 2026); dependency count; banked credit.

### §5 Sunset — everything temporary has an expiry

*Analog: sunset legislation.* Renewal costs; deletion is cheap.

Revised default (audit §5.3): expiry triggers **re-evaluation**, and deletion is the default only when the retirement condition is verifiable (no callers, green suite, no external contract). A stable adapter at a system boundary is not temporary debt and should be promoted, not deleted on a timer.

CHEAPEST PATH. Delete when the retirement condition holds: no record, earns credit. Renew on a `renew/` branch: a justification, a guaranteed audit, two renewals max. Defer once: `BLOCKED SUNSET-EXPIRED` in the record plus `grace:<today>` on the tag, seven days.

CHECK (`type` renew rule, `sunset`). Every `SUNSET` token at the subject must parse; in code a partial tag or an impossible date is malformed, never a crash. The per-kind term (30 days for `todo`/`masks`/`skip`, 90 otherwise) is checked on the tag lines the change **adds or renews**; tree-wide only the 180-day maximum applies, so a legal tag written by someone else never blocks an unrelated change (audit RT-04, and `SUNSET_MAX` now does something). A tag's date, kind or reason may change only on a `renew` branch, and a renew is a field-level diff: removed and added lines pair up, the code before the tag is byte-identical, kind and owner are unchanged (audit P08, P12). Expired ⇒ FAIL unless all of: `grace:` is dated today or earlier and within 7 days; the change's **own** record files `BLOCKED SUNSET-EXPIRED`; and the same tag was not already in grace at the base — the deferral is once (audit P0-8). Untagged `TODO`/`FIXME`/`HACK`/`XXX` on added code lines ⇒ FAIL. Not yet automated: stable tag ids and the renewal count (`renewals_cap` NOT_RUN).

METRIC. Live tags (count, median age). Resolutions by path. Renewals per tag. Introduced-issue survival to the latest revision (reference: 24.2%, arXiv:2603.28592v1).

### §6 The record — paperwork that is cheapest to fill honestly

*Analog: the legislative record.* The form is designed so that the least-effort way to complete it truthfully is to have done the thing.

CHEAPEST PATH. The search is one command and usually finds the helper. The dependency record is cheapest to skip by not adding the dependency. The `WHY` line is one sentence; writing it at the moment of decision is cheaper than reconstructing it.

CHECK (`records`, `deps`). Record committed at the subject (an uncommitted record is not evidence, P16). The change's record is the one it adds; failing that the single one it modifies; and when a `<type>/<slug>` branch is given, the one matching it — so correcting a previously merged record alongside your own is allowed (audit RT-08). `TYPE:` matches; `WHY:` on `feature`/`fix`; `TESTS:` on `feature`/`fix`/`refactor`; new files under `src/` ⇒ `SEARCHED:`; every dependency spec actually added to a Python manifest ⇒ a `DEP:` line for that package (bound by name, F10). `deps`: each `DEP` exists on PyPI at that version and is ≥ `DEP_MIN_AGE` days old; `DEPS_OFFLINE=1` ⇒ NOT_RUN (P19); registry unreachable ⇒ ERROR. Not automated: `SEARCHED` replay (`searched_replay` NOT_RUN); per-helper `SEARCHED` binding inside existing modules (P17).

METRIC. Duplicated-block delta. New dependencies per 100 changes. Nonexistent-package attempts caught at CI (reference attempt rates: 5.2% commercial / 21.7% open-source models, USENIX Security 2025; 4.62–6.10% frontier, arXiv:2605.17062 — the merged rate is to be zero). Share of `SEARCHED` with hits ending in `REUSED`.

### §7 Audit — randomness the implementer cannot optimize against

*Analog: random tax audits and independent inspectors, with term limits.*

Selection (`audit-select`): `AUDIT_RATE` of merged changes by a salted draw on the subject SHA, plus 100% of `renew`/`policy` changes, any change to the protected set, `masks` tags, `boundary` exemptions, `NONE-FITS` with hits, `POLICY-GAP` and `SUNSET-EXPIRED` filings, allowance grants and `AUDIT_ALWAYS_PATHS`. Those globs are matched with a recursive matcher in which `**` spans zero or more directories: under `fnmatch`, which v0.3 used, `src/**/auth*` did not match `src/auth.py`, so the most obvious security-sensitive paths never triggered the rule the whole design leans on (audit P0-10). The type comes from the committed record, so the 100% triggers survive merging (P24). The selector only selects; triggering the auditor, validating its deliverable and re-auditing are orchestrated outside the gate.

Auditor: a fresh instance given the subject and base SHAs from the gate result, the diff and the record at the subject — never the implementer's session. Procedure and outputs: `.claude/skills/audit/SKILL.md`. Against fault-finding bias (audit §5.4): a minimum risk surface is checked before attesting; outputs are `FINDING`, `NO-FINDING`, `INCONCLUSIVE`; severity and uncovered paths are reported; auditors are judged on overturned attestations and escaped regressions, not on finding counts. `OWNERSHIP-LOSS` is a located contract defect, not a forced failing test.

METRIC. Finding rate per audited change paired with attestation-overturn rate. RECONSTRUCT adequacy rate. Findings by clause.

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

Each row is a behavioral dependent variable with a published reference point, so clauses can be ablated one at a time behind pre-registered gates instead of evaluating `AGENTS.md` as a monolith against a task-resolution rate. State every result with its scope — this repository, this task family, this model set, this period. None of the references is causal; several are vendor-sourced; none was independently re-verified here except where a fixed arXiv version is cited. They indicate direction and magnitude, not targets, and do not justify any specific parameter value in §6.

| Metric | Clause | Direction | Published reference | Source and caveat |
|---|---|---|---|---|
| error-masking constructs / 1k changed lines | §2 | ↓ | +47% rise in AI era | GitClear 2026, 623M changes; commercial vendor, longitudinal not causal |
| unauthorized weakening of frozen acceptance (attempts caught) | §3 | → 0 | — | repo-local; H1 hook and gate refusals |
| share of test commits adding mocks | §3 | ↓ | 36% agent vs 26% non-agent test commits | arXiv:2602.00409v1, RQ2 / Table 7 — denominator is test commits |
| share of commits touching test files | §3 | should not fall | 23% agent vs 13% non-agent | arXiv:2602.00409v1 — test activity, includes legitimate additions; not a tampering measure |
| mutation score on touched lines | §3 | ↑ | — | repo-local baseline needed; not automated |
| refactor share / net-credit changes | §4 | ↑ | refactoring −70% | GitClear 2026 |
| duplicated-block delta | §4, §6 | ↓ | +81% | GitClear 2026 |
| introduced-issue survival to latest revision | §5 | ↓ | 24.2% | arXiv:2603.28592v1 (304,362 commits, 6,275 repos) |
| nonexistent-package attempts merged | §6 | 0 | attempt rates 5.2% / 21.7%; 4.62–6.10% frontier | USENIX Security 2025; arXiv:2605.17062 |
| new dependencies / 100 changes | §6 | ↓ | — | repo-local baseline needed |
| RECONSTRUCT adequacy rate | §7 | ↑ | — | repo-local; operational definition of ownership |
| finding rate × attestation-overturn rate | §7 | ↓ × low | — | repo-local |
| false-block rate (legitimate changes refused) | all | low | — | repo-local; the cost side of every rule |

Primary outcomes for any experiment: real completion rate, hidden regressions, unauthorized acceptance weakening, false-block rate, maintenance-task pass rate, token/time/tool overhead and human interventions. Complexity and deletion counts are secondary. Repeated maintenance tasks test the anti-entropy claim better than one-off features.

## 6. Parameters

Authoritative in `policy.mk` **at the trusted ref** — the verifier parses that file; environment variables cannot override policy values. Mirrored as literal numbers in `AGENTS.md`; a `policy/` change updates both. Starting values, pre-registered; none is calibrated.

| Parameter | Value | Used by |
|---|---|---|
| `PROTECTED_PATHS` | `AGENTS.md policy.mk tests/MOCK_ALLOWLIST docs/agents-policy.md Makefile scripts/ .claude/ .github/ .gate/ .gitattributes` | §1, H5, H6 |
| `REQUIRED_CHECKS_ENFORCED` | `type protected_files export_integrity harness_integrity unit_tests test_inventory red_before_green h1 mocks masking_markers masking_ruff sunset records deps verifier_selftest` — one physical line, because a value truncated by a continuation is how a required check silently becomes advisory | gate |
| `REQUIRED_CHECKS_ADVISORY` | `type protected_files unit_tests` | gate |
| `UNIT_TESTS_TIMEOUT` | 900 s | §3 |
| `ALLOWANCE_DEFAULT` / `BANK_CAP` | 2 / 6 | §4 (advisory) |
| `MUTATION_MIN` | 0.70 | §3 (not automated) |
| `SUNSET_SHORT` / `SUNSET_LONG` / `SUNSET_MAX` / `SUNSET_GRACE` | 30 / 90 / 180 / 7 days | §5 |
| `RENEWALS_MAX` | 2 | §5 (not automated) |
| `DEP_MIN_AGE` | 30 days | §6 |
| `AUDIT_RATE` | 0.20 | §7 — consumed by `audit-select` |
| `REAUDIT_RATE` / `ATTEST_MIN_PATHS` / `AUDITOR_OVERTURN_MAX` | 0.10 / 3 / 0.20 | §7 — **declared and consumed by nothing.** They price the auditor's accountability, and no code reads them (see §7.6) |
| `AUDIT_ALWAYS_PATHS` | `src/**/auth* src/**/secret* src/**/subprocess* src/**/net* src/**/sql* src/**/serial*` | §7 — adapt to the layout |

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
