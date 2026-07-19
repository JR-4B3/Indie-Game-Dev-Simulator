# Indie Studio Game Dev Sim

A terminal-based economic simulation about trying to keep a small independent
game studio alive. The simulation begins on the current date. You start with one
founder, personal runway, no guaranteed audience, and the same tradeoffs a small
studio faces: scope, payroll, contract work, discoverability, refunds, taxes, and
burnout.

## Run

The game uses only the Python standard library and requires a terminal of at
least 74 columns by 24 rows.

```bash
python main.py
```

Load the default save or choose another save file:

```bash
python main.py --load
python main.py gamedev_save.json
python main.py --load gamedev_save.json
python main.py --load --save-file my_studio.json
```

A positional filename implies `--load`. Use `--save-file` without `--load` when
you want a new studio that will save under a custom filename.

An old version-one save is migrated into a present-day studio, and version-two
and version-three saves load into the current planning model. Legacy cash,
followers, reputation, and release count are retained where possible; obsolete
1970s projects and fixed employees are not.

## The Simulation

- **Real calendar and accounting:** weeks use the current calendar. Salaries,
  employer payroll burden, software seats, insurance, administration, upgrade
  subscriptions, and estimated quarterly income tax affect cash.
- **Runway, not points:** the key studio metric is how many months remain at the
  currently committed burn. The game prevents a hire or purchase when it would
  leave less than one month for bills.
- **Concept room:** a game can combine two genres and two themes, including
  Battle Royale, Extraction Shooter, Survivors-like, Roguelike, Roguelite,
  Deckbuilder, Automation, Cozy, Social Deduction, Immersive Sim, Soulslike, and
  Metroidvania concepts. Instead of moving abstract focus percentages, choose a
  target audience, game format, lead and supporting creative bets, launch-life
  strategy, scope, marketing level, and store. Every bet states its tradeoff.
- **Uncertain market validation:** the brief estimates ranges for addressable
  players, overlapping competing releases, market fit, workload, schedule, risk,
  and post-setup runway before greenlight. Genre/theme mix, audience, format,
  creative bets, trend, release plan, and store move the underlying market much
  more strongly. The report is not simulation truth: employee Research determines
  confidence and interval width, and even a strong signal can be wrong.
- **Production by work:** Micro, Compact, Small, Mid-size, Ambitious, Large, and
  Blockbuster projects require increasingly serious teams, reputation, capital,
  and work. Completion time changes with team skill, morale, fatigue, hardware,
  creative commitments, online infrastructure, and time diverted to client work.
- **Multiplayer ambition:** Offline Solo, Online Co-op, Competitive Online,
  Persistent World, and MMO formats are visible from the beginning. Networking,
  server setup, staffing, reputation gates, launch risk, retention, and recurring
  hosting costs make the biggest formats something a new studio can inspect but
  cannot responsibly greenlight.
- **Occasional production events:** a project schedules zero to two events based
  on its scale rather than interrupting every phase. An event appears as a blocking
  popup over any page and offers two explicit schedule/quality/market/defect
  tradeoffs. Time and other controls remain locked until the decision is made.
- **Production phases and defects:** projects move through prototype,
  pre-production, production, alpha, and beta. Team code skill and QA equipment
  influence defect load and launch refunds. Testing reveals only part of the real
  defect count, so the interface reports known bugs rather than perfect information.
- **A developing small team:** six new applicants are generated each month with a
  role, seniority, salary expectation, four production skills, Research, morale,
  fatigue, a work style, and a separate quirk. Every style and quirk combines an
  advantage with a liability. Project, contract, and live-operations experience
  improves staff over time; stronger employees demand raises. The Team page can
  send a selected employee to four weeks of paid Design, Art, Audio, Code, or
  Research education. They are unavailable while studying and receive a skill
  increase and salary review on completion.
- **Studio statistics:** four switchable views provide a studio overview,
  solid-color revenue/expense breakdowns, vertical monthly cash-flow columns,
  statistics for every genre, and a permanent release catalog. Accounting keeps
  contract and game revenue separate and retains payroll, employer costs,
  operations, development, marketing, taxes, equipment, hosting, recruiting,
  and severance categories.
- **Named games and franchises:** every project starts with a generated title
  based on its primary genre and theme. Reroll it or type a custom name. Releases
  retain the complete concept brief, market position, scope, score, units, net
  revenue, genre/theme mix, production decisions, and sequel lineage. Genre and theme
  audiences grow from actual buyers, and established audiences improve sequel
  discoverability without guaranteeing success. Starting a new game first opens
  an Original Game / Sequel chooser populated by prior releases.
- **Game portfolio:** the empty Game tab explains the concept loop; active
  production shows its market position and creative commitments; a mature
  catalogue combines commercial performance, live operations, DLC history, and
  the next game in development. Every released game remains on sale. Genre/theme
  fit, audience, competition, quality, defects, platform, reputation, followers, scope, and storefront
  reach drive launch sales, while review quality and franchise audience establish
  a permanent weekly sales floor. Refunds, store cuts, hosting, and support costs
  still apply, so a bad game may sell one copy per week without being profitable.
  Buyers discover previously hidden bugs while playing and complain online; the
  catalogue bug column increases as those reports arrive.
