# Agents policy — design, rationale, enforcement

Status: v0.2 · 2026-09-19 · companion to `/AGENTS.md`.

This document is for humans and for the E-series evaluation. Agents never load it; the operative file is `AGENTS.md` (132 lines, 10.9 KB). Everything here explains, justifies, parameterizes or enforces a line in that file. If a sentence here would change an agent's behavior, it belongs in `AGENTS.md`; if a sentence in `AGENTS.md` only explains, it belongs here.

Contents: 1 Principle · 2 Assumptions · 3 Clauses §1–§7 · 4 Checks on the checkers · 5 Metrics and baselines · 6 Parameters · 7 Enforcement · 8 Loading and verification per tool · 9 Maintenance

---

## 1. Principle

The rules assume the knave: an agent takes the shortest path to whatever counts as done. They do not ask it not to. They move "done" so that the shortest path runs through the behavior the repository needs. Each clause therefore has four parts:

- **RULE** — what is binding (in `AGENTS.md`).
- **CHEAPEST PATH** — the least-effort legal route, and why the evasion costs more (one "Safe path" line in `AGENTS.md`; the full argument is here).
- **CHECK** — the mechanical gate that refuses completion without it (a hook or a `make` target; specified here, implemented in `Makefile`, `scripts/`, `.claude/`).
- **METRIC** — what is measured afterward (here).

Two facts shape the split between the files. First, both vendors state that instruction files are context, not enforcement: Claude Code says to use a `PreToolUse` hook to block an action regardless of what the model decides, and Codex's review-rule guidance leaves formatting and lint checks to CI. A rule that exists only as prose is the condition the task-resolution null result measured. Second, both vendors cap what an agent will absorb: Claude Code targets under 200 lines per file and reports reduced adherence beyond it; Codex concatenates the global, root and nested `AGENTS.md` files and stops adding at 32 KiB by default. The root file is kept under 150 lines and 12 KB for that reason.

The two-price problem the policy addresses: generation cost fell to zero and removal cost did not move. The creation price cannot be restored, so the mechanisms make removal free (§5 sunset; deletion needs no record and no audit) and couple the two prices (§4 PAYGO; new complexity must be offset). Stigmergy works the same way — trails decay for free unless re-walked.

## 2. Assumptions

- One change = one branch, merged as one unit (PR). The change **type is the branch prefix**: `feature/`, `fix/`, `refactor/`, `test/`, `chore/`, `renew/`, `policy/`. Every tool can read it without parsing prose.
- The change record lives at `docs/changes/<type>-<slug>.md` (slug = branch name after the prefix). It is the "legislative record": the artifact a fresh reviewer reconstructs the design from.
- Source under `src/`, tests under `tests/`. Python tooling is assumed in the shipped `Makefile` (`pytest`, `ruff`, PyPI); the targets are the contract, the recipes are the adapter.
- The default branch is `main` (override with `MAIN=` in `policy.mk`).

## 3. Clauses

### §1 Definition of done — single-subject rule

*Analog: the single-subject rule in state constitutions, which stops riders.* Here it stops a test edit from riding inside a feature, or a threshold change inside a fix.

CHEAPEST PATH. The six conditions of DONE are ordered so that doing them in sequence is the least total effort: pick the branch type first (it fixes what you may touch), write the test before the code (§3 makes this the cheap route), write each record line at the moment of the decision instead of reconstructing it at the end. "Then stop" is the anti-scope-creep lever: unrequested work is a debit.

CHECK (`make check-type`). Branch prefix ∈ the seven types; diff path set ⊆ the type's allowed set; `renew/` diffs contain only `SUNSET` lines; `policy/` touches only the policy set.

METRIC. Share of changes refused by the type gate; should fall toward zero as splitting becomes cheaper than being refused.

### §2 Terminal states — BLOCKED is the cheapest exit

*Analog: Hirschman's "voice."* A system in which dissent is cheaper than corruption gets dissent instead of corruption.

