# Change record — copy to docs/changes/<type>-<slug>.md, fill in as you go, and COMMIT it with the change (an uncommitted record is not evidence)

TYPE: <feature|fix|refactor|test|chore|renew|policy>
WHY: <decision> instead of <alternative>, because <one clause>.
SEARCHED: rg -n "<concept>" src/ → <N hits: path:line ...> | REUSED: <path> | NONE-FITS: <one line per hit>
DEP: <name>==<version> lookup:pip index versions <name> published:<YYYY-MM-DD> | REASON: <one line> | INSTEAD-OF: <stdlib or existing dep rejected>
TESTS: <exact commands run>

# Optional lines
# ALLOWANCE: <n> granted-by:<task owner>        (always audited)
# BLOCKED <TAG>: ... / NEED: ... / STATE: ...    (paste the filing here when the task ends BLOCKED)
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
