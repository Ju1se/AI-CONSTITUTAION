# AI CONSTITUTION

A merge gate and a written policy for repositories whose code is largely written by agents. The premise is
not that a better prompt produces a more careful agent. It is that an agent takes the shortest path to
whatever counts as "done", so "done" has to be a verdict the agent cannot issue about itself.

There is no application here. The kit is the project: a constitution, a verifier that enforces part of it,
the verifier's own counterexample corpus, and the audits that found what both of them got wrong.

## What it does

A change is a branch, a commit series, and one change record. `make gate` judges that change and writes
`.gate/result.json`. A merge needs `merge_eligible: true`, which means every required check returned PASS.

Four outcomes, and only one of them authorises anything:

| | meaning |
|---|---|
| PASS | the check ran and found nothing, within the scope its own summary states |
| FAIL | a refusal under the policy; the safe path is named in the output |
| ERROR | the check could not be evaluated — a bad base, a missing tool, a crash |
| NOT_RUN | the check exists on paper only, or was skipped explicitly |

Three things are kept apart, and a fourth was added after the second audit found it was not:

- the **candidate** — a branch and its record
- the **verifier** — `scripts/gate_checks.py`, `policy.mk` and `tests/MOCK_ALLOWLIST`, always loaded from
  `main`, never from the branch being judged
- the **host** that runs it — CI, or a human's `make gate`
- the **evidence tree** — the export the checks run in, and the configuration the tools inside it read

The fourth matters because the candidate writes the tree. It also writes the files that tell git what to
export, pytest what to collect and how to report, and ruff what to lint. v0.3 separated the first three and
left the fourth open; four distinct ways to exploit that were reproduced, and v0.4 closed them by verifying
the export against `git ls-tree`, starting every tool with configuration written outside the export, and
comparing the collected test inventory against the base commit.

## The checks

Fifteen required, four advisory and permanently NOT_RUN. `docs/agents-policy.md` §7.2 gives each one's
guarantee scope, status, and the fixture that demonstrates it.

`type` · `protected_files` · `export_integrity` · `harness_integrity` · `unit_tests` · `test_inventory` ·
`red_before_green` · `h1` · `mocks` · `masking_markers` · `masking_ruff` · `sunset` · `records` · `deps` ·
`verifier_selftest`

The one that matters most is `h1`: a committed test may not be modified, deleted, or made to stop being
collected. Not because implementers are usually wrong, but because they cannot tell from inside which case
they are in — see the experiment below.

## Using it

```bash
make gate                    # the merge decision, verifier and policy loaded from main
make check-tests             # one group, working copy's verifier, fast feedback only
make selftest                # the verifier's own corpus
```

Requires `git`, `pytest` and `ruff` on `PATH`. Python manifests only. A gate run costs one full suite run
plus two collections plus the change's new tests; on a small suite that is a few seconds of fixed overhead,
on a large one it approaches the suite's own cost.

**Adoption is not incremental.** Two checks are whole-tree rather than diff-scoped: `masking_ruff` lints the
whole source tree at the subject, and `sunset` scans every tag. On a repository with ordinary existing debt,
a completely compliant documentation change is refused on day one for reasons that have nothing to do with
it. Sweep the tree before enabling enforcement, the way you would when turning on a new linter.

## Status, stated honestly

This has been audited twice by instances that did not write it and could not see the reasoning behind it.

- **[v0.3 review](docs/audits/agents-kit-v0.3-review.md)** — 66 findings, 44 reproduced from scratch, none
  refuted. It produced v0.4.
- **[the three-arm experiment](docs/audits/separation-of-powers-experiment.md)** — the same five tasks under
  no policy, written policy with no enforcement, and enforced separation, two runs each.
- **[audit of the two proposed amendments](docs/audits/policy-legislative-and-judicial.md)** — no finding
  against either amendment; three confirmed findings against the machinery they would govern.

What the experiment actually measured, with two runs agreeing in each direction:

- Without any policy, a capable agent rewrote four committed tests and argued well for doing so, and left
  expired debt in place. With a policy — enforced or merely written — neither happened.
- Written policy with no enforcement was enough to produce the correct refusal and a well-drafted BLOCKED
  filing. It was not enough to make that filing durable: both runs left it on a branch they never merged.
  The mechanism's measured contribution over the text was institutional memory, not restraint.
