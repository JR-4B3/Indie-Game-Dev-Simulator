# Variant 3 — Board Map (WP-UI-01V3)

Disposable prototype, not production UI and not a selected visual direction. This
directory is the entire variant: `variant.js`, `variant.css`, `README.md`. Shared
foundation files (`shared.js`, `shared.css`, `harness.*`, `check.cjs`,
`fixtures.js`) are read-only and were verified unchanged against
`/tmp/opencode/gamedev-ui-parallel/shared-frozen.sha256`. No other variant
directory was touched.

## What makes this treatment different

Board Map replaces page/tab navigation with **one spatial relationship board**
plus a **persistent focus lens**:

- The left side is a fixed board of entity nodes — Studio (Northstar Works),
  Support (Paper Harbor), the active project (Signal Drift), People (Mina Rao),
  Outcome (Paper Harbor postmortem) and Systems (Capabilities) — plus three
  evidence nodes (newcomer stall, fan depth, integration estimate).
- Dashed **edges** expose the relationships (`decision`, `competes`,
  `evidence`, `lead`, `outcome`) rather than presenting routes as a menu.
- The right side is the **focus lens**: the current node's shared content pieces
  (summary, studio, signals, findings, responses, preview, actions, history,
  person, support, postmortem, capabilities) rendered through the shared
  `part()` API. The lens is a layout column, never an overlay, so it cannot
  cover the board.
- There are **no pages, tabs or route list**. Navigation is selecting a node;
  the board stays visible while the lens changes.

The node subtitles are live reads of shared state: the Studio node shows the
current plan's cash, the active-project node shows phase, 60% baseline work, an
inline 60% work meter and the derived decision status (`Open — no response
committed`, `Deferred — revisit before validation`, `Rejected — original risk
remains`, `Committed`). No status is hard-coded and the words "decision pending"
are never rendered.

## Interaction and keyboard

- **Pointer**: click any board node, a response card, preview/confirm/defer/
  reject/reopen, or a capability list item. All controls are native buttons.
- **Enter / Space**: activate the focused native button (map node, lens control,
  response, capability). No custom key activation is required.
- **Arrow keys on the board**: when focus is on a board node, ArrowUp/
  ArrowDown/ArrowLeft/ArrowRight move focus to the nearest node in that
  direction using real geometry (compact grid at narrow widths, absolute board
  on desktop). The listener is attached to the map canvas element only; it is
  not a window/document handler and cannot hijack inputs elsewhere. While a node
  has focus, arrows are consumed by the board instead of scrolling the page.
- **Tab**: reaches every board node, the "Jump to focus lens" button, and then
  the lens contents (responses → preview controls → actions → history →
  capabilities) in DOM order. The focused `view-title` heading is at the start
  of the lens, so after opening a node the next Tab already reaches its content.
- **Jump to focus lens** (button, top of the board): re-opens the current node
  in place and moves focus to the lens heading. This is the short keyboard path
  at narrow widths where the compact board sits above the lens.
- **Narrow behaviour** (`max-width: 1180px`): the absolute canvas becomes a
  static auto-fit grid, edges/labels are hidden, and the lens moves into normal
  flow. There is no canvas to pan and no horizontal overflow; critical actions
  are reachable by Tab without panning to them. At a 390px viewport the game
  surface is 278px wide and the flow above still holds.

## Workflow demonstrated (same fixtures, same reducer effects)

1. Overview lens: studio condition, people, cash/runway, decision summary and
   the Paper Harbor obligation link.
2. Active-project node: pillars, phase (Production), colored 60% baseline work
   bar, readiness (At risk, categorical), finish estimate, scope baseline.
3. Evidence nodes open the same project context; findings show categorical
   Supported/Tentative shapes with source, sample/limitations and date/history —
   no numeric odds.
4. Select a response → Preview compares baseline vs proposed cash, estimate,
   scope, spend and residual tradeoff with no state change; Cancel closes it.
5. Confirm commits once (cash/runway/estimate/scope update, history records it);
   Defer and Reject change no money and require Reopen before any new decision.
6. People / Support / Outcome / Systems nodes inspect Mina Rao, the Paper Harbor
   promise, the qualified postmortem and the capability graph with its
   keyboard-readable list (inspection only).
7. HUD (paused label, 18 May 2031, cash, runway) is present on every node.

## Run and evidence

```
node --check prototypes/studio-lab/variants/3/variant.js
NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules \
  node prototypes/studio-lab/check.cjs --variant 3        # own server port 18783
```

Evidence directory: `/tmp/opencode/gamedev-ui-parallel/variant-3/`.

- `check.log` — official checker result (all shared workflow, guards, keyboard,
  geometry, screenshot and unavailable-route assertions).
- Seven checker screenshots: `overview-desktop`, `project-desktop`,
  `preview-desktop`, `graph-desktop`, `project-narrow`, `signals-narrow`,
  `preview-narrow`.
- `own-map-keys-test.cjs`, `own-map-keys.log`, `own-map-keys-desktop.png`,
  `own-map-keys-narrow.png` — extra V3-specific probe run by this worker on the
  same port (sequentially): geometric ArrowRight/ArrowDown focus movement with
  no surface scroll, Enter/Space activation of nodes, 278px game width with no
  document/surface horizontal overflow, static (non-pannable) narrow board, Tab
  reachability of `open-project` and `response-simplify` critical actions, and the
  jump-to-lens focus move.

This README claims no winner and no production readiness; it records only what
the disposable prototype does and which evidence files exist. The capability
graph SVG is small at 278px game width — the shared keyboard-readable list is
the accessible inspection path there. Prototype state resets on reload; the
variant writes no storage, network or game files.
