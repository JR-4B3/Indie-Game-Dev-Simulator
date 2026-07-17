from __future__ import annotations

import argparse
import curses
import json
import time
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from game_data import GENRES, GOOD_MATCHES, TOPICS
from simulation import (
    CHANNELS,
    MARKETING,
    PROMOTIONS,
    SCOPES,
    SKILLS,
    TIME_LABELS,
    TIME_SPEEDS,
    UPDATE_FOCUSES,
    UPDATE_SIZES,
    UPGRADES,
    GameState,
    accept_contract_offer,
    adjust_focus,
    advance_game,
    applicant_pool_size,
    buy_upgrade,
    buy_promotion,
    cycle_game_update_focus,
    cycle_game_update_size,
    dismiss_employee,
    expense_breakdown,
    game_by_id,
    game_profit,
    game_total_cost,
    estimated_contract_weeks,
    estimated_update_weeks,
    hire_candidate,
    load_game,
    monthly_fixed_cost,
    prepare_sequel,
    projected_weekly_output,
    recommended_team_size,
    refresh_draft_title,
    revenue_breakdown,
    runway_months,
    save_game,
    sale_for_game,
    start_project,
    toggle_auto_contracts,
    toggle_game_updates,
)


DEFAULT_SAVE_FILE = "gamedev_save.json"
NAVIGATION_KEYS = {curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT, curses.KEY_RIGHT}
CTRL_S = 19


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:.2f}m"
    if value >= 100_000:
        return f"{sign}${value / 1_000:.0f}k"
    return f"{sign}${value:,.0f}"


def update_status(game) -> str:
    status = "ON" if game.auto_updates else "OFF"
    return f"Updates {status} {game.update_progress:.0f}% #{game.updates_released}"


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
    studio = state.studio
    title = "INDIE STUDIO GAME DEV SIM "
    year = (state.clock.week - 1) // 52 + 1
    week = (state.clock.week - 1) % 52 + 1
    speed = "CLOSED" if studio.closed else TIME_LABELS[state.time_speed_index]
    if width >= 150:
        bar_width = 34
        date_text = f"{state.clock.current_date:%d %b %Y}  Y {year}  W {week}  {speed:<8}"
    elif width >= 100:
        bar_width = 28
        date_text = f"{state.clock.current_date:%d %b %y} Y {year} W {week} {speed:<8}"
    else:
        bar_width = 24
        date_text = f"{state.clock.current_date:%d%b%y} Y{year} W{week} {speed:<8}"
    date_block = f" {date_text:^{bar_width + 2}}"
    add_text(screen, 0, 0, (date_block + " " * max(1, width - len(date_block) - len(title)) + title).ljust(width), width, curses.color_pair(1) | curses.A_BOLD)
    filled = round(bar_width * state.clock.progress)
    week_progress = "█" * filled + "░" * (bar_width - filled)
    if width >= 150:
        line = f" [{week_progress}] | Games {studio.released_games} | Team {len(studio.team)} | Fans {studio.followers:,} | Game reputation {studio.reputation:.1f} | Contractor reputation {studio.contractor_reputation:.1f}"
    elif width >= 100:
        line = f" [{week_progress}] | Games {studio.released_games} | Team {len(studio.team)} | Fans {studio.followers:,} | GRep {studio.reputation:.1f} | CRep {studio.contractor_reputation:.1f}"
    else:
        line = f" [{week_progress}] | G {studio.released_games} | T {len(studio.team)} | F {studio.followers:,} | GR {studio.reputation:.1f} | CR {studio.contractor_reputation:.1f}"
    add_text(screen, 1, 0, line.ljust(width), width, curses.color_pair(4))


def draw_live_operations(panel: curses.window, state: GameState, panel_width: int, start_row: int) -> None:
    studio = state.studio
    add_text(panel, start_row, 2, f"Continuous updates {sum(game.auto_updates for game in studio.catalog)} | Active promotions {len(studio.active_promotions)}", panel_width - 4)
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
    finance = screen.derwin(finance_height, left_width, 3, 0)
    command_height = 16 if width >= 120 else 8
    project_panel = screen.derwin(command_height, right_width, 3, left_width + 1)
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
        add_text(project_panel, 2, 2, "N  build a realistic project plan", right_width - 4)
        add_text(project_panel, 3, 2, f"Game Catalogue {len(studio.catalog)} | Promotions {len(studio.active_promotions)} | Active update plans {sum(game.auto_updates for game in studio.catalog)}", right_width - 4)
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
            platform_text += f" | Hype {project.hype:.0f} | Defects {project.defects:.1f}"
        add_text(project_panel, 4, 2, platform_text, right_width - 4)
        add_text(project_panel, 5, 2, f"Tracked cost {money(project.production_cost + project.labor_cost + project.marketing_cost)} | Marketing {money(project.marketing_cost)}", right_width - 4)
    if width >= 120:
        add_text(project_panel, 7, 2, "OPERATIONS", right_width - 4, curses.A_BOLD)
        draw_live_operations(project_panel, state, right_width, 8)
        add_text(project_panel, 11, 2, "CONTRACTS", right_width - 4, curses.A_BOLD)
        draw_contract_status(project_panel, state, right_width, 12)
    return 11


def draw_main_content(screen: curses.window, state: GameState, width: int, height: int, y: int) -> None:
    studio = state.studio
    journal_height = 7 if height >= 32 else 4
    journal_y = height - journal_height - 1

    left_width = width // 2
    right_width = width - left_width - 1
    if width >= 120:
        team_y = 19
        team_height = max(0, journal_y - team_y)
        catalogue_y = 19
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
                portfolio_title_width = max(18, portfolio_inner_width - 57)
                portfolio_header = f"{'GAME':<{portfolio_title_width}} {'RATING':>6} {'SALES':>7} {'MONTHLY':>9} {'REVENUE':>11} {'PROFIT':>11} {'UPDATES':>7}"
            else:
                portfolio_title_width = max(14, portfolio_inner_width - 27)
                portfolio_header = f"{'GAME':<{portfolio_title_width}} {'RATE':>4} {'SALES':>6} {'MONTHLY':>8} {'UPD':>5}"
            add_text(portfolio, 1, 2, portfolio_header, portfolio_inner_width, curses.A_BOLD)
            for row, game in enumerate(live_games(state)[: catalogue_height - 3], 2):
                sale = sale_for_game(studio, game.game_id)
                if catalogue_expanded:
                    profit = money(game_profit(game)) if game.cost_history_complete else "n/a"
                    text = f"{game.title[:portfolio_title_width]:<{portfolio_title_width}} {rating_text(game):>6} {(sale.weekly_units if sale else 0):>7,} {game.monthly_players:>9,} {money(game.net_revenue):>11} {profit:>11} {('#' + str(game.updates_released)):>7}"
                else:
                    text = f"{game.title[:portfolio_title_width]:<{portfolio_title_width}} {rating_text(game):>4} {(sale.weekly_units if sale else 0):>6,} {game.monthly_players:>8,} {('#' + str(game.updates_released)):>5}"
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
                add_text(portfolio, row, 2, f"{game.title}: R{rating_text(game)} {(sale.weekly_units if sale else 0):,}/w {game.monthly_players:,} monthly", right_width - 4)
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
    panel = screen.derwin(height - 4, width, 3, 0)
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
            text = f"SEQUEL         {choice.title[:26]:<26} {choice.genre[:13]:<13} rating {rating_text(choice):>3} | hype {choice.hype:.0f} | {choice.monthly_players:,} monthly players | {update_status(choice)}"
        add_text(panel, row, 2, f"{'> ' if selected else '  '}{text}", width - 4, curses.color_pair(3) | curses.A_BOLD if selected else 0)
    tracked = len(state.studio.catalog)
    missing = max(0, state.studio.released_games - tracked)
    if missing:
        add_text(panel, height - 3, 2, f"{missing} older release(s) lack recoverable title data and cannot be selected as sequels.", width - 4, curses.color_pair(5))
    add_text(panel, height - 2, 2, "Enter or double-click to continue. Mouse wheel scrolls the release list.", width - 4, curses.color_pair(4))


