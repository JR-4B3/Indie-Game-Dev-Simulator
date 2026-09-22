# M1-K1 — Frozen clock, command, finance and save contracts

Status: **FROZEN / AUTHORIZED**, Astra, 2026-09-11. User explicitly decoupled
kernel work from rendered D7b and ordered WP-01/02/03. This document overrides
the candidate C1/C2 and draft package details for this foundation ONLY. D7b still
blocks production UI, not the simulation kernel. No lab fixture balance is reused.
Python standard library only; Linux is the tested save-lock platform. No CLI,
HTTP adapter, wall-clock scheduler, legacy import, project/market simulation or
production UI in these packages. Existing game and all existing saves stay intact.

## K0 — Ownership and dependency seam

- WP-01 owns explicit Campaign/command/clock types and stateless random adapter.
- WP-02 extends WP-01 sequentially with finance rules; no schema changes required.
- WP-03 is an independent dictionary-to-bytes codec and filesystem repository.
  It imports **no application/domain module**: both workers use the exact JSON
  snapshot below. This permits genuinely independent implementation and tests.
- Domain/application never import saves, wall clock, OS, adapters or global RNG.
  Saving explicitly consumes `to_payload(campaign)`; loading validates into a
  temporary dictionary then caller constructs via `from_validated_payload`.
  Neither decode nor load initializes/defaults a campaign or swaps active state.
- Finance commands here are **trusted application/test stimuli**, not permission
  for a player/browser to mint money or author obligations. A later gameplay/API
  package maps validated business outcomes to these effects. No new user-facing
  mechanic is implied by these technical transaction inputs.

## K1 — Types, canonical snapshot and bounds

All integers are exact Python/JSON integers, **never bool, float or coerced text**.
Identifiers match `[a-z][a-z0-9_-]{0,47}`; campaign/command/decision/obligation/
product IDs use this rule. No generated UUID/time-dependent defaults. Text reason
is 1..160 characters, no NUL; other free text is not part of this schema.
Dates are exact ISO `YYYY-MM-DD`, valid calendar dates; start year2000..2199.
Day offsets0..36500; date derived by start+day, not separately persisted.
Money absolute values≤10^12 minor units (cents), per-post amounts nonzero;
opening cash0..10^12; monthly founder draw0..10^9; seed0..2^64−1.
Revision0..10^9. Collections bounded: decisions64, recent receipts64,
events8192, postings8192, obligations512, labor4096. Resource exhaustion rejects
commands with `capacity`, or stops advance before the affected day with `capacity`.
No silent eviction except oldest accepted command receipts (FIFO64).

Canonical snapshot exact keys (no omitted/unknown keys at any level):
```
{
  "campaign_id": ID, "start_date": ISO, "seed": INT,
  "simulation_version": 1, "ruleset_id": "m1-kernel-1",
  "mode": "normal"|"ironman", "day": INT, "revision": INT,
  "status": "running"|"retired"|"failed",
  "closed_reason": null|"retired"|"insolvent", "manual_paused": BOOL,
  "next_event_id": INT, "events": [EVENT],
  "decisions": [DECISION], "receipts": [RECEIPT],
  "finance": FINANCE
}
DECISION = {"id":ID,"due_day":INT,"reason":TEXT,"resolved":BOOL}
EVENT = {"id":"e-N","day":INT,"kind":KIND,"source":SOURCE,
         "subject_id":ID|null,"facts":FACTS}
RECEIPT = {"command_id":ID,"fingerprint":HEX64,"applied_revision":INT,
           "event_ids":["e-N"]}
FINANCE = {
 "opening_cash_minor":INT,"cash_minor":INT,"monthly_draw_minor":INT,
 "negative_since_day":INT|null,"next_posting_id":INT,
 "postings":[POSTING],"obligations":[OBLIGATION],"labor":[LABOR]
}
POSTING = {"id":"p-N","day":INT,"category":CATEGORY,"amount_minor":INT,
           "source":SOURCE,"product_id":ID|null}
OBLIGATION = {"id":ID,"due_day":INT,"category":CATEGORY,"amount_minor":INT,
              "product_id":ID|null,"paid":BOOL}
LABOR = {"posting_id":"p-N","product_id":ID,"amount_minor":POSITIVE_INT}
```
N is canonical positive decimal, starting1, no leading zeros. Event/posting lists
are in creation order, contiguous IDs; next counters equal len+1, even when empty.
Decision/obligation IDs unique within their list, lists sorted by ID. Events/postings
nondecreasing day, each≤campaign day. Resolved decisions must be due≤day. Unresolved
decisions may be due≤day (they hold time). Paid obligations due≤day; unpaid must
be due>day in valid boundary snapshots. Receipt IDs unique, fingerprints lowerhex,
applied revisions strictly increasing1..revision; referenced events must exist.
An accepted no-op command has an empty event list but still a receipt/revision.
Product IDs are accounting attribution keys, not references to a not-yet-built
project registry. LABOR references an existing expense posting; unique
(posting_id,product_id), summed allocation≤absolute posting amount.

