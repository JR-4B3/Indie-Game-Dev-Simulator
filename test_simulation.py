import curses
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from main import CTRL_S, draw_dashboard, draw_footer, draw_games_screen, draw_header, draw_main_content, draw_team_screen, footer_button_ranges, footer_layout, handle_key, handle_mouse, handle_new_game_key, open_new_game, parse_args, team_panel_widths
from simulation import (
    START_DATE,
    TIME_LABELS,
    TIME_SPEEDS,
    GameState,
    accept_contract,
    accept_contract_offer,
    advance_game,
    bump_version,
    buy_promotion,
    contract_weekly_output,
    cycle_game_update_size,
    estimated_update_weeks,
    game_profit,
    game_total_cost,
    hire_candidate,
    load_game,
    monthly_fixed_cost,
    queue_game_update,
    recommended_team_size,
    refresh_applicants,
    save_game,
    start_project,
    toggle_auto_contracts,
)


def advance(state: GameState, weeks: int) -> None:
    for _ in range(weeks):
        state.clock.current_date += timedelta(days=7)
        state.clock.week += 1
        advance_game(state, 1)


def rendered_games_text(state: GameState, width: int, height: int) -> list[str]:
    screen = MagicMock()
    windows = []

    def create_window(panel_height, panel_width, _y, _x):
        window = MagicMock()
        window.getmaxyx.return_value = (panel_height, panel_width)
        windows.append(window)
        return window

    screen.derwin.side_effect = create_window
    with patch("main.curses.color_pair", return_value=0):
        draw_games_screen(screen, state, width, height)
    return [call.args[2] for window in windows for call in window.addstr.call_args_list]


def rendered_team_text(state: GameState, width: int, height: int) -> list[str]:
    screen = MagicMock()
    windows = []

    def create_window(panel_height, panel_width, _y, _x):
        window = MagicMock()
        window.getmaxyx.return_value = (panel_height, panel_width)
        windows.append(window)
        return window

    screen.derwin.side_effect = create_window
    with patch("main.curses.color_pair", return_value=0):
        draw_team_screen(screen, state, width, height)
    return [call.args[2] for window in windows for call in window.addstr.call_args_list]


def rendered_main_content_text(state: GameState, width: int, height: int) -> list[str]:
    screen = MagicMock()
    windows = []

    def create_window(panel_height, panel_width, _y, _x):
        window = MagicMock()
        window.getmaxyx.return_value = (panel_height, panel_width)
        windows.append(window)
        return window

    screen.derwin.side_effect = create_window
    with patch("main.curses.color_pair", return_value=0):
        draw_dashboard(screen, state, width)
        draw_main_content(screen, state, width, height, 11)
    return [call.args[2] for window in windows for call in window.addstr.call_args_list]


