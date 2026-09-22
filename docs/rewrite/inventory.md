# Prototype inventory and characterization

Observed 2026-09-10 on branch `game_developemnt`, HEAD `a52123a`.
This describes the **dirty working tree**, not just HEAD.

## Protected work

Existing modified files: `README.md`, `browser.py`, `test_browser.py`,
`web/app.js`, `web/browser-smoke.cjs`, `web/browser-views.cjs`, `web/index.html`,
`web/style.css`, `web/views.css`, `web/views.js`.
Existing untracked work: `.opencode/`, `opencode.jsonc`,
`web/browser-operations.cjs`, `web/operations.css`, `web/operations.js`.
Tracked diff at entry: 10 files, 491 insertions, 322 deletions.
No `docs/rewrite/` existed. Existing five save/backup files were hash-checked.
External discovery evidence is in `/tmp/opencode/gamedev-rewrite-discovery/`:
`user-before.diff`, `protected-work.sha256`, `saves-before.sha256`, test logs and
screenshots. Temporary evidence is not a permanent backup or commit.

## System map

| Area | Observed implementation | Reuse judgment |
| --- | --- | --- |
| Engine | `simulation.py`, 6,037 lines; entities, actions, time, rules, forecasts and persistence | Reference, not replacement kernel |
| State | `Studio` and `GameState`; domain, plan selections, cursor, modal, clock, saves intertwined | Replace shape and ownership |
| Pipeline | `start_concept_project`, `start_experiment`, `begin_design_review`, `commit_design_plan`, `develop_project`, release | Preserve evidence/commitment idea; redesign rules |
| Market | `sim_core/market.py:allocate_weekly_demand`; explicit offers, macro snapshot, seed, finite cohorts, outside option | Strong boundary and invariant ideas; verify end-to-end conservation |
| Products | `sim_core/products.py`; monetization, announcement and support tables | Vocabulary/reference, not fixed balance |
| Finance | `sim_core/finance.py`; transactions, P&L, commitments/runway with duck-typed schemas | Preserve accounting distinctions; remove competing sources of truth |
| Evidence | `sim_core/ideas.py`, `sim_core/events.py`; findings, IDs, bounded event history | Preserve causal intent, not loose dictionaries/UI coupling |
| Terminal | `main.py`, `ui_input.py`, `ui_chrome.py`, `ui_*.py`; curses/keyboard/mouse/geometry | Keep legacy runnable; reuse real-terminal test strategy |
| Browser | `browser.py:BrowserGame`, stdlib HTTP server; `web/` plain local JS/CSS/SVG | Keep offline delivery, local font, keyboard support, pause safeguards |
| Content | `game_data.py`, tables in simulation/core | Audit each rule; avoid inherited binary genre/theme recipes |
| Saves | `state_to_data`, `state_from_data`, `save_game`, `load_game`; exact version 11 | Preserve files; do not silently reinterpret into new mechanics |

## Current UX inspected

Exercised existing Chromium flows: new campaign, pause/speed, ideas, experiment,
design review and commitment confirmation, applicants, research, contracts,
statistics, post-release update/marketing/community/support/pricing.
Populated layout fixtures are explicitly synthetic; they are layout evidence,
not evidence of natural late-game balance. Terminal geometry was exercised by
the existing PTY test, not by a manual long-running campaign.

Inspected images include Studio 1440×900, design picker, People 1440×900,
Projects 1440×900 and 390×844, applicants 390×844, and operations detail.
Good: recognizable dark navy/lavender, yellow actions, green results, readable
monospace, phase rail, local charts, persistent time, keyboard paths, focused
dialog controls. Weak: fixed-height empty panels, text truncation even on desktop,
context displaced into modal forms, evidence visually separated from the choice
it should inform, uniform project measures, extremely compressed navigation and
reduced evidence on narrow screens. Geometry passing is not usability approval.

## Verified baseline

Environment: Python 3.14.7, Node 24.18.1, isolated Playwright 1.63.0 with cached
Chromium. The connected browser tool reported no desktop connection; existing
Playwright browser checks were used instead. No project dependency was added.

```
TMPDIR=/tmp/opencode PYTHONDONTWRITEBYTECODE=1 python -m unittest test_simulation test_version10 test_browser
# 147 tests, 34.354 seconds, OK
NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules node web/browser-smoke.cjs
# PASS: four viewports, experiments, keyboard, dialogs, design/time/pause
NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules node web/browser-views.cjs
# PASS: populated workspaces at four viewports, generated ledger/market charts
NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules node web/browser-operations.cjs
# PASS: release metrics, updates, marketing/community, support, price, charts
```

Python persistence tests use disposable paths. The smoke script creates an
in-memory new campaign and never saves/loads the default file; views/operations
use disposable paths. A separate temporary discovery server was stopped cleanly.
Existing save hashes and the tracked diff remained unchanged after checks.
This is one baseline run, not a balance certification or minimum-Python-version test.

## Static risks to investigate, not asserted test failures

- `GameState` construction repopulates empty team/applicants/contracts/rivals;
  load is therefore not necessarily an exact restoration of intentional emptiness.
- Save fields include positional indexes and display names; version 11 only,
  no migration pipeline, limited validation. Atomic final rename exists, but
  durability, backup failure, recovery, and concurrent writers lack guarantees.
- Calendar defaults use import-time `date.today()`; seed alone is insufficient.
  Callers advance clocks separately from `process_day`; batch equivalence is not
  demonstrated. Browser's day-at-a-time loop already mitigates some cases.
- `market_report` query caching depends on an incomplete signature and feeds
  planning. Rendering/queries should not change future simulation results.
- Finite weekly allocation is not end-to-end purchase conservation: launch,
  Early Access and daily sales have separate paths; cross-store ownership and
  Early Access → 1.0 ownership transfer need probes.
- Cash, transaction, monthly ledger and product cost attribution can diverge;
  tax deduction in `close_month` bypasses transaction recording.
- Event history is bounded, important actions sometimes only log text, and
  project references sometimes use titles instead of stable IDs.
- Terminal rendering mutates selections; save-picker drawing can create a
  directory. Closed-studio Enter deletes the current save, and other keys are
  swallowed. Characterize separately; recommend non-destructive replacement.
- Browser view serializes the full studio; replacement must project knowledge
  deliberately rather than leak hidden facts. Actions use indexes and some
  failed commands can partially mutate state. HTTP-level security/failure tests
  are thinner than `BrowserGame` tests.

## Characterization strategy

Keep **legacy observations** separate from **new required invariants**. A known
prototype inconsistency must not become a required new rule merely via a golden file.

1. Freeze explicit start date, seed, rule identity, scripted choices, representative
   initial/phase/release/live/insolvency states. Use JSON encoding, not aliasing
   `state_to_data` dictionaries.
2. Record save round-trip and future continuation, intentional emptiness, invalid
   versions and malformed payloads. All file/fault tests under disposable paths.
3. Probe single-day versus batched stepping, month/quarter boundaries, decision
   stops, closure, and repeated projections. Label observed differences as risks.
4. Verify money/loan/refund/recoup/hosting identities, cross-store acquisitions,
   Early Access transition, ownership, unique users versus purchases, rival demand.
5. Characterize terminal key/mouse/pause/resize/closure and browser disconnect,
   focus, rejected action, repeated command, save and reconnect behavior.
6. New-engine tests: unit and scenario tests, deterministic command replay,
   serialization continuation, conservation, state transition guards, information
   disclosure, causal explanations, and seeded multi-campaign balance experiments.
7. Run baseline on supported Python versions before claiming support. Establish
   timing/memory/long-save budgets from benchmarks, not invented limits.
