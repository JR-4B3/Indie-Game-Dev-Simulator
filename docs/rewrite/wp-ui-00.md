# WP-UI-00 — Five interactive UI prototypes

Status: **P2–P6 behavior retained; original single-writer scope superseded** by
[controlled parallel packages](ui-parallel.md) on 2026-09-11. The incomplete Sol
correction is retained as source/reference, not claimed accepted implementation.
Milestone: M0 / rendered selection lab. Owner: Astra. Worker: `frontend-go`
(DeepSeek; matching OpenRouter only for a recorded Go provider failure).

## P1 — Goal, authority and scope

Implement exactly five small, genuinely different full-surface visual/interaction
variants from the **one** decision-centered UX foundation in `ui-concepts.md`.
DeepSeek owns the five visual treatments, navigation and layout exploration; Astra
owns the fixture, behavior and constraints below. These are not the superseded
five prose concepts. All variants answer the same player questions with the same
actions/data, including one radical departure from page/tab navigation. Five color
themes or identical cards shuffled around do not pass.

References: `ui-concepts.md` (all), `decisions.md` D1–D7, `game-design.md` G1–G3,
G5/G7, `contracts.md` C5 accessibility/knowledge principles only. Production schema,
simulation and balance candidates are not authorization to implement game rules.
This P-contract takes precedence for the lab's explicitly synthetic state.

Exact repository files allowed to create/change:

1. `prototypes/studio-lab/index.html`
2. `prototypes/studio-lab/lab.css`
3. `prototypes/studio-lab/lab.js`
4. `prototypes/studio-lab/fixtures.js`
5. `prototypes/studio-lab/browser-test.cjs`
6. `prototypes/studio-lab/README.md`

No other repository paths, no configuration/dependency manifest edits, no game
entrypoint changes. Read/reuse existing local font via relative URL if desired;
do not copy or change font assets. Screenshots/logs go to `/tmp/opencode/gamedev-ui-lab/`.
Use vanilla HTML/CSS/JS, optional inline SVG/pixel CSS art, stdlib static server.
No production server, save interaction, HTTP API, database, network assets or deps.

## P2 — One common workflow

1. From studio overview identify Signal Drift's unresolved onboarding decision.
2. Open its product context; inspect pillars, phase/work bar, baseline schedule,
   readiness and the 3 findings with sources/confidence/history below.
3. Compare one proposed response with the committed plan and immediate cash impact.
4. Cancel a preview without spending; or confirm once, defer, or reject the response.
5. See acknowledgement plus a decision-history record; return to an overview
   reflecting the new cash/plan/decision status, never invented commercial success.
6. Inspect Mina's relevant traits and return to the project without losing state;
   inspect the other product's support obligation in the same way.
7. Open Paper Harbor's compact postmortem with observed versus expected outcomes
   and appropriately qualified contributing factors.
8. Inspect a small connected capability graph and a node's prerequisites/tradeoff.
   Graph is navigation/inspection only, with an equivalent keyboard-readable list.

Different variants may order/reveal these surfaces differently; all must provide
all steps. One common state model holds current entity, workflow step, selected
response, decision status and committed fixture data. Switching 1–5 changes the
presentation immediately while retaining this context/data. No independent state
copies that reset a half-reviewed decision on switching. Scroll position/focus may
change to keep the selected context visible. Keep rail controls stable on switching.
The active surface is a single `#game-surface` containing one `[data-variant="1"…"5"]`
root; inactive variants must not remain visible or keyboard-focusable in the DOM.

## P3 — Frozen representative fixture (illustrative, not balanced simulation)

Date: 18 May 2031, **paused fixture time**. No running clock, setInterval simulation,
real purchases, auto-advance, autosaves or Ironman controls. Persistent label:
"Prototype · fixture data · time paused". Persistent cash/runway/date, including
when looking at a finding/person/postmortem; report weeks as estimates not turns.

Studio: **Northstar Works**, 1.5 stars, 4 staff, cash **$84,000**, monthly burn
**$12,000**, rough runway **7.0 months** (cash/burn, not a revenue forecast).
Identity: compact systems games; 2 shipped releases, 8,400 fans. Label audience
strength as supported for systems players, tentative for newcomers. Reusing an IP
helps familiarity but does not guarantee new-audience fit.

Active project **Signal Drift**: tactics/automation, small paid PC release;
pillars "Readable systems", "Short thoughtful sessions", "Emergent solutions".
Phase Production, work completed **60% of baseline scope**, readiness **At risk**,
finish forecast **8–11 weeks**, scope baseline **100%**. Progress is deliberately
baseline-relative even after a scope change; explicitly label this so cuts do not
imply unexplained completed work. Quality is not a new precise number.

