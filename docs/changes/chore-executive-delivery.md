TYPE: chore
WHY: Give the executor clear responsibility for authorized delivery and continuity instead of treating a blocking record or delegation as completion, because work otherwise can stop without a truthful result or an accepted handoff.
SEARCHED: rg --files --hidden -g '*execut*' -g '*implement*' -g '*delivery*' -g '*行政*' -g 'SKILL.md' -g 'AGENTS.md' -g '!**/.git/**' → administrative entry docs/implementing.md | REUSED: docs/implementing.md | no new module, helper, wrapper, or dependency.
TESTS: git diff --cached --check -- docs/implementing.md docs/changes/chore-executive-delivery.md; git diff --cached --name-only; text and scope checks only, not a gate or independent acceptance.

# Executive delivery procedure

## Authority and scope

The task owner requested changes only to the executive branch and prohibited reading or auditing the other two branches. This change starts at 6bf527f on chore/executive-delivery. Earlier legislative and judicial commits are ancestors, not modifications authored in this change.

The only existing project document read for this task was docs/implementing.md. Git metadata and file paths were inspected to locate the administrative entry, confirm the baseline and checkout, and limit the change. No legislative text, judicial procedure, audit report, verifier source, implementation source, existing test, or shared change template was read.

Only docs/implementing.md and this change record are modified. This remains executive operating advice. It creates no policy exception, binding acceptance criterion, new mandatory record format, approval step, or authority to merge, publish, or judge one's own work.

## Resulting execution guidance

- Carry forward existing authorization, including delegated decisions, and update future work when the user changes it. Routine authorized work does not require repeated permission.
- Keep one owner for dependencies, integration, and closure. Bound delegated work and shared writes; confirm responsibility transfers rather than treating a sent message as acceptance.
- Distinguish implementation choices, expressly delegated behavior choices, and decisions outside the mandate. READ records a choice or ambiguity; it does not authorize one.
- Classify failures by their actual effect and dependencies. Continue independent authorized work, use finite justified retries, and resolve uncertain side effects before repeating an operation.
- Preserve blocking records through an authorized persistence and routing path. Saving a record neither authorizes a merge into main nor completes the original task.
- Report planned, attempted, observed, verified, and pending work accurately without replacing the binding task-end states. Associate evidence with the actual deliverable and preserve failures and limitations.
- Make handoff acceptance, next responsibility, and recovery conditions explicit. Evaluate workflow quality without penalizing legitimate blocking or rewarding apparent activity.

Eight hypothetical scenarios illustrate these distinctions. They are operating examples, not executable tests, measured outcomes, or findings about the current implementation.

## Concrete wording corrected

The earlier administrative document advised declining rules without an evidence basis, landing blocked records on main, treated delegated choices and undelegated specification gaps alike, and described the executor as having no continuing responsibility. This revision removes those permissions or implications from the administrative advice. It does not adjudicate the validity of any rule, prior decision, or historical experiment.

The blanket claim that every recommendation had been measured is replaced with a clear distinction between design guidance and experimental evidence. The Federalist references were already consulted during the preceding conceptual discussion; no external source or historical audit was fetched for this modification task.

## Verification and handoff

Verification in this task is limited to the administrative text, its hypothetical cases, local references and formatting, and the exact changed-file scope. Drafting assistance is limited to this administrative document and conceptual scenarios; it is not a formal audit or independent acceptance.

The task owner's separation instruction excludes whole-repository checks that would read or execute the other branches. No gate PASS, merge eligibility, independent approval, or empirical improvement is claimed. Any required independent acceptance remains with an appropriately authorized role. This change does not merge itself into main or make new binding law.

## Checks completed

Text checks confirmed final newlines, absence of trailing whitespace, balanced Markdown code fences, seven procedure sections, eight hypothetical scenarios, and a matching chore record. Changed-path inspection found only the administrative guide and this record. A second drafting agent read only the administrative guide and found no remaining required wording correction; this was document collaboration, not independent acceptance.

Git hook metadata was inspected without reading hook contents; no executable commit hooks were present. No hook or check was disabled. No full gate, selftest, or implementation test was run.
