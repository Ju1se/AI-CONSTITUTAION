# Change record — copy to docs/changes/<type>-<slug>.md, fill in as you go, and COMMIT it with the change (an uncommitted record is not evidence)

TYPE: <feature|fix|refactor|test|chore|renew|policy>
WHY: <decision> instead of <alternative>, because <one clause>.
SEARCHED: rg -n "<concept>" src/ → <N hits: path:line ...> | REUSED: <path> | NONE-FITS: <one line per hit>
DEP: <name>==<version> lookup:pip index versions <name> published:<YYYY-MM-DD> | REASON: <one line> | INSTEAD-OF: <stdlib or existing dep rejected>
TESTS: <exact commands run>

# Add only when applicable; a filled template does not constitute authorization.
# BLOCKED <TAG>: <affected scope> / NEED: <smallest decision and responsible authority> / STATE: <commit>
# DISPOSITION: <answer/decision, authority/date, resumed scope or explicit deferral; preserve the filing>
# ACCEPTANCE: <correction|migration; independent approver/date and decision reference; reason; old/new spec and exact cases; effective transition; preserved evidence>
# EXCEPTION: <permitting clause; owner/date and decision reference; exact scope; reason; conditions; effective point; expiry/event>
# For a dependency-age exception also name the exact package/version, alternatives and withdrawal plan.
# EFFECTIVE: <adoption commit or later transition; pending work covered; old decisions preserved>

# Policy amendments: state the protected interest, adjacent allowed/refused cases, compliance burden,
# alternatives and affected clauses. State EFFECTIVE explicitly; do not self-certify approval or enactment.
# REVIEW: <for a trial: scope; review point; benefit and burden measures; fallback>
# Ledger targets and a proposed allowance/bank are advisory; no grant creates spendable rights yet.
#
# READ: the spec did not say <X>; I read it as <Y>; the other reading was <Z>; granted-by:<task owner|none>
#   Use this, and not WHY, when the task delegated a decision to you or left one open, and your answer
#   becomes a rule the repository lives under afterwards — what counts as a valid input, what a caller
#   must handle, what an interface promises. WHY explains a choice inside the spec; READ records that you
#   supplied part of the spec. Nothing in the gate reads this line yet (see the POLICY-GAP in
#   docs/changes/chore-executive-craft.md); write it because the reviewer who has to live with the rule
#   cannot otherwise tell it apart from an ordinary design decision.
#
# HANDOFF: <what you did not verify> | <what you assumed> | <where to look first if this breaks>
#   You will not see this change again. This line is for whoever does.
