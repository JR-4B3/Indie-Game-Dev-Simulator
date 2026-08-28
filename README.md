# Indie Studio Game Dev Sim

You start as a one-person indie developer on the current day. Keep the studio alive, take contracts, make games, grow a team, research new capabilities, and build an IP that can eventually become iconic.

## Requirements

- Python 3.10 or newer
- A terminal at least 74 columns by 24 rows
- No external Python packages are required (on Windows: `pip install windows-curses`)

## Compatibility

On modern terminals the game keeps the terminal's own palette, so a themed emulator (for example Ghostty with Tokyo Night) looks exactly like the rest of your setup; pass `--theme tokyo` to force the built-in Tokyo Night palette everywhere. On legacy consoles (old Windows cmd) the game forces a high-contrast dark scheme so the default colors cannot wash the UI out, and it switches meters, charts, and the logo to plain ASCII where Unicode blocks are unsupported; force a glyph mode with `--ascii` or `--unicode` (or `GAMEDEV_ASCII=1`). For the best look on Windows use Windows Terminal. Rendering adapts to any window size and is frame-limited, so large high-resolution terminals stay fast.

## Start

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