- **Rating versus hype:** rating and hype are independent. Hype controls exposure
  and can produce an enormous launch spike even for a bad game, but rating controls
  conversion, week-to-week sales retention, evergreen demand, player retention,
  and how many owners return for updates. A badly rated viral release therefore
  falls quickly after launch; a well-rated release can survive after hype fades.
- **Hype and promotion:** every project and release has hype that naturally
  decays. Launch investment ranges from organic promotion to a showcase launch.
  The separate Promotion Planning screen sells social pushes, press outreach,
  creator-key promotions, streamer placements, festival demos, games-event booths,
  and premium showcase slots. Better opportunities require game reputation; promotions cost
  cash, enter a FIFO queue, and consume team time only while active. Waiting
  promotions can be cancelled for an 80% refund; the active campaign is committed.
- **Live operations and DLC:** updates are planned and added to a studio-wide FIFO queue.
  Choose Bug fixes, Balance, Visual, Audio, or New content and a Hotfix, Patch,
  Content, Expansion, or Paid DLC scope. Relevant employee skill determines duration; every
  update must then clear a bug-fixing phase before it can ship. Scopes advance the
  public version by `0.00.01`, `0.00.10`, `0.01.00`, `0.10.00`, or `1.00.00`. Larger updates
  cost more and consume more team capacity. Shipping restores hype, sales, and
  monthly players in proportion to the game's rating. Bug-fix-focused updates also
  remove existing defects, although a small number of new defects can escape QA.
  Paid DLC has its own launch sales and net revenue; a DLC roadmap improves take-up
  but does not remove its production cost or QA burden. Waiting updates can be
  cancelled for 15% of their ship budget; active development cannot be cancelled.
- **Monthly active players:** this is the estimated number of distinct people who
  played during the recent month, not copies sold. A game can continue selling
  while having almost no active players, which is a warning that another update
  may not justify its staff time unless the game is well rated enough to revive.
- **Per-game profit accounting:** new releases retain setup/store fees, employee
  labor accumulated during development, launch and later marketing, hosting, and
  update costs. The Game Catalogue statistics view shows revenue, total cost, profit, and the full cost
  breakdown. Older releases remain marked `n/a` where historical cost allocation
  did not exist instead of showing misleading zero expenses.
- **Contract business:** the monthly Contract Board offers Design, Art, Audio, Code,
  and Generalist work with different workloads, payouts, deadlines, difficulty,
  and contractor-reputation requirements. Relevant team skill determines speed.
  Successful delivery builds a separate contractor reputation; missed deadlines
  lose reputation and pay nothing. Active client work diverts production capacity
  and adds fatigue.
- **Automatic contracting:** toggle automatic work to accept every currently
  eligible board offer and queue them sequentially. New eligible contracts are
  automatically queued when the board refreshes each month. Turning automation
  off stops future acceptance and cancels every unstarted automatically accepted
  contract. A contract already in progress finishes, and manually selected queued contracts are
  preserved.
- **Meaningful upgrades:** workstations, professional tools, QA hardware,
  coworking space, health coverage, and analytics have purchase prices, recurring
  costs, and simulation effects.
- **Failure:** a negative bank balance starts an eight-week insolvency clock. If
  it is not recovered, the studio closes permanently. A blocking insolvency popup
  requires deleting that run's save before a fresh studio can begin.

## Controls

- `Tab`: cycle `Hub -> Game -> Team -> Statistics`
- `H` / `G` / `T` / `S`: jump directly to a top-level page; `T` also selects the Team roster
- `J`: open Jobs from the Hub
- `N`: plan an original game or sequel from the Hub or Game page
- `U`: open Upgrades from the Hub or Update Planner from the Game Catalogue
- `P`: open Promotion Planning from the Game page
- `C`: select waiting work to cancel in Promotion Planning or Update Planner
- `Enter`: choose, advance New Game planning, greenlight, buy, hire, or queue the selected update
- `E`: select Employ while on the Team page, or edit a game title while planning
- `R`: regenerate a game title while planning
- `Left` / `Right`: adjust the secondary genre/theme or selected creative-brief
  field during concept planning; otherwise adjust simulation speed except in Statistics
- `D`: dismiss the selected non-founder employee
- `L`: open professional training for the selected Team-roster member, including the founder
- `Up` / `Down`: select an item or planning field
- `Backspace`: go back within the current page or workflow
- `Esc`: open or close the centered Settings popup from anywhere
- `<` / `>`: activate the bottom `</>` controls; these adjust speed normally, Production Plan values while planning, or Statistics views
- `Space`: pause or resume
- `Ctrl+S`: save
- `Q`: quit

