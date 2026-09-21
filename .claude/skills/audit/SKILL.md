---
name: audit
description: Audit and adjudicate a recorded change under the applicable repository policy. Use for an authorized audit, review, verification, spot-check, or re-audit of a recorded change; selection by make audit-select; renew or policy changes; masks tags; POLICY-GAP or SUNSET-EXPIRED filings; allowance grants; or questions about test evidence and design rationale. Establish jurisdiction and evidence, test specific compliance claims, and issue a reasoned FINDING, NO-FINDING, or INCONCLUSIVE decision with bounded remedies and independent review. Follow the task owner's access and role limits.
---

# Audit and adjudicate a recorded change

Exercise judgment within the authority already granted for the case. This procedure does not authorize changing the specification, acceptance criteria, implementation, verifier, or policy, and does not grant permission to merge. Apply the binding rules; recommendations and personal preferences cannot become additional acceptance conditions.

Valid results are **FINDING** (a proved violation), **NO-FINDING** (a costed attestation within the completed scope), or **INCONCLUSIVE** (material evidence, authority, or coverage is missing). A finding needs a reproducible failing test or a located contract defect, together with the applicable obligation and the reasoning that connects them. Neither finding a defect nor issuing an approval is a quota. "LGTM" is not an output.

## 1. Admit the case and fix its scope

Record these inputs before investigating; verify them from the supplied immutable artifacts, never from whatever branch happens to be checked out:

- `SUBJECT` and `BASE`: the audited commit and the recorded comparison base, from the original gate result (`subject_sha`, `base_sha`) or the selector's output. Resolve discrepancies before judging.
- `RULESET`: the applicable policy/specification versions, their authority and effective scope, and the required checks. Record whether this is a review under the original rules or a separately authorized assessment under later rules. A later-policy result does not overwrite the historical result.
- `QUESTIONS`: the obligations and claims submitted for decision, including any full-change coverage required by the authorized audit.
- `ACCESS`: permitted files, submitted rule excerpts, evidence, commands, and any explicit exclusions. Reading necessary case evidence does not confer power to change it; access restrictions still apply. Do not inspect excluded roles or run a command that reads or executes excluded material.
- `RECORD`: the change record as committed at `SUBJECT`, including its `TYPE:`, and the permitted portion of the `BASE` to `SUBJECT` diff.
- `MANDATE`: the appointing authority, permitted remedies, investigation limit, and the designated route for independent review. Use authorization already given; do not request it again.

Use a versioned evidence inventory: artifact identity, source, relevant location or command, and observed result. A submitter's summary is a claim until checked against accessible evidence. Missing essential inputs make the affected question `INCONCLUSIVE`; identify the missing item and its custodian without broadening access. Do not call a partial review a full-change attestation.

### Independence and recusal

Do not finally adjudicate your own implementation, submitted change, disputed acceptance revision, or amendment of this judicial procedure. Disclose participation before taking the case; the appointing authority or its existing delegate assigns an eligible reviewer. A self-selected second instance is not independent authorization.

Do not read private implementer sessions, chats, or reasoning. If already exposed to them, disclose the exposure and recuse from the independent audit; do not silently discard the context and claim freshness. A response deliberately submitted into the shared case record is admissible argument and does not by itself require recusal. Recusal establishes no defect in the subject.

## 2. Reconstruct the claim, then seek evidence

Within the admitted scope, read the permitted diff and touched material before the record's rationale. Write a provisional reconstruction in at most three sentences, then compare it with `WHY:`. Separate observations from assumptions.

Use `RECONSTRUCT: adequate`, `unresolved`, or `contradicted`, with the supporting locations. Inability to guess the purpose or rejected alternative is not a violation. An `OWNERSHIP-LOSS` finding requires an identified applicable obligation and a demonstrated omission or contradiction within that obligation; otherwise seek clarification, state the uncertainty, or leave a nonbinding observation. Do not label an intelligible but disliked design a defect.

### Test a specific obligation

For each hypothesis, state the existing rule, the input or condition it covers, the expected behavior, and what evidence would support or refute the claim. The applicant supplies the prescribed completion evidence. The auditor proves each alleged violation; neither side owes a proof that no unknown defect can ever exist.

Examine the applicable minimum risk surface: failure paths of new handlers, boundary inputs of new public symbols, interactions with callers, and behavior covered by mocks. Record why an item does not apply; an inapplicable item is not a tested path. Broaden investigation only when evidence connects the new question to the admitted scope, and record the reason. A question outside that scope is a referral, not a new condition imposed on this case.

Run relevant existing checks or construct a minimal reproduction where needed and authorized. A new test must exercise a real in-repo call path and obey the applicable mock restrictions. Do not modify existing tests, expected results, collection, implementation, or the trusted checker to obtain a desired outcome. If the permitted evidence cannot establish the claim, report that limit.

