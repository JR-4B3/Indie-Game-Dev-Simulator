# Controlled parallel UI lab — WP-UI-01 family

Authorized by user 2026-09-11. Supersedes WP-UI-00's single-writer implementation
scope/sequencing, **not** its fixture/product/accessibility/privacy requirements.
No visual direction is selected. Existing lab and unfinished Sol correction retained
as reference until integrated replacement proves itself. No current writer active
at rescope. D1–D7 and WP-UI-00 P2–P4 remain authoritative.

## Ownership and schedule

1. **WP-UI-01S shared foundation** — one Go worker creates shared shell/fixture API
   and checker below. No variant directories edited. Astra scope/tests → Sol →
   Ponytail → final Sol. Freeze accepted shared file hashes before fan-out.
2. **WP-UI-01V1–V5** — dispatch FIVE `frontend-go` child sessions concurrently, one
   isolated directory each. All shared files read-only. No integration writer runs
   during this wave. Contract ambiguity goes to Astra, never cross-directory edits.
   Each has its own test port/evidence directory; no conflicting browser servers.
3. Scope/test each variant and send each through Sol/Ponytail/final Sol. Independent
   reviewer work may run concurrently; correctness corrections go to the same child
   session and stay within that directory. No parallel edits to shared code.
4. **WP-UI-01I integration**, only after all five workers finish and pass: one Go
   writer builds the right-side 1–5 switcher, local feedback and full browser checks.
   Variant directories/shared core frozen; defects there return to original owner
   under a sequential clarified package before integration resumes.
5. Full correctness/simplicity gates and Astra lab audit before rendered user review.

Per package: max two Sol correction cycles, one justified simplicity rewrite; after
that Astra diagnoses/rescopes. OpenRouter only after matching Go provider/auth/quota/
transport failure, not step exhaustion or incorrect code. No source resets/commits.

## Frozen C-UI-S1 — Shared state and renderer seam

Use browser ES modules (no package.json required), plain DOM/CSS. Existing
`fixtures.js` remains unchanged, loaded before modules; `shared.js` reads and deeply
freezes `globalThis.STUDIO_LAB_FIXTURES` as `F`. No duplication of fixture truth.

`shared.js` named exports:

- `F`: fixture object, identical WP-UI-00 P3 data.
- `createState()`: `{view:'overview', selectedResponseId:null, previewFor:null,
  decisionStatus:'open', committedResponseId:null, history:[], ack:'',
  selectedCapabilityId:'automated-tests'}`. Each history entry `{kind,text}`.
- `planOf(state)`: frozen baseline/response record, never mutates.
- `statusText(state)`: current Open/Deferred/Response rejected/Committed label,
  using P3 meanings. Overview and node/lane labels must use this, not fixed pending.
- `reduce(state, action, arg)`: returns next state, never mutates input/F; unknown
  action/invalid arg returns input unchanged. Allowed actions: `goto` (view enum
  overview/project/person/product/postmortem/capabilities), `select-response`
  (response ID), `preview`, `cancel-preview`, `confirm`, `defer`, `reject`, `reopen`,
  `select-capability` (node ID, opens capabilities), `reset`.
  Exact P3 effects; confirm requires matching selected/preview and commits once;
  navigation/inspection cannot clear draft/preview/history or change money.
  Decision actions select-response/preview/confirm/defer/reject are open-only;
  deferred/rejected states explicitly require Reopen. Both DOM and reducer enforce.
- `el(tag, attrs={}, ...children)`: tiny explicit DOM helper, supports text/nodes/
  arrays/null children, omits null/false attrs, handles `class` and `text`; other
  keys are literal attributes (e.g. `data-testid`). No string second-arg shorthand,
  HTML injection/eval/templating framework. Native append(null) must not leak text.
- `part(state, name)`: returns fresh DOM fragment for one named content piece:
  `hud`, `studio`, `summary`, `signals`, `findings`, `responses`, `preview`,
  `actions`, `history`, `person`, `support`, `postmortem`, `capabilities`.
  Returns null only for absent preview. Content pieces are NOT whole variant pages;
  each renderer chooses hierarchy, navigation, disclosure, layout and control feel.
  Shared semantic classes `.lab-*`, tests below; variants can style under their root.