The original footer-style tabs and contextual controls now sit at the top and are
clickable when the terminal exposes curses mouse events, except queueing an update,
which deliberately requires the `Enter` key. Settings stays at the top-right, with
Save and Quit inside its popup. The bottom status strip is visible on every page:
week progress, cash, runway, and — whenever they exist — live progress meters for
the in-development game (`DEV`) and the active contract (`JOB`, a narrower bar),
plus fans and player/contractor trust (`PTrust`/`CTrust`) on wide terminals. Playback
controls sit beside date/year/week and display `||`, `>`, `>>`, and so on. The Hub
is a read-focused studio overview.
The Team page shows a full-width roster with a Person Detail panel — stacked skill
meters on the left, wellbeing (or an applicant's offer with its exact burn and
runway impact) to their right. In the roster and applicant tables the best value
in each skill column is crowned in green bold, and column headers align with the
row content. Its action bar is side-aware: Hire appears only while
employing, Dismiss/Learn only for a roster selection, and the active side is
marked `>[E]mploy<` / `>[T]eam<`.
The Game page opens with an In Production banner while a game is being made:
phase bar, weeks vs plan, ETA, and every current capacity drain (contract,
promotions, updates, training). The Advisor panel recommends the next move.
While planning a game, the theme list is tiered by market signal — themes you
have a proven audience for, then good genre fits (both green), then the rest —
so 300+ themes never need blind scrubbing. Pressing `B` switches the Genre or
Theme list into blend mode (the header swaps PRIMARY for BLEND, your primary
stays marked yellow) so Up/Down picks the mix partner directly — Enter confirms
the blend, `B` again cancels it back to a single genre/theme; a confirmed blend
shows in the panel border (`1 Genre  + Building Game`). On the Production Plan
step the highlighted field shows its value in `<…>` and an adaptive Options row
lists every choice for it (clickable), while the plan list and brief keep your
earlier decisions in view. The Creative
Brief panel groups the concept into Plan, Market (fit range bar, confidence
meter), and Workload (runway vs needed weeks bars) sections, ending with a
plain-language recap of the concept.
Opening Settings temporarily pauses a running game and restores its previous speed
when closed; a game that was already paused stays paused. Use Up/Down to select
Close, Save, or Quit and Enter to activate the highlighted action.
During New Game planning, Enter advances from Genre Mix through Theme Mix and the
Creative Brief to Market & Store, where Enter greenlights an eligible game.
Up/Down chooses a primary genre/theme or planning field; Left/Right chooses the
secondary influence or changes the highlighted concrete decision. Backspace returns
to the previous step. Production-event popups use Up/Down and Enter while all
other simulation controls are locked.
Update Planner keeps the Game Catalogue and planner visible together. Up/Down first
selects a game, then an update scope, then an update area. Enter locks each step and
queues the update from the final step; Backspace moves through those steps in reverse
and returns to the Game page from game selection. In either queue page, press `C`,
use Up/Down to select waiting work, and press Enter to cancel it. Selection remains
active for further cancellations until Backspace returns to ordinary planning.
Rows select games, promotions, applicants,
employees, upgrades, genres, or releases; double-clicking confirms choices where
available; the wheel scrolls lists and changes selections. Game titles still
require keyboard text input.

## Code Layout

The UI follows one design system; every page is assembled from the same
pieces instead of bespoke layouts:

- `ui_common.py`: primitives — clipped text, titled panels, meters, money,
  the shared scrolling selection list (`> ` marker, accent highlight),
  table cells, key/value lines, and queue headers.
- `ui_chrome.py`: the frame around every page — top tabs plus the current
  page's context actions, the persistent bottom status strip (cash, runway,
  `DEV`/`JOB` progress), date/playback bars, and all centered popups
  (Settings, Training, Production Event, Insolvency).
- One module per page: `ui_hub.py`, `ui_newgame.py`, `ui_team.py`,
  `ui_contracts.py`, `ui_games.py` (catalogue, Update Planner, Promotion
  Planning), `ui_upgrades.py`, `ui_stats.py`.
- `ui_input.py`: keyboard and mouse. Overlays capture input first; then
  global keys; then page keys. Mouse hit-testing calls the same layout
  helpers the screens draw with, so clicks cannot drift from rendering.
- `main.py`: entry point — screen dispatch table, curses run loop,
  `--simulate`, CLI parsing.
- `simulation.py` / `game_data.py`: game rules and static data; UI modules
  read them but never the other way around.

Navigation rules are global: `Up/Down` moves a selection, `Enter` is the
primary action, `Backspace` goes one level up, `Left/Right` adjusts the
context's horizontal axis (speed, planning values, statistics views),
`Tab`/`H`/`G`/`T`/`S` switch pages, `Esc` opens Settings.

## Verification

Run the automated simulation tests:

```bash
python -m unittest -v
```

Advance a studio without curses to inspect long-term accounting behavior:

```bash
python main.py --simulate 52
python main.py --load --simulate 12
```