- Every change the gate passed in the enforced arm was then attacked by two independent auditors, who found
  seven substantive defects including an exception message that echoed a credential into every log line.
  The gate checks form; an auditor checks substance; neither substitutes for the other.

Two rules have a measured behavioural effect: `h1` and `sunset`. The rest are uncalibrated in both
directions, and no false-block rate has ever been measured on real work.

### What the third audit found, and what happened to it

The audit of the two amendments raised twenty findings against the machinery. Four were confirmed by
independent reproduction with controls, and all four are now closed:

- `run_in` strips the run's own identity — `SUBJECT`, `BASE`, `BRANCH`, `POLICY_REF`, `GATE_OUT` and the
  rest — from every process the gate spawns, so a nested gate must be told what to judge. Following the
  audit procedure's recheck command no longer fabricates a `verifier_selftest` failure on policy changes.
- `TYPE: test` no longer disables the frozen-test rule. The exemption is conditional on an `ACCEPTANCE:`
  line, and such a change lands in the 100% audit set.
- A placeholder is an angle-bracket token, not any `<`, so a truthful `WHY:` carrying a bound such as
  `n <= 3` is accepted.
- `harness_integrity` refuses any pytest hook in a conftest, plus the marker and outcome forms the
  reproduced autouse attack used.

Two remain open and are stated as such:

- **LM-1 is closed for the form reproduced, not for the class.** The gate runs code the candidate wrote;
  a conftest or an imported module can still reach the verdict by a route no pattern anticipates. Closing
  the class needs the acceptance that judges a change to come from the trusted ref.
- **LM-4** — harness policy outside `PROTECTED_PATHS` (`pyproject.toml` sections, a root `conftest.py`) is
  refused on every branch type, each check's safe path naming the route the other closes.
- **LM-5** — every "independent approval" clause is honour-based. The gate can read that a decision was
  recorded; it cannot read that the approver was independent.

`docs/agents-policy.md` §7.5 and §7.6 state what the gate does not claim, including the residue that no
arrangement of checks removes: the gate runs code the candidate wrote.

## Branches

`main` is the enacted state. Three branches carry proposals that are **deliberately unmerged**:

| branch | what it proposes |
|---|---|
| `policy/legislative-rules` | rewrites the constitution: amendment effect, a lawful route for revising a frozen acceptance, proportionate restrictions |
| `policy/judicial-process` | rewrites the audit procedure: jurisdiction, evidence, bounded remedies, independent review |
| `chore/executive-delivery` | executive-side changes, stacked on both of the above |

They are unmerged because their own records say they must be. The legislative record's effective clause
reads "After independent approval and adoption on main"; the judicial record says the amendment "requires
independent acceptance … Its author and the agents assisting its drafting do not approve it." No such
approval has been recorded.

The other blocker is now gone. Until the change above, merging them would have enacted a constitution
whose central new safeguard the machinery did not implement: the new §3 requires a designated approver
before a frozen acceptance may be revised, and the verifier did not parse the field that would record
one. It now parses all five new fields and enforces the condition. What it still cannot check is whether
the approver was independent, which is LM-5 above — so adoption remains a human decision, not a gate
verdict.

`chore/executive-delivery` additionally cannot pass the gate as it stands, because it sits on top of both
policy branches and its diff against `main` therefore contains them. It needs rebasing onto `main` first.

## What is missing

The system can refuse a change. It cannot yet learn that a rule is wrong.

Every verdict is written into `.gate/`, which is ignored by `*`. Nothing records what a rule refused, how
often, or what happened to the change afterwards — abandoned, fixed, or merged anyway by a human who
disagreed. `REAUDIT_RATE`, `ATTEST_MIN_PATHS` and `AUDITOR_OVERTURN_MAX` are declared in `policy.mk` and
read by no code. A `POLICY-GAP` filing triggers an audit draw and nothing else.

So the correction loop — operate, observe, detect a rule that is wrong or too costly, propose, judge
independently, authorise, observe again, roll back if worse — is open at observation, at independent
judgment of soundness, and at after-effect. The first of those is the precondition for the other two, and
it is not a check. It is a record.

## Licence

MIT. See [LICENSE](LICENSE).
