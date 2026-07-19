"""Upgrades page: purchasable studio equipment and subscriptions."""

from __future__ import annotations

import curses

from simulation import UPGRADES, GameState, monthly_fixed_cost
from ui_common import add_text, draw_box, draw_selectable_list, money


def draw_upgrades(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel = screen.derwin(height - 4, width, 2, 0)
    draw_box(panel, "Upgrades")
    inner = width - 4
    if width >= 100:
        name_width = 28
        purchase_width, monthly_width, status_width = 11, 10, 10
        effect_width = max(14, inner - 73)
        header = f"  {'UPGRADE':<{name_width}} {'PURCHASE':>11} {'MONTHLY':>10} {'STATUS':>10} {'EFFECT':<{effect_width}}"
    else:
        name_width = 18
        purchase_width, monthly_width, status_width = 9, 9, 8
        effect_width = max(8, inner - 55)
        header = f"  {'UPGRADE':<{name_width}} {'BUY':>9} {'MONTHLY':>9} {'STATUS':>8} {'EFFECT':<{effect_width}}"
    add_text(panel, 1, 2, header, inner, curses.A_BOLD)
    rows = []
    for upgrade in UPGRADES:
        owned = upgrade["key"] in state.studio.upgrades
        recurring = upgrade.get("monthly", 0) + upgrade.get("per_employee", 0) * len(state.studio.team)
        status = "ACTIVE" if owned else "AVAILABLE"
        text = f"{upgrade['name'][:name_width]:<{name_width}} {money(upgrade['cost']):>{purchase_width}} {money(recurring):>{monthly_width}} {status:>{status_width}} {upgrade['effect'][:effect_width]:<{effect_width}}"
        rows.append((text, curses.color_pair(4) if owned else 0))
    draw_selectable_list(panel, rows, state.selected_upgrade, True, y=2, width=width - 4, scroll=False, highlight_wins=False)
    add_text(panel, len(UPGRADES) + 3, 2, f"Current committed monthly burn: {money(monthly_fixed_cost(state.studio))} | Enter/double-click purchases selected upgrade", width - 4, curses.color_pair(4))
