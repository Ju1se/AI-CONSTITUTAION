# AGENTS.md

Policy for agents changing this repository. This file states operative duties; `policy.mk` supplies parameter values. `docs/agents-policy.md` explains legislation and creates no additional permission. A check result is evidence within its stated scope.

## Authority and effect

- Explicit task-owner instructions take precedence. Distinguish task instructions, clause-authorized exceptions, and policy amendments. Do not infer an exception or amendment from a request to finish. Record explicit overrides by clause, scope, reason and duration. Ambiguous conflicts are `BLOCKED H-CONFLICT`; existing authorization need not be requested again.
- Hard rules allocate authority and protect evidence; ordinary rules govern work within that authority. Interpretation cannot invent exceptions. Rules are binding unless expressly advisory. Ledger, mutation target, SEARCHED replay and auditor-accountability parameters are advisory; targets alone cannot block work or require unrelated work. Search, truthful records and §7 evidence duties remain binding.
- Amendments take effect on `main` at the recorded effective commit or later transition; name pending work covered. Preserve earlier rules, evidence and outcomes; reconsideration creates a new decision. Authors cannot certify their own amendments. Mechanism refusals require referral, never bypass or relabeling FAIL/ERROR/NOT_RUN as PASS.
- Exceptions need prior written owner authorization naming clause, scope, reason, conditions, effective point and expiry/event, and only apply where a clause permits them. §3 additionally requires independent approval. Expiry never renews itself. Repeated similar exceptions require reconsidering the general rule.

## Commands

- `make test`: business tests; `make selftest`: verifier tests; `make gate`: merge decision on committed objects using policy/verifier from `main`, recorded in `.gate/result.json`.
- Local feedback: `make check-type check-evidence check-tests check-masking check-sunset check-records`; deletion candidates: `make credits`.
- Before a helper/module/wrapper: `rg -n "<concept>" src/`; before a dependency: `pip index versions <pkg>`.
- Start branch `<type>/<slug>`, copy `docs/changes/_TEMPLATE.md` to `docs/changes/<type>-<slug>.md`, and commit the record with the work.

## How a task ends

**DONE** — the authorized specification is met, binding duties fulfilled, acceptance decisions resolved, and every required merge check is PASS. FAIL requires correction; ERROR requires repairing or reporting inputs/environment; NOT_RUN awaits execution. None authorizes merging. Distinguish completed role work from decisions owed by another role; never certify unperformed checks. Stop at the authorized scope.

**BLOCKED** — file three lines and pause only dependent work; independent authorized work may continue. No penalty or proof-of-failure exercise is required. The owner must answer, designate a decision maker, revise scope or explicitly defer; silence is not approval. Persist the filing before handoff, retain its disposition, and resume only the scope resolved by the answer.

```
BLOCKED <TAG>: <affected scope and what cannot proceed>
NEED: <smallest missing decision/fact/artifact and who supplies it>
STATE: <branch/commit, or "none">
```

| TAG | When |
|---|---|
| `SPEC-AMBIGUOUS` | plausible readings change acceptance and no authorized default resolves them |
| `FAILURE-SEMANTICS` | the caller's required observation on failure is unknown |
| `TEST-DEFECT` | existing acceptance appears inconsistent with the governing spec |
| `NO-HARNESS` | a required real-path test has no harness |
| `ENV-MISSING` | a dependency, fixture or credential cannot be obtained within H4 |
| `SUNSET-EXPIRED` | safe retirement cannot be established within task scope |
| `H-CONFLICT` | an instruction conflicts with a hard rule and authority is unclear |
| `POLICY-GAP` | an evasion is cheaper than compliance — name it for independent assessment |

## Hard rules

A change is a commit series on one branch, merged as a unit. A branch or role name grants no authority. Binding duties remain duties when a tool cannot establish them.

