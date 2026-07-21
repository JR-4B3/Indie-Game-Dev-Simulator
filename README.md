# Indie Studio Game Dev Sim

You start as a one-person indie developer on the current day. Keep the studio alive, take contracts, make games, grow a team, research new capabilities, and build an IP that can eventually become iconic.

## Requirements

- Python 3.10 or newer
- A terminal at least 74 columns by 24 rows
- No external Python packages are required

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

Use `Ctrl+S` in-game to save. Saves are compatible with the current release only.

## Quick Tutorial

1. Start on the **Hub**. Watch cash and runway: monthly payroll and operations are real costs.
2. Press `J` for **Jobs**. Contracts provide early survival income, but use team capacity and can cause fatigue.
3. Press `N` to plan a game. Begin with a Micro or Compact project, choose a genre, theme, plan, and storefront, then greenlight it.
4. Press `U` for **Studio Development**. Research unlocks larger scopes, more genres/themes, promotion, online formats, DLC, better staffing, and automation.
5. Press `T` for **Team**. Hire carefully, train people with `L`, and give tired staff a one-week vacation with `V`.
6. After release, use the **Game** page for updates, promotion, sequels, spin-offs, and support level.

Micro games take roughly 3–6 months with a healthy minimum team. Blockbusters take roughly 6–7 years. Do not overcommit: games, contracts, updates, promotions, R&D, and live support share one studio capacity budget.

## Controls

- `Tab`: cycle Hub, Game, Team, Statistics
- `H` / `G` / `T` / `S`: jump to a top-level page
- `N`: new game, sequel, or spin-off
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
