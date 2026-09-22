# Variant 5 — Command Board

Disposable WP-UI-01V5 prototype for rendered comparison only. No direction is
selected, this is not production UI, and it does not consume feedback or storage.
It reads the frozen fixture/state seam (`../../shared.js`) and composes the shared
content pieces; it does not duplicate the reducer, fixture, or focus logic.

## What it is

A searchable command-palette workspace. The left **command deck** holds a filter
input, a Run button, a Clear button, a live context readout, and a catalogue of
readable commands. The right **board** answers each command with structured panels
— decision brief, systems readout, evidence board, decision deck, decision ledger,
channel map, capability graph, postmortem — instead of a terminal transcript.

The palette is a browser UI, not a CLI: typing filters visible command buttons,
and every command is also a normal clickable button. The six native view buttons
(`open-overview` … `open-capabilities`) stay visible at all times and are never
hidden behind the palette.

## Running it

```
# syntax
node --check prototypes/studio-lab/variants/5/variant.js

# acceptance (starts its own server on port 18785, cwd = repo root)
NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules \
  node prototypes/studio-lab/check.cjs --variant 5
```

Manual viewing: serve the repo root (`python3 -m http.server 18785`) and open
`http://127.0.0.1:18785/prototypes/studio-lab/harness.html?variant=5`.

## Commands (20)

- **Navigate** — Open — Studio overview; Open — Project: Signal Drift; Open —
  Person: Mina Rao; Open — Obligation: Paper Harbor; Open — Postmortem: Paper
  Harbor; Open — Capability graph
- **Response** — Select response — Simplify branching; Select response — Build
  guided introduction; Select response — Keep current plan
- **Decision** — Preview selected response; Commit selected response; Defer
  decision; Reject response; Reopen decision
- **Inspect** — Inspect capability — Repeatable builds; Automated tests; Safe
  release train; Community practice; Incident process
- **Fixture** — Reset fixture state

Unavailable commands stay in place and are disabled with a visible reason
(“Preview the selected response first”, “Already committed — reset the fixture to
compare again”), matching the shared reducer guards.

## Keyboard and pointer

- Tab reaches the input, Run, Clear, the catalogue, then the native nav buttons.
- Typing filters commands by label, group and keywords (e.g. `project`, `simpl`,
  `preview`, `reopen`, `capability`). Clear (✕) or Escape restores all 20.
- Enter in the input runs the first matching *enabled* command and then clears
  the filter, so controls reappear after every change/re-render.
- ArrowDown (shown as “↓ enter list” in the deck) moves from the input into the
  first matching command button; Tab/Shift+Tab then move between the visible
  command buttons. Enter or Space activates any focused command/response/action
  button natively.
- Focus after actions follows the shared mount contract: view heading after
  navigation, the selected response, Cancel preview, the decision result, Reopen
  after defer/reject, the selected capability item.
- A zero-match filter shows a visible recovery message while Run, Clear and the
  six nav buttons stay usable.

## Real differences from a generic page/tab treatment

- Command-first interaction model: navigation, response selection, comparison,
  decision transitions and capability inspection are all exposed as one filtered
  command catalogue with a live `n/20 commands` count.
- Output is a card board (decision brief, evidence board, comparison matrix,
  ledger, channel map), not one long page of shared defaults.
- Persistent deck readout shows view, decision status, selected response, open
  preview and cash beside the command input.
- Visual lineage: dark navy bridge console with cyan readouts, amber command
  accent, LED panel heads, segmented phase bar and dashed evidence cards.
- Overview adds a Channel map with a second native route surface to every view.

## Evidence

All under `/tmp/opencode/gamedev-ui-parallel/variant-5`:

- `check.log` — acceptance run: **323 checks PASS** (shared `check.cjs --variant 5`,
  port 18785, includes workflow, guards, immutability, invalid actions, Tab/Enter/
  Space keyboard flow, geometry 1440×900 / 1024×768 / 390×844, no external
  requests/console errors).
- Canonical screenshots, all inspected as images:
  `overview-desktop.png`, `project-desktop.png`, `preview-desktop.png`,
  `graph-desktop.png`, `project-narrow.png`, `signals-narrow.png`,
  `preview-narrow.png`.
- Extra keyboard probe (`/tmp/opencode/variant-5-keyboard.cjs`, port 18795):
  `keyboard-probe.log` — **35 checks PASS**, plus `keyboard-filter.png`,
  `keyboard-empty.png`, `keyboard-narrow-filter.png`.
  The probe types real keys, asserts only matching commands are rendered
  visible, that Enter runs the first match, that Space activates command buttons,
  that the zero-match message is recoverable, and that the nav stays visible at a
  390px viewport (278px game surface).
- CSS scope audit (`/tmp/opencode/variant-5-css-audit.cjs`, port 18796):
  `css-scope-audit.log` — **20 checks PASS**. It parses the loaded stylesheet via
  the CSSOM and asserts every one of the 136 selector parts is `.variant-5` or
  starts with `.variant-5 `, then places decoy nodes with each `v5-*` class (and
  grouped/state combinations) outside the root — in the rail and in `body` — and
  proves their computed styles match unclassed baselines at 1440px and 390px
  while in-root scoped styling still applies.
- Defect found and fixed through screenshot review: `.v5-cmd`'s `display:grid`
  was overriding the UA `[hidden]` rule, so filtering changed only the count.
  `variant.css` now contains `.variant-5 .v5-cmd[hidden] { display: none; }` and
  the probe asserts rendered visibility rather than the `hidden` property.
- Scope correction after Sol review: every non-root selector (including grouped
  and `@media` selectors) is now prefixed with `.variant-5`; declarations are
  byte-identical to the pre-correction file and the screenshots are unchanged.

## Scope

Writes limited to `prototypes/studio-lab/variants/5/variant.js`, `variant.css`
and this README. Shared `shared.js`/`shared.css`/`harness.*`/`check.cjs`/
`fixtures.js` untouched (hashes match `shared-frozen.sha256`). No storage,
network, feedback, or global listeners.
