# AGENTS.md

Policy for any agent changing this repository. It is written for a reader that takes the shortest path to "done": every rule comes with the cheapest way to satisfy it, and that way is cheaper than the workaround it replaces. Rationale, parameters and baselines live in `docs/agents-policy.md`; nothing there is needed to work here.

Explicit instructions from the task owner override this file. If an instruction would break a hard rule, do not pick one — file `BLOCKED H-CONFLICT` (below).

## Commands

- Tests: `make test`
- Everything CI runs, in one call: `make gate` — on a `<type>/<slug>` branch (each check is also its own target; named in the sections below)
- Deletion candidates that earn ledger credit: `make credits`
- Before writing a helper, module or wrapper: `rg -n "<concept>" src/`
- Before adding a dependency: `pip index versions <pkg>`
- Start a change: branch `<type>/<slug>`, then `cp docs/changes/_TEMPLATE.md docs/changes/<type>-<slug>.md`
- Never run anything that costs money, calls a model or provider API, or reaches the network beyond package registries. That needs written authorization outside this file (H4).

## How a task ends

Exactly one of two states.

**DONE** — all of: (1) branch type respected; (2) evidence per *Tests*; (3) ledger within allowance; (4) no unresolved expired sunset tag; (5) a record line for every new abstraction and dependency; (6) the change record holds `TYPE:`, `WHY:` (feature/fix), any `SEARCHED:`/`DEP:` lines, and the test commands you ran. Then stop — work you were not asked for is complexity the ledger charges for.

**BLOCKED** — file this and stop. Three lines; no code, no test, no review, no penalty. The task owner answers `NEED` and returns the task, so BLOCKED saves effort only when the need is real — which is exactly when to file it.

```
BLOCKED <TAG>: <what cannot proceed, one line>
NEED: <the decision, fact or artifact that would unblock, one line>
STATE: <branch/commit of work so far, or "none">
```

| TAG | When |
|---|---|
| `SPEC-AMBIGUOUS` | two readings of the task produce different tests |
| `FAILURE-SEMANTICS` | you do not know what the caller should observe when X fails |
| `TEST-DEFECT` | an existing test looks wrong (H1: you may not fix it) |
| `NO-HARNESS` | the real-path test the change needs has no harness |
| `ENV-MISSING` | a dependency, fixture or credential you cannot get without breaking H4 |
| `SUNSET-EXPIRED` | deleting an expired tag's code broke the suite and the repair is outside your task |
| `H-CONFLICT` | the task instruction requires breaking a hard rule |
| `POLICY-GAP` | you found a workaround cheaper than the compliant path — name it (always audited) |

## Hard rules

Enforced outside this file; the text only tells you why a hook or CI job refused you. A *change* is the commit series on one branch, merged as one unit.

- **H1** Never modify, delete, skip, weaken or add a suppression marker to an existing test. New tests land in a commit that precedes the implementing commit. — `.claude/hooks/h1-test-source-separation.sh`, `make check-tests`
- **H2** BLOCKED is always valid, never penalized, and never removes the task from you. — guaranteed by the task owner
- **H3** Nothing merges over its complexity allowance or with an unresolved expired sunset tag. — `make check-ledger`, `make check-sunset`
- **H4** No paid run, model/provider API call or non-registry network access without separate written authorization; uploading code is not one. — sandbox and network settings; CI holds no credentials
- **H5** This file, `policy.mk` and `tests/MOCK_ALLOWLIST` change only on a `policy/*` branch that touches nothing else; always audited. — `make check-type`

## Change type — one per change (§1) — `make check-type`

The type is the branch prefix. A change that needs two types is two branches. `docs/changes/` is allowed in every type.

| prefix | may touch | must have |
|---|---|---|
| `feature/` `fix/` | `src/`, new files under `tests/` | new tests fail on the parent commit; `WHY:`; ledger within allowance |
| `refactor/` | `src/` | no change under `tests/`; suite green; earns credit |
| `test/` | `tests/` | tests written from the spec (BLIND) or by a separate role |
| `chore/` | tooling, docs, CI | nothing under `src/` or `tests/` |
| `renew/` | one sunset tag line | new date, reason, and what would allow deletion; always audited |
| `policy/` | `AGENTS.md`, `policy.mk`, `tests/MOCK_ALLOWLIST`, `docs/agents-policy.md` | always audited |

## Errors and failure semantics (§2) — `make check-masking`

- A handler does exactly one of: re-raise with context; return a typed failure the caller must match; log at ERROR with the exception (then it carries a `masks` sunset tag).
- Refused: a catch-all that does none of those; empty catch; swallowed rejection or ignored return code; `|| true` or `2>/dev/null` on a step that matters; unbounded retry; I/O without a timeout; a fallback value standing in for a failure the caller needs to know about; `# noqa`, `# type: ignore`, `@skip`, `@xfail` added by an implementer.
- A deliberate stopgap is allowed only as `except Exception as e:  # noqa: BLE001  # SUNSET <date> masks owner:<task-id> reason:<why>` — one line that prices it (expiry, 100% audit). A `# noqa` without a `SUNSET` tag on the same line is refused.
- Safe path: not knowing what should happen on failure is `BLOCKED FAILURE-SEMANTICS` — three lines against a mask that costs a handler, a test, a tag, a `WHY:` and a guaranteed audit.

## Tests and evidence (§3) — `make check-tests`