Findings (all visible without an analytics purchase):
- F1, 15 May: "8 of 12 new playtesters stalled at the first branching system."
  Supported observation, moderated playtest, small newcomer sample; implies an
  onboarding concern, not that 67% of the whole market will fail.
- F2, 12 May: "5 of 6 returning fans enjoyed the branching depth."
  Tentative audience inference, existing-fan sample biased toward current studio
  identity; cutting branches risks weakening a pillar for established fans.
- F3, 17 May, Mina: "A guided introduction looks feasible, but integration is
  untested." Tentative technical estimate, employee review, requires validation.

Responses and frozen preview/commit effects:

| Response ID | Label | Immediate fixture cash | Revised finish estimate | Scope | Residual tradeoff |
| --- | --- | --- | --- | --- | --- |
| simplify | Simplify branching | Spend $4,000 → $80,000; runway 6.7mo | 7–9 weeks | 92% of baseline | Some core fans may miss depth; onboarding improvement unverified |
| onboarding | Build guided introduction | Spend $12,000 → $72,000; runway 6.0mo | 10–13 weeks | 100% | Keeps depth, costs time/runway; integration untested |
| hold | Keep current plan | Spend $0 → $84,000; runway 7.0mo | 8–11 weeks | 100% | Preserves schedule, newcomer friction unresolved |

Preview shows baseline and proposed values plus cash, scope, schedule and residual
risk. Editing/selecting/closing preview does not change committed data. Confirm
applies the selected row exactly once and records decision/status **Committed**;
subsequent attempts disabled/rejected until fixture reset, including after switching.
Readiness remains **At risk — follow-up validation needed**; no instant fix/success.
Deferral sets **Deferred — revisit before validation**, no cash or plan change.
Rejection sets **Response rejected — original risk remains**, no cash or plan change.
Deferred/rejected decisions can be reopened and another response previewed; history
retains those acknowledgements. Cancel preview is not a decision-history event.
No need to author alternate simulated future outcomes for the current project.

Person **Mina Rao**, production/engineering lead, systems experience 6 years.
Visible traits: "Methodical — catches integration risks; needs validation time"
and "Mentor — develops colleagues; coaching consumes delivery capacity".
Current commitment: Signal Drift integration; not idle/free extra capacity.
Other roster summaries: founder generalist (no traits), artist (one visible trait:
"Inventive — offers unusual directions; exploration needs time"), community
specialist (no traits). No hiring/training mutation in this lab.

