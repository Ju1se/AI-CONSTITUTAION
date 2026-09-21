# Change record — chore/readme

TYPE: chore
WHY: state what the repository is, what it measured and what is still broken in one place, because a
visitor currently opens AGENTS.md and a directory of audits with no way to tell which is the artefact and
which is the evidence against it.

TESTS: none — documentation only. The gate run on this branch is the evidence that a docs-only change is a
complete change.

HANDOFF: the README's "Known unfixed defects" and "Branches" sections are the parts that rot. They name
four live defects and three unmerged proposals; if any is repaired or enacted, that section is wrong and
nothing checks it.
