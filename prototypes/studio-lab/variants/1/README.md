# Variant 1 — Ops Deck (disposable prototype)

This directory is one isolated candidate in the WP-UI-01 five-variant lab. It is a
disposable prototype, not a production screen and not a selected winner. It talks to
the frozen shared core (`../../shared.js`, `../../fixtures.js`) and owns only its own
three files: `variant.js`, `variant.css`, `README.md`.

## Treatment

Persistent three-pane operations deck around one shared state:

- **Entity spine (left)** — every route as a native button with a status LED, label
  and dynamic meta line (e.g. Signal Drift shows `decision open`, `comparing`,
  `plan committed`). The selected entity is marked with `aria-current` and a yellow
  notch. It sticks beside the focus deck while the deck scrolls above 700px viewport
  width and scrolls normally in the single-column narrow layout.
- **Focus deck (centre)** — a DECK breadcrumb, the `view-title` heading (the shared
  mount moves focus here after navigation) and numbered plates that make the decision
  order explicit: `01 Decision desk → 02 Telemetry → 03 Evidence → 04 Response options
  → 05 Commit controls → 06 Decision ledger`. A narrow screen keeps the same order and
  all controls visible; nothing becomes hover-only.
- **Ops readout (right)** — decision-status lamp, status-aware Evidence → Compare →
  Decide pipeline, plan lineage (`baseline ▶ proposed` for cash, finish, scope,
  runway), committed readout, project pulse (colored segmented phase track and
  baseline work bar), categorical confidence key and decision log. It is sticky
  beside the deck above 1180px viewport width; below that it becomes a full-width
  panel under the deck and scrolls with the page, so it is not always on screen.
- **Pixel character** — chunky 2px frames, offset hard shadows, pixel grid backdrop
  and inline `shape-rendering="crispEdges"` pixel marks (brand star, personnel
  portrait, paper-boat, outcome chart, node grid). No external assets, no blurry
  scaling, no invented numeric precision.

Overview shows the open decision first, then studio identity/audiences/people, plus
telemetry, an evidence watch and the Paper Harbor obligation card. Project is the full
decision workspace. Person, product, postmortem and capabilities reuse the shared
parts inside the same deck frame.

## Keyboard

Shared workflow keys (owned by `mount`): `Tab` between controls, `Enter`/`Space`
activate, preview moves focus to Cancel, cancel returns to Preview, confirm/defer/
reject/reopen move focus to the result/reopen as contracted.

Ops Deck additions, all handled by a listener scoped to the variant root:

- In the entity spine: `ArrowDown`/`ArrowRight` and `ArrowUp`/`ArrowLeft` move focus
  between entities, `Home`/`End` jump to the first/last. Focus moves only; shared
  state is unchanged until `Enter` opens the entity.
- Decision shortcuts on any view, but only while focus is **not inside an interactive
  control** (buttons, links, inputs, contenteditable and common widget roles are
  excluded): `1` Simplify branching, `2` Build guided introduction, `3` Keep current
  plan; `p` preview, `Escape` cancel preview, `c` confirm, `d` defer, `r` reject,
  `o` reopen. Focus the view heading or the deck root to use them. The shared reducer
  still guards every action, so shortcuts are no-ops when the decision is not open or
  the required selection/preview is missing. Native `Enter`/`Space` activation of
  focused controls and the spine `Arrow`/`Home`/`End` focus movement are unaffected.

## Run and verify

From the repository root:

```
node --check prototypes/studio-lab/variants/1/variant.js
NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules \
  node prototypes/studio-lab/check.cjs --variant 1
```

Manual launch (static server only):

```
python -m http.server 18770 --bind 127.0.0.1 --directory .
# http://127.0.0.1:18770/prototypes/studio-lab/harness.html?variant=1
```

The shared checker starts its own server on port 18781 (variant 1), passes with
`PASS — 323 checks`, and writes evidence to
`/tmp/opencode/gamedev-ui-parallel/variant-1/`:

- `check.log` — pass log.
- `overview-desktop.png`, `project-desktop.png`, `preview-desktop.png`,
  `graph-desktop.png` — 1440×900.
- `project-narrow.png`, `signals-narrow.png`, `preview-narrow.png` — 390×844.
- `overview-1024.png`, `project-1024.png` — extra 1024×768 captures.
- `overview-narrow.png` — extra narrow capture.
- `deferred-desktop.png`, `rejected-desktop.png`, `committed-desktop.png` and
  `deferred-narrow.png`, `rejected-narrow.png`, `committed-narrow.png` — non-open
  states showing the status-aware pipeline/lineage/readout/focus-note text.
- `unique-nav.log` — result of the variant-specific regression probe
  (`/tmp/opencode/gamedev-ui-parallel/variant-1/unique-nav-probe.cjs`, port 18799):
  102 checks covering key suppression inside every interactive control (no state
  changes; preview stays open with Cancel focused), native `Enter`/`Space`, spine
  `Arrow`/`Home`/`End` focus movement without state mutation, shortcuts from the
  heading/root, and status-aware text for open, selected, preview, cancel, defer,
  reject, reopen and all three commits (baseline cash untouched until Confirm).

All of the above screenshots were read back by the worker; the first pass fixed
duplicated plate/heading wording, truncated narrow meta and brand subtitle, and an
over-bright disabled Confirm. The Sol correction pass removed shortcut hijacking of
focused controls and made pipeline/lineage/readout text status-aware for
deferred/rejected/committed states (see the non-open captures).

## Limits

- No storage, feedback, network, timers or global listeners; no fixture or reducer
  logic is duplicated here.
- Readiness stays `At risk — follow-up validation needed`; no success is invented.
- Rollback: delete this directory; nothing outside it is imported or modified.
- This README claims a passing checker and inspected screenshots only — it does not
  select this direction or claim production approval.