- `mount(surface, renderer)`: owns the one state and delegated `[data-action]`
  buttons/args inside surface; renderer signature `render(state, dispatch)` returns
  one HTMLElement. Returns `{getState, dispatch, setRenderer, reset, destroy}`.
  `setRenderer(render)` keeps state/draft/selected entity and rail focus; reset resets
  fixture only. Renderers read state, never mutate it or write storage. Every render
  removes old root; no accumulating listeners/timers or hidden inactive variants.
  Snapshot passed to renderer is read-only; no side effects in getters/projections.

Focus owned by mount: native Enter/Space button activation; preserve selected
response focus on rerender, preview→Cancel preview, cancel→Preview response,
confirm→focusable decision result, defer/reject→Reopen, reopen→decision result,
navigation→focusable new view heading. Stable `[data-focus-key]` IDs, no catch-all
focus-to-overview. Rail outside surface never loses focus on switching. Fallback
visible heading/root only if intended target absent; no hidden/disabled target.
Variants can attach root-local arrow/filter listeners, never global/window ones.

No running time, RNG, saves, localStorage, network or feedback in shared core.
Feedback stays solely in integration shell. Headless test tooling is not a game CLI.

## Frozen C-UI-S2 — Required visible pieces and selectors

All variants display hud (paused label/date/cash/runway) persistently. Overview
contains studio identity/fans/IP/people information, decision summary and access
to all routes. Project contains pillars, signals, all 3 findings, responses,
comparison preview, action controls/history. Other routes use relevant part(s).
Variants may split/disclose parts via accessible native controls; required content
must not become a hover-only hint or inaccessible hidden duplicate.

Part semantics and stable test IDs (use existing lab names where below):
- HUD: `date`, `metric-cash`, `metric-runway`; date exactly 18 May 2031.
- Summary: `decision-flag`, `decision-status`, `committed-plan`; derive labels/state.
- Signals: `project-name`, `pillar` ×3, `work-progress` text, `work-bar` visible
  progressbar named "Baseline work completed", min0 max100 now60 with 60% fill,
  `phase-track` segmented with Production labeled current, `readiness` categorical
  shape/text At risk, `finish-estimate`, `scope-baseline`. No fake numeric quality.
- Findings: `finding-f1/f2/f3`, `confidence-f1/f2/f3` visibly shaped Supported/
  Tentative indicators with source, sample/limitations, date/history, no precise odds.
- Responses: native buttons `response-simplify/onboarding/hold`, aria-pressed and
  disabled after commit. `preview-panel` compares baseline and proposed cash,
  schedule/scope/spend/residual risks. IDs `preview-baseline-cash`,
  `preview-proposed-cash`, `preview-baseline-estimate`, `preview-proposed-estimate`,
  `preview-baseline-scope`, `preview-proposed-scope`, `preview-spend`, `preview-tradeoff`.
- Buttons: `preview-button`, `cancel-preview`, `confirm-button`, `defer-button`,
  `reject-button`, `reopen-button`; result `decision-result` focusable role=status;
  history `history-entry` records actual decisions, not preview/cancel.
- Person `person-name`, `person-traits`, `person-commitment`; support
  `support-obligation`; postmortem `postmortem` with qualified history and full P3
  accounting; capabilities `capability-graph`, keyboard `capability-list` with
  buttons `cap-list-<id>`, detail `cap-detail`, AND requirement and inspection-only.

Each variant navigation exposes native buttons with literal `data-action="goto"`,
`data-arg="<view>"`, and test ID `open-overview/project/person/product/postmortem/capabilities`.
Each currently selected view has `[data-focus-key="view-title"]` heading tabindex=-1.
Root: `data-variant="N"`, class `variant-N`. Layout/CSS scoped to `.variant-N`;
never style body/html/rail/shared nodes outside that root. No arbitrary API changes.

## WP-UI-01S — shared foundation package

Goal/rationale: freeze one tested interaction/fixture/shell seam BEFORE five writers.
References: C-UI-S1/S2 above; WP-UI-00 P2–P6; Sol defects in `review-ui-00.md`.
Worker: SAME `frontend-go` as prior shared implementation where practical.
Exact allowed NEW files:
- `prototypes/studio-lab/shared.js`
- `prototypes/studio-lab/shared.css`
- `prototypes/studio-lab/harness.html`
- `prototypes/studio-lab/harness.js`
- `prototypes/studio-lab/check.cjs`

