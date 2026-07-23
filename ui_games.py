"""Game page family: the game catalogue table, the wide/narrow Game page,\nthe Update Planner (a catalogue mode), and Promotion Planning. All three\nshare one catalogue table and one selectable-list idiom."""

from __future__ import annotations

import curses

from simulation import (
    FRANCHISE_RANKS,
    FRANCHISE_RANK_THRESHOLDS,
    MEDIA_VENTURES,
    PROMOTIONS,
    UPDATE_FOCUSES,
    UPDATE_SIZES,
    GameState,
    activity_allocations,
    capacity_drains,
    chart_positions,
    estimated_update_delivery_weeks,
    franchise_for_game,
    game_by_id,
    game_profit,
    game_total_cost,
    genre_release_pressure,
    has_research,
    market_chart,
    market_share_multiplier,
    media_venture_available,
    monthly_fixed_cost,
    planned_update_version,
    projected_weekly_output,
    research_requirement_for_update,
    research_requirement_for_promotion,
    sale_for_game,
)
from ui_common import (
    add_text,
    catalogue_entries,
    draw_box,
    draw_lines,
    draw_selectable_list,
    game_recommendation,
    game_title,
    live_games,
    meter,
    money,
    promotion_targets,
    queue_header,
    rating_text,
    range_meter,
    wrap_text,
)


def update_jobs_for_game(state: GameState, game_id: int) -> list:
    studio = state.studio
    jobs = ([studio.active_update] if studio.active_update else []) + studio.update_queue
    return [job for job in jobs if job.game_id == game_id]


SPARK_CHARS = "▁▂▃▄▅▆▇█"


def sparkline(values: list[int]) -> str:
    if not values:
        return ""
    peak = max(1, max(values))
    return "".join(SPARK_CHARS[min(7, round(7 * value / peak))] for value in values)


def satisfaction(user_rating: float) -> tuple[str, int]:
    if user_rating >= 85:
        return "EUPHORIC", 4
    if user_rating >= 70:
        return "HAPPY", 4
    if user_rating >= 55:
        return "CONTENT", 3
    if user_rating >= 40:
        return "UNHAPPY", 5
    return "HOSTILE", 5


def rating_trend(trend: float) -> str:
    if trend > 0.2:
        return "▲"
    if trend < -0.2:
        return "▼"
    return "="


