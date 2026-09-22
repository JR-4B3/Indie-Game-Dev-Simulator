# Variant 4 — Timeline Table (WP-UI-01V4)

Disposable prototype for the controlled UI lab. Not production, not a selected
direction, not a sixth candidate contract. Fixture state resets on reload; this
variant stores nothing and chooses no winner.

## Treatment

A fixed-epoch commitment agenda. The clock is an epoch (`18 May 2031`, time
paused), never a running timeline, so temporal information is inspection only:

- A six-lane table is the navigation and the hierarchy: Studio, Signal Drift,
  Mina Rao, Paper Harbor (support obligation), Paper Harbor postmortem and the
  capability ledger. Clicking a lane opens that record below; the current lane
  keeps a yellow left rule and `aria-current`.
- Each lane is a categorical record, not a proportion or gauge. The Studio lane
  derives cash, runway and plan from `planOf(state)`, so it follows the shared
  reducer after a commit. The Signal Drift lane keeps the single fixture-owned
  proportional visual (`60% of baseline scope`, denominator in its own label)
  and states its finish window as text. The promise (`by 2 June`), the reserved
  `1 engineer-week` obligation and its opportunity cost, the recorded
  planned/actual postmortem schedule and the inspection-only capability ledger
  are text records and chips.
- The header line is a neutral `Decision agenda`, derived from shared state:
  the fixture wording (`Unresolved onboarding decision`) appears only while the
  decision is open; after commit/defer/reject it shows `planOf(state).label`
  plus `statusText(state)`, with no stale open/unresolved contradiction.
- Selecting a response only highlights its option record in the decision
  window; records change through shared decision transitions (commit, defer,
  reject), never from a draft hover or selection.
- The project record contains a decision window: recorded evidence dates
  (12/15/17 May) with categorical confidence shapes, a `18 May 2031 · TODAY`
  marker, and the three option estimate ranges as text. No exact future dates
  are shown, and no odds or proportional width are invented.

No week scrubber, no week turning, no time advancement, no new scheduling
actions, no economy changes. All reducer effects remain the shared ones.

## Real interaction differences from the other directions

- Navigation is a table of commitment lanes rather than a spine (Ops Deck),
  a chapter/document flow (Field Notes), a spatial node board (Board Map) or a
  command stream (Command Board).
- Arrow keys walk the lane rows (root-local listener, no global handlers):
  `ArrowDown`/`ArrowRight` next lane, `ArrowUp`/`ArrowLeft` previous lane,
  `Home`/`End` first/last, with wrap-around. `Enter`/`Space` opens a lane
  through the shared mount's `[data-action]` delegation and focuses the
  visible `view-title` heading.
- The record desk composes the frozen shared content pieces; it does not
  duplicate reducer, fixture or feedback logic.

## Keyboard instructions

1. `Tab` reaches the lane table (`open-overview` first).
2. `ArrowDown`/`ArrowUp` (or `Left`/`Right`) move between lanes; `Home`/`End`
   jump to the first/last lane.
3. `Enter` or `Space` opens the focused lane.
4. In Signal Drift: `Tab` to a response button, `Enter`/`Space` selects it;
   `Tab` to `Preview response` and `Enter` opens the comparison; `Cancel
   preview` returns focus to `Preview response`; `Enter` on `Confirm` commits
   and focuses `decision-result`. `Defer`/`Reject` focus `Reopen decision`;
   reopening focuses the result region. After a commit the responses and
   decision buttons are disabled until the fixture is reset.

## Acceptance commands and results

```
node --check prototypes/studio-lab/variants/4/variant.js
# -> OK

NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules \
  node prototypes/studio-lab/check.cjs --variant 4
# -> PASS — 323 checks on the final rerun, port 18784,
#    evidence in /tmp/opencode/gamedev-ui-parallel/variant-4
#    (322 on the first run; the unavailable-variant probe gains one
#    assertion when sibling variant 1 is present in the workspace)
```

The shared checker covers the full P2 workflow, exact response effects,
guards, invalid actions, real Tab/Enter/Space flow and focus ownership, and
1440×900 / 1024×768 / 390×844 geometry without page horizontal overflow.