CHEAPEST PATH. Three lines. No code, no test, no review, no penalty, the task ends cleanly. A masked error costs the handler, a test written around it, a `masks` sunset tag whose expiry the agent will meet again, a `WHY:` line, and a guaranteed audit (every `masks` tag is in the 100% audit set). On every axis BLOCKED is cheaper. The one thing BLOCKED does not do is make the task disappear — the task owner answers `NEED` and the task returns. That round trip is the guard against frivolous filing: a `NEED` the task already answered comes straight back with the same work still to do, so BLOCKED saves effort only when the need is real.

Why the denylist is a list of constructs, not a principle: agents optimize against whatever evaluator exists, and a construct list is what a linter can refuse.

CHECK (`make check-masking`). Ruff rules on `src/` (E722 bare except, BLE001 blind except without re-raise, S110/S112 try-except-pass/continue, S113 request without timeout) plus a diff scan of added lines for suppression markers, skip/xfail decorators, and a catch-all followed by `pass`/`continue`/`return`, all refused unless the line carries a `SUNSET` tag. The sanctioned stopgap is therefore exactly one shape — `# noqa: BLE001` paired with a `masks` tag on the same line — which prices it and puts it in the 100% audit set. BLOCKED records are validated by grammar only.

METRIC. Error-masking constructs per 1,000 changed lines (reference: +47% in AI-era commits, GitClear 2026). BLOCKED filings per task by TAG. Share of BLOCKED whose `NEED` was already answered in the task — a measure of spec quality, never a sanction.

### §3 Evidence — separation of powers over verification

*Analog: Federalist 51.* The role that writes the code cannot certify it; the role that certifies is not done until it has found something or paid to say it looked.

Definitions. **BLIND** tests are written from the spec before the implementation and committed first; the commit is the registered hash and CI verifies it precedes the implementing commit. **SEPARATE ROLE** tests are written by a different instance given the spec and public interface, not the diff. **H1** is stated as "never modify or delete an existing test"; adding new tests is how BLIND works, so it is allowed on `feature/`/`fix/` branches — the H1 hook only requires that the test commit precede the `src/` edit.

CHEAPEST PATH. Test-first from the spec, commit, implement until green. That single motion satisfies BLIND, red-before-green and H1, with no second agent and no waiting; every other route (implement first, hand tests to a separate role, prove red-before-green retroactively) costs more. A spec too vague to test from is `BLOCKED SPEC-AMBIGUOUS`, not a reason to reach for a mock. A test that looks wrong is `BLOCKED TEST-DEFECT` — three lines against an H1 refusal plus rework.

Why the mock allowlist is a file and not a principle: "mock only I/O boundaries" is a judgment; a prefix list is a check. The file is policy-protected (H5) so the allowlist cannot be widened inside a feature change.

CHECK (`make check-tests` + hook). (a) H1: on `feature/`/`fix/`/`refactor/` branches, `git diff --diff-filter=MD` under `tests/` is empty; on `refactor/`, `tests/` is untouched. (b) Hook: refuse `src/` edits while `tests/` has uncommitted changes; refuse edits to tracked test files off a `test/` branch. (c) Red-before-green: run the change's new tests against the parent commit; at least one must fail (`feature`/`fix` only). (d) Mock targets ⊆ `tests/MOCK_ALLOWLIST` prefixes. (e) Mutation score on touched lines ≥ `MUTATION_MIN`.

METRIC. Test-modification rate in implementer changes (reference: 23% for agent commits vs 13% non-agent, arXiv:2602.00409). Share of changes adding mocks (36% vs 26%, same source). Allowlist violations caught. Mutation score distribution. Red-before-green failures caught — a test that passes on the parent commit tested nothing the change did.

### §4 PAYGO — the complexity ledger

*Analog: pay-as-you-go budget rules.* New spending must be offset. Here new complexity must be offset by deletion, and deleting dead or duplicate code is the cheapest offset there is.

CHEAPEST PATH. Over allowance, the least-effort credit is deleting code with zero references: `make credits` lists candidates sorted by credit, and pointing a duplicate helper's callers at the survivor is one credit for a diff of a few lines — cheaper than a budget appeal (which needs the task owner) and far cheaper than restructuring. Private symbols weigh zero so that the ledger prices public surface, not internal structure; the perverse incentive toward giant functions is thereby avoided.

