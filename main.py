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
    title = " INDIE STUDIO / REALITY MODE "
    date_text = state.clock.current_date.strftime("%d %b %Y")
    right = f"{date_text}  WEEK {state.clock.week} "
    add_text(screen, 0, 0, (title + " " * max(1, width - len(title) - len(right)) + right).ljust(width), width, curses.color_pair(1) | curses.A_BOLD)
    bar_width = max(8, min(34, width - 50))
    filled = round(bar_width * state.clock.progress)
    week_progress = "█" * filled + "░" * (bar_width - filled)
    contract = ""
    if studio.contract:
        contract_progress = 0 if studio.contract.required_work <= 0 else studio.contract.work_done / studio.contract.required_work
        contract = f" | JOB {studio.contract.focus} {contract_progress:.0%}/{studio.contract.weeks_left}w"
    if studio.auto_contracts:
        contract += " | AUTO JOBS"
    status = "CLOSED" if studio.closed else TIME_LABELS[state.time_speed_index]
    suggested = recommended_team_size(studio)
    line = f" Next week [{week_progress}]  {status} | Team {len(studio.team)}/{suggested} suggested | Followers {studio.followers:,}{contract}"
    add_text(screen, 1, 0, line.ljust(width), width, curses.color_pair(4))


def draw_dashboard(screen: curses.window, state: GameState, width: int) -> int:
    left_width = max(34, width // 2)
    right_width = width - left_width - 1
    finance = screen.derwin(7, left_width, 3, 0)
    project_panel = screen.derwin(7, right_width, 3, left_width + 1)
    draw_box(finance, "Cash & Runway")
    draw_box(project_panel, "Production")

    studio = state.studio
    burn = monthly_fixed_cost(studio)
    runway = runway_months(studio)
    runway_text = f"{runway:.1f} months" if runway < 99 else "99+ months"
    add_text(finance, 1, 2, f"Bank balance       {money(studio.cash)}", left_width - 4, curses.A_BOLD if studio.cash >= 0 else curses.color_pair(5) | curses.A_BOLD)
    add_text(finance, 2, 2, f"Committed burn     {money(burn)}/month", left_width - 4)
    add_text(finance, 3, 2, f"Runway             {runway_text}", left_width - 4, curses.color_pair(5) if runway < 4 else 0)
    add_text(finance, 4, 2, f"This month         {money(studio.period_revenue)} in / {money(studio.period_expenses)} out", left_width - 4)
    add_text(finance, 5, 2, f"Tax reserve        {money(studio.tax_reserve)}", left_width - 4, curses.color_pair(4))

    project = studio.current_project
    if project is None:
        add_text(project_panel, 1, 2, "No original game in production", right_width - 4, curses.A_BOLD)
        add_text(project_panel, 2, 2, "N  build a realistic project plan", right_width - 4)
        add_text(project_panel, 3, 2, "J job board | C toggle automatic contracts", right_width - 4)
        add_text(project_panel, 4, 2, f"Released {studio.released_games} | Game rep {studio.reputation:.1f} | Contractor {studio.contractor_reputation:.1f}", right_width - 4)
        if studio.contract:
            source = "auto" if studio.contract.auto_accepted else "manual"
            add_text(project_panel, 5, 2, f"{studio.contract.client}: {studio.contract.title} [{source}] | queue {len(studio.contract_queue)}", right_width - 4, curses.color_pair(4))
    else:
        bar_width = max(8, right_width - 20)
        filled = round(bar_width * project.progress)
        bar = "█" * filled + "░" * (bar_width - filled)
        weekly_output = projected_weekly_output(studio, project.focus)
        remaining = max(1, round((project.total_work - project.work_done) / weekly_output))
        add_text(project_panel, 1, 2, project.title, right_width - 4, curses.A_BOLD)
        add_text(project_panel, 2, 2, f"{project.phase} [{bar}] {project.progress:.0%}", right_width - 4, curses.color_pair(4))
        add_text(project_panel, 3, 2, f"Week {project.weeks} | about {remaining}w left | plan {project.planned_weeks}w", right_width - 4)
        add_text(project_panel, 4, 2, f"{project.scope} / {project.channel} / {money(project.price)} retail", right_width - 4)
        warning = "Contract is cutting project capacity by 45%" if studio.contract else f"Hype {project.hype:.0f} | Defect load {project.defects:.1f}"
        add_text(project_panel, 5, 2, warning, right_width - 4, curses.color_pair(5) if studio.contract else curses.color_pair(4))
    return 10


def draw_main_content(screen: curses.window, state: GameState, width: int, height: int, y: int) -> None:
    left_width = max(38, width // 2)
    right_width = width - left_width - 1
    panel_height = 8
    team = screen.derwin(panel_height, left_width, y, 0)
    market = screen.derwin(panel_height, right_width, y, left_width + 1)
    draw_box(team, f"Small Team {len(state.studio.team)} / Suggested {recommended_team_size(state.studio)}")
    draw_box(market, "Market & Accounts")

    for row, employee in enumerate(state.studio.team[:6], 1):
        founder = " [founder]" if employee.founder else ""
        text = f"{employee.name}{founder} | {employee.role} | M{employee.morale:.0f} F{employee.fatigue:.0f} | {money(employee.monthly_salary)}/mo"
        attr = curses.color_pair(5) if employee.morale < 30 or employee.fatigue > 70 else 0
        add_text(team, row, 2, text, left_width - 4, attr)

    row = 1
    for game in list(reversed(state.studio.catalog))[:3]:
        sale = sale_for_game(state.studio, game.game_id)
        weekly = sale.weekly_units if sale else 0
        text = f"{game.title}: rating {rating_text(game)}/100 | hype {game.hype:.0f} | {weekly:,}/week | {game.monthly_players:,} monthly players | {update_status(game)}"
        add_text(market, row, 2, text, right_width - 4)
        row += 1
    for entry in state.studio.ledger[: max(0, 6 - row + 1)]:
        add_text(market, row, 2, f"{entry.month}  {money(entry.revenue)} - {money(entry.expenses)} = {money(entry.net)}", right_width - 4, curses.color_pair(4) if entry.net >= 0 else curses.color_pair(5))
        row += 1
    if row == 1:
        add_text(market, 1, 2, "No sales or closed month yet.", right_width - 4)

    log_y = y + panel_height
    log_height = height - log_y - 1
    if log_height >= 3:
        activity = screen.derwin(log_height, width, log_y, 0)
        draw_box(activity, "Studio Journal")
        for row, message in enumerate(state.logs[: log_height - 2], 1):
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
    draw_box(panel, "Start Development: Original Game or Sequel")
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
    draw_box(plan, "4 Production Plan: T type title, R randomize, Enter greenlight")
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


def draw_team_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel_height = height - 4
    roster_width = max(35, width // 2)
    applicant_width = width - roster_width - 1
    roster = screen.derwin(panel_height, roster_width, 3, 0)
    applicants = screen.derwin(panel_height, applicant_width, 3, roster_width + 1)
    target = recommended_team_size(state.studio)
    draw_box(roster, f"Roster {len(state.studio.team)}/{target} suggested: D dismiss")
    next_pool = applicant_pool_size(state.studio)
    draw_box(applicants, f"Applicants {len(state.studio.applicants)} / Next market {next_pool}: Enter hire")
    removable_index = 0
    for row, employee in enumerate(state.studio.team[: panel_height - 2], 1):
        is_selected = state.team_tab == 1 and not employee.founder and removable_index == state.selected_roster
        if not employee.founder:
            removable_index += 1
        marker = ">" if is_selected else " "
        salary = "owner draw" if employee.founder else f"${employee.annual_salary:,}/yr"
        line = f"{marker} {employee.name} | {employee.role} | {salary}"
        add_text(roster, row, 2, line, roster_width - 4, curses.color_pair(3) | curses.A_BOLD if is_selected else 0)
        if row + 1 < panel_height - 1 and roster_width >= 60:
            pass
    for row, employee in enumerate(state.studio.applicants[: panel_height - 2], 1):
        selected = state.team_tab == 0 and row - 1 == state.selected_employee
        marker = ">" if selected else " "
        skills = f"D{employee.design} A{employee.art} Au{employee.audio} C{employee.code}"
        text = f"{marker} {employee.name} | {employee.role} | {skills} | ${employee.annual_salary:,}/yr | {employee.trait}"
        add_text(applicants, row, 2, text, applicant_width - 4, curses.color_pair(3) | curses.A_BOLD if selected else 0)


def draw_contract_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel_height = height - 4
    board_width = max(46, width * 2 // 3)
    detail_width = width - board_width - 1
    board = screen.derwin(panel_height, board_width, 3, 0)
    detail = screen.derwin(panel_height, detail_width, 3, board_width + 1)
    studio = state.studio
    auto = "ON" if studio.auto_contracts else "OFF"
    draw_box(board, f"Job Board: Enter accept one | C auto {auto}")
    draw_box(detail, "Contractor Profile & Queue")
    if not studio.contract_offers:
        add_text(board, 1, 2, "No unaccepted jobs. The board refreshes monthly.", board_width - 4)
    state.selected_contract = min(state.selected_contract, max(0, len(studio.contract_offers) - 1))
    for row, contract in enumerate(studio.contract_offers[: panel_height - 2], 1):
        selected = row - 1 == state.selected_contract
        estimate = estimated_contract_weeks(studio, contract)
        locked = studio.contractor_reputation < contract.reputation_required
        status = f"LOCK rep {contract.reputation_required}" if locked else f"est {estimate}w / due {contract.weeks_left}w"
        text = f"{'> ' if selected else '  '}{contract.client[:16]:<16} {contract.title[:24]:<24} {contract.focus:<10} D{contract.difficulty} {money(contract.payout):>9} {status}"
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
        add_text(detail, 5, 2, f"ACTIVE {source} JOB", detail_width - 4, curses.color_pair(3) | curses.A_BOLD)
        add_text(detail, 6, 2, f"{active.client}", detail_width - 4)
        add_text(detail, 7, 2, active.title, detail_width - 4)
        add_text(detail, 8, 2, f"Focus {active.focus} | D{active.difficulty}", detail_width - 4)
        add_text(detail, 9, 2, f"Progress {progress:.0%} | est {estimate}w", detail_width - 4)
        add_text(detail, 10, 2, f"Deadline {active.weeks_left}w | {money(active.payout)}", detail_width - 4)
    else:
        add_text(detail, 5, 2, "No active client job", detail_width - 4)
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
    list_width = max(48, width * 2 // 3)
    detail_width = width - list_width - 1
    games_panel = screen.derwin(panel_height, list_width, 3, 0)
    detail = screen.derwin(panel_height, detail_width, 3, list_width + 1)
    draw_box(games_panel, "Live Game Catalogue: every release remains on sale")
    draw_box(detail, "Selected Game")
    games = live_games(state)
    if not games:
        add_text(games_panel, 1, 2, "No releases yet.", list_width - 4)
        add_text(detail, 1, 2, "Release a game to begin live operations.", detail_width - 4)
        return
    state.selected_game = min(state.selected_game, len(games) - 1)
    visible = panel_height - 3
    start = list_start(state.selected_game, len(games), visible)
    add_text(games_panel, 1, 2, "TITLE                         RATING  HYPE  SALES/W  MONTHLY PLAYERS  UPDATE STATE", list_width - 4, curses.A_BOLD)
    for row, game in enumerate(games[start : start + visible], 2):
        index = start + row - 2
        sale = sale_for_game(state.studio, game.game_id)
        weekly = sale.weekly_units if sale else 0
        text = f"{'> ' if index == state.selected_game else '  '}{game.title[:28]:<28} {rating_text(game):>6}  {game.hype:>4.0f}  {weekly:>7,}  {game.monthly_players:>7,}  {update_status(game)}"
        add_text(games_panel, row, 2, text, list_width - 4, curses.color_pair(3) | curses.A_BOLD if index == state.selected_game else 0)

    game = games[state.selected_game]
    sale = sale_for_game(state.studio, game.game_id)
    rating_attr = curses.color_pair(4) if game.score >= 70 else curses.color_pair(5) if game.score < 45 else curses.color_pair(3)
    size = next((item for item in UPDATE_SIZES if item["name"] == game.update_size), UPDATE_SIZES[0])
    add_text(detail, 1, 2, game.title, detail_width - 4, curses.A_BOLD)
    add_text(detail, 2, 2, f"{game.genre} / {game.topic}", detail_width - 4)
    add_text(detail, 3, 2, f"Rating  [{meter(game.score, 100, 16)}] {rating_text(game)}/100", detail_width - 4, rating_attr)
    add_text(detail, 4, 2, f"Hype    [{meter(game.hype, 200, 16)}] {game.hype:.0f}/200", detail_width - 4, curses.color_pair(3))
    add_text(detail, 5, 2, f"Monthly active players  {game.monthly_players:,}", detail_width - 4, curses.color_pair(4) if game.monthly_players else curses.color_pair(5))
    add_text(detail, 6, 2, f"Peak monthly players    {game.peak_monthly_players:,}", detail_width - 4)
    add_text(detail, 7, 2, f"Weekly sales      {(sale.weekly_units if sale else 0):,}", detail_width - 4)
    add_text(detail, 8, 2, f"Lifetime units    {game.units_sold:,}", detail_width - 4)
    add_text(detail, 9, 2, f"Studio net        {money(game.net_revenue)}", detail_width - 4)
    add_text(detail, 10, 2, f"Evergreen floor   {(sale.evergreen_units if sale else 0):,}/week", detail_width - 4)
    add_text(detail, 12, 2, f"CONTINUOUS UPDATES {'ON' if game.auto_updates else 'OFF'}", detail_width - 4, curses.color_pair(4) if game.auto_updates else curses.color_pair(5) | curses.A_BOLD)
    add_text(detail, 13, 2, f"Focus {game.update_focus} | Size {game.update_size}", detail_width - 4)
    add_text(detail, 14, 2, f"Estimate {estimated_update_weeks(state.studio, game)}w | Ship cost {money(size['cost'])}", detail_width - 4)
    add_text(detail, 15, 2, f"Progress [{meter(game.update_progress, 100, 16)}] {game.update_progress:.0f}%", detail_width - 4, curses.color_pair(4))
    add_text(detail, 16, 2, f"Updates shipped   #{game.updates_released}", detail_width - 4)
    recommendation, recommendation_color = game_recommendation(game)
    promotions = [promotion for promotion in state.studio.active_promotions if promotion.game_id == game.game_id]
    if panel_height >= 22:
        add_text(detail, 18, 2, "RECOMMENDED", detail_width - 4, curses.A_BOLD)
        add_text(detail, 19, 2, recommendation, detail_width - 4, curses.color_pair(recommendation_color))
    if panel_height >= 24:
        add_text(detail, 21, 2, f"PROMOTIONS ({len(promotions)})", detail_width - 4, curses.A_BOLD)
        for row, promotion in enumerate(promotions[: panel_height - 23], 22):
            add_text(detail, row, 2, f"{promotion.name} {promotion.weeks_left}w", detail_width - 4)


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
    target_width = max(32, width // 3)
    option_width = width - target_width - 1
    targets_panel = screen.derwin(panel_height, target_width, 3, 0)
    options_panel = screen.derwin(panel_height, option_width, 3, target_width + 1)
    draw_box(targets_panel, "Choose Game")
    draw_box(options_panel, f"Promotion Options: Game reputation {state.studio.reputation:.1f}")
    targets = promotion_targets(state)
    if not targets:
        add_text(targets_panel, 1, 2, "No project or released game to promote.", target_width - 4)
    state.selected_promotion_target = min(state.selected_promotion_target, max(0, len(targets) - 1))
    for row, (_, title, hype, status) in enumerate(targets[: panel_height - 2], 1):
        selected = row - 1 == state.selected_promotion_target
        add_text(targets_panel, row, 2, f"{'> ' if selected else '  '}{title[:22]:<22} H{hype:>4.0f} {status}", target_width - 4, curses.color_pair(3) | curses.A_BOLD if selected else 0)
    state.selected_promotion = min(state.selected_promotion, len(PROMOTIONS) - 1)
    for row, promotion in enumerate(PROMOTIONS, 1):
        selected = row - 1 == state.selected_promotion
        locked = state.studio.reputation < promotion["rep"]
        status = f"LOCK rep {promotion['rep']}" if locked else f"{money(promotion['cost'])}, {promotion['weeks']}w, +{promotion['hype']} hype, {promotion['team']:.0%} team"
        text = f"{'> ' if selected else '  '}{promotion['name']:<24} {status:<34} {promotion['effect']}"
        attr = curses.color_pair(5) if locked else curses.color_pair(3) | curses.A_BOLD if selected else 0
        add_text(options_panel, row, 2, text, option_width - 4, attr)
    active = state.studio.active_promotions
    add_text(options_panel, len(PROMOTIONS) + 2, 2, f"Active campaigns: {len(active)} | Combined team load {sum(item.team_share for item in active):.0%}", option_width - 4, curses.color_pair(4))


def draw_upgrades(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel = screen.derwin(height - 4, width, 3, 0)
    draw_box(panel, "Infrastructure: Enter purchase, Backspace close")
    for row, upgrade in enumerate(UPGRADES, 1):
        selected = row - 1 == state.selected_upgrade
        owned = upgrade["key"] in state.studio.upgrades
        recurring = upgrade.get("monthly", 0) + upgrade.get("per_employee", 0) * len(state.studio.team)
        status = "ACTIVE" if owned else f"{money(upgrade['cost'])} + {money(recurring)}/month"
        text = f"{'> ' if selected else '  '}{upgrade['name']:<25} {status:<24} {upgrade['effect']}"
        attr = curses.color_pair(4) if owned else curses.color_pair(3) | curses.A_BOLD if selected else 0
        add_text(panel, row, 2, text, width - 4, attr)
    add_text(panel, len(UPGRADES) + 2, 2, f"Current committed monthly burn: {money(monthly_fixed_cost(state.studio))}", width - 4)


ANALYSIS_TABS = ("Overview", "Cash Flow", "Genres", "Game History")


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
    add_text(panel, height - 3, 2, f"{game.title} | {game.topic} / {game.channel} / {lineage} | Rating {rating_text(game)}/100 | Hype {game.hype:.0f} | Monthly active players {game.monthly_players:,}", width - 4, curses.color_pair(4))
    if game.cost_history_complete:
        costs = f"COSTS: setup/store {money(game.production_cost)} + development staff {money(game.labor_cost)} + marketing {money(game.marketing_cost)} + hosting/updates {money(game.post_launch_cost)} = {money(game_total_cost(game))} total | PROFIT {money(game_profit(game))}"
    else:
        costs = "COSTS: full per-game cost tracking was not present when this older title was developed; revenue remains accurate."
    add_text(panel, height - 2, 2, costs, width - 4, curses.color_pair(4) if game.cost_history_complete and game_profit(game) >= 0 else curses.color_pair(5))


def draw_analysis(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel = screen.derwin(height - 4, width, 3, 0)
    draw_box(panel, "Studio Analytics & Franchise Statistics")
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


def footer_actions(state: GameState) -> list[tuple[str, str]]:
    if state.modal == "main":
        auto = "Auto ON" if state.studio.auto_contracts else "Auto OFF"
        return [("New", "new"), ("Jobs", "contracts"), (auto, "toggle_contracts"), ("Team", "team"), ("Up", "upgrades"), ("Games", "games"), ("<", "slower"), ("||", "pause"), (">", "faster"), ("Save", "save"), ("Quit", "quit")]
    if state.modal == "new_game":
        confirm = "Choose" if state.new_game_step == -1 else "Start" if state.new_game_step == 3 else "Next"
        actions = [("Back", "back"), (confirm, "confirm")]
        if state.new_game_step >= 0:
            actions.extend([("Random", "random_title"), ("Type", "type_title")])
        return actions + [("||", "pause"), ("Save", "save"), ("Quit", "quit")]
    if state.modal == "team":
        return [("Back", "back"), ("Applicants", "applicants"), ("Roster", "roster"), ("Hire", "hire"), ("Dismiss", "dismiss"), ("||", "pause"), ("Save", "save"), ("Quit", "quit")]
    if state.modal == "contracts":
        auto = "Auto ON" if state.studio.auto_contracts else "Auto OFF"
        return [("Back", "back"), ("Accept", "accept_contract"), (auto, "toggle_contracts"), ("||", "pause"), ("Save", "save"), ("Quit", "quit")]
    if state.modal == "games":
        games = live_games(state)
        update_label = "U:OFF"
        focus_label = "F:Focus"
        size_label = "Z:Size"
        if games:
            game = games[min(state.selected_game, len(games) - 1)]
            update_label = "U:ON" if game.auto_updates else "U:OFF"
            focus_label = f"F:{game.update_focus[:7]}"
            size_label = f"Z:{game.update_size}"
        return [("Back", "back"), (update_label, "toggle_updates"), (focus_label, "cycle_update_focus"), (size_label, "cycle_update_size"), ("Promote", "promote_game"), ("||", "pause"), ("Save", "save"), ("Quit", "quit")]
    if state.modal == "marketing":
        return [("Back", "back"), ("Buy", "buy_promotion"), ("< Game", "previous_target"), ("Game >", "next_target"), ("||", "pause"), ("Save", "save"), ("Quit", "quit")]
    if state.modal == "upgrades":
        return [("Back", "back"), ("Buy", "buy"), ("||", "pause"), ("Save", "save"), ("Quit", "quit")]
    return [("Back", "back"), ("< View", "previous_view"), ("View >", "next_view"), ("||", "pause"), ("Save", "save"), ("Quit", "quit")]


def footer_button_ranges(state: GameState) -> list[tuple[str, int, int]]:
    ranges = []
    x = 1
    for label, action in footer_actions(state):
        button = f"[{label}]"
        ranges.append((action, x, x + len(button)))
        x += len(button) + 1
    return ranges


def draw_footer(screen: curses.window, state: GameState, height: int, width: int) -> None:
    add_text(screen, height - 1, 0, " " * width, width, curses.color_pair(1))
    x = 1
    for label, _ in footer_actions(state):
        button = f"[{label}]"
        add_text(screen, height - 1, x, button, len(button), curses.color_pair(1) | curses.A_BOLD)
        x += len(button) + 1


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
    elif action == "buy_promotion":
        targets = promotion_targets(state)
        if targets:
            buy_promotion(state, targets[state.selected_promotion_target][0], state.selected_promotion)
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
        if state.new_game_step < 3:
            state.new_game_step += 1
        else:
            start_project(state)
    elif key in (8, 127, curses.KEY_BACKSPACE, 27):
        if state.new_game_step >= 0:
            state.new_game_step -= 1
        else:
            state.modal = "main"
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
        for action, start, end in footer_button_ranges(state):
            if start <= x < end:
                return perform_footer_action(state, action)
        return

    if state.modal == "main":
        if 3 <= y < 10:
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
        elif 10 <= y < 18:
            state.modal = "team" if x < width // 2 else "games"
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

    if state.modal == "games":
        games = live_games(state)
        row = y - 5
        if x <= max(48, width * 2 // 3) and row >= 0 and games:
            visible = height - 7
            start = list_start(state.selected_game, len(games), visible)
            index = start + row
            if 0 <= index < len(games):
                state.selected_game = index
                if double_click:
                    toggle_game_updates(state, games[index].game_id)
        return

    if state.modal == "marketing":
        target_width = max(32, width // 3)
        row = y - 4
        if x <= target_width:
            targets = promotion_targets(state)
            if 0 <= row < len(targets):
                state.selected_promotion_target = row
        elif 0 <= row < len(PROMOTIONS):
            state.selected_promotion = row
            if double_click:
                targets = promotion_targets(state)
                if targets:
                    buy_promotion(state, targets[state.selected_promotion_target][0], row)
        return

    if state.modal == "team":
        roster_width = max(35, width // 2)
        row = y - 4
        if row < 0:
            return
        if x <= roster_width:
            state.team_tab = 1
            visible_team = state.studio.team[: height - 6]
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
            if double_click:
                handle_new_game_key(state, 10)
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
    if key in (ord("s"), ord("S")):
        save_state(state)
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
        elif key == curses.KEY_UP:
            state.selected_promotion = (state.selected_promotion - 1) % len(PROMOTIONS)
        elif key == curses.KEY_DOWN:
            state.selected_promotion = (state.selected_promotion + 1) % len(PROMOTIONS)
        elif key in (curses.KEY_LEFT, curses.KEY_RIGHT) and targets:
            delta = -1 if key == curses.KEY_LEFT else 1
            state.selected_promotion_target = (state.selected_promotion_target + delta) % len(targets)
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
    elif state.modal == "main":
        if key in (ord("n"), ord("N")):
            open_new_game(state)
        elif key in (ord("e"), ord("E")):
            state.modal = "team"
        elif key in (ord("u"), ord("U")):
            state.modal = "upgrades"
        elif key in (ord("a"), ord("A")):
            state.modal = "analysis"
        elif key in (ord("g"), ord("G")):
            state.modal = "games"
        elif key in (ord("m"), ord("M")):
            state.modal = "marketing"
        elif key in (ord("c"), ord("C")):
            toggle_auto_contracts(state)
        elif key in (ord("j"), ord("J")):
            state.modal = "contracts"
        elif key == curses.KEY_RIGHT:
            state.time_speed_index = min(len(TIME_SPEEDS) - 1, max(1, state.time_speed_index + 1))
            state.resume_speed_index = state.time_speed_index
        elif key == curses.KEY_LEFT:
            state.time_speed_index = max(1, state.time_speed_index - 1)
            state.resume_speed_index = state.time_speed_index
    return True


def run(screen: curses.window, load_save: bool, save_path: str) -> None:
    curses.curs_set(0)
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