Valid finance categories: `income` (positive), `expense` (negative), `draw`
(negative), `financing` (either sign). Obligations allow all except `draw`.
Sources: `cmd:ID`, `obligation:ID`, `draw:YYYY-MM-DD`, `tick`, `clock`.
Postings only use the first three: command for immediate posts, obligation for
settlements, draw for founder draw (date equals posting's derived date). Exactly
one posting per paid obligation with equal category/amount/product/due day; none
for unpaid; no unknown obligation source. At most one draw posting per date,
category draw/product null, amount from K3's daily formula. Immediate postings
cannot use category draw. Multiple events/postings may reference a command whose
receipt has aged out; do not require its receipt to remain.

Cash = opening + sum(all postings), signed and bounded. Negative cash iff
negative_since_day is non-null; it is between1 and current day. In `running`,
day−negative_since_day+1 <7. In `failed`, cash<0 and that interval≥7;
closed_reason=`insolvent`. In `retired`, closed_reason=`retired`; running reason
null. Retired snapshots may contain shorter negative intervals. No end-state
mutation/advance (aside from identical cached command replay returning a receipt).
No cross-ruleset/schema defaults, empty-list regeneration or hidden fields.

EVENT kinds/facts exact (all sources/subjects constrained as follows):
- `pause_changed`: source cmd:ID, subject null, facts {"paused":BOOL}.
- `decision_resolved`: source cmd:ID, subject existing decision ID, facts {}.
- `campaign_closed`: source cmd:ID for retirement or tick for insolvency,
  subject null, facts {"reason":"retired"|"insolvent"} matching source/status.
- `cash_posted`: source matches referenced posting source, subject null,
  facts {"posting_id":"p-N"}; reference must exist and share event day.
- `obligation_added`: source cmd:ID, subject existing obligation ID, facts {}.
- `labor_attributed`: source cmd:ID, subject product ID,
  facts {"posting_id":"p-N","amount_minor":POSITIVE_INT}; matching LABOR entry.
- `liquidity_warning`: source tick, subject null,
  facts {"negative_since_day":INT}; equals event day (new negative episode).
No event for an idle day or merely querying. Material events never get truncated.

## K2 — Clock, command transactions and randomness

Public imports (names frozen; internal implementation simple and explicit):
```
domain.campaign:
  CampaignConfig(campaign_id, start_date, seed, mode,
                 opening_cash_minor, monthly_draw_minor, decisions=())
  Campaign  # dataclass with explicit top-level snapshot fields
  new_campaign(config) -> Campaign
  to_payload(campaign) -> dict
  from_validated_payload(payload) -> Campaign
  calendar_date(campaign) -> str
application.commands:
  Command(command_id, expected_revision, kind, payload)
  CommandResult(campaign, accepted, code, applied_revision, event_ids, duplicate)
application.service:
  execute(campaign, command) -> CommandResult
application.tick:
  AdvanceGate(active_play, preview_holds=())
  AdvanceResult(campaign, consumed_days, stop_reason, pending_decision_ids)
  advance(campaign, requested_days, gate) -> AdvanceResult
infrastructure.randomness:
  draw_u64(seed, system, day, entity, purpose, ordinal) -> int
```
Campaign's nested records may be JSON-shaped dicts/lists (no speculative class
per record). Boundary functions deep-copy nested state. **All APIs functional**:
input campaign/config/payload unchanged even on success; results own new state,
no alias into caller collections. Frozen dataclasses recommended at top level;
no recursive immutable framework needed. from_validated_payload trusts only the
strict codec's already-validated dictionary; it copies but does not regenerate
missing fields. It is an internal loading seam, not an untrusted browser API.
to_payload is full internal save/test snapshot, **not** a player knowledge view.

