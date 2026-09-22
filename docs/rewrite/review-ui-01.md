# WP-UI-01 review ledger

## Shared foundation S — 2026-09-11

Worker: frontend-go `ses_f72f0334fffejF44u35bci35Cq`.
Sol: `ses_f7243d53fffeIxuk6HadrVtlbW`.
Scope: exactly five new shared/harness/checker files in `ui-parallel.md`.
Original six prototype files, production/config files and existing saves preserved.

Initial Sol **REWRITE** (238-check suite passed but was insufficient):
1. Major missing SVG stroke: graph appeared disconnected.
2. Major deferred/rejected actions could proceed without Reopen; duplicate history.
3. Major static Unresolved label after non-open status.
4. Major rail-key focus stolen, offscreen heading, hidden targets/root fallback.
5. Major missing tests for guards, graph visibility, all three committed effects,
   valid-transition immutability and actual focus cases.
6. Major narrow screenshots omitted visible phase/bar evidence.
7. Minor renderer accepted any node, not HTMLElement.

Cycle 1 Sol **REWRITE** (330 checks): original issues substantially resolved;
four remaining findings:
1. Major public reset() called removed focusKeyOfActive, throwing ReferenceError.
2. Major CSS-hidden targets accepted, focus landed on BODY rather than fallback.
3. Minor setRenderer invoked renderer twice.
4. Minor immutability test only covered invalid actions, not retained valid snapshots.

Cycle 2 Sol **PASS** (350 checks, independently rerun by Astra and Sol): stale reset
call removed/tested with inside/outside focus; computed visibility/geometry and
ancestors checked with verified focus/fallback; single renderer call with invalid
return preserving prior DOM/state; valid-transition retained snapshot/history and
nested fixture-freezing regression tests. SVG/phase/work/evidence categorical
graphics verified in seven screenshots. No remaining findings.

**Astra Ponytail:** explicitly loaded skill after Sol PASS, reviewed complete five
files and callers. **LEAN**: reducer and content parts have actual five-consumer
purpose; native buttons/DOM/CSS/static stdlib server suffice; no framework/container/
plugins or speculative production architecture. Focus validation and regression
tests address demonstrated failures and are retained. No style/line-count rewrite.
Sol then verified unchanged hashes/scope and returned **final PASS**.

Evidence: `/tmp/opencode/gamedev-ui-parallel/shared.diff`,
`shared-candidate.sha256`, `astra-core.log`, `core/check-run15.log`, seven core images.
Accepted public contract is C-UI-S1/S2, with explicit open-only decision actions;
deferred/rejected require Reopen. No running simulation or feedback in shared core.
Freeze manifest: `/tmp/opencode/gamedev-ui-parallel/shared-frozen.sha256`.

### Foundation boundary audit

Shared state/API and focus corrected before fan-out. File ownership is disjoint:
five variant directories may be written concurrently; shared/fixture/harness/checker
and original files read-only. Each worker gets its own port18781–18785/evidence dir.
No production UI selection, no migration/CLI/save effects. Final integration remains
blocked on all five package results and review gates. Test harness is not a sixth
design; only IDs1–5 are candidates. Long-run engine design outside this package.

## Variant and integration records

Five concurrent Go sessions dispatched after foundation gates. Each requires
separate scope/tests/Sol/Ponytail/final Sol evidence before integration. No PASS is
implied by shared PASS. All original/shared files and sibling directories read-only.

| Package | Worker session | Only writable directory | Test port | Status |
| --- | --- | --- | --- | --- |
| V1 Ops Deck | `ses_f7234a826ffeCo1igQ9RBhKnnD` | `prototypes/studio-lab/variants/1/` | 18781 | Accepted / frozen; Sol PASS → SIMPLIFY → LEAN → final PASS |
| V2 Field Notes | `ses_f7234a80bffekA9sGAtqRbbOLv` | `prototypes/studio-lab/variants/2/` | 18782 | Accepted / frozen; Sol PASS → LEAN → final PASS |
| V3 Board Map | `ses_f7234a808ffeJ7yZhj9qHm8ylj` | `prototypes/studio-lab/variants/3/` | 18783 | Accepted / frozen; Sol PASS → LEAN → final PASS |
| V4 Timeline Table | `ses_f7234a807ffeMuq9A99Wy53xM2` | `prototypes/studio-lab/variants/4/` | 18784 | Accepted / frozen; Sol PASS → LEAN → final PASS |
| V5 Command Board | `ses_f7234a802ffepDLQ7DE1gXxmco` | `prototypes/studio-lab/variants/5/` | 18785 | Accepted / frozen; Sol PASS → SIMPLIFY → LEAN → final PASS |

