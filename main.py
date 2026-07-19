from __future__ import annotations

import argparse
import curses
import json
import time
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from game_data import GENRES, TOPICS
from simulation import (
    AUDIENCES,
    CHANNELS,
    CREATIVE_DIRECTIONS,
    EMPLOYEE_SKILLS,
    GAME_FORMATS,
    MARKETING,
    PROMOTIONS,
    PRODUCTION_DECISIONS,
    QUIRKS,
    RELEASE_STRATEGIES,
    SCOPES,
    SKILLS,
    TRAITS,
    TIME_LABELS,
    TIME_SPEEDS,
    UPDATE_FOCUSES,
    UPDATE_SIZES,
    UPGRADES,
    GameState,
    accept_contract_offer,
    advance_game,
    applicant_pool_size,
    buy_upgrade,
    buy_promotion,
    cancel_queued_promotion,
    cancel_queued_update,
    cycle_game_update_focus,
    cycle_game_update_size,
    concept_focus,
    dismiss_employee,
    expense_breakdown,
    game_by_id,
    game_profit,
    game_total_cost,
    estimated_contract_weeks,
    estimated_update_delivery_weeks,
    hire_candidate,
    load_game,
    monthly_fixed_cost,
    market_report,
    plan_requirements,
    prepare_sequel,
    planned_update_version,
    projected_weekly_output,
    queue_game_update,
    recommended_team_size,
    refresh_draft_title,
    revenue_breakdown,
    resolve_project_decision,
    runway_months,
    save_game,
    sale_for_game,
    selected_roster_employee,
    start_employee_training,
    start_project,
    training_cost,
    toggle_auto_contracts,
)


DEFAULT_SAVE_FILE = "gamedev_save.json"
NAVIGATION_KEYS = {curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT, curses.KEY_RIGHT}
CTRL_S = 19
ESCAPE_KEYS = (27, getattr(curses, "KEY_EXIT", -1))
SETTINGS_ACTIONS = ("Close", "Save", "Quit")
SETTINGS_ACTION_ROWS = (6, 8, 10)
TOP_TABS = (
    ("Hub", "H", "main"),
    ("Game", "G", "games"),
    ("Team", "T", "team"),
    ("Statistics", "S", "analysis"),
)
MODAL_TAB_INDEX = {
    "main": 0,
    "contracts": 0,
    "upgrades": 0,
    "settings": 0,
    "games": 1,
    "update_planner": 1,
    "new_game": 1,
    "marketing": 1,
    "team": 2,
    "analysis": 3,
}


def active_top_tab(state: GameState) -> int:
    return MODAL_TAB_INDEX.get(state.modal, 0)


def activate_top_tab(state: GameState, index: int) -> None:
    state.naming_game = False
    state.queue_cancellation = ""
    state.modal = TOP_TABS[index % len(TOP_TABS)][2]
    if state.modal == "games":
        state.games_tab = 0


def cycle_top_tab(state: GameState, delta: int = 1) -> None:
    activate_top_tab(state, (active_top_tab(state) + delta) % len(TOP_TABS))


def centered_layout(actions: list[tuple[str, str]], width: int) -> list[tuple[str, str, int]]:
    available = max(1, width - 2)
    total = sum(len(label) for label, _ in actions) + max(0, len(actions) - 1)
    x = 1 + max(0, (available - total) // 2)
    layout = []
    for label, action in actions:
        if x + len(label) > width - 1:
            break
        layout.append((label, action, x))
        x += len(label) + 1
    return layout


def control_label(control: str, text: str) -> str:
    matches = len(control) == 1 and text[:1].lower() == control.lower()
    suffix = text[1:] if matches else f" {text}"
    return f"[{control}]{suffix}"


def top_tab_actions(state: GameState) -> list[tuple[str, str]]:
    active = active_top_tab(state)
    actions = []
    for index, (name, key, _) in enumerate(TOP_TABS):
        label = f">[{key}]{name[1:]}<" if index == active else f"[{key}]{name[1:]}"
        actions.append((label, f"top_tab_{index}"))
    return actions


def top_tab_layout(state: GameState, width: int) -> list[tuple[str, int, int]]:
    x = 2
    layout = []
    for label, action in top_tab_actions(state):
        layout.append((action, x, x + len(label)))
        x += len(label) + 1
    return layout


def top_context_uses_second_row(state: GameState, width: int) -> bool:
    context = footer_layout(state, width)
    if not context:
        return False
    tab_end = top_tab_layout(state, width)[-1][2]
    global_start = global_action_layout(state, width)[0][2]
    context_start = context[0][2]
    context_end = context[-1][2] + len(context[-1][0])
    return context_start <= tab_end or context_end >= global_start


def top_control_layout(state: GameState, width: int) -> list[tuple[str, str, int]]:
    labels = {action: label for label, action in top_tab_actions(state)}
    layout = [(labels[action], action, start) for action, start, _ in top_tab_layout(state, width)]
    if not top_context_uses_second_row(state, width):
        layout.extend(footer_layout(state, width))
    layout.extend(global_action_layout(state, width))
    return layout


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:.2f}m"
    if value >= 100_000:
        return f"{sign}${value / 1_000:.0f}k"
    return f"{sign}${value:,.0f}"


def update_status(game) -> str:
    return f"v{game.version} | {game.updates_released} update{'s' if game.updates_released != 1 else ''} shipped"


def game_title(game, width: int | None = None) -> str:
    suffix = f" v{game.version}"
    if width is None:
        return game.title + suffix
    return game.title[: max(1, width - len(suffix))] + suffix


def rating_text(game) -> str:
    return "n/a" if game.release_date == "Historical" else str(game.score)


def meter(value: float, maximum: float, width: int) -> str:
    filled = max(0, min(width, round(width * value / max(1, maximum))))
    return "█" * filled + "░" * (width - filled)


def game_recommendation(game) -> tuple[str, int]:
    if game.score < 45:
        return "Low rating: updates have weak returns. Invest in the next game instead.", 5
    if game.monthly_players < 10 and game.score >= 70:
        return "Dormant but well rated: a Content update can revive former owners.", 4
    if game.monthly_players < 10:
        return "Very few monthly players: promotion or updates are financially risky.", 5
    if game.hype < 15 and game.score >= 65:
        return "Good reception, low hype: promotion or New content has strong potential.", 4
    if game.monthly_players > 1_000:
        return "Healthy audience: regular patches can protect retention.", 4
    return "Stable niche audience: compare update cost and estimated duration before committing.", 3


def add_text(window: curses.window, y: int, x: int, text: str, width: int, attr: int = 0) -> None:
    max_y, max_x = window.getmaxyx()
    if width <= 0 or y < 0 or y >= max_y or x < 0 or x >= max_x - 1:
        return
    window.addstr(y, x, text[: min(width, max_x - x - 1)], attr)


def draw_box(window: curses.window, title: str) -> None:
    height, width = window.getmaxyx()
    if height < 3 or width < 4:
        return
    window.attron(curses.color_pair(2))
    window.border()
    window.attroff(curses.color_pair(2))
    add_text(window, 0, 2, f" {title} ", width - 4, curses.color_pair(3) | curses.A_BOLD)


def draw_header(screen: curses.window, state: GameState, width: int) -> None:
    bar_width = width - 2
    add_text(screen, 0, 1, " " * bar_width, bar_width, curses.color_pair(1))
    for label, _, x in top_control_layout(state, width):
        draw_footer_label(screen, 0, x, label, width)
    if top_context_uses_second_row(state, width):
        add_text(screen, 1, 1, " " * bar_width, bar_width, curses.color_pair(1))
        for label, _, x in footer_layout(state, width):
            draw_footer_label(screen, 1, x, label, width)


def draw_live_operations(panel: curses.window, state: GameState, panel_width: int, start_row: int) -> None:
    studio = state.studio
    active = 1 if studio.active_update else 0
    promotion_active = 1 if studio.active_promotions else 0
    add_text(panel, start_row, 2, f"Update queue {active + len(studio.update_queue)} ({active} active) | Promotion queue {len(studio.active_promotions)} ({promotion_active} active)", panel_width - 4)
    add_text(panel, start_row + 1, 2, f"Monthly players {sum(game.monthly_players for game in studio.catalog):,} | Weekly game sales {sum(sale.weekly_units for sale in studio.active_sales):,}", panel_width - 4)


def draw_contract_status(panel: curses.window, state: GameState, panel_width: int, start_row: int) -> None:
    studio = state.studio
    active = studio.contract
    add_text(panel, start_row, 2, f"[C] Auto contracts {'ON' if studio.auto_contracts else 'OFF'} | Queue {len(studio.contract_queue)} | Contractor rep {studio.contractor_reputation:.1f}", panel_width - 4, curses.A_BOLD)
    if active:
        progress = 0 if active.required_work <= 0 else active.work_done / active.required_work
        add_text(panel, start_row + 1, 2, f"Active: {active.client} / {active.focus}", panel_width - 4)
        add_text(panel, start_row + 2, 2, f"[{meter(progress, 1, 16)}] {progress:.0%} | due {active.weeks_left}w | {money(active.payout)}", panel_width - 4, curses.color_pair(4))
    else:
        add_text(panel, start_row + 1, 2, "No active contract", panel_width - 4)
        add_text(panel, start_row + 2, 2, "J  open Jobs to accept client work", panel_width - 4)


