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

An old version-one save is migrated into a present-day studio. Its cash,
followers, reputation, and release count are retained where possible; obsolete
1970s projects and fixed employees are not.

## The Simulation

- **Real calendar and accounting:** weeks use the current calendar. Salaries,
  employer payroll burden, software seats, insurance, administration, upgrade
  subscriptions, and estimated quarterly income tax affect cash.
- **Runway, not points:** the key studio metric is how many months remain at the
  currently committed burn. The game prevents a hire or purchase when it would
  leave less than one month for bills.
- **Production by work:** Micro, Small, and Ambitious projects require different
  amounts of work. Completion time changes with team skill, morale, fatigue,
  hardware, and time diverted to client contracts.
- **Production phases and defects:** projects move through prototype,
  pre-production, production, alpha, and beta. Team code skill and QA equipment
  influence defect load and launch refunds. Testing reveals only part of the real
  defect count, so the interface reports known bugs rather than perfect information.
- **A real small team:** six new applicants are generated each month with a role,
  seniority, salary expectation, four skills, morale, fatigue, and a working
  trait. Employees gain experience, can improve, resign when neglected, and cost
  severance to dismiss. As releases, followers, reputation, and revenue grow, the
  suggested headcount and applicant pool grow too; hiring remains your decision.
- **Studio statistics:** four switchable views provide a studio overview,
  solid-color revenue/expense breakdowns, vertical monthly cash-flow columns,
  statistics for every genre, and a permanent release catalog. Accounting keeps
  contract and game revenue separate and retains payroll, employer costs,
  operations, development, marketing, taxes, equipment, hosting, recruiting,
  and severance categories.
- **Named games and franchises:** every project starts with a generated title
  based on its genre and theme. Reroll it or type a custom name. Releases retain
  score, units, net revenue, genre, theme, and sequel lineage. Genre and theme
  audiences grow from actual buyers, and established audiences improve sequel
  discoverability without guaranteeing success. Starting a new game first opens
  an Original Game / Sequel chooser populated by prior releases.
- **Game Catalogue:** every released game remains on sale. Genre/theme
  fit, quality, defects, platform, reputation, followers, scope, and storefront
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
  cash, run for multiple weeks, and some consume substantial team time.
- **Live operations:** updates are planned and added to a studio-wide FIFO queue.
  Choose Bug fixes, Balance, Visual, Audio, or New content and a Hotfix, Patch,
  Content, or Expansion scope. Relevant employee skill determines duration; every
  update must then clear a bug-fixing phase before it can ship. Scopes advance the
  public version by `0.00.01`, `0.00.10`, `0.01.00`, or `0.10.00`. Larger updates
  cost more and consume more team capacity. Shipping restores hype, sales, and
  monthly players in proportion to the game's rating. Bug-fix-focused updates also
  remove existing defects, although a small number of new defects can escape QA.
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
  it is not recovered, the studio closes.

## Controls

- `N`: plan a new game
- `J`: open the Contract Board and accept one selected contract
- `C`: toggle automatic contract acceptance and queue all eligible board offers
- `T`: open team management
- `E`: legacy alias for team management
- `U`: open Upgrades
- `G`: open the Game Catalogue
- `Tab`: expand or close the Update Planner inside the Game Catalogue
- `Enter`: queue the selected game's update plan
- `F`: cycle the update area for the selected live game
- `Z`: cycle Hotfix, Patch, Content, and Expansion update scopes
- `M`: open Promotion Planning for the current project or selected catalogue game
- `S`: open Studio Statistics
- `T`: type a custom game title while planning
- `R`: generate another title from the selected genre and theme
- `Enter`: choose a project, greenlight a production plan, queue an update, hire, or purchase
- `Tab`: switch planning panels, update views, promotion panels, applicants, or current staff
- `Tab` / `Left` / `Right`: switch statistics views
- `D`: dismiss the selected non-founder employee
- `Up` / `Down`: select an item or planning field
- `Left` / `Right`: adjust a production plan; on the dashboard, change speed
- `Backspace` or `Esc`: go back; on the dashboard, `Esc` opens Settings
- `Space`: pause or resume
- `Ctrl+S`: save
- `Q`: quit

Footer controls are clickable when the terminal exposes curses mouse events, except
queueing an update, which deliberately requires the `Enter` key.
The dashboard panels open production, team, statistics, and the live catalog; rows
select projects, games, promotions, applicants, employees, upgrades, genres, or
releases; double-clicking confirms choices where available; the wheel scrolls lists,
changes promotion targets, adjusts planning fields, and changes
dashboard speed; right-click closes the current screen. Game titles still require
keyboard text input, but generated and randomized titles are clickable.

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