Do not edit original six files or any variant directory. Existing partly-corrected
`lab.js`/CSS may be read as source/reference, not imported by the new core. Prefer
reuse of proven fragments while eliminating renderer/feedback coupling. No build
step/framework/registry. `shared.css` handles readable content pieces, visible focus
and shared shell geometry only; typography/colors can be overridden by variants.

Harness shell: one `#game-surface` beside reserved fixed-right rail placeholder
(desktop280px, narrow112px); header/rail describes isolated variant testing. URL
`harness.html?variant=N` dynamically imports `./variants/N/variant.js`, loads exactly
that CSS, calls mount. Missing/invalid variant shows honest unavailable message,
never substitutes another design. Before variants exist, `?core=1` mounts a plain
contract-test composition; explicitly not a sixth candidate or selectable design.
No 1–5 switcher or feedback implementation in this foundation (integration owns it).

`check.cjs` is shared immutable acceptance tooling for later workers:
`node prototypes/studio-lab/check.cjs --core` or `--variant N`. Playwright via NODE_PATH;
starts/stops its own stdlib static server port18780+N (core18779), cwd repo root.
Outputs evidence under `/tmp/opencode/gamedev-ui-parallel/core` or `variant-N`.
No server output polling shell loops; script may wait for its own server normally.
Common tests use visible controls/selectors above: full P2 workflow and exact all3
response effects, no change on preview/cancel, duplicate guard, defer/reject/reopen,
readiness/baseline bar persistence, categorical confidence, all routes and capability
selection, date unchanged, invalid actions/no mutation, setRenderer preservation
(core test), real Tab/Enter/Space workflow and focus assertions, no external requests
or console errors. Geometry 1440×900/1024×768/390×844, no rail overlap/page horizontal
overflow, native scroll allowed. Capture overview/project/preview/graph at desktop
and project/preview narrow, including visible phase/work bar (not only scrolled
below it). Check failure must set nonzero exit. Do not use loose assertion count
as proof of keyboard coverage. Tests should be concise scenario loops, not framework.

Acceptance:
```
node --check prototypes/studio-lab/shared.js
node --check prototypes/studio-lab/harness.js
NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules node prototypes/studio-lab/check.cjs --core
```
Evidence: output, module API, original files/hash unchanged, core screenshots read
by worker. Non-goals: candidate design, feedback/storage, production, CLI, migration.
Rollback: additive core not imported by original index; no existing save/state touched.
Reviewer: S1/S2 behavior/validation/focus, Sol's four issues addressed in core,
checker really presses keys/asserts geometry, no overbuilt component framework.

## WP-UI-01V1–V5 — parallel variant packages

Milestone M0. Goal: five independent visual/interaction treatments of identical
player workflow, without touching shared contracts or reproducing fixture logic.
References: accepted C-UI-S1/S2, `ui-concepts.md`, WP-UI-00 P2–P6. Shared hash baseline
must be recorded before dispatch; workers cannot repair or extend shared modules.

For package V**N**, exact allowed files ONLY:
- `prototypes/studio-lab/variants/N/variant.js`
- `prototypes/studio-lab/variants/N/variant.css`
- `prototypes/studio-lab/variants/N/README.md`

JS exports `render(state, dispatch)` returning one `.variant-N[data-variant=N]`
root, and `metadata={id:N,name,description}`. Import shared helpers only from
`../../shared.js`. No duplication of reducer/fixture/feedback. Ordinary UI event
listeners must be scoped to returned root; pure visual data may remain module-local,
never authoritative cash/decision/history. Each CSS only styles its own root.
Preserve existing feedback IDs/names: 1 Ops Deck, 2 Field Notes, 3 Board Map,
4 Timeline Table, 5 Command Board. These are current rendered directions, not the
superseded prose list; workers may improve their visual treatment within the brief.

Distinct exploration ownership (DeepSeek determines actual layout/treatment):
V1 persistent entity/focus/evidence workspace; V2 readable document/disclosure
workflow; V3 radical spatial/node interaction with accessible focus lens and keyboard
path (no requirement to pan to critical actions); V4 commitment agenda/timeline
hierarchy, no meaningless week scrubber/time advancement; V5 searchable command
palette-driven workspace (browser UI, not an actual CLI). Preserve same evidence,
tradeoffs and useful bars; do not hide them behind extra steps to appear different.
Do not choose a winner. Shared content pieces may be styled/composed differently;
five nearly identical pages with a different navigation border do not pass.