Within each directory only `variant.js`, `variant.css`, `README.md` allowed.
Evidence isolated under `/tmp/opencode/gamedev-ui-parallel/variant-N/`.
Integration NOT dispatched; waits for all five completions and review gates.
Pre-wave full-file baseline: `/tmp/opencode/gamedev-ui-parallel/pre-wave.sha256`.

V4 initial completed evidence: syntax and Astra independent variant checker PASS
323 assertions (`astra-v4.log`); directory diff/hash `variant-4.diff/.sha256`.
Worker reported 25 unique lane-key checks, 14 images read. Sol session
`ses_f722e9d1bffeHy4lO4Q9a84Cbk` independently reviewing; no verdict implied yet.
Other variant continuations stay concurrent with review and retain original owners.
322 versus 323 checker assertions depends on whether its final unavailable-variant
probe sees completed V1; count alone is not evidence of changed package behavior.
Per-variant workers should not rerun shared --core concurrently (same core test port);
only their isolated per-variant check ports are part of the parallel acceptance wave.

All five implementation deliveries now have Astra independent syntax/checker PASS
323 (`astra-v1.log` through `astra-v5.log`) and collected three-file diffs/hashes.
These are test passes, not correctness-review acceptance. Protected pre-wave
non-planning hashes and saves verified unchanged. No Go-provider fallback occurred.

### V4 initial Sol REWRITE / correction 1

Initial direct Sol call hit usage limit; one retry after user "continue" succeeded.
No fallback or bypass. Full findings, all ordered to original Go worker:
- Major JS115–125: Studio lane still baseline $84k/7.0 months after committed
  onboarding HUD $72k/6.0 months. Use planOf(state), test all three responses.
- Major JS218–234: OPEN AGENDA / Unresolved title after commit/defer/reject.
  Use neutral "Decision agenda" with state-derived current label.
- Major JS120,149–170: arbitrary runway100%, support40%, history92%, capabilities100%
  proportional bands without denominator. Replace with categorical text/chips;
  retain only fixture-backed work60% and explicit schedule scale if used.
- Major CSS28–31,39–47,230: keyboard view heading bottom767.81 at768 viewport and
  844.06 at844 viewport clips outline/content. Clear sticky HUD and full outline
  using focus scroll margins, verify all six routes at all three viewports.
- Minor README22–23,105–107: incorrectly says draft selection changes lane band
  tone; actually only commit. Correct and replace unsupported no-clipping claim
  with final tested geometry/evidence.

Sol independently passed323 checks, inspected14 images, found no horizontal
surface spill or prohibited APIs; scope/shared hashes intact. Sharedchecker does
not cover every candidate-specific label/bar/focus placement, so targeted probes
remain necessary. No shared contract/hash edits authorized for these corrections.

Other initial Sol sessions (parallel read-only reviews): V1
`ses_f70859672ffeRA3cxgmucytyH2`; V2 `ses_f7084b1b3ffeQV8jHZavhwPLFi`;
V3 `ses_f70857085ffevp4OxWx0k3Yu4a`; V5 `ses_f70854247ffeKdtTWcpG2QIyGL`.

### V3 Board Map — correctness PASS / simplicity LEAN

Sol initial PASS, no findings. Independently verified syntax, six shared and three
variant hashes, official323 checks and map-key25 checks; inspected seven official
and two map-key images. No prohibited APIs/unscoped CSS/global listeners. Dynamic
state/fixture values, actual spatial navigation, narrow no-pan layout and reachable
lens controls accepted. No save/simulation compatibility risk introduced.