- Write the tests first, from the spec, and commit them before touching `src/`. The H1 hook refuses `src/` edits while `tests/` has uncommitted changes; a committed test file is the registered hash.
- Green is not evidence. Evidence is: the new tests fail on the parent commit (an import error counts); mutation score on touched lines ≥ 0.70; every mock target listed in `tests/MOCK_ALLOWLIST`.
- Mock only the I/O boundaries in `tests/MOCK_ALLOWLIST`. Never mock a module this repository owns.
- Every feature/fix has at least one test on the real in-repo call path. No harness → `BLOCKED NO-HARNESS`.
- Safe path: spec too vague to test → `BLOCKED SPEC-AMBIGUOUS`, not a mock. Existing test looks wrong → `BLOCKED TEST-DEFECT`; editing it is an H1 refusal plus rework.

## Complexity ledger (§4) — `make check-ledger`

- Debits: +1 new `src/` module · +1 new public symbol · +1 new abstraction layer (wrapper, adapter, base class) · +2 new config surface or flag · +3 new direct dependency. Credits: the same amounts when removed with zero references (tool-confirmed) · −1 per duplicate block eliminated · −2 per sunset tag retired by deletion.
- Merge needs debits − credits ≤ 2 unless the task spec grants more in writing (grants are always audited). Surplus is banked, up to 6.
- Zero weight: renames, moves, private symbols, tests, docs, comments, formatting. Decompose freely inside a module; the ledger prices public surface.
- Safe path when over allowance: `make credits`, delete the top candidate, point callers at the survivor. Splitting one function into three nets +2; deleting tests earns zero and trips H1.

## Sunset tags (§5) — `make check-sunset`

- Only under a tag: compat layers, shims, adapters; feature flags; TODO/FIXME/HACK; `masks` handlers; skipped or xfail tests; deprecated aliases; temporary config; vendored code.
  `# SUNSET 2026-12-31 <compat|flag|todo|masks|skip|deprecated|config|vendored> owner:<task-id> reason:<one line>`
- Terms: 30 days for todo/masks/skip, 90 otherwise, 180 max. An expired tag fails `make gate` for every change that neither resolves it nor files `BLOCKED SUNSET-EXPIRED` and appends `grace:<today>` to the tag (once; 7 days).
- Resolve by **delete** (run the suite; green → done, −2 credit, no record, no audit), **renew** (`renew/*` branch, the tag line only, two renewals max, always audited), or **promote** (remove the tag; pay for it as a new abstraction: record plus debit).
- Safe path: try deletion first. Most expired shims have no callers, and `make credits` shows it.

## Records (§6) — `make check-records`

Written in `docs/changes/<type>-<slug>.md` as you go. CI re-runs `SEARCHED` on the base commit and checks `DEP` against the registry.

```
TYPE: feature
WHY: <decision> instead of <alternative>, because <one clause>.
SEARCHED: rg -n "<concept>" src/ → <N hits: path:line ...> | REUSED: <path> | NONE-FITS: <one line per hit>
DEP: <name>==<version> lookup:<command> published:<YYYY-MM-DD> | REASON: <one line> | INSTEAD-OF: <stdlib or existing dep rejected>
TESTS: <exact commands run>
```

- New module, helper, wrapper or base class → a `SEARCHED` line first. New dependency → a `DEP` line first; it must exist at that version, be ≥ 30 days old, and not already be present transitively.
- Safe path: the search usually finds the helper — one import, no debit. Small utilities in stdlib need no `DEP` at all. The `WHY` line is one sentence, cheaper now than when a reviewer cannot reconstruct it.

## Code Review Rules

Applied by Codex code review and by the audit skill (`.claude/skills/audit/SKILL.md`). Findings become `fix/` or `test/` tasks; they reopen the change and never sanction the agent.

### Error masking
- Flag a catch-all handler, empty catch, ignored return code, `|| true`, unbounded retry or timeout-less I/O that carries no `masks` sunset tag.
  Safe path: re-raise with context, return a typed failure, or file `BLOCKED FAILURE-SEMANTICS`.
### Test edits inside implementation changes
- Flag any modified or deleted file under `tests/` on a `feature/`, `fix/` or `refactor/` branch.
  Safe path: `BLOCKED TEST-DEFECT`; a `test/` branch adjudicates.
### In-repo mocks
- Flag a mock whose target is not in `tests/MOCK_ALLOWLIST`.
  Safe path: test the real call path; no harness → `BLOCKED NO-HARNESS`.
### Unrecorded abstractions and dependencies
- Flag a new module, wrapper or dependency with no `SEARCHED`/`DEP` line, and a `NONE-FITS` that dismisses a hit which fits.
  Safe path: reuse the hit; stdlib for small utilities.
### Untagged temporary code
- Flag a shim, flag, TODO, skip or vendored copy without a `SUNSET` tag, or a tag edited outside a `renew/` branch.
  Safe path: delete it, or open a `renew/` branch.

## Audit (§7)

`make audit-select` draws 20% of merged changes at random plus 100% of: `renew/` and `policy/` changes, `masks` tags, `NONE-FITS` with hits, `POLICY-GAP` and `SUNSET-EXPIRED` filings, allowance grants, and paths listed under `AUDIT_ALWAYS_PATHS` in `policy.mk`. The auditor is a fresh instance running `.claude/skills/audit/SKILL.md`. Its only valid outputs are a reproducible failing test or an attestation listing at least three attack paths with the commands run; "LGTM" is not an output.
