# Variant 2 — Field Notes (WP-UI-01V2)

Disposable prototype renderer for the shared studio-lab harness. This is **not
production UI**, not a simulation, and **no winner is selected here**; the user
reviews the rendered variants and chooses. Files in this directory:

- `variant.js` — exports `render(state, dispatch)` returning one
  `.variant-2[data-variant="2"]` root, plus `metadata = {id: 2, name: 'Field
  Notes', description}`.
- `variant.css` — all rules scoped to `.variant-2`.
- `README.md` — this file.

All visible content comes from the shared `part(state, name)` pieces and all
state/actions from the shared mount. No fixture/reducer/history duplication, no
storage, no timers, no network, no game formulas.

## Visual and interaction differences (real, not a reskin)

1. **Document reading order, not a workspace.** Each view is a numbered file
   (`File 01 … 06`) on warm paper with hard 2px rules, file/exhibit badges and
   a ruled footer. There is no persistent three-pane spine (variant 1) and no
   command stream (variant 5); navigation is a dossier index in the masthead.
2. **Evidence and commitment together on one spread.** On wide viewports
   (≥ 1240px) the project view lays Exhibit A — project signals and Exhibit B —
   findings beside the Disposition register (responses, comparison, sign-off,
   decision log). Below 1240px the spread becomes one readable column; nothing
   is hidden or duplicated.
3. **The decision register is a fold.** Responses, preview, actions and history
   sit inside a native `<details open>` so comparison and commit stay one step
   away, while keyboard users can collapse the register to read the evidence
   and re-open it without losing state (verified with real Enter/Space).
4. **Footnote disclosure apparatus.** A masthead “Reading key & prototype
   note”, a per-file appendix, and view notes explain symbols, sources and
   limitations. These are additive; no required control or indicator is behind
   a closed disclosure.
5. **Slim persistent running head.** A narrow navy HUD bar (paused label, date,
   cash, runway) stays sticky at the top; the taller masthead (brand, status
   folio, index, reading key) scrolls with the dossier.
6. **Print markers, not fabricated precision.** Shaped confidence (● Supported
   observation / ◐ tentative), a dashed “At risk — follow-up validation needed”
   stamp, segmented phase blocks with the outlined Production segment, a
   baseline-relative striped work bar, and a reversed register header.

## Keyboard instructions

- `Tab` / `Shift+Tab` move through the masthead index: `open-overview`,
  `open-project`, `open-person`, `open-product`, `open-postmortem`,
  `open-capabilities`. `Enter` activates a tab and focus moves to the view
  heading `[data-focus-key="view-title"]`.
- From the view heading, `Tab` reaches the disposition register `<summary>`;
  `Space` collapses it (controls become hidden), `Enter` re-opens it; focus
  stays on the summary through both toggles.
- Masthead “Reading key & prototype note”: `Enter` opens, `Space` closes.
- Each file’s appendix footnote (`Appendix …`, `Capacity note`, `Promise ledger
  note`, `How to read outcomes`, `How to read the board`): `Space` opens,
  `Enter` closes.
- Decision controls remain native buttons: select a response, `Enter` on
  “Preview response”, then “Confirm”, “Defer” or “Reject”; the shared mount
  returns focus to Cancel preview, the decision result, or Reopen as
  appropriate. `Reopen decision` returns a deferred/rejected decision to open.

## Commands

```
# syntax
node --check prototypes/studio-lab/variants/2/variant.js

# shared checker (starts its own stdlib server on port 18782)
NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules \
  node prototypes/studio-lab/check.cjs --variant 2

# manual review
python3 -m http.server 18782 --bind 127.0.0.1 --directory .
# open http://127.0.0.1:18782/prototypes/studio-lab/harness.html?variant=2

# unique keyboard / disclosure / surface-overflow probe (tmp tool, not in repo)
NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules \
  node /tmp/opencode/gamedev-ui-parallel/variant-2/probe-keyboard.cjs
```

## Evidence (recorded 2026-09-11)

- Shared checker: **PASS — 323 checks** (`…/variant-2/check.log`); full P3
  workflow, guards, immutability, keyboard workflow, geometry at 1440×900,
  1024×768 and 390×844, honest unavailable-variant probe.
- Own probe: **PASS — 34 checks** (`…/probe-keyboard.cjs`, output in
  `probe-keyboard.log`, raw metrics in `probe-report.json`):
  - actual `#game-surface` horizontal overflow is **0** at 1440
    (client/scroll 1160/1160), 1024 (744/744) and 390 (278/278); no document
    overflow and no unclipped wide descendants at any size;
  - real Tab order reaches `open-project`; `Enter` focuses the view heading and
    marks the tab active;
  - native `<details>` toggles verified with real keys on the register fold
    (Space close, Enter open, focus retained), the masthead reading key
    (Enter/Space) and an appendix footnote (Space/Enter);
  - keyboard navigation continues into the Capabilities heading with the
    graph visible; no external requests.
- Screenshots inspected: `overview-desktop.png`, `project-desktop.png`,
  `preview-desktop.png`, `graph-desktop.png`, `project-narrow.png`,
  `signals-narrow.png` (278px game surface — no horizontal clipping),
  `preview-narrow.png` (preview heading and all comparison rows visible below
  the sticky HUD), plus probe captures `probe-narrow-overview.png` and
  `probe-narrow-fold-closed.png`. All under
  `/tmp/opencode/gamedev-ui-parallel/variant-2/`.
- Shared files were not modified; their hashes were checked against
  `/tmp/opencode/gamedev-ui-parallel/shared-frozen.sha256`.

## Limitations

Prototype-only. Fixture time stays paused at 18 May 2031; cash/runway/estimates
are illustrative P3 values, confidence is categorical, and readiness stays
“At risk”. The capability graph is inspection-only (horizontal scroll inside
its own frame at very narrow widths). Not an audited accessibility
implementation; no backend, save, or production entrypoint is touched.
