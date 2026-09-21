TYPE: policy
WHY: Make judicial decisions depend on applicable obligations and reviewable evidence instead of failure-seeking incentives, because unsupported refusals and unbounded re-audits can expand judicial power.
SEARCHED: rg --files --hidden -g '*audit*' -g '*judic*' -g '*judg*' -g '*appeal*' -g '*司法*' -g 'AGENTS.md' -g 'SKILL.md' -g '!**/.git/**' → judicial entry .claude/skills/audit/SKILL.md | REUSED: .claude/skills/audit/SKILL.md | no module, helper, wrapper, or dependency added.
TESTS: git diff --cached --check -- .claude/skills/audit/SKILL.md .claude/skills/audit/references/adjudication-cases.md docs/changes/policy-judicial-process.md; git diff --cached --name-only; text and scope checks only, not a gate or independent acceptance.

# Judicial process amendment

## Scope and authority

The task owner explicitly requested changes to the judicial branch and prohibited reading or auditing the other two branches. This change starts at bf81be0 on policy/judicial-process. The preceding legislative commit is a parent, not part of this change's authored modifications.

Existing project content read for this task is limited to the judicial skill and docs/audits/README.md. Git metadata and path names were used to locate the judicial entry and preserve the existing checkout. No legislative document, implementation, verifier source, existing test, or historical audit finding was read or adjudicated.

Modified artifacts are the protected judicial skill, its new hypothetical adjudication examples, and this permitted change record. The examples describe expected judicial reasoning and are not executable tests or claims of observed repository behavior.

## Resulting judicial behavior

- Fix subject, base, applicable rules, questions, access, mandate, and evidence before judging; respect role-specific access exclusions.
- Require an applicable obligation and supported causal reasoning for a finding. A failed check, missing tool, or difficulty reconstructing rationale does not automatically establish a substantive violation.
- Preserve at least three distinct attack paths and applicable minimum coverage for attestations; do not equate an attestation with merge authorization.
- Record all check statuses and their provenance. Preserve required non-PASS holds without converting missing evidence into a proved defect.
- Give material responses an authorized hearing and explain their disposition. State the narrow remedy and its sufficient resolution condition.
- Require recusal, designated independent review, reasoned reopening, bounded precedent, and preservation of prior evidence and decisions.

## Interests and neighboring cases

Protected interests: reliable acceptance, independent judgment, predictable obligations, a fair response, proportionate correction, and finite review.

Allowed: declining approval for absent required evidence while recording an inconclusive question; issuing a proved finding alongside a separate coverage limit; withdrawing a rebutted allegation; reopening on material unreliable evidence.

Refused: fabricating a failure to finish an audit; treating ERROR as proof of implementation fault; imposing a preferred timeout absent an applicable rule; treating a narrow remedy as permission to bypass a whole-change gate; repeatedly replacing reviewers to obtain a desired answer.

The companion examples include these distinctions and the conflict between historical and current rule versions. They are design examples, not formal audit results.

## Costs and alternatives

The procedure adds a fixed case record, explanation of adverse decisions, and an independent review route. Small undisputed cases may use concise entries; repeat the issue block only for actual questions. Invest additional investigation only where relevant evidence justifies it.

A check-only verdict would omit rule applicability and process errors. Unrestricted repeated audits would increase cost and make finality unreliable. No new tool, dependency, automatic task creator, implementation path, or permission is introduced.

## Effect and handoff

This judicial amendment requires independent acceptance and adoption through the applicable policy process. Its author and the agents assisting its drafting do not approve it. Adoption may apply it prospectively; applying it to an existing case requires the authorized transition decision, a recorded ruleset, and preservation of the earlier decision.

Verification in this task is limited to text, artifact, and diff-scope checks. The task owner's separation instruction excludes a whole-repository gate and the other branches' sources. No PASS, merge eligibility, independent audit, or retroactive effect is claimed. An appropriately authorized independent role must perform any required acceptance outside this task's restricted scope.

## Verification performed

Text checks confirmed the skill header, balanced Markdown code fences, existing local reference, final newlines, and absence of trailing whitespace. Scope checks confirmed exactly the three authored artifacts and ten hypothetical example sections. A second drafting agent checked only the two judicial texts for consistency; its response-opportunity correction was incorporated. This was drafting assistance, not an independent judicial acceptance.

Git hook metadata was inspected without reading hook contents; no executable commit hooks were present. No hook or check was disabled. No full gate, selftest, or implementation test was run.