def draw_dashboard(screen: curses.window, state: GameState, width: int) -> int:
    left_width = max(34, width // 2)
    right_width = width - left_width - 1
    finance_height = 16 if width >= 120 else 8
    finance = screen.derwin(finance_height, left_width, 2, 0)
    command_height = 16 if width >= 120 else 8
    project_panel = screen.derwin(command_height, right_width, 2, left_width + 1)
    draw_box(finance, "Finance")
    draw_box(project_panel, "Production Command")

    studio = state.studio
    burn = monthly_fixed_cost(studio)
    runway = runway_months(studio)
    runway_text = f"{runway:.1f} months" if runway < 99 else "99+ months"
    add_text(finance, 1, 2, f"Bank balance       {money(studio.cash)}", left_width - 4, curses.A_BOLD if studio.cash >= 0 else curses.color_pair(5) | curses.A_BOLD)
    add_text(finance, 2, 2, f"Committed burn     {money(burn)}/month", left_width - 4)
    add_text(finance, 3, 2, f"Runway             {runway_text}", left_width - 4, curses.color_pair(5) if runway < 4 else 0)
    add_text(finance, 4, 2, f"This month         {money(studio.period_revenue)} in / {money(studio.period_expenses)} out", left_width - 4)
    add_text(finance, 5, 2, f"Tax reserve        {money(studio.tax_reserve)}", left_width - 4, curses.color_pair(4))
    lifetime_net = studio.lifetime_revenue - studio.lifetime_expenses
    add_text(finance, 6, 2, f"Lifetime result    {money(lifetime_net)}", left_width - 4, curses.color_pair(4) if lifetime_net >= 0 else curses.color_pair(5))
    if width >= 120:
        add_text(finance, 8, 2, "RECENT ACTIVITY", left_width - 4, curses.A_BOLD)
        if not studio.ledger:
            add_text(finance, 9, 2, "No closed months yet.", left_width - 4)
        for row, entry in enumerate(studio.ledger[:6], 9):
            text = f"{entry.month}  revenue {money(entry.revenue):>9}  expenses {money(entry.expenses):>9}  net {money(entry.net):>9}"
            add_text(finance, row, 2, text, left_width - 4, curses.color_pair(4) if entry.net >= 0 else curses.color_pair(5))

    project = studio.current_project
    if project is None:
        add_text(project_panel, 1, 2, "GAME", 4, curses.A_BOLD)
        add_text(project_panel, 1, 8, "No original game in production", right_width - 10)
        add_text(project_panel, 2, 2, "Press N here or open Game with G to plan a release", right_width - 4)
        add_text(project_panel, 3, 2, f"Game Catalogue {len(studio.catalog)} | Promotion queue {len(studio.active_promotions)} | Update queue {len(studio.update_queue) + bool(studio.active_update)}", right_width - 4)
    else:
        phase_labels = {
            "Pre-production": "Pre-prod",
            "Alpha / content lock": "Alpha",
            "Beta / release prep": "Beta",
        }
        phase = phase_labels.get(project.phase, project.phase)
        phase_width = min(10, max(8, right_width - 20))
        bar_width = max(8, right_width - 12 - phase_width)
        filled = round(bar_width * project.progress)
        bar = "█" * filled + "░" * (bar_width - filled)
        weekly_output = projected_weekly_output(studio, project.focus)
        remaining = max(1, round((project.total_work - project.work_done) / weekly_output))
        add_text(project_panel, 1, 2, "GAME", 4, curses.A_BOLD)
        add_text(project_panel, 1, 8, project.title, right_width - 10)
        add_text(project_panel, 2, 2, f"{phase[:phase_width]} [{bar}] {project.progress:>4.0%}", right_width - 4, curses.color_pair(4))
        add_text(project_panel, 3, 2, "PLAN", 4)
        plan_text = f"Week {project.weeks} | about {remaining}w left / {project.planned_weeks}w planned"
        add_text(project_panel, 3, 8, plan_text, right_width - 10)
        if studio.contract:
            contract_note = " | Contract is cutting capacity by 45%" if right_width >= 90 else " | Contract capacity -45%"
            add_text(project_panel, 3, 8 + len(plan_text), contract_note, right_width - 10 - len(plan_text), curses.color_pair(5))
        platform_text = f"{project.scope} / {project.channel} / {money(project.price)} retail"
        if not studio.contract:
            platform_text += f" | Hype {project.hype:.0f} | Known bugs {int(project.known_defects)}"
        add_text(project_panel, 4, 2, platform_text, right_width - 4)
        add_text(project_panel, 5, 2, f"Tracked cost {money(project.production_cost + project.labor_cost + project.marketing_cost)} | Marketing {money(project.marketing_cost)}", right_width - 4)
    if width >= 120:
        add_text(project_panel, 7, 2, "OPERATIONS", right_width - 4, curses.A_BOLD)
        draw_live_operations(project_panel, state, right_width, 8)
        add_text(project_panel, 11, 2, "CONTRACTS", right_width - 4, curses.A_BOLD)
        draw_contract_status(project_panel, state, right_width, 12)
    return 10


def draw_main_content(screen: curses.window, state: GameState, width: int, height: int, y: int) -> None:
    studio = state.studio
    journal_height = 7 if height >= 32 else 4
    journal_y = height - journal_height - 2

    left_width = width // 2
    right_width = width - left_width - 1
    if width >= 120:
        team_y = 18
        team_height = max(0, journal_y - team_y)
        catalogue_y = 18
        catalogue_height = max(0, journal_y - catalogue_y)

        if team_height >= 3:
            team = screen.derwin(team_height, left_width, team_y, 0)
            total_payroll = sum(employee.monthly_salary for employee in studio.team)
            draw_box(team, f"Team | {len(studio.team)}/{recommended_team_size(studio)} suggested | {money(total_payroll)}/month")
            team_inner_width = left_width - 4
            team_expanded = team_inner_width >= 85
            if team_expanded:
                role_width = max(16, team_inner_width - 69)
                team_header = f"{'NAME':<16} {'ROLE':<{role_width}} {'TOP SKILL':<12} {'MORALE':>6} {'FATIGUE':>7} {'COST/MO':>8} {'PERSONALITY':<14}"
            else:
                role_width = max(10, min(28, team_inner_width - 39))
                team_header = f"{'NAME':<14} {'ROLE':<{role_width}} {'MORALE':>6} {'FATIGUE':>7} {'COST/MO':>8}"
            add_text(team, 1, 2, team_header, team_inner_width, curses.A_BOLD)
            for row, employee in enumerate(studio.team[: team_height - 3], 2):
                name = employee.name + (" *" if employee.founder else "")
                if team_expanded:
                    top_skill_index = max(range(len(SKILLS)), key=lambda index: employee.skills[index])
                    top_skill = f"{SKILLS[top_skill_index]} {employee.skills[top_skill_index]}"
                    text = f"{name[:16]:<16} {employee.role[:role_width]:<{role_width}} {top_skill:<12} {employee.morale:>6.0f} {employee.fatigue:>7.0f} {money(employee.monthly_salary):>8} {employee.trait[:14]:<14}"
                else:
                    text = f"{name[:14]:<14} {employee.role[:role_width]:<{role_width}} {employee.morale:>6.0f} {employee.fatigue:>7.0f} {money(employee.monthly_salary):>8}"
                attr = curses.color_pair(5) if employee.morale < 30 or employee.fatigue > 70 else 0
                add_text(team, row, 2, text, team_inner_width, attr)

        if catalogue_height >= 3:
            portfolio = screen.derwin(catalogue_height, right_width, catalogue_y, left_width + 1)
            draw_box(portfolio, f"Game Catalogue | {len(studio.catalog)} {'game' if len(studio.catalog) == 1 else 'games'}")
            portfolio_inner_width = right_width - 4
            catalogue_expanded = width >= 170
            if catalogue_expanded:
                portfolio_title_width = max(18, portfolio_inner_width - 53)
                portfolio_header = f"{'GAME':<{portfolio_title_width}} {'RATING':>6} {'HYPE':>6} {'BUGS':>6} {'SALES':>7} {'REVENUE':>11} {'PROFIT':>11}"
            else:
                portfolio_title_width = max(12, portfolio_inner_width - 39)
                portfolio_header = f"{'GAME':<{portfolio_title_width}} {'RATE':>4} {'HYPE':>4} {'BUGS':>4} {'SALES':>5} {'REVENUE':>8} {'PROFIT':>8}"
            add_text(portfolio, 1, 2, portfolio_header, portfolio_inner_width, curses.A_BOLD)
            for row, game in enumerate(live_games(state)[: catalogue_height - 3], 2):
                sale = sale_for_game(studio, game.game_id)
                if catalogue_expanded:
                    profit = money(game_profit(game)) if game.cost_history_complete else "n/a"
                    title = game_title(game, portfolio_title_width)
                    text = f"{title:<{portfolio_title_width}} {rating_text(game):>6} {game.hype:>6.0f} {game.known_bug_count:>6} {(sale.weekly_units if sale else 0):>7,} {money(game.net_revenue):>11} {profit:>11}"
                else:
                    profit = money(game_profit(game)) if game.cost_history_complete else "n/a"
                    title = game_title(game, portfolio_title_width)
                    text = f"{title:<{portfolio_title_width}} {rating_text(game):>4} {game.hype:>4.0f} {game.known_bug_count:>4} {(sale.weekly_units if sale else 0):>5,} {money(game.net_revenue):>8} {profit:>8}"
                add_text(portfolio, row, 2, text, portfolio_inner_width, curses.color_pair(4) if game.score >= 70 else 0)

    else:
        available = max(0, journal_y - y)
        middle_height = available if available < 16 else (available + 1) // 2
        lower_y = y + middle_height
        lower_height = max(0, journal_y - lower_y)
        if middle_height >= 3:
            team = screen.derwin(middle_height, left_width, y, 0)
            portfolio = screen.derwin(middle_height, right_width, y, left_width + 1)
            draw_box(team, f"Team | {len(studio.team)}/{recommended_team_size(studio)} suggested")
            draw_box(portfolio, f"Game Catalogue | {len(studio.catalog)} {'game' if len(studio.catalog) == 1 else 'games'}")
            add_text(team, 1, 2, f"{'NAME':<14} {'MOR':>3} {'FAT':>3} {'COST':>8}", left_width - 4, curses.A_BOLD)
            for row, employee in enumerate(studio.team[: middle_height - 3], 2):
                add_text(team, row, 2, f"{employee.name[:14]:<14} {employee.morale:>3.0f} {employee.fatigue:>3.0f} {money(employee.monthly_salary):>8}", left_width - 4)
            for row, game in enumerate(live_games(state)[: middle_height - 2], 1):
                sale = sale_for_game(studio, game.game_id)
                add_text(portfolio, row, 2, f"{game_title(game)}: R{rating_text(game)} {(sale.weekly_units if sale else 0):,}/w {game.monthly_players:,} monthly", right_width - 4)
        if lower_height >= 4:
            trend = screen.derwin(lower_height, left_width, lower_y, 0)
            operations = screen.derwin(lower_height, right_width, lower_y, left_width + 1)
            draw_box(trend, "Recent Financial Trend")
            draw_box(operations, "Contracts")
            for row, entry in enumerate(studio.ledger[: lower_height - 2], 1):
                text = f"{entry.month}  revenue {money(entry.revenue):>9}  expenses {money(entry.expenses):>9}  net {money(entry.net):>9}"
                add_text(trend, row, 2, text, left_width - 4, curses.color_pair(4) if entry.net >= 0 else curses.color_pair(5))
            add_text(operations, 1, 2, "OPERATIONS", right_width - 4, curses.A_BOLD)
            draw_live_operations(operations, state, right_width, 2)
            add_text(operations, 5, 2, "CONTRACT STATUS", right_width - 4, curses.A_BOLD)
            draw_contract_status(operations, state, right_width, 6)

    activity = screen.derwin(journal_height, width, journal_y, 0)
    draw_box(activity, "Recent Activity")
    for row, message in enumerate(state.logs[: journal_height - 2], 1):
        add_text(activity, row, 2, message, width - 4)


def draw_list(window: curses.window, items: list[str], selected: int, active: bool) -> None:
    height, width = window.getmaxyx()
    visible = max(1, height - 2)
    start = list_start(selected, len(items), visible)
    for row, item in enumerate(items[start : start + visible], 1):
        index = start + row - 1
        marker = ">" if index == selected else " "
        attr = curses.color_pair(3) | curses.A_BOLD if active and index == selected else 0
        add_text(window, row, 2, f"{marker} {item}", width - 4, attr)


def list_start(selected: int, item_count: int, visible: int) -> int:
    return max(0, min(selected - visible // 2, item_count - visible))


def sequel_choices(state: GameState) -> list:
    return [None] + list(reversed(state.studio.catalog))


def draw_project_type(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel = screen.derwin(height - 4, width, 2, 0)
    draw_box(panel, "Start Production | Original Game or Sequel")
    add_text(panel, 1, 2, "Choose an original concept or continue one of your released games.", width - 4, curses.color_pair(4))
    choices = sequel_choices(state)
    state.selected_sequel_choice = min(state.selected_sequel_choice, len(choices) - 1)
    visible = height - 8
    start = list_start(state.selected_sequel_choice, len(choices), visible)
    for row, choice in enumerate(choices[start : start + visible], 3):
        index = start + row - 3
        selected = index == state.selected_sequel_choice
        if choice is None:
            text = "ORIGINAL GAME  Create a new genre/theme concept and generated title"
        else:
            label = game_title(choice, 34)
            text = f"SEQUEL         {label:<34} {choice.genre[:13]:<13} rating {rating_text(choice):>3} | hype {choice.hype:.0f} | {choice.monthly_players:,} monthly players | {update_status(choice)}"
        add_text(panel, row, 2, f"{'> ' if selected else '  '}{text}", width - 4, curses.color_pair(3) | curses.A_BOLD if selected else 0)
    tracked = len(state.studio.catalog)
    missing = max(0, state.studio.released_games - tracked)
    if missing:
        add_text(panel, height - 3, 2, f"{missing} older release(s) lack recoverable title data and cannot be selected as sequels.", width - 4, curses.color_pair(5))
    add_text(panel, height - 2, 2, "Enter or double-click to continue. Mouse wheel scrolls the release list.", width - 4, curses.color_pair(4))


def new_game_panel_geometry(width: int, height: int) -> tuple[int, int, int, int, int]:
    storefront_height = 11
    top_height = max(9, height - 4 - storefront_height)
    genre_width = max(16, min(28, width // 6))
    theme_width = max(18, min(32, width // 5))
    plan_width = width - genre_width - theme_width - 2
    return top_height, genre_width, theme_width, plan_width, storefront_height


def draw_new_game(screen: curses.window, state: GameState, width: int, height: int) -> None:
    if state.new_game_step == -1:
        draw_project_type(screen, state, width, height)
        return
    top_height, genre_width, theme_width, plan_width, storefront_height = new_game_panel_geometry(width, height)
    genre = screen.derwin(top_height, genre_width, 2, 0)
    topic = screen.derwin(top_height, theme_width, 2, genre_width + 1)
    plan = screen.derwin(top_height + storefront_height, plan_width, 2, genre_width + theme_width + 2)
    draw_box(genre, "1 Genre Mix")
    draw_box(topic, "2 Theme Mix")
    draw_box(plan, "3 Creative Brief & Market")
    add_text(genre, 1, 2, "PRIMARY", genre_width - 4, curses.A_BOLD)
    genre_visible = max(1, top_height - 5)
    genre_start = list_start(state.selected_genre, len(GENRES), genre_visible)
    for row, name in enumerate(GENRES[genre_start : genre_start + genre_visible], 2):
        index = genre_start + row - 2
        selected = index == state.selected_genre
        add_text(genre, row, 2, f"{'> ' if selected else '  '}{name}", genre_width - 4, curses.color_pair(3) | curses.A_BOLD if selected and state.new_game_step == 0 else 0)
    genre_blend = GENRES[state.selected_secondary_genre]
    add_text(genre, top_height - 2, 2, f"Blend < {genre_blend} >", genre_width - 4, curses.color_pair(4) if state.new_game_step == 0 else 0)

    add_text(topic, 1, 2, "PRIMARY", theme_width - 4, curses.A_BOLD)
    topic_visible = max(1, top_height - 5)
    topic_start = list_start(state.selected_topic, len(TOPICS), topic_visible)
    for row, name in enumerate(TOPICS[topic_start : topic_start + topic_visible], 2):
        index = topic_start + row - 2
        selected = index == state.selected_topic
        add_text(topic, row, 2, f"{'> ' if selected else '  '}{name}", theme_width - 4, curses.color_pair(3) | curses.A_BOLD if selected and state.new_game_step == 1 else 0)
    theme_blend = TOPICS[state.selected_secondary_topic]
    add_text(topic, top_height - 2, 2, f"Blend < {theme_blend} >", theme_width - 4, curses.color_pair(4) if state.new_game_step == 1 else 0)

    scope = SCOPES[state.selected_scope]
    marketing = MARKETING[state.selected_marketing]
    channel_data = CHANNELS[state.selected_channel]
    audience = AUDIENCES[state.selected_audience]
    game_format = GAME_FORMATS[state.selected_format]
    primary_direction = CREATIVE_DIRECTIONS[state.selected_creative_primary]
    secondary_direction = CREATIVE_DIRECTIONS[state.selected_creative_secondary]
    release_strategy = RELEASE_STRATEGIES[state.selected_release_strategy]
    report = market_report(state)
    title_mode = "TYPE NAME, ENTER TO ACCEPT" if state.naming_game else "E edit / R randomize"
    add_text(plan, 1, 2, f"Title      {state.draft_title}_  [{title_mode}]" if state.naming_game else f"Title      {state.draft_title}  [{title_mode}]", plan_width - 4, curses.color_pair(3) | curses.A_BOLD)
    fields = [
        f"Scope       {scope['name']} | base {scope['work']:,} work | {money(scope['setup'])}",
        f"Game format {game_format['name']} | +{game_format['work'] - 1:.0%} work | {money(game_format['setup'])} tech",
        f"Audience    {audience['name']}",
        f"Lead bet    {primary_direction['name']}",
        f"Support bet {secondary_direction['name']}",
        f"Launch life {release_strategy['name']} | {release_strategy['tradeoff']}",
        f"Marketing   {marketing['name']} | {money(marketing['cost'])} | hype {5 + marketing['boost'] / 25:.0f}",
    ]
    for row, text in enumerate(fields, 2):
        selected = state.new_game_step == 2 and state.selected_focus == row - 2
        add_text(plan, row, 2, ("> " if selected else "  ") + text, plan_width - 4, curses.color_pair(3) | curses.A_BOLD if selected else 0)
    cost = scope["setup"] + game_format["setup"] + release_strategy["setup"] + marketing["cost"] + channel_data["fee"]
    output = projected_weekly_output(state.studio, concept_focus(state))
    week_low = max(4, round(report["work_low"] / output))
    week_high = max(week_low, round(report["work_high"] / output))
    add_text(plan, 10, 2, "MARKET INTELLIGENCE", plan_width - 4, curses.A_BOLD)
    add_text(plan, 11, 2, f"{report['outlook']} | Research confidence {report['confidence']}% (team Research {report['research']})", plan_width - 4, curses.color_pair(4) if report["score_low"] >= 52 else curses.color_pair(5) if report["score_high"] < 38 else 0)
    add_text(plan, 12, 2, f"Fit likely {report['score_low']}-{report['score_high']}/100 | Interested players {report['audience_low']:,}-{report['audience_high']:,}", plan_width - 4)
    add_text(plan, 13, 2, f"Competing releases {report['competitors_low']}-{report['competitors_high']} | Risk exposure {report['risk']} | rivals share audience overlap", plan_width - 4)
    add_text(plan, 14, 2, f"Workload forecast {report['work_low']:,}-{report['work_high']:,} work | roughly {week_low}-{week_high} weeks", plan_width - 4)
    add_text(plan, 15, 2, f"TRADE-OFF  {primary_direction['tradeoff']} + {secondary_direction['tradeoff']}", plan_width - 4)
    requirements = plan_requirements(state)
    runway_weeks = max(0, state.studio.cash - cost) / max(1, monthly_fixed_cost(state.studio)) * 4.33
    runway_danger = runway_weeks < week_high
    if requirements:
        readiness = f"LOCKED: needs {', '.join(requirements)}"
    elif runway_danger:
        readiness = f"HIGH FAILURE RISK: {runway_weeks:.0f}w runway vs forecast up to {week_high}w"
    else:
        readiness = "PRODUCTION READY - forecast still carries uncertainty"
    add_text(plan, 17, 2, readiness, plan_width - 4, curses.color_pair(5) if requirements or runway_danger else curses.color_pair(4) | curses.A_BOLD)
    summary = f"Cash due {money(cost)} | runway after setup {(state.studio.cash - cost) / max(1, monthly_fixed_cost(state.studio)):.1f} months | estimates can be wrong"
    sequel = next((game for game in state.studio.catalog if game.game_id == state.sequel_game_id), None)
    if sequel:
        score = "score n/a" if sequel.release_date == "Historical" else f"{sequel.score}/100"
        summary += f" | sequel to {sequel.title} ({score})"
    add_text(plan, 18, 2, summary, plan_width - 4, curses.color_pair(4) if not requirements and not runway_danger else curses.color_pair(5))

    storefront_width = genre_width + theme_width + 1
    storefront = screen.derwin(storefront_height, storefront_width, 2 + top_height, 0)
    draw_box(storefront, "4 Market & Store")
    store_width = max(8, storefront_width - 24)
    add_text(storefront, 1, 2, f"  {'STORE':<{store_width}} | {'CUT':>4} | {'COST':>8}", storefront_width - 4, curses.A_BOLD)
    visible = storefront_height - 3
    start = list_start(state.selected_channel, len(CHANNELS), visible)
    for row, channel in enumerate(CHANNELS[start : start + visible], 2):
        index = start + row - 2
        marker = ">" if index == state.selected_channel else " "
        text = f"{marker} {channel['name']:<{store_width}} | {channel['cut']:>4.0%} | {money(channel['fee']):>8}"
        selected = state.new_game_step == 3 and index == state.selected_channel
        add_text(storefront, row, 2, text, storefront_width - 4, curses.color_pair(3) | curses.A_BOLD if selected else 0)


def team_panel_widths(state: GameState, width: int) -> tuple[int, int]:
    if width < 120:
        roster_width = width // 2
    elif state.team_tab == 1:
        roster_width = round(width * 0.64)
    else:
        roster_width = round(width * 0.36)
    roster_width = max(35, min(width - 36, roster_width))
    return roster_width, width - roster_width - 1


def draw_team_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel_height = height - 4
    roster_width, applicant_width = team_panel_widths(state, width)
    roster = screen.derwin(panel_height, roster_width, 2, 0)
    applicants = screen.derwin(panel_height, applicant_width, 2, roster_width + 1)
    target = recommended_team_size(state.studio)
    draw_box(roster, f"Team | {len(state.studio.team)}/{target} suggested")
    next_pool = applicant_pool_size(state.studio)
    draw_box(applicants, f"Applicants | {len(state.studio.applicants)} available | Next pool {next_pool}")

    roster_expanded = roster_width >= 112
    applicant_expanded = applicant_width >= 100
    if roster_expanded:
        roster_inner = roster_width - 4
        flexible_width = roster_inner - 62
        name_width = min(20, max(16, flexible_width // 3))
        trait_width = min(18, max(14, flexible_width - name_width - 20))
        role_width = flexible_width - name_width - trait_width
        roster_header = f"  {'NAME':<{name_width}} {'ROLE':<{role_width}} {'DES':>3} {'ART':>3} {'AUD':>3} {'CODE':>4} {'RES':>3} {'MORALE':>6} {'FATIGUE':>7} {'SALARY/YR':>11} {'COST/MO':>9} {'STYLE / QUIRK':<{trait_width}}"
    else:
        roster_header = f"  {'NAME':<14} {'DES':>3} {'ART':>3} {'AUD':>3} {'CODE':>4} {'MOR':>3} {'FAT':>3} {'PERSONALITY':<12}"
    add_text(roster, 1, 2, roster_header, roster_width - 4, curses.A_BOLD)

    removable_index = 0
    for row, employee in enumerate(state.studio.team[: panel_height - 3], 2):
        is_selected = state.team_tab == 1 and (
            (employee.founder and (state.selected_roster < 0 or len(state.studio.team) == 1))
            or (not employee.founder and removable_index == state.selected_roster)
        )
        if not employee.founder:
            removable_index += 1
        marker = ">" if is_selected else " "
        salary = "owner draw" if employee.founder else f"${employee.annual_salary:,}"
        personality = f"{employee.trait} / {employee.quirk}"
        display_name = f"{employee.name} [TRAIN {employee.training_weeks_left}w]" if employee.training_weeks_left else employee.name
        if roster_expanded:
            line = f"{marker} {display_name[:name_width]:<{name_width}} {employee.role[:role_width]:<{role_width}} {employee.design:>3} {employee.art:>3} {employee.audio:>3} {employee.code:>4} {employee.research:>3} {employee.morale:>6.0f} {employee.fatigue:>7.0f} {salary:>11} {money(employee.monthly_salary):>9} {personality[:trait_width]:<{trait_width}}"
        else:
            line = f"{marker} {display_name[:14]:<14} {employee.design:>3} {employee.art:>3} {employee.audio:>3} {employee.code:>4} {employee.morale:>3.0f} {employee.fatigue:>3.0f} {personality[:12]:<12}"
        add_text(roster, row, 2, line, roster_width - 4, curses.color_pair(3) | curses.A_BOLD if is_selected else 0)

    summary_row = len(state.studio.team[: panel_height - 3]) + 3
    if roster_expanded and summary_row + 5 < panel_height:
        team = state.studio.team
        payroll = sum(employee.monthly_salary for employee in team)
        average_morale = sum(employee.morale for employee in team) / len(team)
        average_fatigue = sum(employee.fatigue for employee in team) / len(team)
        average_tenure = sum(employee.weeks_employed for employee in team) / len(team)
        overview = [
            ("TEAM OVERVIEW", curses.A_BOLD),
            (f"Headcount {len(team)}/{target} suggested | Payroll {money(payroll)}/month | {money(payroll * 12)}/year", 0),
            (f"Average morale {average_morale:.0f}/100 | Fatigue {average_fatigue:.0f}/100 | Tenure {average_tenure:.1f} weeks", 0),
            ("TEAM CAPABILITY", curses.A_BOLD),
        ]
        for skill_index, skill_name in enumerate(EMPLOYEE_SKILLS):
            average_skill = sum(employee.all_skills[skill_index] for employee in team) / len(team)
            lead = max(team, key=lambda employee: employee.all_skills[skill_index])
            overview.append((f"{skill_name:<8} [{meter(average_skill, 100, 18)}] avg {average_skill:>4.0f} | Lead {lead.name} {lead.all_skills[skill_index]}", 0))

        selected_member = selected_roster_employee(state) or team[0]
        overview.extend(
            [
                ("SELECTED TEAM MEMBER", curses.A_BOLD),
                (f"{selected_member.name} | {selected_member.role} | {selected_member.trait} / {selected_member.quirk}", 0),
                (f"Skills  Design {selected_member.design} | Art {selected_member.art} | Audio {selected_member.audio} | Code {selected_member.code} | Research {selected_member.research}", 0),
                (f"Wellbeing  Morale {selected_member.morale:.0f}/100 | Fatigue {selected_member.fatigue:.0f}/100 | Employed {selected_member.weeks_employed}w", 0),
                (f"Compensation  {money(selected_member.annual_salary)}/year | {money(selected_member.monthly_salary)}/month", 0),
                (f"Development  XP {selected_member.experience}/100 | {'TRAINING ' + selected_member.training_skill + ' ' + str(selected_member.training_weeks_left) + 'w' if selected_member.training_weeks_left else 'Available for training'}", 0),
                (f"Style: {TRAITS.get(selected_member.trait, 'unclassified')} | Quirk: {QUIRKS.get(selected_member.quirk, 'unclassified')}", 0),
            ]
        )
        for row, (text, attr) in enumerate(overview[: panel_height - summary_row - 1], summary_row):
            add_text(roster, row, 2, text, roster_width - 4, attr)

    if applicant_expanded:
        applicant_header = f"  {'NAME':<16} {'ROLE':<22} {'DES':>3} {'ART':>3} {'AUD':>3} {'CODE':>4} {'RES':>3} {'SALARY/YR':>11} {'STYLE / QUIRK':<14}"
    else:
        applicant_header = f"  {'NAME':<14} {'ROLE':<17} {'DES':>3} {'ART':>3} {'AUD':>3} {'CODE':>4} {'SALARY':>9} {'TRAIT':<10}"
    add_text(applicants, 1, 2, applicant_header, applicant_width - 4, curses.A_BOLD)
    for row, employee in enumerate(state.studio.applicants[: panel_height - 3], 2):
        selected = state.team_tab == 0 and row - 2 == state.selected_employee
        marker = ">" if selected else " "
        personality = f"{employee.trait}/{employee.quirk}"
        if applicant_expanded:
            text = f"{marker} {employee.name[:16]:<16} {employee.role[:22]:<22} {employee.design:>3} {employee.art:>3} {employee.audio:>3} {employee.code:>4} {employee.research:>3} {money(employee.annual_salary):>11} {personality[:14]:<14}"
        else:
            text = f"{marker} {employee.name[:14]:<14} {employee.role[:17]:<17} {employee.design:>3} {employee.art:>3} {employee.audio:>3} {employee.code:>4} {money(employee.annual_salary):>9} {personality[:10]:<10}"
        add_text(applicants, row, 2, text, applicant_width - 4, curses.color_pair(3) | curses.A_BOLD if selected else 0)


def draw_contract_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel_height = height - 4
    board_width = max(46, width * 2 // 3)
    detail_width = width - board_width - 1
    board = screen.derwin(panel_height, board_width, 2, 0)
    detail = screen.derwin(panel_height, detail_width, 2, board_width + 1)
    studio = state.studio
    auto = "ON" if studio.auto_contracts else "OFF"
    draw_box(board, f"Contract Board | {len(studio.contract_offers)} offers | Auto {auto}")
    draw_box(detail, "Contract Queue & Profile")
    if not studio.contract_offers:
        add_text(board, 1, 2, "No contract offers. The board refreshes monthly.", board_width - 4)
    state.selected_contract = min(state.selected_contract, max(0, len(studio.contract_offers) - 1))
    board_inner = board_width - 4
    board_expanded = board_inner >= 85
    client_width = 18 if board_expanded else 10
    focus_width = 10 if board_expanded else 5
    job_width = max(8, board_inner - (69 if board_expanded else 32))
    if board_expanded:
        board_header = f"  {'CLIENT':<{client_width}} {'CONTRACT':<{job_width}} {'FOCUS':<{focus_width}} {'LEVEL':>5} {'PAYOUT':>10} {'ETA':>5} {'DUE':>5} {'REQ REP':>7}"
    else:
        board_header = f"  {'CLIENT':<{client_width}} {'CONTRACT':<{job_width}} {'FOCUS':<{focus_width}} {'PAY':>8} {'DUE':>4}"
    add_text(board, 1, 2, board_header, board_inner, curses.A_BOLD)
    for row, contract in enumerate(studio.contract_offers[: panel_height - 3], 2):
        selected = row - 2 == state.selected_contract
        estimate = estimated_contract_weeks(studio, contract)
        locked = studio.contractor_reputation < contract.reputation_required
        if board_expanded:
            text = f"{'> ' if selected else '  '}{contract.client[:client_width]:<{client_width}} {contract.title[:job_width]:<{job_width}} {contract.focus[:focus_width]:<{focus_width}} {contract.difficulty:>5} {money(contract.payout):>10} {estimate:>4}w {contract.weeks_left:>4}w {contract.reputation_required:>7}"
        else:
            text = f"{'> ' if selected else '  '}{contract.client[:client_width]:<{client_width}} {contract.title[:job_width]:<{job_width}} {contract.focus[:focus_width]:<{focus_width}} {money(contract.payout):>8} {contract.weeks_left:>3}w"
        attr = curses.color_pair(5) if locked else curses.color_pair(3) | curses.A_BOLD if selected else 0
        add_text(board, row, 2, text, board_width - 4, attr)

    add_text(detail, 1, 2, f"Contractor reputation  {studio.contractor_reputation:.1f}/100", detail_width - 4, curses.A_BOLD)
    add_text(detail, 2, 2, f"Completed {studio.contracts_completed} | Failed {studio.contracts_failed}", detail_width - 4)
    add_text(detail, 3, 2, f"Auto accept: {auto}", detail_width - 4, curses.color_pair(4) if studio.auto_contracts else curses.color_pair(5))
    active = studio.contract
    if active:
        progress = 0 if active.required_work <= 0 else active.work_done / active.required_work
        estimate = estimated_contract_weeks(studio, active)
        source = "AUTO" if active.auto_accepted else "MANUAL"
        add_text(detail, 5, 2, f"ACTIVE {source} CONTRACT", detail_width - 4, curses.color_pair(3) | curses.A_BOLD)
        add_text(detail, 6, 2, f"{active.client}", detail_width - 4)
        add_text(detail, 7, 2, active.title, detail_width - 4)
        add_text(detail, 8, 2, f"Focus {active.focus} | D{active.difficulty}", detail_width - 4)
        add_text(detail, 9, 2, f"Progress {progress:.0%} | est {estimate}w", detail_width - 4)
        add_text(detail, 10, 2, f"Deadline {active.weeks_left}w | {money(active.payout)}", detail_width - 4)
    else:
        add_text(detail, 5, 2, "No active contract", detail_width - 4)
    queue_row = 12
    if queue_row < panel_height - 1:
        add_text(detail, queue_row, 2, f"QUEUE ({len(studio.contract_queue)})", detail_width - 4, curses.A_BOLD)
        for row, contract in enumerate(studio.contract_queue[: panel_height - queue_row - 2], queue_row + 1):
            source = "A" if contract.auto_accepted else "M"
            add_text(detail, row, 2, f"{row - queue_row}. [{source}] {contract.focus}: {contract.title} ({money(contract.payout)})", detail_width - 4)


def live_games(state: GameState) -> list:
    return list(reversed(state.studio.catalog))


def update_jobs_for_game(state: GameState, game_id: int) -> list:
    studio = state.studio
    jobs = ([studio.active_update] if studio.active_update else []) + studio.update_queue
    return [job for job in jobs if job.game_id == game_id]


def draw_update_planner(panel: curses.window, state: GameState, game, panel_width: int, panel_height: int) -> None:
    studio = state.studio
    size = next((item for item in UPDATE_SIZES if item["name"] == game.update_size), UPDATE_SIZES[1])
    target_version = planned_update_version(studio, game, game.update_size)
    active = studio.active_update
    compact = panel_width < 70 or panel_height < 20
    split = panel_width // 2 if not compact else 2
    plan_width = split - 4 if not compact else panel_width - 4

    add_text(panel, 1, 2, f"PLAN FOR  {game_title(game)}", panel_width - 4, curses.A_BOLD)
    dlc_price = f" | {money(size['price'])} retail" if "price" in size else ""
    add_text(panel, 2, 2, f"Target v{target_version} | {game.update_size} | {money(size['cost'])}{dlc_price} | delivery ETA {estimated_update_delivery_weeks(studio, game)}w", panel_width - 4, curses.color_pair(4))
    add_text(panel, 4, 2, "SCOPE / VERSION STEP", plan_width, curses.A_BOLD)
    if compact:
        step = size["version"]
        add_text(panel, 5, 2, f"[{game.update_size}] +{step[0]}.{step[1]:02d}.{step[2]:02d}", plan_width, curses.color_pair(3) | curses.A_BOLD if state.games_tab == 1 else 0)
        add_text(panel, 7, 2, "UPDATE AREA", plan_width, curses.A_BOLD)
        add_text(panel, 8, 2, f"[{game.update_focus}]", plan_width, curses.color_pair(3) | curses.A_BOLD if state.games_tab == 2 else 0)
        add_text(panel, 9, 2, f"{size['work']} work -> mandatory QA: fix {size['bugs']} bugs -> v{target_version}", plan_width)
    else:
        for row, item in enumerate(UPDATE_SIZES, 5):
            step = item["version"]
            selected = item["name"] == game.update_size
            scope_active = selected and state.games_tab == 1
            price = f" | {money(item['price'])}" if "price" in item else ""
            add_text(panel, row, 2, f"{'> ' if selected else '  '}{item['name']:<10} +{step[0]}.{step[1]:02d}.{step[2]:02d} | {item['work']:>3} work | {item['bugs']:>2} QA bugs{price}", plan_width, curses.color_pair(3) | curses.A_BOLD if scope_active else 0)
        add_text(panel, 10, 2, "UPDATE AREA", plan_width, curses.A_BOLD)
        for row, item in enumerate(UPDATE_FOCUSES, 11):
            selected = item["name"] == game.update_focus
            area_active = selected and state.games_tab == 2
            add_text(panel, row, 2, f"{'> ' if selected else '  '}{item['name']:<16} | {item['skill']} team", plan_width, curses.color_pair(3) | curses.A_BOLD if area_active else 0)
        add_text(panel, 17, 2, f"Pipeline: {size['work']} work -> mandatory QA: fix {size['bugs']} bugs -> v{target_version}", plan_width)

    if compact and panel_height < 20:
        return
    status_row = 11 if compact else 4
    status_x = 2 if compact else split
    status_width = panel_width - status_x - 2
    if not compact:
        add_text(panel, 3, split - 2, "|", 1, curses.color_pair(2))
    add_text(panel, status_row, status_x, "ACTIVE UPDATE", status_width, curses.A_BOLD)
    if active:
        bugs_left = max(0, active.bugs_found - active.bugs_fixed)
        add_text(panel, status_row + 1, status_x, f"{active.game_title} -> v{active.target_version}", status_width, curses.A_BOLD)
        add_text(panel, status_row + 2, status_x, f"{active.size} / {active.focus} | {active.phase}", status_width)
        add_text(panel, status_row + 3, status_x, f"[{meter(active.progress, 1, min(24, max(8, status_width - 9)))}] {active.progress:.0%}", status_width, curses.color_pair(4))
        add_text(panel, status_row + 4, status_x, f"Build {active.work_done:.0f}/{active.required_work:.0f} | Bugs left {bugs_left:.0f}/{active.bugs_found:.0f}", status_width)
    else:
        add_text(panel, status_row + 1, status_x, "No active update. Queue a plan to start work.", status_width)

    queue_row = status_row + (5 if compact else 6)
    if queue_row < panel_height - 1:
        queue = ([active] if active else []) + studio.update_queue
        active_count = 1 if active else 0
        cancellation = state.queue_cancellation == "update"
        heading = "CANCEL QUEUED UPDATE" if cancellation else "UPDATE QUEUE"
        add_text(panel, queue_row, status_x, f"{heading} ({len(queue)}) | {active_count} active | {len(studio.update_queue)} waiting", status_width, (curses.color_pair(5) if cancellation else 0) | curses.A_BOLD)
        for row, job in enumerate(queue[: max(0, panel_height - queue_row - 2)], queue_row + 1):
            status = "ACTIVE" if active and job is active else "WAITING"
            waiting_index = row - queue_row - 1 - active_count
            selected = cancellation and status == "WAITING" and waiting_index == state.selected_queue_cancellation
            marker = ">" if selected else str(row - queue_row)
            attr = curses.color_pair(5) | curses.A_BOLD if selected else curses.color_pair(4) if status == "ACTIVE" else 0
            add_text(panel, row, status_x, f"{marker}. {status:<7} {job.game_title} -> v{job.target_version} | {job.size} {job.focus}", status_width, attr)


def draw_game_catalogue_table(
    panel: curses.window,
    state: GameState,
    panel_width: int,
    panel_height: int,
    selected_index: int,
    active: bool,
    include_project: bool = False,
    title: str | None = None,
) -> None:
    entries = ([(0, state.studio.current_project)] if include_project and state.studio.current_project else []) + [
        (game.game_id, game) for game in live_games(state)
    ]
    draw_box(panel, title or f"Game Catalogue | {len(entries)} {'game' if len(entries) == 1 else 'games'}")
    if not entries:
        add_text(panel, 1, 2, "No released games yet.", panel_width - 4)
        return

    inner_width = panel_width - 4
    if panel_width >= 120:
        genre_width = 28 if panel_width >= 170 else 12
        title_width = max(17, min(50, inner_width - genre_width - 87))
        header = f"  {'TITLE':<{title_width}} {'GENRE':<{genre_width}} {'RATING':>6} {'HYPE':>6} {'BUGS':>6} {'SALES/W':>9} {'UNITS':>10} {'MONTHLY PLAYERS':>15} {'NET REVENUE':>12} {'PROFIT':>12}"
    else:
        title_width = 12
        genre_width = 8
        header = f"  {'TITLE':<12} {'GENRE':<8} {'RATE':>4} {'HYPE':>4} {'BUGS':>4} {'SALES':>5} {'UNITS':>5} {'MONTH':>5} {'REV':>6} {'PROFIT':>6}"
    add_text(panel, 1, 2, header, inner_width, curses.A_BOLD)

    visible = panel_height - 3
    start = list_start(selected_index, len(entries), visible)
    for row, (game_id, entry) in enumerate(entries[start : start + visible], 2):
        index = start + row - 2
        selected = index == selected_index
        if game_id == 0:
            game_title_text = entry.title
            genre = GENRES[state.selected_genre]
            rating = "dev"
            hype = entry.hype
            bugs = int(entry.known_defects)
            weekly = monthly = units = 0
            revenue, profit = "$0", "n/a"
        else:
            sale = sale_for_game(state.studio, game_id)
            game_title_text = game_title(entry)
            genre = entry.genre
            rating = rating_text(entry)
            hype = entry.hype
            bugs = entry.known_bug_count
            weekly = sale.weekly_units if sale else 0
            monthly = entry.monthly_players
            units = entry.units_sold
            revenue = money(entry.net_revenue)
            profit = money(game_profit(entry)) if entry.cost_history_complete else "n/a"
        if panel_width >= 120:
            text = f"{'> ' if selected else '  '}{game_title_text[:title_width]:<{title_width}} {genre[:genre_width]:<{genre_width}} {rating:>6} {hype:>6.0f} {bugs:>6} {weekly:>9,} {units:>10,} {monthly:>15,} {revenue:>12} {profit:>12}"
        else:
            text = f"{'> ' if selected else '  '}{game_title_text[:12]:<12} {genre[:8]:<8} {rating:>4} {hype:>4.0f} {bugs:>4} {weekly:>5,} {units:>5,} {monthly:>5,} {revenue:>6} {profit:>6}"
        add_text(panel, row, 2, text, inner_width, curses.color_pair(3) | curses.A_BOLD if selected and active else 0)


def draw_update_planner_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    draw_games_screen(screen, state, width, height)


def production_review_geometry(width: int, height: int) -> tuple[int, int, int, int]:
    popup_width = min(100, max(66, width - 12))
    popup_height = 20
    return popup_height, popup_width, max(2, (height - popup_height) // 2), max(1, (width - popup_width) // 2)


def draw_production_review(screen: curses.window, state: GameState, width: int, height: int) -> None:
    project = state.studio.current_project
    if project is None or project.pending_decision is None:
        return
    decision = PRODUCTION_DECISIONS[project.pending_decision]
    popup_height, popup_width, popup_y, popup_x = production_review_geometry(width, height)
    panel = screen.derwin(popup_height, popup_width, popup_y, popup_x)
    panel.erase()
    draw_box(panel, f"Production Event | {decision['title']}")
    genre_mix = project.genre if project.secondary_genre == project.genre else f"{project.genre} / {project.secondary_genre}"
    add_text(panel, 1, 3, project.title, popup_width - 6, curses.A_BOLD)
    add_text(panel, 2, 3, f"{genre_mix} | {project.target_audience} | {project.game_format}", popup_width - 6)
    add_text(panel, 3, 3, f"Progress {project.progress:.0%} | week {project.weeks}/{project.planned_weeks} forecast | known bugs {int(project.known_defects)}", popup_width - 6)
    add_text(panel, 5, 3, decision["question"], popup_width - 6, curses.color_pair(5) | curses.A_BOLD)
    for index, option in enumerate(decision["options"]):
        selected = index == state.selected_project_decision
        row = 8 + index * 4
        add_text(panel, row, 5, f"{'> ' if selected else '  '}{option['name']}", popup_width - 10, curses.color_pair(3) | curses.A_BOLD if selected else 0)
        add_text(panel, row + 1, 9, option["effect"], popup_width - 14, curses.color_pair(4) if selected else 0)
    if project.decisions_made:
        add_text(panel, 16, 3, f"Earlier: {project.decisions_made[-1]}", popup_width - 6)
    add_text(panel, popup_height - 2, 3, "Up/Down chooses. Enter commits. Other controls are locked.", popup_width - 6, curses.color_pair(4))


def draw_games_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel_height = height - 4
    games = live_games(state)
    planner_open = state.modal == "update_planner"
    game_count = f"{len(games)} {'game' if len(games) == 1 else 'games'}"
    if width < 120:
        list_width = max(28, width // 3) if planner_open else max(48, width * 2 // 3)
        detail_width = width - list_width - 1
        games_panel = screen.derwin(panel_height, list_width, 2, 0)
        detail = screen.derwin(panel_height, detail_width, 2, list_width + 1)
        development = f" | IN DEV {state.studio.current_project.title}" if state.studio.current_project else ""
        draw_box(games_panel, f"Game Catalogue | {game_count}{development}")
        draw_box(detail, "Update Planner" if planner_open else "Commercial Performance")
        if not games:
            project = state.studio.current_project
            add_text(games_panel, 1, 2, "No released games yet.", list_width - 4, curses.A_BOLD)
            if project:
                add_text(games_panel, 2, 2, f"In production: {project.title}", list_width - 4, curses.A_BOLD)
                add_text(games_panel, 3, 2, f"{project.phase} | {project.progress:.0%} complete", list_width - 4, curses.color_pair(4))
                add_text(detail, 1, 2, project.title, detail_width - 4, curses.A_BOLD)
                genre_mix = project.genre if project.secondary_genre == project.genre else f"{project.genre} / {project.secondary_genre}"
                add_text(detail, 2, 2, genre_mix, detail_width - 4)
                add_text(detail, 3, 2, f"{project.target_audience} | {project.game_format}", detail_width - 4)
                add_text(detail, 4, 2, f"Forecast {project.forecast_score_low}-{project.forecast_score_high}/100 | confidence {project.forecast_confidence}%", detail_width - 4)
                add_text(detail, 6, 2, f"Production {project.progress:.0%} | Known bugs {int(project.known_defects)}", detail_width - 4)
                add_text(detail, 8, 2, "P opens Promotion Planning", detail_width - 4, curses.color_pair(4))
            else:
                add_text(detail, 1, 2, "BUILD A MARKET POSITION", detail_width - 4, curses.A_BOLD)
                add_text(detail, 3, 2, "Mix modern genres and themes.", detail_width - 4)
                add_text(detail, 4, 2, "Choose an audience and creative bets.", detail_width - 4)
                add_text(detail, 5, 2, "Test demand, rivals, risk, and runway.", detail_width - 4)
                add_text(detail, 7, 2, "Press N to open the concept room.", detail_width - 4, curses.color_pair(4))
            return
        state.selected_game = min(state.selected_game, len(games) - 1)
        visible = panel_height - 2
        start = list_start(state.selected_game, len(games), visible)
        for row, game in enumerate(games[start : start + visible], 1):
            sale = sale_for_game(state.studio, game.game_id)
            selected = start + row - 1 == state.selected_game
            title = game_title(game)
            if planner_open:
                text = f"{'> ' if selected else '  '}{title}"
            else:
                title = game_title(game, 20)
                text = f"{'> ' if selected else '  '}{title:<20} R{rating_text(game):>3} {(sale.weekly_units if sale else 0):>5,}/w {game.monthly_players:>6,} monthly"
            active = selected and (not planner_open or state.games_tab == 0)
            add_text(games_panel, row, 2, text, list_width - 4, curses.color_pair(3) | curses.A_BOLD if active else 0)
        game = games[state.selected_game]
        if planner_open:
            draw_update_planner(detail, state, game, detail_width, panel_height)
            return
        sale = sale_for_game(state.studio, game.game_id)
        add_text(detail, 1, 2, game_title(game), detail_width - 4, curses.A_BOLD)
        genre_mix = game.genre if not game.secondary_genre or game.secondary_genre == game.genre else f"{game.genre} / {game.secondary_genre}"
        add_text(detail, 2, 2, genre_mix, detail_width - 4)
        add_text(detail, 3, 2, f"{game.target_audience} | {game.game_format}", detail_width - 4)
        add_text(detail, 4, 2, f"Market fit {game.market_score}/100 | {game.competitors} launch rivals", detail_width - 4)
        add_text(detail, 6, 2, f"Rating {rating_text(game)}/100 | Hype {game.hype:.0f}/200", detail_width - 4)
        add_text(detail, 7, 2, f"Monthly players {game.monthly_players:,} | Sales {(sale.weekly_units if sale else 0):,}/week", detail_width - 4)
        add_text(detail, 8, 2, f"Known bugs {game.known_bug_count} | DLC {game.dlcs_released}", detail_width - 4, curses.color_pair(5) if game.known_bug_count else 0)
        add_text(detail, 10, 2, f"{game.update_size} / {game.update_focus} | U opens planner", detail_width - 4)
        return

    catalog_height = panel_height if not games else min(15, max(9, min(len(games) + 4, panel_height // 3 + 2)))
    games_panel = screen.derwin(catalog_height, width, 2, 0)
    if not games:
        draw_box(games_panel, f"Game Catalogue | {game_count}")
        project = state.studio.current_project
        add_text(games_panel, 1, 2, "THE GAME PORTFOLIO", width - 4, curses.A_BOLD)
        if project:
            genre_mix = project.genre if project.secondary_genre == project.genre else f"{project.genre} / {project.secondary_genre}"
            add_text(games_panel, 3, 2, f"IN PRODUCTION  {project.title}", width - 4, curses.color_pair(4) | curses.A_BOLD)
            add_text(games_panel, 4, 2, f"Concept    {genre_mix} | {project.topic} + {project.secondary_topic}", width - 4)
            add_text(games_panel, 5, 2, f"Position   {project.target_audience} | {project.game_format} | {project.release_strategy}", width - 4)
            add_text(games_panel, 6, 2, f"Forecast   fit {project.forecast_score_low}-{project.forecast_score_high}/100 | {project.forecast_audience_low:,}-{project.forecast_audience_high:,} interested | {project.forecast_competitors_low}-{project.forecast_competitors_high} rivals", width - 4)
            add_text(games_panel, 8, 2, f"Production {project.phase} | {project.progress:.0%} | week {project.weeks}/{project.planned_weeks} planned | {int(project.known_defects)} known bugs", width - 4)
            add_text(games_panel, 10, 2, f"Creative bets: {project.creative_primary} + {project.creative_secondary}", width - 4)
            add_text(games_panel, 12, 2, "P opens Promotion Planning. The catalogue unlocks when this project ships.", width - 4, curses.color_pair(4))
        else:
            add_text(games_panel, 3, 2, "Your first release should be a deliberate market position, not a genre/theme dice roll.", width - 4)
            add_text(games_panel, 5, 2, "1  MIX        Combine a primary genre and theme with a second influence.", width - 4)
            add_text(games_panel, 6, 2, "2  POSITION   Pick the people you serve and the way they will play together.", width - 4)
            add_text(games_panel, 7, 2, "3  COMMIT     Make creative bets with visible benefits and production costs.", width - 4)
            add_text(games_panel, 8, 2, "4  VALIDATE   Read demand, competing releases, project risk, runway, and capability gates.", width - 4)
            add_text(games_panel, 10, 2, "Small games teach cheaply. Large and online games multiply both the audience and the failure cost.", width - 4, curses.color_pair(5))
            add_text(games_panel, 12, 2, "Press N to enter the concept room.", width - 4, curses.color_pair(4) | curses.A_BOLD)
        return
    state.selected_game = min(state.selected_game, len(games) - 1)
    development = f" | IN DEVELOPMENT: {state.studio.current_project.title}" if state.studio.current_project else ""
    draw_game_catalogue_table(games_panel, state, width, catalog_height, state.selected_game, not planner_open or state.games_tab == 0, title=f"Game Catalogue | {game_count}{development}")

    game = games[state.selected_game]
    sale = sale_for_game(state.studio, game.game_id)
    bottom_y = 2 + catalog_height
    bottom_height = panel_height - catalog_height
    detail_height = bottom_height if bottom_height < 24 else 20
    summary_height = bottom_height - detail_height
    first_width = width // 3
    second_width = width // 3
    third_width = width - first_width - second_width - 2
    if planner_open:
        summary_width = max(42, width * 36 // 100)
        planner_width = width - summary_width - 1
        summary = screen.derwin(bottom_height, summary_width, bottom_y, 0)
        planner = screen.derwin(bottom_height, planner_width, bottom_y, summary_width + 1)
        draw_box(summary, "Selected Game")
        draw_box(planner, f"Update Planner & Queue | {1 if state.studio.active_update else 0} active | {len(state.studio.update_queue)} waiting")
        add_text(summary, 1, 2, game_title(game), summary_width - 4, curses.A_BOLD)
        add_text(summary, 2, 2, f"{game.genre} / {game.topic} | Rating {rating_text(game)}/100", summary_width - 4)
        add_text(summary, 3, 2, f"Hype {game.hype:.0f} | Monthly players {game.monthly_players:,}", summary_width - 4)
        add_text(summary, 4, 2, f"Sales {(sale.weekly_units if sale else 0):,}/week | Updates shipped {game.updates_released}", summary_width - 4)
        add_text(summary, 5, 2, f"Known bugs {game.known_bug_count} | More may remain undiscovered", summary_width - 4, curses.color_pair(5) if game.known_bug_count else 0)
        add_text(summary, 6, 2, "VERSION HISTORY", summary_width - 4, curses.A_BOLD)
        add_text(summary, 7, 2, f"Current public build  v{game.version}", summary_width - 4, curses.color_pair(4))
        add_text(summary, 8, 2, f"Plans for this game   {len(update_jobs_for_game(state, game.game_id))}", summary_width - 4)
        if bottom_height >= 18:
            add_text(summary, 10, 2, "VERSION RULES", summary_width - 4, curses.A_BOLD)
            for row, item in enumerate(UPDATE_SIZES, 11):
                step = item["version"]
                add_text(summary, row, 2, f"{item['name']:<10} +{step[0]}.{step[1]:02d}.{step[2]:02d}", summary_width - 4)
            add_text(summary, 16, 2, "Every update must clear its bug-fixing phase before release.", summary_width - 4, curses.color_pair(4))
        else:
            add_text(summary, 9, 2, "Mandatory bug fixing before every release.", summary_width - 4, curses.color_pair(4))
        draw_update_planner(planner, state, game, planner_width, bottom_height)
        return
    commercial = screen.derwin(detail_height, first_width, bottom_y, 0)
    live_ops = screen.derwin(detail_height, second_width, bottom_y, first_width + 1)
    strategy = screen.derwin(detail_height, third_width, bottom_y, first_width + second_width + 2)
    draw_box(commercial, "Commercial Performance")
    draw_box(live_ops, "Live Operations")
    draw_box(strategy, "Promotion Planning")

    rating_attr = curses.color_pair(4) if game.score >= 70 else curses.color_pair(5) if game.score < 45 else 0
    size = next((item for item in UPDATE_SIZES if item["name"] == game.update_size), UPDATE_SIZES[1])
    focus = next((item for item in UPDATE_FOCUSES if item["name"] == game.update_focus), UPDATE_FOCUSES[0])
    if detail_height < 20:
        add_text(commercial, 1, 2, f"Rating {rating_text(game)}/100 | Hype {game.hype:.0f} | Bugs {game.known_bug_count}", first_width - 4, rating_attr)
        add_text(commercial, 2, 2, f"Sales {(sale.weekly_units if sale else 0):,}/w | Monthly {game.monthly_players:,}", first_width - 4)
        add_text(commercial, 3, 2, f"Revenue {money(game.net_revenue)} | Profit {money(game_profit(game)) if game.cost_history_complete else 'n/a'}", first_width - 4)
        jobs = update_jobs_for_game(state, game.game_id)
        add_text(live_ops, 1, 2, f"Version v{game.version} | {len(jobs)} active/queued", second_width - 4)
        add_text(live_ops, 2, 2, f"{game.update_size} / {game.update_focus}", second_width - 4)
        add_text(live_ops, 3, 2, f"Next v{planned_update_version(state.studio, game, game.update_size)} | delivery {estimated_update_delivery_weeks(state.studio, game)}w | U planner", second_width - 4)
        recommendation, recommendation_color = game_recommendation(game)
        add_text(strategy, 1, 2, "Recommended", third_width - 4, curses.A_BOLD)
        compact_recommendation_attr = curses.color_pair(recommendation_color) if recommendation_color in (4, 5) else 0
        add_text(strategy, 2, 2, recommendation, third_width - 4, compact_recommendation_attr)
        return
    add_text(commercial, 1, 2, game_title(game), first_width - 4, curses.A_BOLD)
    genre_mix = game.genre if not game.secondary_genre or game.secondary_genre == game.genre else f"{game.genre} / {game.secondary_genre}"
    add_text(commercial, 2, 2, f"{genre_mix} | {game.game_format} | {game.channel}", first_width - 4)
    add_text(commercial, 3, 2, "MARKET SIGNALS", first_width - 4, curses.A_BOLD)
    add_text(commercial, 4, 2, f"Rating [{meter(game.score, 100, 18)}] {rating_text(game)}/100", first_width - 4, rating_attr)
    add_text(commercial, 5, 2, f"Hype   [{meter(game.hype, 200, 18)}] {game.hype:.0f}/200 | Known bugs {game.known_bug_count}", first_width - 4)
    add_text(commercial, 6, 2, f"AUDIENCE & SALES | market {game.market_score}/100 | {game.competitors} rivals", first_width - 4, curses.A_BOLD)
    add_text(commercial, 7, 2, f"Weekly sales             {(sale.weekly_units if sale else 0):,}", first_width - 4)
    add_text(commercial, 8, 2, f"Monthly active players   {game.monthly_players:,}", first_width - 4, curses.color_pair(5) if not game.monthly_players else 0)
    add_text(commercial, 9, 2, f"Peak monthly players     {game.peak_monthly_players:,}", first_width - 4)
    add_text(commercial, 10, 2, f"Lifetime units           {game.units_sold:,}", first_width - 4)
    add_text(commercial, 11, 2, f"Net revenue              {money(game.net_revenue)}", first_width - 4)
    add_text(commercial, 12, 2, "UNIT ECONOMICS", first_width - 4, curses.A_BOLD)
    if game.cost_history_complete:
        add_text(commercial, 13, 2, f"Total cost               {money(game_total_cost(game))}", first_width - 4)
        profit = game_profit(game)
        margin = profit / game.net_revenue * 100 if game.net_revenue else 0
        add_text(commercial, 14, 2, f"Profit                   {money(profit)} ({margin:+.1f}%)", first_width - 4, (curses.color_pair(4) if profit >= 0 else curses.color_pair(5)) | curses.A_BOLD)
        add_text(commercial, 16, 2, f"Setup/store {money(game.production_cost)} | Staff {money(game.labor_cost)}", first_width - 4)
        add_text(commercial, 17, 2, f"Marketing {money(game.marketing_cost)} | Live ops {money(game.post_launch_cost)}", first_width - 4)
    else:
        add_text(commercial, 13, 2, "Cost history unavailable", first_width - 4, curses.color_pair(5))
        add_text(commercial, 14, 2, "This historical release predates cost tracking.", first_width - 4)
        add_text(commercial, 16, 2, f"Release record  {game.release_date}", first_width - 4)
        add_text(commercial, 17, 2, f"Franchise generation {game.generation}", first_width - 4)

    rating_factor = max(0.10, (game.score / 100) ** 2)
    expected_hype = size["hype"] * focus["hype"] * rating_factor
    expected_players = round(
        (game.monthly_players * 0.20 + game.units_sold * 0.012)
        * size["sales"]
        * focus["players"]
        * rating_factor
    )
    jobs = update_jobs_for_game(state, game.game_id)
    active_job = state.studio.active_update if state.studio.active_update and state.studio.active_update.game_id == game.game_id else None
    status = "ACTIVE" if active_job else "QUEUED" if jobs else "READY"
    progress = active_job.progress * 100 if active_job else 0
    update_load = size["team"] if active_job else 0
    update_attr = curses.color_pair(4) if jobs else curses.color_pair(3)
    add_text(live_ops, 1, 2, f"STATUS  {status} | v{game.version}", second_width - 4, update_attr | curses.A_BOLD)
    add_text(live_ops, 2, 2, "CURRENT PLAN", second_width - 4, curses.A_BOLD)
    add_text(live_ops, 3, 2, f"Focus       {game.update_focus} ({focus['skill']} skill)", second_width - 4)
    add_text(live_ops, 4, 2, f"Scope       {game.update_size} | +{size['version'][0]}.{size['version'][1]:02d}.{size['version'][2]:02d} -> v{planned_update_version(state.studio, game, game.update_size)}", second_width - 4)
    add_text(live_ops, 5, 2, f"Pipeline    {size['work']:,} work, then fix {size['bugs']} QA bugs | delivery {estimated_update_delivery_weeks(state.studio, game)}w", second_width - 4)
    add_text(live_ops, 6, 2, f"Ship budget {money(size['cost'])} | Active team load {update_load:.0%}", second_width - 4)
    add_text(live_ops, 7, 2, f"Forecast    +{expected_hype:.1f} hype | ~{expected_players:,} returning players", second_width - 4)
    phase = active_job.phase if active_job else "Waiting for queue"
    add_text(live_ops, 9, 2, f"[{meter(progress, 100, 24)}] {progress:.0f}% | {phase}", second_width - 4, curses.color_pair(4) if active_job else 0)
    add_text(live_ops, 10, 2, f"Release history  {game.updates_released} updates | {game.dlcs_released} DLC | {len(jobs)} active/queued", second_width - 4)
    update_queue = ([state.studio.active_update] if state.studio.active_update else []) + state.studio.update_queue
    active_count = 1 if state.studio.active_update else 0
    add_text(live_ops, 12, 2, f"UPDATE QUEUE ({len(update_queue)}) | {active_count} active | {len(state.studio.update_queue)} waiting", second_width - 4, curses.A_BOLD)
    if not update_queue:
        add_text(live_ops, 13, 2, "No active or waiting updates.", second_width - 4)
    for row, job in enumerate(update_queue[:5], 13):
        status = "ACTIVE" if state.studio.active_update and job is state.studio.active_update else "WAITING"
        add_text(live_ops, row, 2, f"{row - 12}. {status:<7} {job.game_title} -> v{job.target_version} | {job.size} / {job.focus}", second_width - 4, curses.color_pair(4) if status == "ACTIVE" else 0)

    recommendation, recommendation_color = game_recommendation(game)
    promotion_queue = state.studio.active_promotions
    promotions = [promotion for promotion in promotion_queue if promotion.game_id == game.game_id]
    active_promotion = promotion_queue[0] if promotion_queue else None
    game_active = 1 if active_promotion and active_promotion.game_id == game.game_id else 0
    game_waiting = len(promotions) - game_active
    weekly_sales = sale.weekly_units if sale else 0
    evergreen = sale.evergreen_units if sale else 0
    demand_multiple = weekly_sales / max(1, evergreen)
    retention = game.monthly_players / max(1, game.peak_monthly_players)
    if game.monthly_players == 0:
        audience_status, audience_color = "DORMANT", 5
    elif retention >= 0.60 and game.monthly_players >= 100:
        audience_status, audience_color = "HEALTHY", 4
    elif retention >= 0.25:
        audience_status, audience_color = "STABLE", 3
    else:
        audience_status, audience_color = "FADING", 5
    genre_fans = state.studio.genre_fans.get(game.genre, 0)
    topic_fans = state.studio.topic_fans.get(game.topic, 0)
    unlocked_promotions = [item for item in PROMOTIONS if state.studio.reputation >= item["rep"]]
    best_promotion = max(unlocked_promotions, key=lambda item: item["hype"])
    can_afford = state.studio.cash >= best_promotion["cost"] + monthly_fixed_cost(state.studio)
    campaign_load = active_promotion.team_share if active_promotion else 0.0
    recommendation_attr = curses.color_pair(recommendation_color) if recommendation_color in (4, 5) else 0
    audience_attr = curses.color_pair(audience_color) if audience_color in (4, 5) else 0
    add_text(strategy, 1, 2, "RECOMMENDED ACTION", third_width - 4, curses.A_BOLD)
    add_text(strategy, 2, 2, recommendation, third_width - 4, recommendation_attr)
    add_text(strategy, 4, 2, "AUDIENCE HEALTH", third_width - 4, curses.A_BOLD)
    add_text(strategy, 5, 2, f"{audience_status:<8} Rating {rating_text(game):>3}/100 | Hype {game.hype:>5.0f}/200", third_width - 4, audience_attr)
    add_text(strategy, 6, 2, f"Retention  {retention:>6.1%} | {game.monthly_players:,} monthly / {game.peak_monthly_players:,} peak", third_width - 4)
    add_text(strategy, 7, 2, f"Demand     {weekly_sales:,}/w | {demand_multiple:.1f}x evergreen floor ({evergreen:,})", third_width - 4)
    add_text(strategy, 9, 2, "FRANCHISE POSITION", third_width - 4, curses.A_BOLD)
    add_text(strategy, 10, 2, f"Generation {game.generation} | {game.genre} audience {genre_fans:,}", third_width - 4)
    add_text(strategy, 11, 2, f"Theme affinity {topic_fans:,} | Storefront {game.channel}", third_width - 4)
    add_text(strategy, 13, 2, "PROMOTION CAPACITY", third_width - 4, curses.A_BOLD)
    add_text(strategy, 14, 2, f"This game {game_active} active / {game_waiting} queued | Studio queue {len(promotion_queue)} | Team load {campaign_load:.0%}", third_width - 4, curses.color_pair(5) if campaign_load >= 0.30 else 0)
    add_text(strategy, 15, 2, f"Best unlocked  {best_promotion['name']} | +{best_promotion['hype']} hype", third_width - 4)
    add_text(strategy, 16, 2, f"Budget {money(best_promotion['cost'])} | {'FUNDED' if can_afford else 'CASH BUFFER TOO LOW'}", third_width - 4, curses.color_pair(4) if can_afford else curses.color_pair(5))
    promotion_names = ", ".join(f"{'ACTIVE' if item is active_promotion else 'QUEUED'} {item.name} ({item.weeks_left}w)" for item in promotions) or "No promotion queued for this game"
    add_text(strategy, 17, 2, promotion_names, third_width - 4)
    add_text(strategy, 18, 2, "P  Open promotion planning", third_width - 4)

    if summary_height >= 5:
        summary_y = bottom_y + detail_height
        left_width = max(42, width // 3)
        right_width = width - left_width - 1
        economics = screen.derwin(summary_height, left_width, summary_y, 0)
        activity = screen.derwin(summary_height, right_width, summary_y, left_width + 1)
        draw_box(economics, "Game Catalogue | Economics")
        draw_box(activity, f"Recent Activity | {game_title(game)}")
        catalog = state.studio.catalog
        tracked_games = [item for item in catalog if item.cost_history_complete]
        tracked_revenue = sum(item.net_revenue for item in tracked_games)
        tracked_cost = sum(game_total_cost(item) for item in tracked_games)
        tracked_profit = tracked_revenue - tracked_cost
        tracked_margin = tracked_profit / tracked_revenue * 100 if tracked_revenue else 0
        rated_games = [item for item in catalog if item.release_date != "Historical"]
        average_rating = sum(item.score for item in rated_games) / len(rated_games) if rated_games else None
        average_rating_attr = curses.color_pair(4) if average_rating is not None and average_rating >= 70 else curses.color_pair(5) if average_rating is not None and average_rating < 45 else 0
        top_game = max(catalog, key=lambda item: item.net_revenue)
        top_audience = max(catalog, key=lambda item: item.monthly_players)
        economics_lines = [
            ("CATALOGUE SCALE", curses.A_BOLD),
            (f"Games in catalogue        {len(catalog)}", 0),
            (f"Cost coverage             {len(tracked_games)}/{len(catalog)} fully tracked", curses.color_pair(4) if len(tracked_games) == len(catalog) else curses.color_pair(5)),
            (f"Average release rating    {average_rating:.1f}/100" if average_rating is not None else "Average release rating    n/a", average_rating_attr),
            (f"Current weekly sales      {sum(item.weekly_units for item in state.studio.active_sales):,}", 0),
            (f"Monthly active players    {sum(item.monthly_players for item in catalog):,}", 0),
            (f"Lifetime units sold       {sum(item.units_sold for item in catalog):,}", 0),
            ("CATALOGUE RETURNS", curses.A_BOLD),
            (f"Lifetime game revenue     {money(sum(item.net_revenue for item in catalog))}", 0),
            (f"Tracked total cost        {money(tracked_cost)}", 0),
            (f"Tracked catalogue profit  {money(tracked_profit)}", (curses.color_pair(4) if tracked_profit >= 0 else curses.color_pair(5)) | curses.A_BOLD),
            (f"Tracked net margin        {tracked_margin:+.1f}%", 0),
            (f"Revenue leader            {game_title(top_game)} ({money(top_game.net_revenue)})", 0),
            ("LIVE OPERATIONS", curses.A_BOLD),
            (f"Update pipeline           {1 if state.studio.active_update else 0} active | {len(state.studio.update_queue)} queued", 0),
            (f"Updates shipped           {sum(item.updates_released for item in catalog)} total", 0),
            (f"Promotion queue           {len(state.studio.active_promotions)} | Team load {campaign_load:.0%}", curses.color_pair(5) if campaign_load >= 0.30 else 0),
            (f"Largest live audience     {game_title(top_audience)} ({top_audience.monthly_players:,})", 0),
        ]
        for row, (text, attr) in enumerate(economics_lines[: summary_height - 2], 1):
            add_text(economics, row, 2, text, left_width - 4, attr)

        related_logs = [message for message in state.logs if game.title in message]
        add_text(activity, 1, 2, "RECENT EVENTS", right_width - 4, curses.A_BOLD)
        journal_slots = min(len(related_logs), max(1, summary_height - 10))
        if not related_logs:
            add_text(activity, 2, 2, "[INFO] No journal entries recorded for this game yet.", right_width - 4, curses.color_pair(2))
            journal_slots = 1
        for row, message in enumerate(related_logs[:journal_slots], 2):
            lower_message = message.lower()
            if "released update" in lower_message or "finished" in lower_message:
                event, attr = "UPDATE", 0
            elif "started" in lower_message and ("push" in lower_message or "campaign" in lower_message or "outreach" in lower_message or "placement" in lower_message or "festival" in lower_message or "event" in lower_message or "showcase" in lower_message):
                event, attr = "PROMO", 0
            elif "released" in lower_message or "launched" in lower_message:
                event, attr = "LAUNCH", 0
            elif "off" in lower_message or "cannot" in lower_message or "failed" in lower_message:
                event, attr = "ALERT", curses.color_pair(5) | curses.A_BOLD
            elif "changed" in lower_message or "continuous updates" in lower_message:
                event, attr = "PLAN", 0
            else:
                event, attr = "INFO", 0
            add_text(activity, row, 2, f"[{event:<6}] {message}", right_width - 4, attr)

        snapshot_row = min(summary_height - 7, journal_slots + 3)
        if snapshot_row > 2:
            add_text(activity, snapshot_row, 2, "CURRENT SNAPSHOT", right_width - 4, curses.A_BOLD)
            add_text(activity, snapshot_row + 1, 2, f"Lifecycle   {game.release_date} | Generation {game.generation} | Storefront {game.channel}", right_width - 4)
            add_text(activity, snapshot_row + 2, 2, f"Demand      {weekly_sales:,}/w vs {evergreen:,}/w floor ({demand_multiple:.1f}x)", right_width - 4)
            add_text(activity, snapshot_row + 3, 2, f"Audience    {game.monthly_players:,} monthly | {retention:.1%} of peak | {audience_status}", right_width - 4, audience_attr)
            add_text(activity, snapshot_row + 4, 2, f"Live ops    {status} | v{game.version} | {game.updates_released} shipped | {len(promotions)} promotions queued", right_width - 4)
            result = money(game_profit(game)) if game.cost_history_complete else "cost history unavailable"
            add_text(activity, snapshot_row + 5, 2, f"Economics   {money(game.net_revenue)} net revenue | {result} profit", right_width - 4, curses.color_pair(5) if game.cost_history_complete and game_profit(game) < 0 else 0)


def promotion_targets(state: GameState) -> list[tuple[int, str, float, str]]:
    targets = []
    if state.studio.current_project:
        project = state.studio.current_project
        targets.append((0, project.title, project.hype, "In development"))
    for game in live_games(state):
        targets.append((game.game_id, game_title(game), game.hype, f"rating {rating_text(game)} | {game.monthly_players:,} monthly | {update_status(game)}"))
    return targets


def draw_marketing_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel_height = height - 4
    state.marketing_tab = 0 if state.marketing_tab <= 0 else 1
    targets = promotion_targets(state)
    catalog_height = min(15, max(9, min(len(targets) + 4, panel_height // 3 + 2)))
    targets_panel = screen.derwin(catalog_height, width, 2, 0)
    if not targets:
        draw_box(targets_panel, "Game Catalogue | 0 promotion targets")
        add_text(targets_panel, 1, 2, "No project or released game to promote.", width - 4)
        return
    state.selected_promotion_target = min(state.selected_promotion_target, max(0, len(targets) - 1))
    draw_game_catalogue_table(
        targets_panel,
        state,
        width,
        catalog_height,
        state.selected_promotion_target,
        state.marketing_tab == 0,
        include_project=True,
        title=f"Game Catalogue | {len(targets)} promotion target{'s' if len(targets) != 1 else ''}",
    )

    bottom_y = 2 + catalog_height
    bottom_height = panel_height - catalog_height
    summary_width = max(38, width * 36 // 100)
    option_width = width - summary_width - 1
    summary_panel = screen.derwin(bottom_height, summary_width, bottom_y, 0)
    options_panel = screen.derwin(bottom_height, option_width, bottom_y, summary_width + 1)
    draw_box(summary_panel, "Selected Game")
    draw_box(options_panel, f"Promotion Planning & Queue | Reputation {state.studio.reputation:.1f}")
    selected_id, selected_title, selected_hype, selected_status = targets[state.selected_promotion_target]
    add_text(summary_panel, 1, 2, selected_title, summary_width - 4, curses.A_BOLD)
    add_text(summary_panel, 2, 2, selected_status, summary_width - 4)
    add_text(summary_panel, 3, 2, f"Hype {selected_hype:.0f}/200", summary_width - 4)
    target_queue = [item for item in state.studio.active_promotions if item.game_id == selected_id]
    active = state.studio.active_promotions[0] if state.studio.active_promotions else None
    target_active = 1 if active in target_queue else 0
    add_text(summary_panel, 5, 2, f"Promotion queue  {target_active} active | {len(target_queue) - target_active} waiting", summary_width - 4, curses.A_BOLD)
    for row, item in enumerate(target_queue[: max(0, bottom_height - 8)], 6):
        status = "ACTIVE" if item is active else "WAITING"
        add_text(summary_panel, row, 2, f"{status:<7} {item.name} | {item.weeks_left}w", summary_width - 4, curses.color_pair(4) if item is active else 0)

    state.selected_promotion = min(state.selected_promotion, len(PROMOTIONS) - 1)
    option_inner = option_width - 4
    option_expanded = option_inner >= 80
    promotion_name_width = 24 if option_expanded else max(12, option_inner - 22)
    effect_width = max(10, option_inner - promotion_name_width - 51)
    option_header = f"  {'PROMOTION':<{promotion_name_width}} {'COST':>10} {'WEEKS':>5} {'HYPE':>6} {'TEAM':>6} {'REQ REP':>7} {'EFFECT':<{effect_width}}" if option_expanded else f"  {'PROMOTION':<{promotion_name_width}} {'COST':>9} {'STATUS':>10}"
    add_text(options_panel, 1, 2, option_header, option_inner, curses.A_BOLD)
    for row, promotion in enumerate(PROMOTIONS, 2):
        selected = row - 2 == state.selected_promotion
        locked = state.studio.reputation < promotion["rep"]
        if option_expanded:
            text = f"{'> ' if selected else '  '}{promotion['name'][:promotion_name_width]:<{promotion_name_width}} {money(promotion['cost']):>10} {promotion['weeks']:>5} {promotion['hype']:>6} {promotion['team']:>6.0%} {promotion['rep']:>7} {promotion['effect'][:effect_width]:<{effect_width}}"
        else:
            status = f"REP {promotion['rep']}" if locked else "AVAILABLE"
            text = f"{'> ' if selected else '  '}{promotion['name'][:promotion_name_width]:<{promotion_name_width}} {money(promotion['cost']):>9} {status:>10}"
        attr = curses.color_pair(5) if locked else curses.color_pair(3) | curses.A_BOLD if selected and state.marketing_tab == 1 else 0
        add_text(options_panel, row, 2, text, option_width - 4, attr)
    queue = state.studio.active_promotions
    queue_row = len(PROMOTIONS) + 3
    team_load = queue[0].team_share if queue else 0.0
    if queue_row < bottom_height - 1:
        cancellation = state.queue_cancellation == "promotion"
        heading = "CANCEL QUEUED PROMOTION" if cancellation else "PROMOTION QUEUE"
        add_text(options_panel, queue_row, 2, f"{heading} ({len(queue)}) | {1 if queue else 0} active | {max(0, len(queue) - 1)} waiting | Team load {team_load:.0%}", option_width - 4, (curses.color_pair(5) if cancellation else 0) | curses.A_BOLD)
        for row, item in enumerate(queue[: max(0, bottom_height - queue_row - 2)], queue_row + 1):
            status = "ACTIVE" if row == queue_row + 1 else "WAITING"
            waiting_index = row - queue_row - 2
            selected = cancellation and status == "WAITING" and waiting_index == state.selected_queue_cancellation
            marker = ">" if selected else str(row - queue_row)
            attr = curses.color_pair(5) | curses.A_BOLD if selected else curses.color_pair(4) if status == "ACTIVE" else 0
            add_text(options_panel, row, 2, f"{marker}. {status:<7} {item.name} | {item.target_title} | {item.weeks_left}w", option_width - 4, attr)


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
    for row, upgrade in enumerate(UPGRADES, 2):
        selected = row - 2 == state.selected_upgrade
        owned = upgrade["key"] in state.studio.upgrades
        recurring = upgrade.get("monthly", 0) + upgrade.get("per_employee", 0) * len(state.studio.team)
        status = "ACTIVE" if owned else "AVAILABLE"
        text = f"{'> ' if selected else '  '}{upgrade['name'][:name_width]:<{name_width}} {money(upgrade['cost']):>{purchase_width}} {money(recurring):>{monthly_width}} {status:>{status_width}} {upgrade['effect'][:effect_width]:<{effect_width}}"
        attr = curses.color_pair(4) if owned else curses.color_pair(3) | curses.A_BOLD if selected else 0
        add_text(panel, row, 2, text, width - 4, attr)
    add_text(panel, len(UPGRADES) + 3, 2, f"Current committed monthly burn: {money(monthly_fixed_cost(state.studio))} | Enter/double-click purchases selected upgrade", width - 4, curses.color_pair(4))


ANALYSIS_TABS = ("Overview", "Cash Flow", "Genres", "Game Catalogue")


def draw_breakdown_bars(panel: curses.window, title: str, data: dict[str, int], y: int, x: int, width: int, color: int) -> None:
    add_text(panel, y, x, title, width, curses.A_BOLD)
    if not data:
        add_text(panel, y + 1, x, "No categorized history yet", width)
        return
    peak = max(data.values())
    bar_width = max(4, width - 30)
    for row, (category, amount) in enumerate(list(data.items())[:6], y + 1):
        filled = max(1, round(bar_width * amount / peak))
        add_text(panel, row, x, f"{category[:15]:<15} {'█' * filled:<{bar_width}} {money(amount):>10}", width, curses.color_pair(color))


def draw_analysis_overview(panel: curses.window, state: GameState) -> None:
    height, width = panel.getmaxyx()
    studio = state.studio
    games_revenue = sum(game.net_revenue for game in studio.catalog)
    tracked_game_costs = sum(game_total_cost(game) for game in studio.catalog if game.cost_history_complete)
    tracked_game_revenue = sum(game.net_revenue for game in studio.catalog if game.cost_history_complete)
    units = sum(game.units_sold for game in studio.catalog)
    target = recommended_team_size(studio)
    add_text(panel, 3, 2, f"Cash {money(studio.cash)}   Runway {runway_months(studio):.1f} months   Burn {money(monthly_fixed_cost(studio))}/month", width - 4, curses.A_BOLD)
    add_text(panel, 4, 2, f"Team {len(studio.team)}/{target} suggested   Followers {studio.followers:,}   Game rep {studio.reputation:.1f}   Contractor rep {studio.contractor_reputation:.1f}", width - 4)
    add_text(panel, 5, 2, f"Games {studio.released_games}   Units {units:,}   Total game revenue {money(games_revenue)}   Tracked costs {money(tracked_game_costs)}   Tracked profit {money(tracked_game_revenue - tracked_game_costs)}", width - 4)
    add_text(panel, 6, 2, f"STUDIO LIFETIME TOTAL: revenue {money(studio.lifetime_revenue)} - all expenses {money(studio.lifetime_expenses)} = {money(studio.lifetime_revenue - studio.lifetime_expenses)} | Contracts {studio.contracts_completed} done/{studio.contracts_failed} failed", width - 4, curses.A_BOLD)
    recent = studio.ledger[:3]
    recent_net = sum(entry.net for entry in recent)
    diagnosis = "Profitable recent quarter" if recent_net > 0 else "Recent operations are consuming runway"
    if len(studio.team) < target:
        diagnosis += "; growth supports another hire if cash can carry the salary"
    add_text(panel, 7, 2, diagnosis, width - 4, curses.color_pair(4) if recent_net > 0 else curses.color_pair(5))
    column_width = (width - 6) // 2
    draw_breakdown_bars(panel, "REVENUE SOURCES / 12 MONTHS", revenue_breakdown(studio), 9, 2, column_width, 4)
    draw_breakdown_bars(panel, "EXPENSE SOURCES / 12 MONTHS", expense_breakdown(studio), 9, 4 + column_width, column_width, 5)
    top_genre = max(studio.genre_fans.items(), key=lambda item: item[1], default=("None yet", 0))
    top_topic = max(studio.topic_fans.items(), key=lambda item: item[1], default=("None yet", 0))
    if height > 18:
        add_text(panel, height - 2, 2, f"Strongest audience: {top_genre[0]} ({top_genre[1]:,}) | Theme: {top_topic[0]} ({top_topic[1]:,})", width - 4, curses.color_pair(3))


def cashflow_entries(state: GameState, count: int) -> list:
    entries = list(reversed(state.studio.ledger[: max(0, count - 1)]))
    entries.append(
        SimpleNamespace(
            month=state.studio.accounting_month + "*",
            revenue=round(state.studio.period_revenue),
            expenses=round(state.studio.period_expenses),
            net=round(state.studio.period_revenue - state.studio.period_expenses),
        )
    )
    return entries[-count:]


def draw_vertical_cashflow(panel: curses.window, state: GameState) -> None:
    height, width = panel.getmaxyx()
    chart_height = max(6, height - 11)
    group_width = 7
    count = max(1, (width - 7) // group_width)
    entries = cashflow_entries(state, count)
    peak = max(1, *(max(entry.revenue, entry.expenses) for entry in entries))
    top = 5
    baseline = top + chart_height
    add_text(panel, 3, 2, f"Monthly vertical cash flow   █ revenue   █ expenses   Scale peak {money(peak)}", width - 4, curses.A_BOLD)
    add_text(panel, 3, 31, "██", 2, curses.color_pair(4))
    add_text(panel, 3, 44, "██", 2, curses.color_pair(5))
    for index, entry in enumerate(entries):
        x = 4 + index * group_width
        revenue_height = round(chart_height * entry.revenue / peak)
        expense_height = round(chart_height * entry.expenses / peak)
        for level in range(chart_height):
            y = baseline - level - 1
            if level < revenue_height:
                add_text(panel, y, x, "██", 2, curses.color_pair(4))
            if level < expense_height:
                add_text(panel, y, x + 2, "██", 2, curses.color_pair(5))
        add_text(panel, baseline, x, "────", 4, curses.color_pair(2))
        add_text(panel, baseline + 1, x, entry.month[-3:], 4)
        add_text(panel, baseline + 2, x, "+" if entry.net >= 0 else "-", 1, curses.color_pair(4) if entry.net >= 0 else curses.color_pair(5))
    add_text(panel, min(height - 2, baseline + 3), 2, "Each pair is revenue (green) beside expenses (red); * is the open month.", width - 4)


def genre_statistics(state: GameState) -> list[dict]:
    statistics = []
    for genre in GENRES:
        games = [game for game in state.studio.catalog if game.genre == genre]
        scored_games = [game for game in games if game.release_date != "Historical"]
        statistics.append(
            {
                "genre": genre,
                "fans": state.studio.genre_fans.get(genre, 0),
                "games": len(games),
                "score": round(sum(game.score for game in scored_games) / len(scored_games)) if scored_games else 0,
                "units": sum(game.units_sold for game in games),
                "revenue": sum(game.net_revenue for game in games),
            }
        )
    return sorted(statistics, key=lambda item: (item["fans"], item["games"], item["revenue"]), reverse=True)


def draw_genre_statistics(panel: curses.window, state: GameState) -> None:
    height, width = panel.getmaxyx()
    statistics = genre_statistics(state)
    state.selected_stat = min(state.selected_stat, len(statistics) - 1)
    visible = height - 6
    start = list_start(state.selected_stat, len(statistics), visible)
    peak_fans = max(1, *(item["fans"] for item in statistics))
    available = width - 4
    genre_width = 24 if width >= 105 else 15
    average_width = 10 if width >= 105 else 5
    bar_width = max(5, min(30, available - genre_width - average_width - 44))
    average_label = "AVG RATING" if average_width == 10 else "AVG"
    header = f"  {'GENRE':<{genre_width}} {'FANS':>9} {'AUDIENCE':<{bar_width}} {'GAMES':>5} {average_label:>{average_width}} {'UNITS':>11} {'GAME NET':>11}"
    add_text(panel, 3, 2, header, available, curses.A_BOLD)
    for row, item in enumerate(statistics[start : start + visible], 4):
        index = start + row - 4
        filled = round(bar_width * item["fans"] / peak_fans)
        average = str(item["score"]) if item["score"] else "-"
        text = f"{'> ' if index == state.selected_stat else '  '}{item['genre'][:genre_width]:<{genre_width}} {item['fans']:>9,} {'█' * filled:<{bar_width}} {item['games']:>5} {average:>{average_width}} {item['units']:>11,} {money(item['revenue']):>11}"
        attr = curses.color_pair(3) | curses.A_BOLD if index == state.selected_stat else curses.color_pair(2)
        add_text(panel, row, 2, text, width - 4, attr)


def catalog_games(state: GameState) -> list:
    return list(reversed(state.studio.catalog))


def draw_game_catalog(panel: curses.window, state: GameState) -> None:
    height, width = panel.getmaxyx()
    games = catalog_games(state)
    if not games:
        add_text(panel, 4, 2, "No tracked releases yet. Finish a game to create franchise statistics.", width - 4)
        return
    state.selected_stat = min(state.selected_stat, len(games) - 1)
    visible = height - 8
    start = list_start(state.selected_stat, len(games), visible)
    wide = width >= 125
    if wide:
        header = f"  {'TITLE':<28} {'GENRE':<16} {'RATING':>6} {'HYPE':>5} {'MONTHLY':>9} {'UNITS':>10} {'NET REVENUE':>11} {'TOTAL COST':>11} {'PROFIT':>11} {'BUGS':>9}"
    else:
        header = f"  {'TITLE':<18} {'RATE':>4} {'MONTHLY':>8} {'REVENUE':>10} {'PROFIT':>10} {'BUGS':>8}"
    add_text(panel, 3, 2, header, width - 4, curses.A_BOLD)
    for row, game in enumerate(games[start : start + visible], 4):
        index = start + row - 4
        cost = money(game_total_cost(game)) if game.cost_history_complete else "n/a"
        profit = money(game_profit(game)) if game.cost_history_complete else "n/a"
        if wide:
            title = game_title(game, 28)
            text = f"{'> ' if index == state.selected_stat else '  '}{title:<28} {game.genre[:16]:<16} {rating_text(game):>6} {game.hype:>5.0f} {game.monthly_players:>9,} {game.units_sold:>10,} {money(game.net_revenue):>11} {cost:>11} {profit:>11} {game.known_bug_count:>9}"
        else:
            title = game_title(game, 18)
            text = f"{'> ' if index == state.selected_stat else '  '}{title:<18} {rating_text(game):>4} {game.monthly_players:>8,} {money(game.net_revenue):>10} {profit:>10} {game.known_bug_count:>8}"
        add_text(panel, row, 2, text, width - 4, curses.color_pair(3) | curses.A_BOLD if index == state.selected_stat else 0)
    game = games[state.selected_stat]
    lineage = "original" if game.sequel_of is None else f"sequel generation {game.generation}"
    add_text(panel, height - 3, 2, f"{game_title(game)} | Theme {game.topic} / Storefront {game.channel} / {lineage} | Rating {rating_text(game)}/100 | Hype {game.hype:.0f} | Monthly active players {game.monthly_players:,}", width - 4, curses.color_pair(4))
    if game.cost_history_complete:
        costs = f"COSTS: setup/store {money(game.production_cost)} + development staff {money(game.labor_cost)} + marketing {money(game.marketing_cost)} + hosting/updates {money(game.post_launch_cost)} = {money(game_total_cost(game))} total | PROFIT {money(game_profit(game))}"
    else:
        costs = "COSTS: full per-game cost tracking was not present when this older title was developed; revenue remains accurate."
    add_text(panel, height - 2, 2, costs, width - 4, curses.color_pair(4) if game.cost_history_complete and game_profit(game) >= 0 else curses.color_pair(5))


def draw_analysis(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel = screen.derwin(height - 4, width, 2, 0)
    draw_box(panel, "Studio Statistics")
    tab_width = max(12, (width - 4) // len(ANALYSIS_TABS))
    for index, tab in enumerate(ANALYSIS_TABS):
        label = f"[{tab}]" if index == state.analysis_view else f" {tab} "
        add_text(panel, 1, 2 + index * tab_width, label, tab_width - 1, curses.color_pair(3) | curses.A_BOLD if index == state.analysis_view else curses.color_pair(4))
    if state.analysis_view == 0:
        draw_analysis_overview(panel, state)
    elif state.analysis_view == 1:
        draw_vertical_cashflow(panel, state)
    elif state.analysis_view == 2:
        draw_genre_statistics(panel, state)
    else:
        draw_game_catalog(panel, state)


def draw_settings(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel = screen.derwin(height - 4, width, 2, 0)
    draw_box(panel, "Settings")
    speed = TIME_LABELS[state.time_speed_index]
    add_text(panel, 1, 2, "CURRENT SETTINGS", width - 4, curses.A_BOLD)
    add_text(panel, 2, 2, f"Simulation speed   {speed}", width - 4)
    add_text(panel, 3, 2, f"Save file          {state.save_path}", width - 4)
    add_text(panel, 4, 2, "Minimum terminal   74 columns x 24 rows", width - 4)
    add_text(panel, 6, 2, "TOP NAVIGATION", width - 4, curses.A_BOLD)
    add_text(panel, 7, 2, "Tab cycles Hub, Game, Team, and Statistics | H/G/T/S jump directly", width - 4)
    add_text(panel, 8, 2, "Settings sits top-right; Save and Quit are inside it. Playback sits beside the bottom date.", width - 4)
    add_text(panel, 10, 2, "Esc opens this popup everywhere. Backspace handles page-level navigation.", width - 4)


def settings_popup_geometry(width: int, height: int) -> tuple[int, int, int, int]:
    popup_width = min(52, max(40, width // 3))
    popup_height = 15
    popup_y = max(2, (height - popup_height) // 2)
    popup_x = max(1, (width - popup_width) // 2)
    return popup_height, popup_width, popup_y, popup_x


def draw_settings_popup(screen: curses.window, state: GameState, width: int, height: int) -> None:
    popup_height, popup_width, popup_y, popup_x = settings_popup_geometry(width, height)
    panel = screen.derwin(popup_height, popup_width, popup_y, popup_x)
    panel.erase()
    draw_box(panel, "Settings")
    add_text(panel, 1, 2, "GAME STATUS", popup_width - 4, curses.A_BOLD)
    add_text(panel, 2, 2, f"Simulation speed   {TIME_LABELS[state.time_speed_index]}", popup_width - 4)
    add_text(panel, 3, 2, f"Save file          {state.save_path}", popup_width - 4)
    add_text(panel, 5, 2, "ACTIONS", popup_width - 4, curses.A_BOLD)
    for index, (row, name) in enumerate(zip(SETTINGS_ACTION_ROWS, SETTINGS_ACTIONS)):
        selected = index == state.selected_setting_action
        label = f"[{name}]" if selected else name
        x = max(2, (popup_width - len(label)) // 2)
        add_text(panel, row, x, label, len(label), curses.A_BOLD if selected else 0)


def training_popup_geometry(width: int, height: int) -> tuple[int, int, int, int]:
    popup_width = min(76, max(58, width - 16))
    popup_height = 17
    return popup_height, popup_width, max(2, (height - popup_height) // 2), max(1, (width - popup_width) // 2)


def draw_training_popup(screen: curses.window, state: GameState, width: int, height: int) -> None:
    employee = selected_roster_employee(state)
    popup_height, popup_width, popup_y, popup_x = training_popup_geometry(width, height)
    panel = screen.derwin(popup_height, popup_width, popup_y, popup_x)
    panel.erase()
    draw_box(panel, "Professional Training")
    if employee is None:
        add_text(panel, 2, 3, "Hire and select an employee before booking education.", popup_width - 6)
        return
    add_text(panel, 1, 3, f"{employee.name} | {employee.role}", popup_width - 6, curses.A_BOLD)
    add_text(panel, 2, 3, f"Current salary {money(employee.annual_salary)}/year | XP {employee.experience}/100", popup_width - 6)
    if employee.training_weeks_left:
        add_text(panel, 4, 3, f"Already studying {employee.training_skill}: {employee.training_weeks_left} weeks remaining.", popup_width - 6, curses.color_pair(5))
    add_text(panel, 4 if not employee.training_weeks_left else 6, 3, "COURSE                         SKILL   COST       RESULT", popup_width - 6, curses.A_BOLD)
    start_row = 5 if not employee.training_weeks_left else 7
    for index, skill_name in enumerate(EMPLOYEE_SKILLS):
        value = employee.all_skills[index]
        selected = index == state.selected_training_skill
        cost = training_cost(employee, skill_name)
        result = "mastered" if value >= 99 else "+4 skill, salary review"
        text = f"{'> ' if selected else '  '}{skill_name:<25} {value:>3}/99  {money(cost):>9}  {result}"
        add_text(panel, start_row + index, 3, text, popup_width - 6, curses.color_pair(3) | curses.A_BOLD if selected else 0)
    add_text(panel, popup_height - 3, 3, "Course length: 4 weeks away from projects, updates, and contracts.", popup_width - 6, curses.color_pair(5))
    add_text(panel, popup_height - 2, 3, "Up/Down chooses | Enter enrolls | Backspace closes", popup_width - 6, curses.color_pair(4))


def draw_insolvency_popup(screen: curses.window, state: GameState, width: int, height: int) -> None:
    popup_width = min(62, max(46, width - 24))
    popup_height = 11
    popup_y = max(2, (height - popup_height) // 2)
    popup_x = max(1, (width - popup_width) // 2)
    panel = screen.derwin(popup_height, popup_width, popup_y, popup_x)
    panel.erase()
    draw_box(panel, "Studio Insolvent")
    add_text(panel, 2, 2, "The studio remained insolvent for eight weeks and has closed.", popup_width - 4, curses.color_pair(5) | curses.A_BOLD)
    add_text(panel, 4, 2, "This run cannot continue.", popup_width - 4)
    add_text(panel, 5, 2, "Delete its save to start a new studio.", popup_width - 4)
    label = "[Delete Save]"
    add_text(panel, 7, (popup_width - len(label)) // 2, label, len(label), curses.A_BOLD)
    add_text(panel, 9, 2, "Press Enter", popup_width - 4, curses.color_pair(4))


def footer_actions(state: GameState, width: int | None = None) -> list[tuple[str, str]]:
    compact = width is not None and width < 120
    dense = width is not None and width < 150
    if state.modal == "main":
        return [("[N]" if compact else control_label("N", "New Game"), "new"), ("[J]" if compact else control_label("J", "Jobs"), "contracts"), ("[U]" if compact else control_label("U", "Upgrades"), "upgrades")]
    if state.modal == "new_game":
        if state.naming_game:
            return [("[Enter]" if compact else control_label("Enter", "Accept title"), "accept_title")]
        if state.new_game_step == -1:
            return [("[Bksp]" if compact else control_label("Backspace", "Catalogue"), "back"), ("[Up/Dn]" if dense else control_label("Up/Down", "Game"), "project_choice"), ("[Enter]" if compact else control_label("Enter", "Choose"), "confirm")]
        panel_names = ("Genre", "Theme", "Production Plan", "Storefront")
        if compact:
            actions = [(control_label("Bksp", "Prev"), "back"), ("[Up/Dn]", "new_game_selection")]
            actions.extend([("[E]", "type_title"), ("[R]", "random_title")])
            actions.append((control_label("Enter", "Green" if state.new_game_step == 3 else "Next"), "confirm"))
        else:
            actions = [(control_label("Backspace", "Previous"), "back"), (control_label("Up/Down", panel_names[state.new_game_step]), "new_game_selection")]
            enter_label = control_label("Enter", "Greenlight" if state.new_game_step == 3 else "Next")
            actions.extend([(control_label("E", "Edit title"), "type_title"), (control_label("R", "Random"), "random_title"), (enter_label, "confirm")])
        return actions
    if state.modal == "team":
        if compact:
            actions = [("[E]", "applicants"), ("[T]", "roster"), ("[Enter]", "hire"), ("[D]", "dismiss")]
        else:
            actions = [(control_label("E", "Employ"), "applicants"), (control_label("T", "Team"), "roster"), (control_label("Enter", "Hire"), "hire"), (control_label("D", "Dismiss"), "dismiss")]
        if state.team_tab == 1 and selected_roster_employee(state):
            actions.append(("[L]" if compact else control_label("L", "Learn"), "train"))
        return actions
    if state.modal == "contracts":
        auto = "ON" if state.studio.auto_contracts else "OFF"
        return [("[Bksp]" if compact else control_label("Backspace", "Hub"), "back"), ("[Enter]" if compact else control_label("Enter", "Accept"), "accept_contract"), (control_label("C", "Auto") if compact else control_label("C", f"Auto {auto}"), "toggle_contracts")]
    if state.modal == "games":
        project = state.studio.current_project
        if project and project.pending_decision is not None:
            return [
                ("[Up/Dn]" if compact else control_label("Up/Down", "Option"), "production_option"),
                ("[Enter]" if compact else control_label("Enter", "Commit Decision"), "resolve_decision"),
            ]
        games = live_games(state)
        if not games:
            actions = []
            if state.studio.current_project is None:
                actions.append(("[N]" if compact else control_label("N", "New Game"), "new"))
            if state.studio.current_project:
                actions.append(("[P]" if compact else control_label("P", "Promotion"), "game_marketing"))
            return actions
        return [("[N]" if compact else control_label("N", "New Game"), "new"), ("[U]" if compact else control_label("U", "Update Planner"), "open_update_planner"), ("[P]" if compact else control_label("P", "Promotion"), "game_marketing")]
    if state.modal == "update_planner":
        if state.queue_cancellation == "update":
            return [("[Bksp]" if compact else control_label("Backspace", "Return to planning"), "leave_queue_cancellation"), ("[Up/Dn]" if compact else control_label("Up/Down", "Queued update"), "queue_cancellation_selection"), ("[Enter]" if compact else control_label("Enter", "Cancel selected"), "cancel_selected_queue_item")]
        games = live_games(state)
        if not games:
            return [("[Bksp]" if compact else control_label("Backspace", "Game"), "back")]
        if state.games_tab == 0:
            actions = [("[Bksp]" if compact else control_label("Backspace", "Game"), "back"), ("[Up/Dn]" if compact else control_label("Up/Down", "Game"), "update_game_selection"), ("[Enter]" if compact else control_label("Enter", "Select"), "select_update_game")]
            actions.append(("[C]" if compact else control_label("C", "Cancel"), "enter_queue_cancellation"))
            return actions
        if state.games_tab == 1:
            actions = [("[Bksp]" if compact else control_label("Backspace", "Game"), "back"), ("[Up/Dn]" if compact else control_label("Up/Down", "Scope"), "update_scope_selection"), ("[Enter]" if compact else control_label("Enter", "Select"), "select_update_scope")]
        else:
            actions = [("[Bksp]" if compact else control_label("Backspace", "Scope"), "back"), ("[Up/Dn]" if compact else control_label("Up/Down", "Area"), "update_area_selection"), ("[Enter]" if compact else control_label("Enter", "Queue Update"), "enter_only")]
        actions.append(("[C]" if compact else control_label("C", "Cancel"), "enter_queue_cancellation"))
        return actions
    if state.modal == "marketing":
        if state.queue_cancellation == "promotion":
            return [("[Bksp]" if compact else control_label("Backspace", "Return to planning"), "leave_queue_cancellation"), ("[Up/Dn]" if compact else control_label("Up/Down", "Queued promotion"), "queue_cancellation_selection"), ("[Enter]" if compact else control_label("Enter", "Cancel selected"), "cancel_selected_queue_item")]
        if state.marketing_tab == 0:
            actions = [("[Bksp]" if compact else control_label("Backspace", "Catalogue"), "back"), ("[Up/Dn]" if compact else control_label("Up/Down", "Game"), "marketing_selection"), ("[Enter]" if compact else control_label("Enter", "Select"), "select_marketing_target")]
        else:
            actions = [("[Bksp]" if compact else control_label("Backspace", "Planning"), "back"), ("[Up/Dn]" if compact else control_label("Up/Down", "Promotion"), "marketing_selection"), ("[Enter]" if compact else control_label("Enter", "Buy"), "buy_promotion")]
        actions.append(("[C]" if compact else control_label("C", "Cancel"), "enter_queue_cancellation"))
        return actions
    if state.modal == "upgrades":
        return [("[Bksp]" if compact else control_label("Backspace", "Hub"), "back"), ("[Enter]" if compact else control_label("Enter", "Buy"), "buy")]
    if state.modal == "settings":
        return [("[Bksp]" if compact else control_label("Backspace", "Hub"), "back")]
    return []


def global_actions(state: GameState, width: int) -> list[tuple[str, str]]:
    return [("[Esc]" if width < 120 else control_label("Esc", "Settings"), "settings")]


def global_action_layout(state: GameState, width: int) -> list[tuple[str, str, int]]:
    actions = global_actions(state, width)
    total = sum(len(label) for label, _ in actions) + max(0, len(actions) - 1)
    x = max(2, width - total - 2)
    layout = []
    for label, action in actions:
        layout.append((label, action, x))
        x += len(label) + 1
    return layout


def bottom_date_text(state: GameState, width: int) -> str:
    year = (state.clock.week - 1) // 52 + 1
    week = (state.clock.week - 1) % 52 + 1
    if width >= 100:
        return f"{state.clock.current_date:%d %b %Y}  Y {year}  W {week}"
    return f"{state.clock.current_date:%d%b%y} Y{year} W{week}"


def horizontal_actions(state: GameState) -> tuple[str, str]:
    if state.modal == "new_game" and state.new_game_step in (0, 1, 2):
        return "new_game_adjust_left", "new_game_adjust_right"
    if state.modal == "analysis":
        return "previous_view", "next_view"
    return "slower", "faster"


def bottom_time_layout(state: GameState, width: int) -> list[tuple[str, str, int]]:
    speed = "||" if state.time_speed_index == 0 else ">" * state.time_speed_index
    left_action, right_action = horizontal_actions(state)
    actions = [("[<]", left_action), (f"[Space]{speed}", "pause"), ("[>]", right_action)]
    x = 3 + len(bottom_date_text(state, width))
    layout = []
    for label, action in actions:
        layout.append((label, action, x))
        x += len(label) + 1
    return layout


def footer_layout(state: GameState, width: int) -> list[tuple[str, str, int]]:
    return centered_layout(footer_actions(state, width), width)


def footer_button_ranges(state: GameState, width: int | None = None) -> list[tuple[str, int, int]]:
    resolved_width = width or 120
    return [(action, x, x + len(label)) for label, action, x in footer_layout(state, resolved_width)]


def draw_footer_label(screen: curses.window, y: int, x: int, label: str, width: int) -> None:
    cursor = 0
    while cursor < len(label) and x + cursor < width:
        shortcut_start = label.find("[", cursor)
        if shortcut_start < 0:
            add_text(screen, y, x + cursor, label[cursor:], width - x - cursor, curses.color_pair(1))
            break
        if shortcut_start > cursor:
            add_text(screen, y, x + cursor, label[cursor:shortcut_start], width - x - cursor, curses.color_pair(1))
        shortcut_end = label.find("]", shortcut_start) + 1
        if shortcut_end <= 0:
            shortcut_end = len(label)
        add_text(screen, y, x + shortcut_start, label[shortcut_start:shortcut_end], width - x - shortcut_start, curses.color_pair(1) | curses.A_BOLD)
        cursor = shortcut_end


def draw_footer(screen: curses.window, state: GameState, height: int, width: int) -> None:
    studio = state.studio
    title = "INDIE GAME DEV SIM"
    if width >= 150:
        progress_width = 34
    elif width >= 100:
        progress_width = 28
    else:
        progress_width = 20
    bar_width = width - 2
    filled = round(progress_width * state.clock.progress)
    progress = "█" * filled + "░" * (progress_width - filled)
    if width >= 150:
        line = f" [{progress}] | Games {studio.released_games} | Team {len(studio.team)} | Fans {studio.followers:,} | Game reputation {studio.reputation:.1f} | Contractor reputation {studio.contractor_reputation:.1f}"
    elif width >= 100:
        line = f" [{progress}] | Games {studio.released_games} | Team {len(studio.team)} | Fans {studio.followers:,} | GRep {studio.reputation:.1f} | CRep {studio.contractor_reputation:.1f}"
    else:
        line = f" [{progress}] | G {studio.released_games} | T {len(studio.team)} | F {studio.followers:,} | GR {studio.reputation:.1f} | CR {studio.contractor_reputation:.1f}"
    add_text(screen, height - 2, 1, line.ljust(bar_width), bar_width, curses.color_pair(4))
    add_text(screen, height - 1, 1, " " * bar_width, bar_width, curses.color_pair(1))
    date_text = bottom_date_text(state, width)
    add_text(screen, height - 1, 2, date_text, len(date_text), curses.color_pair(1) | curses.A_BOLD)
    for label, _, x in bottom_time_layout(state, width):
        draw_footer_label(screen, height - 1, x, label, width)
    if width >= 120:
        title_x = width - len(title) - 2
        add_text(screen, height - 1, title_x, title, len(title), curses.color_pair(1) | curses.A_BOLD)


def draw_screen(screen: curses.window, state: GameState) -> None:
    height, width = screen.getmaxyx()
    screen.erase()
    if height < 24 or width < 74:
        add_text(screen, 0, 0, "Terminal too small. Need at least 74x24. Resize or press Q.", width)
        return
    draw_header(screen, state, width)
    if state.modal == "new_game":
        draw_new_game(screen, state, width, height)
    elif state.modal == "team":
        draw_team_screen(screen, state, width, height)
    elif state.modal == "contracts":
        draw_contract_screen(screen, state, width, height)
    elif state.modal == "games":
        draw_games_screen(screen, state, width, height)
    elif state.modal == "update_planner":
        draw_update_planner_screen(screen, state, width, height)
    elif state.modal == "marketing":
        draw_marketing_screen(screen, state, width, height)
    elif state.modal == "upgrades":
        draw_upgrades(screen, state, width, height)
    elif state.modal == "analysis":
        draw_analysis(screen, state, width, height)
    elif state.modal == "settings":
        draw_settings(screen, state, width, height)
    else:
        y = draw_dashboard(screen, state, width)
        draw_main_content(screen, state, width, height, y)
    draw_footer(screen, state, height, width)
    project = state.studio.current_project
    if project and project.pending_decision is not None:
        draw_production_review(screen, state, width, height)
    if state.training_open:
        draw_training_popup(screen, state, width, height)
    if state.settings_open:
        draw_settings_popup(screen, state, width, height)
    if state.studio.closed:
        draw_insolvency_popup(screen, state, width, height)


def toggle_pause(state: GameState) -> None:
    if state.time_speed_index == 0:
        state.time_speed_index = max(1, state.resume_speed_index)
    else:
        state.resume_speed_index = state.time_speed_index
        state.time_speed_index = 0


def open_new_game(state: GameState) -> None:
    if state.studio.current_project:
        state.log("Ship or cancel the current project before planning another.")
        return
    state.modal = "new_game"
    state.new_game_step = -1
    state.selected_focus = 0
    state.selected_sequel_choice = 0


def save_state(state: GameState) -> None:
    runtime_speed = state.time_speed_index
    try:
        if state.settings_open and state.settings_resume_on_close:
            state.time_speed_index = state.resume_speed_index
        save_game(state)
        state.log(f"Saved studio to {state.save_path}.")
    except OSError as error:
        state.log(f"Save failed: {error}.")
    finally:
        state.time_speed_index = runtime_speed


def delete_save_and_restart(state: GameState) -> bool:
    save_path = state.save_path
    try:
        Path(save_path).unlink(missing_ok=True)
    except OSError as error:
        state.log(f"Could not delete save: {error}.")
        return False
    fresh_state = GameState(save_path=save_path)
    state.__dict__.clear()
    state.__dict__.update(fresh_state.__dict__)
    return True


def open_settings(state: GameState) -> None:
    if state.settings_open:
        return
    state.settings_resume_on_close = state.time_speed_index != 0
    if state.settings_resume_on_close:
        state.resume_speed_index = state.time_speed_index
        state.time_speed_index = 0
    state.selected_setting_action = 0
    state.settings_open = True


def close_settings(state: GameState) -> None:
    if not state.settings_open:
        return
    state.settings_open = False
    if state.settings_resume_on_close and not state.studio.closed:
        state.time_speed_index = max(1, state.resume_speed_index)
    state.settings_resume_on_close = False


def open_training(state: GameState) -> None:
    if state.training_open or selected_roster_employee(state) is None:
        if selected_roster_employee(state) is None:
            state.log("Hire and select an employee before booking training.")
        return
    state.training_resume_on_close = state.time_speed_index != 0
    if state.training_resume_on_close:
        state.resume_speed_index = state.time_speed_index
        state.time_speed_index = 0
    state.selected_training_skill = 0
    state.training_open = True


def close_training(state: GameState) -> None:
    if not state.training_open:
        return
    state.training_open = False
    if state.training_resume_on_close and not state.studio.closed:
        state.time_speed_index = max(1, state.resume_speed_index)
    state.training_resume_on_close = False


def confirm_training(state: GameState) -> bool:
    if not start_employee_training(state):
        return False
    close_training(state)
    return True


def activate_settings_action(state: GameState) -> bool:
    if state.selected_setting_action == 0:
        close_settings(state)
        return True
    if state.selected_setting_action == 1:
        save_state(state)
        return True
    return False


def enter_queue_cancellation(state: GameState) -> bool:
    if state.modal == "update_planner":
        if not state.studio.update_queue:
            state.log("There are no waiting updates to cancel; the active update cannot be cancelled.")
            return False
        state.queue_cancellation = "update"
    elif state.modal == "marketing":
        if len(state.studio.active_promotions) <= 1:
            state.log("There are no waiting promotions to cancel; the active promotion cannot be cancelled.")
            return False
        state.queue_cancellation = "promotion"
    else:
        return False
    state.selected_queue_cancellation = 0
    return True


def queue_cancellation_count(state: GameState) -> int:
    if state.queue_cancellation == "update":
        return len(state.studio.update_queue)
    if state.queue_cancellation == "promotion":
        return max(0, len(state.studio.active_promotions) - 1)
    return 0


def cancel_selected_queue_item(state: GameState) -> bool:
    if state.queue_cancellation == "update":
        return cancel_queued_update(state)
    if state.queue_cancellation == "promotion":
        return cancel_queued_promotion(state)
    return False


def perform_footer_action(state: GameState, action: str) -> bool:
    if action == "quit":
        return False
    if action == "new":
        open_new_game(state)
    elif action == "contracts":
        state.modal = "contracts"
    elif action == "marketing":
        state.modal = "marketing"
        state.marketing_tab = 0
        state.queue_cancellation = ""
    elif action == "toggle_contracts":
        toggle_auto_contracts(state)
    elif action == "accept_contract":
        accept_contract_offer(state)
    elif action == "team":
        state.modal = "team"
    elif action == "upgrades":
        state.modal = "upgrades"
    elif action == "analysis":
        state.modal = "analysis"
    elif action == "settings":
        if state.settings_open:
            close_settings(state)
        else:
            open_settings(state)
    elif action == "games":
        state.modal = "games"
        state.games_tab = 0
    elif action == "open_update_planner":
        state.modal = "update_planner"
        state.games_tab = 0
        state.queue_cancellation = ""
    elif action == "update_game_selection":
        games = live_games(state)
        if games:
            state.selected_game = (state.selected_game + 1) % len(games)
    elif action == "select_update_game":
        if live_games(state):
            state.games_tab = 1
    elif action in ("update_scope_selection", "update_area_selection"):
        games = live_games(state)
        if games:
            game_id = games[min(state.selected_game, len(games) - 1)].game_id
            if action == "update_scope_selection":
                cycle_game_update_size(state, game_id)
            else:
                cycle_game_update_focus(state, game_id)
    elif action == "select_update_scope":
        if live_games(state):
            state.games_tab = 2
    elif action == "promote_game":
        games = live_games(state)
        if games:
            game_id = games[min(state.selected_game, len(games) - 1)].game_id
            targets = promotion_targets(state)
            state.selected_promotion_target = next((index for index, target in enumerate(targets) if target[0] == game_id), 0)
            state.modal = "marketing"
            state.marketing_tab = 1
    elif action == "game_marketing":
        targets = promotion_targets(state)
        if targets:
            games = live_games(state)
            selected_id = games[min(state.selected_game, len(games) - 1)].game_id if games else 0
            state.selected_promotion_target = next((index for index, target in enumerate(targets) if target[0] == selected_id), 0)
        state.modal = "marketing"
        state.marketing_tab = 0
        state.queue_cancellation = ""
    elif action == "production_option":
        state.selected_project_decision = (state.selected_project_decision + 1) % 2
    elif action == "resolve_decision":
        resolve_project_decision(state, state.selected_project_decision)
    elif action == "enter_queue_cancellation":
        enter_queue_cancellation(state)
    elif action == "leave_queue_cancellation":
        state.queue_cancellation = ""
    elif action == "queue_cancellation_selection":
        count = queue_cancellation_count(state)
        if count:
            state.selected_queue_cancellation = (state.selected_queue_cancellation + 1) % count
    elif action == "cancel_selected_queue_item":
        cancel_selected_queue_item(state)
    elif action == "buy_promotion":
        targets = promotion_targets(state)
        if targets:
            buy_promotion(state, targets[state.selected_promotion_target][0], state.selected_promotion)
    elif action == "marketing_selection":
        if state.marketing_tab == 0:
            targets = promotion_targets(state)
            if targets:
                state.selected_promotion_target = (state.selected_promotion_target + 1) % len(targets)
        else:
            state.selected_promotion = (state.selected_promotion + 1) % len(PROMOTIONS)
    elif action == "select_marketing_target":
        state.marketing_tab = 1
    elif action in ("previous_target", "next_target"):
        targets = promotion_targets(state)
        if targets:
            delta = -1 if action == "previous_target" else 1
            state.selected_promotion_target = (state.selected_promotion_target + delta) % len(targets)
    elif action == "slower":
        state.time_speed_index = max(1, state.time_speed_index - 1)
        state.resume_speed_index = state.time_speed_index
    elif action == "faster":
        state.time_speed_index = min(len(TIME_SPEEDS) - 1, max(1, state.time_speed_index + 1))
        state.resume_speed_index = state.time_speed_index
    elif action == "pause":
        toggle_pause(state)
    elif action == "save":
        save_state(state)
    elif action == "back":
        if state.modal == "new_game":
            handle_new_game_key(state, curses.KEY_BACKSPACE)
        elif state.modal == "marketing":
            if state.marketing_tab == 1:
                state.marketing_tab = 0
            else:
                state.modal = "games"
        elif state.modal == "update_planner":
            if state.games_tab > 0:
                state.games_tab -= 1
            else:
                state.modal = "games"
        else:
            state.modal = "main"
    elif action == "confirm":
        handle_new_game_key(state, 10)
    elif action == "accept_title":
        if state.draft_title.strip():
            state.draft_title = state.draft_title.strip()
            state.naming_game = False
    elif action == "cancel_title":
        state.naming_game = False
    elif action == "project_choice":
        choices = sequel_choices(state)
        state.selected_sequel_choice = (state.selected_sequel_choice + 1) % len(choices)
    elif action == "new_game_selection":
        handle_new_game_key(state, curses.KEY_DOWN)
    elif action == "new_game_adjust_left":
        handle_new_game_key(state, curses.KEY_LEFT)
    elif action == "new_game_adjust_right":
        handle_new_game_key(state, curses.KEY_RIGHT)
    elif action == "random_title":
        state.naming_game = False
        state.title_roll += 1
        refresh_draft_title(state)
    elif action == "type_title":
        state.naming_game = True
        state.draft_title = ""
    elif action == "applicants":
        state.team_tab = 0
    elif action == "roster":
        state.team_tab = 1
    elif action == "hire":
        if state.team_tab == 0:
            hire_candidate(state)
    elif action == "dismiss":
        if state.team_tab == 1:
            dismiss_employee(state)
    elif action == "train":
        if state.team_tab == 1:
            open_training(state)
    elif action == "buy":
        buy_upgrade(state)
    elif action == "previous_view":
        state.analysis_view = (state.analysis_view - 1) % len(ANALYSIS_TABS)
        state.selected_stat = 0
    elif action == "next_view":
        state.analysis_view = (state.analysis_view + 1) % len(ANALYSIS_TABS)
        state.selected_stat = 0
    return True


def handle_new_game_key(state: GameState, key: int) -> None:
    if state.new_game_step == -1:
        choices = sequel_choices(state)
        if key in (10, 13, curses.KEY_ENTER):
            choice = choices[state.selected_sequel_choice]
            if choice is None:
                state.sequel_game_id = None
                state.selected_secondary_genre = state.selected_genre
                state.selected_secondary_topic = state.selected_topic
                state.new_game_step = 0
                state.title_roll += 1
                refresh_draft_title(state)
            else:
                prepare_sequel(state, choice)
        elif key in (8, 127, curses.KEY_BACKSPACE):
            state.modal = "games"
        elif key == curses.KEY_UP:
            state.selected_sequel_choice = (state.selected_sequel_choice - 1) % len(choices)
        elif key == curses.KEY_DOWN:
            state.selected_sequel_choice = (state.selected_sequel_choice + 1) % len(choices)
        return
    previous_concept = (state.selected_genre, state.selected_secondary_genre, state.selected_topic, state.selected_secondary_topic)
    if key in (10, 13, curses.KEY_ENTER):
        if state.new_game_step < 3:
            state.new_game_step += 1
        else:
            start_project(state)
    elif key in (8, 127, curses.KEY_BACKSPACE):
        state.new_game_step = max(-1, state.new_game_step - 1)
    elif key in (ord("e"), ord("E")):
        state.naming_game = True
        state.draft_title = ""
    elif key in (ord("r"), ord("R")):
        state.title_roll += 1
        refresh_draft_title(state)
    elif key == curses.KEY_UP:
        if state.new_game_step == 0:
            state.selected_genre = (state.selected_genre - 1) % len(GENRES)
        elif state.new_game_step == 1:
            state.selected_topic = (state.selected_topic - 1) % len(TOPICS)
        elif state.new_game_step == 2:
            state.selected_focus = (state.selected_focus - 1) % 7
        else:
            state.selected_channel = (state.selected_channel - 1) % len(CHANNELS)
    elif key == curses.KEY_DOWN:
        if state.new_game_step == 0:
            state.selected_genre = (state.selected_genre + 1) % len(GENRES)
        elif state.new_game_step == 1:
            state.selected_topic = (state.selected_topic + 1) % len(TOPICS)
        elif state.new_game_step == 2:
            state.selected_focus = (state.selected_focus + 1) % 7
        else:
            state.selected_channel = (state.selected_channel + 1) % len(CHANNELS)
    elif key in (curses.KEY_LEFT, curses.KEY_RIGHT) and state.new_game_step in (0, 1, 2):
        delta = -1 if key == curses.KEY_LEFT else 1
        if state.new_game_step == 0:
            state.selected_secondary_genre = (state.selected_secondary_genre + delta) % len(GENRES)
        elif state.new_game_step == 1:
            state.selected_secondary_topic = (state.selected_secondary_topic + delta) % len(TOPICS)
        else:
            fields = (
                ("selected_scope", len(SCOPES)),
                ("selected_format", len(GAME_FORMATS)),
                ("selected_audience", len(AUDIENCES)),
                ("selected_creative_primary", len(CREATIVE_DIRECTIONS)),
                ("selected_creative_secondary", len(CREATIVE_DIRECTIONS)),
                ("selected_release_strategy", len(RELEASE_STRATEGIES)),
                ("selected_marketing", len(MARKETING)),
            )
            attribute, count = fields[state.selected_focus]
            setattr(state, attribute, (getattr(state, attribute) + delta) % count)
    if previous_concept != (state.selected_genre, state.selected_secondary_genre, state.selected_topic, state.selected_secondary_topic):
        state.sequel_game_id = None
        state.title_roll += 1
        refresh_draft_title(state)


def handle_team_key(state: GameState, key: int) -> None:
    if key in (8, 127, curses.KEY_BACKSPACE):
        state.modal = "main"
    elif key in (ord("e"), ord("E")):
        state.team_tab = 0
    elif key == curses.KEY_UP:
        if state.team_tab == 0 and state.studio.applicants:
            state.selected_employee = (state.selected_employee - 1) % len(state.studio.applicants)
        else:
            choices = len(state.studio.team)
            state.selected_roster = state.selected_roster % choices - 1
    elif key == curses.KEY_DOWN:
        if state.team_tab == 0 and state.studio.applicants:
            state.selected_employee = (state.selected_employee + 1) % len(state.studio.applicants)
        else:
            choices = len(state.studio.team)
            state.selected_roster = (state.selected_roster + 2) % choices - 1
    elif key in (10, 13, curses.KEY_ENTER) and state.team_tab == 0:
        hire_candidate(state)
    elif key in (ord("d"), ord("D")) and state.team_tab == 1:
        dismiss_employee(state)
    elif key in (ord("l"), ord("L")) and state.team_tab == 1:
        open_training(state)


def handle_mouse(state: GameState, dimensions: tuple[int, int]) -> bool | None:
    try:
        _, x, y, _, buttons = curses.getmouse()
    except curses.error:
        return
    height, width = dimensions
    wheel_up = bool(buttons & getattr(curses, "BUTTON4_PRESSED", 0))
    wheel_down = bool(buttons & getattr(curses, "BUTTON5_PRESSED", 0))
    if wheel_up or wheel_down:
        if state.settings_open:
            return
        if state.queue_cancellation:
            count = queue_cancellation_count(state)
            if count:
                delta = -1 if wheel_up else 1
                state.selected_queue_cancellation = (state.selected_queue_cancellation + delta) % count
            return
        if state.training_open:
            delta = -1 if wheel_up else 1
            state.selected_training_skill = (state.selected_training_skill + delta) % len(EMPLOYEE_SKILLS)
            return
        project = state.studio.current_project
        if project and project.pending_decision is not None:
            state.selected_project_decision = (state.selected_project_decision + 1) % 2
            return
        key = curses.KEY_UP if wheel_up else curses.KEY_DOWN
        if state.modal == "analysis":
            if state.analysis_view in (2, 3):
                item_count = len(GENRES) if state.analysis_view == 2 else len(state.studio.catalog)
                if item_count:
                    state.selected_stat = (state.selected_stat + (-1 if wheel_up else 1)) % item_count
            else:
                state.analysis_view = (state.analysis_view + (-1 if wheel_up else 1)) % len(ANALYSIS_TABS)
        elif state.modal == "new_game" and state.new_game_step == 2:
            handle_new_game_key(state, curses.KEY_LEFT if wheel_up else curses.KEY_RIGHT)
        elif state.modal == "team":
            handle_team_key(state, key)
        elif state.modal == "contracts" and state.studio.contract_offers:
            state.selected_contract = (state.selected_contract + (-1 if wheel_up else 1)) % len(state.studio.contract_offers)
        elif state.modal == "games" and state.studio.catalog:
            state.selected_game = (state.selected_game + (-1 if wheel_up else 1)) % len(state.studio.catalog)
        elif state.modal == "update_planner" and state.games_tab == 0 and state.studio.catalog:
            state.selected_game = (state.selected_game + (-1 if wheel_up else 1)) % len(state.studio.catalog)
        elif state.modal == "marketing":
            if state.marketing_tab == 0:
                targets = promotion_targets(state)
                if targets:
                    state.selected_promotion_target = (state.selected_promotion_target + (-1 if wheel_up else 1)) % len(targets)
            else:
                state.selected_promotion = (state.selected_promotion + (-1 if wheel_up else 1)) % len(PROMOTIONS)
        elif state.modal == "upgrades":
            state.selected_upgrade = (state.selected_upgrade + (-1 if wheel_up else 1)) % len(UPGRADES)
        elif state.modal == "new_game":
            handle_new_game_key(state, key)
        elif state.modal == "main":
            perform_footer_action(state, "faster" if wheel_up else "slower")
        return

    right_click = bool(buttons & (getattr(curses, "BUTTON3_CLICKED", 0) | getattr(curses, "BUTTON3_RELEASED", 0)))
    if state.queue_cancellation:
        return
    if right_click and state.settings_open:
        close_settings(state)
        return
    project = state.studio.current_project
    if right_click and (state.training_open or (project and project.pending_decision is not None)):
        return
    if right_click and state.modal != "main":
        owner_root = TOP_TABS[active_top_tab(state)][2]
        state.naming_game = False
        state.queue_cancellation = ""
        state.modal = owner_root if state.modal != owner_root else "main"
        if state.modal == "games":
            state.games_tab = 0
        return
    left_click = bool(
        buttons
        & (
            getattr(curses, "BUTTON1_CLICKED", 0)
            | getattr(curses, "BUTTON1_RELEASED", 0)
            | getattr(curses, "BUTTON1_DOUBLE_CLICKED", 0)
        )
    )
    if not left_click:
        return
    double_click = bool(buttons & getattr(curses, "BUTTON1_DOUBLE_CLICKED", 0))

    if state.training_open:
        employee = selected_roster_employee(state)
        if employee:
            _, popup_width, popup_y, popup_x = training_popup_geometry(width, height)
            start_row = popup_y + (7 if employee.training_weeks_left else 5)
            if popup_x <= x < popup_x + popup_width and start_row <= y < start_row + len(EMPLOYEE_SKILLS):
                state.selected_training_skill = y - start_row
                if double_click:
                    confirm_training(state)
        return
    if project and project.pending_decision is not None and not state.settings_open:
        _, popup_width, popup_y, popup_x = production_review_geometry(width, height)
        for option_index, row in enumerate((popup_y + 8, popup_y + 12)):
            if popup_x <= x < popup_x + popup_width and row <= y <= row + 1:
                state.selected_project_decision = option_index
                if double_click:
                    resolve_project_decision(state, option_index)
                break
        return

    if y == 0:
        for label, action, start in top_control_layout(state, width):
            if start <= x < start + len(label):
                if state.settings_open and action not in ("settings", "save", "quit"):
                    return
                if action.startswith("top_tab_"):
                    activate_top_tab(state, int(action.rsplit("_", 1)[1]))
                    return
                return perform_footer_action(state, action)
        return
    if y == 1 and top_context_uses_second_row(state, width):
        if state.settings_open:
            return
        for action, start, end in footer_button_ranges(state, width):
            if start <= x < end:
                return perform_footer_action(state, action)
        return
    if y == height - 1:
        if state.settings_open:
            return
        for label, action, start in bottom_time_layout(state, width):
            if start <= x < start + len(label):
                return perform_footer_action(state, action)
        return
    if y == height - 2 or state.settings_open:
        if state.settings_open:
            _, popup_width, popup_y, popup_x = settings_popup_geometry(width, height)
            if popup_x <= x < popup_x + popup_width:
                for action_index, row in enumerate(SETTINGS_ACTION_ROWS):
                    if y == popup_y + row:
                        state.selected_setting_action = action_index
                        if double_click:
                            return activate_settings_action(state)
                        break
        return

    if state.modal == "main":
        return

    if state.modal == "analysis":
        tab_width = max(12, (width - 4) // len(ANALYSIS_TABS))
        if y == 3:
            state.analysis_view = min(len(ANALYSIS_TABS) - 1, max(0, (x - 2) // tab_width))
            state.selected_stat = 0
        elif state.analysis_view in (2, 3) and y >= 6:
            item_count = len(GENRES) if state.analysis_view == 2 else len(state.studio.catalog)
            visible = height - 11 if state.analysis_view == 3 else height - 10
            start = list_start(state.selected_stat, item_count, visible) if item_count else 0
            index = start + y - 6
            if 0 <= index < item_count:
                state.selected_stat = index
        return

    if state.modal == "upgrades":
        row = y - 4
        if 0 <= row < len(UPGRADES):
            state.selected_upgrade = row
            if double_click:
                buy_upgrade(state)
        return

    if state.modal == "contracts":
        board_width = max(46, width * 2 // 3)
        row = y - 4
        if x <= board_width and 0 <= row < len(state.studio.contract_offers):
            state.selected_contract = row
            if double_click:
                accept_contract_offer(state)
        return

    if state.modal in ("games", "update_planner"):
        project = state.studio.current_project
        if state.modal == "games" and project and project.pending_decision is not None:
            option_row = (y - 11) // 4
            if option_row in (0, 1):
                state.selected_project_decision = option_row
                if double_click:
                    resolve_project_decision(state, option_row)
            return
        games = live_games(state)
        if width >= 120:
            row = y - 4
            panel_height = height - 4
            catalog_height = min(15, max(9, min(len(games) + 4, panel_height // 3 + 2)))
            in_catalog = 4 <= y < 2 + catalog_height - 1
            visible = catalog_height - 3
        else:
            row = y - 3
            list_width = max(28, width // 3) if state.modal == "update_planner" else max(48, width * 2 // 3)
            in_catalog = x <= list_width and row >= 0
            visible = height - 6
        catalog_active = state.modal == "games" or state.games_tab == 0
        if catalog_active and in_catalog and row >= 0 and games:
            start = list_start(state.selected_game, len(games), visible)
            index = start + row
            if 0 <= index < len(games):
                state.selected_game = index
                if double_click and state.modal == "update_planner":
                    state.games_tab = 1
        return

    if state.modal == "marketing":
        targets = promotion_targets(state)
        panel_height = height - 4
        catalog_height = min(15, max(9, min(len(targets) + 4, panel_height // 3 + 2)))
        row = y - 4
        if 4 <= y < 2 + catalog_height - 1:
            state.marketing_tab = 0
            visible = catalog_height - 3
            start = list_start(state.selected_promotion_target, len(targets), visible) if targets else 0
            index = start + row
            if 0 <= index < len(targets):
                state.selected_promotion_target = index
                if double_click:
                    state.marketing_tab = 1
        else:
            bottom_y = 2 + catalog_height
            summary_width = max(38, width * 36 // 100)
            option_row = y - (bottom_y + 2)
            if x > summary_width and 0 <= option_row < len(PROMOTIONS):
                state.marketing_tab = 1
                state.selected_promotion = option_row
                if double_click and targets:
                    buy_promotion(state, targets[state.selected_promotion_target][0], option_row)
        return

    if state.modal == "team":
        roster_width, _ = team_panel_widths(state, width)
        row = y - 4
        if row < 0:
            return
        if x <= roster_width:
            state.team_tab = 1
            visible_team = state.studio.team[: height - 7]
            if row < len(visible_team):
                employee = visible_team[row]
                if employee.founder:
                    state.selected_roster = -1
                else:
                    removable = [item for item in state.studio.team if not item.founder]
                    state.selected_roster = removable.index(employee)
        else:
            state.team_tab = 0
            if row < len(state.studio.applicants):
                state.selected_employee = row
                if double_click:
                    hire_candidate(state)
        return

    if state.modal == "new_game":
        if state.new_game_step == -1:
            choices = sequel_choices(state)
            visible = height - 8
            row = y - 5
            if row >= 0:
                start = list_start(state.selected_sequel_choice, len(choices), visible)
                index = start + row
                if 0 <= index < len(choices):
                    state.selected_sequel_choice = index
                    if double_click:
                        handle_new_game_key(state, 10)
            return
        top_height, genre_width, theme_width, _, storefront_height = new_game_panel_geometry(width, height)
        plan_x = genre_width + theme_width + 2
        if 4 <= y < 2 + top_height - 2:
            visible = top_height - 5
            row = y - 4
            if x < genre_width:
                state.new_game_step = 0
                index = list_start(state.selected_genre, len(GENRES), visible) + row
                state.selected_genre = min(index, len(GENRES) - 1)
            elif genre_width < x < plan_x:
                state.new_game_step = 1
                index = list_start(state.selected_topic, len(TOPICS), visible) + row
                state.selected_topic = min(index, len(TOPICS) - 1)
            elif x >= plan_x:
                state.new_game_step = 2
                if y == 3:
                    state.naming_game = True
                    state.draft_title = ""
                    return
                field = y - 4
                if 0 <= field < 7:
                    state.selected_focus = field
                    if double_click:
                        handle_new_game_key(state, 10)
            if state.new_game_step in (0, 1):
                state.sequel_game_id = None
                state.title_roll += 1
                refresh_draft_title(state)
        else:
            storefront_width = genre_width + theme_width + 1
            storefront_y = 2 + top_height
            row = y - (storefront_y + 2)
            if x < storefront_width and 0 <= row < storefront_height - 3:
                state.new_game_step = 3
                start = list_start(state.selected_channel, len(CHANNELS), storefront_height - 3)
                state.selected_channel = min(start + row, len(CHANNELS) - 1)
                if double_click:
                    handle_new_game_key(state, 10)


def handle_key(state: GameState, key: int, dimensions: tuple[int, int] | None = None) -> bool:
    if state.studio.closed:
        if key in (10, 13, curses.KEY_ENTER):
            delete_save_and_restart(state)
        return True
    if key == CTRL_S:
        save_state(state)
        return True
    if state.settings_open:
        if key in ESCAPE_KEYS:
            close_settings(state)
        elif key in (ord("q"), ord("Q")):
            return False
        elif key == curses.KEY_UP:
            state.selected_setting_action = (state.selected_setting_action - 1) % 3
        elif key == curses.KEY_DOWN:
            state.selected_setting_action = (state.selected_setting_action + 1) % 3
        elif key in (10, 13, curses.KEY_ENTER):
            return activate_settings_action(state)
        elif key == curses.KEY_MOUSE and dimensions is not None:
            return handle_mouse(state, dimensions) is not False
        return True
    if state.training_open:
        if key in ESCAPE_KEYS or key in (8, 127, curses.KEY_BACKSPACE):
            close_training(state)
        elif key == curses.KEY_UP:
            state.selected_training_skill = (state.selected_training_skill - 1) % len(EMPLOYEE_SKILLS)
        elif key == curses.KEY_DOWN:
            state.selected_training_skill = (state.selected_training_skill + 1) % len(EMPLOYEE_SKILLS)
        elif key in (10, 13, curses.KEY_ENTER):
            confirm_training(state)
        elif key == curses.KEY_MOUSE and dimensions is not None:
            return handle_mouse(state, dimensions) is not False
        return True
    project = state.studio.current_project
    if project and project.pending_decision is not None:
        if key in ESCAPE_KEYS:
            open_settings(state)
        elif key in (curses.KEY_UP, curses.KEY_DOWN):
            state.selected_project_decision = (state.selected_project_decision + 1) % 2
        elif key in (10, 13, curses.KEY_ENTER):
            resolve_project_decision(state, state.selected_project_decision)
        elif key == curses.KEY_MOUSE and dimensions is not None:
            return handle_mouse(state, dimensions) is not False
        return True
    if state.queue_cancellation:
        count = queue_cancellation_count(state)
        if key in (8, 127, curses.KEY_BACKSPACE):
            state.queue_cancellation = ""
        elif key in (curses.KEY_UP, curses.KEY_DOWN) and count:
            delta = -1 if key == curses.KEY_UP else 1
            state.selected_queue_cancellation = (state.selected_queue_cancellation + delta) % count
        elif key in (10, 13, curses.KEY_ENTER):
            cancel_selected_queue_item(state)
        elif key == curses.KEY_MOUSE and dimensions is not None:
            return handle_mouse(state, dimensions) is not False
        return True
    if key in ESCAPE_KEYS:
        open_settings(state)
        return True
    if key == 9:
        state.naming_game = False
        cycle_top_tab(state)
        return True
    if state.modal == "new_game" and state.naming_game:
        if key in (10, 13, curses.KEY_ENTER):
            if state.draft_title.strip():
                state.draft_title = state.draft_title.strip()
                state.naming_game = False
        elif key in (8, 127, curses.KEY_BACKSPACE):
            if state.draft_title:
                state.draft_title = state.draft_title[:-1]
            else:
                state.naming_game = False
        elif 32 <= key <= 126 and len(state.draft_title) < 48:
            state.draft_title += chr(key)
        return True
    for index, (_, shortcut, _) in enumerate(TOP_TABS):
        if key in (ord(shortcut.lower()), ord(shortcut)):
            activate_top_tab(state, index)
            if shortcut == "T":
                state.team_tab = 1
            return True
    if key in (ord("q"), ord("Q")):
        return False
    if key == ord(" "):
        toggle_pause(state)
        return True
    if key in (ord("<"), curses.KEY_LEFT, ord(">"), curses.KEY_RIGHT):
        left_action, right_action = horizontal_actions(state)
        perform_footer_action(state, left_action if key in (ord("<"), curses.KEY_LEFT) else right_action)
        return True
    if key == curses.KEY_MOUSE and dimensions is not None:
        return handle_mouse(state, dimensions) is not False
    if state.modal == "new_game":
        handle_new_game_key(state, key)
    elif state.modal == "team":
        handle_team_key(state, key)
    elif state.modal == "contracts":
        if key in (8, 127, curses.KEY_BACKSPACE):
            state.modal = "main"
        elif key in (ord("c"), ord("C")):
            toggle_auto_contracts(state)
        elif key == curses.KEY_UP and state.studio.contract_offers:
            state.selected_contract = (state.selected_contract - 1) % len(state.studio.contract_offers)
        elif key == curses.KEY_DOWN and state.studio.contract_offers:
            state.selected_contract = (state.selected_contract + 1) % len(state.studio.contract_offers)
        elif key in (10, 13, curses.KEY_ENTER):
            accept_contract_offer(state)
    elif state.modal == "games":
        games = live_games(state)
        project = state.studio.current_project
        if project and project.pending_decision is not None and key in (curses.KEY_UP, curses.KEY_DOWN):
            state.selected_project_decision = (state.selected_project_decision + 1) % 2
        elif project and project.pending_decision is not None and key in (10, 13, curses.KEY_ENTER):
            resolve_project_decision(state, state.selected_project_decision)
        elif key in (8, 127, curses.KEY_BACKSPACE):
            state.modal = "main"
        elif key in (ord("u"), ord("U")) and games:
            state.modal = "update_planner"
            state.games_tab = 0
        elif key in (ord("n"), ord("N")):
            open_new_game(state)
        elif key == curses.KEY_UP and games:
            state.selected_game = (state.selected_game - 1) % len(games)
        elif key == curses.KEY_DOWN and games:
            state.selected_game = (state.selected_game + 1) % len(games)
        elif key in (ord("p"), ord("P")):
            perform_footer_action(state, "game_marketing")
    elif state.modal == "update_planner":
        games = live_games(state)
        if state.queue_cancellation == "update":
            count = queue_cancellation_count(state)
            if key in (8, 127, curses.KEY_BACKSPACE):
                state.queue_cancellation = ""
            elif key in (curses.KEY_UP, curses.KEY_DOWN) and count:
                delta = -1 if key == curses.KEY_UP else 1
                state.selected_queue_cancellation = (state.selected_queue_cancellation + delta) % count
            elif key in (10, 13, curses.KEY_ENTER):
                cancel_selected_queue_item(state)
        elif key in (ord("c"), ord("C")):
            enter_queue_cancellation(state)
        elif key in (8, 127, curses.KEY_BACKSPACE):
            if state.games_tab > 0:
                state.games_tab -= 1
            else:
                state.modal = "games"
        elif state.games_tab == 0:
            if key == curses.KEY_UP and games:
                state.selected_game = (state.selected_game - 1) % len(games)
            elif key == curses.KEY_DOWN and games:
                state.selected_game = (state.selected_game + 1) % len(games)
            elif key in (10, 13, curses.KEY_ENTER) and games:
                state.games_tab = 1
        elif state.games_tab == 1:
            if key in (curses.KEY_UP, curses.KEY_DOWN) and games:
                cycle_game_update_size(state, games[state.selected_game].game_id, -1 if key == curses.KEY_UP else 1)
            elif key in (10, 13, curses.KEY_ENTER) and games:
                state.games_tab = 2
        elif state.games_tab == 2:
            if key in (curses.KEY_UP, curses.KEY_DOWN) and games:
                cycle_game_update_focus(state, games[state.selected_game].game_id, -1 if key == curses.KEY_UP else 1)
            elif key in (10, 13, curses.KEY_ENTER) and games:
                queue_game_update(state, games[state.selected_game].game_id)
    elif state.modal == "marketing":
        targets = promotion_targets(state)
        if state.queue_cancellation == "promotion":
            count = queue_cancellation_count(state)
            if key in (8, 127, curses.KEY_BACKSPACE):
                state.queue_cancellation = ""
            elif key in (curses.KEY_UP, curses.KEY_DOWN) and count:
                delta = -1 if key == curses.KEY_UP else 1
                state.selected_queue_cancellation = (state.selected_queue_cancellation + delta) % count
            elif key in (10, 13, curses.KEY_ENTER):
                cancel_selected_queue_item(state)
        elif key in (ord("c"), ord("C")):
            enter_queue_cancellation(state)
        elif key in (8, 127, curses.KEY_BACKSPACE):
            if state.marketing_tab == 1:
                state.marketing_tab = 0
            else:
                state.modal = "games"
        elif key in (curses.KEY_UP, curses.KEY_DOWN):
            delta = -1 if key == curses.KEY_UP else 1
            if state.marketing_tab == 0 and targets:
                state.selected_promotion_target = (state.selected_promotion_target + delta) % len(targets)
            elif state.marketing_tab == 1:
                state.selected_promotion = (state.selected_promotion + delta) % len(PROMOTIONS)
        elif key in (10, 13, curses.KEY_ENTER) and state.marketing_tab == 0:
            state.marketing_tab = 1
        elif key in (10, 13, curses.KEY_ENTER) and targets:
            buy_promotion(state, targets[state.selected_promotion_target][0], state.selected_promotion)
    elif state.modal == "upgrades":
        if key in (8, 127, curses.KEY_BACKSPACE):
            state.modal = "main"
        elif key == curses.KEY_UP:
            state.selected_upgrade = (state.selected_upgrade - 1) % len(UPGRADES)
        elif key == curses.KEY_DOWN:
            state.selected_upgrade = (state.selected_upgrade + 1) % len(UPGRADES)
        elif key in (10, 13, curses.KEY_ENTER):
            buy_upgrade(state)
    elif state.modal == "analysis":
        if key in (8, 127, curses.KEY_BACKSPACE):
            state.modal = "main"
        elif key in (curses.KEY_UP, curses.KEY_DOWN) and state.analysis_view in (2, 3):
            count = len(GENRES) if state.analysis_view == 2 else len(state.studio.catalog)
            if count:
                state.selected_stat = (state.selected_stat + (-1 if key == curses.KEY_UP else 1)) % count
    elif state.modal == "settings":
        if key in (8, 127, curses.KEY_BACKSPACE):
            state.modal = "main"
    elif state.modal == "main":
        if key in (ord("n"), ord("N")):
            open_new_game(state)
        elif key in (ord("u"), ord("U")):
            state.modal = "upgrades"
        elif key in (ord("c"), ord("C")):
            toggle_auto_contracts(state)
        elif key in (ord("j"), ord("J")):
            state.modal = "contracts"
    return True


def run(screen: curses.window, load_save: bool, save_path: str) -> None:
    curses.curs_set(0)
    curses.raw()
    curses.set_escdelay(25)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_GREEN, -1)
    curses.init_pair(5, curses.COLOR_RED, -1)
    screen.nodelay(True)
    screen.keypad(True)
    try:
        curses.mouseinterval(100)
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
    except curses.error:
        pass
    if load_save:
        try:
            state = load_game(save_path)
            state.log(f"Loaded studio from {save_path}.")
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            state = GameState(save_path=save_path)
            state.log(f"Could not load save: {error}. Started a new studio.")
    else:
        state = GameState(save_path=save_path)
    previous_time = time.monotonic()
    running = True
    while running:
        now = time.monotonic()
        weeks = state.clock.update((now - previous_time) * TIME_SPEEDS[state.time_speed_index])
        previous_time = now
        advance_game(state, weeks)
        draw_screen(screen, state)
        screen.refresh()
        key = screen.getch()
        while key != -1:
            running = handle_key(state, key, screen.getmaxyx())
            if not running:
                break
            if key in NAVIGATION_KEYS:
                curses.flushinp()
                break
            key = screen.getch()
        time.sleep(0.03)


def simulate(weeks: int, load_save: bool, save_path: str) -> None:
    state = load_game(save_path) if load_save else GameState(save_path=save_path)
    for _ in range(weeks):
        state.clock.current_date += timedelta(days=7)
        state.clock.week += 1
        advance_game(state, 1)
    print(f"Date: {state.clock.current_date:%d %b %Y}")
    print(f"Cash: {money(state.studio.cash)} | Runway: {runway_months(state.studio):.1f} months")
    print(f"Team: {len(state.studio.team)} | Released: {state.studio.released_games} | Followers: {state.studio.followers:,}")
    for message in state.logs[:8]:
        print(f"- {message}")


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the realistic indie studio simulation.")
    parser.add_argument("save_path", nargs="?", help="save file to load (for example: gamedev_save.json)")
    parser.add_argument("--load", action="store_true", help="load a studio; optionally put its path after this flag")
    parser.add_argument("--save-file", dest="save_file_option", help=f"explicit save path (default: {DEFAULT_SAVE_FILE})")
    parser.add_argument("--simulate", type=int, metavar="WEEKS", help="advance without curses and print a summary")
    args = parser.parse_args(arguments)
    if args.save_path and args.save_file_option:
        parser.error("choose either a positional save path or --save-file, not both")
    positional_path = args.save_path
    args.save_path = positional_path or args.save_file_option or DEFAULT_SAVE_FILE
    args.load = args.load or positional_path is not None
    return args


def main() -> None:
    args = parse_args()
    if args.load and not Path(args.save_path).is_file():
        available = ", ".join(path.name for path in sorted(Path.cwd().glob("*.json"))) or "none"
        raise SystemExit(f"Save file not found: {args.save_path}\nAvailable JSON saves: {available}")
    if args.simulate is not None:
        simulate(max(0, args.simulate), args.load, args.save_path)
    else:
        curses.wrapper(run, args.load, args.save_path)


if __name__ == "__main__":
    main()
