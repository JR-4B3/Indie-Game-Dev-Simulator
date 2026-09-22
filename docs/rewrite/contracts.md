# Contracts — M1 kernel frozen; remaining systems candidates

**M1 clock/command, finance and saves are now frozen** in
[M1-K1](m1-kernel-contract.md), which supersedes C1/C2 candidates for WP-01/02/03.
User explicitly removed D7b as a kernel dependency. The remaining API/UI/content
schemas below are candidates; D7b still governs production presentation only.
The separate WP-UI-00 contract is frozen only for disposable fixture prototypes.
Later slices may extend versioned contracts only through an explicit decision.
Implementers must escalate missing semantics rather than inventing them.

## C1 — Simulation

- Campaign identity: `campaign_id`, explicit ISO start date/calendar day, integer
  master seed, ruleset ID, simulation version, revision, status, next entity IDs,
  domain aggregates, player knowledge and pending decisions.
- Proposed entrypoints: `new_campaign(config, rules) -> Campaign`,
  `execute(campaign, command, rules, random_source) -> CommandResult`,
  `advance(campaign, requested_days, rules, random_source) -> AdvanceResult`,
  `project_view(campaign, query) -> ViewDTO`. Mutation confined to successful
  application transactions; commands are validated fully before authoritative commit.
- Command envelope: command ID, expected revision, kind, stable target ID and typed
  payload. Rejection leaves domain, RNG counters, ID counters and ledger unchanged.
  Result: accepted/rejected, code, current revision, field errors and emitted event IDs.
  Idempotency means repeated command ID with identical body cannot spend/advance
  twice; reused ID with another body is rejected. Save the bounded recent receipts;
  requests outside that window with stale revision are rejected, never assumed safe.
- Canonical integer day, integer currency minor units and integer populations/work
  quanta where meaningful. Rate rounding and attribution remainder rules must be
  explicit; prohibit NaN/infinity. UI conversions never define simulation behavior.
- Same canonical start state/date, rules/simulation version, seed and commands →
  identical state and event sequence, including across save/reload. Named draw keys
  include system/day/entity/purpose/ordinal, with a specified stable digest protocol;
  do not use Python's process-randomized `hash()` or depend on iteration order.
  Freeze golden draw vectors before M1 implementation. No cross-ruleset identity promise.
- `AdvanceResult`: actual days consumed, revision, stop reason and pending decision
  IDs. Single-step/batch equivalence is mandatory. Closed campaigns do not advance
  or accept business commands. Normal closed campaigns remain inspectable/saveable;
  a failed opt-in Ironman campaign cannot produce a resumable save.
- Every labor unit has one allocation; obligations and cash reconcile; all cohort
  populations and product ownership transitions obey specified conservation rules.

## C2 — Save/persistence

- Proposed envelope: `format_id="studio-rewrite"`, `schema_version`,
  `simulation_version`, `ruleset_id`, `campaign_id`, canonical campaign payload and
  integrity digest. Wall-clock saved-at metadata is outside deterministic state.
- Contains complete simulation/knowledge/decision state, deterministic counters and
  recent command receipts; no modal/focus state, wall-clock elapsed time, auth token
  or server filesystem path. User preferences may live in a separate section/file.
- Strict decode into a temporary validated aggregate. Validate types (including bool
  versus int), bounds, finite values, unique IDs, referential integrity and transitions.
  Unknown version fails clearly; no silent default regeneration or partial repair.
- New saves use a distinct directory and extension/format recognition. Legacy v11
  conversion is excluded by D3; unsupported-file rejection is non-destructive.
- Unique temporary sibling file, flush/fsync, verified backup of last valid payload,
  atomic replace, platform-appropriate directory sync. Do not overwrite a known-good
  backup with a corrupt primary. Failed load/write never changes the active campaign
  or silently replaces a valid file. Single writer per save; explicitly reject a
  conflicting writer. Detailed lock/recovery semantics must be specified for M1.
- Recovery offers verified backup inspection/restore to a new file; never guesses
  silently. Migrations are pure version-to-version transforms with fixtures and
  original preserved. No downgrade writes. Normal campaigns retain reloadable
  autosaves on bankruptcy. Campaign mode is selected explicitly at creation;
  Ironman failure may delete/invalidate that campaign's primary/autosave/backup set
  only. Requires a reviewed ownership manifest, explicit failure record, path
  containment and crash-consistent invalidation/recovery policy before implementation.
  Never infer failure from corrupt data, transport error or a failed write. Never
  traverse/delete unrelated campaigns or legacy saves. No deletion in WP-UI-00.

## C3 — Events, causality and knowledge

- Domain event: schema version, ID, day, kind, subject IDs, originating command or
  tick, causally relevant prior event/decision IDs, structured facts and visibility.
  Domain events describe what happened, not authoritative prose-only logs.