CHECK (`make check-ledger`). Ledger computed by tooling from the diff, never self-reported. Credits require a zero-reference proof at symbol level plus a green suite. Merge refused over allowance (H3). Allowance grants come from the task spec, are recorded in the change record as `ALLOWANCE: n granted-by:<owner>`, and are in the 100% audit set.

METRIC. Net complexity per change. Share of changes that are `refactor/` or carry net credit (reference: refactoring share −70%, GitClear 2026). Duplicated-block delta (reference: +81%, GitClear 2026). Dependency count trend. Banked-credit balance.

### §5 Sunset — everything temporary has an expiry

*Analog: sunset legislation, and pheromone evaporation.* A trail nobody re-walks disappears for free. Renewal costs; deletion doesn't.

CHEAPEST PATH. Delete: no record, earns credit, never audited. Renew: a separate `renew/` branch, a justification, a guaranteed audit, two renewals max. When an expired tag is met mid-task, deletion is tried first; most expired shims have no callers and `make credits` shows it. If deletion breaks the suite and the repair is outside the task: revert, file `BLOCKED SUNSET-EXPIRED` naming the failing test, append `grace:<today>` to the tag (once), continue. The grace edit is the one tag edit allowed off a `renew/` branch.

Why tree-wide expiry fails every change: an expiry that only fails the owner's change is ignorable; one that fails whoever is working is not. The grace period keeps this from deadlocking unrelated work while forcing a filing.

CHECK (`make check-sunset`). Tag grammar on every tracked file; untagged items of the listed kinds on **added lines** (so pre-existing debt does not block the rollout — file it under a `chore/` sweep); tree-wide expiry scan honoring `grace:`; renewals counted per tag (see enforcement status).

METRIC. Live tags (count, median age). Resolutions by path (delete / renew / promote / defer). Renewals per tag. Introduced-issue survival to the latest revision (reference: 24.2%, arXiv:2603.28592).

### §6 The record — paperwork that is cheapest to fill honestly

*Analog: the legislative record and freedom-of-information rules.* The form is designed so that the least-effort way to complete it truthfully is to have done the thing.

CHEAPEST PATH. The search is one command and usually finds the helper — reuse is one import instead of a new file and a §4 debit avoided. The dependency record is cheapest to skip by not adding the dependency: for small utilities, stdlib is zero paperwork. The `WHY` line is one sentence; writing it at the moment of decision is cheaper than reconstructing it, and far cheaper than the audit finding when a fresh reviewer cannot. The `SEARCHED` command must be a deterministic repository search (`rg`, `grep`, symbol index), not a model query, so CI can re-run it.

CHECK (`make check-records`). Record file exists and `TYPE:` matches the branch. `WHY:` present on `feature/`/`fix/`. New files under `src/` ⇒ a `SEARCHED:` line; CI re-runs the command on the base commit and compares hit counts. Added lines in a dependency manifest ⇒ a `DEP:` line; CI verifies the package exists at that version on the registry, is ≥ `DEP_MIN_AGE` days old, and is not already present transitively. `NONE-FITS` with N > 0 is in the priority audit set.

METRIC. Duplicated-block delta (shared with §4). New dependencies per 100 changes. Nonexistent-package attempts caught at CI (reference attempt rates: 5.2% commercial / 21.7% open-source models, USENIX Security 2025; 4.62–6.10% frontier, arXiv:2605.17062 — the merged rate is to be zero). Share of `SEARCHED` records with N > 0 ending in `REUSED`.

### §7 Audit — randomness the implementer cannot optimize against

*Analog: random tax audits and independent inspectors, with term limits on the inspectors.* An agent optimizes against whatever evaluator exists; it cannot optimize against one it cannot predict, and an auditor cannot coast if the auditor is audited.

