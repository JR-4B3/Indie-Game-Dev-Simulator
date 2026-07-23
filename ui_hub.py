"""Hub page: studio dashboard (finance + production command) and the\nteam/market/activity overview panels below it."""

from __future__ import annotations

import curses

from simulation import (
    SKILLS,
    GameState,
    activity_allocations,
    chart_positions,
    game_profit,
    loan_weekly_obligation,
    market_chart,
    monthly_fixed_cost,
    projected_weekly_output,
    has_research,
    research_by_key,
    recommended_team_size,
    runway_months,
    sale_for_game,
)
from ui_common import add_text, draw_box, draw_chart_rows, game_title, live_games, meter, money, rating_text


def draw_live_operations(panel: curses.window, state: GameState, panel_width: int, start_row: int) -> None:
    studio = state.studio
    active = 1 if studio.active_update else 0
    promotion_active = 1 if studio.active_promotions else 0
    add_text(panel, start_row, 2, f"Update queue {active + len(studio.update_queue)} ({active} active) | Promotion queue {len(studio.active_promotions)} ({promotion_active} active)", panel_width - 4)
    activity = f"Monthly players {sum(game.monthly_players for game in studio.catalog):,} | Weekly game sales {sum(sale.week_to_date for sale in studio.active_sales):,}"
    if studio.active_research:
        node = research_by_key(studio.active_research.node_key)
        activity += f" | R&D {node['name'] if node else studio.active_research.node_key} {studio.active_research.progress:.0%}"
    add_text(panel, start_row + 1, 2, activity, panel_width - 4)


def draw_contract_status(panel: curses.window, state: GameState, panel_width: int, start_row: int) -> None:
    studio = state.studio
    active = studio.contract
    auto_status = "ON" if studio.auto_contracts else "OFF" if has_research(studio, "contract_automation") else "LOCKED"
    add_text(panel, start_row, 2, f"[C] Auto contracts {auto_status} | Queue {len(studio.contract_queue)} | Contractor rep {studio.contractor_reputation:.1f}", panel_width - 4, curses.A_BOLD)
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
    debt = sum(loan.balance for loan in studio.loans)
    if debt:
        add_text(finance, 7, 2, f"Bank debt          {money(debt)} | {money(loan_weekly_obligation(studio))}/week", left_width - 4, curses.color_pair(5))
    else:
        add_text(finance, 7, 2, "[B] Finance desk   Loans and publisher deals", left_width - 4, curses.color_pair(2))
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
            "Bug fixing": "Bugfix",
        }
        phase = phase_labels.get(project.phase, project.phase)
        phase_width = min(10, max(8, right_width - 20))
        bar_width = max(8, right_width - 12 - phase_width)
        bar_value = project.bug_progress if project.bug_work else project.progress
        filled = round(bar_width * bar_value)
        bar = "█" * filled + "░" * (bar_width - filled)
        weekly_output = projected_weekly_output(studio, project.focus)
        remaining = max(1, round(project.remaining_work / weekly_output))
        add_text(project_panel, 1, 2, "GAME", 4, curses.A_BOLD)
        add_text(project_panel, 1, 8, project.title, right_width - 10)
        add_text(project_panel, 2, 2, f"{phase[:phase_width]} [{bar}] {bar_value:>4.0%}", right_width - 4, curses.color_pair(4))
        add_text(project_panel, 3, 2, "PLAN", 4)
        plan_text = f"Week {project.weeks} | about {remaining}w left / {project.planned_weeks}w planned"
        add_text(project_panel, 3, 8, plan_text, right_width - 10)
        if studio.contract:
            contract_share = activity_allocations(studio)["contract"]
            contract_note = f" | Contract uses {contract_share:.0%} capacity" if right_width >= 90 else f" | Job {contract_share:.0%}"
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
    return 2 + finance_height


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
            pulse = screen.derwin(catalogue_height, right_width, catalogue_y, left_width + 1)
            draw_box(pulse, "Market Pulse")
            pulse_inner = right_width - 4
            latest = live_games(state)[0] if live_games(state) else None
            add_text(pulse, 1, 2, "CHART POSITION", pulse_inner, curses.A_BOLD)
            positions = chart_positions(state)
            position = positions.get(latest.game_id) if latest else None
            if position:
                add_text(pulse, 2, 2, f"#{position} {latest.title}", pulse_inner, curses.color_pair(3) | curses.A_BOLD)
            elif latest:
                add_text(pulse, 2, 2, "Grow fans and sales to crack the charts.", pulse_inner)
            else:
                add_text(pulse, 2, 2, "Release a game to enter the charts.", pulse_inner)
            add_text(pulse, 3, 2, "TOP CHART THIS WEEK", pulse_inner, curses.A_BOLD)
            chart = market_chart(state)
            draw_chart_rows(pulse, chart, latest.game_id if latest else 0, 4, pulse_inner, max(3, catalogue_height - 5))

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
                add_text(portfolio, row, 2, f"{game_title(game)}: R{rating_text(game)} {(sale.week_to_date if sale else 0):,}/w {game.monthly_players:,} monthly", right_width - 4)
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
