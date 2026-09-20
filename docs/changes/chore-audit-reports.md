# Change record — chore/audit-reports

TYPE: chore
WHY: keep the two review records in the repository rather than outside it, because the v0.4 policy change
cites both as its justification and a claim whose evidence is not in the tree is the failure the reviews
were about.

## Scope

- `docs/audits/agents-kit-v0.3-review.md` — the independent review of v0.3. 66 findings, 44 reproduced
  from scratch by instances that had not seen the reasoning behind them, none refuted. It is what
  `docs/changes/policy-v04-evidence-tree.md` cites finding by finding.
- `docs/audits/separation-of-powers-experiment.md` — three arms on identical tasks (no policy, written
  policy with no enforcement, enforced separation), two runs each. Measures what the mechanism adds over
  the text, and what it does not.
- `.gitignore` — the caches the toolchain writes.
- `agents-kit.zip` removed: the v0.2 source archive, superseded twice. Recoverable from history at 996a184.

TESTS: this change adds no code; `python -m pytest -q scripts/tests` was green (130 passed) at the policy
commit this one builds on, and is unaffected by documentation.