Selection: `AUDIT_RATE` of merged changes drawn with a seed unavailable before merge (merge commit hash + `AUDIT_SALT` kept outside the repository), plus the 100% sets listed in `AGENTS.md`. Auditor: a fresh-context instance given the repository at the merged commit, the diff and the change record — never the implementer's session. Procedure: `.claude/skills/audit/SKILL.md` (RECONSTRUCT → BREAK → RECHECK). Output: a reproducible failing test, or an attestation with ≥ `ATTEST_MIN_PATHS` attack paths and commands. `REAUDIT_RATE` of attestations are re-audited by a second fresh instance; an auditor overturned above `AUDITOR_OVERTURN_MAX` is rotated out.

CHEAPEST PATH (for the auditor). The least-effort valid output is one reproducible failing test on the most obvious weak path. An attestation costs enumerating three tried paths with commands and carries re-audit risk. So the auditor's shortcut is to look hard at the obvious place first, which is what an auditor is for.

METRIC. Finding rate per audited change (should fall) paired with attestation-overturn rate (should stay low) — the pair distinguishes "the code got better" from "the auditors got lazy". RECONSTRUCT pass rate — the operational measure of ownership. Findings by clause, which says which mechanism is leaking.

## 4. Checks on the checkers

*Analog: judicial review and a free press.* Every mechanism creates a predictable shortcut of its own; each is priced.

| Mechanism | Predictable exploit | Guard |
|---|---|---|
| BLOCKED (§2) | file it on everything | round trip, not exit (H2); frivolous `NEED`s are a metric on specs and the work comes back |
| BLIND tests (§3) | commit a trivial test, then "implement" | mutation score on touched lines; red-before-green; BREAK step of the audit |
| Mock allowlist (§3) | add in-repo modules to the allowlist | allowlist is in the H5 policy set: separate `policy/` branch, always audited |
| PAYGO (§4) | delete the wrong thing; split to fake credit; delete tests | zero-reference proof plus green suite; new public symbols debit; tests weigh zero and trip H1 |
| Sunset (§5) | renew by editing the date; defer forever | tag edits only on `renew/` (except one `grace:`); renewals capped; deferrals audited |
| SEARCHED (§6) | paste a fake search | CI re-runs the command on the base commit; hit-count mismatch refuses |
| DEP (§6) | invent a package or version | registry existence, version and age check |
| WHY (§6) | write a vacuous sentence | RECONSTRUCT compares a fresh reading against it |
| Audit (§7) | rubber-stamp | no "LGTM" output exists; attestations cost paths; re-audit and rotation |
| Parameters | edit thresholds inside a feature change | `policy.mk` is in the H5 set; `make check-type` refuses it off a `policy/` branch |

## 5. Metrics and baselines (for E-series evaluation)

Each row is a behavioral dependent variable with a published reference point, so clauses can be ablated one at a time behind pre-registered gates instead of evaluating `AGENTS.md` as a monolith against a task-resolution rate. State every result with its scope — this repository, this task family, this model set, this period — and do not generalize past it. None of the references is causal; several are vendor-sourced (flagged); they indicate direction and magnitude, not targets.

| Metric | Clause | Direction | Published reference | Source and caveat |
|---|---|---|---|---|
| error-masking constructs / 1k changed lines | §2 | ↓ | +47% rise in AI era | GitClear 2026, 623M changes; commercial vendor, longitudinal not causal |
| test-modification rate in implementer changes | §3 | ↓ toward non-agent | 23% agent vs 13% non-agent | arXiv:2602.00409, 1.2M commits |
| share of changes adding mocks | §3 | ↓ | 36% vs 26% | arXiv:2602.00409 |
| mutation score on touched lines | §3 | ↑ | — | repo-local baseline needed |
| refactor share / net-credit changes | §4 | ↑ | refactoring −70% | GitClear 2026 |
| duplicated-block delta | §4, §6 | ↓ | +81% | GitClear 2026 |
| introduced-issue survival to latest revision | §5 | ↓ | 24.2% | arXiv:2603.28592, 304,362 commits, 6,275 repos |
| nonexistent-package attempts merged | §6 | 0 | attempt rates 5.2% / 21.7%; 4.62–6.10% frontier | USENIX Security 2025; arXiv:2605.17062 |
| new dependencies / 100 changes | §6 | ↓ | — | repo-local baseline needed |
| RECONSTRUCT pass rate | §7 | ↑ | — | repo-local; operational definition of ownership |
| finding rate × attestation-overturn rate | §7 | ↓ × low | — | repo-local |
| security-check pass rate on `AUDIT_ALWAYS_PATHS` | §7 | ↑ | ~55% pass | Veracode Spring 2026; benchmark tasks chosen to contain security decisions, not a base rate |
| leaked secrets / hardcoded credentials | H4, §7 | 0 | 14% of projects | Quality Clouds scan of 424 projects; vendor, prevalence not established |

