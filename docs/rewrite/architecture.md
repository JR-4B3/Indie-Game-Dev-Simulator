# Target architecture A0.1 — direction approved D6; M1 kernel contracts frozen

M1 foundation is now authorized independently of D7b. [M1-K1](m1-kernel-contract.md)
freezes functional Campaign/command/day APIs and an independent strict dictionary
save codec. WP-01 and WP-03 can write disjoint files concurrently; WP-02 extends
commands/service/tick sequentially after WP-01. No frontend or legacy dependency.
Full project/market/browser contracts below remain future-slice candidates.

## A1 — Small local application, one authoritative simulation

Recommended runtime: Python 3.10+ standard library (minimum-version claim requires
testing), dataclasses, explicit application commands and pure player projections;
browser is locally served HTML/CSS/JavaScript with bundled assets. Retain native
SVG/CSS for charts and the capability graph, not a frontend framework or canvas-only UI.
No async task framework, generalized ECS, plugin bus, DI container, event sourcing,
microservices or database service. A local single-writer server is sufficient.

Proposed new namespace, coexisting with the prototype:

```
studio_sim/
  domain/
    campaign.py       # calendar, identity, aggregate ownership, campaign status
    projects.py       # lifecycle, work plan, quality and technical state
    people.py         # skills, traits, time allocation, condition, learning
    market.py         # products/listings, finite cohort acquisition and experience
    finance.py        # monetary postings, obligations, product attribution
    evidence.py       # observations, provenance, knowledge and causal references
    capabilities.py  # validated prerequisite graph and operating capabilities
    operations.py    # live lifecycle, initiatives and delegated policies
  application/
    commands.py       # typed command/result vocabulary
    service.py        # validation/commit boundary, revisions, single writer
    tick.py           # authoritative day orchestration, stopping at decisions
    queries.py        # pure knowledge-aware projections, explicit query inputs
  content/
    rules.py          # reviewed named/versioned constants, initial typed content
  infrastructure/
    randomness.py     # stable named deterministic draw protocol
    saves.py          # strict codec and crash-safe local persistence
    migrations.py     # explicit new-save migrations, no legacy guessing
  adapters/
    browser.py        # local HTTP transport, controller lease, session holds
  __main__.py         # composition/launch; not a home for game rules
studio_web/
  index.html, app.js, style.css    # first approved slice only; split by real feature later
tests/rewrite/
  ...                 # contract, system, scenario, browser and save safety tests
```

This is the target ownership map, not an instruction to create empty modules now.
Extract files only when their first approved vertical slice needs them. Avoid
replacing the old monolith with a new generic service full of every business rule.

## A2 — Dependency rules

- Domain imports standard library and other explicitly owned domain value types,
  never adapters, filesystem, wall clock, HTTP, curses or UI state. No global RNG.
- Cross-domain effects are explicit typed results applied in application tick/command
  order, not hidden callbacks or side effects from rendering. Shared IDs/money
  primitives move to a tiny value module only if actual dependencies require it.
- Application owns canonical mutation/commit order and asks domain systems to
  calculate effects. It receives the active rules and random source; it does not
  import browser/terminal adapters or construct filesystem services.
- Queries receive campaign knowledge and return display-neutral typed DTOs; they
  do not cache by mutating campaign, consume RNG or advance time.
- Infrastructure implements random/save contracts and imports domain schemas;
  domain does not know about infrastructure. Composition supplies implementations.
- The browser adapter translates transport/input into application commands and renders
  projections. No market, cost, gating, prestige or outcome formulas in production JS.
- Content is validated at startup for stable IDs, valid references, meaningful
  prerequisites and acyclic capability dependencies. Labels never serve as IDs.

## A3 — Tick design

Daily quantum; proposed weekly cohort shopping aggregation and monthly settlements
occur at explicit calendar boundaries inside that day. Start-date, campaign seed,
ruleset and simulation version are inputs, not wall-clock defaults in the engine.

Proposed within-day order: due obligations/commitments → snapshot available labor
and policies → allocate/reserve capacity → perform work/learning/support → resolve
new product state/incidents/releases → market/experience transactions → settle cash
and employee effects → form observations/escalations → evaluate solvency/status.
Payments have explicit deadlines; no subsystem gets extra labor because it runs
first. Precise same-day release/settlement/closure rules must be frozen for M1.
Advance(n) is exactly repeated single-day stepping, stopping after the first
blocking decision or campaign end and reporting consumed days. Interpolation is
presentation only; hidden/inactive/closed/disconnected controlling browser produces
no offline catch-up. Week-based reports do not restrict when the player can act.

## A4 — Frontend support decision: browser only (approved D4)

| Option | Benefit | Cost / limitation |
| --- | --- | --- |
| Full browser/terminal parity | Both equally playable, strongest portability | Every feature needs two interaction designs, high QA burden, graph/spatial compromise |
| Browser primary; secondary terminal (recommended) | Browser can serve deep visuals; terminal retains headless/replay/reporting value; legacy TUI remains runnable | Define terminal subset honestly; not a promise of new-game interactive parity |
| Browser only for replacement | Lowest frontend burden, clearest UX scope | New-game terminal play is lost; needs explicit retirement approval; still keep non-UI scenario runner |

The table records prior alternatives, not current scope or a new scenario-runner
CLI commitment. User selected browser
only: no replacement terminal, interactive CLI, reporting/replay CLI or terminal
parity work. Internal tests may call the engine directly; they are not a second
player frontend. Preserve existing `main.py` and user work during migration, but
do not spend new effort developing the old or a replacement CLI.

## A5 — Migration and rollback

Approved: a **parallel product path with vertical slices**, not an in-place blend
of incompatible game economies. Existing entrypoints, files and saves remain intact.
New entrypoint/namespace and new save directory are opt-in. Build one small complete
release loop, then grow that proven loop with people, markets and portfolio systems.
The old game remains playable at every intermediate boundary.

Approved D3: no legacy compatibility, economic conversion or museum/history importer.
New game means new campaigns. Existing saves/files remain untouched as protected
user data; unsupported files are rejected without mutation. New-format migrations
remain necessary for future rewrite schema versions, not for version 11.

At cutover, audit cold start, complete campaigns, advanced scenarios, save recovery,
frontend scope, access, balance and documentation; user explicitly approves default
entrypoint change. Keep the prior version launchable. Rollback selects the old
entrypoint and old saves, **not** reverse-migration or resetting user changes.
Preserve new saves on rollback and clearly state which ruleset can reopen them.
No dual writing to legacy and new saves; no automatic cleanup of either.