- **H1** Implementers must not unilaterally modify, delete, skip, weaken or suppress existing acceptance, or stop its collection. Frozen: `tests/`, `scripts/tests/` and every `conftest.py`; revisions require §3 approval. Preserve old specs, tests and outcomes in committed history. Commit tests defining approved behavior before implementation, never together.
- **H2** BLOCKED is always valid, never penalized, and never removes the task from its owner.
- **H3** No merge with a failing applicable suite, unresolved expired sunset obligation or non-PASS required check. §3 records acceptance at a transition before edits; failure cannot retroactively select another standard. Complexity allowances remain advisory until expressly activated.
- **H4** No paid run, model/provider API call or non-registry network access without separate written authorization. Permission to upload code is not such authorization.
- **H5** Protected: `AGENTS.md`, `policy.mk`, `tests/MOCK_ALLOWLIST`, `docs/agents-policy.md`, `Makefile`, `scripts/`, `.claude/`, `.github/`, `.gate/`, `.gitattributes` (listed in `policy.mk`). Changes use `policy/*` plus their record and require independent assessment. Policy comes from `main`; counterexamples bind unless §3 approval explicitly supersedes them, preserving their history and replacement obligations.
- **H6** The judged tree is the commit. Export, collection/reporting rules and tool configuration are policy: `.gitattributes`, harness hooks, pytest/ruff sections, `addopts`, file-level suppressions. Candidates may not configure their own judgment; such changes require policy authority.

## Change type (§1)

Record TYPE, filename and branch prefix agree. One type per change; `docs/changes/` is allowed in every type. A §3-approved migration may coordinate behavior and exact acceptance revisions within a feature/fix, with separate test/implementation commits. It never permits protected changes on that branch.

| type | may touch | must have |
|---|---|---|
| `feature` `fix` | `src/`, new `tests/`, manifests; existing acceptance only under §3 | new test file; WHY; migration approval if applicable |
| `refactor` | `src/` | no acceptance change; suite green |
| `test` | `tests/`, except the allowlist | BLIND or separate-role tests; §3 for existing acceptance |
| `chore` | tooling/docs/CI outside `src/`, `tests/` and protected paths | record |
| `renew` | one sunset tag line | date, reason, retirement condition; independent assessment |
| `policy` | protected set and harness policy under H6 | applicable counterexamples preserved; §3 for revisions; independent assessment |

## Errors and failure semantics (§2)

- A handler propagates an exception with context, returns a typed failure the caller must match, or logs ERROR with the exception under a `masks` tag. A fallback must not conceal a failure the caller needs to know.
- Refused: empty/swallowing catches, ignored return codes, `|| true` or `2>/dev/null` on material steps, unbounded retry, timeout-less I/O, and unauthorized suppression/skip markers, wherever added code lives.
- Two catch-all forms, both independently assessed: `except Exception as e:  # noqa: BLE001  # SUNSET <date> masks owner:<id> reason:<why>` for a temporary handler, and `except Exception as e:  # noqa: BLE001  # boundary: <typed failure>` for a permanent process/check boundary. The latter must return or raise that failure on every path; `return None` is insufficient. The former must satisfy the handling duty above. Partial tags and boundary notes on other suppressions/skips grant no exemption.
- Unknown failure semantics: `BLOCKED FAILURE-SEMANTICS`. A sunset tag does not independently authorize a suppression, skipped test or H1 violation.

## Tests and evidence (§3)

- BLIND tests are authored from the spec before implementation; a separate author receives the spec/interface, not the implementation diff. Commit tests first. Every feature/fix adds a test file and exercises a real in-repo call path; no harness means `BLOCKED NO-HARNESS`.
- Evidence includes new cases collected and failing on the recorded pre-change base; identify an import error as such. A green suite proves no more than its assertions. Mutation ≥ 0.70 is advisory: record the measurement or why unmeasured.
- Mock only allowed I/O boundaries in `main`'s `tests/MOCK_ALLOWLIST`, never owned modules. Unresolved targets are not proof of permission; disclose them and obtain a decision. Tests cannot widen their own allowlist.
- **ACCEPTANCE revision:** distinguish correcting a test against the current spec from migration to an authorized new spec. Before edits, the owner designates an approver other than the implementer or revision proposer, with power to refuse. Record decision maker/date/reason, spec versions, exact old/new cases, effective transition and retained evidence. A second instance selected by the proposer has no automatic authority.
- Corrections use `test/`; behavior migrations use §1's feature/fix exception. Protected acceptance, including `scripts/tests/` and harness policy, requires `policy/`. Approval identifies retained and superseded obligations. Preserve prior outcomes. Without approval pause as `TEST-DEFECT` or `H-CONFLICT`; mechanism mismatches await separate resolution, never bypass.

