# Change record — chore/readme-after-prerequisites

TYPE: chore
WHY: state the repaired state instead of the state before the repair, because the README listed four
confirmed defects as unfixed and three of them were closed by the change merged immediately before it,
and a status section that is stale understates nothing — it misreports.

TESTS: NOT_RUN — documentation only; no behaviour changes and no check reads this file.

HANDOFF: the section is now split into what was closed and what remains, and names the two open items
(LM-4, LM-5) plus the class LM-1 leaves open. If a later change closes one of them, this section is the
place that has to move with it.
