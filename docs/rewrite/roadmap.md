# Proposed roadmap and work-package register

**WP-01/02/03 kernel packages AUTHORIZED; D7b is not their prerequisite.**
[Frozen M1-K1](m1-kernel-contract.md) and [issued work packages](wp-m1-foundation.md)
supersede the draft foundation entries below. WP-01 and disjoint WP-03 run
concurrently; WP-02 follows WP-01 final acceptance. Tiny vector/test edits use micro-go.
UI-lab integration paused at user direction until kernel exists; files preserved.
Production UI still needs explicit rendered approval; kernel content is not invented
by implementers. Full M1 playable release loop remains later work.
The old game remains playable throughout; only proven slices enter the new game.

## R1 — Milestones and playable boundaries

| ID | Playable outcome / gate | Dependencies and audit |
| --- | --- | --- |
| M0 Discovery and protection | Existing browser/terminal still playable; approved direction and frozen first-slice contract | D1–D6 approved; M1-K1 frozen; D7b only blocks presentation, not kernel |
| M1-kernel Foundation | Deterministic clock/commands, auditable cash and obligations, strict safe save/reload | WP-01 + disjoint WP-03 parallel; WP-02 after WP-01; all reviews and cross-codec audit |
| M1 One distinctive small release | New opt-in solo campaign can study/contract, investigate, commit/cut/delay, release into a small reactive market, inspect a postmortem, save/reload and fail safely | Minimal clock/finance/knowledge/persistence; approved UI; at least three contrasting project strategies, not a single scripted demo |
| M2 Small team and capability paths | Hire zero/multiple-trait people, specialize/mentor, allocate work, research transformative capabilities; small studio can remain viable | Prove training costs/capacity, knowledge effects, trait tradeoffs and accessible connected tree |
| M3 Commercial studio | Multiple stores/platforms, audience/cohort/region analysis, pricing/marketing/publisher commitments and franchises | Acquisition/owner/refund conservation, accounting attribution, confidence/coverage and information progression |
| M4 Sustainable portfolio | Concurrent projects/teams, support policies, diagnosed initiatives, leads and escalations, risky live pivots | Bounded delegation, scarce attention, routine automation without losing causal explanations; long-lived success possible but not guaranteed |
| M5 Industry-scale mastery | Departments, global catalogue, strategic partnerships and high-prestige expectations; long-run challenge without arbitrary inflation | Only approved global-company scope; balance many seeds, organizational costs, boutique path remains worthwhile |
| M6 Replacement release / cutover | Complete new campaign, safe saves, supported frontend matrix, onboarding and recovery; user approves new default entrypoint | Holistic audit, compatibility/rollback rehearsal, performance/accessibility, documentation and user acceptance |

Each milestone must prove a satisfying loop before widening content. Do not build a
huge research tree or analytics warehouse before the decisions they support exist.
No time estimate is meaningful until the initial scope and support matrix are approved.

## R2 — Draft bounded packages for M0 / M1 foundation

### WP-UI-00 — Authorized now: rendered selection lab

**Implementation scope superseded 2026-09-11:** [WP-UI-01 family](ui-parallel.md)
uses a reviewed shared foundation, FIVE concurrent directory-isolated frontend-go
workers, then one integration package. Original P2–P6 fixture behavior retained.

See [frozen work package](wp-ui-00.md). DeepSeek implements exactly five interactive
variants of one decision-centered product plan with common fixtures. Only six
new files under `prototypes/studio-lab/` are allowed; production untouched.
Scope/diff/acceptance → Sol → Ponytail → final Sol → Astra lab audit → user selection.
Historical authorization only. UI integration is now paused; kernel packages are
authorized independently. No further lab expansion before the simulation kernel.

### D1–D6 roadmap adjustments

- Strong soft specialization across people/experience/fans/IP/capabilities is a
  cross-milestone requirement, not a mandatory global-corporation progression ladder.
- No weekly turn/mandatory planning ritual; only active visible browser play advances.
- No legacy-save migration/import work and no new CLI/terminal work. Existing code
  remains untouched as the rollback baseline, not a replacement support commitment.
- Normal reloadable autosaves plus creation-time opt-in Ironman belong in the save
  design. Exact safe campaign-scoped invalidation/deletion must be reviewed before
  implementation; the lab never touches real campaign saves.
- Architecture/staged replacement approved, exact production schemas still pending.

These specify scope and objective checks **as proposals**. Listed tests/modules do
not exist yet; their commands are future acceptance commands, not claimed passes.
Astra must freeze the referenced C-contracts and concrete scenario/expected-value
appendices before issue. Package owner is `frontend-go` for these substantial
tasks. No task here is tiny enough to justify `micro-go`. Writers are sequential
where files/dependencies overlap. The worker must not create unlisted files.

### WP-00 — Legacy characterization witnesses