Own Playwright self-review (script kept in `/tmp`, not committed; run on the
initial implementation before correction 1) additionally exercised the unique
lane keyboard navigation. 25/25 assertions passed:
`Tab` → `open-overview`; `ArrowDown`/`ArrowUp` walking and wrap-around;
`End`/`Home`; `Enter` navigation focusing `view-title`; arrow navigation
surviving a rerender; keyboard `Space` select → preview → `Enter` confirm
(HUD `Cash $72,000`); product/postmortem route content; at 390×844 all six
lane buttons visible (244px wide), document overflow `390 = innerWidth 390`
and zero spill inside the 278px game surface; no console or page errors.

Sol REWRITE correction 1 was verified with a separate temp Playwright probe
(`/tmp/opencode/gamedev-ui-parallel/regression-v4.cjs`, not committed):
`REGRESSION PASS — 264 assertions for correction 1`, covering
`planOf(state)`-derived Studio lane after all three commit outcomes and return
to overview; the derived decision agenda for open/deferred/rejected/committed
with no stale `Unresolved` title; exactly one proportional lane visual (the
fixture 60% work bar) with all arbitrary-width tone classes and option fills
gone; focus-heading geometry under real `Enter`/`Space` navigation for all six
routes at 1440×900 / 1024×768 / 390×844 in both scroll directions, asserting
the heading rect and its computed outline width/offset stay below the sticky
HUD and inside the viewport; and the document/surface no-overflow guard.

Correction 2 (final) replaced the overview subtitle with the exact neutral text
`Studio condition and the current decision record.` The same probe now reports
`REGRESSION PASS — 276 assertions`, including exact-subtitle checks while open,
deferred, rejected and after all three commits, and confirmation that the old
phrase `open decision before any commitment` is absent on every route. The
committed overview desktop/narrow captures (`reg-overview-committed-desktop.png`,
`reg-overview-committed-narrow.png`) were refreshed from this run and inspected.

Shared frozen baseline was verified untouched:
`sha256sum -c /tmp/opencode/gamedev-ui-parallel/shared-frozen.sha256` matches
for all six accepted files.

## Screenshot evidence read

Checker captures (`/tmp/opencode/gamedev-ui-parallel/variant-4/`):
`overview-desktop.png`, `project-desktop.png`, `preview-desktop.png`,
`graph-desktop.png`, `project-narrow.png`, `signals-narrow.png`,
`preview-narrow.png`.

Own captures (`/tmp/opencode/gamedev-ui-parallel/variant-4/`):
`self-project-top-desktop.png`, `self-project-committed-desktop.png`,
`self-overview-narrow.png`, `self-project-selected-narrow.png`,
`self-product-desktop.png`, `self-postmortem-desktop.png`,
`self-person-narrow.png`.

Correction-1 captures (`/tmp/opencode/gamedev-ui-parallel/variant-4/`):
`reg-overview-desktop.png`, `reg-project-desktop.png`,
`reg-overview-committed-desktop.png`, `reg-overview-committed-narrow.png`,
`reg-project-narrow.png`.

All of the above were inspected with image input; the correction captures show
the committed Studio lane (`$72,000 / 6.0 months`), the derived
`Decision agenda: Build guided introduction · Committed`, categorical lane
records, no option fills and the single 60% work bar. A blanket "no clipping"
claim is not made from images alone: heading-outline clearance, no stale title,
record removal and overflow are the explicit probe assertions above.

## Scope

Only these files exist for this variant:

- `variant.js` — `metadata = {id: 4, name: 'Timeline Table', description}` and
  `render(state, dispatch)` returning one
  `.variant-4[data-variant="4"]` root; imports `F`, `el`, `part`, `planOf`,
  `statusText` from `../../shared.js`.
- `variant.css` — everything scoped under `.variant-4`.
- `README.md` — this file.

Non-goals: shared/controller/fixture/checker edits, storage, network,
production integration, feedback UI (integration owns it), extra mechanics.