Astra explicitly loaded `ponytail-review` AFTER correctness PASS and read all three
candidate files. **LEAN**: finite node/edge data serves required spatial navigation;
DOM geometry arrow-key handling is necessary for both board and narrow grid, scoped
to the map. Native buttons and shared content/reducer avoid parallel game logic;
responsive rules preserve reachability. No worthwhile maintenance reduction;
minor stylistic alternatives are not a reason to churn. No edits made or ordered.
Final Sol **PASS**: three candidate and six shared hashes unchanged; retained
323+25 checks and image evidence. Accepted manifest `variant-3-frozen.sha256` under
the evidence root. V3 must remain read-only through sibling correction/integration.

### V1 Ops Deck — initial REWRITE / correction 1

Full Sol findings ordered to same Go worker (no scope expansion):
- Major JS596–630: decision shortcuts hijack focused native buttons (2 switched
  response, p previewed while response button focused). Suppress decision keys on
  interactive elements; preserve native activation and intentional spine arrows.
- Major JS281–327,342–354: non-open pipeline says awaiting preview/Select a response
  despite Reopen guard; response remains labeled Draft even after commit. Render
  status-aware selected/deferred/rejected/committed labels and available guidance.
- Minor README21–24: readout "never leaves screen" false below1180px where static.
  Document existing responsive collapse; no new sticky redesign ordered.
Sol verified syntax323 checks, exact candidate diff/hashes and shared hashes,
11 images and independent no-spill/HUD probes. These misses require targeted
interactive-control and sidebar-state tests, not changing immutable sharedchecker.

### V5 Command Board — initial REWRITE / correction 1

Full Sol findings ordered to same Go worker:
- Major CSS52 onward: most .v5-* selectors unscoped despite documentation claim.
  Prefix every non-root selector (including groups/media) with .variant-5 and test
  parsed rules plus outside-root decoy elements for style isolation.
- Minor JS333: hint ↑↓ list promises missing ArrowUp behavior. Astra chose minimal
  correction: describe actual Down-to-enter and native Tab/Shift+Tab, not new custom
  navigation machinery. Update docs if necessary.
Sol independently syntax323+keyboard35 checks, scoped three-file diff/hashes and
shared hashes; ten images, no narrow spill, valid retained draft/guards/focus.
Selector defect remains major despite no visible collision in isolated harness.

### Correction-1 submissions — V1 / V4 / V5

All three completed by original workers, exact three-file directory scope; Astra
collected refreshed per-variant diffs/hashes and independently reran acceptance:
- V1 syntax +323 common +102 targeted checks. Interactive-control shortcut guard,
  status-aware pipeline/lineage/readout and responsive documentation corrected;
  worker inspected seven common plus six deferred/rejected/committed images.
- V4 syntax +323 common +264 targeted checks. Live plan cash/runway, neutral
  state-aware agenda, arbitrary proportion fills deleted in favor of categorical
  records (fixture60% work retained), heading/outline clearance and README corrected;
  five affected state/viewport images inspected by worker. Two probe assumptions
  corrected (CSS uppercase, legitimate residual-risk "unresolved" text), not app.
- V5 syntax +323 common +35 keyboard +20 CSS audit checks. All136 parsed rules
  scoped, including media/groups; outside-root decoys confirm no leaking styles.
  Hint corrected without adding custom navigation; ten images inspected by worker.

Evidence: `astra-v1-regression.log`, `astra-v4-regression.log`,
`astra-v5-keyboard.log`, `astra-v5-css.log` plus common `astra-vN.log` in evidence
root. Same Sol sessions re-reviewing concurrently; no verdict implied by passing
tests. Protected non-planning baseline/save hashes and accepted V2/V3 hashes
rechecked unchanged. No integration writer yet; shared and all sibling scopes held.

### V4 correction-1 Sol REWRITE / final correction 2

One remaining major JS25–31: static overview subtitle says "the open decision
before any commitment" after all three commits, contradicting the otherwise fixed
overview. Sol independently passed323, all18 route/viewport outline checks,
live plan values, one60% band/no option fills/no horizontal spill; inspected five
correction images. A reviewer-script variable typo was corrected before final probe.
Same Go worker ordered exact state-neutral replacement: "Studio condition and the
current decision record." Add exact copy checks for open/deferred/rejected/all
three committed overview states, and absence of old phrase across routes. No
unrelated changes. This is second/final correction cycle; any remaining major
requires Astra diagnosis/rescope rather than an automatic third correction.

