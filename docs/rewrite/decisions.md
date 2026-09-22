# Decisions, questions and review register

## Status vocabulary

Observed = repository evidence. Proposed = Astra recommendation. Approved = user
has explicitly accepted direction. Frozen = Astra has specified the approved
behavior/contract sufficiently to implement. Verified = objective implementation
evidence plus required reviews. These labels are not interchangeable.

## Approval register — user feedback recorded 2026-09-10

| ID | User decision | Astra recommendation | Status |
| --- | --- | --- | --- |
| D1 | Multiple viable identities; experience, employees, fans, IPs and progression create strong but nonabsolute specialization | Build competence/relationships/technical reuse and transition costs, never a permanent studio class | Approved direction; detailed balance pending |
| D2 | Time only while playing; reconsider/explain weekly planning | No mandatory weekly turns; inspect/decide anytime; active visible controller only, no offline catch-up. Weeks are optional summaries/units, not chores | Active-play-only approved; Astra clarification recorded |
| D3 | No legacy-save compatibility required | No import/conversion/museum compatibility packages; preserve existing files, new format rejects old data safely | Approved |
| D4 | Browser only; no resources spent on CLI | Remove replacement terminal/reporting/replay CLI work. Internal automated tests are not a player frontend | Approved |
| D5 | Reloadable autosaves normally; explicit Ironman/permadeath may destroy its own save on failure | Normal is non-destructive; creation-time Ironman consent, campaign-scoped deletion/invalidation only; exact failure-safety contract must freeze before implementation | Approved direction |
| D6 | Local standard-library architecture and staged migration | Separate domain/application/persistence/browser, isolated entrypoint and save namespace, no big-bang replacement | Approved |
| D7a | UI selection process | One Astra UX plan; DeepSeek implements five interactive variants in a local comparison/feedback lab; user selects from rendered work | **Approved 2026-09-10** |
| D7b | Recommended decision-centered workspace is a solid common foundation; rendered production direction still to be selected | Five genuine DeepSeek alternatives derived from that one plan, not the old five prose candidates | Pending rendered selection |

The user's exact D1–D7 feedback supersedes earlier recommendations. End-to-end
balance, date/setting, the first-release playtime target and full platform-holder
scope were not explicitly settled by this feedback; retain them as proposals, not
new blockers to the isolated lab. Astra next freezes production schemas/rules after
design elaboration. D7a plus the frozen WP-UI-00 authorizes the lab only; liking the
recommended foundation is not approval of an unrendered production visual design.

### D1–D7 feedback (user wording)

> D1: Multiple viable studio identities with experience, employees, fans, IPs, and progression creating strong—but not absolute—specialization.
>
> D2: Time advances only while playing. “Weekly planning” needs reconsideration or explanation.
>
> D3: No legacy-save compatibility required.
>
> D4: Browser only; no resources spent on the CLI.
>
> D5: Reloadable autosaves normally; explicitly selected Ironman/permadeath mode can destroy its own save on failure.
>
> D6: Approved.
>
> D7: Five implemented DeepSeek prototypes, not five written concepts. your recomended design concept sounds solid so follow it

### Astra clarification of D2

Remove mandatory "weekly planning" from the control model. The player can inspect,
allocate, pause and decide whenever relevant; recurring weeks only help reports
and estimation. Simulation requires a visible active controlling game tab and
unpaused play; hidden/closed/disconnected sessions do not accumulate catch-up time.
Reading/decision holds and responsiveness will be judged in the prototypes. The
lab is deliberately frozen fixture time, not the production clock implementation.

## Contradictions resolved in the proposal, still open to user revision

- Determinism concerns reproducibility, not player omniscience. Seeded hidden state
  and uncertain evidence allow understandable but not perfectly forecast outcomes.
- Five-star *influence* is not synonymous with game quality or cash. Boutique success
  needs its own visible dimensions and opportunities, not a compulsory growth funnel.
- Deep analytics must not leak truth; progression improves sampling/coverage and
  interpretation, while basic own finances remain visible from day one.
- A large connected tree must grow from transformative decisions; node count is not
  a quality goal, and mechanical prerequisites must describe real dependencies.
- Visible employee traits coexist with uncertain outcomes, not secretly hidden
  punishments. Training competes for useful time, not only money.
- Huge corporate scale cannot retain individual-task micromanagement. Delegation
  changes authority and attention without becoming an autopilot money printer.
- Plausibility is a constraint on relationships, not a mandate for tax/legal/HR
  bureaucracy or hard-coded demographic stereotypes.
- Major economy redesign and exact legacy economic continuation are incompatible
  promises; preserve access to old campaigns rather than pretend exact conversion.

## Discovery record — 2026-09-10

- Read-only exploration agent inspected simulation/core/terminal/test architecture;
  Astra inspected browser code, current user diff, workflows and screenshots.
- No existing rewrite source of truth; created the planning-only documents here.
- Protected tracked/untracked work inventoried; no runtime/configuration changes.
- Python: 147 tests passed. Existing Chromium smoke/views/operations checks passed.
- Connected desktop browser unavailable; isolated Playwright tooling under
  `/tmp/opencode`, no runtime dependency/config change. Desktop/narrow screenshots
  personally inspected. This is discovery, not approved-UI acceptance.
- Tests show regression baseline health, not verified balance, determinism across
  date/batch, complete save durability, accessibility or late-game playability.
