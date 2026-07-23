"""Statistics page: overview, vertical cash flow, per-genre statistics,\nand the historical game catalogue, switched via the in-page tab row."""

from __future__ import annotations

import curses
from types import SimpleNamespace

from game_data import GENRES
from simulation import (
    GameState,
    expense_breakdown,
    game_profit,
    game_total_cost,
    market_chart,
    monthly_fixed_cost,
    recommended_team_size,
    revenue_breakdown,
    runway_months,
)
from ui_common import add_text, draw_box, draw_selectable_list, game_title, live_games, money, rating_text


ANALYSIS_TABS = ("Overview", "Cash Flow", "Genres", "Game Catalogue", "Market")


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
    tracked_game_costs = sum(game_total_cost(game) for game in studio.catalog)
    tracked_game_revenue = sum(game.net_revenue for game in studio.catalog)
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
        scored_games = games
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
    peak_fans = max(1, *(item["fans"] for item in statistics))
    available = width - 4
    genre_width = 24 if width >= 105 else 15
    average_width = 10 if width >= 105 else 5
    bar_width = max(5, min(30, available - genre_width - average_width - 44))
    average_label = "AVG RATING" if average_width == 10 else "AVG"
    header = f"  {'GENRE':<{genre_width}} {'FANS':>9} {'AUDIENCE':<{bar_width}} {'GAMES':>5} {average_label:>{average_width}} {'UNITS':>11} {'GAME NET':>11}"
    add_text(panel, 3, 2, header, available, curses.A_BOLD)
    rows = []
    for item in statistics:
        filled = round(bar_width * item["fans"] / peak_fans)
        average = str(item["score"]) if item["score"] else "-"
        text = f"{item['genre'][:genre_width]:<{genre_width}} {item['fans']:>9,} {'█' * filled:<{bar_width}} {item['games']:>5} {average:>{average_width}} {item['units']:>11,} {money(item['revenue']):>11}"
        rows.append((text, curses.color_pair(2)))
    draw_selectable_list(panel, rows, state.selected_stat, True, y=4, width=width - 4, visible=height - 6)


def draw_game_catalog(panel: curses.window, state: GameState) -> None:
    height, width = panel.getmaxyx()
    games = live_games(state)
    if not games:
        add_text(panel, 4, 2, "No tracked releases yet. Finish a game to create franchise statistics.", width - 4)
        return
    state.selected_stat = min(state.selected_stat, len(games) - 1)
    wide = width >= 125
    if wide:
        header = f"  {'TITLE':<28} {'GENRE':<16} {'RATING':>6} {'HYPE':>5} {'MONTHLY':>9} {'UNITS':>10} {'NET REVENUE':>11} {'TOTAL COST':>11} {'PROFIT':>11} {'BUGS':>9}"
    else:
        header = f"  {'TITLE':<18} {'RATE':>4} {'MONTHLY':>8} {'REVENUE':>10} {'PROFIT':>10} {'BUGS':>8}"
    add_text(panel, 3, 2, header, width - 4, curses.A_BOLD)
    rows = []
    for game in games:
        cost = money(game_total_cost(game))
        profit = money(game_profit(game))
        if wide:
            title = game_title(game, 28)
            text = f"{title:<28} {game.genre[:16]:<16} {rating_text(game):>6} {game.hype:>5.0f} {game.monthly_players:>9,} {game.units_sold:>10,} {money(game.net_revenue):>11} {cost:>11} {profit:>11} {game.known_bug_count:>9}"
        else:
            title = game_title(game, 18)
            text = f"{title:<18} {rating_text(game):>4} {game.monthly_players:>8,} {money(game.net_revenue):>10} {profit:>10} {game.known_bug_count:>8}"
        rows.append((text, 0))
    draw_selectable_list(panel, rows, state.selected_stat, True, y=4, width=width - 4, visible=height - 8)
    game = games[state.selected_stat]
    lineage = "original" if game.sequel_of is None else f"sequel generation {game.generation}"
    add_text(panel, height - 3, 2, f"{game_title(game)} | Theme {game.topic} / Storefront {game.channel} / {lineage} | Rating {rating_text(game)}/100 | Hype {game.hype:.0f} | Monthly active players {game.monthly_players:,}", width - 4, curses.color_pair(4))
    costs = f"COSTS: setup/store {money(game.production_cost)} + development staff {money(game.labor_cost)} + marketing {money(game.marketing_cost)} + hosting/updates {money(game.post_launch_cost)} = {money(game_total_cost(game))} total | PROFIT {money(game_profit(game))}"
    add_text(panel, height - 2, 2, costs, width - 4, curses.color_pair(4) if game_profit(game) >= 0 else curses.color_pair(5))