V4 correction2 submitted: exact neutral subtitle replacement and README evidence;
CSS unchanged. Astra independently syntax323+276 regression checks PASS, refreshed
diff/hash and sent same Sol session final correctness re-review. Worker read current
committed overview desktop/narrow; prior fixes not redesigned.

### V1 correctness PASS / Ponytail SIMPLIFY

Sol correction1 PASS with no findings: syntax323+102, matching diff/candidate/shared
hashes, thirteen refreshed/state images. All actually rendered interactive controls
suppress shortcuts/Escape; native/spine behavior retained. Empty/plaintext-only
contenteditable are not rendered by candidate or shared contract; no expansion to
hypothetical controls required for this disposable package.

Astra explicitly loaded Ponytail AFTER PASS, read complete three files and traced
PIXEL references. One justified delete (only simplicity rewrite):
`variant.js:L124–L139 | delete | unused PIXEL.overview artwork | no replacement |
all callers statically reference other named icons; no dynamic access/iteration`.
Remove sixteen lines of dead visual data, preserve all displayed artwork, state,
keyboard guards, layout and documentation. Same worker instructed to change ONLY
variant.js, rerun323+102 checks. Sol must review simplified diff before acceptance.

V1 simplicity completed: Astra compared collected pre/post candidate diffs, exact
sixteen-line deletion only, CSS/README identical. Independently syntax323+102 PASS.
**LEAN** after the single justified deletion; Sol final **PASS** independently
confirmed deletion-only/live callers, hashes and reran323+102. Prior13 images
remain applicable. Frozen manifest `variant-1-frozen.sha256` in evidence root.

### V4 final gates and review availability

V4 and V5 direct Sol re-reviews hit usage limit; after user "continue", one retry
each in the same direct sessions. No fallback/bypass; unavailable reviews never
counted as accepted. V4 retry correctness **PASS**: syntax323, six exact subtitle
state probes, reviewed276 regression evidence and refreshed committed images.
Astra then explicitly loaded Ponytail and read full JS351/CSS427/README154:
**LEAN**. Earlier fixes already removed misleading scale machinery; remaining
native controls, categorical records, lane keys and shared composition warranted.
No additional rewrite. Sol final **PASS** confirmed unchanged scope/three candidate
and six shared hashes. Frozen manifest `variant-4-frozen.sha256` in evidence root.
V5 retry also returned correctness PASS; integration barrier awaits its simplicity
completion/final Sol confirmation below, not a further correctness correction.

### V5 correctness PASS / Ponytail SIMPLIFY

Sol correction1 PASS with no findings. Independently syntax323+keyboard35+CSS20
(136 parsed rules), candidate/shared hashes, ten regenerated images and clean
test-port shutdown. Both selector scope and truthful keyboard hint fixed.
Astra explicitly loaded Ponytail after PASS and read full JS426/CSS505/README121;
traced `appendPart` with grep (only definition, not exported or called).
One justified delete, only simplicity rewrite:
`variant.js:L44–L48 | delete | unused appendPart helper | no replacement |
all output uses part()/panel directly, null guard remains in panel`.
Same Go worker allowed ONLY variant.js for this deletion; no CSS/README/command
machinery edits. Rerun323+35+20, then Astra incremental diff and final Sol. No
additional simplification will be ordered for this package.

V5 simplicity completed: six-line deletion only (function plus blank), verified
personally by Astra against retained pre-simplicity diff, CSS/README identical.
Astra syntax323+35+20 rerun PASS; **LEAN** after deletion. Sol final **PASS**:
independent syntax323, deletion-only check/no references, candidate/shared hashes,
retained35/20 logs and ten image files. No DOM/CSS output change. Accepted manifest
`variant-5-frozen.sha256` in evidence root.

## Astra variant-wave boundary audit / integration authorization

All five original Go directory owners finished, each passed separate Sol correctness,
explicit Ponytail and final Sol gates. Exactly fifteen candidate files, no overlapping
writers, shared six files hash-frozen throughout. V1/V5 each used one justified
dead-code simplicity deletion; V4 used two correctness cycles, others at most one.
Go step-limit continuations were not provider failures. Direct Sol usage-limit
interruptions were recorded/retried on user continuation, never routed elsewhere.