new_campaign: explicit config values, day/revision0, running/null reason,
manual_paused=false, counters1, empty events/receipts/postings/obligations/labor,
cash=opening, negative_since=null, configured decisions copied/sorted and unresolved.
Config decisions exactly {id,due_day,reason}, may be due0; only technical scheduled
review witnesses until real project decisions exist. Validate config, raise ValueError
on invalid values; never accept an already-resolved config decision.

Command envelope validation: actual Command, ID valid, revision bounded integer,
kind string, payload exact plain dict. Payload descendants must be exact JSON
types: dict with string keys, list, str, int (not an integer subclass), bool or None;
no tuple/set/custom objects/floats. Reject ancestor cycles and nesting beyond32
container levels (root payload counts as1) as invalid_command, not an exception.
These limits bound untrusted command validation; shared references without cycles
are allowed and canonicalize as repeated JSON values. Fingerprint SHA256(canonical JSON of
{"expected_revision":N,"kind":K,"payload":P}), lowerhex; reject invalid JSON types
or unknown payload keys before use. Canonical JSON defined K4. Validation order:
envelope/types → existing receipt lookup → stale revision → closed campaign →
kind/payload semantics → transactional application and capacity validation.
Cached same ID/fingerprint: accepted true, code `duplicate`, duplicate true, current
unchanged campaign, ORIGINAL applied_revision/event_ids, even after end. Same ID
different body: `id_conflict`. Evicted ID has no special privilege; stale expected
revision gets `stale_revision`. Rejected commands not cached and change nothing.
Accepted new command increments revision exactly1, receipt FIFO64, code `ok`,
duplicate false. event_ids tuple of emitted IDs; rejected applied_revision null,
event_ids empty. Other codes: `invalid_command`, `unknown_command`, `ended`,
`not_due`, `already_resolved`, `unknown_target`, `insufficient_cash`,
`duplicate_target`, `invalid_allocation`, `capacity`. Reject rather than raise for
command input failures; don't blanket-catch programming bugs.

WP-01 kinds/payloads:

Every new acceptance, including a no-op set_pause, checks revision capacity first;
a full event list alone does not prohibit a no-op that emits no events. Cached
duplicates consume neither revision nor event capacity and still return normally.
- `set_pause`: {"paused":BOOL}; valid while held. Same value accepted no-op receipt,
  no event. Changed value emits pause_changed.
- `resolve_decision`: {"decision_id":ID}; unknown/notdue/resolved reject with
  corresponding codes; due unresolved resolves and emits decision_resolved.
- `retire`: {}; status retired/reason retired, emits campaign_closed. Normal and
  Ironman voluntary retirement remain inspectable; it is NOT insolvency invalidation.
WP-02 adds three exact finance kinds in K3; WP-01 returns unknown_command for these
until extension. No plugin registry or arbitrary callback command dispatcher.

advance requested_days integer0..3660, gate actual AdvanceGate with active bool,
preview_holds tuple of unique IDs, invalid function inputs raise ValueError.
Zero request returns `complete` with no changes regardless of holds/status.
For positive requests pre-step stop precedence: ended → inactive → manual_pause →
preview_hold → decision (all unresolved due≤day). Then one whole day:
  increment day → K3 settlements (WP-02) → identify due reviews → evaluate solvency
  → revision+1 → stop if failed or due decision, else repeat up to request.