- A failing test becomes a finding only after establishing the expected behavior from an applicable rule, checking the environment and causal link, and considering a material counterexample or response. Distinguish a defect introduced by the change, an existing defect relevant under an applicable whole-tree duty, and an unrelated pre-existing defect.
- A located contract defect may be established by verified records, authority, or incompatible obligations; no artificial failing test is required. A genuine unresolved choice between lawful interpretations is not itself proof against the implementation.
- Preserve an authorized new ordinary test exhibit on a `test/audit-<slug>` branch and cite its commit and test node. A protected-path exhibit requires the applicable separately authorized policy procedure. Evidence creation does not authorize a repair.
- `NO-FINDING` requires at least three distinct examined attack paths, the applicable minimum risk surface, and any higher binding coverage requirement. List exact commands and results. Repeating one command does not create distinct paths. A lower advisory parameter cannot reduce this floor. This is the overall attestation minimum, not a prerequisite to withdrawing a refuted allegation.
- An absent harness, inaccessible evidence, or exhausted investigation limit with material questions unresolved gives `INCONCLUSIVE`. State the missing evidence and next decision; do not invent a defect or an attestation to finish the report.

Consult [the adjudication examples](references/adjudication-cases.md) when distinguishing evidence, authority, and remedies. The examples illustrate this procedure; they do not amend the applicable rules or supply facts about a subject.

## 3. Recheck within the granted access

When authorized and supported by the existing interface, rerun the trusted verifier against the recorded pair and preserve the original result:

```sh
make gate SUBJECT=<sha> BASE=<sha> GATE_OUT=.gate/recheck-<unique-case-id>.json
```

Use an unused output path. Confirm the existing interface addresses the recorded pair rather than the audit branch. Record verifier provenance, the resolved policy/verifier revision, toolchain, subject, and base. Do not assume that a provenance label alone establishes their identity. If the intended rule version or pair cannot be selected, do not change the verifier or route around its refusal. Mark the intended recheck `INCONCLUSIVE`; label any authorized later-policy run as a separate assessment.

Use the required toolchain, including `ruff`, `pytest`, and the interpreter selected by `PY` where applicable. Record all required statuses and compare them with the required set in the admitted ruleset. Do not inspect another role's files or run a whole-repository gate when the task excludes that access. An unavailable or unauthorized recheck is an evidence limitation, not permission to infer its result.

| Observed status | Judicial treatment |
|---|---|
| `PASS` | Evidence that this check passed for this pair and configuration; no claim about unexamined obligations. |
| `FAIL` | The check's condition was not met. Explain the applicable rule and evidence before attributing a substantive violation. |
| `ERROR` | The check failed to produce a valid result. Identify the cause if established; do not presume implementation fault. |
| `NOT_RUN` | Required evidence is absent. Explain the missing prerequisite without treating absence as proof of a defect. |

Missing, unknown, or contradictory required statuses and unverifiable provenance leave that part inconclusive. Preserve them in the report. A separately proved defect can coexist with these limitations. If binding rules require every required check to pass, any required non-PASS or missing result continues to prevent authorization; judicial interpretation cannot relabel it PASS.

## 4. Hear the response and give reasons

Before finally recording an adverse finding, expose the proposed obligation, evidence, causal claim, and remedy through the authorized case channel. Give the affected party the opportunity specified in the mandate to respond; if no process is specified, request the missing procedure from the appointing authority. A response already in the case record can satisfy this opportunity; do not repeat it unnecessarily. An explicit waiver after disclosure can be recorded where the mandate permits it. Do not contact other people or create tasks without existing authorization.

Address each material response with evidence: accept it, distinguish it, or explain why it does not change the conclusion. Do not demand unrelated work in response to a successful rebuttal. Silence is neither an admission nor approval. If an authorized response period ends, decide on the admissible record and identify its limits; if no authorized closing condition exists, keep the disputed issue inconclusive. Preserve any provisional concern as provisional. Record an inconclusive referral and end the dependent adjudication when a missing procedure prevents a decision; do not wait indefinitely or treat elapsed time as the missing authorization.

Every adjudicated issue needs:

1. The effective obligation and the question within jurisdiction.
2. Established facts and precise evidence references, separate from unresolved claims.
3. Reasons connecting the facts to the obligation, including material contrary evidence.
4. `FINDING`, `NO-FINDING`, or `INCONCLUSIVE`, limited to that issue and coverage.
5. The authorized consequence, affected scope, sufficient corrective or evidentiary condition, and responsible decision-maker.
6. The route and grounds for independent review.

Interpret the existing rules using their authorized hierarchy. Do not invent an exception, a numerical threshold, a general obligation, or a new power from a preference. Where an irreconcilable conflict or genuine policy choice exceeds the delegated interpretive power, identify it and refer it to the competent authority; do not invalidate a rule on self-granted authority.

## 5. Limit the remedy and close the case