- No worker implementation delegated, no provider fallback, no Sol/Ponytail
  implementation review claimed. The initial prose-only UI selection format was
  rejected and superseded by the approved rendered-prototype workflow in D7a.

## Astra discovery audit (historical, before D1–D7 feedback)

Legacy runnable baseline: **verified by existing suites**, including real-terminal
geometry test and actual browser flows. Save/user-work preservation: hash/diff
checks. Game design: coherent proposal, approval outstanding. Architecture: boundaries
and staged migration proposed; exact contract freeze outstanding. UX: the earlier five
prose directions are superseded; rendered five-variant prototype lab pending. Testing gaps: recorded
in inventory, not papered over by 147 passing tests. Roadmap: proposed only; all work
packages blocked. Full M0 completion requires approvals and characterization/freeze
work; discovery alone is **not** an approved milestone completion.

## Package and review status

| Package | Status | Worker | Sol | Ponytail | Milestone audit |
| --- | --- | --- | --- | --- | --- |
| WP-UI-00 | Superseded scope; behavior retained | frontend-go, session `ses_f72f0334fffejF44u35bci35Cq` | REWRITE; [record](review-ui-00.md) | Not reached | Rescoped by user |
| WP-UI-01S | Accepted / hash frozen | Same Go worker | PASS after 2 correction cycles | LEAN, final Sol PASS | [Foundation audit](review-ui-01.md) |
| WP-UI-01V1–V5 | Accepted / hash frozen | [Five directory-isolated Go sessions](review-ui-01.md) | All PASS | All LEAN, final Sol PASS | Wave audit complete |
| WP-UI-01I | Paused/interrupted by user: kernel first | frontend-go `ses_f6f59dcdaffez9jWndq2eypaXZ` | Not delivered | Pending | Files retained |
| WP-01 | Correcting cycle1 | [frontend-go session](review-m1.md) | REWRITE: capacity/validation/layering | Pending | Gates before WP-02 |
| WP-02 | Queued after WP-01 final acceptance | frontend-go | Pending | Pending | Kernel finance/continuation audit |
| WP-03 | Implementing disjoint save codec/safety | [frontend-go session](review-m1.md) | Pending | Pending | Parallel with WP-01 |
| WP-KV | Accepted / hash frozen | [micro-go session](review-m1.md) | PASS | LEAN, final Sol PASS | Frozen RNG witness verified |
| WP-00 | Withdrawn after D3/D4; historical draft only | Not dispatched | Not run | Not run | Not required |
| WP-01 | Draft / blocked | Not dispatched | Not run | Not run | Pending M1 |
| WP-02 | Draft / blocked | Not dispatched | Not run | Not run | Pending M1 |
| WP-03 | Draft / blocked | Not dispatched | Not run | Not run | Pending M1 |

## Feedback incorporation and prototype dispatch — 2026-09-10

- Re-read `.opencode/agents/astra.md` and all five requested source-of-truth files
  before processing feedback. Preserved user's intervening prototype-workflow edits.
- Recorded exact D1–D7 feedback above; updated game, architecture, save, time,
  frontend and migration proposals consistently. Withdrawn WP-00 compatibility
  characterization expansion; no resources assigned to a new CLI.
- Authorized/froze WP-UI-00 with one shared workflow, identical explicit fixtures,
  five genuine visual/control alternatives, right-side numbered review rail,
  local/exportable feedback and an explicit disposal/reuse boundary.
- Dispatched `frontend-go` first; no fallback used at dispatch. Production UI and
  simulation packages remain blocked. This does not select a visual variant.
- Pre-worker regression baseline: all 147 existing Python tests passed in 34.136s.
  Existing save hashes and tracked user diff unchanged. Connected browser tool
  remains unavailable; isolated Playwright is the executable browser fallback,
  not a provider/model fallback or game dependency change.
- Snapshot/evidence directory: `/tmp/opencode/gamedev-ui-lab/`; existing source
  hashes in `baseline.sha256`, original tracked diff in `user-before.diff`, save
  hashes in `saves-before.sha256`, pre-edit planning copy `docs-before/`.

## Controlled parallelism decision — 2026-09-11

User requires parallel Go workers when contracts are frozen and allowed files
strictly disjoint. For lab: shared shell/fixture first → five concurrent variant
directories → integration switcher/feedback/browser checks. Never shared-file
concurrent edits. Approved; [new package family](ui-parallel.md) owns sequencing.
Original monolithic lab failed Sol once; correction tranches remained incomplete
at step limits, not provider failures. Astra rescoping isolates fixture/control
correctness from candidate design; original files and partial fixes retained.
Parallelism is now a default planning consideration, not permission for overlapping
writers. Production roadmap unchanged and no rendered direction approved.

## Kernel first / D7b dependency correction — 2026-09-11

User ordered immediate clock/command, finance and save freeze; WP-01+WP-03 parallel,
WP-02 depends on WP-01; all packages through Sol/Ponytail. Approved and specified in
[M1-K1](m1-kernel-contract.md) and [work packages](wp-m1-foundation.md). D7b only
blocks production presentation, not mechanics. UI integration interrupted with work
preserved; no new lab expansion until accepted kernel exists. Kernel commands are
internal transaction stimuli, not player cash cheats; full game content remains
separate. Ironman uses owned campaign failure marker, not broad filesystem deletion.
