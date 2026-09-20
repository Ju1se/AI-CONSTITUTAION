# Legislative amendment — authority, effect and lawful revision

TYPE: policy
WHY: define revision authority and prospective effect instead of making existing acceptance or uncalibrated targets absolute, because legitimate correction needs a bounded path that preserves evidence and independent decisions.
TESTS: NOT_RUN — make test, make selftest and make gate were not invoked; the task owner confined this task to legislation and prohibited reading or auditing the other powers.
EFFECTIVE: After independent approval and adoption on main, for subsequently started changes. Pending work adopts these rules only by an explicit owner decision identifying its scope and a new assessment; previous rule versions and outcomes remain intact. This record grants no individual acceptance revision, dependency exception or merge approval.

## Authority and scope

The task owner requested improvements to the legislative specification only. The work is confined to AGENTS.md, the legislative portions of docs/agents-policy.md, comments in policy.mk, the change-record template and this record. The existing parameter assignments and required-check lists are unchanged. No implementation, test, CI, hook, audit procedure or audit result was read or assessed for this change.

Sections 4 and 7 onward of the companion document are retained as prior-version material. The new introduction distinguishes them from the revised legislation; retaining them is not a new claim of implementation coverage. Their independent reassessment is outside this task.

The working branch started from 3c11f0b. During drafting, an external commit advanced main to f9c70cc. This change is based on that updated main and preserves its additions to the shared template. No content from the other role's new procedure was inspected.

## Protected interests and changes

- **Authority and truthful evidence:** distinguish task instructions, interpretation, authorized exceptions and amendments. Amendments have an effective point and pending-work scope. New decisions never erase or relabel old outcomes.
- **Legitimate acceptance:** replace unilateral absolute freezing with a prohibition on unauthorized revision. Correction against an existing specification and migration to a new specification require distinct reasons and an owner-designated approver other than the implementer or proposer. Preserve old cases and outcomes; retain every obligation not expressly superseded.
- **Completion and relief:** require substantive specification and binding duties as well as required PASS outcomes. BLOCKED pauses dependent work, preserves independent authorized work, and places a response/disposition duty on the owner. Silence supplies no approval.
- **Proportional restrictions:** keep ledger and mutation targets advisory; tool availability does not activate a rule. Require an explicit activation amendment and benefit-versus-burden evidence. No unrelated deletion is demanded to satisfy an advisory target.
- **Safe retirement:** consider internal and external contracts before deletion. Permit a recorded stable responsibility and a tag-specific, limited grace when safe retirement cannot yet be established.
- **Bounded exceptions:** a dependency-age exception names the exact package/version/change and expiry, while preserving existence and record duties. Any required mechanism refusal still awaits separate resolution.
- **Legislative restraint:** amendments state affected clauses, neighboring allowed/refused cases, alternatives, compliance burden and effect. Trials state review and fallback. Summaries reference operative rules rather than creating conflicting exceptions.

## Normative examples — proposed application, not executed tests

| Topic | Allowed case | Refused case |
|---|---|---|
| Acceptance | An authorized specification changes output 900 to 899; an independent approval identifies the exact cases and transition, retaining the earlier evidence. | The specification still requires 900; the implementer changes the assertion to 899 solely to pass. |
| BLOCKED | A missing decision pauses dependent subtask A; unrelated authorized work B and C continues. | Silence is treated as permission to choose A's acceptance standard. |
| Ledger | Net +3 is honestly recorded as an observation; applicable obligations still govern. | Unrelated deletion is demanded solely to satisfy the currently advisory +2 target. |
| Dependency age | Prior written approval covers one necessary young version, named change, conditions and expiry; existence evidence is retained. | A general delivery request is taken as permission to waive age or package verification. |
| Sunset | An external contract prevents retirement despite green local tests; document the obligation and seek the applicable disposition. | Green local tests are treated as proof that the external contract ended. |
| Effect | A newly effective rule supports a fresh decision on a named submission; its earlier failure stays recorded. | An old failure is deleted or renamed PASS after the rule changes. |

## Alternatives and burden

Keeping absolute prohibitions would leave correction and authorized behavior migration without a clear ordinary route. Unrestricted owner or implementer waivers would let case pressure redefine acceptance. The chosen path requires additional fields only for an acceptance revision, exception, amendment or trial; routine changes keep their ordinary record. BLOCKED itself needs no permission or failed-code demonstration.

The additional decision cost is deliberate where the author would otherwise change their own standard. The legislation does not assume that different instances have different incentives, or that branch names confer independent authority. Legislative authors do not approve this amendment's compliance or merge eligibility.

## Text checks and handoff

Only ordinary drafting checks apply in this task: whitespace, document size, authorized paths, unchanged parameter assignments, preservation of external template additions and unchanged out-of-scope companion sections. These are not gate results or an independent audit.

Drafting checks completed: `git diff --check` passed; inline `python3 -B -` text assertions confirmed five legislative paths, AGENTS.md at 115 lines / 13,971 bytes, unchanged policy assignments, unchanged companion §4 and §7 onward, balanced Markdown fences, and preservation of all 11 externally added template lines. No Git hook was executed and no merge decision was requested.

The legislative work is complete for handoff. Enactment and any reconciliation with independently maintained mechanisms remain separate decisions. Preserve any refusal under the prior rules; this amendment is not permission to disable a check or claim an unperformed check passed.