Both settlement AND solvency evaluation belong to WP-02. WP-01 only preserves
already-ended absorption/stop precedence; it must not inspect financial balances
or synthesize insolvency closure before the settlement implementation exists.
Do not emit routine day events. Before exceeding day/revision/collection/money bound,
stop `capacity` without consuming that day. Post-day precedence ended before decision.
Other stop reasons exactly `complete`, `ended`, `inactive`, `manual_pause`,
`preview_hold`, `decision`, `capacity`. Pending IDs sorted; include due unresolved
IDs in every result. Day/batch results' campaigns identical, no batch metadata in
state. Core **never reads a real clock**; caller must supply current active-play
gate. Visibility/lease enforcement belongs to later browser adapter, not simulated
by a boolean pretending to authenticate a browser here. No offline catch-up.

RNG is stateless SHA256 of ASCII canonical JSON list
`["studio-rng-v1",seed,system,day,entity,purpose,ordinal]`; u64 is first8 digest
bytes big-endian unsigned. system/entity/purpose IDs, ordinal0..2^32−1, bounds
as above. No Python hash()/random/global RNG or hidden draw counter. Callers own
explicit ordinal when future rules use draws; kernel idle/command/query draw none.
Goldens (args → full hash → u64):
```
[0,"clock",0,"campaign","witness",0]
235fc7ebcd986a6d8321e25bf8b4e0f8ddebf02b48195eaecc08cc314a16474e
2548975729695550061
[42,"market",7,"project-a","demand",0]
efd9c714aee6be7066db918f8beacfd24bb38259cbe7e471171cba574812ef90
17283063936658620016
[42,"market",7,"project-a","demand",1]
f8537aa4ba9526ae8514e3a12583bc12c5ce2f2ff5dabd2973e29641ecc70842
17893780592396674734
```

## K3 — Finance / settlement rules frozen for kernel, not game balance

No default starting wealth/runway is selected here: opening and monthly living
draw are explicit campaign configuration, not inherited $100k or lab$84k.
Public domain.finance functions:
`apply_finance_command(campaign, command) -> (candidate, event_ids, error_code)`;
`settle_day(campaign) -> (candidate, event_ids, error_code)` after day increment;
`finance_summary(campaign) -> dict`. Functional, no revision/receipt changes;
service/tick own those. error_code null on success; error leaves campaign unchanged.
Summary exact keys cash_minor, income_minor, expense_minor, draw_minor,
financing_minor, attributed_labor_minor, runway_days. Expenses/draw totals positive
magnitudes, financing signed; runway_days null if monthly_draw0 else
floor(cash_minor*30/monthly_draw_minor), can be negative (rough estimate only).

Finance kinds (service executes via same transaction/idempotency contract):
- `post_cash`: {category, amount_minor, product_id}; category income/expense/financing.
  Optional outflow cannot make cash<0; incoming may be accepted during negative
  episode. Create next posting with source cmd:command_id, event cash_posted.
  If cash reaches≥0, reset negative_since=null immediately. No negative episode
  can be initiated by this optional command, only mandatory daily settlement.
- `add_obligation`: {obligation_id,due_day,category,amount_minor,product_id}; ID
  unique, due_day>current day, category income/expense/financing signed as K1;
  add unpaid sorted by ID, emit obligation_added. No current cash effect.
- `attribute_labor`: {posting_id,product_id,amount_minor}; require existing expense
  posting, positive amount, unique posting/product pair, summed allocation≤cost.
  Append LABOR; emit labor_attributed, **zero new cash posting/deduction**.
- `cancel_obligation`: NOT AUTHORIZED. Do not implement it or any other finance kind.
  (There are THREE finance kinds; this explicit exclusion prevents free cancellation.)

Daily order: all due unpaid obligations sorted ID, post full signed amounts even
if resulting cash negative, mark paid, one cash_posted event each; then founder
draw. For resulting calendar date with day-of-month n and month length L, founder
charge = floor(monthly_draw*n/L)−floor(monthly_draw*(n−1)/L). No draw on initial
day0; each entered date contributes its known integer share. Zero charge creates
no posting. Source draw:ISO, category draw, product null, cash_posted event.
No real months/events required outside Python calendar/date arithmetic.