## Complexity ledger (§4) — advisory

- Observation weights: +1 source module, public symbol or abstraction layer; +2 config surface/flag; +3 direct dependency. Retirement uses corresponding credits, −1 duplicate block and −2 deleted sunset responsibility. Renames, moves, private symbols, tests, docs and formatting have zero weight.
- Net ≤2 and bank cap 6 are observation targets, not merge conditions or spendable rights. Report related changes together; more branches or private names do not establish reduced responsibility. Do not delete unrelated code to meet an advisory target.
- Activation requires a policy amendment defining counting/overlap, bank ownership, related-change aggregation, legitimate counterexamples and benefit versus burden. Tool availability does not activate the rule. Credit requires safe retirement, including external obligations.

## Sunset (§5)

- Tag temporary compat/shims/adapters, flags, TODO/FIXME/HACK, `masks`, skips/xfails, deprecated aliases, temporary config and vendored code. A stable boundary may be permanent from inception with its contract, owner and rationale recorded. Tags grant no H1/§2 exemption.
  `# SUNSET <YYYY-MM-DD> <compat|flag|todo|masks|skip|deprecated|config|vendored> owner:<id> reason:<why>`
- Terms: 30 days for todo/masks/skip, 90 otherwise on added/renewed tags; tree-wide maximum 180 days. Expired obligations block merging unless resolved or validly deferred. Change tag date/reason only on `renew/`; preserve code, kind and owner. A changed responsibility needs its own authorized change, not a renewal.
- **Delete** only when no internal/external obligation remains and the suite is green; **renew** with reason and retirement condition, twice maximum; or **promote** to a permanent responsibility with contract and owner. Every path has a record; ledger effects remain advisory.
- If safe retirement cannot be established within scope, file `BLOCKED SUNSET-EXPIRED` naming each tag and unmet condition, including external contracts; add `grace:<today>` once per tag for at most seven days. Bind filing to tag. Grace defers only that obligation. Establish retirement conditions before a risky deletion.

## Records and legislation (§6)

Add and commit one `docs/changes/<type>-<slug>.md`. Correct older records transparently, preserving original decisions. New helper/module/wrapper: SEARCHED first. New dependency: DEP first. Truthful search and records are duties; automated replay is advisory.

```
TYPE: feature
WHY: <decision, alternative and reason>
SEARCHED: rg -n "<concept>" src/ → <hits with locations> | REUSED: <path> | NONE-FITS: <reason per hit>
DEP: <name>==<version> lookup:<command> published:<YYYY-MM-DD> | REASON: <why> | INSTEAD-OF: <alternative>
TESTS: <exact commands run; distinguish anything not run>
```

- Each manifest dependency needs its actual package/version, existence evidence and publication date. Minimum age: 30 days. Prior written owner authorization may waive age only for an exact version/change, stating necessity, alternatives, withdrawal plan and expiry. Existence and record duties remain; required refusals await separate resolution.
- A policy amendment records its protected interest, adjacent allowed/refused cases, compliance burden, alternatives, affected clauses, effective point and pending-work treatment. Trials name scope, review point, benefit/burden measures and fallback. Advisory targets need explicit amendment to become binding.
- Applicable ACCEPTANCE, EXCEPTION and EFFECTIVE entries carry the approvals above. Repeated exceptions prompt general reconsideration. Ordinary changes need no extra authorization forms. A template, branch name or author assertion is not approval.

## Decision rules (§7)

Apply the clauses above consistently: summaries create no extra prohibitions or exceptions. Findings reopen relevant work without sanctioning the agent.

The audit duty covers 20% of merged changes plus all policy/renew changes, acceptance revisions, exceptions, masks/boundary exemptions, NONE-FITS with hits, POLICY-GAP/SUNSET-EXPIRED filings and AUDIT_ALWAYS_PATHS. This specifies duties, not tool coverage. Independent decisions may be FINDING (reproducible evidence or located contract defect), NO-FINDING (at least three examined attack paths, commands and limitations), or INCONCLUSIVE (missing evidence and next decision). Inconclusive is neither approval nor proof of defect. Legislative authors do not adjudicate their own amendments.