class SimulationTests(unittest.TestCase):
    def test_footer_highlights_shortcuts_and_right_aligns_global_controls(self) -> None:
        state = GameState()
        layout = footer_layout(state, 190)
        positions = {action: (label, x) for label, action, x in layout}

        self.assertEqual(positions["contracts"][0], "[J]obs")
        self.assertEqual(positions["marketing"][0], "[M]arketing")
        self.assertEqual(positions["analysis"][0], "[S]tatistics")
        self.assertEqual(positions["settings"][0], "[Esc]Settings")
        self.assertNotIn("toggle_contracts", positions)
        self.assertGreater(positions["slower"][1], positions["games"][1] + len(positions["games"][0]))
        self.assertLess(positions["settings"][1], positions["save"][1])
        self.assertEqual(positions["save"][0], "[Ctrl+S]Save")
        self.assertEqual(positions["quit"][0], "[Q]Quit")
        self.assertEqual(positions["quit"][1] + len(positions["quit"][0]), 189)

        screen = MagicMock()
        screen.getmaxyx.return_value = (50, 190)
        with patch("main.curses.color_pair", return_value=0):
            draw_footer(screen, state, 50, 190)
        shortcut = next(call for call in screen.addstr.call_args_list if call.args[2] == "[J]")
        word = next(call for call in screen.addstr.call_args_list if call.args[2] == "obs")
        self.assertTrue(shortcut.args[3] & curses.A_BOLD)
        self.assertFalse(word.args[3] & curses.A_BOLD)

    def test_dashboard_uses_balanced_team_catalogue_finance_and_contract_panels(self) -> None:
        state = GameState()
        advance(state, 4)

        wide_text = rendered_main_content_text(state, 190, 50)
        compact_text = rendered_main_content_text(state, 74, 40)

        self.assertTrue(any(" Finance " in line for line in wide_text))
        self.assertTrue(any("RECENT ACTIVITY" in line for line in wide_text))
        self.assertTrue(any("Production Command" in line for line in wide_text))
        self.assertTrue(any(line.strip() == "OPERATIONS" for line in wide_text))
        self.assertTrue(any("Update queue" in line and "Active promotions" in line and "|" in line for line in wide_text))
        self.assertTrue(any(line.strip() == "CONTRACTS" for line in wide_text))
        self.assertTrue(any("[C] Auto contracts" in line for line in wide_text))
        self.assertTrue(any("TOP SKILL" in line and "PERSONALITY" in line for line in wide_text))
        self.assertTrue(any("REVENUE" in line and "PROFIT" in line and "BUGS" in line for line in wide_text))
        self.assertFalse(any("Recent Financial Trend" in line for line in wide_text))
        self.assertTrue(any("Recent Financial Trend" in line for line in compact_text))
        self.assertTrue(any(" Contracts " in line for line in compact_text))
        self.assertTrue(any("CONTRACT STATUS" in line for line in compact_text))

        screen = MagicMock()
        screen.derwin.side_effect = lambda panel_height, panel_width, _y, _x: MagicMock(**{"getmaxyx.return_value": (panel_height, panel_width)})
        with patch("main.curses.color_pair", return_value=0):
            draw_dashboard(screen, state, 190)
            draw_main_content(screen, state, 190, 50, 11)
        panel_calls = [call.args for call in screen.derwin.call_args_list]
        finance = next(args for args in panel_calls if args[2:] == (3, 0))
        production = next(args for args in panel_calls if args[2] == 3 and args[3] > 0)
        team = next(args for args in panel_calls if args[2:] == (19, 0))
        catalogue = next(args for args in panel_calls if args[2] == 19 and args[3] > 0)
        self.assertEqual(finance[0], production[0])
        self.assertEqual(team[0], catalogue[0])

    def test_production_command_uses_game_and_plan_hierarchy(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        self.assertTrue(accept_contract(state))
        advance(state, 2)

        text = rendered_main_content_text(state, 190, 50)

        self.assertIn("GAME", text)
        self.assertIn(state.studio.current_project.title, text)
        self.assertIn("PLAN", text)
        self.assertTrue(any("Week 2" in line and "w left /" in line and "w planned" in line for line in text))
        self.assertTrue(any("Contract is cutting capacity by 45%" in line for line in text))
        self.assertFalse(any(line == "Contract is cutting project capacity by 45%" for line in text))

    def test_production_progress_keeps_fixed_bar_and_visible_percentage(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        project = state.studio.current_project
        bar_lengths = set()

        for progress in (0.05, 0.34, 0.76, 0.95, 1.0):
            project.work_done = project.total_work * progress
            text = rendered_main_content_text(state, 190, 50)
            progress_line = next(line for line in text if "[" in line and line.rstrip().endswith("%"))
            if progress == 0.05:
                self.assertTrue(progress_line.startswith("Prototype ["))
            bar_lengths.add(len(progress_line.split("[", 1)[1].split("]", 1)[0]))
            self.assertTrue(progress_line.rstrip().endswith(f"{progress:.0%}"))

        project.work_done = project.total_work * 0.34
        self.assertTrue(accept_contract(state))
        toggle_auto_contracts(state)
        text = rendered_main_content_text(state, 190, 50)
        progress_line = next(line for line in text if "[" in line and line.rstrip().endswith("%"))
        bar_lengths.add(len(progress_line.split("[", 1)[1].split("]", 1)[0]))
        self.assertTrue(progress_line.rstrip().endswith("34%"))
        self.assertEqual(bar_lengths, {72})

    def test_expanded_team_roster_uses_spare_width_and_height(self) -> None:
        state = GameState()
        self.assertTrue(hire_candidate(state))
        state.team_tab = 1

        text = rendered_team_text(state, 190, 50)

        self.assertTrue(any("SALARY/YR" in line and "COST/MO" in line for line in text))
        self.assertTrue(any("TEAM OVERVIEW" in line for line in text))
        self.assertTrue(any("TEAM CAPABILITY" in line for line in text))
        self.assertTrue(any("SELECTED TEAM MEMBER" in line for line in text))

    def test_header_uses_game_dev_sim_branding(self) -> None:
        state = GameState()
        state.clock.week = 429
        screen = MagicMock()
        screen.getmaxyx.return_value = (36, 120)

        with patch("main.curses.color_pair", return_value=0):
            draw_header(screen, state, 120)

        title = screen.addstr.call_args_list[0].args[2]
        self.assertIn("INDIE STUDIO GAME DEV SIM", title)
        self.assertTrue(title.rstrip().endswith("INDIE STUDIO GAME DEV SIM"))
        self.assertIn(f"{state.clock.current_date:%d %b %y}", title[:31])
        self.assertIn("Y 9", title)
        self.assertIn("W 13", title)
        self.assertNotIn("YEAR", title)
        self.assertNotIn("WEEK", title)
        self.assertNotIn("/52", title)
        self.assertIn("> 1x", title)

    def test_header_speed_indicator_matches_four_speed_levels(self) -> None:
        self.assertEqual(TIME_SPEEDS, (0.0, 1.0, 2.0, 4.0, 8.0))
        self.assertEqual(TIME_LABELS, ("||", "> 1x", ">> 2x", ">>> 4x", ">>>> 8x"))

        progress_ends = set()
        metric_starts = set()
        for speed_index, label in enumerate(TIME_LABELS):
            state = GameState()
            state.time_speed_index = speed_index
            screen = MagicMock()
            screen.getmaxyx.return_value = (36, 160)
            with patch("main.curses.color_pair", return_value=0):
                draw_header(screen, state, 160)
            self.assertIn(label, screen.addstr.call_args_list[0].args[2])
            status_line = screen.addstr.call_args_list[1].args[2]
            progress_ends.add(status_line.index("]"))
            metric_starts.add(status_line.index("| Team"))
        self.assertEqual(progress_ends, {36})
        self.assertEqual(len(metric_starts), 1)

        state = GameState()
        state.clock.week = 429
        screen = MagicMock()
        screen.getmaxyx.return_value = (50, 160)
        with patch("main.curses.color_pair", return_value=0):
            draw_header(screen, state, 160)
        top_line = screen.addstr.call_args_list[0].args[2]
        date_block = f"{state.clock.current_date:%d %b %Y}  Y 9  W 13  {TIME_LABELS[state.time_speed_index]:<8}"
        date_start = top_line.index(date_block)
        self.assertEqual(date_start + (len(date_block) - 1) / 2, (1 + 36) / 2)

    def test_promotion_panels_use_tab_and_contextual_up_down_navigation(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)
        self.assertTrue(start_project(state))
        state.modal = "marketing"
        state.marketing_tab = 0

        handle_key(state, curses.KEY_DOWN)
        self.assertEqual(state.selected_promotion_target, 1)
        self.assertEqual(state.selected_promotion, 0)
        handle_key(state, 9)
        handle_key(state, curses.KEY_DOWN)
        self.assertEqual(state.marketing_tab, 1)
        self.assertEqual(state.selected_promotion_target, 1)
        self.assertEqual(state.selected_promotion, 1)

        target_before = state.selected_promotion_target
        handle_key(state, curses.KEY_RIGHT)
        self.assertEqual(state.selected_promotion_target, target_before)
        handle_key(state, 9)
        handle_key(state, 10)
        self.assertEqual(state.marketing_tab, 1)

        labels = {action: label for label, action, _ in footer_layout(state, 190)}
        self.assertEqual(labels["switch_marketing_tab"], "[Tab]Targets")
        self.assertEqual(labels["buy_promotion"], "[Enter]Buy")

    def test_new_game_uses_tab_for_panels_and_enter_to_greenlight(self) -> None:
        state = GameState()
        state.modal = "new_game"
        state.new_game_step = 0
        genre_before = state.selected_genre

        handle_new_game_key(state, curses.KEY_DOWN)
        self.assertNotEqual(state.selected_genre, genre_before)
        handle_new_game_key(state, 9)
        self.assertEqual(state.new_game_step, 1)
        labels = {action: label for label, action, _ in footer_layout(state, 190)}
        self.assertEqual(labels["next_new_game_panel"], "[Tab]Storefront")
        self.assertEqual(labels["new_game_selection"], "[Up/Down]Theme")
        self.assertEqual(labels["confirm"], "[Enter]Greenlight")

        handle_new_game_key(state, 10)
        self.assertIsNotNone(state.studio.current_project)
        self.assertEqual(state.modal, "main")

    def test_compact_main_footer_keeps_every_mouse_target_visible(self) -> None:
        ranges = footer_button_ranges(GameState(), 74)

        self.assertLessEqual(ranges[-1][2], 74)
        self.assertEqual([action for action, _, _ in ranges][1:6], ["contracts", "marketing", "team", "upgrades", "games"])

        states = []
        for step in range(4):
            state = GameState(modal="new_game", new_game_step=step)
            states.append(state)
        states.extend([GameState(modal="marketing", marketing_tab=0), GameState(modal="marketing", marketing_tab=1)])
        for state in states:
            self.assertLessEqual(footer_button_ranges(state, 74)[-1][2], 74)

        game_state = GameState(modal="games")
        self.assertTrue(start_project(game_state))
        game_state.studio.current_project.work_done = game_state.studio.current_project.total_work - 1
        advance(game_state, 1)
        self.assertLessEqual(footer_button_ranges(game_state, 100)[-1][2], 100)

    def test_statistics_settings_control_save_and_quit_shortcuts(self) -> None:
        state = GameState()
        handle_key(state, ord("s"))
        self.assertEqual(state.modal, "analysis")

        state.modal = "main"
        handle_key(state, 27)
        self.assertEqual(state.modal, "settings")
        handle_key(state, 27)
        self.assertEqual(state.modal, "main")

        with tempfile.TemporaryDirectory() as directory:
            state.save_path = str(Path(directory) / "ctrl-save.json")
            self.assertTrue(handle_key(state, CTRL_S))
            self.assertTrue(Path(state.save_path).is_file())
        self.assertFalse(handle_key(state, ord("q")))
        state.modal = "new_game"
        state.naming_game = True
        state.draft_title = ""
        self.assertTrue(handle_key(state, ord("q")))
        self.assertEqual(state.draft_title, "q")
        state.naming_game = False
        self.assertFalse(handle_key(state, ord("Q")))

    def test_wide_games_screen_exposes_detailed_management_sections(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)

        text = rendered_games_text(state, 200, 60)

        self.assertTrue(any("Game Catalogue | 1 game" in line for line in text))
        self.assertTrue(any("Live Operations" in line for line in text))
        self.assertTrue(any("Promotion Planning" in line for line in text))
        self.assertTrue(any("CURRENT PLAN" in line for line in text))
        self.assertTrue(any("PROMOTION CAPACITY" in line for line in text))
        self.assertTrue(any("CATALOGUE RETURNS" in line for line in text))
        self.assertTrue(any("CURRENT SNAPSHOT" in line for line in text))
        self.assertFalse(any("permanently on sale" in line for line in text))

        game = state.studio.catalog[0]
        queue_game_update(state, game.game_id)
        queue_game_update(state, game.game_id)
        text = rendered_games_text(state, 200, 60)
        self.assertTrue(any("UPDATE QUEUE (1 waiting)" in line for line in text))
        self.assertTrue(any(game.title in line and "-> v" in line for line in text))
        self.assertFalse(any(line == "CONTROLS" for line in text))

    def test_games_screen_still_renders_at_minimum_terminal_size(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)

        text = rendered_games_text(state, 74, 24)

        self.assertTrue(any("Game Catalogue | 1 game" in line for line in text))
        self.assertTrue(any("Monthly players" in line for line in text))

    def test_new_studio_starts_today_with_real_overhead(self) -> None:
        state = GameState()

        self.assertEqual(state.clock.current_date, START_DATE)
        self.assertEqual(len(state.studio.team), 1)
        self.assertEqual(len(state.studio.applicants), 6)
        self.assertGreater(monthly_fixed_cost(state.studio), 3_000)

    def test_project_uses_variable_work_and_releases_to_store(self) -> None:
        state = GameState()

        self.assertTrue(start_project(state))
        setup_cash = state.studio.cash
        self.assertGreater(state.studio.current_project.planned_weeks, 8)
        advance(state, 40)

        self.assertIsNone(state.studio.current_project)
        self.assertEqual(state.studio.released_games, 1)
        self.assertGreaterEqual(state.studio.followers, 40)
        self.assertLess(state.studio.cash, setup_cash)

    def test_testing_and_players_reveal_only_part_of_real_bug_count(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        advance(state, 5)
        project = state.studio.current_project
        self.assertGreater(project.defects, 0)
        self.assertGreaterEqual(project.known_defects, 0)
        self.assertLess(project.known_defects, project.defects)

        project.work_done = project.total_work - 1
        advance(state, 1)
        game = state.studio.catalog[0]
        self.assertLess(game.known_bugs, game.actual_bugs)
        game.actual_bugs = 20
        game.known_bugs = 1
        game.reported_bug_count = 1
        state.studio.active_sales[0].weekly_units = 10_000

        advance(state, 1)

        self.assertGreater(game.known_bugs, 1)
        self.assertLess(game.known_bugs, game.actual_bugs)
        self.assertTrue(any("complained online" in message for message in state.logs))

    def test_bug_fix_update_removes_existing_bugs_but_can_miss_hidden_ones(self) -> None:
        state = GameState()
        start_project(state)
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)
        game = state.studio.catalog[0]
        game.actual_bugs = 20
        game.known_bugs = 10
        game.reported_bug_count = 10
        game.update_size = "Hotfix"
        game.update_focus = "Bug fixes"
        queue_game_update(state, game.game_id)
        state.studio.active_update.work_done = state.studio.active_update.required_work
        state.studio.active_update.bugs_fixed = state.studio.active_update.bugs_found

        advance(state, 1)

        self.assertAlmostEqual(game.actual_bugs, 16.2)
        self.assertLess(game.known_bugs, 10)
        self.assertLess(game.known_bugs, game.actual_bugs)

        game.actual_bugs = 0
        game.known_bugs = 0
        game.reported_bug_count = 0
        queue_game_update(state, game.game_id)
        state.studio.active_update.work_done = state.studio.active_update.required_work
        state.studio.active_update.bugs_fixed = state.studio.active_update.bugs_found
        advance(state, 1)
        self.assertEqual(game.actual_bugs, 0)

    def test_legacy_campaign_name_can_finish_saved_project(self) -> None:
        state = GameState()
        state.selected_marketing = 4
        self.assertTrue(start_project(state))
        state.studio.current_project.marketing_name = "Campaign"
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1

        advance(state, 1)

        self.assertIsNone(state.studio.current_project)
        self.assertEqual(state.studio.released_games, 1)

    def test_game_profit_includes_development_staff_marketing_and_live_costs(self) -> None:
        state = GameState()
        state.selected_marketing = 2
        self.assertTrue(start_project(state))
        advance(state, 40)
        game = state.studio.catalog[0]

        self.assertTrue(game.cost_history_complete)
        self.assertGreater(game.production_cost, 0)
        self.assertGreater(game.labor_cost, 0)
        self.assertEqual(game.marketing_cost, 4_000)
        self.assertGreater(game.post_launch_cost, 0)
        self.assertEqual(
            game_total_cost(game),
            game.production_cost + game.labor_cost + game.marketing_cost + game.post_launch_cost,
        )
        self.assertEqual(game_profit(game), game.net_revenue - game_total_cost(game))

    def test_released_game_keeps_selling_at_evergreen_floor(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        advance(state, 40)
        game = state.studio.catalog[0]
        sale = next(item for item in state.studio.active_sales if item.game_id == game.game_id)

        advance(state, 30)

        self.assertIn(sale, state.studio.active_sales)
        self.assertGreaterEqual(sale.weekly_units, sale.evergreen_units)
        self.assertGreater(game.units_sold, 0)

    def test_queued_update_ships_and_raises_live_game_activity(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        advance(state, 40)
        game = state.studio.catalog[0]
        self.assertTrue(queue_game_update(state, game.game_id))

        advance(state, 30)

        self.assertGreaterEqual(game.updates_released, 1)
        self.assertEqual(game.version, "1.00.10")
        self.assertIsNone(state.studio.active_update)

    def test_update_size_changes_estimated_development_length(self) -> None:
        state = GameState()
        start_project(state)
        advance(state, 40)
        game = state.studio.catalog[0]
        patch_weeks = estimated_update_weeks(state.studio, game)

        cycle_game_update_size(state, game.game_id)
        cycle_game_update_size(state, game.game_id)
        expansion_weeks = estimated_update_weeks(state.studio, game)

        self.assertEqual(game.update_size, "Expansion")
        self.assertGreater(expansion_weeks, patch_weeks * 4)

    def test_update_scopes_use_fixed_version_steps_and_carry(self) -> None:
        self.assertEqual(bump_version("1.00.00", "Hotfix"), "1.00.01")
        self.assertEqual(bump_version("1.00.00", "Patch"), "1.00.10")
        self.assertEqual(bump_version("1.00.00", "Content"), "1.01.00")
        self.assertEqual(bump_version("1.00.00", "Expansion"), "1.10.00")
        self.assertEqual(bump_version("1.99.95", "Patch"), "2.00.05")

    def test_update_queue_snapshots_plans_and_requires_bug_fixing(self) -> None:
        state = GameState()
        start_project(state)
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)
        game = state.studio.catalog[0]
        game.update_size = "Hotfix"
        game.update_focus = "Balance pass"
        self.assertTrue(queue_game_update(state, game.game_id))
        game.update_size = "Content"
        game.update_focus = "New content"
        self.assertTrue(queue_game_update(state, game.game_id))

        active = state.studio.active_update
        self.assertEqual((active.size, active.focus, active.target_version), ("Hotfix", "Balance pass", "1.00.01"))
        self.assertEqual((state.studio.update_queue[0].size, state.studio.update_queue[0].focus), ("Content", "New content"))
        self.assertEqual(state.studio.update_queue[0].target_version, "1.01.01")

        active.work_done = active.required_work - 0.01
        advance(state, 1)
        self.assertEqual(game.version, "1.00.00")
        self.assertEqual(state.studio.active_update.phase, "Bug fixing")
        self.assertEqual(state.studio.active_update.bugs_fixed, 0)

        advance(state, 1)
        self.assertEqual(game.version, "1.00.01")
        self.assertEqual(game.updates_released, 1)
        self.assertEqual(state.studio.active_update.size, "Content")

    def test_update_queue_and_versions_survive_save_load(self) -> None:
        state = GameState()
        start_project(state)
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)
        game = state.studio.catalog[0]
        game.update_size = "Patch"
        queue_game_update(state, game.game_id)
        game.update_size = "Expansion"
        queue_game_update(state, game.game_id)
        state.studio.active_update.work_done = 12

        with tempfile.TemporaryDirectory() as directory:
            state.save_path = str(Path(directory) / "updates.json")
            save_game(state)
            loaded = load_game(state.save_path)

        self.assertEqual(loaded.studio.catalog[0].version, "1.00.00")
        self.assertEqual(loaded.studio.active_update.target_version, "1.00.10")
        self.assertEqual(loaded.studio.active_update.work_done, 12)
        self.assertEqual(loaded.studio.update_queue[0].target_version, "1.10.10")

    def test_old_update_plans_migrate_with_paused_and_automatic_progress(self) -> None:
        state = GameState()
        for _ in range(2):
            start_project(state)
            state.studio.current_project.work_done = state.studio.current_project.total_work - 1
            advance(state, 1)
        first, second = state.studio.catalog
        first.updates_released = 3
        first.update_progress = 25
        second.update_progress = 50
        second.auto_updates = True

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "old-updates.json"
            state.save_path = str(path)
            save_game(state)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["studio"].pop("active_update")
            data["studio"].pop("update_queue")
            data["studio"].pop("next_update_id")
            for game_data in data["studio"]["catalog"]:
                game_data.pop("version")
            path.write_text(json.dumps(data), encoding="utf-8")
            loaded = load_game(str(path))

        self.assertEqual(loaded.studio.active_update.game_id, second.game_id)
        self.assertEqual(loaded.studio.catalog[0].version, "1.00.30")
        self.assertEqual(loaded.studio.active_update.target_version, "1.00.10")
        self.assertAlmostEqual(loaded.studio.active_update.work_done, loaded.studio.active_update.required_work * 0.50)
        self.assertEqual(loaded.studio.update_queue[0].game_id, first.game_id)
        self.assertAlmostEqual(loaded.studio.update_queue[0].work_done, loaded.studio.update_queue[0].required_work * 0.25)
        self.assertTrue(all(not game.auto_updates for game in loaded.studio.catalog))

    def test_expanded_update_planner_shows_scope_area_qa_and_queue(self) -> None:
        state = GameState()
        start_project(state)
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)
        state.modal = "games"
        state.games_tab = 1
        queue_game_update(state, state.studio.catalog[0].game_id)
        queue_game_update(state, state.studio.catalog[0].game_id)

        wide_text = rendered_games_text(state, 200, 60)
        compact_text = rendered_games_text(state, 74, 24)

        self.assertTrue(any("Update Planner & Queue" in line for line in wide_text))
        self.assertTrue(any("Hotfix" in line and "+0.00.01" in line for line in wide_text))
        self.assertTrue(any("UPDATE AREA" in line for line in wide_text))
        self.assertTrue(any("mandatory QA" in line for line in wide_text))
        self.assertTrue(any("Update Planner" in line for line in compact_text))
        self.assertTrue(any("fix" in line and "bugs" in line for line in compact_text))
        self.assertTrue(any("QUEUE (1)" in line for line in compact_text))

    def test_rating_controls_hype_decay_and_player_retention(self) -> None:
        low = GameState()
        high = GameState()
        for state in (low, high):
            start_project(state)
            state.studio.current_project.work_done = state.studio.current_project.total_work - 1
            advance(state, 1)
            game = state.studio.catalog[0]
            sale = state.studio.active_sales[0]
            game.hype = 120
            sale.weekly_units = 500
        low.studio.catalog[0].score = low.studio.active_sales[0].score = 25
        high.studio.catalog[0].score = high.studio.active_sales[0].score = 90

        advance(low, 8)
        advance(high, 8)

        self.assertGreater(high.studio.active_sales[0].weekly_units, low.studio.active_sales[0].weekly_units * 3)
        self.assertGreater(high.studio.catalog[0].monthly_players, low.studio.catalog[0].monthly_players * 2)

    def test_pre_release_hype_creates_a_larger_launch_spike(self) -> None:
        organic = GameState()
        hyped = GameState()
        for state, hype in ((organic, 5), (hyped, 180)):
            start_project(state)
            state.studio.current_project.hype = hype
            state.studio.current_project.work_done = state.studio.current_project.total_work - 1
            advance(state, 1)

        self.assertGreater(hyped.studio.active_sales[0].weekly_units, organic.studio.active_sales[0].weekly_units * 3)

    def test_promotion_costs_money_and_builds_project_hype(self) -> None:
        state = GameState()
        state.studio.reputation = 20
        self.assertTrue(start_project(state))
        before_cash = state.studio.cash
        before_hype = state.studio.current_project.hype

        self.assertTrue(buy_promotion(state, 0, 3))
        advance(state, 2)

        self.assertLess(state.studio.cash, before_cash)
        self.assertGreater(state.studio.current_project.hype, before_hype)

    def test_only_enter_queues_updates_while_mouse_still_selects_games(self) -> None:
        state = GameState()
        start_project(state)
        advance(state, 40)
        state.modal = "games"
        game_row = (0, 2, 5, 0, curses.BUTTON1_DOUBLE_CLICKED)
        with patch("main.curses.getmouse", return_value=game_row):
            handle_mouse(state, (38, 120))
        self.assertIsNone(state.studio.active_update)

        narrow_first_row = (0, 2, 4, 0, curses.BUTTON1_DOUBLE_CLICKED)
        with patch("main.curses.getmouse", return_value=narrow_first_row):
            handle_mouse(state, (24, 74))
        self.assertIsNone(state.studio.active_update)
        handle_key(state, ord("u"))
        self.assertIsNone(state.studio.active_update)
        enter_action = next((start, end) for action, start, end in footer_button_ranges(state, 120) if action == "enter_only")
        footer_click = (0, enter_action[0], 37, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=footer_click):
            handle_mouse(state, (38, 120))
        self.assertIsNone(state.studio.active_update)
        handle_key(state, 10)
        self.assertIsNotNone(state.studio.active_update)

        handle_key(state, ord("m"))
        promotion_row = (0, 42, 5, 0, curses.BUTTON1_DOUBLE_CLICKED)
        with patch("main.curses.getmouse", return_value=promotion_row):
            handle_mouse(state, (38, 120))
        self.assertEqual(len(state.studio.active_promotions), 1)

    def test_hiring_changes_team_and_monthly_burn(self) -> None:
        state = GameState()
        old_burn = monthly_fixed_cost(state.studio)
        candidate = state.studio.applicants[0]

        self.assertTrue(hire_candidate(state))
        self.assertIn(candidate, state.studio.team)
        self.assertGreater(monthly_fixed_cost(state.studio), old_burn + candidate.monthly_salary)

    def test_contract_diverts_capacity_then_pays(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        self.assertTrue(accept_contract(state))
        payout = state.studio.contract.payout
        deadline = state.studio.contract.weeks_left
        revenue_before = state.studio.lifetime_revenue

        advance(state, deadline)

        self.assertIsNone(state.studio.contract)
        self.assertGreaterEqual(state.studio.lifetime_revenue, revenue_before + payout)
        self.assertGreater(state.studio.contractor_reputation, 0)

    def test_contract_speed_uses_relevant_team_skill(self) -> None:
        state = GameState()
        state.studio.team[0].code = 20
        low_output = contract_weekly_output(state.studio, "Code")
        state.studio.team[0].code = 95
        high_output = contract_weekly_output(state.studio, "Code")

        self.assertGreater(high_output, low_output * 4)

    def test_auto_contract_toggle_queues_every_eligible_offer(self) -> None:
        state = GameState()
        eligible = sum(job.reputation_required <= state.studio.contractor_reputation for job in state.studio.contract_offers)

        self.assertTrue(toggle_auto_contracts(state))

        self.assertIsNotNone(state.studio.contract)
        self.assertEqual(1 + len(state.studio.contract_queue), eligible)
        self.assertEqual(len(state.studio.contract_offers), 6 - eligible)
        self.assertFalse(toggle_auto_contracts(state))
        self.assertEqual(len(state.studio.contract_queue), 0)
        self.assertIsNotNone(state.studio.contract)

    def test_disabling_auto_preserves_manually_queued_job(self) -> None:
        state = GameState()
        self.assertTrue(accept_contract(state))
        eligible_index = next(index for index, job in enumerate(state.studio.contract_offers) if job.reputation_required <= state.studio.contractor_reputation)
        self.assertTrue(accept_contract_offer(state, eligible_index))
        manual_id = state.studio.contract_queue[0].contract_id

        toggle_auto_contracts(state)
        toggle_auto_contracts(state)

        self.assertEqual([job.contract_id for job in state.studio.contract_queue], [manual_id])

    def test_auto_off_save_clears_untagged_legacy_queue(self) -> None:
        state = GameState()
        toggle_auto_contracts(state)
        state.studio.auto_contracts = False
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy-auto-queue.json"
            state.save_path = str(path)
            save_game(state)
            data = json.loads(path.read_text(encoding="utf-8"))
            for contract in data["studio"]["contract_queue"]:
                contract.pop("auto_accepted", None)
            path.write_text(json.dumps(data), encoding="utf-8")
            loaded = load_game(str(path))

        self.assertFalse(loaded.studio.auto_contracts)
        self.assertEqual(loaded.studio.contract_queue, [])
        self.assertIn("Removed", loaded.logs[0])

    def test_header_shows_studio_reputation_instead_of_contract_progress(self) -> None:
        state = GameState()
        self.assertTrue(accept_contract(state))
        state.studio.contract.work_done = state.studio.contract.required_work * 0.4
        screen = MagicMock()
        screen.getmaxyx.return_value = (36, 120)

        with patch("main.curses.color_pair", return_value=0):
            draw_header(screen, state, 120)

        status_line = screen.addstr.call_args_list[1].args[2]
        self.assertTrue(status_line.startswith(" ["))
        self.assertNotIn("Next week", status_line)
        self.assertIn("░", status_line)
        self.assertIn("Games", status_line)
        self.assertIn("Team 1", status_line)
        self.assertNotIn("suggested", status_line)
        self.assertIn("Fans", status_line)
        self.assertIn("GRep", status_line)
        self.assertIn("CRep", status_line)
        self.assertNotIn(state.studio.contract.title, status_line)

    def test_version_two_save_round_trip(self) -> None:
        state = GameState()
        state.marketing_tab = 1
        start_project(state)
        advance(state, 3)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            state.save_path = str(path)
            save_game(state)
            loaded = load_game(str(path))

        self.assertEqual(loaded.clock.current_date, state.clock.current_date)
        self.assertEqual(loaded.studio.cash, state.studio.cash)
        self.assertEqual(loaded.studio.current_project.work_done, state.studio.current_project.work_done)
        self.assertEqual(len(loaded.studio.applicants), 6)
        self.assertEqual(len(loaded.studio.contract_offers), len(state.studio.contract_offers))
        self.assertEqual(loaded.marketing_tab, 1)

    def test_accounting_preserves_expense_categories(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))

        advance(state, 4)

        self.assertTrue(state.studio.ledger)
        self.assertIn("Development", state.studio.ledger[0].categories)
        self.assertIn("Payroll", state.studio.period_expense_categories)

    def test_reach_expands_staffing_target_and_applicant_pool(self) -> None:
        state = GameState()
        state.studio.followers = 1_250
        state.studio.released_games = 6
        state.studio.reputation = 18

        refresh_applicants(state)

        self.assertGreater(recommended_team_size(state.studio), 1)
        self.assertGreater(len(state.studio.applicants), 6)

    def test_positional_save_path_implies_loading(self) -> None:
        direct = parse_args(["studio.json"])
        after_load = parse_args(["--load", "studio.json"])
        explicit = parse_args(["--load", "--save-file", "studio.json"])

        self.assertTrue(direct.load)
        self.assertTrue(after_load.load)
        self.assertTrue(explicit.load)
        self.assertEqual(direct.save_path, "studio.json")
        self.assertEqual(after_load.save_path, "studio.json")
        self.assertEqual(explicit.save_path, "studio.json")

    def test_mouse_opens_and_switches_analysis(self) -> None:
        state = GameState()
        click = (0, 2, 4, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=click):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.modal, "analysis")

        second_tab = (0, 40, 4, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=second_tab):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.analysis_view, 1)

        state.modal = "main"
        combined_contract_section = (0, 170, 12, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=combined_contract_section):
            handle_mouse(state, (50, 190))
        self.assertEqual(state.modal, "contracts")

        state.modal = "main"
        expanded_team_panel = (0, 20, 25, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=expanded_team_panel):
            handle_mouse(state, (50, 190))
        self.assertEqual(state.modal, "team")

    def test_footer_mouse_can_start_and_choose_a_new_game(self) -> None:
        state = GameState()
        new_button = (0, 2, 35, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=new_button):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.modal, "new_game")
        self.assertEqual(state.new_game_step, -1)

        choose_button = (0, 26, 35, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=choose_button):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.new_game_step, 0)

        marketing_state = GameState()
        marketing_button = (0, 16, 35, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=marketing_button):
            handle_mouse(marketing_state, (36, 120))
        self.assertEqual(marketing_state.modal, "marketing")

    def test_mouse_can_open_board_and_accept_a_single_contract(self) -> None:
        state = GameState()
        jobs_button = (0, 8, 35, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=jobs_button):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.modal, "contracts")

        first_job = (0, 2, 5, 0, curses.BUTTON1_DOUBLE_CLICKED)
        with patch("main.curses.getmouse", return_value=first_job):
            handle_mouse(state, (36, 120))
        self.assertIsNotNone(state.studio.contract)
        self.assertEqual(len(state.studio.contract_offers), 5)

    def test_t_opens_team_and_e_remains_legacy_alias(self) -> None:
        state = GameState()
        handle_key(state, ord("t"))
        self.assertEqual(state.modal, "team")
        state.modal = "main"
        handle_key(state, ord("e"))
        self.assertEqual(state.modal, "team")

    def test_active_team_side_receives_more_table_width(self) -> None:
        state = GameState()
        state.team_tab = 0
        roster_narrow, applicants_wide = team_panel_widths(state, 190)
        state.team_tab = 1
        roster_wide, applicants_narrow = team_panel_widths(state, 190)

        self.assertGreater(applicants_wide, roster_narrow)
        self.assertGreater(roster_wide, applicants_narrow)
        self.assertGreater(roster_wide, roster_narrow)

    def test_custom_title_and_sequel_lineage_are_persistent(self) -> None:
        state = GameState()
        state.modal = "new_game"
        handle_new_game_key(state, ord("t"))
        for character in "My First Commercial Game":
            handle_key(state, ord(character))
        handle_key(state, 10)
        self.assertTrue(start_project(state))
        advance(state, 40)

        original = state.studio.catalog[0]
        self.assertEqual(original.title, "My First Commercial Game")
        self.assertGreater(state.studio.genre_fans[original.genre], 0)

        open_new_game(state)
        self.assertEqual(state.new_game_step, -1)
        handle_new_game_key(state, curses.KEY_DOWN)
        handle_new_game_key(state, 10)
        self.assertIn("II", state.draft_title)
        self.assertTrue(start_project(state))
        self.assertEqual(state.studio.current_project.sequel_of, original.game_id)
        self.assertEqual(state.studio.current_project.generation, 2)
        with tempfile.TemporaryDirectory() as directory:
            state.save_path = str(Path(directory) / "franchise.json")
            save_game(state)
            loaded = load_game(state.save_path)
        self.assertEqual(loaded.studio.catalog[0].title, "My First Commercial Game")
        self.assertEqual(loaded.studio.current_project.sequel_of, original.game_id)

    def test_old_settled_release_is_recovered_for_sequels(self) -> None:
        state = GameState()
        state.studio.released_games = 1
        state.logs = [
            "Music: Visual Novel settled at 1,573 units and $14,403 studio net.",
            "Delivered the prototype for a local agency; client paid $10,000.",
            "Delivered the UI implementation contract; client paid $12,000.",
        ]
        with tempfile.TemporaryDirectory() as directory:
            state.save_path = str(Path(directory) / "old-v2.json")
            save_game(state)
            loaded = load_game(state.save_path)

        self.assertEqual(len(loaded.studio.catalog), 1)
        self.assertEqual(loaded.studio.catalog[0].title, "Music: Visual Novel")
        self.assertEqual(loaded.studio.catalog[0].units_sold, 1_573)
        self.assertGreater(loaded.studio.catalog[0].actual_bugs, 0)
        self.assertGreater(loaded.studio.catalog[0].known_bugs, 0)
        self.assertLess(loaded.studio.catalog[0].known_bugs, loaded.studio.catalog[0].actual_bugs)
        self.assertEqual(loaded.studio.contracts_completed, 2)
        self.assertEqual(loaded.studio.contractor_reputation, 3.0)

    def test_legacy_save_migrates_to_current_date(self) -> None:
        legacy = {
            "clock": {"current_date": "1976-01-08", "week": 2},
            "studio": {"cash": 10_000, "fans": 12, "reputation": 3, "released_games": 1},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.json"
            path.write_text(json.dumps(legacy), encoding="utf-8")
            loaded = load_game(str(path))

        self.assertEqual(loaded.clock.current_date, date.today())
        self.assertEqual(loaded.studio.cash, 30_000)
        self.assertEqual(loaded.studio.followers, 52)
        self.assertIn("Migrated", loaded.logs[0])


if __name__ == "__main__":
    unittest.main()