Other product **Paper Harbor**: shipped finite puzzle game, support obligation
"Compatibility fix promised by 2 June; one engineer-week reserved". No emergency
modal or budget mutation; show opportunity cost to ongoing production.
Postmortem (separate historical fixture, NOT the new decision's outcome):
planned 20 weeks / actual 24; budget $60,000 / actual $68,000; 90-day gross receipts
expected $100,000 / observed $92,000; fees/refunds $22,000, net receipts $70,000,
tracked contribution $2,000 after $68,000 tracked cost (not studio lifetime profit).
"Playtests suggest simpler onboarding helped completion; small sample."
"Late integration work contributed to schedule overrun (recorded work history)."
"Store reach may explain weaker acquisition; evidence incomplete."

Capability inspection fixture: Repeatable builds (owned) → Automated tests
(available; reserve $6,000 and 2 engineer-weeks; detects regressions, not design fun)
→ Safe release train (locked; needs Automated tests AND Incident process).
Community practice (owned) → Incident process (available; $3,000 and 1 lead-week;
response preparation competes with current production). No unlocking/spending here;
node details must explicitly say inspection-only. Show meaningful connections and
AND requirement without a speculative large tree implementation.

## P4 — Review rail and feedback contract

- Fixed rail on the right at all viewport sizes; reserve its width so game content
  never sits underneath it. One game surface consumes the remaining width/full
  height; it may vertically scroll. At narrow size rail may be slimmer but must
  remain right-fixed, readable and operable with scrollable controls. Never
  replace it with top tabs or show variants side-by-side/thumbnail grids.
- Five numbered buttons with accessible names `Variant 1` … `Variant 5`, selected
  state (`aria-pressed` or equivalent), visible focus, target at least 40×40px.
  Click or keyboard activation immediately swaps presentation; no network wait.
- Rail always identifies selected variant and contains labeled per-variant rating
  (Unrated, 1–5) and comment, plus overall comment, `Export feedback`,
  `Reset fixture` and `Clear feedback` controls. A collapsible feedback section in
  the rail is allowed on narrow sizes; no inaccessible hover-only controls.
- Names for testing: `Variant rating`, `Variant feedback`, `Overall feedback`.
- Store only feedback/selected variant under `studio-rewrite-ui-lab-v1` in
  localStorage. Never read/write other keys. Feedback JSON version 1, selected
  variant, all five `{id, name, rating:null|1..5, comment}` entries, overall comment.
  Export a local JSON download using Blob/object URL; escape typed feedback when
  displayed. No upload/fetch/beacon/analytics, no external requests.
- Storage unavailable or malformed: show nonblocking warning, keep in-memory
  feedback and export working, do not crash. Validate loaded feedback shape/IDs,
  rating bounds and string types; reject invalid entries without evaluating text.
- Reload retains saved feedback/selection; fixture resets on reload (explain this).
  Switching retains current fixture state/draft/entity, ratings/comments and overall
  feedback. Reset fixture clears only shared fixture/draft/history, not feedback
  or selected variant. Clear feedback requires explicit confirmation, affects all
  five entries and overall feedback, leaves fixture and selected variant intact.

## P5 — Acceptance and visual evidence

Launch from repository root (serves only static files; never start production server):

```
python -m http.server 18770 --bind 127.0.0.1 --directory .
# http://127.0.0.1:18770/prototypes/studio-lab/
```

Use existing isolated dev-only Playwright at
`/tmp/opencode/gamedev-rewrite-discovery/node_modules`; do not install in repo.
Worker writes self-contained `browser-test.cjs` which starts/stops its own stdlib
static server on 18771, using process cwd repo root (separate from review server).

```
node --check prototypes/studio-lab/lab.js
node --check prototypes/studio-lab/fixtures.js
NODE_PATH=/tmp/opencode/gamedev-rewrite-discovery/node_modules SCREENSHOT_DIR=/tmp/opencode/gamedev-ui-lab node prototypes/studio-lab/browser-test.cjs
```

Browser checks must exercise visible controls, not merely directly call reducers:
all five full workflows; preview/cancel/confirm/duplicate guard; defer/reject/reopen;
switch mid-preview, post-commit and while inspecting a person; reset distinctions;
feedback/rating save/switch/reload/export content; malformed/denied storage; keyboard
operation and focus; no external requests/page errors; one visible variant root;
rail anchored right and no overlap/horizontal page overflow at 1440×900, 1024×768,
390×844. Verify key fixtures and unchanged paused date, capability inspection and
postmortem qualification. Explicitly assert each response's exact cash/scope/estimate.
Capture at least 10 screenshots (all 5 at desktop and narrow), plus a comparison
preview and connected graph. Worker must **read screenshots with image input**, not
just capture them; record its own visual findings/fixes in the completion report.
Tests cannot decide whether designs are genuinely different: Sol/Astra inspect that.

README: exact launch/test commands, no production/save effects, shared fixture reset
behavior, per-variant real interaction differences, feedback/export instructions,
and lifecycle/reuse plan. Do not choose a winner or claim production approval.

## P6 — Non-goals, rollback and reviewer checklist

Non-goals: simulation/economy implementation, production UI, new features beyond
fixtures, real autosave/Ironman deletion, terminal, legacy migration, frameworks,
drag-only controls, decorative walking/office systems, five static screenshots.

Disposable boundary: all lab code stays in `prototypes/studio-lab/`; production
never imports it. After rendered selection, archive user feedback and selected
screenshots/specification. Reuse approved visual tokens/assets/interaction ideas
only through a new package; do not promote fixture reducers into simulation code.
Remove the lab later only by explicit scoped cleanup after selection/evidence
retention; never delete user feedback or preexisting work automatically. Stopping
the static server rolls back exposure without altering either game or any save.

Sol checklist: allowed scope, five distinct control/hierarchy treatments and radical
alternative, identical full workflow/data, stable context, right rail all sizes,
feedback privacy/persistence/export/error behavior, exact commit/cancel/reset effects,
semantic/focus/keyboard/non-color access, readable screenshots, no invented game
results/backend, isolation/cleanup. Report PASS/REWRITE/ESCALATE, never edit.
Astra: scope and tests → Sol → explicitly load Ponytail skill → independent senior
simplicity gate → final Sol confirmation/recheck → lab audit → user rendered review.
Only the user chooses the production direction; no selection by worker or reviewers.