After mandatory settlement: if cash<0 and negative_since null, set current day and
emit liquidity_warning. If cash≥0 clear negative_since. Seven consecutive end-day
negative balances close failed/reason insolvent and emit campaign_closed once.
No filesystem action in finance. A blocking project review holds days (and thus
costs) until resolved; there is no deadline passing behind a paused player.
Clock flags cannot create free income. Save/reload preserves current debt episode.
Normal failed campaign is saveable/reloadable but absorbing; opt-in Ironman failed
campaign invalidates only its owned save set under K4. No surprise deletion on I/O.

Mandatory exact witnesses (minor units, not dollars):
- Opening10000, monthly0: income2500→12500; expense−1200→11300;
  financing+5000→16300; financing−2000→14300. Expense total1200, income2500,
  financing3000. Attribute700+500 to two products on p-2 → cash14300 unchanged;
  extra1 allocation fails unchanged. Optional −14301 fails; −14300 yields0.
- Start2031-01-31, monthly60000: entering Feb1 draw2142, Feb2 draw2143;
  all28 February dates total60000. Start2032-01-31, leap-Feb29 totals60000.
  No fractional cents/remainder discarded; batch28==28 single days.
- Opening1000/monthly0, day1 obligations a-income +500 and b-expense−1800:
  postings sorted a then b, cash−300; negative_since1/warning. At day6 running;
  day7 failed (seven entered negative days). Income300 on day6 restores0, clears
  episode; following day solvent. Income299 leaves−1 and failure still day7.
- Same day7 due review and insolvency: consume through day7, stop ended (review
  remains inspectable); no day8. No I/O, no resurrection through business commands.

## K4 — Strict codec and Linux local save safety

Public infrastructure.saves APIs (no migrations.py for v1):
```
class SaveError(Exception): code: str
encode(payload: dict) -> bytes
decode(data: bytes) -> dict
SaveStore(root: pathlib.Path)
  save(payload: dict) -> None
  load(campaign_id: str, source="primary") -> dict
  recover_backup(campaign_id: str) -> pathlib.Path
  invalidate_failed(payload: dict) -> None
```
Canonical JSON = json.dumps(sort_keys=True,separators=(",",":"),ensure_ascii=True,
allow_nan=False).encode("ascii"). Envelope exact:
`{"format_id":"studio-rewrite","schema_version":1,"payload":SNAPSHOT,
"sha256":SHA256(canonical payload).hexdigest()}`. No saved_at/realtime/UI fields.
encode validates complete K1 snapshot, returns canonical envelope bytes (no newline).
decode accepts UTF8 JSON whitespace/key ordering but duplicate keys at ANY nesting,
NaN/Infinity, floating values, non-dict roots, invalid types, unknown fields/versions,
bad digest or failed invariants fail SaveError; payload detached. Max serialized
input/output4MiB. Catch malformed nesting/recursion/UTF8 errors without crashes.
Error codes: `invalid_payload`, `invalid_json`, `unsupported_format`,
`unsupported_version`, `integrity`, `too_large`, `not_found`, `conflict`,
`unsafe_path`, `ownership`, `corrupt_primary`, `ironman_failed`, `io`,
`durability_uncertain`. No eval/pickle/import hooks/default repair.

Root supplied by trusted composition (future distinct `saves_rewrite/`, NOT `saves/`);
tests only TemporaryDirectory under /tmp/opencode. Fixed paths within root/ID/:
`autosave.studio.json`, `autosave.studio.json.bak`, `recovery.studio.json`,
`.lock`, `failed.json`; nothing else caller-addressable. source allowlist primary/
backup/recovery, defaultprimary. No absolute/traversal IDs, symlinks in root ancestry,
campaign directory or named files; reject rather than follow. No broad scan/delete.
Never delete existing primary, backup or recovery to signify failure.

