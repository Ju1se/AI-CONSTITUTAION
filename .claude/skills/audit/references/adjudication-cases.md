# Adjudication examples

These hypothetical cases illustrate the audit procedure. They are not findings about this repository, executable tests, new acceptance criteria, or an independent approval of the procedure. Apply the admitted ruleset if a case differs.

## 1. A required check cannot run

- Evidence: a required tool is absent; the check is `ERROR` or `NOT_RUN`; no independent evidence establishes a violation.
- Decision: `INCONCLUSIVE` for that question. Preserve the technical status, name the missing prerequisite, and withhold any approval that requires the absent evidence.
- Exclude: declaring an implementation defect solely from the missing tool, or approving because no defect was found.

## 2. A response defeats the proposed finding

- Evidence: the auditor alleges a hidden failure. A submitted response identifies the actual call path and a typed failure the caller handles, as required by the admitted rule.
- Decision: verify that evidence and withdraw or narrow the allegation with reasons. Unresolved material facts remain inconclusive. The overall report still requires its own coverage and recheck.
- Exclude: ignoring the response, treating rebuttal as misconduct, or adding a demand to prove that all possible failures are impossible.

## 3. A preference supplies an invented threshold

- Evidence: the applicable rule requires a timeout but specifies no universal duration. The auditor prefers five seconds and proposes refusing every longer timeout on that basis alone.
- Decision: that preference does not establish a violation. Consider a separately applicable contractual duration if one exists; otherwise label the suggestion nonbinding.
- Exclude: imposing the invented duration retrospectively or treating an interpretation question as permission to amend the specification.

## 4. A local defect sits within a whole-change gate

- Evidence: an isolated feature lacks required evidence, and the binding merge rule requires all checks for the change to pass.
- Decision: describe the affected feature and sufficient evidence needed. Preserve the whole-change merge hold required by the rule. Extend corrective work only on demonstrated dependencies.
- Exclude: requiring an unrelated project-wide rewrite or claiming that a narrow remedy authorizes partial merging around the gate.

## 5. The proposed reviewer participated in the work

- Evidence: the reviewer authored the subject or the disputed acceptance revision, or already received the implementer's private reasoning.
- Decision: disclose and recuse from the independent audit. Request assignment through the designated authority. Submitted facts may remain in the case record for an eligible reviewer.
- Exclude: self-certifying independence, self-appointing a replacement with final authority, or inferring a subject defect from the recusal.

## 6. A final decision is challenged repeatedly

- Evidence: ordinary review has ended. The request offers only dissatisfaction; later, a separate submission identifies a falsified artifact material to the outcome.
- Decision: decline the repetitive review absent another applicable authorization. Evaluate the material new evidence through the designated reopening route; preserve the prior decision and explain any new one.
- Exclude: rotating reviewers until a favorable answer appears, or using finality to ignore material evidence without addressing reopening grounds.

## 7. One defect is proved while another check is unavailable

- Evidence: an admitted rule and verified record establish an unauthorized change; a separate required check cannot run.
- Decision: after the response process, record the supported `FINDING`, the unavailable check, and partial coverage. Do not certify the remainder or relabel the check.
- Exclude: erasing a proved finding because another issue is inconclusive, or describing the mixed report as a complete attestation.

## 8. The historical and current rules differ

- Evidence: the original case used rule version A; an available recheck uses version B. The existing interface cannot reproduce A.
- Decision: the intended original-rules recheck is inconclusive. If a B assessment is independently authorized, label it separately and retain both versions and outcomes.
- Exclude: declaring the historical judgment erroneous solely because B yields another result, modifying the verifier to force the desired outcome, or overwriting the original evidence.

## 9. The auditor cannot explain the design

- Evidence: the auditor cannot infer a rejected alternative, but the record satisfies the applicable explanation obligation and no contradiction is established.
- Decision: do not issue `OWNERSHIP-LOSS` solely for that uncertainty. Seek a submitted clarification if material; otherwise record a nonbinding observation and judge the actual obligations.
- Exclude: making the auditor's understanding or preferred architecture an unannounced acceptance condition.

## 10. The response period is unspecified

- Evidence: an adverse allegation is disputed and the mandate supplies neither a response process nor a closing condition.
- Decision: preserve the provisional evidence, request the missing procedural decision through the designated route, and keep the disputed issue inconclusive until it can be adjudicated.
- Exclude: assuming silence means consent, inventing a retrospective deadline, or removing an existing mandatory hold while the issue is pending.
