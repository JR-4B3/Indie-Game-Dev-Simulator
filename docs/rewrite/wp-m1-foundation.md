# M1 foundation work packages — authorized 2026-09-11

Authority: user ordered kernel before more UI-lab effort. Astra freezes
[M1-K1](m1-kernel-contract.md), overriding draft WP-01/02/03 entries in roadmap.
References all packages: M1-K1 K0–K5, architecture A1–A3/A5, decisions D1–D6.
Exact contracts take precedence over earlier candidates/lab fixtures.

## Scheduling and shared review rules

UI integration session interrupted through documented session interrupt API after
user reprioritization (`interrupted:true`); files retained, not reset or expanded.
D7b is user's independent rendered review, not a prerequisite for these packages.
**WP-01 and WP-03 dispatch concurrently, strictly disjoint files. WP-02 queues
until WP-01 Sol/Ponytail/final PASS**, then sequentially extends its files while
WP-03 may continue independently. No concurrent writer touches shared code.
One tiny independent WP-KV uses micro-go for mechanical golden-vector fixture/test
materialization; no design discretion or production edits. Larger packages Go first.
No provider fallback except actual matching Go availability/auth/quota/transport
failure. Step exhaustion continues same owner. Sol and Astra remain direct.

Every package: Astra scope/diff + independent commands → Sol (max2 correction
cycles, same Go worker) → explicit ponytail-review skill/senior simplicity review
(max1 justified simplicity rewrite) → final Sol → recorded acceptance. Never count
interrupted reviews or worker assertion counts as acceptance. No commits/reset/revert.
Logs/diffs under `/tmp/opencode/gamedev-m1/<package>/`; tests only temp saves.
Protected full baseline `/tmp/opencode/gamedev-m1/baseline.sha256` and user-before.diff.
Old game stays runnable throughout; a headless kernel is not a replacement UI/CLI.

## WP-01 — Authoritative clock and command boundary

Milestone M1-kernel. Goal/rationale: deterministic functional state boundary before
finance, no implicit wall clock or rejected-command mutation. References K0/K1/K2
and K3 initial finance shape, K5 minimal witness. Status AUTHORIZED.

Exact allowed files:
- studio_sim/__init__.py
- studio_sim/domain/__init__.py
- studio_sim/domain/campaign.py
- studio_sim/application/__init__.py
- studio_sim/application/commands.py
- studio_sim/application/service.py
- studio_sim/application/tick.py
- studio_sim/infrastructure/__init__.py
- studio_sim/infrastructure/randomness.py
- tests/rewrite/test_clock_commands.py

Implement every K2 named API, explicit Campaign fields/full initialized K1 payload,
deep-copy ownership, calendar/day/revision/holds/end/idempotency64, three clock
commands, material event IDs and stateless named SHA256 vectors. Initialize full
finance snapshot without settlement rules (WP-02 owns them). Do not create finance
stubs or imports of nonexistent finance/saves modules. Package __init__ files empty
or docstring only; don't eager-import siblings that may still be under construction.
New_campaign validates config; from_validated_payload copies trusted K1 JSON only.
Reserve K1 finance fields unchanged for next slice. No plugin/transaction framework.

Acceptance:
```
python -m unittest discover -s tests/rewrite -p test_clock_commands.py
python -m compileall -q studio_sim
```
Objective evidence: exact three goldens; bool/NaN/invalid config rejection; input
and snapshots not aliased; day/batch equality across month/year/leap dates; no
query/draw consumption; active/manual/preview/review hold precedence, due0/day3
stop exactly, resolve/retire; all rejection snapshots unchanged; duplicate after
advance/retirement identical receipt and no effect; ID conflict/stale/receipt65
eviction; event/revision/day bounds before partial step. Use explicit dates/seeds.
No finance expectations until WP-02. Worker may read but NEVER edit WP-03 files.

Non-goals: browser/UI/CLI, money settlement, market/projects, saves, wall-clock loop.
Rollback: additive namespace; existing entrypoints/saves unchanged. Reviewer:
functional transactions, original receipt revision, exact K1 serialization shape,
no ignored config fields/hidden default draws, named-source determinism and capacity.

## WP-02 — Auditable cash and obligations

Milestone M1-kernel. Goal/rationale: cash identity, deterministic dated settlements,
cost attribution and warning-before-failure. References K1/K2 extension/K3/K5, G4/G8.
Status QUEUED, dependency WP-01 final acceptance; WP-03 not a write dependency.

Exact allowed files:
- studio_sim/domain/finance.py
- studio_sim/domain/campaign.py
- studio_sim/application/commands.py
- studio_sim/application/service.py
- studio_sim/application/tick.py
- tests/rewrite/test_finance_obligations.py

Service/commands added explicitly to original draft scope so the THREE frozen
finance kinds can use WP-01's real receipt/rejection boundary. No alternate command
service, dynamic plugin registry or monkey-patching required. Preserve K1/K2 API
and payload; add finance functions and within-day sequencing exactly K3.
No changes to infrastructure/saves or clock tests; regressions return to owner.

