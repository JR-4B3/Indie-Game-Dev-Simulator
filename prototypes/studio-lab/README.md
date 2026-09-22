# Studio Lab — five disposable UI prototypes (WP-UI-01I integration)

This folder is a **disposable, static review lab** for the decision-centered studio
workspace. Five accepted interactive renderers share one fixture/state seam and one
fixed right review rail; the rail switches between them and carries local feedback.
It is **not production UI**, **not a simulation**, **not a save format**, and **not
an approved visual direction**. No winner is chosen here; only the user selects or
combines a rendered direction, and this integration itself is still pending Astra/Sol
review gates.

All state in this lab is illustrative fixture state frozen by `docs/rewrite/wp-ui-00.md`.
Nothing here writes a game save, calls an API, loads a network asset, or changes any
production entrypoint.

## Architecture (accepted seams, read-only)

- `fixtures.js` — frozen fixture values, loaded as a classic script before modules.
- `shared.js` — `F`, `createState`, `planOf`, `statusText`, `reduce`, `el`,
  `part(state, name)` and `mount(surface, renderer)` with
  `setRenderer/getState/dispatch/reset/destroy`. One state object; renderers read it
  and never mutate it.
- `shared.css` + `variants/N/variant.css` — shared content pieces, then five scoped
  candidate styles. `lab.css` adds shell-only rail/chrome rules.
- `variants/N/variant.js` — each candidate exports `render(state, dispatch)` and
  `metadata`. `index.html` loads shared CSS, all five candidate styles, then `lab.css`,
  and `lab.js` statically imports all five renderers, so every numbered activation is
  synchronous and does no network work.
- `harness.html`/`harness.js`/`check.cjs` are immutable tooling and are **not**
  imported by the lab; there is no sixth selectable candidate.

Exactly one candidate root (`[data-variant]`) exists in `#game-surface` at a time;
inactive variants are not left visible or keyboard-focusable. The rail is outside the
mounted surface, so switching or resetting never steals rail focus.

## Launch

From the repository root (static files only; never the production server):

```
python -m http.server 18770 --bind 127.0.0.1 --directory .
# open http://127.0.0.1:18770/prototypes/studio-lab/
```

Stopping the server removes all exposure; no game or save file is touched.

## Acceptance tests

Syntax:

```
node --check prototypes/studio-lab/lab.js
node --check prototypes/studio-lab/fixtures.js
node --check prototypes/studio-lab/browser-test.cjs
```

Integration suite (starts/stops its own stdlib static server on port 18771):

```
NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules \
  SCREENSHOT_DIR=/tmp/opencode/gamedev-ui-lab \
  node prototypes/studio-lab/browser-test.cjs
```

Result on the current five files: **PASS — 2154 checks, 25 screenshots**. The suite
covers: five full visible workflows with exact preview/commit effects for all three
responses; preview/cancel/duplicate guard; defer/reject/reopen; switching mid-preview,
deferred, rejected, post-commit, person and capability inspection with rail focus
retained; same-task synchronous switching with zero further network requests; rail
typing never dispatching game actions or rerendering the surface; invalid-transition
guards; real Tab/Enter/Space activation and mount-owned focus; feedback
save/switch/reload/export/clear/reset distinctions and confirmation focus; malformed,
invalid, partial-valid and denied storage (including no auto-migration on load); the
seven-stylesheet load order with per-candidate CSS scoping audit; and geometry at
1440×900, 1024×768 and 390×844 including rail width, page/surface/internal-scroller
overflow, candidate-root fit, 40×40 rail targets and focus-outline clearance below
sticky HUDs.

Each accepted candidate also re-runs its immutable shared checker (own server on
port 18780+N; results may be stored outside the frozen evidence dirs):

```
for n in 1 2 3 4 5; do
  LAB_EVIDENCE_DIR=/tmp/opencode/gamedev-ui-parallel/integration/check-v$n \
  NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules \
  node prototypes/studio-lab/check.cjs --variant $n
done
```

Result on the current files: **all five PASS — 323 checks each**. Raw logs for this
integration wave are under `/tmp/opencode/gamedev-ui-parallel/integration/`
(`integration-run8.log`, `check-v1..5.log`).

## Fixed rail and screenshot set

The rail stays on the right at every viewport, reserving **280px** desktop and
**112px at ≤800px**, matching the accepted harness widths; the game surface consumes
the rest and scrolls independently. The rail contains the five numbered buttons
(accessible names `Variant 1`…`Variant 5`, 40×40 minimum, `aria-pressed`), the
selected-variant line, `Variant rating` (Unrated, 1–5), `Variant feedback`,
`Overall feedback`, `Export feedback`, `Reset fixture` and `Clear feedback`. On
narrow screens the variant names are hidden inside the still-labelled buttons and the
rail scrolls vertically; no control is hover-only.

Recorded evidence (read by the integration worker): all five candidates at overview
and half-reviewed decision, desktop 1440×900 and narrow 390×844
(`v1..v5-overview-*.png`, `v1..v5-decision-*.png`), plus a preview comparison and
connected capability views, 25 files under `SCREENSHOT_DIR`. Reproduce with the
integration suite command above.

## Shared fixture and workflow