Read pairings, not single rows. Throughput held while stability falls is the pattern DORA 2025 associates with AI adoption; the stability side is the check on whether whatever speed this policy preserves came at the cost it exists to prevent.

## 6. Parameters

Authoritative in `policy.mk` (read by every `make` target). Mirrored as literal numbers in `AGENTS.md` so an agent never has to look one up; a `policy/` change updates both. Starting values, pre-registered; change only on a `policy/` branch (H5).

| Parameter | Value | Used by |
|---|---|---|
| `ALLOWANCE_DEFAULT` | 2 | §4 |
| `BANK_CAP` | 6 | §4 |
| `MUTATION_MIN` | 0.70 | §3 |
| `SUNSET_SHORT` / `SUNSET_LONG` / `SUNSET_MAX` | 30 / 90 / 180 days | §5 |
| `SUNSET_GRACE` | 7 days | §5 |
| `RENEWALS_MAX` | 2 | §5 |
| `DEP_MIN_AGE` | 30 days | §6 |
| `AUDIT_RATE` / `REAUDIT_RATE` | 0.20 / 0.10 | §7 |
| `ATTEST_MIN_PATHS` | 3 | §7 |
| `AUDITOR_OVERTURN_MAX` | 0.20 | §7 |
| `AUDIT_ALWAYS_PATHS` | `src/**/auth* src/**/secret* src/**/subprocess* src/**/net* src/**/sql* src/**/serial*` | §7 — adapt to the layout |

## 7. Enforcement

### 7.1 Shipped mechanisms

| Check | Clause | Mechanism | Status as shipped |
|---|---|---|---|
| branch type ∈ set; diff paths ⊆ allowed set; `renew/` tag-only; `policy/` set only | §1, H5 | `make check-type` | live |
| src/tests separation during editing (H1 hook) | §3, H1 | `.claude/hooks/h1-test-source-separation.sh` via `PreToolUse` | live (Claude Code) |
| no modified/deleted tests on implementation branches (H1 in CI) | §3, H1 | `make check-tests` | live |
| red-before-green on parent commit | §3 | `make check-tests` | text-only |
| mock targets ⊆ allowlist | §3 | `make check-tests` → `scripts/gate_checks.py mocks` | live |
| mutation score on touched lines | §3 | `make check-tests` | text-only (suggest `mutmut`) |
| error-masking constructs | §2 | `make check-masking` (ruff + diff scan) | live |
| ledger from diff; zero-reference credits; allowance | §4, H3 | `make check-ledger` | text-only (suggest `jscpd` or `pylint --enable=duplicate-code`, `vulture`, symbol diff) |
| deletion candidates | §4 | `make credits` | live if `vulture` installed, else text-only |
| sunset grammar; untagged on added lines; tree-wide expiry with grace | §5, H3 | `make check-sunset` → `scripts/gate_checks.py sunset` | live |
| renewals ≤ `RENEWALS_MAX` | §5 | `make check-sunset` | text-only |
| record exists; `TYPE:` matches; `WHY:`; `SEARCHED:`/`DEP:` presence | §6 | `make check-records` → `scripts/gate_checks.py records` | live |
| `SEARCHED` re-run on base commit | §6 | `make check-records` | text-only |
| `DEP` exists at version, age ≥ `DEP_MIN_AGE` (PyPI) | §6 | `make check-records` → `scripts/gate_checks.py deps` | live |
| audit selection with out-of-repo salt | §7 | `make audit-select` → `scripts/gate_checks.py audit-select` | live |
| auditor output grammar; re-audit; rotation | §7 | manual (skill + `docs/audits/`) | text-only |
| no paid / provider / non-registry network runs | H4 | Claude Code `permissions.deny` + sandbox; Codex sandbox; CI without credentials | configure per tool |