Acceptance:
```
python -m unittest discover -s tests/rewrite -p test_clock_commands.py
python -m unittest discover -s tests/rewrite -p test_finance_obligations.py
```
Evidence: every exact K3 witness plus sources/posting IDs, income/expense/principal
classification, allocation totals/no second charge, optional-spend rejection,
obligation due/order/paid uniqueness, February28/leap29/fullmonth60000, active-hold
no costs, negative day1→day7 closure, same-day incoming rescue0 versus−1, review
and closure precedence, postclosure no business mutation, transaction capacity and
all money/revision bounds. Save/continuation test in this file must run after WP-03
acceptance; until then report as pending separately (never silently skipped PASS).

Non-goals: player money grants, debt offers, projects/market/tax/recoup/economy tuning,
filesystem invalidation or irreversible deletion. Rollback: additive kernel only;
normal and Ironman end state differ in persistence policy, not financial arithmetic.
Reviewer: exact cent rounding/order, no bypass of command receipt cache, proper
closure warning, transactional mandatory-day settlement, shared schema preserved.

## WP-03 — Strict save and safe continuation

Milestone M1-kernel. Goal/rationale: validated complete snapshots, last-good-copy
protection and campaign-scoped Ironman invalidation before player-time investment.
References K1/K4/K5 exact schema+state machine, A5, D3/D5. Status AUTHORIZED,
parallel with WP-01. **No import dependency on WP-01**; codec is strict dict seam.

Exact allowed files:
- studio_sim/infrastructure/saves.py
- tests/rewrite/test_save_safety.py
- tests/rewrite/fixtures/rewrite_v1.json

No migrations.py: no version transforms exist yet. May mkdir parent directories,
but NEVER create/edit __init__.py (WP-01 owns those). Standard Python namespace
packages work before WP-01 completes. Implement exact K4 names/error codes,
strict nested K1 validation and canonical envelope/digest/size. Invalidation uses
nonresumable failure marker, no save deletion. Functional loads never touch active
Campaign because they return detached dictionaries. No assumptions about lab data.

Acceptance:
```
TMPDIR=/tmp/opencode python -m unittest discover -s tests/rewrite -p test_save_safety.py
python -m py_compile studio_sim/infrastructure/saves.py
```
Evidence: golden fixture exact decode/canonical encode; empty lists stay empty;
all nested unknown/type/bool/float/duplicate/reference/cash/paid/counter/status
failures; unsupported versions, digest/UTF8/nesting/4MiB limits; primary corruption
doesn't clobber backup; verified explicit backup load/recovery-to-new-file; conflicting
process lock; malicious paths/symlinks; wrong campaign/mode/revision conflict;
write/flush/fsync/temp verify/backup/primary-replace/final-directory-sync faults,
valid copies retained and durability_uncertain distinguished. Normal failure reload
inspectable; valid Ironman marker blocks all sources, corrupt marker fails closed,
idempotent same marker, other campaign/legacy sentinels byte-identical; I/O error
alone NEVER infers failure. Use real temp files and mock specific low-level faults,
not just mocks claiming save calls occurred.

Non-goals: legacy conversion, CLI, cloud, arbitrary user paths, compression,
tamper-proof offline copies, migration registry, autosave scheduling/browser.
Rollback: distinct caller-supplied root and validated extension; no real saves opened
for write. Reviewer: decoder semantic completeness, lastvalidbackup, original
preservation, explicit commit-point failure semantics, no directory sweep/delete.

## WP-KV — tiny mechanical contract/test materialization

Milestone M1-kernel. Worker micro-go. Independent/disjoint from WP-01/03.
Goal: machine-readable golden values and stdlib witness of the frozen algorithm;
NOT authority to choose a random protocol. Exact reference K2 three vectors.
Allowed ONLY:
- docs/rewrite/fixtures/m1-random-vectors.json
- tests/rewrite/test_m1_contract_vectors.py

JSON object {"protocol":"studio-rng-v1","vectors":[{"args":LIST,"sha256":HEX,
"u64":INT}, ...]} copies the three exact K2 rows in order. Small unittest reads
file relative to __file__ (repo root via parents[2]), verifies length3 and for each
SHA256 of json.dumps([protocol]+args,separators=(",",":"),ensure_ascii=True,
allow_nan=False).encode("ascii"), first8bytes big-endian equals supplied u64.
No production imports, dependencies, runtime edits or additional vectors.
Acceptance `python -m unittest discover -s tests/rewrite -p test_m1_contract_vectors.py`.
Evidence exact literal vectors, test output and two-file diff. Non-goals statistical
quality, design changes, framework. Rollback additive fixture/test only. Reviewer
compare every supplied hash/integer with K2; no tautological regenerated expected data.

## Kernel boundary audit (after all packages accepted)

Run all rewrite tests together (no skips), then existing stdlib game suites per
inventory; compare protected source/save hashes. WP-02 must prove cross-codec
continuation of commands, receipts, negative episodes and day/batch equality.
Audit domain→application→infrastructure dependency direction, no UI dependency,
schema compatibility/no divergence, seeded vectors, money identity and safe failure.
Only then kernel exists as an accepted foundation; no claim M1 playable release
loop or D7b approval. Resume UI work only per user's new priority after this boundary.