def draw_trend_bars(panel: curses.window, values: list[int], y: int, inner: int, height: int = 4, x: int = 2) -> int:
    """Weekly sales as a small bar chart: bars scale in height against the
    peak week and are separated by a space. Returns the first free row."""
    if not values:
        add_text(panel, y, x, "no weekly history yet", inner)
        return y + 1
    peak = max(1, max(values))
    column = max(1, min(3, (inner + 1) // len(values) - 1))
    shown = min(len(values), (inner + 1) // (column + 1))
    heights = [max(1, round(height * value / peak)) for value in values[-shown:]]
    for level in range(height, 0, -1):
        line = "".join(("█" * column if bar >= level else " " * column) + " " for bar in heights)
        add_text(panel, y + height - level, x, line, inner, curses.color_pair(4))
    return y + height


def draw_sales_trend_panel(panel: curses.window, selected, x: int, height: int, width: int) -> None:
    """The selected entry's weekly-sales bar chart, docked inside the
    catalogue panel and scaled to its height."""
    inner = width - 4
    add_text(panel, 1, x + 2, "SALES TREND (16 WEEKS)", inner, curses.A_BOLD)
    history = getattr(selected, "sales_history", [])
    bar_height = max(2, height - 4)
    stat_row = draw_trend_bars(panel, history, 2, inner, height=bar_height, x=x + 2)
    if history:
        all_time_peak = max(getattr(selected, "peak_weekly_sales", 0), max(history))
        add_text(panel, stat_row, x + 2, f"peak {all_time_peak:,}/w | latest {history[-1]:,}/w", inner, curses.color_pair(2))


# Layout geometry shared with the mouse handler in ui_input; hit-testing
# uses exactly the same numbers the screen drew with.


def catalogue_table_height(count: int, panel_height: int) -> int:
    """Height of the catalogue table strip: sized to content, capped by space.

    The table scrolls around the selection, so extra games never need extra
    rows: the cap reserves room for the detail panels (20 rows) and the
    economics & activity strip below (at least 12 rows), keeping them fully
    on screen when the catalogue is large or a production banner is up.
    """
    minimum_bottom = 32
    return min(15, max(7, count + 4), max(7, panel_height // 2), max(7, panel_height - minimum_bottom))


def sales_trend_width(width: int) -> int:
    """Width of the sales-trend chart docked inside the catalogue panel."""
    return max(28, width * 22 // 100)


def operations_width(width: int) -> int:
    """Width of the bottom-right Operations / Market Pulse column."""
    return max(30, width * 26 // 100)


def catalogue_table_width(width: int) -> int:
    return width - sales_trend_width(width)


def games_list_width(width: int, planner_open: bool) -> int:
    """Width of the narrow Game page's catalogue list panel."""
    return max(28, width // 3) if planner_open else max(48, width * 2 // 3)


def summary_panel_width(width: int) -> int:
    """Width of the 'Selected Game' summary panel beside planners."""
    return max(42, width * 36 // 100)


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
        scope_rows = []
        for item in UPDATE_SIZES:
            step = item["version"]
            price = f" | {money(item['price'])}" if "price" in item else ""
            requirement = research_requirement_for_update(item["name"])
            locked = bool(requirement and not has_research(studio, requirement))
            lock = " | LOCKED" if locked else ""
            scope_rows.append((f"{item['name']:<10} +{step[0]}.{step[1]:02d}.{step[2]:02d} | {item['work']:>3} work | {item['bugs']:>2} QA bugs{price}{lock}", curses.color_pair(5) if locked else 0))
        selected_scope = next((index for index, item in enumerate(UPDATE_SIZES) if item["name"] == game.update_size), 0)
        draw_selectable_list(panel, scope_rows, selected_scope, state.games_tab == 1, y=5, width=plan_width, scroll=False)
        add_text(panel, 10, 2, "UPDATE AREA", plan_width, curses.A_BOLD)
        focus_rows = [(f"{item['name']:<16} | {item['skill']} team", 0) for item in UPDATE_FOCUSES]
        selected_focus = next((index for index, item in enumerate(UPDATE_FOCUSES) if item["name"] == game.update_focus), 0)
        draw_selectable_list(panel, focus_rows, selected_focus, state.games_tab == 2, y=11, width=plan_width, scroll=False)
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
        add_text(panel, queue_row, status_x, queue_header(heading, active_count, len(studio.update_queue)), status_width, (curses.color_pair(5) if cancellation else 0) | curses.A_BOLD)
        for row, job in enumerate(queue[: max(0, panel_height - queue_row - 2)], queue_row + 1):
            status = "ACTIVE" if active and job is active else "WAITING"
            waiting_index = row - queue_row - 1 - active_count
            selected = cancellation and status == "WAITING" and waiting_index == state.selected_queue_cancellation
            marker = ">" if selected else str(row - queue_row)
            attr = curses.color_pair(5) | curses.A_BOLD if selected else curses.color_pair(4) if status == "ACTIVE" else 0
            add_text(panel, row, status_x, f"{marker}. {status:<7} {job.game_title} -> v{job.target_version} | {job.size} / {job.focus}", status_width, attr)


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
    entries = catalogue_entries(state) if include_project else [(game.game_id, game) for game in live_games(state)]
    draw_box(panel, title or f"Game Catalogue | {len(entries)} {'game' if len(entries) == 1 else 'games'}")
    if not entries:
        add_text(panel, 1, 2, "No released games yet.", panel_width - 4)
        return

    inner_width = panel_width - 4
    if panel_width >= 112:
        positions = chart_positions(state)
        title_width = max(17, min(50, inner_width - 94))
        header = f"  {'TITLE':<{title_width}} {'HYPE':>6} {'BUGS':>6} {'USER':>6} {'PRESS':>6} {'CHART':>6} {'SALES/W':>9} {'PLAYERS/M':>9} {'UNITS':>10} {'REVENUE':>12} {'PROFIT':>12}"
    else:
        title_width = 12
        genre_width = 8
        header = f"  {'TITLE':<12} {'GENRE':<8} {'RATE':>4} {'HYPE':>4} {'BUGS':>4} {'SALES':>5} {'UNITS':>5} {'MONTH':>5} {'REV':>6} {'PROFIT':>6}"
    add_text(panel, 1, 2, header, inner_width, curses.A_BOLD)

    visible = panel_height - 3
    rows = []
    for game_id, entry in entries:
        if game_id == 0:
            game_title_text = f"{entry.title} (dev)"
            genre = entry.genre
            rating = "dev"
            user = press = chart = "--"
            hype = entry.hype
            bugs = int(entry.known_defects)
            weekly = monthly = units = 0
            revenue, profit = "$0", "n/a"
        else:
            sale = sale_for_game(state.studio, game_id)
            game_title_text = game_title(entry)
            genre = entry.genre
            rating = rating_text(entry)
            user = f"{entry.user_rating:.0f}%" if entry.user_rating else "--"
            press = f"{entry.press_rating:.0f}" if entry.press_rating else "--"
            position = positions.get(game_id) if panel_width >= 112 else None
            chart = f"#{position}" if position else "--"
            hype = entry.hype
            bugs = entry.known_bug_count
            weekly = sale.week_to_date if sale else 0
            monthly = entry.monthly_players
            units = entry.units_sold
            revenue = money(entry.net_revenue)
            profit = money(game_profit(entry))
        if panel_width >= 112:
            text = f"{game_title_text[:title_width]:<{title_width}} {hype:>6.0f} {bugs:>6} {user:>6} {press:>6} {chart:>6} {weekly:>9,} {monthly:>9,} {units:>10,} {revenue:>12} {profit:>12}"
        else:
            text = f"{game_title_text[:12]:<12} {genre[:8]:<8} {rating:>4} {hype:>4.0f} {bugs:>4} {weekly:>5,} {units:>5,} {monthly:>5,} {revenue:>6} {profit:>6}"
        rows.append((text, 0))
    draw_selectable_list(panel, rows, selected_index, active, y=2, width=inner_width, visible=visible)


def draw_compact_detail(overview, updates, promotion, state: GameState, game, sale, rating_attr: int, widths: tuple[int, int, int], positions: dict) -> None:
    game_width, updates_width, promotion_width = widths
    user_text = f"{game.user_rating:.0f}%" if game.user_rating else "--"
    press_text = f"{game.press_rating:.0f}" if game.press_rating else "--"
    add_text(overview, 1, 2, f"Rating {rating_text(game)}/100 | User {user_text} | Press {press_text}", game_width - 4, rating_attr)
    add_text(overview, 2, 2, f"Hype {game.hype:.0f} | Bugs {game.known_bug_count} | Monthly {game.monthly_players:,}", game_width - 4)
    add_text(overview, 3, 2, f"Revenue {money(game.net_revenue)} | Profit {money(game_profit(game))}", game_width - 4)
    position = positions.get(game.game_id)
    add_text(overview, 4, 2, f"Chart {f'#{position}' if position else '--'} | Sales {(sale.week_to_date if sale else 0):,}/w | {sparkline(game.sales_history)}", game_width - 4)
    jobs = update_jobs_for_game(state, game.game_id)
    add_text(updates, 1, 2, f"Version v{game.version} | {len(jobs)} active/queued", updates_width - 4)
    add_text(updates, 2, 2, f"{game.update_size} / {game.update_focus}", updates_width - 4)
    add_text(updates, 3, 2, f"Next v{planned_update_version(state.studio, game, game.update_size)} | delivery {estimated_update_delivery_weeks(state.studio, game)}w | U planner", updates_width - 4)
    recommendation, recommendation_color = game_recommendation(game)
    compact_recommendation_attr = curses.color_pair(recommendation_color) if recommendation_color in (4, 5) else 0
    add_text(promotion, 1, 2, recommendation, promotion_width - 4, compact_recommendation_attr)
    add_text(promotion, 2, 2, f"Promotions {len(state.studio.active_promotions)} queued | P opens planning", promotion_width - 4)


def draw_game_overview(panel: curses.window, state: GameState, game, sale, panel_width: int, detail_height: int) -> None:
    """The single-panel overview of a released game: identity, condition,
    ratings, audience, and economics — with meters and bars instead of plain
    numbers wherever a comparison helps. Franchise IP lives in Promotion."""
    inner = panel_width - 4
    rating_attr = curses.color_pair(4) if game.score >= 70 else curses.color_pair(5) if game.score < 45 else 0
    add_text(panel, 1, 2, game_title(game), inner, curses.A_BOLD)
    genre_mix = game.genre if not game.secondary_genre or game.secondary_genre == game.genre else f"{game.genre} + {game.secondary_genre}"
    topic_mix = game.topic if not game.secondary_topic or game.secondary_topic == game.topic else f"{game.topic} + {game.secondary_topic}"
    add_text(panel, 2, 2, f"{genre_mix} | {topic_mix}", inner)
    add_text(panel, 3, 2, f"{game.target_audience} | {game.game_format}", inner)
    add_text(panel, 4, 2, f"{game.channel} | {game.scope} | {money(game.price)}", inner)
    support_hint = " | [X] change" if has_research(state.studio, "portfolio_management") else ""
    add_text(panel, 5, 2, f"Support {game.support_level.upper()}{support_hint}", inner, curses.color_pair(4) if game.support_level == "Active" else curses.color_pair(5) if game.support_level == "Sunset" else curses.color_pair(3))
    meter_width = max(10, min(18, inner - 26))
    add_text(panel, 6, 2, "CONDITION", inner, curses.A_BOLD)
    known = game.known_bug_count
    bug_hint = " | more may lurk" if game.actual_bugs > game.known_bugs + 0.5 else ""
    add_text(panel, 7, 2, f"BUGS  [{meter(min(known, 20), 20, meter_width)}] {known} known{bug_hint}", inner, curses.color_pair(5) if known else 0)
    add_text(panel, 8, 2, f"HYPE  [{meter(game.hype, 200, meter_width)}] {game.hype:>5.0f}/200", inner)
    add_text(panel, 10, 2, "CRITICS & PLAYERS", inner, curses.A_BOLD)
    user_label, user_color = satisfaction(game.user_rating)
    add_text(panel, 11, 2, f"USER  [{meter(game.user_rating, 100, meter_width)}] {game.user_rating:>4.0f}% {rating_trend(game.user_trend)} {user_label}", inner, curses.color_pair(user_color))
    add_text(panel, 12, 2, f"PRESS [{meter(game.press_rating, 100, meter_width)}] {game.press_rating:>4.0f}/100", inner)
    add_text(panel, 13, 2, f"SCORE [{meter(game.score, 100, meter_width)}] {rating_text(game):>4}/100", inner, rating_attr)
    weekly_sales = sale.week_to_date if sale else 0
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
    audience_attr = curses.color_pair(audience_color) if audience_color in (4, 5) else 0
    add_text(panel, 15, 2, "AUDIENCE HEALTH", inner, curses.A_BOLD)
    add_text(panel, 16, 2, f"{audience_status:<8} Demand {weekly_sales:,}/w | {demand_multiple:.1f}x floor", inner, audience_attr)
    add_text(panel, 17, 2, f"RET [{meter(retention, 1, meter_width)}] {retention:>5.0%} | {game.monthly_players:,}/{game.peak_monthly_players:,} peak", inner)
    next_row = 19
    segments = [segment for segment in getattr(game, "segments", []) if segment.weight > 0]
    if segments:
        from simulation import SEGMENT_NAMES, community_insight
        insight = community_insight(state.studio)
        mood_colors = {"Euphoric": 4, "Content": 4, "Skeptical": 3, "Angry": 5, "Leaving": 5}
        if insight == 0:
            average = sum(segment.satisfaction * segment.weight for segment in segments) / sum(segment.weight for segment in segments)
            mood = "Euphoric" if average >= 85 else "Content" if average >= 65 else "Skeptical" if average >= 45 else "Angry" if average >= 25 else "Leaving"
            add_text(panel, next_row, 2, f"Community mood: {mood}", inner, curses.color_pair(mood_colors[mood]))
            add_text(panel, next_row + 1, 2, "Research Market Research to read your audience.", inner, curses.color_pair(4))
            next_row += 3
        else:
            for segment in segments[: 4 if insight >= 2 else 3]:
                name = SEGMENT_NAMES.get(segment.key, segment.key)
                color = mood_colors.get(segment.mood, 0)
                if insight >= 2 and segment.note:
                    add_text(panel, next_row, 2, f"{name}: {segment.mood} {segment.note}", inner, curses.color_pair(color))
                else:
                    add_text(panel, next_row, 2, f"{name}: {segment.mood}", inner, curses.color_pair(color))
                next_row += 1
            next_row += 1
    if detail_height >= 28:
        add_text(panel, next_row, 2, "UNIT ECONOMICS", inner, curses.A_BOLD)
        total_cost = game_total_cost(game)
        cash_peak = max(game.net_revenue, total_cost, 1)
        bar_width = max(6, inner - 19)
        add_text(panel, next_row + 1, 2, f"REVENUE [{meter(game.net_revenue, cash_peak, bar_width)}] {money(game.net_revenue)}", inner, curses.color_pair(4))
        add_text(panel, next_row + 2, 2, f"COST    [{meter(total_cost, cash_peak, bar_width)}] {money(total_cost)}", inner, curses.color_pair(5))
        profit = game_profit(game)
        margin = profit / game.net_revenue * 100 if game.net_revenue else 0
        add_text(panel, next_row + 3, 2, f"Profit   {money(profit)} ({margin:+.1f}%)", inner, (curses.color_pair(4) if profit >= 0 else curses.color_pair(5)) | curses.A_BOLD)
        add_text(panel, next_row + 4, 2, f"Setup {money(game.production_cost)} | Staff {money(game.labor_cost)} | Marketing {money(game.marketing_cost)} | Live {money(game.post_launch_cost)}", inner)
        next_row += 6
    if detail_height >= next_row + 6:
        add_text(panel, next_row, 2, "RECORD", inner, curses.A_BOLD)
        add_text(panel, next_row + 1, 2, f"Released {game.release_date} | Gen {game.generation} | v{game.version}", inner)
        add_text(panel, next_row + 2, 2, f"{game.units_sold:,} lifetime units | {game.updates_released} updates | {game.dlcs_released} DLC", inner)
        next_row += 4


def project_recommendation(state: GameState, project) -> tuple[str, int]:
    studio = state.studio
    if studio.contract:
        return f"Contract work drains capacity; finishing {studio.contract.title} speeds up {project.title}.", 3
    if studio.active_update:
        return f"The {studio.active_update.game_title} update holds {studio.active_update.size} team share; production continues slower.", 3
    if project.weeks > project.planned_weeks:
        return "Behind the planned schedule; decisions and capacity decide the final quality.", 5
    if project.known_defects >= 8:
        return "Known bugs are piling up; heavy defects mean worse ratings at launch.", 5
    return "On track. Keep capacity focused on production until release.", 4


def draw_franchise_ip_block(panel: curses.window, state: GameState, game, row: int, inner: int) -> int:
    """Franchise IP summary for the selected released game. Returns next free row."""
    meter_width = max(10, min(18, inner - 26))
    add_text(panel, row, 2, "FRANCHISE IP", inner, curses.A_BOLD)
    franchise = franchise_for_game(state.studio, game)
    if franchise:
        rank = franchise.rank
        if rank < len(FRANCHISE_RANK_THRESHOLDS):
            target = FRANCHISE_RANK_THRESHOLDS[rank]
            add_text(panel, row + 1, 2, f"{franchise.name[:20]} [{meter(franchise.total_units, target, meter_width)}] {franchise.total_units:,}/{target:,} units", inner, curses.color_pair(3))
            add_text(panel, row + 2, 2, f"{franchise.rank_name} -> {FRANCHISE_RANKS[rank + 1]} | gen {game.generation} | {franchise.entries} releases", inner)
        else:
            add_text(panel, row + 1, 2, f"{franchise.name[:20]} [{'█' * meter_width}] {franchise.rank_name}", inner, curses.color_pair(3) | curses.A_BOLD)
            add_text(panel, row + 2, 2, f"gen {game.generation} | {franchise.entries} releases", inner)
        add_text(panel, row + 3, 2, f"FAT [{meter(franchise.fatigue, 120, meter_width)}] {franchise.fatigue:.0f} fatigue | {franchise.total_units:,} IP units", inner, curses.color_pair(5) if franchise.fatigue >= 90 else 0)
        genre_fans = state.studio.genre_fans.get(game.genre, 0)
        topic_fans = state.studio.topic_fans.get(game.topic, 0)
        add_text(panel, row + 4, 2, f"{game.genre} fans {genre_fans:,} | Theme affinity {topic_fans:,}", inner)
        return row + 6
    add_text(panel, row + 1, 2, f"Generation {game.generation} | no IP record", inner)
    return row + 3


def draw_promotion_panel(panel: curses.window, state: GameState, game_id: int, inner: int, detail_height: int, campaign_load: float, recommendation: str | None = None, recommendation_color: int = 0, prelaunch_hype: float | None = None, game=None) -> None:
    """The Promotion panel: recommendation, franchise IP, capacity, the running
    campaign with its progress bar, and the numbered promotion queue."""
    row = 1
    if recommendation is not None:
        recommendation_attr = curses.color_pair(recommendation_color) if recommendation_color in (4, 5) else 0
        add_text(panel, row, 2, "RECOMMENDED ACTION", inner, curses.A_BOLD)
        for offset, wrap_line in enumerate(wrap_text(recommendation, inner)[:3], 1):
            add_text(panel, row + offset, 2, wrap_line, inner, recommendation_attr)
        row += 5
    if game is not None and getattr(game, "game_id", 0):
        row = draw_franchise_ip_block(panel, state, game, row, inner)
    promotion_queue = state.studio.active_promotions
    active_promotion = promotion_queue[0] if promotion_queue else None
    promotions = [item for item in promotion_queue if item.game_id == game_id]
    unlocked_promotions = [item for item in PROMOTIONS if state.studio.reputation >= item["rep"]]
    best_promotion = max(unlocked_promotions, key=lambda item: item["hype"])
    can_afford = state.studio.cash >= best_promotion["cost"] + monthly_fixed_cost(state.studio)
    add_text(panel, row, 2, "PROMOTION", inner, curses.A_BOLD)
    add_text(panel, row + 1, 2, f"{len(promotions)} queued here | Load {campaign_load:.0%}", inner, curses.color_pair(5) if campaign_load >= 0.30 else 0)
    add_text(panel, row + 2, 2, f"Best {best_promotion['name']} +{best_promotion['hype']} hype | {money(best_promotion['cost'])} {'FUNDED' if can_afford else 'LOW CASH'}", inner, curses.color_pair(4) if can_afford else curses.color_pair(5))
    row += 4
    if prelaunch_hype is not None:
        add_text(panel, row, 2, f"Hype {prelaunch_hype:.0f}/200 pre-launch", inner, curses.color_pair(3))
        row += 2
    if active_promotion:
        progress = 1 - active_promotion.weeks_left / max(1, active_promotion.total_weeks)
        add_text(panel, row, 2, "ACTIVE CAMPAIGN", inner, curses.A_BOLD)
        add_text(panel, row + 1, 2, f"{active_promotion.name} | {active_promotion.target_title}", inner)
        add_text(panel, row + 2, 2, f"[{meter(progress, 1, max(8, inner - 16))}] {progress:.0%} | {active_promotion.weeks_left}w left", inner, curses.color_pair(4))
        row += 4
    add_text(panel, row, 2, queue_header("PROMOTION QUEUE", 1 if promotion_queue else 0, max(0, len(promotion_queue) - 1)), inner, curses.A_BOLD)
    row += 1
    if not promotion_queue:
        add_text(panel, row, 2, "No promotion running. P opens planning.", inner)
        return
    name_width = max(10, inner - 26)
    for offset, item in enumerate(promotion_queue[: max(0, detail_height - row - 2)]):
        add_text(panel, row + offset, 2, f"{offset + 1}. {item.name[:name_width]} | {item.target_title[: max(8, inner - name_width - 12)]} | {item.weeks_left}w", inner, curses.color_pair(4) if item is active_promotion else 0)


def draw_project_detail(screen: curses.window, state: GameState, project, bottom_y: int, detail_height: int, summary_height: int, width: int, overview_width: int, promotion_width: int, positions: dict, campaign_load: float) -> None:
    """Detail panels for the in-development catalogue entry: one wide Game
    panel built around the production progress bar, plus Promotion."""
    overview = screen.derwin(detail_height, overview_width, bottom_y, 0)
    promotion = screen.derwin(detail_height, promotion_width, bottom_y, overview_width + 1)
    draw_box(overview, "Game")
    draw_box(promotion, "Promotion")

    weekly_output = projected_weekly_output(state.studio, project.focus)
    remaining = max(1, round(project.remaining_work / weekly_output))
    drains = capacity_drains(state.studio)
    if detail_height < 20 or width < 150:
        add_text(overview, 1, 2, f"{project.phase} {project.progress:.0%} | week {project.weeks}/~{project.planned_weeks} | ~{remaining}w left", overview_width - 4, curses.color_pair(4))
        add_text(overview, 2, 2, f"Bugs {int(project.known_defects)} | Hype {project.hype:.0f}", overview_width - 4)
        recommendation, recommendation_color = project_recommendation(state, project)
        add_text(overview, 3, 2, recommendation, overview_width - 4, curses.color_pair(recommendation_color) if recommendation_color in (4, 5) else 0)
        add_text(overview, 4, 2, f"Forecast {project.forecast_score_low}-{project.forecast_score_high}/100 | Capacity {weekly_output:.1f} work/wk", overview_width - 4)
        add_text(promotion, 1, 2, f"Hype {project.hype:.0f}/200 pre-launch", promotion_width - 4)
        add_text(promotion, 2, 2, "P opens Promotion Planning", promotion_width - 4)
    else:
        left_inner = (overview_width - 6) // 2
        right_x = 4 + left_inner
        right_inner = overview_width - right_x - 2
        add_text(overview, 1, 2, project.title, left_inner, curses.A_BOLD)
        genre_mix = project.genre if project.secondary_genre == project.genre else f"{project.genre} + {project.secondary_genre}"
        topic_mix = project.topic if project.secondary_topic == project.topic else f"{project.topic} + {project.secondary_topic}"
        add_text(overview, 2, 2, f"{genre_mix} | {topic_mix}", left_inner)
        bar_width = max(10, left_inner - len(project.phase) - 8)
        bar_value = project.bug_progress if project.bug_work else project.progress
        add_text(overview, 3, 2, f"{project.phase} [{meter(bar_value, 1, bar_width)}] {bar_value:>4.0%}", left_inner, curses.color_pair(4))
        plan_text = f"PLAN  Week {project.weeks} | about {remaining}w left / {project.planned_weeks}w planned"
        if project.bug_work:
            plan_text += f" | {project.bugs_to_clear} bugs to clear"
        add_text(overview, 4, 2, plan_text, left_inner)
        add_text(overview, 5, 2, f"{project.scope} / {project.channel} / {money(project.price)} retail | {project.target_audience}", left_inner)
        tracked_cost = project.production_cost + project.labor_cost + project.marketing_cost
        add_text(overview, 6, 2, f"Tracked cost {money(tracked_cost)} | Marketing {money(project.marketing_cost)}", left_inner)
        add_text(overview, 8, 2, "CAPACITY", left_inner, curses.A_BOLD)
        add_text(overview, 9, 2, f"{weekly_output:.1f} work/wk | Team {len(state.studio.team)}", left_inner)
        shown_drains = drains[:4]
        if shown_drains:
            add_text(overview, 10, 2, "Drains:", left_inner)
            for offset, drain in enumerate(shown_drains):
                add_text(overview, 11 + offset, 2, drain, left_inner, curses.color_pair(5) if "contract" in drain.lower() else 0)
            condition_row = 12 + len(shown_drains)
        else:
            add_text(overview, 10, 2, "Drains: none - full capacity on this game", left_inner, curses.color_pair(4))
            condition_row = 12
        meter_width = max(8, min(16, left_inner - 26))
        add_text(overview, condition_row, 2, "CONDITION", left_inner, curses.A_BOLD)
        known = int(project.known_defects)
        add_text(overview, condition_row + 1, 2, f"BUGS  [{meter(min(known, 20), 20, meter_width)}] {known} known", left_inner, curses.color_pair(5) if known else 0)
        add_text(overview, condition_row + 2, 2, f"HYPE  [{meter(project.hype, 200, meter_width)}] {project.hype:>5.0f}/200", left_inner)
        bets_row = condition_row + 4
        add_text(overview, bets_row, 2, "CREATIVE BETS", left_inner, curses.A_BOLD)
        add_text(overview, bets_row + 1, 2, f"{project.creative_primary} + {project.creative_secondary}", left_inner)
        add_text(overview, bets_row + 2, 2, project.release_strategy, left_inner)
        decisions_row = bets_row + 4
        if detail_height >= decisions_row + 3:
            add_text(overview, decisions_row, 2, "DECISIONS", left_inner, curses.A_BOLD)
            made = project.decisions_made[-3:] if project.decisions_made else ["none yet"]
            for offset, note in enumerate(made):
                add_text(overview, decisions_row + 1 + offset, 2, note, left_inner, curses.color_pair(2))

        recommendation, recommendation_color = project_recommendation(state, project)
        recommendation_attr = curses.color_pair(recommendation_color) if recommendation_color in (4, 5) else 0
        add_text(overview, 1, right_x, "RECOMMENDED ACTION", right_inner, curses.A_BOLD)
        for wrap_row, wrap_line in enumerate(wrap_text(recommendation, right_inner)[:3], 2):
            add_text(overview, wrap_row, right_x, wrap_line, right_inner, recommendation_attr)
        add_text(overview, 6, right_x, "LAUNCH FORECAST", right_inner, curses.A_BOLD)
        meter_right = max(8, min(14, right_inner - 20))
        add_text(overview, 7, right_x, f"SCORE [{range_meter(project.forecast_score_low, project.forecast_score_high, 100, meter_right)}] {project.forecast_score_low}-{project.forecast_score_high}", right_inner)
        add_text(overview, 8, right_x, f"confidence {project.forecast_confidence}% | research narrows this", right_inner, curses.color_pair(2))
        add_text(overview, 10, right_x, "AUDIENCE", right_inner, curses.A_BOLD)
        add_text(overview, 11, right_x, f"{project.forecast_audience_low:,}-{project.forecast_audience_high:,} interested", right_inner)
        add_text(overview, 12, right_x, f"{project.forecast_competitors_low}-{project.forecast_competitors_high} rival launches", right_inner)
        add_text(overview, 14, right_x, "MARKET POSITION", right_inner, curses.A_BOLD)
        market_shift = project.market_score - project.market_score_start
        shift_hint = ""
        shift_attr = 0
        if abs(market_shift) >= 8:
            shift_hint = f" | {'cooling' if market_shift < 0 else 'heating'} since greenlight"
            shift_attr = curses.color_pair(5) if market_shift < 0 else curses.color_pair(4)
        open_market = market_share_multiplier(state, project.genre, project.channel)
        add_text(overview, 15, right_x, f"Market fit {project.market_score}/100 | {project.competitors} rivals{shift_hint}", right_inner, shift_attr)
        add_text(overview, 16, right_x, f"Genre pressure {genre_release_pressure(state.studio, project.genre):.1f}/3.0", right_inner, curses.color_pair(5) if genre_release_pressure(state.studio, project.genre) >= 1.5 else 0)
        add_text(overview, 17, right_x, f"Store demand {open_market:.0%} open on {project.channel}", right_inner, curses.color_pair(5) if open_market < 0.55 else 0)

        draw_promotion_panel(promotion, state, 0, promotion_width - 4, detail_height, campaign_load, prelaunch_hype=project.hype)
    if summary_height >= 5:
        draw_economics_strip(screen, state, project.title, bottom_y + detail_height, summary_height, width, positions, campaign_load)


def draw_economics_strip(screen: curses.window, state: GameState, title: str, summary_y: int, summary_height: int, width: int, positions: dict, campaign_load: float) -> None:
    econ_width = max(58, width * 2 // 5)
    col_width = (econ_width - 6) // 2
    right_x = econ_width + 3
    right_width = width - right_x - 2
    panel = screen.derwin(summary_height, width, summary_y, 0)
    draw_box(panel, f"Catalogue Economics & Activity | {title}")
    catalog = state.studio.catalog
    tracked_revenue = sum(item.net_revenue for item in catalog)
    tracked_cost = sum(game_total_cost(item) for item in catalog)
    tracked_profit = tracked_revenue - tracked_cost
    tracked_margin = tracked_profit / tracked_revenue * 100 if tracked_revenue else 0
    rated_games = catalog
    average_rating = sum(item.score for item in rated_games) / len(rated_games) if rated_games else None
    average_rating_attr = curses.color_pair(4) if average_rating is not None and average_rating >= 70 else curses.color_pair(5) if average_rating is not None and average_rating < 45 else 0
    best_rank = min(positions.values(), default=None)
    best_game = game_by_id(state.studio, min(positions, key=positions.get)) if positions else None
    best_chart = f"#{best_rank} {best_game.title}" if best_rank and best_game else "--"
    scale_lines = [
        ("CATALOGUE SCALE", curses.A_BOLD),
        (f"Games {len(catalog)} | Avg rating {f'{average_rating:.1f}' if average_rating is not None else 'n/a'}", average_rating_attr),
        (f"Weekly sales   {sum(item.week_to_date for item in state.studio.active_sales):,}", 0),
        (f"Monthly players {sum(item.monthly_players for item in catalog):,}", 0),
        (f"Lifetime units  {sum(item.units_sold for item in catalog):,}", 0),
    ]
    return_lines = [
        ("CATALOGUE RETURNS", curses.A_BOLD),
        (f"Revenue {money(sum(item.net_revenue for item in catalog))} | Cost {money(tracked_cost)}", 0),
        (f"Profit {money(tracked_profit)} ({tracked_margin:+.0f}%)", (curses.color_pair(4) if tracked_profit >= 0 else curses.color_pair(5)) | curses.A_BOLD),
        (f"Best chart {best_chart}", curses.color_pair(3) if best_rank else 0),
        (f"Live ops {1 if state.studio.active_update else 0}a/{len(state.studio.update_queue)}q | Promos {len(state.studio.active_promotions)}", curses.color_pair(5) if campaign_load >= 0.30 else 0),
    ]
    draw_lines(panel, scale_lines[: summary_height - 2], 1, 2, col_width)
    draw_lines(panel, return_lines[: summary_height - 2], 1, 4 + col_width, econ_width - col_width - 6)
    for divider_row in range(1, summary_height - 1):
        add_text(panel, divider_row, econ_width + 1, "|", 1, curses.color_pair(2))

    related_logs = [message for message in state.logs if title in message]
    add_text(panel, 1, right_x, "RECENT EVENTS", right_width, curses.A_BOLD)
    journal_slots = min(len(related_logs), max(1, summary_height - 3))
    if not related_logs:
        add_text(panel, 2, right_x, "[INFO] No journal entries recorded for this game yet.", right_width, curses.color_pair(2))
    for row, message in enumerate(related_logs[:journal_slots], 2):
        lower_message = message.lower()
        if "released update" in lower_message or "finished" in lower_message:
            event, attr = "UPDATE", 0
        elif "started" in lower_message and ("push" in lower_message or "campaign" in lower_message or "outreach" in lower_message or "placement" in lower_message or "festival" in lower_message or "event" in lower_message or "showcase" in lower_message):
            event, attr = "PROMO", 0
        elif "topped the charts" in lower_message or "released" in lower_message or "launched" in lower_message:
            event, attr = "LAUNCH", curses.color_pair(3) | curses.A_BOLD if "topped the charts" in lower_message else 0
        elif "off" in lower_message or "cannot" in lower_message or "failed" in lower_message:
            event, attr = "ALERT", curses.color_pair(5) | curses.A_BOLD
        elif "changed" in lower_message or "continuous updates" in lower_message:
            event, attr = "PLAN", 0
        else:
            event, attr = "INFO", 0
        add_text(panel, row, right_x, f"[{event:<6}] {message}", right_width, attr)


def draw_update_planner_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    draw_games_screen(screen, state, width, height)


def draw_games_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel_height = height - 4
    games = live_games(state)
    project = state.studio.current_project
    planner_open = state.modal == "update_planner"
    entries = catalogue_entries(state) if not planner_open else [(game.game_id, game) for game in games]
    game_count = f"{len(entries)} {'game' if len(entries) == 1 else 'games'}"
    top = 2
    if width < 120:
        list_width = games_list_width(width, planner_open)
        detail_width = width - list_width - 1
        games_panel = screen.derwin(panel_height, list_width, top, 0)
        detail = screen.derwin(panel_height, detail_width, top, list_width + 1)
        draw_box(games_panel, f"Game Catalogue | {game_count}")
        draw_box(detail, "Update Planner" if planner_open else "Development /Game")
        if not entries:
            add_text(games_panel, 1, 2, "No released games yet.", list_width - 4, curses.A_BOLD)
            add_text(detail, 1, 2, "BUILD A MARKET POSITION", detail_width - 4, curses.A_BOLD)
            add_text(detail, 3, 2, "Mix modern genres and themes.", detail_width - 4)
            add_text(detail, 4, 2, "Choose an audience and creative bets.", detail_width - 4)
            add_text(detail, 5, 2, "Test demand, rivals, risk, and runway.", detail_width - 4)
            add_text(detail, 7, 2, "Press N to open the concept room.", detail_width - 4, curses.color_pair(4))
            return
        if planner_open:
            state.selected_game = min(state.selected_game, len(games) - 1)
            rows = [(game_title(game), 0) for game in games]
            draw_selectable_list(games_panel, rows, state.selected_game, state.games_tab == 0, width=list_width - 4, visible=panel_height - 2)
            draw_update_planner(detail, state, games[state.selected_game], detail_width, panel_height)
            return
        state.selected_game = min(state.selected_game, len(entries) - 1)
        visible = panel_height - 2
        rows = []
        for entry_id, entry in entries:
            if entry_id == 0:
                rows.append((f"{entry.title[:20]:<20} dev {entry.phase} {entry.progress:.0%}", curses.color_pair(3)))
            else:
                sale = sale_for_game(state.studio, entry.game_id)
                title = game_title(entry, 20)
                rows.append((f"{title:<20} R{rating_text(entry):>3} {(sale.week_to_date if sale else 0):>5,}/w {entry.monthly_players:>6,} monthly", 0))
        draw_selectable_list(games_panel, rows, state.selected_game, True, width=list_width - 4, visible=visible)
        selected_id, selected = entries[state.selected_game]
        if selected_id == 0:
            add_text(detail, 1, 2, selected.title, detail_width - 4, curses.A_BOLD)
            genre_mix = selected.genre if selected.secondary_genre == selected.genre else f"{selected.genre} + {selected.secondary_genre}"
            add_text(detail, 2, 2, genre_mix, detail_width - 4)
            add_text(detail, 3, 2, f"{selected.target_audience} | {selected.game_format}", detail_width - 4)
            weekly_output = projected_weekly_output(state.studio, selected.focus)
            remaining = max(1, round(selected.remaining_work / weekly_output))
            bar_value = selected.bug_progress if selected.bug_work else selected.progress
            add_text(detail, 5, 2, f"{selected.phase} [{meter(bar_value, 1, max(8, detail_width - 16))}] {bar_value:.0%}", detail_width - 4, curses.color_pair(4))
            add_text(detail, 6, 2, f"week {selected.weeks} / ~{selected.planned_weeks} planned | ~{remaining}w left", detail_width - 4)
            add_text(detail, 7, 2, f"Capacity {weekly_output:.1f} work/wk | Drains: {', '.join(capacity_drains(state.studio)) or 'none'}", detail_width - 4)
            add_text(detail, 9, 2, f"Known bugs {int(selected.known_defects)} | Hype {selected.hype:.0f}", detail_width - 4)
            add_text(detail, 10, 2, f"Forecast {selected.forecast_score_low}-{selected.forecast_score_high}/100 | confidence {selected.forecast_confidence}%", detail_width - 4)
            add_text(detail, 12, 2, "P opens Promotion Planning", detail_width - 4, curses.color_pair(4))
            return
        game = selected
        sale = sale_for_game(state.studio, game.game_id)
        add_text(detail, 1, 2, game_title(game), detail_width - 4, curses.A_BOLD)
        genre_mix = game.genre if not game.secondary_genre or game.secondary_genre == game.genre else f"{game.genre} + {game.secondary_genre}"
        add_text(detail, 2, 2, genre_mix, detail_width - 4)
        add_text(detail, 3, 2, f"{game.target_audience} | {game.game_format}", detail_width - 4)
        add_text(detail, 4, 2, f"Market fit {game.market_score}/100 | {game.competitors} launch rivals", detail_width - 4)
        user_text = f"{game.user_rating:.0f}%" if game.user_rating else "--"
        press_text = f"{game.press_rating:.0f}" if game.press_rating else "--"
        add_text(detail, 6, 2, f"Rating {rating_text(game)}/100 | User {user_text} | Press {press_text}", detail_width - 4)
        position = chart_positions(state).get(game.game_id)
        add_text(detail, 7, 2, f"Chart {f'#{position}' if position else '--'} | Hype {game.hype:.0f}/200", detail_width - 4)
        add_text(detail, 8, 2, f"Monthly players {game.monthly_players:,} | Sales {(sale.week_to_date if sale else 0):,}/week", detail_width - 4)
        add_text(detail, 9, 2, f"Known bugs {game.known_bug_count} | DLC {game.dlcs_released}", detail_width - 4, curses.color_pair(5) if game.known_bug_count else 0)
        add_text(detail, 11, 2, f"{game.update_size} / {game.update_focus} | U opens planner", detail_width - 4)
        return

    trend_width = sales_trend_width(width)
    table_width = width - trend_width
    catalog_height = panel_height if not entries else catalogue_table_height(len(entries), panel_height)
    games_panel = screen.derwin(catalog_height, width, top, 0)
    if not entries:
        draw_box(games_panel, f"Game Catalogue | {game_count}")
        add_text(games_panel, 1, 2, "THE GAME PORTFOLIO", table_width - 4, curses.A_BOLD)
        add_text(games_panel, 3, 2, "Your first release should be a deliberate market position, not a genre/theme dice roll.", table_width - 4)
        add_text(games_panel, 5, 2, "1  MIX        Combine a primary genre and theme with a second influence.", table_width - 4)
        add_text(games_panel, 6, 2, "2  POSITION   Pick the people you serve and the way they will play together.", table_width - 4)
        add_text(games_panel, 7, 2, "3  COMMIT     Make creative bets with visible benefits and production costs.", table_width - 4)
        add_text(games_panel, 8, 2, "4  VALIDATE   Read demand, competing releases, project risk, runway, and capability gates.", table_width - 4)
        add_text(games_panel, 10, 2, "Small games teach cheaply. Large and online games multiply both the audience and the failure cost.", table_width - 4, curses.color_pair(5))
        add_text(games_panel, 12, 2, "Press N to enter the concept room.", table_width - 4, curses.color_pair(4) | curses.A_BOLD)
        return
    if planner_open:
        state.selected_game = min(state.selected_game, len(games) - 1)
    else:
        state.selected_game = min(state.selected_game, len(entries) - 1)
    draw_game_catalogue_table(games_panel, state, table_width, catalog_height, state.selected_game, not planner_open or state.games_tab == 0, include_project=not planner_open, title=f"Game Catalogue | {game_count}")
    for divider_row in range(1, catalog_height - 1):
        add_text(games_panel, divider_row, table_width - 1, "|", 1, curses.color_pair(2))
    draw_sales_trend_panel(games_panel, entries[state.selected_game][1], table_width, catalog_height, trend_width)

    bottom_y = top + catalog_height
    bottom_height = panel_height - catalog_height
    summary_height = min(7, max(0, bottom_height - 20))
    detail_height = bottom_height - summary_height
    side_width = operations_width(width)
    game_width = (width - side_width - 2) // 2
    updates_width = (width - game_width - 2) // 2
    promotion_width = width - game_width - updates_width - 2
    if planner_open:
        game = games[state.selected_game]
        sale = sale_for_game(state.studio, game.game_id)
        summary_width = summary_panel_width(width)
        planner_width = width - summary_width - 1
        summary = screen.derwin(bottom_height, summary_width, bottom_y, 0)
        planner = screen.derwin(bottom_height, planner_width, bottom_y, summary_width + 1)
        draw_box(summary, "Selected Game")
        draw_box(planner, f"Update Planner & Queue | {1 if state.studio.active_update else 0} active | {len(state.studio.update_queue)} waiting")
        add_text(summary, 1, 2, game_title(game), summary_width - 4, curses.A_BOLD)
        add_text(summary, 2, 2, f"{game.genre} / {game.topic} | Rating {rating_text(game)}/100", summary_width - 4)
        add_text(summary, 3, 2, f"Hype {game.hype:.0f} | Monthly players {game.monthly_players:,}", summary_width - 4)
        add_text(summary, 4, 2, f"Sales {(sale.week_to_date if sale else 0):,}/week | Updates shipped {game.updates_released}", summary_width - 4)
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
    selected_id, selected = entries[state.selected_game]
    positions = chart_positions(state)
    lead_promotion = state.studio.active_promotions[0] if state.studio.active_promotions else None
    campaign_load = lead_promotion.team_share if lead_promotion else 0.0
    if selected_id == 0:
        draw_project_detail(screen, state, selected, bottom_y, detail_height, summary_height, width, width - promotion_width - 1, promotion_width, positions, campaign_load)
        return
    game = selected
    sale = sale_for_game(state.studio, game.game_id)
    overview = screen.derwin(detail_height, game_width, bottom_y, 0)
    updates = screen.derwin(detail_height, updates_width, bottom_y, game_width + 1)
    promotion = screen.derwin(detail_height, promotion_width, bottom_y, game_width + updates_width + 2)
    draw_box(overview, "Game")
    draw_box(updates, "Updates")
    draw_box(promotion, "Promotion")

    rating_attr = curses.color_pair(4) if game.score >= 70 else curses.color_pair(5) if game.score < 45 else 0
    size = next((item for item in UPDATE_SIZES if item["name"] == game.update_size), UPDATE_SIZES[1])
    focus = next((item for item in UPDATE_FOCUSES if item["name"] == game.update_focus), UPDATE_FOCUSES[0])
    if detail_height < 20 or width < 150:
        draw_compact_detail(overview, updates, promotion, state, game, sale, rating_attr, (game_width, updates_width, promotion_width), positions)
        if summary_height >= 5:
            draw_economics_strip(screen, state, game.title, bottom_y + detail_height, summary_height, width, positions, campaign_load)
        return

    draw_game_overview(overview, state, game, sale, game_width, detail_height)

    updates_inner = updates_width - 4
    jobs = update_jobs_for_game(state, game.game_id)
    active_job = state.studio.active_update if state.studio.active_update and state.studio.active_update.game_id == game.game_id else None
    target_version = active_job.target_version if active_job else planned_update_version(state.studio, game, game.update_size)
    status = "ACTIVE" if active_job else "QUEUED" if jobs else "READY"
    add_text(updates, 1, 2, f"{game.title} -> v{target_version}", updates_inner, curses.A_BOLD)
    add_text(updates, 2, 2, f"Status {status}", updates_inner, (curses.color_pair(4) if active_job else curses.color_pair(3)) | curses.A_BOLD)
    add_text(updates, 3, 2, f"Focus {game.update_focus} ({focus['skill']} skill)", updates_inner)
    add_text(updates, 4, 2, f"Scope {game.update_size} | +{size['version'][0]}.{size['version'][1]:02d}.{size['version'][2]:02d} step", updates_inner)
    update_load = activity_allocations(state.studio)["update"] if active_job else 0
    add_text(updates, 5, 2, f"Cost {money(size['cost'])} | Team load {update_load:.0%}", updates_inner)
    rating_factor = max(0.10, (game.score / 100) ** 2)
    expected_hype = size["hype"] * focus["hype"] * rating_factor
    expected_players = round((game.monthly_players * 0.20 + game.units_sold * 0.012) * size["sales"] * focus["players"] * rating_factor)
    add_text(updates, 6, 2, f"Forecast +{expected_hype:.1f} hype | ~{expected_players:,} returning", updates_inner)
    eta = estimated_update_delivery_weeks(state.studio, game)
    progress = active_job.progress * 100 if active_job else 0
    phase = active_job.phase if active_job else "waiting for queue"
    add_text(updates, 8, 2, f"[{meter(progress, 100, max(8, updates_inner - 16))}] {progress:.0f}%", updates_inner, curses.color_pair(4) if active_job else 0)
    remaining = max(1, round(eta * (1 - progress / 100))) if active_job else eta
    if active_job:
        add_text(updates, 9, 2, f"~{remaining}w left of ~{eta}w delivery | {phase}", updates_inner)
    else:
        add_text(updates, 9, 2, f"waiting for queue | ~{eta}w delivery", updates_inner)
    update_queue = ([state.studio.active_update] if state.studio.active_update else []) + state.studio.update_queue
    active_count = 1 if state.studio.active_update else 0
    add_text(updates, 11, 2, queue_header("UPDATE QUEUE", active_count, len(state.studio.update_queue)), updates_inner, curses.A_BOLD)
    if not update_queue:
        add_text(updates, 12, 2, "Queue an update with U.", updates_inner)
    shown_jobs = update_queue[: max(0, detail_height - 18)]
    job_title_width = max(10, updates_inner - 22)
    for row, job in enumerate(shown_jobs, 12):
        is_active = bool(state.studio.active_update and job is state.studio.active_update)
        add_text(updates, row, 2, f"{row - 11}. {job.game_title[:job_title_width]} | {job.size} / {job.focus}", updates_inner, curses.color_pair(4) if is_active else 0)
    history_row = 13 + len(shown_jobs)
    if history_row < detail_height - 1:
        add_text(updates, history_row, 2, f"Release history: {game.updates_released} updates | {game.dlcs_released} DLC", updates_inner)

    recommendation, recommendation_color = game_recommendation(game)
    draw_promotion_panel(promotion, state, game.game_id, promotion_width - 4, detail_height, campaign_load, recommendation=recommendation, recommendation_color=recommendation_color, game=game)

    if summary_height >= 5:
        draw_economics_strip(screen, state, game.title, bottom_y + detail_height, summary_height, width, positions, campaign_load)


def draw_marketing_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel_height = height - 4
    state.marketing_tab = max(0, min(2, state.marketing_tab))
    targets = promotion_targets(state)
    catalog_height = catalogue_table_height(len(targets), panel_height)
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
    summary_width = summary_panel_width(width)
    option_width = width - summary_width - 1
    summary_panel = screen.derwin(bottom_height, summary_width, bottom_y, 0)
    options_panel = screen.derwin(bottom_height, option_width, bottom_y, summary_width + 1)
    draw_box(summary_panel, "Selected Game")
    selected_id, selected_title, selected_hype, selected_status = targets[state.selected_promotion_target]
    selected_game = game_by_id(state.studio, selected_id) if selected_id else None
    franchise = franchise_for_game(state.studio, selected_game) if selected_game else None
    if state.marketing_tab == 2:
        draw_box(options_panel, f"Merch & Media | {franchise.name + ' IP' if franchise else 'no IP selected'}")
    else:
        draw_box(options_panel, f"Promotion Planning & Queue | Reputation {state.studio.reputation:.1f}")
    add_text(summary_panel, 1, 2, selected_title, summary_width - 4, curses.A_BOLD)
    add_text(summary_panel, 2, 2, selected_status, summary_width - 4)
    add_text(summary_panel, 3, 2, f"Hype {selected_hype:.0f}/200", summary_width - 4)
    if franchise:
        add_text(summary_panel, 4, 2, f"IP {franchise.name} | {franchise.rank_name} rank", summary_width - 4, curses.color_pair(3) | curses.A_BOLD)
    else:
        add_text(summary_panel, 4, 2, "No IP yet; releasing founds one.", summary_width - 4)
    target_queue = [item for item in state.studio.active_promotions if item.game_id == selected_id]
    active = state.studio.active_promotions[0] if state.studio.active_promotions else None
    target_active = 1 if active in target_queue else 0
    add_text(summary_panel, 5, 2, f"Promotion queue  {target_active} active | {len(target_queue) - target_active} waiting", summary_width - 4, curses.A_BOLD)
    for row, item in enumerate(target_queue[: max(0, bottom_height - 12)], 6):
        status = "ACTIVE" if item is active else "WAITING"
        add_text(summary_panel, row, 2, f"{status:<7} {item.name} | {item.weeks_left}w", summary_width - 4, curses.color_pair(4) if item is active else 0)
    venture_row = 6 + max(0, min(len(target_queue), bottom_height - 12)) + 1
    if franchise:
        add_text(summary_panel, venture_row, 2, f"IP awareness {franchise.awareness:.0f} | fatigue {franchise.fatigue:.0f}", summary_width - 4)
        add_text(summary_panel, venture_row + 1, 2, f"IP releases {franchise.entries} | units {franchise.total_units:,.0f}", summary_width - 4)
        active_ventures = [item for item in state.studio.media_ventures if item.franchise_id == franchise.franchise_id]
        if active_ventures and venture_row + 2 < bottom_height - 1:
            add_text(summary_panel, venture_row + 2, 2, "Merch & Media", summary_width - 4, curses.A_BOLD)
            for offset, item in enumerate(active_ventures[: max(0, bottom_height - venture_row - 4)], 1):
                add_text(summary_panel, venture_row + 2 + offset, 2, f"{item.name} | {item.weeks_left}w left", summary_width - 4, curses.color_pair(4))

    if state.marketing_tab == 2:
        state.selected_venture = min(state.selected_venture, len(MEDIA_VENTURES) - 1)
        option_inner = option_width - 4
        add_text(options_panel, 1, 2, f"  {'VENTURE':<22} {'COST':>10} {'WEEKS':>6} {'REQ RANK':<12} EFFECT", option_inner, curses.A_BOLD)
        venture_rows = []
        for venture in MEDIA_VENTURES:
            if franchise is None:
                status = "release a game in this IP first"
            else:
                status = media_venture_available(state.studio, franchise, venture)
            locked = bool(status)
            required = FRANCHISE_RANKS[venture["rank"]]
            text = f"{venture['name'][:22]:<22} {money(venture['cost']):>10} {venture['weeks']:>6} {required:<12} {status or venture['effect']}"
            venture_rows.append((text[:option_inner], curses.color_pair(5) if locked else 0))
        draw_selectable_list(options_panel, venture_rows, state.selected_venture, True, y=2, width=option_width - 4, scroll=False, highlight_wins=False)
        rank_line = "Merch at Niche rank, conventions at Popular, films and series at Famous."
        add_text(options_panel, len(MEDIA_VENTURES) + 3, 2, rank_line, option_inner, curses.color_pair(2))
        active_ventures = state.studio.media_ventures
        if active_ventures:
            heading_row = len(MEDIA_VENTURES) + 5
            add_text(options_panel, heading_row, 2, "ACTIVE VENTURES", option_inner, curses.A_BOLD)
            for row, item in enumerate(active_ventures[: max(0, bottom_height - heading_row - 2)], heading_row + 1):
                add_text(options_panel, row, 2, f"{item.name} | {item.franchise_name} | {item.weeks_left}w left | earned {money(item.revenue)}", option_inner, curses.color_pair(4))
        return

    state.selected_promotion = min(state.selected_promotion, len(PROMOTIONS) - 1)
    option_inner = option_width - 4
    option_expanded = option_inner >= 80
    promotion_name_width = 24 if option_expanded else max(12, option_inner - 22)
    effect_width = max(10, option_inner - promotion_name_width - 55)
    option_header = f"  {'PROMOTION':<{promotion_name_width}} {'COST':>10} {'WEEKS':>5} {'HYPE CAP':>9} {'TEAM':>6} {'REQ REP':>7} {'EFFECT':<{effect_width}}" if option_expanded else f"  {'PROMOTION':<{promotion_name_width}} {'COST':>9} {'STATUS':>10}"
    add_text(options_panel, 1, 2, option_header, option_inner, curses.A_BOLD)
    option_rows = []
    for promotion in PROMOTIONS:
        research_key = research_requirement_for_promotion(promotion["key"])
        research_locked = bool(research_key and not has_research(state.studio, research_key))
        locked = state.studio.reputation < promotion["rep"] or research_locked
        if option_expanded:
            text = f"{promotion['name'][:promotion_name_width]:<{promotion_name_width}} {money(promotion['cost']):>10} {promotion['weeks']:>5} +{promotion['hype']:<3}/{promotion['ceiling']:<3} {promotion['team']:>6.0%} {promotion['rep']:>7} {promotion['effect'][:effect_width]:<{effect_width}}"
        else:
            status = "RESEARCH" if research_locked else f"REP {promotion['rep']}" if locked else "AVAILABLE"
            text = f"{promotion['name'][:promotion_name_width]:<{promotion_name_width}} {money(promotion['cost']):>9} {status:>10}"
        option_rows.append((text, curses.color_pair(5) if locked else 0))
    draw_selectable_list(options_panel, option_rows, state.selected_promotion, state.marketing_tab == 1, y=2, width=option_width - 4, scroll=False, highlight_wins=False)
    queue = state.studio.active_promotions
    queue_row = len(PROMOTIONS) + 3
    team_load = queue[0].team_share if queue else 0.0
    if queue_row < bottom_height - 1:
        cancellation = state.queue_cancellation == "promotion"
        heading = "CANCEL QUEUED PROMOTION" if cancellation else "PROMOTION QUEUE"
        add_text(options_panel, queue_row, 2, queue_header(heading, 1 if queue else 0, max(0, len(queue) - 1), suffix=f"Team load {team_load:.0%}"), option_width - 4, (curses.color_pair(5) if cancellation else 0) | curses.A_BOLD)
        for row, item in enumerate(queue[: max(0, bottom_height - queue_row - 2)], queue_row + 1):
            status = "ACTIVE" if row == queue_row + 1 else "WAITING"
            waiting_index = row - queue_row - 2
            selected = cancellation and status == "WAITING" and waiting_index == state.selected_queue_cancellation
            marker = ">" if selected else str(row - queue_row)
            attr = curses.color_pair(5) | curses.A_BOLD if selected else curses.color_pair(4) if status == "ACTIVE" else 0
            add_text(options_panel, row, 2, f"{marker}. {status:<7} {item.name} | {item.target_title} | {item.weeks_left}w", option_width - 4, attr)
