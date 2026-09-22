# Indie Studio Game Dev Sim

You start as a one-person indie developer on the current day. Keep the studio alive, take contracts, make games, grow a team, research new capabilities, and build an IP that can eventually become iconic.

## Requirements

- Python 3.10 or newer
- A terminal at least 74 columns by 24 rows
- No external Python packages are required (on Windows: `pip install windows-curses`)

## Compatibility

On modern terminals the game keeps the terminal's own palette, so a themed emulator (for example Ghostty with Tokyo Night) looks exactly like the rest of your setup; pass `--theme tokyo` to force the built-in Tokyo Night palette everywhere. On legacy consoles (old Windows cmd) the game forces a high-contrast dark scheme so the default colors cannot wash the UI out, and it switches meters, charts, and the logo to plain ASCII where Unicode blocks are unsupported; force a glyph mode with `--ascii` or `--unicode` (or `GAMEDEV_ASCII=1`). For the best look on Windows use Windows Terminal. Rendering adapts to any window size and is frame-limited, so large high-resolution terminals stay fast.

## Start

### Browser interface (preview)

```bash
python browser.py
```

Opens a local browser interface at `http://127.0.0.1:8765`. It uses the
existing Python simulation and version 11 saves, without curses, external
Python dependencies, accounts, CDN assets, or internet access. Python 3.10+
and a modern browser are required on Windows, Linux, and macOS.

The preview introduces Studio, Projects, People, Business, and Market pages
with the blue/lavender, yellow, and green terminal palette. JetBrains Mono
2.304 is bundled locally under its SIL Open Font License (see
`web/fonts/OFL.txt`), matching the font face reported by Ghostty on the
development machine. Browser and terminal rasterization can still differ.
Compact top
navigation replaces the sidebar. Main pages fit the viewport; detailed
choices open in scrollable popups with a slim themed scrollbar. Only the
staged Design & Production form retains Previous/Next steps. Dropdowns use
the themed native picker where supported, with a native fallback elsewhere.
Time runs continuously with the original simulation speeds and a filling
week bar in the persistent footer. The meter interpolates on animation frames
between authoritative server updates rather than visibly stepping at the
polling interval. Studio uses a fixed two-column overview of finances, work,
team fatigue/morale, market pulse, releases and recent activity, with direct work-start actions in
each relevant work row. Player and contractor trust appear in the footer as
`PTrust` and `CTrust`, matching the terminal status bar.
Popups and outstanding production decisions hold time. An uncommitted Design
does not freeze the studio or market: production waits, but time keeps running
after closing the review. Closing a popup preserves your previous pause/speed
choice. An inactive/disconnected browser stops advancing after three seconds;
missed time is not fast-forwarded on reconnect.

Projects has a production workspace, idea shelf and design evidence. People
shows individual skills, condition and vacation actions directly in the roster
(with roster paging for larger teams). Business shows monthly revenue/expense
history, fixed-cost composition, debt and capacity allocation. Market shows
the complete simulation chart directly in the page — every ranked game, the
panel filling its space and scrolling when the pointer is over it — with chart
sales share by studio and your catalogue. Competitor release sales and ledger
records open in scrollable detail views. Charts are local SVGs with no
external dependencies; empty histories remain empty rather than displaying
invented data.

Studio uses a compact four-value status strip, then puts Game and Contract
commands side-by-side. An active game shows its exact stage/phase, completion,
schedule, estimated remaining time, scope, hype, defects and tracked cost.
Team count and payroll sit with Team Condition; Team Condition and Market Pulse
share the right-side overview. Research and studio upgrades live under Business
rather than occupying a Studio command slot. The release-health table shows
weekly and lifetime sales, hype, net revenue, tracked profit, known bugs,
players and support without requiring one large card per game.
Market Pulse shows ten ranked games with the publisher behind each title in a
smaller accent colour, and its Full chart action opens the complete ranking.
Selecting a Studio release-table
row replaces the Original Game command with compact update and support controls;
use its detailed operations action to inspect weekly sales history, player
response and operating queues;
choose an update size/focus, cycle support, adjust price, fund a marketing
campaign or start a community action. Costs and research/reputation requirements
are shown before spending; the simulation still enforces its funding gates.
The Projects workspace also exposes hype, tracked costs and pre-release
marketing/community controls. Revenue is not profit; profit uses the same
tracked game-cost calculation as the terminal UI. WTD means week-to-date.