- Observation: ID, observed subject/claim, source/method, evidence quality,
  sampling/coverage and lag, confidence, date, supporting/contradicting observations,
  relevant decision links and discoverability condition.
- Actual causes and the player's inferred causes are different types/projections.
  Player endpoints never expose hidden truths/formula contributions just because
  they are logged internally. Discovery changes knowledge, not past reality.
- Retain project commitments and material causal chains for lifetime postmortems;
  compact routine ticks into aggregates. A retention policy must preserve referenced
  evidence or its immutable summary; never dangling causal links after a log cap.
  Not a full event-sourced world: snapshots are authoritative, events explain them.
- Alerts have severity, decision requirement, due day, allowed actions and fallback
  policy. Routine observations do not force modal interruption; material unresolved
  decisions stop time according to the approved interaction contract.

## C4 — Browser API and session safety

- Local loopback-only server, bundled assets, no cloud/CDN dependency. Proposed
  routes: `GET /api/v1/session`, `GET /api/v1/view?scope=...`,
  `POST /api/v1/commands`, and `POST /api/v1/session/control` for speed/hold/lease.
  Save/load are explicitly authorized commands using validated slot IDs; clients
  cannot provide arbitrary filesystem paths. Exact allowed request schemas freeze
  with the first slice, not via reflection over internal dataclasses.
- Read endpoints are pure with respect to domain and knowledge; transport heartbeat
  renewal affects only controller session state. Responses include API version,
  campaign revision, projected knowledge, available action descriptors and errors.
- Validate exact loopback Host, same-origin policy/Origin when supplied, session
  token for mutations, content type, bounded bodies and rate/command sizes.
  Reject unknown routes/fields/types; escape text and use restrictive CSP. Never
  serialize internal errors, save paths or hidden state to the browser.
- Semantic command failures use stable machine codes plus readable/field messages;
  stale revision/conflicting controller is a conflict, not a silent lost update.
  Disabled actions explain prerequisites; the server remains authoritative.
- One controlling tab/session; other tabs are read-only or explicitly acquire
  control. Separate manual pause, decision holds and temporary preview holds with
  ownership; closing a dialog cannot overwrite a later manual pause decision.
- Visibility loss releases active play immediately; a controller lease bounds abrupt
  disconnect detection (candidate three seconds). No background/offline catch-up.
  Regaining visibility/reconnecting establishes a fresh time baseline and state before
  commands. Wall-clock interval only requests whole-day advances; engine stopping
  rules prevail. Client meter interpolation never exceeds confirmed progression.

## C5 — UI/presentation

- Stable IDs, explicit action capabilities and knowledge-safe browser view models.
  No retained replacement terminal or `asdict(campaign)` browser escape hatch.
- Metrics expose value or unknown, unit, period, scope, source/lag, coverage,
  estimated/observed status and uncertainty. A display label is not a simulation key.
- Proposed plan is distinct from committed plan. Editing and canceling never spend
  money or alter authoritative work; commit previews display cost/capacity,
  irreversible effects, tradeoffs and relevant unknowns. Revision conflicts preserve
  the draft for review but require refreshing affected estimates before commit.
- Separate progress/work, readiness and confidence. Scope changes annotate baseline
  movement. Color is redundant with text/shape. Findings link to affected decisions.
- All critical flows keyboard accessible, visible focus, safe text editing shortcuts,
  dialog focus restore, labeled charts/tables, readable contrast and reduced motion.
  Narrow viewport keeps complete action/inspection paths; scroll is allowed.
- Inspection is normally nonblocking; commitment preview, explicit pause and severe
  escalation have named holds. Final exact behavior depends on the selected rendered
  prototype direction.
- Screenshot acceptance uses 1440×900 and 390×844 plus intermediate sizes, long
  labels, missing/uncertain data, large teams/portfolios, loading/errors, pending
  decisions and keyboard-only flows. No clipping/overlap or hidden critical actions;
  verify meaningful hierarchy visually, not just absence of scrollbars.

## C6 — Outstanding freeze decisions

K1/K2/K3/K4 below the M1-K1 document settle kernel schemas, command/clock stops,
golden RNG, cents/settlement/solvency and save locking/recovery/invalidation now.
Do not use the older unresolved list to block these authorized foundation packages.

User: rendered D7b selection pending; D1–D6 feedback is recorded in `decisions.md`.
Astra: exact M1 content/balance table,
daily/weekly processing and launch/obligation timing; typed schemas/error codes;
random protocol/goldens; cash/rounding and ownership rules; event retention;
save locking/fault recovery; controller/hold state machine; selected UI layouts;
deterministic scenario fixtures; runtime/performance/analytics-size budgets.
No package can start while its relevant entries remain unspecified.
