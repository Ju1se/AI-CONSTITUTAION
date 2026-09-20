# Change record — chore/executive-craft

TYPE: chore
WHY: give the executive a written procedure of its own and two record lines for the discretion it
actually exercises, instead of proposing amendments to `AGENTS.md`, because the executive may not
legislate and the gaps that need legislation are filed below rather than drafted.

TESTS: none — this change adds no code. `DEPS_OFFLINE=1 make gate` on this branch is the evidence that a
docs-only change is a complete change.

READ: the constitution does not say who owns the record form. `docs/changes/_TEMPLATE.md` is outside the
protected set and `docs/changes/` is allowed in every change type, so I read that as the executive being
free to change the form it fills. The other reading is that a form every future change must use is
legislative surface and belongs in the protected set. I took the first reading because it is what the
text says, and filed the second as a gap below. granted-by:none

HANDOFF: I did not give either new line any force — the gate does not read `READ:` or `HANDOFF:`, so both
are conventions until a policy change makes them otherwise. I assumed the next implementer finds
`docs/implementing.md`, which is an assumption with nothing behind it (gap 4). If the lines go unfilled,
look first at whether anything ever told an implementer they exist.

## Scope

- `docs/changes/_TEMPLATE.md` — two optional lines. `READ:` for a decision the task delegated or left
  open, whose answer becomes a rule the repository lives under. `HANDOFF:` for the instance that will see
  this change again, since the author will not.
- `docs/implementing.md` — the executive's operating procedure. The judiciary has one
  (`.claude/skills/audit/SKILL.md`); the executive had only the law it is judged by. Six disciplines,
  each traced to a measured outcome in `docs/audits/separation-of-powers-experiment.md`, not to a
  preference.

Nothing in the protected set is touched, no rule is added, and neither new line is enforced. This is the
whole of what the executive can do here by itself.

The first attempt at this change did touch the protected set: `git add -A` swept an uncommitted rewrite of
`AGENTS.md`, authored by the task owner and sitting in the working tree, into the commit. The gate refused
it — `type FAIL`, `protected_files FAIL`, naming the file — and the commit was backed out with that file
left exactly as it was found. An executive committing a constitutional amendment as a routine chore, by
accident, is the failure this separation exists to catch, and it was caught by the branch whose job that
is rather than by the branch that made the mistake. Recorded here because the record is the only place a
near miss survives.

## POLICY-GAP: four things this layer cannot fix from inside

Filed under §2's terms — the compliant path is more expensive than the workaround, so the gap is named
rather than routed around. Each needs a `policy/` change, which is not the executive's to make.

**1. `READ:` has no force.** The record check does not know the key, and the audit draw does not trigger
on it, so an executive that supplies part of the spec still produces a record formally identical to one
that made an ordinary design choice. The audit report's §4 shows what that costs: four runs answered the
same delegated question well, and one of the answers put a credential in every log line. `ALLOWANCE:` is
the precedent — a grant from the owner that lands the change in the 100% audit set. A rule the executive
supplied has at least as strong a claim to the same treatment, and arguably to a sunset as well, since it
was never ratified by anyone.

**2. The form every change must use is not protected.** This change altered it on a `chore/` branch, with
no audit and no review, and that was legal. An executive can rewrite the shape of the evidence the
judiciary reads. I do not think it should be able to, and I cannot fix it without legislating.

**3. The executive has no term.** A finding "becomes a `fix/` or `test/` task" that is assigned to nobody,
so nothing connects a defect back to the party that wrote it and nothing recalls that party to fix it. The
`HANDOFF:` line above is a substitute for continuity, not continuity. What would actually close this is
re-invoking the same executive identity when its change is audited or found defective — the executive
returns to repair, while the auditor stays fresh, so the separation is preserved and the horizon is not
one task long.

**4. The executive's procedure is undiscoverable.** `docs/implementing.md` is not referenced from
anything an implementer is given, and making it referenced means editing `AGENTS.md`. So the one artifact
this change produces for the next executive depends, to be read at all, on a branch of government this one
may not touch. That is the no-term problem in another form: the executive can write for its successor but
cannot arrange to be heard by it.