**Withdrawn from dispatch after D3/D4.** Retained below as historical draft, not a
compatibility obligation or allocation of new work. Use existing baseline tests and
targeted new-engine invariants instead of a legacy conversion/terminal test project.

- **Milestone/goal/rationale:** M0; distinguish reusable guarantees from accidents
  without touching the protected prototype.
- **References:** `inventory.md` characterization strategy; A5 preservation;
  approved C1/C2 continuation invariants are comparison targets, not legacy assertions.
- **Allowed files:** `tests/rewrite/test_legacy_characterization.py`,
  `tests/rewrite/fixtures/legacy_witnesses.json` only.
- **Required behavior:** fixed seed and injected explicit date; observe representative
  pipeline JSON round-trip/continuation, query neutrality and day/batch behavior.
  Fixtures report known divergences rather than rewriting legacy code to pass.
  All writes use disposable directories; never open a user save for mutation.
- **Acceptance:** `TMPDIR=/tmp/opencode python -m unittest discover -s tests/rewrite -p test_legacy_characterization.py`;
  then `python -m unittest test_simulation test_version10 test_browser`.
  Evidence: deterministic witness contents, passing tests, explicit risk ledger
  for divergences; no silently updated snapshots.
- **Non-goals:** fixes, new mechanics, HTTP/UI redesign, economic compatibility promises.
- **Rollback/compatibility:** additive tests only; legacy entrypoints untouched.
- **Reviewer checklist:** freeze date not just seed; actual JSON encode/decode;
  no external saves; no invented expected outcomes; observations labeled honestly.

### WP-01 — Authoritative clock and command boundary (draft superseded)

Issued scope/interfaces/acceptance: [WP-M1 foundation](wp-m1-foundation.md), M1-K1.

- **Milestone/goal/rationale:** M1 foundation; eliminate split-clock, rejected-command
  mutation and randomness coupling before adding production rules.
- **References:** A1–A3, C1, C3, frozen M1 clock/command/random vectors (not yet written).
- **Allowed files:** `studio_sim/__init__.py`, `studio_sim/domain/__init__.py`,
  `studio_sim/domain/campaign.py`, `studio_sim/application/__init__.py`,
  `studio_sim/application/commands.py`, `studio_sim/application/service.py`,
  `studio_sim/application/tick.py`, `studio_sim/infrastructure/__init__.py`,
  `studio_sim/infrastructure/randomness.py`, `tests/rewrite/test_clock_commands.py`.
- **Required interfaces:** C1 configuration/campaign/revision/command/result/advance
  types; named random protocol with golden vectors; no-op days, explicit holds,
  ended-campaign status and transactional rejection. Only the minimal authorized command
  vocabulary, not a dynamic handler/plugin framework.
- **Acceptance:** `python -m unittest discover -s tests/rewrite -p test_clock_commands.py`.
  Evidence: day/batch equality, deterministic replay and random vectors, no query
  draws, unchanged snapshots on rejection, duplicate/stale-ID behavior, stopping
  at exact decision day and closed-state absorption.
- **Non-goals:** project/market rules, save files, wall-clock loop, UI, general event bus.
- **Rollback/compatibility:** new namespace only; old game remains the playable boundary
  until the full M1 release loop passes. No claim that this kernel alone is a game.
- **Reviewer checklist:** no implicit date/time/global RNG; no unbounded command
  receipt cache; stable IDs; service contains transaction mechanics, not game rules.

### WP-02 — Auditable cash and obligations (draft superseded)

Issued scope adds service.py/commands.py for the real transaction boundary, without
parallel overlap; see [WP-M1 foundation](wp-m1-foundation.md), M1-K1.

- **Milestone/goal/rationale:** M1 foundation; every early survival decision must
  reconcile cash and explain product economics.
- **References:** G3/G4/G8, A2/A3, C1/C3; frozen M1 money/rounding/settlement table
  and normal versus Ironman failure policy (blocked until specified).
- **Allowed files:** `studio_sim/domain/finance.py`,
  `studio_sim/domain/campaign.py`, `studio_sim/application/tick.py`,
  `tests/rewrite/test_finance_obligations.py` only, sequentially after WP-01.
- **Required behavior:** opening balance and postings reconcile to cash; dated
  obligations, founder living draw, income, expense and financing classifications;
  product labor attribution is not a second cash deduction; lifecycle-safe closure.
  Finance returns typed effects rather than writing saves or UI messages.
- **Acceptance:** `python -m unittest discover -s tests/rewrite -p 'test_*.py'`.
  Evidence: cash identity, due-date/boundary/rounding examples, principal versus
  expense, negative-runway warnings, rejected spend atomicity, safe end-state tests.
- **Non-goals:** real tax jurisdictions, stock exchange, M3 publishing/recoup mechanics,
  accounting framework or importing legacy float balances.
- **Rollback/compatibility:** replacement namespace only; preserve WP-01 interface
  guarantees and existing baseline. Reject schema changes beyond approved extension.