One shared state holds the view, selected response, preview, decision status,
committed response, history, acknowledgement and capability selection. Fixture time
is paused at **18 May 2031**; cash/runway/date stay visible and weeks are estimates,
never turns. Switching 1–5 keeps a half-reviewed preview, draft, entity, capability
selection and history.

1. Overview identifies Signal Drift's unresolved onboarding decision.
2. Project shows pillars, phase, baseline-relative work (60% of baseline scope,
   labelled as baseline-relative), readiness (At risk — follow-up validation needed),
   finish estimate (8–11 weeks), scope baseline and all three findings with source,
   categorical confidence and history.
3. Preview compares baseline vs proposed against committed data with no spend.
4. Cancel keeps the decision open; confirm, defer or reject apply exactly once.
5. Overview reflects the committed cash/plan/status after a decision; readiness stays
   At risk — no instant fix and no invented commercial success.
6. Mina Rao's traits/commitment and Paper Harbor's support obligation (compatibility
   fix promised by 2 June, one engineer-week reserved, opportunity cost) are
   inspection-only.
7. Paper Harbor's compact postmortem shows planned vs actual schedule/budget/receipts,
   full accounting and qualified contributing factors.
8. The capability graph has an equivalent keyboard-readable list with AND
   prerequisites, costs, tradeoffs and an explicit inspection-only note.

Exact frozen response effects (asserted by the suite):

| Response | Immediate cash | Finish estimate | Scope | Residual tradeoff |
| --- | --- | --- | --- | --- |
| Simplify branching | −$4,000 → $80,000; runway 6.7 months | 7–9 weeks | 92% of baseline | Some core fans may miss depth; onboarding improvement unverified |
| Build guided introduction | −$12,000 → $72,000; runway 6.0 months | 10–13 weeks | 100% of baseline | Keeps depth, costs time/runway; integration untested |
| Keep current plan | $0 → $84,000; runway 7.0 months | 8–11 weeks | 100% of baseline | Preserves schedule, newcomer friction unresolved |

## The five candidates — real interaction differences

1. **Ops Deck** — persistent three-pane cockpit: entity spine, focus deck and an ops
   readout with status-aware pipeline, plan lineage and project pulse; all navigation
   in place, no pages or overlays.
2. **Field Notes** — editorial paper dossier: numbered files, evidence/disposition
   spread, native `<details>` decision register and footnote disclosure; one readable
   column below 1240px.
3. **Board Map** — radical non-page alternative: one spatial relationship board with
   edges and a persistent focus lens; arrow keys move between board nodes, Enter
   activates, and narrow screens use a no-pan grid.
4. **Timeline Table** — fixed-epoch commitment agenda: six categorical lanes, estimate
   ranges, evidence dates and a record desk; time is paused inspection, never a
   scrubber.
5. **Command Board** — searchable command palette: filter or click readable commands,
   run with Enter, and read structured decision/evidence/commitment panels; the six
   native view buttons stay visible.

These differ in navigation, hierarchy and control model, not just color. Do not read
this list as a ranking; no winner is selected.

## Review rail and feedback

- One localStorage key only: `studio-rewrite-ui-lab-v1`, JSON version 1 with
  `{selectedVariant, variants:[{id,name,rating:null|1..5,comment}], overallComment}`.
  No other key is read or written; no upload, fetch, beacon or analytics runs.
- Load validates shape/IDs/rating bounds/string types and rejects invalid branches in
  memory **without writing the stored value back**; a later user action persists the
  repaired in-memory model. User feedback is never silently erased or migrated.
- Storage unavailable or save failure: a nonblocking warning appears and feedback
  keeps working in memory while export still works.
- `Export feedback` downloads `studio-rewrite-ui-lab-feedback.json` via a local Blob
  object URL. Typed feedback is only ever rendered as text and round-trips literally,
  including markup-looking strings.
- `Reset fixture` clears only shared fixture/draft/history (cash returns to $84,000,
  the decision reopens) and keeps feedback, the selected variant and rail focus.
- `Clear feedback` requires explicit confirmation (focus moves to Confirm clear) and
  returns focus to Clear feedback on confirm or cancel; it clears all five entries and
  the overall comment while leaving fixture state and the selected variant intact.
- **Fixture state resets on page reload**; saved feedback and the selected variant do
  not.

## Lifecycle, evidence and rollback

This lab is disposable by contract. Keep all code inside `prototypes/studio-lab/`;
production must never import it. The superseded coupled shell (`index.html`, `lab.js`,
`lab.css`, `browser-test.cjs`, old `README.md`) is archived unchanged under
`/tmp/opencode/gamedev-ui-parallel/pre-integration/` with
`pre-integration.sha256`. After the rendered user review, archive the feedback export
and selected screenshots/specification, then reuse only approved visual
tokens/assets/interaction ideas through a new explicitly scoped package. Do not
promote fixture reducers into simulation code. Remove the lab later only through an
explicit scoped cleanup after evidence retention; never delete user feedback or
preexisting work automatically.

Accessibility in the lab: semantic native buttons and inputs, visible
`:focus-visible` outlines, full keyboard operation, non-color status text,
`role="status"` acknowledgements and reduced-motion support. Known limitation: this is
a review prototype, not an audited production accessibility implementation. This
integration still requires the remaining Astra/Sol gates and an explicit user
rendered choice before any production UI work.