Apply the holds or reopening required by binding rules. Within delegated discretion, use the smallest measure sufficient to address the proved issue: request specified evidence, withhold the affected certification, or refer a correction. Explain dependencies before enlarging the affected scope. A narrow finding does not waive a whole-change gate requirement or independently authorize partial merging.

State the property that must be restored and how its satisfaction can be shown. Do not dictate an implementation or require a rewrite unless the applicable obligation actually requires it. Identify an appropriate `fix/`, `test/`, or `policy/` handoff where relevant; the finding does not itself authorize edits, acceptance changes, task creation, or policy amendments. Apply existing task-owner authorization when arranging a permitted handoff.

For the overall report:

- `FINDING`: at least one issue has been proved and adjudicated; separately list incomplete issues and coverage. This does not certify the rest of the change.
- `NO-FINDING`: the admitted required coverage and recheck are complete, with no proved violation or material unresolved issue. The attestation is bounded by its recorded evidence and is not an independent merge approval.
- `INCONCLUSIVE`: no final finding establishes a violation, and material evidence, authority, response procedure, or required coverage is still missing. Name what would permit a decision.

Finality binds the stated subject, ruleset, questions, and evidence. Keep the original evidence and decision when correcting a report; append a dated, linked decision instead of rewriting the earlier reasoning or outcome.

### Independent review and precedent

Unless an applicable rule provides otherwise, permit one ordinary independent review of a disputed decision, assigned by the appointing authority or its existing delegate. The reviewer must not have made the original decision or participated in the disputed work. Review specific factual, interpretive, procedural, or remedy errors against the case record; a fresh instance is not another unrestricted investigation.

Allow material additional evidence with its source and relevance recorded. Issue a reasoned decision to affirm, narrow, reverse, or remand; a remand identifies the unresolved question and return condition. Do not repeat completed issues without a reason capable of changing the outcome.

After ordinary review, reopening requires a reasoned determination of material new evidence, materially unreliable evidence, or a substantial error capable of changing the outcome. Mere dissatisfaction, a different reviewer preference, or a later rule is not that determination. A separately authorized assessment under new rules remains separately labeled. Remand and reopening do not create automatic permission for further appeals or expand access. A re-audit required by applicable selection rules retains its separate mandate; record that basis and do not disguise an ungrounded repeat review as a selected re-audit.

Use comparable prior decisions to explain consistency or relevant differences. Only reasoning necessary to decide an issue under its ruleset carries interpretive weight; incidental suggestions create no new obligation. Distinguish or correct an erroneous precedent with reasons and preserved history. Precedent cannot override the applicable higher-authority rule.

## 6. Record the decision

Write one report per audited change at `docs/audits/<type>-<slug>.md`, using the authorized artifact workflow. Append review and reopening decisions to that report with their own identifiers and dates. Keep evidence references immutable.

```text
AUDIT subject:<sha> base:<sha> type:<type> by:<reviewer-id> date:<YYYY-MM-DD>
CASE: <id> | APPOINTMENT: <authority/reference> | REVIEWER: <identity>
INDEPENDENCE: <participation/exposure disclosure and recusal disposition>
RULESET: <versions, authority, effective scope> | MODE: original-review | later-assessment
QUESTIONS: <admitted issues and required coverage>
ACCESS: <permitted artifacts/commands and exclusions>
LIMIT: <authorized investigation/response limits and closing condition>
EVIDENCE: <versioned inventory: identities, sources, locations, commands, results>
RECONSTRUCT: adequate | unresolved | contradicted — <up to three sentences> | WHY: <committed rationale>
BREAK: FINDING <evidence-ref> | NO-FINDING | INCONCLUSIVE <missing evidence>
PATHS: <each distinct path, obligation, exact command, result; inapplicable items separately>
RECHECK: <subject/base, policy/verifier revisions, provenance, toolchain, all required statuses>
ISSUE <id>: <question> | RULE: <effective clause>
FACTS: <established facts and evidence references; attribution to subject>
RESPONSE: <material objections or recorded opportunity and closing condition>
REASONS: <why the evidence and response support or limit this decision>
DECISION: FINDING | NO-FINDING | INCONCLUSIVE
REMEDY: <authorized consequence, scope, sufficient resolution condition, decision-maker>
SEVERITY: <supported practical consequence, not speculation about intent>
UNCOVERED: <unexamined paths and unresolved issues>
RESULT: FINDING | NO-FINDING | INCONCLUSIVE
COVERAGE: complete | partial
REVIEW: <designated route, specific grounds, status and decision reference>
```

Apply the authorized re-audit selection rules to attestations. Evaluate judicial work through substantiated reversals, escaped regressions, reproducibility, unsupported obstruction, and correction quality together. Finding count, refusal rate, and approval rate are not success targets. Record only evidence actually obtained; this procedure's author cannot approve its own amendment.