"text-only" targets print `TEXT-ONLY` and exit 0 so the rest of the gate keeps running; `make gate` counts them in its summary so the number is visible every run rather than silently passing. Every row that moves to live should be dated here; the mismatch between this table and `AGENTS.md` is the first thing an audit should catch.

### 7.2 The H1 hook

`.claude/settings.json` registers `.claude/hooks/h1-test-source-separation.sh` on `PreToolUse` for `Edit|Write|MultiEdit`. The hook reads the tool input from stdin, derives the branch type, and exits 2 (which blocks the tool call and feeds stderr back to the model) when:

- the target is under `src/` and `tests/` has uncommitted changes — the tests must be committed first, which is the BLIND registration;
- the target is a tracked file under `tests/` and the branch is not `test/` — modifying an existing test is H1;
- the target is under `src/` or `tests/` and the branch is `chore/`, `renew/` or `policy/` — wrong type.

The refusal message states the cheapest path (`git add tests && git commit -m 'test: <what>'`, or `BLOCKED TEST-DEFECT`). Exit code 2 semantics and the settings format follow the Claude Code hooks documentation; verify against the current docs when upgrading.

### 7.3 CI

`make gate` is the merge gate. Run it on every push to a `*/` branch with `BASE` at the merge base of `MAIN`. It needs `git` history (fetch depth 0), `ruff` and `pytest`; network only to the package registry for `deps`. Nothing in CI holds a provider credential (H4).

### 7.4 Codex code review

The `## Code Review Rules` section of `AGENTS.md` follows the format OpenAI documents for Codex's GitHub review (behavior to flag + safe path). If Codex review is enabled on the repository, the five rules apply to every PR without further setup, which gives §2–§6 a second, independent evaluator.

## 8. Loading and verification per tool

Claude Code (v2.1.277+): reads `AGENTS.md` directly only when no `CLAUDE.md` or `CLAUDE.local.md` exists in the working directory or above it; it does not list `AGENTS.md` in `/memory` or `/context` — look for the `AGENTS.md loaded: …` line at session start. If a `CLAUDE.md` is ever added, put `@AGENTS.md` on its first line. Sessions on third-party providers or with telemetry disabled cannot read `AGENTS.md` directly and need that import. Subdirectory `AGENTS.md` files load when Claude reads a file in that directory.

Codex: builds the instruction chain once at start — `~/.codex/AGENTS.md`, then every `AGENTS.md`/`AGENTS.override.md` from the project root down to the current working directory, concatenated root-first, closer files later — and stops adding files at `project_doc_max_bytes` (32 KiB default). The root file is 10.9 KB. Verify with `codex --ask-for-approval never "Summarize the current instructions."` Nested files are read by directory position, not by edited file, so binding rules stay in the root.

Both: explicit user chat prompts override the file. That is why H-conflicts are handled by `BLOCKED H-CONFLICT` and by tooling, not by a precedence claim.

## 9. Maintenance

- Add a line to `AGENTS.md` when a check refuses agents for a reason the file does not state, or when the same correction is typed twice. Remove a line when its check goes live and the text becomes redundant — the file explains refusals; it does not enforce.
- Every `POLICY-GAP` filing is a policy defect: resolve it on a `policy/` branch, and record the gap and the fix here.
- Budget: `AGENTS.md` ≤ 150 lines and ≤ 12 KB. Anything longer moves here or into a skill.
- Review `AGENTS.md`, this document and `policy.mk` together on every `policy/` change; conflicting lines make an agent pick one arbitrarily.
- Codex's `AGENTS.override.md` and Claude Code's `.claude/rules/` are not used, so that one file carries the same rules to both tools.