Cross-package contract: all import same shared immutable fixtures/state/actions;
no production/save/RNG/time behavior or storage in candidates. $84k baseline,
all three commit outcomes, categorical readiness/confidence, 60% baseline work and
inspection-only graph remain coherent. Exact candidate test gates and extra keyboard/
state/geometry probes cover known defects. Accepted V2/V3 remained unchanged while
siblings corrected. Protected non-planning/source/save hashes remain unchanged.

UX: distinct entity/evidence deck, paper dossier/disclosure, radical spatial board/
lens, commitment agenda and command palette; not five color reskins. Astra inspected
representative renderings, including current V2 overview and V4 committed overview;
Sol/worker reviewed desktop/narrow workflow sets individually. No winner selected.
Combined styles, rail feedback/focus/storage and state retention between renderers
remain integration risks, explicitly covered by the integration handoff tests.

**WP-UI-01I AUTHORIZED** now, one Go integration writer only. Exact five-file scope
and requirements in ui-parallel.md (including final handoff clarifications); all
variants/shared/harness/fixtures/check.cjs read-only. Original five shell/test/docs
files archived under `pre-integration/`, full hashes `pre-integration.sha256` in
evidence root. Integration is still a disposable lab package, not production UI.
Final lab correctness/simplicity gates, Astra holistic audit, running local review
page and explicit rendered user choice still required before production UI work.

Integration dispatched as ONE new frontend-go session
`ses_f6f59dcdaffez9jWndq2eypaXZ`, only the five authorized shell/test/docs files.
Required full browser suite port18771, read all five overview/decision desktop/narrow
images, preserved feedback schema and protected frozen-file checks. No other writer
active; this sequential integration follows the completed five-worker parallel wave.

Integration initial tranche hit worker step limit after writing four files
(index/lab.js/lab.css/browser-test). README still stale; no syntax, browser tests or
screenshots had been run. This is explicitly incomplete/unverified, not a delivered
package or provider failure. Same Go session continued to run acceptance, correct
shell defects, inspect all images, write truthful README and verify frozen scope.
Frozen-variant defects must escalate to Astra; integration writer cannot fix them.

**PAUSED by user priority change:** build M1 simulation kernel before any further
lab effort; user will review candidates separately for D7b. Active integration
session `ses_f6f59dcdaffez9jWndq2eypaXZ` interrupted via documented OpenCode V2
session interrupt API, result `interrupted:true`; cancellation confirmed. Work
retained as-is; no reset/revert or claim of completed integration. Do not dispatch
another UI tranche until the kernel boundary exists. Kernel packages and reviews
are independent of rendered D7b.

### V2 Field Notes — correctness PASS / simplicity LEAN

Sol initial PASS with no findings; syntax323 and independent52 checks cover all
six routes/three viewports, heading outline clear of HUD, collapsed details Tab
exclusion, project/capability pieces and preview/commit state. Two preliminary
reviewer assertion errors corrected before the passing probe; no worker code
change. Nine supplied images inspected; all candidate/shared hashes matched.
"Approved direction" in Sol's prose means authorized candidate brief only: no
user rendered UI selection/production approval has occurred.

Astra explicitly loaded Ponytail after PASS, reviewed complete JS/CSS/README:
**LEAN**. Native details and buttons plus shared parts need no custom disclosure
state/listeners; CSS implements required contrasting paper treatment and responsive
states. No justified maintenance simplification, no edits ordered. Final Sol **PASS**
confirmed three V2 and six shared hashes unchanged, retained323+52 checks/nine images.
Accepted manifest `variant-2-frozen.sha256` under evidence root. V2 is read-only
through sibling corrections/integration; not a user-selected production direction.

Frozen shared foundation hashes (2026-09-11):

```
b761fada34ba533f3ea371436850f9851ed0a411e62ec8a73e98774a955b7640  shared.js
c1e056f15e06bdced875f7364fc6677bf49f5abb669c974977652404cf3170f3  shared.css
3ff2f2c71186fced2cc7129f8ff4513b5080793b998f47306ecf0eb84d3d6656  harness.html
b6f034af28baa271d94b7ca394016ff56030d7dbb4aceebc225d2f1bacd8320e  harness.js
d3f5aa8c8213915b1650825e3db06f2db872b81da86a16c5a91ba0e6bd18c0ff  check.cjs
```
