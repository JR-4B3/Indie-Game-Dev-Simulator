"""Game page family: the game catalogue table, the wide/narrow Game page,\nthe Update Planner (a catalogue mode), and Promotion Planning. All three\nshare one catalogue table and one selectable-list idiom."""

from __future__ import annotations

import curses

from game_data import GENRES
from simulation import (
    FRANCHISE_RANKS,
    MEDIA_VENTURES,
    PROMOTIONS,
    UPDATE_FOCUSES,
    UPDATE_SIZES,
    GameState,
    capacity_drains,
    estimated_update_delivery_weeks,
    franchise_for_game,
    game_by_id,
    game_profit,
    game_total_cost,
    media_venture_available,
    monthly_fixed_cost,
    planned_update_version,
    projected_weekly_output,
    sale_for_game,
)
from ui_common import (
    add_text,
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
    wrap_text,
)


def update_jobs_for_game(state: GameState, game_id: int) -> list:
    studio = state.studio
    jobs = ([studio.active_update] if studio.active_update else []) + studio.update_queue
    return [job for job in jobs if job.game_id == game_id]


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


PRODUCTION_BANNER_HEIGHT = 5


def draw_production_banner(panel: curses.window, state: GameState, width: int) -> None:
    """The in-development project's progress and, critically, what is slowing
    it down — contract work, promotions, updates, training, live titles."""
    studio = state.studio
    project = studio.current_project
    draw_box(panel, f"In Production | {project.title}")
    weekly_output = projected_weekly_output(studio, project.focus)
    remaining = max(1, round((project.total_work - project.work_done) / weekly_output))
    bar_width = max(10, min(48, width // 4))
    add_text(panel, 1, 2, f"{project.phase} [{meter(project.progress, 1, bar_width)}] {project.progress:.0%} | week {project.weeks} / ~{project.planned_weeks} planned | ~{remaining}w left", width - 4, curses.color_pair(4))
    drains = capacity_drains(studio)
    drain_text = " | ".join(drains) if drains else "none - full capacity"
    add_text(panel, 2, 2, f"Capacity {weekly_output:.1f} work/wk | Drains: {drain_text}", width - 4, curses.color_pair(5) if studio.contract else 0)
    add_text(panel, 3, 2, f"Known bugs {int(project.known_defects)} | Hype {project.hype:.0f} | {project.scope} / {project.channel}", width - 4)


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
            scope_rows.append((f"{item['name']:<10} +{step[0]}.{step[1]:02d}.{step[2]:02d} | {item['work']:>3} work | {item['bugs']:>2} QA bugs{price}", 0))
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
    rows = []
    for game_id, entry in entries:
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
            weekly = sale.week_to_date if sale else 0
            monthly = entry.monthly_players
            units = entry.units_sold
            revenue = money(entry.net_revenue)
            profit = money(game_profit(entry)) if entry.cost_history_complete else "n/a"
        if panel_width >= 120:
            text = f"{game_title_text[:title_width]:<{title_width}} {genre[:genre_width]:<{genre_width}} {rating:>6} {hype:>6.0f} {bugs:>6} {weekly:>9,} {units:>10,} {monthly:>15,} {revenue:>12} {profit:>12}"
        else:
            text = f"{game_title_text[:12]:<12} {genre[:8]:<8} {rating:>4} {hype:>4.0f} {bugs:>4} {weekly:>5,} {units:>5,} {monthly:>5,} {revenue:>6} {profit:>6}"
        rows.append((text, 0))
    draw_selectable_list(panel, rows, selected_index, active, y=2, width=inner_width, visible=visible)


def draw_update_planner_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    draw_games_screen(screen, state, width, height)


def draw_games_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel_height = height - 4
    games = live_games(state)
    planner_open = state.modal == "update_planner"
    game_count = f"{len(games)} {'game' if len(games) == 1 else 'games'}"
    top = 2
    if state.studio.current_project:
        banner = screen.derwin(PRODUCTION_BANNER_HEIGHT, width, top, 0)
        draw_production_banner(banner, state, width)
        top += PRODUCTION_BANNER_HEIGHT
        panel_height -= PRODUCTION_BANNER_HEIGHT
    if width < 120:
        list_width = games_list_width(width, planner_open)
        detail_width = width - list_width - 1
        games_panel = screen.derwin(panel_height, list_width, top, 0)
        detail = screen.derwin(panel_height, detail_width, top, list_width + 1)
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
        rows = []
        for game in games:
            sale = sale_for_game(state.studio, game.game_id)
            if planner_open:
                text = game_title(game)
            else:
                title = game_title(game, 20)
                text = f"{title:<20} R{rating_text(game):>3} {(sale.week_to_date if sale else 0):>5,}/w {game.monthly_players:>6,} monthly"
            rows.append((text, 0))
        draw_selectable_list(games_panel, rows, state.selected_game, not planner_open or state.games_tab == 0, width=list_width - 4, visible=visible)
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
        add_text(detail, 7, 2, f"Monthly players {game.monthly_players:,} | Sales {(sale.week_to_date if sale else 0):,}/week", detail_width - 4)
        add_text(detail, 8, 2, f"Known bugs {game.known_bug_count} | DLC {game.dlcs_released}", detail_width - 4, curses.color_pair(5) if game.known_bug_count else 0)
        add_text(detail, 10, 2, f"{game.update_size} / {game.update_focus} | U opens planner", detail_width - 4)
        return

    catalog_height = panel_height if not games else catalogue_table_height(len(games), panel_height)
    games_panel = screen.derwin(catalog_height, width, top, 0)
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
    bottom_y = top + catalog_height
    bottom_height = panel_height - catalog_height
    detail_height = bottom_height if bottom_height < 24 else 20
    summary_height = bottom_height - detail_height
    first_width = width // 3
    second_width = width // 3
    third_width = width - first_width - second_width - 2
    if planner_open:
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
    commercial = screen.derwin(detail_height, first_width, bottom_y, 0)
    live_ops = screen.derwin(detail_height, second_width, bottom_y, first_width + 1)
    strategy = screen.derwin(detail_height, third_width, bottom_y, first_width + second_width + 2)
    draw_box(commercial, "Commercial Performance")
    draw_box(live_ops, "Live Operations")
    draw_box(strategy, "Advisor")

    rating_attr = curses.color_pair(4) if game.score >= 70 else curses.color_pair(5) if game.score < 45 else 0
    size = next((item for item in UPDATE_SIZES if item["name"] == game.update_size), UPDATE_SIZES[1])
    focus = next((item for item in UPDATE_FOCUSES if item["name"] == game.update_focus), UPDATE_FOCUSES[0])
    if detail_height < 20:
        add_text(commercial, 1, 2, f"Rating {rating_text(game)}/100 | Hype {game.hype:.0f} | Bugs {game.known_bug_count}", first_width - 4, rating_attr)
        add_text(commercial, 2, 2, f"Sales {(sale.week_to_date if sale else 0):,}/w | Monthly {game.monthly_players:,}", first_width - 4)
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
    add_text(commercial, 7, 2, f"Weekly sales             {(sale.week_to_date if sale else 0):,}", first_width - 4)
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
    add_text(live_ops, 12, 2, queue_header("UPDATE QUEUE", active_count, len(state.studio.update_queue)), second_width - 4, curses.A_BOLD)
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
    genre_fans = state.studio.genre_fans.get(game.genre, 0)
    topic_fans = state.studio.topic_fans.get(game.topic, 0)
    unlocked_promotions = [item for item in PROMOTIONS if state.studio.reputation >= item["rep"]]
    best_promotion = max(unlocked_promotions, key=lambda item: item["hype"])
    can_afford = state.studio.cash >= best_promotion["cost"] + monthly_fixed_cost(state.studio)
    campaign_load = active_promotion.team_share if active_promotion else 0.0
    recommendation_attr = curses.color_pair(recommendation_color) if recommendation_color in (4, 5) else 0
    audience_attr = curses.color_pair(audience_color) if audience_color in (4, 5) else 0
    add_text(strategy, 1, 2, "RECOMMENDED ACTION", third_width - 4, curses.A_BOLD)
    for wrap_row, wrap_line in enumerate(wrap_text(recommendation, third_width - 4)[:2], 2):
        add_text(strategy, wrap_row, 2, wrap_line, third_width - 4, recommendation_attr)
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
        right_x = left_width + 3
        right_width = width - right_x - 2
        panel = screen.derwin(summary_height, width, summary_y, 0)
        draw_box(panel, f"Catalogue Economics & Activity | {game_title(game)}")
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
            (f"Average release rating    {average_rating:.1f}/100" if average_rating is not None else "Average release rating    n/a", average_rating_attr),
            (f"Current weekly sales      {sum(item.week_to_date for item in state.studio.active_sales):,}", 0),
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
        draw_lines(panel, economics_lines[: summary_height - 2], 1, 2, left_width - 4)
        for divider_row in range(1, summary_height - 1):
            add_text(panel, divider_row, left_width + 1, "|", 1, curses.color_pair(2))

        related_logs = [message for message in state.logs if game.title in message]
        add_text(panel, 1, right_x, "RECENT EVENTS", right_width, curses.A_BOLD)
        journal_slots = min(len(related_logs), max(1, summary_height - 4))
        if not related_logs:
            add_text(panel, 2, right_x, "[INFO] No journal entries recorded for this game yet.", right_width, curses.color_pair(2))
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
            add_text(panel, row, right_x, f"[{event:<6}] {message}", right_width, attr)


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
    effect_width = max(10, option_inner - promotion_name_width - 51)
    option_header = f"  {'PROMOTION':<{promotion_name_width}} {'COST':>10} {'WEEKS':>5} {'HYPE':>6} {'TEAM':>6} {'REQ REP':>7} {'EFFECT':<{effect_width}}" if option_expanded else f"  {'PROMOTION':<{promotion_name_width}} {'COST':>9} {'STATUS':>10}"
    add_text(options_panel, 1, 2, option_header, option_inner, curses.A_BOLD)
    option_rows = []
    for promotion in PROMOTIONS:
        locked = state.studio.reputation < promotion["rep"]
        if option_expanded:
            text = f"{promotion['name'][:promotion_name_width]:<{promotion_name_width}} {money(promotion['cost']):>10} {promotion['weeks']:>5} {promotion['hype']:>6} {promotion['team']:>6.0%} {promotion['rep']:>7} {promotion['effect'][:effect_width]:<{effect_width}}"
        else:
            status = f"REP {promotion['rep']}" if locked else "AVAILABLE"
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