Acceptance per N:
```
node --check prototypes/studio-lab/variants/N/variant.js
NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules node prototypes/studio-lab/check.cjs --variant N
```
Worker additionally exercises unique navigation controls via Playwright (map arrows,
command filtering/Enter etc), captures images and READS its own desktop/narrow
screenshots. README names real interaction differences, keyboard instructions,
commands and evidence; no inflated completion or production approval claims.
Non-goals: shared/controller/fixture/checker edits, extra mechanics, backend/storage,
full-game features, sibling variant edits. Rollback: directory remains unintegrated;
no other variant or current lab affected. Reviewer checklist: directory isolation,
shared API use, full workflow, visual distinction/readable narrow UI, true keyboard
and focus behavior, categorical indicators/no fabricated precision, image inspection.

## WP-UI-01I — integration (AUTHORIZED after all five final gates)

Barrier cleared: [variant-wave audit](review-ui-01.md). All five variants and shared
core frozen; one integration Go writer only. No production direction approved.

Goal: final full-surface lab with fixed-right 1–5 rail, local/exportable feedback,
shared context across variants and unified acceptance. References: P4 privacy/reset
and feedback format in WP-UI-00, C-UI-S1/S2; all five accepted renderer exports.
Exact allowed files: original `index.html`, `lab.js`, `lab.css`, `browser-test.cjs`,
`README.md` under `prototypes/studio-lab/` (NOT fixtures/shared/harness/variants).
Replace old coupled renderer definitions with imports of the five accepted modules;
retain feedback key/schema/IDs and user's saved feedback, no auto-reset. Read-only
assets; only selected variant root active; switch immediate and focus remains rail.
Use mount.setRenderer to retain entity/preview/history/committed values. Shell owns
feedback validation/failure/export/reset distinctions, never game formulas.

Acceptance: original WP full browser command plus all5 new checker commands,
syntax, original-source/save hashes, exact scope/diff. Full test must actually press
keys and exercise shared-state switching, local persistence/export/denied storage,
resets/focus and all views/indicators. Capture overview and decision desktop/narrow
for each, inspect images, no console/network/geometry failures. Final review checklist
includes distinctness across candidates and all original Sol findings, README accuracy,
no imports of superseded coupled implementation, no fixture runtime promoted to game.
Rollback: archive existing original lab files in evidence before replacement; later
cleanup only via scoped approval. Preserve user feedback and original game work.
All gates apply separately; user must explicitly select from the rendered result.

### Integration handoff clarifications (Astra, before authorization)

Preserve accepted candidate geometry: use shared.css followed by the five scoped
candidate stylesheets, then shell-only lab.css. Keep reserved rail width280px,
112px at viewport≤800px, matching the accepted harness (do not reuse the old164px
narrow rail). Preload the five ES-module renderers/styles during page boot, then
switch synchronously with mount.setRenderer; no lazy network wait on numbered
activation. Exactly one candidate root in the game surface, never hidden duplicates.
Do not import harness.js or expose its plain core-test composition in the lab.

Rail DOM remains outside the mounted surface; typed ratings/comments never trigger
variant rerenders. Preserve P4 storage key/version/IDs/names and valid existing local
feedback; no automatic clearing on this handoff. Keep explicit confirmation for
Clear feedback, move focus to its confirmation controls and return to Clear feedback
on confirm/cancel (not BODY or a removed/hidden element). Fixture reset uses the
accepted public reset() and retains selected variant/feedback/rail focus.

Full integration tests must close gaps found during candidate reviews: check actual
game-surface AND candidate/internal-scroller horizontal overflow, not document alone;
check heading/active-control outline clearance below sticky HUDs; CSS isolation with
all five stylesheets loaded; decision-state summaries after defer/reject/eachcommit;
native keyboard activation and no game shortcut effects while typing rail feedback.
Exercise switching mid-preview, deferred/rejected, postcommit, person and capability
inspection, retaining state and rail focus. Browser errors, denied/malformed storage,
literal markup feedback/export and exact reset/clear effects remain mandatory.

The final comparison must let user review all five one at a time. Do not narrow the
candidate set based on reviewer preferences. Existing coupled lab source is archived
in pre-split-lab evidence before replacement; only the authorized five shell/test/docs
files may be replaced. All accepted renderers/shared/fixture/harness/checker files
are read-only. Integration README separates legacy reference from the current lab;
no deletion of archived/user feedback or production-save artifacts.