def draw_market_view(panel: curses.window, state: GameState) -> None:
    height, width = panel.getmaxyx()
    studio = state.studio
    own_width = max(30, width // 3)
    add_text(panel, 3, 2, "YOUR IPs", own_width - 2, curses.A_BOLD)
    ip_slots = max(1, (height - 10) // 2)
    if studio.franchises:
        for row, franchise in enumerate(studio.franchises[:ip_slots], 4):
            add_text(panel, row, 2, f"{franchise.name[:18]:<18} {franchise.rank_name:<11} r{franchise.entries}", own_width - 2, curses.color_pair(3) if franchise.rank >= 4 else 0)
    else:
        add_text(panel, 4, 2, "Release a game to found an IP.", own_width - 2)
    chart_top = 5 + ip_slots
    add_text(panel, chart_top, 2, "TOP CHART THIS WEEK", own_width - 2, curses.A_BOLD)
    chart_title_width = max(10, own_width - 14)
    for index, entry in enumerate(market_chart(state)[: max(0, height - chart_top - 2)], 1):
        entry_attr = curses.color_pair(3) | curses.A_BOLD if entry.game_id else 0
        add_text(panel, chart_top + index, 2, f"{index:>2} {entry.title[:chart_title_width]:<{chart_title_width}} {entry.weekly_units:>7,}", own_width - 2, entry_attr)
    competitors = studio.competitors
    state.selected_stat = min(state.selected_stat, max(0, len(competitors) - 1))
    x = own_width + 4
    available = width - x - 2
    header = f"  {'COMPETITOR':<22} {'TIER':<9} {'FANS':>10} {'REP':>4} {'TOOLS':>5}  IPs / ACTIVITY"
    add_text(panel, 3, x, header, available, curses.A_BOLD)
    rows = []
    for competitor in competitors:
        ips = ", ".join(item.name for item in competitor.franchises[:2]) or "-"
        activity = []
        if competitor.in_development:
            activity.append(f"dev: {competitor.in_development[0].title} ({competitor.in_development[0].weeks_left}w)")
        if competitor.recent_releases:
            activity.append(f"out: {competitor.recent_releases[0].title} {competitor.recent_releases[0].quality}/100")
        text = f"{competitor.name[:22]:<22} {competitor.tier:<9} {competitor.fanbase:>10,} {competitor.reputation:>4.0f} {competitor.tools_level:>5}  {ips}"
        rows.append((text[:available], curses.color_pair(2)))
    draw_selectable_list(panel, rows, state.selected_stat, True, y=4, x=x, width=available, visible=max(1, height - 9))
    if competitors:
        selected = competitors[state.selected_stat]
        detail_y = height - 3
        franchises = "; ".join(f"{item.name} ({item.rank_name}, {item.entries} releases)" for item in selected.franchises) or "no known IPs"
        add_text(panel, detail_y - 1, x, f"{selected.name} tools {selected.tools_level}/8 | scale {selected.size:.1f} | {selected.releases_completed} releases | IPs: {franchises}"[:available], available, curses.color_pair(4))
        add_text(panel, detail_y, x, ("Active: " + "; ".join(activity))[:available] if (activity := [f"developing {g.title} ({g.weeks_left}w)" for g in selected.in_development] + [f"recent {g.title} {g.quality}/100" for g in selected.recent_releases[:2]]) else "", available, curses.color_pair(4))


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
    elif state.analysis_view == 3:
        draw_game_catalog(panel, state)
    else:
        draw_market_view(panel, state)