- **Reviewer checklist:** no double labor charge; no omitted cash postings; exact
  expected amounts from Astra's table; bankruptcy does not touch filesystem.

### WP-03 — Strict save and safe continuation (draft superseded)

Issued independent codec/safety scope, no migrations.py or domain imports:
[WP-M1 foundation](wp-m1-foundation.md), M1-K1. Parallel with WP-01.

- **Milestone/goal/rationale:** M1 foundation; safe saves before accepting player time.
- **References:** A5, C1/C2; frozen schema, lock, backup and recovery state machine
  (blocked), D3 no legacy compatibility, D5 normal/Ironman policy.
- **Allowed files:** `studio_sim/infrastructure/saves.py`,
  `studio_sim/infrastructure/migrations.py`, `tests/rewrite/test_save_safety.py`,
  `tests/rewrite/fixtures/rewrite_v1.json` only.
- **Required interfaces:** strict payload codec, validated temporary load, save-slot
  writer and explicit verified-backup recovery as specified in C2. An empty migration
  module is not required if the first schema needs no transforms; no generic registry.
  Source data preserved on every failure; do not initialize a campaign during decode.
- **Acceptance:** `TMPDIR=/tmp/opencode python -m unittest discover -s tests/rewrite -p 'test_*.py'`.
  Evidence: full canonical round-trip and future replay, intentional empty collections,
  unsupported version/type/ref failures, corrupted primary/valid backup, injected
  write/flush/replace/backup failures and conflicting writer; no user-save paths.
- **Non-goals:** v11 conversion, CLI; cloud sync,
  arbitrary directory browser, compression, downgrade migration.
- **Rollback/compatibility:** new saves distinctly recognized; schema changes require
  explicit migration; rollback preserves both old/new campaign files.
- **Reviewer checklist:** never clobber last valid backup; failed load cannot replace
  active state; no arbitrary code loading; transient UI/session secrets absent.

Before a production UI package, Astra must issue one bounded, isolated prototype-lab
package implementing `ui-concepts.md`: DeepSeek builds five interactive variants from
one shared brief in one local browser page. The selected variant fills the game
surface; a fixed right-side rail provides numbered 1–5 replacement controls and
local/exportable feedback. Variants are never shown side by side. It uses fixtures rather than
replacement simulation/API wiring and includes an explicit cleanup/reuse plan.

M1 project/evidence/market loop, API and production UI packages will be bounded
**after** the remaining design decisions are approved and exact interfaces are frozen.
They are not issued as a vague "build the rest" task. Production UI filenames and
screenshot criteria depend on the selected rendered prototype direction; inventing
them now would preempt user approval.
M2–M6 packages are intentionally not implementation-ready either.

## R3 — Acceptance and review protocol for every issued package

Controlled parallelism: once contracts are frozen and write scopes are disjoint,
dispatch independent work concurrently instead of defaulting to one worker. Shared
contract/shell changes finish and freeze first; integration waits until dependency
workers finish. Reviews may run concurrently on disjoint packages; corrections
stay with each package's original worker. Record explicit dependency barriers and
per-worker files/test ports so shared writes and test processes cannot collide.

1. Capture exact dirty-tree baseline and protected file hashes; record package ID,
   contract versions, allowed paths, worker session and acceptance commands.
2. Dispatch Go first. Record actual provider/auth/quota/transport error before any
   matching OpenRouter fallback. Incorrect work returns to the same Go worker.
3. Astra checks allowed-file scope, collects full diff and reruns objective commands.
4. Sol receives package, contracts, diff and test evidence (including screenshots
   and worker's own image inspection for UI). REWRITE goes back with full findings;
   at most two correction cycles. ESCALATE returns contract decisions to Astra.
5. After PASS, explicitly load `ponytail-review`; Astra separately reviews simplicity.
   Local skill source exists at `.opencode/skills/ponytail-review/SKILL.md`.
   If skill loading is unavailable, report/block the gate, never claim it happened.
6. SIMPLIFY sends only justified deletions/simplifications to the same worker, once
   maximum. Preserve behavior, validation, accessibility, security, tests and save safety.
   Re-run acceptance and Sol on the simplified diff. LEAN requires final Sol PASS;
   without simplification, preserve the correctness record and obtain final confirmation
   on the unchanged accepted diff rather than claiming an unperformed review.
7. Record both review gates and exact diff/evidence in `decisions.md` or linked
   immutable review notes. Update package status only after all gates pass.
8. Astra milestone audit: cross-package contracts, architecture drift, difficulty and
   strategy integrity, knowledge leaks, UX consistency, performance, test gaps,
   legacy preservation, save/rollback safety and documentation accuracy.

No runtime implementation occurred during discovery, so no implementation Sol or
Ponytail gate is claimed. Planning authorship is Astra's responsibility.