Linux fcntl.flock on permanent .lock file, nonblocking exclusive for save/recovery/
invalidation, shared for load; conflicting lock→conflict. Never unlink lock inode.
Create only trusted root/campaign directories as needed (load notfound does not
create a campaign). Root creation may be constructor; campaign only writes.
Single-application local threat model, not adversarial OS file replacement defense;
still reject known symlinks and never follow a caller-supplied arbitrary path.

Every write: validate completely before touching target; acquire lock; check failure
marker and existing ownership (payload campaign_id matches dir, mode immutable).
If primary exists and corrupt, save fails corrupt_primary without replacing primary
or backup. Existing valid primary may be newer? Incoming revision<primary revision
→conflict; identical revision allowed only identical payload (idempotent no-op),
otherwise conflict. New primary writes canonical bytes to unique tempfile sibling,
flush+fsync+decode verify. If primary valid, write its validated bytes through a
separate unique temp to backup, flush+fsync+verify then os.replace backup and fsync
directory. Only then os.replace new primary and fsync directory. First save need
not create a backup. Never copy corrupt primary over known-good backup. Clean ONLY
temporary files created by this invocation; never destroy unrelated/user files.

Failure before primary replacement leaves old primary intact, and a previously
valid backup stays valid (may now be old primary). Primary-replace failure likewise.
Failure of directory fsync AFTER successful replace cannot promise rollback:
raise durability_uncertain; leave valid new primary and valid old backup for explicit
inspection, never silently claim success or attempt a destructive rollback. Ordinary
write/flush/verification/backup failures →io (or existing validation code). Tests
inject actual os.replace/os.fsync/write failures with stdlib mocks at each stage.
All reads strictly validate; **never auto-fallback** on corrupt/missing primary.
load sourcebackup explicitly returns a validated older snapshot without mutating
files. recover_backup creates `recovery.studio.json` using verified backup through
exclusive-create target semantics; existing recovery→conflict. Primary/backup
unchanged, filename fixed, caller must explicitly select recovered source.

Ironman definitive failure safety: invalidation, not deletion. `save` of failed
Ironman delegates to invalidate_failed and does NOT write a resumable autosave.
Only a valid failed/insolvent Ironman payload may invalidate; normal/running/retired
input rejects invalid_payload. Under exclusive lock verify directory ownership/mode
using existing valid primary or backup if present; marker revision cannot be less
than either valid owned snapshot revision. Corrupt owned files aren't proof of
failure: without at least a validated supplied failed payload never invalidate.
Marker exact {format_id:"studio-rewrite-failure",schema_version:1,campaign_id:ID,
mode:"ironman",revision:INT,day:INT,reason:"insolvent"}; atomic temp/flush/fsync/
replace/directory-sync as above. Existing identical marker idempotent; different
marker conflicts. A valid marker blocks load ALLsources/save/recovery for that
campaign with ironman_failed; malformed marker fails closed with integrity (never
ignore/remove it). Other campaigns and legacy saves untouched. Missing marker plus
failed Ironman autosave supplied externally still must not load as resumable:
load rejects ironman_failed. Normal failed snapshots load for inspection; absorbing
status prevents play. Local offline-copy tampering cannot be made impossible and
is explicitly not a security promise. No cross-campaign ownership manifest/registry
needed: fixed validated campaign directory is the ownership boundary.

## K5 — Frozen minimal fixture and integration witness

Save witness `tests/rewrite/fixtures/rewrite_v1.json` is a canonical envelope for:
campaign_id=`kernel-test`, start_date=`2031-01-31`, seed42, mode normal,
day/revision0, running/null/manual_paused false, counters1, all collections empty,
opening/cash10000, monthly_draw0, negative_since null. No extra fields.
WP-03 authors it from these exact values, not from WP-01 imports. WP-01 must produce
the identical payload from corresponding config. WP-02 end-to-end tests perform
encode/decode/to_payload/from_validated_payload and resumed step/command equality
when WP-03 is available; the cross-package witness is mandatory before M1-kernel
audit, never skipped/claimed passing because a dependency hasn't completed.

Foundation done is **not M1 gameplay done**. A later approved content/loop/API slice
must provide meaningful contract/study/project/release decisions and real browser
active-session enforcement. No synthetic kernel command is exposed as player UI.