def draw_new_game(screen: curses.window, state: GameState, width: int, height: int) -> None:
    if state.new_game_step == -1:
        draw_project_type(screen, state, width, height)
        return
    plan_height = 10
    picker_height = max(7, height - 4 - plan_height)
    genre_width = max(20, width // 4)
    topic_width = max(24, width // 3)
    channel_width = width - genre_width - topic_width - 2
    genre = screen.derwin(picker_height, genre_width, 3, 0)
    topic = screen.derwin(picker_height, topic_width, 3, genre_width + 1)
    channel = screen.derwin(picker_height, channel_width, 3, genre_width + topic_width + 2)
    draw_box(genre, "1 Genre")
    draw_box(topic, "2 Theme")
    draw_box(channel, "3 Storefront")
    draw_list(genre, list(GENRES), state.selected_genre, state.new_game_step == 0)
    draw_list(topic, list(TOPICS), state.selected_topic, state.new_game_step == 1)
    channel_items = [f"{item['name']} | {item['cut']:.0%} cut | {money(item['fee'])}" for item in CHANNELS]
    draw_list(channel, channel_items, state.selected_channel, state.new_game_step == 2)

    plan = screen.derwin(plan_height, width, 3 + picker_height, 0)
    draw_box(plan, "4 Production Plan")
    scope = SCOPES[state.selected_scope]
    marketing = MARKETING[state.selected_marketing]
    channel_data = CHANNELS[state.selected_channel]
    title_mode = "TYPE NAME, ENTER TO ACCEPT" if state.naming_game else "T edit / R randomize"
    add_text(plan, 1, 2, f"Title      {state.draft_title}_  [{title_mode}]" if state.naming_game else f"Title      {state.draft_title}  [{title_mode}]", width - 4, curses.color_pair(3) | curses.A_BOLD)
    fields = [
        f"Scope      {scope['name']} | {scope['work']:,} work | {money(scope['setup'])} setup | {money(scope['price'])} price",
        f"Marketing  {marketing['name']} | {money(marketing['cost'])} | starting hype {5 + marketing['boost'] / 25:.0f}",
    ] + [f"Focus      {SKILLS[index]} {state.focus[index]}%" for index in range(4)]
    for row, text in enumerate(fields, 2):
        selected = state.new_game_step == 3 and state.selected_focus == row - 2
        add_text(plan, row, 2, ("> " if selected else "  ") + text, width - 4, curses.color_pair(3) | curses.A_BOLD if selected else 0)
    cost = scope["setup"] + marketing["cost"] + channel_data["fee"]
    weeks = round(scope["work"] / projected_weekly_output(state.studio, state.focus))
    combo = "marketable" if TOPICS[state.selected_topic] in GOOD_MATCHES[GENRES[state.selected_genre]] else "hard to market"
    summary = f"Cash due now {money(cost)} | team estimate {max(4, weeks)} weeks | {combo} genre/theme combination"
    sequel = next((game for game in state.studio.catalog if game.game_id == state.sequel_game_id), None)
    if sequel:
        score = "score n/a" if sequel.release_date == "Historical" else f"{sequel.score}/100"
        summary += f" | sequel to {sequel.title} ({score})"
    add_text(plan, 8, 2, summary, width - 4, curses.color_pair(4) if combo == "marketable" else curses.color_pair(5))


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
    roster = screen.derwin(panel_height, roster_width, 3, 0)
    applicants = screen.derwin(panel_height, applicant_width, 3, roster_width + 1)
    target = recommended_team_size(state.studio)
    draw_box(roster, f"Team | {len(state.studio.team)}/{target} suggested")
    next_pool = applicant_pool_size(state.studio)
    draw_box(applicants, f"Applicants | {len(state.studio.applicants)} available | Next pool {next_pool}")

    roster_expanded = roster_width >= 112
    applicant_expanded = applicant_width >= 100
    if roster_expanded:
        roster_inner = roster_width - 4
        flexible_width = roster_inner - 58
        name_width = min(20, max(16, flexible_width // 3))
        trait_width = min(18, max(14, flexible_width - name_width - 20))
        role_width = flexible_width - name_width - trait_width
        roster_header = f"  {'NAME':<{name_width}} {'ROLE':<{role_width}} {'DES':>3} {'ART':>3} {'AUD':>3} {'CODE':>4} {'MORALE':>6} {'FATIGUE':>7} {'SALARY/YR':>11} {'COST/MO':>9} {'PERSONALITY':<{trait_width}}"
    else:
        roster_header = f"  {'NAME':<14} {'DES':>3} {'ART':>3} {'AUD':>3} {'CODE':>4} {'MOR':>3} {'FAT':>3} {'PERSONALITY':<12}"
    add_text(roster, 1, 2, roster_header, roster_width - 4, curses.A_BOLD)

    removable_index = 0
    for row, employee in enumerate(state.studio.team[: panel_height - 3], 2):
        is_selected = state.team_tab == 1 and not employee.founder and removable_index == state.selected_roster
        if not employee.founder:
            removable_index += 1
        marker = ">" if is_selected else " "
        salary = "owner draw" if employee.founder else f"${employee.annual_salary:,}"
        if roster_expanded:
            line = f"{marker} {employee.name[:name_width]:<{name_width}} {employee.role[:role_width]:<{role_width}} {employee.design:>3} {employee.art:>3} {employee.audio:>3} {employee.code:>4} {employee.morale:>6.0f} {employee.fatigue:>7.0f} {salary:>11} {money(employee.monthly_salary):>9} {employee.trait[:trait_width]:<{trait_width}}"
        else:
            line = f"{marker} {employee.name[:14]:<14} {employee.design:>3} {employee.art:>3} {employee.audio:>3} {employee.code:>4} {employee.morale:>3.0f} {employee.fatigue:>3.0f} {employee.trait[:12]:<12}"
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
        for skill_index, skill_name in enumerate(SKILLS):
            average_skill = sum(employee.skills[skill_index] for employee in team) / len(team)
            lead = max(team, key=lambda employee: employee.skills[skill_index])
            overview.append((f"{skill_name:<8} [{meter(average_skill, 100, 18)}] avg {average_skill:>4.0f} | Lead {lead.name} {lead.skills[skill_index]}", 0))

        removable = [employee for employee in team if not employee.founder]
        selected_member = removable[min(state.selected_roster, len(removable) - 1)] if removable else team[0]
        overview.extend(
            [
                ("SELECTED TEAM MEMBER", curses.A_BOLD),
                (f"{selected_member.name} | {selected_member.role} | {selected_member.trait}", 0),
                (f"Skills  Design {selected_member.design} | Art {selected_member.art} | Audio {selected_member.audio} | Code {selected_member.code}", 0),
                (f"Wellbeing  Morale {selected_member.morale:.0f}/100 | Fatigue {selected_member.fatigue:.0f}/100 | Employed {selected_member.weeks_employed}w", 0),
                (f"Compensation  {money(selected_member.annual_salary)}/year | {money(selected_member.monthly_salary)}/month", 0),
            ]
        )
        for row, (text, attr) in enumerate(overview[: panel_height - summary_row - 1], summary_row):
            add_text(roster, row, 2, text, roster_width - 4, attr)

    if applicant_expanded:
        applicant_header = f"  {'NAME':<16} {'ROLE':<22} {'DES':>3} {'ART':>3} {'AUD':>3} {'CODE':>4} {'SALARY/YR':>11} {'PERSONALITY':<14}"
    else:
        applicant_header = f"  {'NAME':<14} {'ROLE':<17} {'DES':>3} {'ART':>3} {'AUD':>3} {'CODE':>4} {'SALARY':>9} {'TRAIT':<10}"
    add_text(applicants, 1, 2, applicant_header, applicant_width - 4, curses.A_BOLD)
    for row, employee in enumerate(state.studio.applicants[: panel_height - 3], 2):
        selected = state.team_tab == 0 and row - 2 == state.selected_employee
        marker = ">" if selected else " "
        if applicant_expanded:
            text = f"{marker} {employee.name[:16]:<16} {employee.role[:22]:<22} {employee.design:>3} {employee.art:>3} {employee.audio:>3} {employee.code:>4} {money(employee.annual_salary):>11} {employee.trait[:14]:<14}"
        else:
            text = f"{marker} {employee.name[:14]:<14} {employee.role[:17]:<17} {employee.design:>3} {employee.art:>3} {employee.audio:>3} {employee.code:>4} {money(employee.annual_salary):>9} {employee.trait[:10]:<10}"
        add_text(applicants, row, 2, text, applicant_width - 4, curses.color_pair(3) | curses.A_BOLD if selected else 0)


def draw_contract_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel_height = height - 4
    board_width = max(46, width * 2 // 3)
    detail_width = width - board_width - 1
    board = screen.derwin(panel_height, board_width, 3, 0)
    detail = screen.derwin(panel_height, detail_width, 3, board_width + 1)
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


def draw_games_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel_height = height - 4
    games = live_games(state)
    game_count = f"{len(games)} {'game' if len(games) == 1 else 'games'}"
    if width < 120:
        list_width = max(48, width * 2 // 3)
        detail_width = width - list_width - 1
        games_panel = screen.derwin(panel_height, list_width, 3, 0)
        detail = screen.derwin(panel_height, detail_width, 3, list_width + 1)
        draw_box(games_panel, f"Game Catalogue | {game_count}")
        draw_box(detail, "Commercial Performance")
        if not games:
            add_text(games_panel, 1, 2, "No releases yet.", list_width - 4)
            return
        state.selected_game = min(state.selected_game, len(games) - 1)
        for row, game in enumerate(games[: panel_height - 2], 1):
            sale = sale_for_game(state.studio, game.game_id)
            selected = row - 1 == state.selected_game
            add_text(games_panel, row, 2, f"{'> ' if selected else '  '}{game.title[:20]:<20} R{rating_text(game):>3} {(sale.weekly_units if sale else 0):>5,}/w {game.monthly_players:>6,} monthly", list_width - 4, curses.color_pair(3) | curses.A_BOLD if selected else 0)
        game = games[state.selected_game]
        sale = sale_for_game(state.studio, game.game_id)
        add_text(detail, 1, 2, game.title, detail_width - 4, curses.A_BOLD)
        add_text(detail, 2, 2, f"Rating {rating_text(game)}/100", detail_width - 4)
        add_text(detail, 3, 2, f"Hype {game.hype:.0f}/200", detail_width - 4)
        add_text(detail, 4, 2, f"Monthly players {game.monthly_players:,}", detail_width - 4)
        add_text(detail, 5, 2, f"Sales {(sale.weekly_units if sale else 0):,}/week", detail_width - 4)
        add_text(detail, 7, 2, update_status(game), detail_width - 4)
        add_text(detail, 8, 2, f"{game.update_size} / {game.update_focus}", detail_width - 4)
        add_text(detail, 9, 2, f"ETA {estimated_update_weeks(state.studio, game)}w", detail_width - 4)
        return

    catalog_height = min(15, max(9, min(len(games) + 4, panel_height // 3 + 2)))
    games_panel = screen.derwin(catalog_height, width, 3, 0)
    draw_box(games_panel, f"Game Catalogue | {game_count}")
    if not games:
        add_text(games_panel, 1, 2, "No releases yet. Start a project from the main dashboard.", width - 4)
        return
    state.selected_game = min(state.selected_game, len(games) - 1)
    visible = catalog_height - 3
    start = list_start(state.selected_game, len(games), visible)
    very_wide = width >= 170
    if very_wide:
        genre_width = 28
        title_width = max(30, min(50, width - 4 - 95 - genre_width))
        header = f"  {'TITLE':<{title_width}} {'GENRE':<{genre_width}} {'RATING':>6} {'HYPE':>6} {'SALES/W':>9} {'MONTHLY PLAYERS':>15} {'LIFETIME UNITS':>14} {'NET REVENUE':>12} {'PROFIT':>12} {'UPDATES':>10}"
    else:
        header = f"  {'TITLE':<24} {'RATING':>6} {'HYPE':>6} {'SALES/W':>9} {'MONTHLY':>10} {'UNITS':>10} {'PROFIT':>11} {'UPDATES':>9}"
    add_text(games_panel, 1, 2, header, width - 4, curses.A_BOLD)
    for row, game in enumerate(games[start : start + visible], 2):
        index = start + row - 2
        sale = sale_for_game(state.studio, game.game_id)
        weekly = sale.weekly_units if sale else 0
        profit = money(game_profit(game)) if game.cost_history_complete else "n/a"
        if very_wide:
            text = f"{'> ' if index == state.selected_game else '  '}{game.title[:title_width]:<{title_width}} {game.genre[:genre_width]:<{genre_width}} {rating_text(game):>6} {game.hype:>6.0f} {weekly:>9,} {game.monthly_players:>15,} {game.units_sold:>14,} {money(game.net_revenue):>12} {profit:>12} {('#' + str(game.updates_released)):>10}"
        else:
            text = f"{'> ' if index == state.selected_game else '  '}{game.title[:24]:<24} {rating_text(game):>6} {game.hype:>6.0f} {weekly:>9,} {game.monthly_players:>10,} {game.units_sold:>10,} {profit:>11} {('#' + str(game.updates_released)):>9}"
        if index == state.selected_game:
            row_attr = curses.color_pair(3) | curses.A_BOLD
        else:
            row_attr = 0
        add_text(games_panel, row, 2, text, width - 4, row_attr)

    game = games[state.selected_game]
    sale = sale_for_game(state.studio, game.game_id)
    bottom_y = 3 + catalog_height
    bottom_height = panel_height - catalog_height
    detail_height = bottom_height if bottom_height < 24 else 20
    summary_height = bottom_height - detail_height
    first_width = width // 3
    second_width = width // 3
    third_width = width - first_width - second_width - 2
    commercial = screen.derwin(detail_height, first_width, bottom_y, 0)
    live_ops = screen.derwin(detail_height, second_width, bottom_y, first_width + 1)
    strategy = screen.derwin(detail_height, third_width, bottom_y, first_width + second_width + 2)
    draw_box(commercial, "Commercial Performance")
    draw_box(live_ops, "Live Operations")
    draw_box(strategy, "Promotion Planning")

    rating_attr = curses.color_pair(4) if game.score >= 70 else curses.color_pair(5) if game.score < 45 else 0
    size = next((item for item in UPDATE_SIZES if item["name"] == game.update_size), UPDATE_SIZES[0])
    focus = next((item for item in UPDATE_FOCUSES if item["name"] == game.update_focus), UPDATE_FOCUSES[0])
    if detail_height < 20:
        add_text(commercial, 1, 2, f"Rating {rating_text(game)}/100 | Hype {game.hype:.0f}", first_width - 4, rating_attr)
        add_text(commercial, 2, 2, f"Sales {(sale.weekly_units if sale else 0):,}/w | Monthly {game.monthly_players:,}", first_width - 4)
        add_text(commercial, 3, 2, f"Revenue {money(game.net_revenue)} | Profit {money(game_profit(game)) if game.cost_history_complete else 'n/a'}", first_width - 4)
        add_text(live_ops, 1, 2, f"Updates {'ON' if game.auto_updates else 'OFF'} | #{game.updates_released}", second_width - 4)
        add_text(live_ops, 2, 2, f"{game.update_size} / {game.update_focus}", second_width - 4)
        add_text(live_ops, 3, 2, f"{game.update_progress:.0f}% | ETA {estimated_update_weeks(state.studio, game)}w | {money(size['cost'])}", second_width - 4)
        recommendation, recommendation_color = game_recommendation(game)
        add_text(strategy, 1, 2, "Recommended", third_width - 4, curses.A_BOLD)
        compact_recommendation_attr = curses.color_pair(recommendation_color) if recommendation_color in (4, 5) else 0
        add_text(strategy, 2, 2, recommendation, third_width - 4, compact_recommendation_attr)
        return
    add_text(commercial, 1, 2, game.title, first_width - 4, curses.A_BOLD)
    add_text(commercial, 2, 2, f"{game.genre} / {game.topic} | {game.channel}", first_width - 4)
    add_text(commercial, 3, 2, "MARKET SIGNALS", first_width - 4, curses.A_BOLD)
    add_text(commercial, 4, 2, f"Rating [{meter(game.score, 100, 18)}] {rating_text(game)}/100", first_width - 4, rating_attr)
    add_text(commercial, 5, 2, f"Hype   [{meter(game.hype, 200, 18)}] {game.hype:.0f}/200", first_width - 4)
    add_text(commercial, 6, 2, "AUDIENCE & SALES", first_width - 4, curses.A_BOLD)
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
    remaining_work = size["work"] * max(0, 1 - game.update_progress / 100)
    update_load = min(0.55, sum(0.12 for item in state.studio.catalog if item.auto_updates))
    update_attr = curses.color_pair(4) if game.auto_updates else curses.color_pair(5)
    add_text(live_ops, 1, 2, f"STATUS  {'ACTIVE' if game.auto_updates else 'PAUSED'}", second_width - 4, update_attr | curses.A_BOLD)
    add_text(live_ops, 2, 2, "CURRENT PLAN", second_width - 4, curses.A_BOLD)
    add_text(live_ops, 3, 2, f"Focus       {game.update_focus} ({focus['skill']} skill)", second_width - 4)
    add_text(live_ops, 4, 2, f"Scope       {game.update_size} | {size['work']:,} total work", second_width - 4)
    add_text(live_ops, 5, 2, f"Remaining   {remaining_work:,.0f} work | ETA {estimated_update_weeks(state.studio, game)}w", second_width - 4)
    add_text(live_ops, 6, 2, f"Ship budget {money(size['cost'])} | Team load {update_load:.0%}", second_width - 4)
    add_text(live_ops, 7, 2, f"Forecast    +{expected_hype:.1f} hype | ~{expected_players:,} returning players", second_width - 4)
    add_text(live_ops, 9, 2, f"[{meter(game.update_progress, 100, 24)}] {game.update_progress:.0f}%", second_width - 4, curses.color_pair(4) if game.auto_updates else 0)
    add_text(live_ops, 10, 2, f"Release history  {game.updates_released} updates shipped", second_width - 4)
    add_text(live_ops, 12, 2, "CONTROLS", second_width - 4, curses.A_BOLD)
    add_text(live_ops, 13, 2, "U  Start or pause this update plan", second_width - 4)
    add_text(live_ops, 14, 2, "F  Cycle focus; progress resets", second_width - 4)
    add_text(live_ops, 15, 2, "Z  Cycle scope; progress resets", second_width - 4)
    add_text(live_ops, 16, 2, "M  Open promotion planning", second_width - 4)
    add_text(live_ops, 17, 2, "Mouse  Double-click game row to toggle", second_width - 4)

    recommendation, recommendation_color = game_recommendation(game)
    promotions = [promotion for promotion in state.studio.active_promotions if promotion.game_id == game.game_id]
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
    campaign_load = min(0.45, sum(item.team_share for item in state.studio.active_promotions))
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
    add_text(strategy, 14, 2, f"This game {len(promotions)} active | Studio {len(state.studio.active_promotions)} | Team load {campaign_load:.0%}", third_width - 4, curses.color_pair(5) if campaign_load >= 0.30 else 0)
    add_text(strategy, 15, 2, f"Best unlocked  {best_promotion['name']} | +{best_promotion['hype']} hype", third_width - 4)
    add_text(strategy, 16, 2, f"Budget {money(best_promotion['cost'])} | {'FUNDED' if can_afford else 'CASH BUFFER TOO LOW'}", third_width - 4, curses.color_pair(4) if can_afford else curses.color_pair(5))
    active_names = ", ".join(f"{item.name} ({item.weeks_left}w)" for item in promotions) or "No promotion currently running"
    add_text(strategy, 17, 2, active_names, third_width - 4)
    add_text(strategy, 18, 2, "M  Open promotion planning", third_width - 4)

    if summary_height >= 5:
        summary_y = bottom_y + detail_height
        left_width = max(42, width // 3)
        right_width = width - left_width - 1
        economics = screen.derwin(summary_height, left_width, summary_y, 0)
        activity = screen.derwin(summary_height, right_width, summary_y, left_width + 1)
        draw_box(economics, "Game Catalogue | Economics")
        draw_box(activity, f"Recent Activity | {game.title}")
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
            (f"Revenue leader            {top_game.title} ({money(top_game.net_revenue)})", 0),
            ("LIVE OPERATIONS", curses.A_BOLD),
            (f"Updates enabled           {sum(item.auto_updates for item in catalog)}/{len(catalog)} games", 0),
            (f"Updates shipped           {sum(item.updates_released for item in catalog)} total", 0),
            (f"Active promotions         {len(state.studio.active_promotions)} | Team load {campaign_load:.0%}", curses.color_pair(5) if campaign_load >= 0.30 else 0),
            (f"Largest live audience     {top_audience.title} ({top_audience.monthly_players:,})", 0),
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
            add_text(activity, snapshot_row + 4, 2, f"Live ops    {'ACTIVE' if game.auto_updates else 'PAUSED'} | {game.updates_released} shipped | {len(promotions)} promotions", right_width - 4)
            result = money(game_profit(game)) if game.cost_history_complete else "cost history unavailable"
            add_text(activity, snapshot_row + 5, 2, f"Economics   {money(game.net_revenue)} net revenue | {result} profit", right_width - 4, curses.color_pair(5) if game.cost_history_complete and game_profit(game) < 0 else 0)


def promotion_targets(state: GameState) -> list[tuple[int, str, float, str]]:
    targets = []
    if state.studio.current_project:
        project = state.studio.current_project
        targets.append((0, project.title, project.hype, "In development"))
    for game in live_games(state):
        targets.append((game.game_id, game.title, game.hype, f"rating {rating_text(game)} | {game.monthly_players:,} monthly | {update_status(game)}"))
    return targets


def draw_marketing_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel_height = height - 4
    state.marketing_tab = 0 if state.marketing_tab <= 0 else 1
    target_width = max(32, width // 3)
    option_width = width - target_width - 1
    targets_panel = screen.derwin(panel_height, target_width, 3, 0)
    options_panel = screen.derwin(panel_height, option_width, 3, target_width + 1)
    draw_box(targets_panel, "Promotion Targets")
    draw_box(options_panel, f"Promotion Planning | Game Reputation {state.studio.reputation:.1f}")
    targets = promotion_targets(state)
    if not targets:
        add_text(targets_panel, 1, 2, "No project or released game to promote.", target_width - 4)
    state.selected_promotion_target = min(state.selected_promotion_target, max(0, len(targets) - 1))
    target_inner = target_width - 4
    target_expanded = target_inner >= 55
    target_title_width = max(10, target_inner - (34 if target_expanded else 9))
    target_header = f"  {'GAME':<{target_title_width}} {'RATING':>6} {'HYPE':>5} {'MONTHLY':>8} {'UPDATES':>8}" if target_expanded else f"  {'GAME':<{target_title_width}} {'HYPE':>5}"
    add_text(targets_panel, 1, 2, target_header, target_inner, curses.A_BOLD)
    target_visible = panel_height - 3
    target_start = list_start(state.selected_promotion_target, len(targets), target_visible) if targets else 0
    for row, (game_id, title, hype, _) in enumerate(targets[target_start : target_start + target_visible], 2):
        selected = target_start + row - 2 == state.selected_promotion_target
        if game_id == 0:
            rating = "dev"
            monthly = 0
            updates = "-"
        else:
            game = game_by_id(state.studio, game_id)
            rating = rating_text(game) if game else "n/a"
            monthly = game.monthly_players if game else 0
            updates = f"#{game.updates_released}" if game else "-"
        target_text = f"{'> ' if selected else '  '}{title[:target_title_width]:<{target_title_width}} {rating:>6} {hype:>5.0f} {monthly:>8,} {updates:>8}" if target_expanded else f"{'> ' if selected else '  '}{title[:target_title_width]:<{target_title_width}} {hype:>5.0f}"
        add_text(targets_panel, row, 2, target_text, target_inner, curses.color_pair(3) | curses.A_BOLD if selected and state.marketing_tab == 0 else 0)
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
    active = state.studio.active_promotions
    add_text(options_panel, len(PROMOTIONS) + 3, 2, f"Active promotions: {len(active)} | Combined team load {sum(item.team_share for item in active):.0%}", option_width - 4, curses.color_pair(4))


def draw_upgrades(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel = screen.derwin(height - 4, width, 3, 0)
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
        header = f"  {'TITLE':<28} {'GENRE':<16} {'RATING':>6} {'HYPE':>5} {'MONTHLY':>9} {'UNITS':>10} {'NET REVENUE':>11} {'TOTAL COST':>11} {'PROFIT':>11} {'UPDATES':>9}"
    else:
        header = f"  {'TITLE':<18} {'RATE':>4} {'MONTHLY':>8} {'REVENUE':>10} {'PROFIT':>10} {'UPDATES':>8}"
    add_text(panel, 3, 2, header, width - 4, curses.A_BOLD)
    for row, game in enumerate(games[start : start + visible], 4):
        index = start + row - 4
        cost = money(game_total_cost(game)) if game.cost_history_complete else "n/a"
        profit = money(game_profit(game)) if game.cost_history_complete else "n/a"
        if wide:
            text = f"{'> ' if index == state.selected_stat else '  '}{game.title[:28]:<28} {game.genre[:16]:<16} {rating_text(game):>6} {game.hype:>5.0f} {game.monthly_players:>9,} {game.units_sold:>10,} {money(game.net_revenue):>11} {cost:>11} {profit:>11} {('#' + str(game.updates_released)):>9}"
        else:
            text = f"{'> ' if index == state.selected_stat else '  '}{game.title[:18]:<18} {rating_text(game):>4} {game.monthly_players:>8,} {money(game.net_revenue):>10} {profit:>10} {('#' + str(game.updates_released)):>8}"
        add_text(panel, row, 2, text, width - 4, curses.color_pair(3) | curses.A_BOLD if index == state.selected_stat else 0)
    game = games[state.selected_stat]
    lineage = "original" if game.sequel_of is None else f"sequel generation {game.generation}"
    add_text(panel, height - 3, 2, f"{game.title} | Theme {game.topic} / Storefront {game.channel} / {lineage} | Rating {rating_text(game)}/100 | Hype {game.hype:.0f} | Monthly active players {game.monthly_players:,}", width - 4, curses.color_pair(4))
    if game.cost_history_complete:
        costs = f"COSTS: setup/store {money(game.production_cost)} + development staff {money(game.labor_cost)} + marketing {money(game.marketing_cost)} + hosting/updates {money(game.post_launch_cost)} = {money(game_total_cost(game))} total | PROFIT {money(game_profit(game))}"
    else:
        costs = "COSTS: full per-game cost tracking was not present when this older title was developed; revenue remains accurate."
    add_text(panel, height - 2, 2, costs, width - 4, curses.color_pair(4) if game.cost_history_complete and game_profit(game) >= 0 else curses.color_pair(5))


def draw_analysis(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel = screen.derwin(height - 4, width, 3, 0)
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
    panel = screen.derwin(height - 4, width, 3, 0)
    draw_box(panel, "Settings")
    speed = TIME_LABELS[state.time_speed_index]
    add_text(panel, 1, 2, "CURRENT SETTINGS", width - 4, curses.A_BOLD)
    add_text(panel, 2, 2, f"Simulation speed   {speed}", width - 4)
    add_text(panel, 3, 2, f"Save file          {state.save_path}", width - 4)
    add_text(panel, 4, 2, "Minimum terminal   74 columns x 24 rows", width - 4)
    add_text(panel, 6, 2, "GLOBAL CONTROLS", width - 4, curses.A_BOLD)
    add_text(panel, 7, 2, "Left/Right  change speed | Space  pause/resume", width - 4)
    add_text(panel, 8, 2, "Ctrl+S  save | Q  quit | Esc  return to dashboard", width - 4)
    add_text(panel, 10, 2, "Mouse controls and keyboard shortcuts are both enabled.", width - 4)


def footer_actions(state: GameState, width: int | None = None) -> list[tuple[str, str]]:
    compact = width is not None and width < 100
    dense = width is not None and width < 150
    play_label = "Play" if state.time_speed_index == 0 else "Pause"
    if compact:
        playback_actions = [("[<]", "slower"), ("[ ]", "pause"), ("[>]", "faster")]
        save_actions = [("[Ctrl+S]", "save"), ("[Q]", "quit")]
    elif dense:
        playback_actions = [("[<]", "slower"), ("[Space]", "pause"), ("[>]", "faster")]
        save_actions = [("[Ctrl+S]", "save"), ("[Q]", "quit")]
    else:
        playback_actions = [("[<]", "slower"), (f"[Space]{play_label}", "pause"), ("[>]", "faster")]
        save_actions = [("[Ctrl+S]Save", "save"), ("[Q]Quit", "quit")]
    settings_action = [("[Esc]" if dense else "[Esc]Settings", "settings")] if state.modal == "main" else []
    global_actions = playback_actions + settings_action + save_actions
    if state.modal == "main":
        if compact:
            actions = [("[N]", "new"), ("[J]", "contracts"), ("[M]", "marketing"), ("[T]", "team"), ("[U]", "upgrades"), ("[G]", "games"), ("[S]", "analysis")]
        elif dense:
            actions = [("[N]ew", "new"), ("[J]obs", "contracts"), ("[M]Mktg", "marketing"), ("[T]eam", "team"), ("[U]pg", "upgrades"), ("[G]Cat", "games"), ("[S]Stats", "analysis")]
        else:
            actions = [("[N]ew", "new"), ("[J]obs", "contracts"), ("[M]arketing", "marketing"), ("[T]eam", "team"), ("[U]pgrades", "upgrades"), ("[G]ame Catalogue", "games"), ("[S]tatistics", "analysis")]
        return actions + global_actions
    if state.modal == "new_game":
        dense = width is not None and width < 150
        if state.new_game_step == -1:
            actions = [("[Esc]" if compact else "[Esc]Back", "back"), ("[Up/Dn]Game" if dense else "[Up/Down]Game", "project_choice"), ("[Enter]Choose", "confirm")]
            return actions + global_actions
        panel_names = ("Genre", "Theme", "Storefront", "Plan")
        next_panel = panel_names[(state.new_game_step + 1) % len(panel_names)]
        if compact:
            actions = [("[Esc]", "back"), ("[Tab]", "next_new_game_panel"), ("[Up/Dn]", "new_game_selection")]
            if state.new_game_step == 3:
                actions.append(("[L/R]", "new_game_adjust"))
            actions.append(("[Enter]", "confirm"))
        elif dense:
            actions = [("[Esc]", "back"), (f"[Tab]{next_panel}", "next_new_game_panel"), (f"[Up/Dn]{panel_names[state.new_game_step]}", "new_game_selection")]
            if state.new_game_step == 3:
                actions.append(("[L/R]", "new_game_adjust"))
            actions.append(("[Enter]Start", "confirm"))
        else:
            actions = [("[Esc]Back", "back"), (f"[Tab]{next_panel}", "next_new_game_panel"), (f"[Up/Down]{panel_names[state.new_game_step]}", "new_game_selection")]
            if state.new_game_step == 3:
                actions.extend([("[Left/Right]Adjust", "new_game_adjust"), ("[R]andom", "random_title"), ("[T]ype", "type_title")])
            actions.append(("[Enter]Greenlight", "confirm"))
        return actions + global_actions
    if state.modal == "team":
        if compact:
            actions = [("[Esc]", "back"), ("[Tab]A", "applicants"), ("[Tab]T", "roster"), ("[Enter]H", "hire"), ("[D]", "dismiss")]
        else:
            actions = [("[Esc]Back", "back"), ("[Tab]Applicants", "applicants"), ("[Tab]Team", "roster"), ("[Enter]Hire", "hire"), ("[D]ismiss", "dismiss")]
        return actions + global_actions
    if state.modal == "contracts":
        auto = "ON" if state.studio.auto_contracts else "OFF"
        actions = [("[Esc]" if compact else "[Esc]Back", "back"), ("[Enter]Accept", "accept_contract"), ("[C]Auto" if compact else f"[C] Auto {auto}", "toggle_contracts")]
        return actions + global_actions
    if state.modal == "games":
        games = live_games(state)
        update_label = "[U]OFF" if compact else "[U] Updates OFF"
        focus_label = "[F]Focus" if compact else "[F] Focus"
        size_label = "[Z]Size" if compact else "[Z] Size"
        if games:
            game = games[min(state.selected_game, len(games) - 1)]
            update_label = f"[U]{'ON' if game.auto_updates else 'OFF'}" if compact else f"[U] Updates {'ON' if game.auto_updates else 'OFF'}"
            focus_label = f"[F]{game.update_focus[:5]}" if compact else f"[F] {game.update_focus[:10]}"
            size_label = f"[Z]{game.update_size}" if compact else f"[Z] {game.update_size}"
        actions = [("[Esc]", "back"), ("[U]" if compact else update_label, "toggle_updates"), ("[F]" if compact else focus_label, "cycle_update_focus"), ("[Z]" if compact else size_label, "cycle_update_size"), ("[M]" if compact else "[M]Promote", "promote_game")]
        return actions + global_actions
    if state.modal == "marketing":
        if state.marketing_tab == 0:
            actions = [("[Esc]" if compact else "[Esc]Back", "back"), ("[Tab]" if compact else "[Tab]Planning", "switch_marketing_tab"), ("[Up/Dn]" if compact else "[Up/Down]Game", "marketing_selection"), ("[Enter]" if compact else "[Enter]Select", "select_marketing_target")]
        else:
            actions = [("[Esc]" if compact else "[Esc]Back", "back"), ("[Tab]" if compact else "[Tab]Targets", "switch_marketing_tab"), ("[Up/Dn]" if compact else "[Up/Down]Promotion", "marketing_selection"), ("[Enter]" if compact else "[Enter]Buy", "buy_promotion")]
        return actions + global_actions
    if state.modal == "upgrades":
        return [("[Esc]" if compact else "[Esc]Back", "back"), ("[Enter]Buy", "buy")] + global_actions
    if state.modal == "settings":
        return [("[Esc]Back", "back")] + global_actions
    return [("[Esc]" if compact else "[Esc]Back", "back"), ("[<]View", "previous_view"), ("View[>]", "next_view")] + global_actions


def footer_layout(state: GameState, width: int) -> list[tuple[str, str, int]]:
    actions = footer_actions(state, width)
    right_actions = {"slower", "pause", "faster", "settings", "save", "quit"}
    left = [(label, action) for label, action in actions if action not in right_actions]
    right = [(label, action) for label, action in actions if action in right_actions]
    layout = []
    x = 1
    for label, action in left:
        layout.append((label, action, x))
        x += len(label) + 1
    right_width = sum(len(label) for label, _ in right) + max(0, len(right) - 1)
    x = max(x, width - right_width - 1)
    for label, action in right:
        layout.append((label, action, x))
        x += len(label) + 1
    return layout


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
    add_text(screen, height - 1, 0, " " * width, width, curses.color_pair(1))
    for label, _, x in footer_layout(state, width):
        draw_footer_label(screen, height - 1, x, label, width)


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
    try:
        save_game(state)
        state.log(f"Saved studio to {state.save_path}.")
    except OSError as error:
        state.log(f"Save failed: {error}.")


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
        state.modal = "settings"
    elif action == "games":
        state.modal = "games"
    elif action == "toggle_updates":
        games = live_games(state)
        if games:
            toggle_game_updates(state, games[min(state.selected_game, len(games) - 1)].game_id)
    elif action in ("cycle_update_focus", "cycle_update_size"):
        games = live_games(state)
        if games:
            game_id = games[min(state.selected_game, len(games) - 1)].game_id
            if action == "cycle_update_focus":
                cycle_game_update_focus(state, game_id)
            else:
                cycle_game_update_size(state, game_id)
    elif action == "promote_game":
        games = live_games(state)
        if games:
            game_id = games[min(state.selected_game, len(games) - 1)].game_id
            targets = promotion_targets(state)
            state.selected_promotion_target = next((index for index, target in enumerate(targets) if target[0] == game_id), 0)
            state.modal = "marketing"
            state.marketing_tab = 1
    elif action == "buy_promotion":
        targets = promotion_targets(state)
        if targets:
            buy_promotion(state, targets[state.selected_promotion_target][0], state.selected_promotion)
    elif action == "switch_marketing_tab":
        state.marketing_tab = 1 - state.marketing_tab
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
            state.modal = "games" if state.studio.catalog else "main"
        else:
            state.modal = "main"
    elif action == "confirm":
        handle_new_game_key(state, 10)
    elif action == "project_choice":
        choices = sequel_choices(state)
        state.selected_sequel_choice = (state.selected_sequel_choice + 1) % len(choices)
    elif action == "next_new_game_panel":
        handle_new_game_key(state, 9)
    elif action == "new_game_selection":
        handle_new_game_key(state, curses.KEY_DOWN)
    elif action == "new_game_adjust":
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
                state.new_game_step = 0
                state.title_roll += 1
                refresh_draft_title(state)
            else:
                prepare_sequel(state, choice)
        elif key in (8, 127, curses.KEY_BACKSPACE, 27):
            state.modal = "main"
        elif key == curses.KEY_UP:
            state.selected_sequel_choice = (state.selected_sequel_choice - 1) % len(choices)
        elif key == curses.KEY_DOWN:
            state.selected_sequel_choice = (state.selected_sequel_choice + 1) % len(choices)
        return
    previous_concept = (state.selected_genre, state.selected_topic)
    if key in (10, 13, curses.KEY_ENTER):
        start_project(state)
    elif key == 9:
        state.new_game_step = (state.new_game_step + 1) % 4
    elif key in (8, 127, curses.KEY_BACKSPACE, 27):
        state.new_game_step = -1
    elif key in (ord("t"), ord("T")):
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
            state.selected_channel = (state.selected_channel - 1) % len(CHANNELS)
        else:
            state.selected_focus = (state.selected_focus - 1) % 6
    elif key == curses.KEY_DOWN:
        if state.new_game_step == 0:
            state.selected_genre = (state.selected_genre + 1) % len(GENRES)
        elif state.new_game_step == 1:
            state.selected_topic = (state.selected_topic + 1) % len(TOPICS)
        elif state.new_game_step == 2:
            state.selected_channel = (state.selected_channel + 1) % len(CHANNELS)
        else:
            state.selected_focus = (state.selected_focus + 1) % 6
    elif key in (curses.KEY_LEFT, curses.KEY_RIGHT) and state.new_game_step == 3:
        delta = -1 if key == curses.KEY_LEFT else 1
        if state.selected_focus == 0:
            state.selected_scope = (state.selected_scope + delta) % len(SCOPES)
        elif state.selected_focus == 1:
            state.selected_marketing = (state.selected_marketing + delta) % len(MARKETING)
        else:
            focus_index = state.selected_focus - 2
            original = state.selected_focus
            state.selected_focus = focus_index
            adjust_focus(state, delta * 5)
            state.selected_focus = original
    if previous_concept != (state.selected_genre, state.selected_topic):
        state.sequel_game_id = None
        state.title_roll += 1
        refresh_draft_title(state)


def handle_team_key(state: GameState, key: int) -> None:
    if key in (8, 127, curses.KEY_BACKSPACE, 27):
        state.modal = "main"
    elif key == 9:
        state.team_tab = 1 - state.team_tab
    elif key == curses.KEY_UP:
        if state.team_tab == 0 and state.studio.applicants:
            state.selected_employee = (state.selected_employee - 1) % len(state.studio.applicants)
        else:
            removable = max(1, len(state.studio.team) - 1)
            state.selected_roster = (state.selected_roster - 1) % removable
    elif key == curses.KEY_DOWN:
        if state.team_tab == 0 and state.studio.applicants:
            state.selected_employee = (state.selected_employee + 1) % len(state.studio.applicants)
        else:
            removable = max(1, len(state.studio.team) - 1)
            state.selected_roster = (state.selected_roster + 1) % removable
    elif key in (10, 13, curses.KEY_ENTER) and state.team_tab == 0:
        hire_candidate(state)
    elif key in (ord("d"), ord("D")) and state.team_tab == 1:
        dismiss_employee(state)


def handle_mouse(state: GameState, dimensions: tuple[int, int]) -> bool | None:
    try:
        _, x, y, _, buttons = curses.getmouse()
    except curses.error:
        return
    height, width = dimensions
    wheel_up = bool(buttons & getattr(curses, "BUTTON4_PRESSED", 0))
    wheel_down = bool(buttons & getattr(curses, "BUTTON5_PRESSED", 0))
    if wheel_up or wheel_down:
        key = curses.KEY_UP if wheel_up else curses.KEY_DOWN
        if state.modal == "analysis":
            if state.analysis_view in (2, 3):
                item_count = len(GENRES) if state.analysis_view == 2 else len(state.studio.catalog)
                if item_count:
                    state.selected_stat = (state.selected_stat + (-1 if wheel_up else 1)) % item_count
            else:
                state.analysis_view = (state.analysis_view + (-1 if wheel_up else 1)) % len(ANALYSIS_TABS)
        elif state.modal == "new_game" and state.new_game_step == 3:
            handle_new_game_key(state, curses.KEY_LEFT if wheel_up else curses.KEY_RIGHT)
        elif state.modal == "team":
            handle_team_key(state, key)
        elif state.modal == "contracts" and state.studio.contract_offers:
            state.selected_contract = (state.selected_contract + (-1 if wheel_up else 1)) % len(state.studio.contract_offers)
        elif state.modal == "games" and state.studio.catalog:
            state.selected_game = (state.selected_game + (-1 if wheel_up else 1)) % len(state.studio.catalog)
        elif state.modal == "marketing":
            if x < width // 3:
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
    if right_click and state.modal != "main":
        state.modal = "main"
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

    if y == height - 1:
        for action, start, end in footer_button_ranges(state, width):
            if start <= x < end:
                return perform_footer_action(state, action)
        return

    if state.modal == "main":
        if width >= 120:
            journal_height = 7 if height >= 32 else 4
            journal_y = height - journal_height - 1
            if x < width // 2 and 3 <= y < 19:
                state.modal = "analysis"
            elif x < width // 2 and 19 <= y < journal_y:
                state.modal = "team"
            elif x >= width // 2 and 3 <= y < 11 and state.studio.current_project is None:
                state.modal = "new_game"
                state.new_game_step = -1
                state.selected_sequel_choice = 0
            elif x >= width // 2 and 3 <= y < 11:
                targets = promotion_targets(state)
                state.selected_promotion_target = next((index for index, target in enumerate(targets) if target[0] == 0), 0)
                state.modal = "marketing"
                state.marketing_tab = 1
            elif x >= width // 2 and 11 <= y < 19:
                state.modal = "contracts"
            elif x >= width // 2 and 19 <= y < journal_y:
                state.modal = "games"
        else:
            if 3 <= y < 11:
                if x < width // 2:
                    state.modal = "analysis"
                elif state.studio.current_project is None:
                    state.modal = "new_game"
                    state.new_game_step = -1
                    state.selected_sequel_choice = 0
                else:
                    targets = promotion_targets(state)
                    state.selected_promotion_target = next((index for index, target in enumerate(targets) if target[0] == 0), 0)
                    state.modal = "marketing"
                    state.marketing_tab = 1
            else:
                journal_height = 7 if height >= 32 else 4
                journal_y = height - journal_height - 1
                available = max(0, journal_y - 11)
                middle_height = available if available < 16 else (available + 1) // 2
                lower_y = 11 + middle_height
                if 11 <= y < lower_y:
                    state.modal = "team" if x < width // 2 else "games"
                elif lower_y <= y < journal_y:
                    state.modal = "analysis" if x < width // 2 else "contracts"
        return

    if state.modal == "analysis":
        tab_width = max(12, (width - 4) // len(ANALYSIS_TABS))
        if y == 4:
            state.analysis_view = min(len(ANALYSIS_TABS) - 1, max(0, (x - 2) // tab_width))
            state.selected_stat = 0
        elif state.analysis_view in (2, 3) and y >= 7:
            item_count = len(GENRES) if state.analysis_view == 2 else len(state.studio.catalog)
            visible = height - 11 if state.analysis_view == 3 else height - 10
            start = list_start(state.selected_stat, item_count, visible) if item_count else 0
            index = start + y - 7
            if 0 <= index < item_count:
                state.selected_stat = index
        return

    if state.modal == "upgrades":
        row = y - 5
        if 0 <= row < len(UPGRADES):
            state.selected_upgrade = row
            if double_click:
                buy_upgrade(state)
        return

    if state.modal == "contracts":
        board_width = max(46, width * 2 // 3)
        row = y - 5
        if x <= board_width and 0 <= row < len(state.studio.contract_offers):
            state.selected_contract = row
            if double_click:
                accept_contract_offer(state)
        return

    if state.modal == "games":
        games = live_games(state)
        row = y - 5
        if width >= 120:
            panel_height = height - 4
            catalog_height = min(15, max(9, min(len(games) + 4, panel_height // 3 + 2)))
            in_catalog = 5 <= y < 3 + catalog_height - 1
            visible = catalog_height - 3
        else:
            in_catalog = x <= max(48, width * 2 // 3) and row >= 0
            visible = height - 6
        if in_catalog and row >= 0 and games:
            start = list_start(state.selected_game, len(games), visible)
            index = start + row
            if 0 <= index < len(games):
                state.selected_game = index
                if double_click:
                    toggle_game_updates(state, games[index].game_id)
        return

    if state.modal == "marketing":
        target_width = max(32, width // 3)
        row = y - 5
        if x <= target_width:
            state.marketing_tab = 0
            targets = promotion_targets(state)
            visible = height - 7
            start = list_start(state.selected_promotion_target, len(targets), visible) if targets else 0
            index = start + row
            if 0 <= index < len(targets):
                state.selected_promotion_target = index
                if double_click:
                    state.marketing_tab = 1
        elif 0 <= row < len(PROMOTIONS):
            state.marketing_tab = 1
            state.selected_promotion = row
            if double_click:
                targets = promotion_targets(state)
                if targets:
                    buy_promotion(state, targets[state.selected_promotion_target][0], row)
        return

    if state.modal == "team":
        roster_width, _ = team_panel_widths(state, width)
        row = y - 5
        if row < 0:
            return
        if x <= roster_width:
            state.team_tab = 1
            visible_team = state.studio.team[: height - 7]
            if row < len(visible_team) and not visible_team[row].founder:
                employee = visible_team[row]
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
            row = y - 6
            if row >= 0:
                start = list_start(state.selected_sequel_choice, len(choices), visible)
                index = start + row
                if 0 <= index < len(choices):
                    state.selected_sequel_choice = index
                    if double_click:
                        handle_new_game_key(state, 10)
            return
        plan_height = 10
        picker_height = max(7, height - 4 - plan_height)
        genre_width = max(20, width // 4)
        topic_width = max(24, width // 3)
        if 4 <= y < 3 + picker_height - 1:
            visible = picker_height - 2
            row = y - 4
            if x <= genre_width:
                state.new_game_step = 0
                index = list_start(state.selected_genre, len(GENRES), visible) + row
                state.selected_genre = min(index, len(GENRES) - 1)
            elif x <= genre_width + topic_width + 1:
                state.new_game_step = 1
                index = list_start(state.selected_topic, len(TOPICS), visible) + row
                state.selected_topic = min(index, len(TOPICS) - 1)
            else:
                state.new_game_step = 2
                index = list_start(state.selected_channel, len(CHANNELS), visible) + row
                state.selected_channel = min(index, len(CHANNELS) - 1)
            if state.new_game_step in (0, 1):
                state.sequel_game_id = None
                state.title_roll += 1
                refresh_draft_title(state)
        else:
            if y == 4 + picker_height:
                state.naming_game = True
                state.draft_title = ""
                return
            row = y - (5 + picker_height)
            if 0 <= row < 6:
                state.new_game_step = 3
                state.selected_focus = row
                if double_click:
                    handle_new_game_key(state, 10)


def handle_key(state: GameState, key: int, dimensions: tuple[int, int] | None = None) -> bool:
    if key == CTRL_S:
        save_state(state)
        return True
    if state.modal == "new_game" and state.naming_game:
        if key in (10, 13, curses.KEY_ENTER):
            if state.draft_title.strip():
                state.draft_title = state.draft_title.strip()
                state.naming_game = False
        elif key == 27:
            state.naming_game = False
        elif key in (8, 127, curses.KEY_BACKSPACE):
            state.draft_title = state.draft_title[:-1]
        elif 32 <= key <= 126 and len(state.draft_title) < 48:
            state.draft_title += chr(key)
        return True
    if key in (ord("q"), ord("Q")):
        return False
    if key == ord(" "):
        toggle_pause(state)
        return True
    if key == curses.KEY_MOUSE and dimensions is not None:
        return handle_mouse(state, dimensions) is not False
    if state.modal == "new_game":
        handle_new_game_key(state, key)
    elif state.modal == "team":
        handle_team_key(state, key)
    elif state.modal == "contracts":
        if key in (8, 127, curses.KEY_BACKSPACE, 27):
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
        if key in (8, 127, curses.KEY_BACKSPACE, 27):
            state.modal = "main"
        elif key == curses.KEY_UP and games:
            state.selected_game = (state.selected_game - 1) % len(games)
        elif key == curses.KEY_DOWN and games:
            state.selected_game = (state.selected_game + 1) % len(games)
        elif key in (ord("u"), ord("U"), 10, 13, curses.KEY_ENTER) and games:
            toggle_game_updates(state, games[state.selected_game].game_id)
        elif key in (ord("f"), ord("F")) and games:
            cycle_game_update_focus(state, games[state.selected_game].game_id)
        elif key in (ord("z"), ord("Z")) and games:
            cycle_game_update_size(state, games[state.selected_game].game_id)
        elif key in (ord("m"), ord("M")) and games:
            perform_footer_action(state, "promote_game")
    elif state.modal == "marketing":
        targets = promotion_targets(state)
        if key in (8, 127, curses.KEY_BACKSPACE, 27):
            state.modal = "games" if state.studio.catalog else "main"
        elif key == 9:
            state.marketing_tab = 1 - state.marketing_tab
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
        if key in (8, 127, curses.KEY_BACKSPACE, 27):
            state.modal = "main"
        elif key == curses.KEY_UP:
            state.selected_upgrade = (state.selected_upgrade - 1) % len(UPGRADES)
        elif key == curses.KEY_DOWN:
            state.selected_upgrade = (state.selected_upgrade + 1) % len(UPGRADES)
        elif key in (10, 13, curses.KEY_ENTER):
            buy_upgrade(state)
    elif state.modal == "analysis":
        if key in (8, 127, curses.KEY_BACKSPACE, 27):
            state.modal = "main"
        elif key in (9, curses.KEY_RIGHT):
            state.analysis_view = (state.analysis_view + 1) % len(ANALYSIS_TABS)
            state.selected_stat = 0
        elif key == curses.KEY_LEFT:
            state.analysis_view = (state.analysis_view - 1) % len(ANALYSIS_TABS)
            state.selected_stat = 0
        elif key in (curses.KEY_UP, curses.KEY_DOWN) and state.analysis_view in (2, 3):
            count = len(GENRES) if state.analysis_view == 2 else len(state.studio.catalog)
            if count:
                state.selected_stat = (state.selected_stat + (-1 if key == curses.KEY_UP else 1)) % count
    elif state.modal == "settings":
        if key in (8, 127, curses.KEY_BACKSPACE, 27):
            state.modal = "main"
    elif state.modal == "main":
        if key in (ord("n"), ord("N")):
            open_new_game(state)
        elif key in (ord("t"), ord("T"), ord("e"), ord("E")):
            state.modal = "team"
        elif key in (ord("u"), ord("U")):
            state.modal = "upgrades"
        elif key in (ord("s"), ord("S")):
            state.modal = "analysis"
        elif key in (ord("g"), ord("G")):
            state.modal = "games"
        elif key in (ord("m"), ord("M")):
            state.modal = "marketing"
            state.marketing_tab = 0
        elif key in (ord("c"), ord("C")):
            toggle_auto_contracts(state)
        elif key in (ord("j"), ord("J")):
            state.modal = "contracts"
        elif key == 27:
            state.modal = "settings"
        elif key == curses.KEY_RIGHT:
            state.time_speed_index = min(len(TIME_SPEEDS) - 1, max(1, state.time_speed_index + 1))
            state.resume_speed_index = state.time_speed_index
        elif key == curses.KEY_LEFT:
            state.time_speed_index = max(1, state.time_speed_index - 1)
            state.resume_speed_index = state.time_speed_index
    return True


def run(screen: curses.window, load_save: bool, save_path: str) -> None:
    curses.curs_set(0)
    curses.raw()
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