Browser controls: `H/G/T/B/S` switch pages, `N` opens ideas, `J` jobs,
`U` research, `F` financing, and `P` the catalogue. `Space` pauses/resumes;
`Left/Right` or `</>` change speed. `Up/Down` focus controls and `Enter`
activates them; `Tab` retains normal browser focus navigation. `Esc` closes
a popup or opens settings, `Backspace` closes a popup or returns to Studio,
and `Ctrl+S` saves. Form fields keep their native editing keys. On the
Projects page `E` enters Design and `T` opens presentation choices during
Design; on People `E` opens applicants.
Use **Save studio** before closing the server. To avoid overwriting your
existing save while trying it, use `python browser.py --save-file saves/browser-preview.json`.

Options: `--port 8765`, `--no-browser`, and `--save-file PATH`.
This is the first playable browser slice, not yet feature parity with the
terminal: detailed training/dismissal controls, presentation-axis tweaking,
queue cancellation controls, additional statistics,
and a full save-slot interface remain to be migrated.

Browser checks: `python -m unittest test_browser`. Optional real Chromium
smoke test: install Playwright in your testing environment, install its
Chromium browser, and run `node web/browser-smoke.cjs` from the repository
root. `node web/browser-views.cjs` checks populated layouts at four viewport
sizes; set `SCREENSHOT_DIR` to an existing directory to capture each page.
`node web/browser-operations.cjs` exercises real post-release API actions and
checks populated Studio layouts and ten-row Market charts.
Playwright is not a game runtime dependency.

### Original terminal interface

```bash
python main.py
```

The title screen lets you start a new studio or load the default save.

## Saves

To load a save directly instead of using the title screen:

```bash
python main.py --load
python main.py saves/gamedev_save.json
python main.py --load saves/gamedev_save.json
```

Use a different save path for a new run:

```bash
python main.py --save-file saves/my_studio.json
```

Use `Ctrl+S` in-game to save. Saves are compatible with the current release only. Version 11 replaces the genre/theme wizard with the idea-driven pipeline; older saves cannot be migrated.

## Quick Tutorial

1. Start on the **Hub**. Watch cash and runway: monthly payroll and operations are real costs.
2. Press `J` for **Jobs**. Contracts provide early survival income, but use team capacity and can cause fatigue.
3. Press `N` to open the **Idea Shelf**. Your team jots down rough game ideas over time; pick one and explore it in **Concept** by running experiments that produce findings.
4. End Concept to review the **Design & Technical Plan**: choose a presentation direction, adjust the axes if you disagree with the team's advice, set scope, platforms, and monetization, then commit to production.
5. Press `U` for **Studio Development**. Research unlocks larger scopes, more formats, promotion, online capabilities, better staffing, and automation.
6. Press `T` for **Team**. Hire carefully, train people with `L`, and give tired staff a one-week vacation with `V`. Team skill and morale shape both the ideas they pitch and the advice they give.
7. After release, use the **Game** page for updates, promotion, sequels, spin-offs, and support level. Releases spark follow-up ideas on the shelf.

Micro games take roughly 3–6 months with a healthy minimum team. Blockbusters take roughly 6–7 years. Do not overcommit: games, contracts, updates, promotions, R&D, and live support share one studio capacity budget.

## Controls

- `Tab`: cycle Hub, Game, Team, Statistics
- `H` / `G` / `T` / `S`: jump to a top-level page
- `N`: Idea Shelf (start a new game from a team idea; sequels and spin-offs grow from releases)
- `J`: Jobs / contract board
- `U`: Studio Development
- `P`: Promotion Planning from Game
- `Enter`: confirm the current action
- `Up` / `Down`: move selection
- `Left` / `Right` or `<` / `>`: change the current context or game speed
- `Space`: pause/resume
- `L`: train selected team member
- `V`: schedule selected team member's vacation
- `D`: dismiss selected non-founder
- `C`: cancel waiting update/promotion/R&D work where available
- `Ctrl+S`: save
- `Esc`: settings
- `Q`: quit

## Progression

Studio Development has Product, Operations, People, Business, and Live Ops branches. Research takes time and money; specializing makes related research faster, but every branch remains available.

Locked genres and themes are hidden until their research is complete. IP rank uses combined lifetime sales: Niche at 10,000 units, Recognized at 100,000, and Iconic at 10,000,000 units.

## Testing

```bash
python -m unittest test_simulation
```
