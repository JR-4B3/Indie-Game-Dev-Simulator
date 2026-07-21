import curses
import tempfile
import unittest
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from game_data import GENRES, GOOD_MATCHES, TOPICS
from main import CTRL_S, active_top_tab, bottom_time_layout, draw_dashboard, draw_footer, draw_games_screen, draw_header, draw_insolvency_popup, draw_main_content, draw_marketing_screen, draw_new_game, draw_screen, draw_settings_popup, draw_team_screen, footer_button_ranges, footer_layout, global_action_layout, handle_key, handle_mouse, handle_new_game_key, new_game_panel_geometry, open_new_game, parse_args, status_segments, team_layout, top_context_uses_second_row, top_control_layout, top_tab_actions, top_tab_layout
from ui_newgame import topic_order
from ui_upgrades import draw_upgrades
from simulation import (
    ActiveSale,
    GAME_FORMATS,
    MEDIA_VENTURES,
    PRODUCTION_DECISIONS,
    QUIRKS,
    RESEARCH_NODES,
    SAVE_VERSION,
    SCOPES,
    START_DATE,
    TIME_LABELS,
    TIME_SPEEDS,
    GameState,
    accept_contract,
    accept_contract_offer,
    activity_allocations,
    advance_days,
    advance_game,
    bump_version,
    buy_media_venture,
    buy_promotion,
    capacity_drains,
    chart_positions,
    contract_weekly_output,
    cycle_work_priority,
    cycle_game_update_size,
    cycle_game_support,
    estimated_update_weeks,
    franchise_by_id,
    game_profit,
    game_total_cost,
    hire_candidate,
    has_research,
    load_game,
    market_chart,
    market_report,
    market_truth,
    monthly_fixed_cost,
    plan_requirements,
    prepare_spinoff,
    projected_weekly_output,
    queue_game_update,
    queue_research,
    recommended_team_size,
    refresh_applicants,
    research_by_key,
    research_work_requirement,
    save_game,
    start_project,
    start_employee_vacation,
    state_from_data,
    state_to_data,
    toggle_auto_contracts,
)


def advance(state: GameState, weeks: int) -> None:
    for _ in range(weeks):
        state.clock.current_date += timedelta(days=7)
        state.clock.week += 1
        advance_game(state, 1)


def unlock(state: GameState, *node_keys: str) -> None:
    for key in node_keys:
        if key not in state.studio.completed_research:
            state.studio.completed_research.append(key)


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


def rendered_marketing_text(state: GameState, width: int, height: int) -> list[str]:
    screen = MagicMock()
    windows = []

    def create_window(panel_height, panel_width, _y, _x):
        window = MagicMock()
        window.getmaxyx.return_value = (panel_height, panel_width)
        windows.append(window)
        return window

    screen.derwin.side_effect = create_window
    with patch("main.curses.color_pair", return_value=0):
        draw_marketing_screen(screen, state, width, height)
    return [call.args[2] for window in windows for call in window.addstr.call_args_list]


def rendered_new_game_text(state: GameState, width: int, height: int) -> list[str]:
    screen = MagicMock()
    windows = []

    def create_window(panel_height, panel_width, _y, _x):
        window = MagicMock()
        window.getmaxyx.return_value = (panel_height, panel_width)
        windows.append(window)
        return window

    screen.derwin.side_effect = create_window
    with patch("main.curses.color_pair", return_value=0):
        draw_new_game(screen, state, width, height)
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
        draw_main_content(screen, state, width, height, 10)
    return [call.args[2] for window in windows for call in window.addstr.call_args_list]


def rendered_screen_text(state: GameState, width: int, height: int) -> list[str]:
    screen = MagicMock()
    screen.getmaxyx.return_value = (height, width)
    windows = [screen]

    def create_window(panel_height, panel_width, _y, _x):
        window = MagicMock()
        window.getmaxyx.return_value = (panel_height, panel_width)
        windows.append(window)
        return window

    screen.derwin.side_effect = create_window
    with patch("main.curses.color_pair", return_value=0):
        draw_screen(screen, state)
    return [call.args[2] for window in windows for call in window.addstr.call_args_list]


def top_action_target(state: GameState, width: int, action: str) -> tuple[int, int]:
    if top_context_uses_second_row(state, width):
        start = next(start for item, start, _ in footer_button_ranges(state, width) if item == action)
        return start, 1
    start = next(x for label, item, x in top_control_layout(state, width) if item == action)
    return start, 0


class SimulationTests(unittest.TestCase):
    def test_control_bar_layout_uses_top_navigation(self) -> None:
        state = GameState()
        self.assertEqual([label for label, _ in top_tab_actions(state)], [">[H]ub<", "[G]ame", "[T]eam", "[S]tatistics"])
        hub_labels = {action: label for label, action, _ in footer_layout(state, 190)}
        self.assertEqual(hub_labels, {"new": "[N]ew Game", "contracts": "[J]obs", "upgrades": "[U]pgrades"})
        hub_new_game = GameState()
        handle_key(hub_new_game, ord("n"))
        self.assertEqual((hub_new_game.modal, hub_new_game.new_game_step), ("new_game", -1))
        handle_key(state, 9)
        self.assertEqual(state.modal, "games")
        self.assertEqual([label for label, _ in top_tab_actions(state)], ["[H]ub", ">[G]ame<", "[T]eam", "[S]tatistics"])

        for width in (74, 100, 150, 190):
            tabs = top_tab_layout(state, width)
            context = footer_layout(state, width)
            globals_ = global_action_layout(state, width)
            self.assertEqual([action for _, action, _ in globals_], ["settings"])
            self.assertEqual(tabs[0][1], 2)
            self.assertEqual(globals_[-1][2] + len(globals_[-1][0]), width - 2)
            self.assertLessEqual(context[-1][2] + len(context[-1][0]), width - 1)
            controls = top_control_layout(state, width)
            if not top_context_uses_second_row(state, width):
                contextual_controls = [(label, action, x) for label, action, x in controls if action in {item for _, item, _ in context}]
                self.assertEqual(contextual_controls, context)
            ordered = sorted((x, x + len(label)) for label, _, x in controls)
            self.assertTrue(all(end < next_start for (_, end), (next_start, _) in zip(ordered, ordered[1:])))
        dense_state = GameState(modal="marketing")
        self.assertTrue(top_context_uses_second_row(dense_state, 74))
        self.assertFalse(top_context_uses_second_row(dense_state, 190))

        screen = MagicMock()
        screen.getmaxyx.return_value = (50, 190)
        with patch("main.curses.color_pair", return_value=0):
            draw_header(screen, state, 190)
        shortcut = next(call for call in screen.addstr.call_args_list if call.args[2] == "[G]")
        word = next(call for call in screen.addstr.call_args_list if call.args[2] == "ame<")
        self.assertTrue(shortcut.args[3] & curses.A_BOLD)
        self.assertFalse(word.args[3] & curses.A_BOLD)

    def test_leaf_pages_keep_owner_tab_active_and_tab_wraps(self) -> None:
        ownership = {
            "contracts": 0,
            "upgrades": 0,
            "settings": 0,
            "new_game": 1,
            "marketing": 1,
            "update_planner": 1,
            "team": 2,
            "analysis": 3,
        }
        for modal, expected in ownership.items():
            self.assertEqual(active_top_tab(GameState(modal=modal)), expected)

        state = GameState()
        expected_modals = ["games", "team", "analysis", "main"]
        for modal in expected_modals:
            handle_key(state, 9)
            self.assertEqual(state.modal, modal)

        state.modal = "new_game"
        state.naming_game = True
        state.draft_title = ""
        handle_key(state, ord("h"))
        self.assertEqual(state.draft_title, "h")
        handle_key(state, 9)
        self.assertEqual(state.modal, "team")
        self.assertFalse(state.naming_game)

        state.modal = "new_game"
        state.new_game_step = 3
        state.naming_game = True
        state.draft_title = " Mouse Title "
        self.assertEqual([action for _, action, _ in footer_layout(state, 120)], ["accept_title"])
        accept_x, accept_y = top_action_target(state, 120, "accept_title")
        with patch("main.curses.getmouse", return_value=(0, accept_x, accept_y, 0, curses.BUTTON1_CLICKED)):
            handle_mouse(state, (36, 120))
        self.assertFalse(state.naming_game)
        self.assertEqual(state.draft_title, "Mouse Title")

        state.naming_game = True
        state.draft_title = ""
        handle_key(state, curses.KEY_BACKSPACE)
        self.assertFalse(state.naming_game)

    def test_dashboard_uses_balanced_team_catalogue_finance_and_contract_panels(self) -> None:
        state = GameState()
        advance(state, 4)

        wide_text = rendered_main_content_text(state, 190, 50)
        compact_text = rendered_main_content_text(state, 74, 40)

        self.assertTrue(any(" Finance " in line for line in wide_text))
        self.assertTrue(any("RECENT ACTIVITY" in line for line in wide_text))
        self.assertTrue(any("Production Command" in line for line in wide_text))
        self.assertTrue(any(line.strip() == "OPERATIONS" for line in wide_text))
        self.assertTrue(any("Update queue" in line and "Promotion queue" in line and "|" in line for line in wide_text))
        self.assertTrue(any(line.strip() == "CONTRACTS" for line in wide_text))
        self.assertTrue(any("[C] Auto contracts" in line for line in wide_text))
        self.assertTrue(any("TOP SKILL" in line and "PERSONALITY" in line for line in wide_text))
        self.assertTrue(any(" Market Pulse " in line for line in wide_text))
        self.assertTrue(any("CHART POSITION" in line for line in wide_text))
        self.assertTrue(any("TOP CHART THIS WEEK" in line for line in wide_text))
        self.assertFalse(any("-- outside the top 10" in line for line in wide_text))
        self.assertFalse(any("Recent Financial Trend" in line for line in wide_text))
        self.assertTrue(any("Recent Financial Trend" in line for line in compact_text))
        self.assertTrue(any(" Contracts " in line for line in compact_text))
        self.assertTrue(any("CONTRACT STATUS" in line for line in compact_text))

        screen = MagicMock()
        screen.derwin.side_effect = lambda panel_height, panel_width, _y, _x: MagicMock(**{"getmaxyx.return_value": (panel_height, panel_width)})
        with patch("main.curses.color_pair", return_value=0):
            draw_dashboard(screen, state, 190)
            draw_main_content(screen, state, 190, 50, 10)
        panel_calls = [call.args for call in screen.derwin.call_args_list]
        finance = next(args for args in panel_calls if args[2:] == (2, 0))
        production = next(args for args in panel_calls if args[2] == 2 and args[3] > 0)
        team = next(args for args in panel_calls if args[2:] == (18, 0))
        catalogue = next(args for args in panel_calls if args[2] == 18 and args[3] > 0)
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
        self.assertTrue(any("Contract uses" in line and "capacity" in line for line in text))
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

        self.assertTrue(any("STYLE / QUIRK" in line and "COST/MO" in line for line in text))
        self.assertTrue(any("Payroll" in line and "/mo" in line for line in text))
        self.assertTrue(any("Team skills" in line for line in text))
        self.assertTrue(any("Person Detail" in line for line in text))
        self.assertTrue(any("WELLBEING" in line for line in text))
        member = next(employee for employee in state.studio.team if not employee.founder)
        self.assertTrue(any(member.trait in line and member.quirk in line for line in text))
        self.assertTrue(any("TRN" in line for line in text))

        compact_text = rendered_team_text(state, 100, 36)
        self.assertTrue(any("Person Detail" in line for line in compact_text))
        self.assertFalse(any("Applicants |" in line for line in compact_text))
        state.team_tab = 0
        hire_text = rendered_team_text(state, 100, 36)
        self.assertTrue(any("OFFER" in line for line in hire_text))
        self.assertTrue(any("Burn" in line for line in hire_text))
        self.assertTrue(any("Runway after hire" in line for line in hire_text))

    def test_swapped_bottom_header_keeps_date_branding_and_top_tabs(self) -> None:
        state = GameState()
        state.clock.week = 429
        screen = MagicMock()
        screen.getmaxyx.return_value = (36, 190)

        with patch("main.curses.color_pair", return_value=0):
            draw_header(screen, state, 190)
            draw_footer(screen, state, 36, 190)

        rendered = " ".join(call.args[2] for call in screen.addstr.call_args_list)
        self.assertIn("INDIE GAME DEV SIM", rendered)
        self.assertIn(f"{state.clock.current_date:%d %b %Y}", rendered)
        self.assertIn("Y 9", rendered)
        self.assertIn("W 13", rendered)
        self.assertIn("[Space]", rendered)
        self.assertIn("> [H] ub<", rendered)
        date_call = next(call for call in screen.addstr.call_args_list if f"{state.clock.current_date:%d %b %Y}" in call.args[2])
        metric_call = next(call for call in screen.addstr.call_args_list if call.args[2].startswith("$"))
        self.assertEqual(date_call.args[0], 35)
        self.assertEqual(metric_call.args[0], 34)
        backgrounds = [call for call in screen.addstr.call_args_list if not call.args[2].strip()]
        self.assertTrue(all(call.args[1] == 1 for call in backgrounds))

    def test_header_speed_indicator_matches_four_speed_levels(self) -> None:
        self.assertEqual(TIME_SPEEDS, (0.0, 12.0, 24.0, 48.0))
        self.assertEqual(TIME_LABELS, ("||", "> 1x", ">> 2x", ">>> 4x"))

        for speed_index, label in enumerate(TIME_LABELS):
            state = GameState()
            state.time_speed_index = speed_index
            screen = MagicMock()
            screen.getmaxyx.return_value = (36, 160)
            with patch("main.curses.color_pair", return_value=0):
                draw_footer(screen, state, 36, 160)
            rendered = " ".join(call.args[2] for call in screen.addstr.call_args_list)
            speed_glyph = "||" if speed_index == 0 else ">" * speed_index
            self.assertEqual(bottom_time_layout(state, 160)[1][0], f"[Space]{speed_glyph}")
            self.assertIn(speed_glyph, rendered)

        state = GameState()
        state.clock.week = 429
        screen = MagicMock()
        screen.getmaxyx.return_value = (50, 160)
        with patch("main.curses.color_pair", return_value=0):
            draw_footer(screen, state, 50, 160)
        date_call = next(call for call in screen.addstr.call_args_list if f"{state.clock.current_date:%d %b %Y}" in call.args[2])
        self.assertEqual(date_call.args[0], 49)
        self.assertEqual(date_call.args[1], 2)

        state = GameState()
        faster_label, _, faster_x = next(item for item in bottom_time_layout(state, 120) if item[1] == "faster")
        with patch("main.curses.getmouse", return_value=(0, faster_x, 35, 0, curses.BUTTON1_CLICKED)):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.time_speed_index, 2)
        pause_label, _, pause_x = next(item for item in bottom_time_layout(state, 120) if item[1] == "pause")
        with patch("main.curses.getmouse", return_value=(0, pause_x, 35, 0, curses.BUTTON1_CLICKED)):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.time_speed_index, 0)

        for modal in ("main", "games", "team", "contracts", "marketing"):
            state = GameState(modal=modal)
            handle_key(state, curses.KEY_RIGHT)
            self.assertEqual(state.time_speed_index, 2)
            handle_key(state, curses.KEY_LEFT)
            self.assertEqual(state.time_speed_index, 1)

        state = GameState(modal="upgrades")
        branch_before = state.selected_research_branch
        handle_key(state, curses.KEY_RIGHT)
        self.assertNotEqual(state.selected_research_branch, branch_before)
        self.assertEqual(state.time_speed_index, 1)

    def test_promotion_panels_use_enter_and_backspace_while_arrows_adjust_speed(self) -> None:
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
        handle_key(state, curses.KEY_RIGHT)
        self.assertEqual(state.time_speed_index, 2)
        self.assertEqual(state.marketing_tab, 0)
        handle_key(state, 10)
        handle_key(state, curses.KEY_DOWN)
        self.assertEqual(state.marketing_tab, 1)
        self.assertEqual(state.selected_promotion_target, 1)
        self.assertEqual(state.selected_promotion, 1)

        target_before = state.selected_promotion_target
        handle_key(state, curses.KEY_LEFT)
        self.assertEqual(state.time_speed_index, 1)
        self.assertEqual(state.selected_promotion_target, target_before)

        labels = {action: label for label, action, _ in footer_layout(state, 190)}
        self.assertNotIn("switch_marketing_tab", labels)
        self.assertEqual(labels["back"], "[Backspace] Planning")
        self.assertEqual(labels["buy_promotion"], "[Enter] Buy")
        marketing_text = rendered_marketing_text(state, 190, 50)
        self.assertTrue(any("Game Catalogue" in line for line in marketing_text))
        marketing_header = next(line for line in marketing_text if "PLAYERS/M" in line and "CHART" in line)
        game_header = next(line for line in rendered_games_text(state, 190, 50) if "PLAYERS/M" in line and "CHART" in line)
        self.assertEqual(marketing_header.split(), game_header.split())
        self.assertLess(marketing_header.index("TITLE"), marketing_header.index("HYPE"))
        self.assertLess(marketing_header.index("HYPE"), marketing_header.index("BUGS"))
        self.assertLess(marketing_header.index("BUGS"), marketing_header.index("USER"))
        self.assertLess(marketing_header.index("USER"), marketing_header.index("PRESS"))
        self.assertLess(marketing_header.index("PRESS"), marketing_header.index("CHART"))
        self.assertLess(marketing_header.index("CHART"), marketing_header.index("SALES/W"))
        self.assertLess(marketing_header.index("SALES/W"), marketing_header.index("PLAYERS/M"))
        self.assertLess(marketing_header.index("PLAYERS/M"), marketing_header.index("UNITS"))
        self.assertTrue(any("Selected Game" in line for line in marketing_text))
        self.assertTrue(any("Promotion Planning & Queue" in line for line in marketing_text))
        self.assertFalse(any("Promotion Targets" in line for line in marketing_text))
        handle_key(state, curses.KEY_BACKSPACE)
        self.assertEqual(state.marketing_tab, 0)
        handle_key(state, 9)
        self.assertEqual(state.modal, "team")

    def test_new_game_uses_enter_next_and_backspace_previous_before_greenlight(self) -> None:
        state = GameState()
        state.modal = "new_game"
        state.new_game_step = 0
        genre_before = state.selected_genre
        top_height, genre_width, theme_width, plan_width, storefront_height = new_game_panel_geometry(190, 50)
        self.assertEqual((top_height, genre_width, theme_width, plan_width, storefront_height), (35, 28, 32, 128, 11))
        self.assertGreater(plan_width, genre_width + theme_width)

        screen = MagicMock()
        genre_panel = MagicMock()
        theme_panel = MagicMock()
        plan_panel = MagicMock()
        storefront_panel = MagicMock()
        genre_panel.getmaxyx.return_value = (35, 28)
        theme_panel.getmaxyx.return_value = (35, 32)
        plan_panel.getmaxyx.return_value = (46, 128)
        storefront_panel.getmaxyx.return_value = (11, 61)
        screen.derwin.side_effect = [genre_panel, theme_panel, plan_panel, storefront_panel]
        with patch("main.curses.color_pair", return_value=0):
            draw_new_game(screen, state, 190, 50)
        self.assertEqual([item.args for item in screen.derwin.call_args_list], [(35, 28, 2, 0), (35, 32, 2, 29), (46, 128, 2, 62), (11, 61, 37, 0)])
        storefront_text = [item.args[2] for item in storefront_panel.addstr.call_args_list]
        self.assertTrue(any("STORE" in text and "|  CUT |" in text and "COST" in text for text in storefront_text))
        self.assertTrue(any("> Steam" in text and "|  30% |" in text for text in storefront_text))

        handle_new_game_key(state, curses.KEY_DOWN)
        self.assertNotEqual(state.selected_genre, genre_before)
        handle_new_game_key(state, ord(","))
        handle_new_game_key(state, ord("."))
        self.assertEqual(state.new_game_step, 0)
        handle_new_game_key(state, 10)
        self.assertEqual(state.new_game_step, 1)
        labels = {action: label for label, action, _ in footer_layout(state, 190)}
        self.assertEqual(labels["back"], "[Backspace] Previous")
        self.assertEqual(labels["new_game_selection"], "[Up/Down] Theme")
        self.assertEqual(labels["confirm"], "[Enter] Next")
        self.assertEqual(labels["type_title"], "[E]dit title")
        self.assertEqual(labels["random_title"], "[R]andom")
        self.assertNotIn("next_new_game_panel", labels)
        self.assertNotIn("previous_new_game_panel", labels)

        handle_new_game_key(state, 10)
        self.assertEqual(state.new_game_step, 2)
        self.assertIsNone(state.studio.current_project)
        labels = {action: label for label, action, _ in footer_layout(state, 190)}
        self.assertEqual(labels["new_game_selection"], "[Up/Down] Production Plan")
        self.assertEqual(labels["confirm"], "[Enter] Next")
        self.assertEqual([action for _, action, _ in bottom_time_layout(state, 190)], ["new_game_adjust_left", "pause", "new_game_adjust_right"])
        speed_before = state.time_speed_index
        scope_before = state.selected_scope
        handle_key(state, curses.KEY_RIGHT)
        self.assertNotEqual(state.selected_scope, scope_before)
        self.assertEqual(state.time_speed_index, speed_before)
        handle_new_game_key(state, 10)
        self.assertEqual(state.new_game_step, 3)
        self.assertIsNone(state.studio.current_project)
        labels = {action: label for label, action, _ in footer_layout(state, 190)}
        self.assertEqual(labels["new_game_selection"], "[Up/Down] Storefront")
        self.assertEqual(labels["confirm"], "[Enter] Greenlight")
        self.assertNotIn("new_game_adjust", labels)
        self.assertEqual([action for _, action, _ in bottom_time_layout(state, 190)], ["slower", "pause", "faster"])
        handle_new_game_key(state, curses.KEY_BACKSPACE)
        self.assertEqual(state.new_game_step, 2)
        handle_new_game_key(state, 10)
        handle_new_game_key(state, 10)
        self.assertIsNotNone(state.studio.current_project)
        self.assertEqual(state.modal, "games")
        text = rendered_games_text(state, 190, 36)
        self.assertTrue(any(state.studio.current_project.title in line and "dev" in line for line in text))
        self.assertTrue(any("CAPACITY" in line for line in text))

        chooser = GameState(modal="new_game", new_game_step=-1)
        handle_new_game_key(chooser, curses.KEY_BACKSPACE)
        self.assertEqual(chooser.modal, "games")

    def test_blend_mode_switches_list_to_secondary_selection(self) -> None:
        state = GameState(modal="new_game", new_game_step=0)
        state.selected_genre = 0
        state.selected_secondary_genre = 0

        handle_new_game_key(state, ord("b"))
        self.assertTrue(state.mix_blend)
        text = rendered_new_game_text(state, 190, 50)
        self.assertTrue(any(line.startswith("BLEND") for line in text))
        handle_new_game_key(state, curses.KEY_DOWN)
        self.assertEqual(state.selected_genre, 0)
        self.assertEqual(state.selected_secondary_genre, 1)

        handle_new_game_key(state, ord("b"))
        self.assertFalse(state.mix_blend)
        self.assertEqual(state.selected_secondary_genre, 0)
        handle_new_game_key(state, curses.KEY_DOWN)
        self.assertEqual(state.selected_genre, 1)
        self.assertEqual(state.selected_secondary_genre, 1)

        handle_new_game_key(state, ord("b"))
        handle_new_game_key(state, curses.KEY_DOWN)
        handle_new_game_key(state, 10)
        self.assertFalse(state.mix_blend)
        self.assertEqual(state.new_game_step, 0)
        self.assertEqual(state.selected_secondary_genre, GENRES.index("Platformer"))
        handle_new_game_key(state, 10)
        self.assertEqual(state.new_game_step, 1)

        handle_new_game_key(state, ord("b"))
        primary_topic = state.selected_topic
        handle_new_game_key(state, curses.KEY_DOWN)
        self.assertEqual(state.selected_topic, primary_topic)
        self.assertNotEqual(state.selected_secondary_topic, primary_topic)
        handle_new_game_key(state, 10)
        self.assertEqual(state.new_game_step, 1)
        self.assertNotEqual(state.selected_secondary_topic, primary_topic)

        labels = {action: label for label, action, _ in footer_layout(GameState(modal="new_game", new_game_step=0), 190)}
        self.assertEqual(labels["toggle_blend"], "[B]lend")

    def test_primary_navigation_does_not_create_a_blend(self) -> None:
        state = GameState(modal="new_game", new_game_step=0)
        handle_new_game_key(state, curses.KEY_DOWN)
        self.assertEqual(state.selected_secondary_genre, state.selected_genre)
        genre = state.selected_genre
        handle_new_game_key(state, curses.KEY_RIGHT)
        self.assertEqual((state.selected_genre, state.selected_secondary_genre), (genre, genre))

        handle_new_game_key(state, 10)
        handle_new_game_key(state, curses.KEY_DOWN)
        self.assertEqual(state.selected_secondary_topic, state.selected_topic)
        topic = state.selected_topic
        handle_new_game_key(state, curses.KEY_RIGHT)
        self.assertEqual((state.selected_topic, state.selected_secondary_topic), (topic, topic))

    def test_long_confirmed_blend_keeps_plus_in_panel_border(self) -> None:
        state = GameState(modal="new_game", new_game_step=0)
        unlock(state, "genre_systems")
        state.selected_genre = GENRES.index("Building Game")
        state.selected_secondary_genre = GENRES.index("Economic Simulation")
        text = rendered_new_game_text(state, 190, 50)
        self.assertTrue(any(line.startswith("+ Economic") for line in text))

    def test_plan_options_tray_lists_field_choices(self) -> None:
        state = GameState(modal="new_game", new_game_step=2)
        text = rendered_new_game_text(state, 190, 50)
        self.assertTrue(any("Options" in line for line in text))
        self.assertTrue(any("Blockbuster" in line for line in text))
        self.assertTrue(any("<Micro>" in line for line in text))
        state.selected_focus = 2
        text = rendered_new_game_text(state, 190, 50)
        self.assertTrue(any("Kids & families" in line for line in text))
        self.assertFalse(any("Trade-off" in line for line in text))

    def test_compact_new_game_keeps_readiness_workload_and_brief_visible(self) -> None:
        state = GameState(modal="new_game", new_game_step=2)
        text = rendered_new_game_text(state, 74, 24)
        self.assertTrue(any("WORKLOAD" in line for line in text))
        self.assertTrue(any("BRIEF" in line for line in text))
        self.assertTrue(any(label in line for line in text for label in ("PRODUCTION READY", "HIGH FAILURE RISK", "LOCKED")))

    def test_last_visible_genre_and_theme_rows_are_clickable(self) -> None:
        state = GameState(modal="new_game", new_game_step=0)
        unlock(state, "genre_story", "genre_systems", "genre_action", "genre_indie", "theme_library_1", "theme_library_2", "theme_library_3", "theme_library_4")
        with patch("main.curses.getmouse", return_value=(0, 10, 34, 0, curses.BUTTON1_CLICKED)):
            handle_mouse(state, (50, 190))
        self.assertEqual(state.selected_genre, len(GENRES) - 1)
        self.assertEqual(state.selected_secondary_genre, len(GENRES) - 1)

        state.new_game_step = 1
        with patch("main.curses.getmouse", return_value=(0, 30, 35, 0, curses.BUTTON1_CLICKED)):
            handle_mouse(state, (50, 190))
        order = topic_order(state)
        self.assertEqual(TOPICS[state.selected_topic], order[31][0])
        self.assertEqual(state.selected_secondary_topic, state.selected_topic)

    def test_large_roster_scrolls_and_mouse_uses_visible_window(self) -> None:
        state = GameState(modal="team", team_tab=1)
        founder = state.studio.team[0]
        state.studio.team = [founder]
        for index in range(1, 9):
            employee = deepcopy(founder)
            employee.name = f"Employee {index}"
            employee.founder = False
            state.studio.team.append(employee)
        state.selected_roster = 7

        text = rendered_team_text(state, 190, 24)
        self.assertTrue(any("Employee 8" in line for line in text))
        self.assertFalse(any("You *" in line for line in text))

        with patch("main.curses.getmouse", return_value=(0, 10, 4, 0, curses.BUTTON1_CLICKED)):
            handle_mouse(state, (24, 190))
        self.assertEqual(state.selected_roster, 1)

    def test_capacity_drains_reports_first_live_title(self) -> None:
        state = GameState()
        state.studio.active_sales.append(ActiveSale("Game", "Steam", 70, 20, 0.3, 0.05, 100, 10))
        self.assertIn("supporting 1 live title -4%", capacity_drains(state.studio))

    def test_compact_top_bars_keep_every_mouse_target_visible(self) -> None:
        ranges = footer_button_ranges(GameState(), 74)

        self.assertLessEqual(ranges[-1][2], 73)
        self.assertEqual([action for action, _, _ in ranges], ["new", "contracts", "upgrades"])
        self.assertLessEqual(top_tab_layout(GameState(), 74)[-1][2], 73)
        global_label, _, global_x = global_action_layout(GameState(), 74)[-1]
        self.assertLessEqual(global_x + len(global_label), 73)

        states = []
        for step in range(4):
            state = GameState(modal="new_game", new_game_step=step)
            states.append(state)
        states.extend([GameState(modal="marketing", marketing_tab=0), GameState(modal="marketing", marketing_tab=1)])
        for state in states:
            self.assertLessEqual(footer_button_ranges(state, 74)[-1][2], 73)

        game_state = GameState(modal="games")
        self.assertTrue(start_project(game_state))
        game_state.studio.current_project.work_done = game_state.studio.current_project.total_work - 1
        advance(game_state, 1)
        self.assertLessEqual(footer_button_ranges(game_state, 100)[-1][2], 99)

    def test_statistics_settings_control_save_and_quit_shortcuts(self) -> None:
        state = GameState()
        handle_key(state, ord("s"))
        self.assertEqual(state.modal, "analysis")

        handle_key(state, 27)
        self.assertTrue(state.settings_open)
        self.assertEqual(state.time_speed_index, 0)
        self.assertEqual(state.modal, "analysis")
        handle_key(state, 27)
        self.assertFalse(state.settings_open)
        self.assertEqual(state.time_speed_index, 1)
        self.assertEqual(state.modal, "analysis")

        for modal in ("main", "games", "marketing", "team", "analysis", "new_game"):
            state.modal = modal
            handle_key(state, 27)
            self.assertTrue(state.settings_open)
            self.assertEqual(state.modal, modal)
            handle_key(state, 27)
            self.assertFalse(state.settings_open)

        settings_x = next(x for label, action, x in top_control_layout(state, 120) if action == "settings")
        with patch("main.curses.getmouse", return_value=(0, settings_x, 0, 0, curses.BUTTON1_CLICKED)):
            handle_mouse(state, (36, 120))
        self.assertTrue(state.settings_open)
        handle_key(state, 27)

        screen = MagicMock()
        popup = MagicMock()
        popup.getmaxyx.return_value = (15, 40)
        screen.derwin.return_value = popup
        with patch("main.curses.color_pair", return_value=0):
            draw_settings_popup(screen, state, 120, 36)
        screen.derwin.assert_called_once_with(15, 40, 10, 40)
        popup_text = " ".join(call.args[2] for call in popup.addstr.call_args_list)
        self.assertIn("[Close]", popup_text)
        self.assertNotIn("Up/Down select", popup_text)
        popup_labels = [call.args[2] for call in popup.addstr.call_args_list]
        self.assertIn("[Close]", popup_labels)
        self.assertIn("Save", popup_labels)
        self.assertIn("Quit", popup_labels)
        self.assertNotIn("[Save]", popup_labels)
        self.assertNotIn("[Quit]", popup_labels)
        close_call = next(call for call in popup.addstr.call_args_list if call.args[2] == "[Close]")
        save_call = next(call for call in popup.addstr.call_args_list if call.args[2] == "Save")
        quit_call = next(call for call in popup.addstr.call_args_list if call.args[2] == "Quit")
        self.assertEqual((close_call.args[0], save_call.args[0], quit_call.args[0]), (6, 8, 10))
        self.assertEqual(close_call.args[3], curses.A_BOLD)
        self.assertEqual(save_call.args[3], 0)
        self.assertEqual(quit_call.args[3], 0)

        handle_key(state, 27)
        self.assertTrue(handle_key(state, 10))
        self.assertFalse(state.settings_open)
        self.assertEqual(state.time_speed_index, 1)

        state.time_speed_index = 0
        handle_key(state, 27)
        handle_key(state, 27)
        self.assertEqual(state.time_speed_index, 0)

        state.time_speed_index = 1
        handle_key(state, 27)
        handle_key(state, curses.KEY_DOWN)
        handle_key(state, curses.KEY_DOWN)
        self.assertFalse(handle_key(state, 10))
        state.settings_open = False
        state.settings_resume_on_close = False

        with tempfile.TemporaryDirectory() as directory:
            state.save_path = str(Path(directory) / "ctrl-save.json")
            state.time_speed_index = 1
            handle_key(state, 27)
            handle_key(state, curses.KEY_DOWN)
            self.assertTrue(handle_key(state, 10))
            self.assertTrue(state.settings_open)
            self.assertEqual(state.time_speed_index, 0)
            self.assertTrue(Path(state.save_path).is_file())
            loaded = load_game(state.save_path)
            self.assertEqual(loaded.time_speed_index, 1)
            handle_key(state, 27)
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
        self.assertTrue(any("CRITICS & PLAYERS" in line for line in text))
        self.assertTrue(any("AUDIENCE HEALTH" in line for line in text))
        self.assertTrue(any("FRANCHISE IP" in line for line in text))
        self.assertTrue(any(" Updates " in line for line in text))
        self.assertTrue(any(" Promotion " in line for line in text))
        self.assertTrue(any("RECOMMENDED ACTION" in line for line in text))
        self.assertTrue(any("SALES TREND" in line for line in text))
        self.assertTrue(any("PROMOTION QUEUE" in line for line in text))
        self.assertTrue(any("CATALOGUE RETURNS" in line for line in text))
        self.assertTrue(any("RECENT EVENTS" in line for line in text))
        self.assertTrue(any("Catalogue Economics & Activity" in line for line in text))
        self.assertFalse(any("permanently on sale" in line for line in text))

        game = state.studio.catalog[-1]
        queue_game_update(state, game.game_id)
        queue_game_update(state, game.game_id)
        text = rendered_games_text(state, 200, 60)
        self.assertTrue(any("UPDATE QUEUE (2) | 1 active | 1 waiting" in line for line in text))
        self.assertTrue(any(line.startswith("1. " + game.title[:10]) and "Patch" in line for line in text))
        self.assertTrue(any(line.startswith("2. " + game.title[:10]) and "Patch" in line for line in text))
        self.assertFalse(any("-> v" in line and "Patch / Bug fixes" in line for line in text), "queue lines no longer carry the version arrow")
        self.assertFalse(any(line == "CONTROLS" for line in text))

    def test_games_screen_still_renders_at_minimum_terminal_size(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)

        text = rendered_games_text(state, 74, 24)

        self.assertTrue(any("Game Catalogue | 1 game" in line for line in text))
        self.assertTrue(any("Monthly players" in line for line in text))

    def test_in_development_game_appears_in_catalogue_with_project_detail(self) -> None:
        state = GameState()
        game = self.release_first_game(state)
        self.assertTrue(start_project(state))
        project = state.studio.current_project
        state.modal = "games"
        state.selected_game = 0

        text = rendered_games_text(state, 190, 50)

        self.assertTrue(any("Game Catalogue | 2 games" in line for line in text))
        self.assertTrue(any(project.title in line and "(dev)" in line for line in text))
        self.assertTrue(any("CAPACITY" in line for line in text))
        self.assertTrue(any("CAPACITY" in line for line in text))
        self.assertTrue(any("LAUNCH FORECAST" in line for line in text))
        self.assertTrue(any("pre-launch" in line for line in text))

        handle_key(state, curses.KEY_DOWN)
        self.assertEqual(state.selected_game, 1)
        text = rendered_games_text(state, 190, 50)
        self.assertTrue(any("CRITICS & PLAYERS" in line for line in text))
        self.assertTrue(any(game.title in line for line in text))

        handle_key(state, curses.KEY_UP)
        self.assertEqual(state.selected_game, 0)
        handle_key(state, ord("u"))
        self.assertEqual(state.modal, "update_planner")
        self.assertEqual(state.selected_game, 0, "planner selection must map onto released games, not the project row")
        handle_key(state, curses.KEY_BACKSPACE)
        self.assertEqual(state.modal, "games")
        self.assertEqual(state.selected_game, 1, "returning from the planner keeps the released game selected")

    def test_hub_market_pulse_shows_up_to_ten_chart_entries(self) -> None:
        state = GameState()
        self.release_first_game(state)
        text = rendered_main_content_text(state, 190, 50)
        self.assertTrue(any(" Market Pulse " in line for line in text))
        ranked = set()
        for line in text:
            token = line.strip().split(" ", 1)[0]
            if token.isdigit() and 1 <= int(token) <= 10 and "█" in line:
                ranked.add(int(token))
        self.assertGreaterEqual(len(ranked), 8, "the hub pulse panel should render close to the full top 10")

    def test_new_studio_starts_today_with_real_overhead(self) -> None:
        state = GameState()

        self.assertEqual(state.clock.current_date, START_DATE)
        self.assertEqual(len(state.studio.team), 1)
        self.assertEqual(len(state.studio.applicants), 6)
        self.assertGreater(monthly_fixed_cost(state.studio), 3_000)

    def test_project_uses_variable_work_and_releases_to_store(self) -> None:
        state = GameState()

        self.assertTrue(start_project(state))
        self.assertGreater(state.studio.current_project.planned_weeks, 8)
        advance(state, 40)

        self.assertIsNone(state.studio.current_project)
        self.assertEqual(state.studio.released_games, 1)
        self.assertGreaterEqual(state.studio.followers, 40)
        self.assertGreater(state.studio.catalog[-1].net_revenue, 0)

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
        game = state.studio.catalog[-1]
        self.assertLess(game.known_bugs, game.actual_bugs)
        game.actual_bugs = 20
        game.known_bugs = 1
        game.reported_bug_count = 1
        state.studio.active_sales[-1].weekly_units = 10_000

        advance(state, 1)

        self.assertGreater(game.known_bugs, 1)
        self.assertLess(game.known_bugs, game.actual_bugs)
        self.assertTrue(any("complained online" in message for message in state.logs))

    def test_bug_fixing_phase_precedes_release_and_scales_with_defects(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        project = state.studio.current_project
        project.work_done = project.total_work - 1
        project.defects = 30
        project.known_defects = 30
        advance(state, 1)
        project = state.studio.current_project
        self.assertIsNotNone(project, "defects found during development trigger a bug-fixing phase before release")
        self.assertEqual(project.phase, "Bug fixing")
        self.assertGreater(project.bug_work, 0)
        weeks_in_qa = 0
        while state.studio.current_project is not None and weeks_in_qa < 40:
            state.clock.current_date += timedelta(days=7)
            state.clock.week += 1
            advance_game(state, 1)
            weeks_in_qa += 1
        self.assertIsNone(state.studio.current_project)
        game = state.studio.catalog[-1]
        self.assertLess(game.actual_bugs, 30, "the bug-fixing phase clears most defects before shipping")
        self.assertGreater(game.actual_bugs, 1, "QA must not clear every bug before release")
        known_after_launch = game.known_bugs
        for _ in range(3):
            state.clock.current_date += timedelta(days=7)
            state.clock.week += 1
            advance_game(state, 1)
        self.assertGreater(game.known_bugs, known_after_launch, "hidden bugs surface quickly after release")
        self.assertTrue(any("bug fixing" in message for message in state.logs))

    def test_bigger_teams_create_more_defects(self) -> None:
        solo = GameState()
        self.assertTrue(start_project(solo))
        team = GameState()
        for index in range(3):
            member = deepcopy(team.studio.team[0])
            member.employee_id = 10 + index
            member.founder = False
            team.studio.team.append(member)
        self.assertTrue(start_project(team))
        advance(solo, 3)
        advance(team, 3)
        self.assertGreater(team.studio.current_project.defects, solo.studio.current_project.defects)

    def test_bug_fix_update_removes_existing_bugs_but_can_miss_hidden_ones(self) -> None:
        state = GameState()
        start_project(state)
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)
        game = state.studio.catalog[-1]
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

    def test_game_profit_includes_development_staff_marketing_and_live_costs(self) -> None:
        state = GameState()
        unlock(state, "targeted_marketing")
        state.selected_marketing = 2
        self.assertTrue(start_project(state))
        advance(state, 40)
        game = state.studio.catalog[-1]

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
        game = state.studio.catalog[-1]
        sale = next(item for item in state.studio.active_sales if item.game_id == game.game_id)

        advance(state, 30)

        self.assertIn(sale, state.studio.active_sales)
        self.assertGreaterEqual(sale.weekly_units, sale.evergreen_units)
        self.assertGreater(game.units_sold, 0)
        self.assertLessEqual(game.monthly_players, game.units_sold)
        self.assertLessEqual(game.peak_monthly_players, game.units_sold)

        game.monthly_players = game.units_sold + 500
        game.peak_monthly_players = game.units_sold + 1_000
        with tempfile.TemporaryDirectory() as directory:
            state.save_path = str(Path(directory) / "players.json")
            save_game(state)
            loaded = load_game(state.save_path)
        loaded_game = loaded.studio.catalog[-1]
        self.assertEqual(loaded_game.monthly_players, loaded_game.units_sold)
        self.assertEqual(loaded_game.peak_monthly_players, loaded_game.units_sold)

    def test_queued_update_ships_and_raises_live_game_activity(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        advance(state, 40)
        game = state.studio.catalog[-1]
        self.assertTrue(queue_game_update(state, game.game_id))

        advance(state, 30)

        self.assertGreaterEqual(game.updates_released, 1)
        self.assertEqual(game.version, "1.00.10")
        self.assertIsNone(state.studio.active_update)

    def test_update_size_changes_estimated_development_length(self) -> None:
        state = GameState()
        unlock(state, "content_updates", "expansion_pipeline")
        start_project(state)
        advance(state, 40)
        game = state.studio.catalog[-1]
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
        unlock(state, "content_updates")
        start_project(state)
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)
        game = state.studio.catalog[-1]
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
        for _ in range(3):
            state.clock.current_date += timedelta(days=1)
            advance_days(state, 1)
            if state.studio.active_update.phase == "Bug fixing":
                break
        self.assertEqual(game.version, "1.00.00")
        self.assertEqual(state.studio.active_update.phase, "Bug fixing")
        self.assertEqual(state.studio.active_update.bugs_fixed, 0)

        advance(state, 1)
        self.assertEqual(game.version, "1.00.01")
        self.assertEqual(game.updates_released, 1)
        self.assertEqual(state.studio.active_update.size, "Content")

    def test_update_queue_and_versions_survive_save_load(self) -> None:
        state = GameState()
        unlock(state, "content_updates", "expansion_pipeline")
        start_project(state)
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)
        game = state.studio.catalog[-1]
        game.update_size = "Patch"
        queue_game_update(state, game.game_id)
        game.update_size = "Expansion"
        queue_game_update(state, game.game_id)
        state.studio.active_update.work_done = 12

        with tempfile.TemporaryDirectory() as directory:
            state.save_path = str(Path(directory) / "updates.json")
            save_game(state)
            loaded = load_game(state.save_path)

        self.assertEqual(loaded.studio.catalog[-1].version, "1.00.00")
        self.assertEqual(loaded.studio.active_update.target_version, "1.00.10")
        self.assertEqual(loaded.studio.active_update.work_done, 12)
        self.assertEqual(loaded.studio.update_queue[0].target_version, "1.10.10")

    def test_waiting_updates_can_be_cancelled_without_touching_active_work(self) -> None:
        state = GameState()
        unlock(state, "content_updates", "expansion_pipeline")
        self.assertTrue(start_project(state))
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)
        game = state.studio.catalog[-1]
        game.update_size = "Patch"
        self.assertTrue(queue_game_update(state, game.game_id))
        active = state.studio.active_update
        game.update_size = "Content"
        self.assertTrue(queue_game_update(state, game.game_id))
        game.update_size = "Expansion"
        self.assertTrue(queue_game_update(state, game.game_id))
        self.assertEqual(state.studio.update_queue[-1].target_version, "1.11.10")
        cash_before = state.studio.cash
        state.modal = "update_planner"

        handle_key(state, ord("c"))
        self.assertEqual(state.queue_cancellation, "update")
        self.assertTrue(any("CANCEL QUEUED UPDATE" in line for line in rendered_games_text(state, 190, 50)))
        handle_key(state, 10)

        self.assertIs(state.studio.active_update, active)
        self.assertEqual(len(state.studio.update_queue), 1)
        self.assertEqual(state.studio.update_queue[0].size, "Expansion")
        self.assertEqual(state.studio.update_queue[0].target_version, "1.10.10")
        self.assertEqual(state.studio.cash, cash_before + 675)
        self.assertEqual(state.queue_cancellation, "update")
        handle_key(state, curses.KEY_BACKSPACE)
        self.assertEqual(state.modal, "update_planner")
        self.assertEqual(state.queue_cancellation, "")

    def test_expanded_update_planner_shows_scope_area_qa_and_queue(self) -> None:
        state = GameState()
        start_project(state)
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)
        state.modal = "update_planner"
        state.games_tab = 0
        queue_game_update(state, state.studio.catalog[-1].game_id)
        queue_game_update(state, state.studio.catalog[-1].game_id)

        wide_text = rendered_games_text(state, 200, 60)
        compact_text = rendered_games_text(state, 74, 24)

        self.assertTrue(any("Update Planner & Queue" in line for line in wide_text))
        self.assertTrue(any("Selected Game" in line for line in wide_text))
        self.assertTrue(any("Hotfix" in line and "+0.00.01" in line for line in wide_text))
        self.assertTrue(any("UPDATE AREA" in line for line in wide_text))
        self.assertTrue(any("mandatory QA" in line for line in wide_text))
        self.assertTrue(any("Update Planner" in line for line in compact_text))
        self.assertTrue(any("fix" in line and "bugs" in line for line in compact_text))
        self.assertTrue(any("UPDATE QUEUE (2)" in line for line in compact_text))
        self.assertTrue(any("ACTIVE" in line and "-> v" in line for line in compact_text))
        self.assertTrue(any("WAITING" in line and "-> v" in line for line in compact_text))

    def test_rating_controls_hype_decay_and_player_retention(self) -> None:
        low = GameState()
        high = GameState()
        for state in (low, high):
            start_project(state)
            state.studio.current_project.work_done = state.studio.current_project.total_work - 1
            advance(state, 1)
            game = state.studio.catalog[-1]
            sale = state.studio.active_sales[-1]
            game.hype = 120
            sale.weekly_units = 500
        low.studio.catalog[-1].score = low.studio.active_sales[-1].score = 25
        high.studio.catalog[-1].score = high.studio.active_sales[-1].score = 90

        advance(low, 8)
        advance(high, 8)

        self.assertGreater(high.studio.active_sales[-1].weekly_units, low.studio.active_sales[-1].weekly_units * 3)
        self.assertGreater(high.studio.catalog[-1].monthly_players, low.studio.catalog[-1].monthly_players * 2)

    def test_pre_release_hype_creates_a_larger_launch_spike(self) -> None:
        organic = GameState()
        hyped = GameState()
        for state, hype in ((organic, 5), (hyped, 180)):
            start_project(state)
            state.studio.current_project.hype = hype
            state.studio.current_project.work_done = state.studio.current_project.total_work - 1
            advance(state, 1)

        self.assertGreater(hyped.studio.active_sales[-1].weekly_units, organic.studio.active_sales[-1].weekly_units * 3)

    def test_promotions_queue_and_execute_one_at_a_time(self) -> None:
        state = GameState()
        unlock(state, "promotion_basics")
        self.assertTrue(start_project(state))
        before_cash = state.studio.cash
        before_hype = state.studio.current_project.hype

        self.assertTrue(buy_promotion(state, 0, 0))
        self.assertTrue(buy_promotion(state, 0, 0))
        first, second = state.studio.active_promotions
        self.assertIn("Queued", state.logs[0])
        advance(state, 1)

        self.assertLess(state.studio.cash, before_cash)
        self.assertGreater(state.studio.current_project.hype, before_hype)
        self.assertEqual(state.studio.active_promotions, [second])
        self.assertEqual(second.weeks_left, second.total_weeks)
        self.assertNotEqual(first.promotion_id, second.promotion_id)
        advance(state, 1)
        self.assertEqual(state.studio.active_promotions, [])

    def test_waiting_promotions_can_be_cancelled_with_a_partial_refund(self) -> None:
        state = GameState()
        unlock(state, "promotion_basics", "targeted_marketing", "creator_relations")
        self.assertTrue(start_project(state))
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)
        game = state.studio.catalog[-1]
        state.studio.reputation = 100
        self.assertTrue(buy_promotion(state, game.game_id, 0))
        self.assertTrue(buy_promotion(state, game.game_id, 1))
        self.assertTrue(buy_promotion(state, game.game_id, 2))
        active = state.studio.active_promotions[0]
        marketing_before = game.marketing_cost
        cash_before = state.studio.cash
        state.modal = "marketing"

        handle_key(state, ord("c"))
        handle_key(state, curses.KEY_DOWN)
        self.assertTrue(any("CANCEL QUEUED PROMOTION" in line for line in rendered_marketing_text(state, 190, 50)))
        handle_key(state, 10)

        self.assertIs(state.studio.active_promotions[0], active)
        self.assertEqual(len(state.studio.active_promotions), 2)
        self.assertEqual(state.studio.cash, cash_before + 6_000)
        self.assertEqual(game.marketing_cost, marketing_before - 6_000)
        self.assertEqual(state.queue_cancellation, "promotion")
        handle_key(state, curses.KEY_BACKSPACE)
        self.assertEqual(state.modal, "marketing")
        self.assertEqual(state.queue_cancellation, "")

    def test_game_tab_opens_promotion_for_current_project_without_releases(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        self.assertEqual(state.modal, "games")

        labels = {action: label for label, action, _ in footer_layout(state, 120)}
        self.assertEqual(labels["game_marketing"], "[P]romotion")
        handle_key(state, ord("p"))

        self.assertEqual(state.modal, "marketing")
        self.assertEqual(state.selected_promotion_target, 0)
        self.assertEqual(state.marketing_tab, 0)

    def test_only_enter_queues_updates_while_mouse_still_selects_games(self) -> None:
        state = GameState()
        unlock(state, "promotion_basics")
        start_project(state)
        advance(state, 40)
        state.modal = "games"
        game_row = (0, 2, 4, 0, curses.BUTTON1_DOUBLE_CLICKED)
        with patch("main.curses.getmouse", return_value=game_row):
            handle_mouse(state, (38, 120))
        self.assertIsNone(state.studio.active_update)

        narrow_first_row = (0, 2, 3, 0, curses.BUTTON1_DOUBLE_CLICKED)
        with patch("main.curses.getmouse", return_value=narrow_first_row):
            handle_mouse(state, (24, 74))
        self.assertIsNone(state.studio.active_update)
        labels = {action: label for label, action, _ in footer_layout(state, 120)}
        self.assertEqual(labels["open_update_planner"], "[U]pdate Planner")
        self.assertNotIn("enter_only", labels)
        handle_key(state, 10)
        self.assertIsNone(state.studio.active_update)
        handle_key(state, ord("u"))
        self.assertEqual(state.modal, "update_planner")
        self.assertEqual(state.games_tab, 0)
        self.assertIsNone(state.studio.active_update)
        planner_text = rendered_games_text(state, 120, 38)
        self.assertTrue(any("Selected Game" in line for line in planner_text))
        self.assertTrue(any("Update Planner & Queue" in line for line in planner_text))
        handle_key(state, curses.KEY_BACKSPACE)
        self.assertEqual(state.modal, "games")
        handle_key(state, ord("u"))
        handle_key(state, 10)
        self.assertEqual(state.games_tab, 1)
        self.assertIsNone(state.studio.active_update)
        game = state.studio.catalog[-1]
        scope_before = game.update_size
        handle_key(state, curses.KEY_DOWN)
        self.assertNotEqual(game.update_size, scope_before)
        labels = {action: label for label, action, _ in footer_layout(state, 120)}
        self.assertIn("update_scope_selection", labels)
        self.assertNotIn("cycle_update_size", labels)
        self.assertNotIn("cycle_update_focus", labels)
        handle_key(state, 10)
        self.assertEqual(state.games_tab, 2)
        area_before = game.update_focus
        handle_key(state, curses.KEY_DOWN)
        self.assertNotEqual(game.update_focus, area_before)
        enter_x, enter_y = top_action_target(state, 120, "enter_only")
        footer_click = (0, enter_x, enter_y, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=footer_click):
            handle_mouse(state, (38, 120))
        self.assertIsNone(state.studio.active_update)
        handle_key(state, 10)
        self.assertIsNotNone(state.studio.active_update)
        game.update_focus = "New content"
        active_update_text = rendered_games_text(state, 190, 50)
        self.assertTrue(any(state.studio.active_update.game_title in line and "-> v" in line for line in active_update_text))

        handle_key(state, curses.KEY_BACKSPACE)
        self.assertEqual(state.games_tab, 1)
        handle_key(state, curses.KEY_BACKSPACE)
        self.assertEqual(state.games_tab, 0)
        handle_key(state, curses.KEY_BACKSPACE)
        self.assertEqual(state.modal, "games")
        handle_key(state, ord("p"))
        promotion_row = (0, 45, 11, 0, curses.BUTTON1_DOUBLE_CLICKED)
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

    def test_insolvency_blocks_play_until_enter_deletes_save_and_restarts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "insolvent.json"
            save_path.write_text("closed", encoding="utf-8")
            state = GameState(save_path=str(save_path))
            state.studio.closed = True
            state.studio.cash = -1_000

            self.assertFalse(accept_contract_offer(state))
            self.assertTrue(handle_key(state, ord("q")))
            self.assertTrue(save_path.is_file())
            self.assertTrue(state.studio.closed)

            screen = MagicMock()
            popup = MagicMock()
            popup.getmaxyx.return_value = (11, 62)
            screen.derwin.return_value = popup
            with patch("main.curses.color_pair", return_value=0):
                draw_insolvency_popup(screen, state, 120, 36)
            popup_text = " ".join(call.args[2] for call in popup.addstr.call_args_list)
            self.assertIn("Studio Insolvent", popup_text)
            self.assertIn("[Delete Save]", popup_text)

            self.assertTrue(handle_key(state, 10))
            self.assertFalse(save_path.exists())
            self.assertFalse(state.studio.closed)
            self.assertEqual(state.modal, "main")
            self.assertEqual(state.studio.cash, 75_000)

    def test_auto_contract_toggle_queues_every_eligible_offer(self) -> None:
        state = GameState()
        unlock(state, "contract_automation")
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
        unlock(state, "contract_automation")
        self.assertTrue(accept_contract(state))
        eligible_index = next(index for index, job in enumerate(state.studio.contract_offers) if job.reputation_required <= state.studio.contractor_reputation)
        self.assertTrue(accept_contract_offer(state, eligible_index))
        manual_id = state.studio.contract_queue[0].contract_id

        toggle_auto_contracts(state)
        toggle_auto_contracts(state)

        self.assertEqual([job.contract_id for job in state.studio.contract_queue], [manual_id])

    def test_metrics_render_above_bottom_controls(self) -> None:
        state = GameState()
        self.assertTrue(accept_contract(state))
        state.studio.contract.work_done = state.studio.contract.required_work * 0.4
        screen = MagicMock()
        screen.getmaxyx.return_value = (36, 120)

        with patch("main.curses.color_pair", return_value=0):
            draw_footer(screen, state, 36, 120)

        status_line = " ".join(call.args[2] for call in screen.addstr.call_args_list)
        self.assertNotIn("Next week", status_line)
        self.assertIn("░", status_line)
        self.assertIn("INDIE GAME DEV SIM", status_line)
        self.assertIn("$75,000", status_line)
        self.assertNotIn("Cash", status_line)
        self.assertNotIn("Runway", status_line)
        self.assertIn("JOB", status_line)
        self.assertIn("█", status_line)
        self.assertNotIn("Games", status_line)
        self.assertIn(f"Fans {state.studio.followers}", status_line)
        self.assertIn("[Space]", status_line)
        metric_call = next(call for call in screen.addstr.call_args_list if call.args[2].startswith("$"))
        self.assertEqual(metric_call.args[0], 34)

        self.assertTrue(start_project(state))
        with patch("main.curses.color_pair", return_value=0):
            rows = status_segments(state, 120)
            segment_text = " ".join(text for text, _ in status_segments(state, 190))
        project_row = next(text for text, _ in rows if text.startswith("DEV "))
        self.assertIn("░", project_row)
        self.assertNotIn(state.studio.current_project.title, project_row)
        self.assertIn("PTrust", segment_text)
        self.assertIn("CTrust", segment_text)

    def test_current_save_round_trip(self) -> None:
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
        self.assertEqual(len(loaded.studio.applicants), len(state.studio.applicants))
        self.assertEqual(len(loaded.studio.contract_offers), len(state.studio.contract_offers))
        self.assertEqual(loaded.marketing_tab, 1)

    def test_unsupported_save_version_is_rejected(self) -> None:
        state = GameState(selected_scope=1)
        data = state_to_data(state)
        data["version"] = 2

        with self.assertRaises(ValueError):
            state_from_data(data, "legacy-v2.json")

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

    def test_mouse_switches_top_tabs_and_statistics_views(self) -> None:
        state = GameState()
        with patch("main.curses.getmouse", return_value=(0, 20, 10, 0, curses.BUTTON1_CLICKED)):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.modal, "main")
        with patch("main.curses.getmouse", return_value=(0, 20, 35, 0, curses.BUTTON1_CLICKED)):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.modal, "main")

        stats_range = next((start, end) for action, start, end in top_tab_layout(state, 120) if action == "top_tab_3")
        click = (0, stats_range[0], 0, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=click):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.modal, "analysis")
        self.assertEqual(footer_layout(state, 120), [])
        self.assertEqual([action for _, action, _ in bottom_time_layout(state, 120)], ["previous_view", "pause", "next_view"])
        speed_before = state.time_speed_index
        handle_key(state, curses.KEY_RIGHT)
        self.assertEqual(state.analysis_view, 1)
        handle_key(state, curses.KEY_LEFT)
        self.assertEqual(state.analysis_view, 0)
        self.assertEqual(state.time_speed_index, speed_before)

        second_tab = (0, 40, 3, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=second_tab):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.analysis_view, 1)

        team_range = next((start, end) for action, start, end in top_tab_layout(state, 190) if action == "top_tab_2")
        team_click = (0, team_range[0], 0, 0, curses.BUTTON1_CLICKED)
        with patch("main.curses.getmouse", return_value=team_click):
            handle_mouse(state, (50, 190))
        self.assertEqual(state.modal, "team")

        state.modal = "marketing"
        with patch("main.curses.getmouse", return_value=(0, 20, 10, 0, curses.BUTTON3_CLICKED)):
            handle_mouse(state, (50, 190))
        self.assertEqual(state.modal, "games")

    def test_top_bar_mouse_can_open_game_and_start_new_game(self) -> None:
        state = GameState()
        game_range = next((start, end) for action, start, end in top_tab_layout(state, 120) if action == "top_tab_1")
        with patch("main.curses.getmouse", return_value=(0, game_range[0], 0, 0, curses.BUTTON1_CLICKED)):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.modal, "games")

        new_x, new_y = top_action_target(state, 120, "new")
        with patch("main.curses.getmouse", return_value=(0, new_x, new_y, 0, curses.BUTTON1_CLICKED)):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.modal, "new_game")
        self.assertEqual(state.new_game_step, -1)

        choose_x, choose_y = top_action_target(state, 120, "confirm")
        with patch("main.curses.getmouse", return_value=(0, choose_x, choose_y, 0, curses.BUTTON1_CLICKED)):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.new_game_step, 0)

    def test_top_bar_mouse_can_open_board_and_accept_a_single_contract(self) -> None:
        state = GameState()
        jobs_x, jobs_y = top_action_target(state, 120, "contracts")
        with patch("main.curses.getmouse", return_value=(0, jobs_x, jobs_y, 0, curses.BUTTON1_CLICKED)):
            handle_mouse(state, (36, 120))
        self.assertEqual(state.modal, "contracts")

        first_job = (0, 2, 4, 0, curses.BUTTON1_DOUBLE_CLICKED)
        with patch("main.curses.getmouse", return_value=first_job):
            handle_mouse(state, (36, 120))
        self.assertIsNotNone(state.studio.contract)
        self.assertEqual(len(state.studio.contract_offers), 5)

    def test_t_opens_team_e_selects_employ_and_arrows_do_not_switch_sides(self) -> None:
        state = GameState()
        handle_key(state, ord("t"))
        self.assertEqual(state.modal, "team")
        self.assertEqual(state.team_tab, 1)
        labels = {action: label for label, action, _ in footer_layout(state, 190)}
        self.assertEqual(labels["applicants"], "[E]mploy")
        self.assertEqual(labels["roster"], ">[T]eam<")
        self.assertNotIn("hire", labels)
        handle_key(state, ord("e"))
        self.assertEqual(state.team_tab, 0)
        labels = {action: label for label, action, _ in footer_layout(state, 190)}
        self.assertEqual(labels["applicants"], ">[E]mploy<")
        self.assertEqual(labels["roster"], "[T]eam")
        self.assertIn("hire", labels)
        self.assertNotIn("dismiss", labels)
        self.assertTrue(hire_candidate(state))
        state.team_tab = 1
        state.selected_roster = 0
        labels = {action: label for label, action, _ in footer_layout(state, 190)}
        self.assertEqual(labels["dismiss"], "[D]ismiss")
        self.assertEqual(labels["train"], "[L]earn")
        self.assertEqual(labels["roster"], ">[T]eam<")
        state.team_tab = 0
        handle_key(state, curses.KEY_RIGHT)
        self.assertEqual(state.team_tab, 0)
        handle_key(state, ord("t"))
        self.assertEqual(state.team_tab, 1)
        handle_key(state, curses.KEY_LEFT)
        self.assertEqual(state.team_tab, 1)
        handle_key(state, ord("g"))
        self.assertEqual(state.modal, "games")
        handle_key(state, ord("e"))
        self.assertEqual(state.modal, "games")
        handle_key(state, ord("s"))
        self.assertEqual(state.modal, "analysis")
        handle_key(state, ord("h"))
        self.assertEqual(state.modal, "main")
        handle_key(state, ord("e"))
        self.assertEqual(state.modal, "main")

    def test_team_layout_is_full_width_and_stable_across_sides(self) -> None:
        state = GameState()
        wide = team_layout(state, 190, 50)
        self.assertEqual(wide["roster"][3], 190)
        self.assertEqual(wide["roster"][0], 2)
        self.assertEqual(wide["applicants"][0] + wide["applicants"][2], 50 - 2)
        self.assertEqual(wide["detail"][1], wide["applicants"][1] + wide["applicants"][3] + 1)

        state.team_tab = 1
        self.assertEqual(team_layout(state, 190, 50), wide)

        state.team_tab = 0
        compact = team_layout(state, 100, 36)
        self.assertIsNone(compact["roster"])
        self.assertEqual(compact["applicants"][3], 100)
        state.team_tab = 1
        compact = team_layout(state, 100, 36)
        self.assertIsNone(compact["applicants"])
        self.assertEqual(compact["roster"][3], 100)

    def test_screen_hard_clears_only_when_layout_changes(self) -> None:
        import main as game_main

        game_main._LAYOUT_STATE = None
        state = GameState()
        screen = MagicMock()
        screen.getmaxyx.return_value = (36, 120)
        screen.derwin.side_effect = lambda panel_height, panel_width, _y, _x: MagicMock(**{"getmaxyx.return_value": (panel_height, panel_width)})
        with patch("main.curses.color_pair", return_value=0):
            draw_screen(screen, state)
            self.assertTrue(screen.clear.called)
            screen.clear.reset_mock()
            draw_screen(screen, state)
            self.assertFalse(screen.clear.called)
            state.team_tab = 1
            draw_screen(screen, state)
            self.assertTrue(screen.clear.called)
        game_main._LAYOUT_STATE = None

    def test_theme_list_is_tiered_by_market_signal(self) -> None:
        from ui_newgame import select_topic_at, topic_order, topic_position

        state = GameState()
        unlock(state, "theme_library_1", "theme_library_2", "theme_library_3", "theme_library_4")
        state.selected_genre = GENRES.index("Action")
        order = topic_order(state)
        self.assertEqual(len(order), 303)
        self.assertEqual(order[0][1], "fit")
        self.assertEqual(order[-1][1], "rest")
        self.assertNotIn(order[-1][0], GOOD_MATCHES["Action"])
        self.assertEqual(topic_position(state, order), 0)

        state.studio.topic_fans["Zombies"] = 5_000
        state.studio.topic_fans["Ants"] = 1_200
        order = topic_order(state)
        self.assertEqual([topic for topic, _ in order[:2]], ["Zombies", "Ants"])
        self.assertEqual(order[0][1], "strong")
        position = next(index for index, (topic, _) in enumerate(order) if topic == "Zombies")
        select_topic_at(state, order, position)
        self.assertEqual(TOPICS[state.selected_topic], "Zombies")

    def test_custom_title_and_sequel_lineage_are_persistent(self) -> None:
        state = GameState()
        state.modal = "new_game"
        handle_new_game_key(state, ord("e"))
        for character in "My First Commercial Game":
            handle_key(state, ord(character))
        handle_key(state, 10)
        self.assertTrue(start_project(state))
        advance(state, 40)

        original = state.studio.catalog[-1]
        self.assertEqual(original.title, "My First Commercial Game")
        self.assertGreater(state.studio.genre_fans[original.genre], 0)

        open_new_game(state)
        self.assertEqual(state.new_game_step, -1)
        handle_new_game_key(state, curses.KEY_DOWN)
        handle_new_game_key(state, 10)
        self.assertEqual(state.new_game_step, -2)
        handle_new_game_key(state, 10)
        self.assertEqual(state.draft_title, "My First Commercial Game II")
        self.assertEqual(state.new_game_step, 2)
        self.assertTrue(start_project(state))
        self.assertEqual(state.studio.current_project.sequel_of, original.game_id)
        self.assertEqual(state.studio.current_project.generation, 2)
        with tempfile.TemporaryDirectory() as directory:
            state.save_path = str(Path(directory) / "franchise.json")
            save_game(state)
            loaded = load_game(state.save_path)
        self.assertEqual(loaded.studio.catalog[-1].title, "My First Commercial Game")
        self.assertEqual(loaded.studio.current_project.sequel_of, original.game_id)
        loaded.studio.current_project.work_done = loaded.studio.current_project.total_work - 1
        advance(loaded, 1)
        self.assertEqual(loaded.studio.catalog[-1].title, "My First Commercial Game II")
        open_new_game(loaded)
        handle_new_game_key(loaded, curses.KEY_DOWN)
        handle_new_game_key(loaded, 10)
        handle_new_game_key(loaded, 10)
        self.assertEqual(loaded.draft_title, "My First Commercial Game III")

    def test_modern_mixed_concept_has_market_position_and_capability_gates(self) -> None:
        state = GameState()
        unlock(state, "genre_action")
        state.selected_genre = GENRES.index("Extraction Shooter")
        state.selected_secondary_genre = GENRES.index("Roguelite")
        state.selected_audience = 2
        state.selected_format = next(index for index, item in enumerate(GAME_FORMATS) if item["name"] == "MMO")

        report = market_report(state)
        self.assertGreater(report["audience"], 0)
        self.assertGreater(report["competitors"], 0)
        self.assertFalse(start_project(state))
        self.assertTrue(any("team 30" in message and "reputation 60" in message for message in state.logs))

        state.selected_format = 0
        solo_report = market_report(state)
        truth = market_truth(state)
        self.assertTrue(start_project(state))
        project = state.studio.current_project
        self.assertEqual((project.genre, project.secondary_genre), ("Extraction Shooter", "Roguelite"))
        self.assertEqual(project.target_audience, "Core players")
        self.assertEqual(project.addressable_audience, truth["audience"])
        self.assertEqual((project.forecast_audience_low, project.forecast_audience_high), (solo_report["audience_low"], solo_report["audience_high"]))
        self.assertNotEqual(project.addressable_audience, solo_report["audience"])

    def test_production_reviews_pause_and_apply_a_real_tradeoff(self) -> None:
        state = GameState(selected_scope=2, modal="analysis")
        unlock(state, "small_production")
        self.assertTrue(start_project(state))
        state.modal = "analysis"
        self.assertEqual(len(state.studio.current_project.scheduled_decisions), 1)
        while state.studio.current_project.pending_decision is None:
            advance(state, 1)

        project = state.studio.current_project
        decision = project.pending_decision
        selected_option = PRODUCTION_DECISIONS[decision]["options"][1]["name"]
        original_work = project.total_work
        self.assertEqual(state.time_speed_index, 0)
        review_text = rendered_screen_text(state, 120, 36)
        self.assertTrue(any("Production Event" in line for line in review_text))
        handle_key(state, 9)
        self.assertEqual(state.modal, "analysis")
        handle_key(state, curses.KEY_DOWN)
        handle_key(state, 10)
        self.assertIsNone(project.pending_decision)
        self.assertNotEqual(project.total_work, original_work)
        self.assertIn(selected_option, project.decisions_made[-1])
        self.assertGreater(state.time_speed_index, 0)

    def test_research_narrows_forecasts_without_changing_market_truth(self) -> None:
        state = GameState()
        state.selected_genre = GENRES.index("Battle Royale")
        state.selected_secondary_genre = state.selected_genre
        state.selected_audience = 5
        state.selected_format = 2
        truth_before = market_truth(state)
        state.studio.team[0].research = 20
        weak_report = market_report(state)
        state.studio.team[0].research = 90
        strong_report = market_report(state)

        self.assertEqual(market_truth(state), truth_before)
        self.assertGreater(strong_report["confidence"], weak_report["confidence"])
        self.assertLess(strong_report["score_high"] - strong_report["score_low"], weak_report["score_high"] - weak_report["score_low"])
        self.assertLess(strong_report["work_high"] - strong_report["work_low"], weak_report["work_high"] - weak_report["work_low"])

    def test_employee_training_grows_skill_and_salary_while_removing_capacity(self) -> None:
        state = GameState()
        state.selected_employee = max(range(len(state.studio.applicants)), key=lambda index: state.studio.applicants[index].research)
        self.assertTrue(hire_candidate(state))
        employee = state.studio.team[-1]
        state.team_tab = 1
        state.selected_roster = 0
        state.selected_training_skill = 4
        research_before = employee.research
        salary_before = employee.annual_salary
        cash_before = state.studio.cash
        output_before = contract_weekly_output(state.studio, "Generalist")

        state.modal = "team"
        handle_key(state, ord("l"))
        self.assertTrue(state.training_open)
        self.assertTrue(any("Professional Training" in line for line in rendered_screen_text(state, 120, 36)))
        state.selected_training_skill = 4
        handle_key(state, 10)
        self.assertFalse(state.training_open)
        self.assertEqual(employee.training_weeks_left, 4)
        self.assertLess(state.studio.cash, cash_before)
        self.assertLess(contract_weekly_output(state.studio, "Generalist"), output_before)
        advance(state, 4)

        self.assertEqual(employee.training_weeks_left, 0)
        self.assertEqual(employee.research, research_before + 4)
        self.assertGreater(employee.annual_salary, salary_before)
        self.assertIn(employee.quirk, QUIRKS)

    def test_founder_can_train_but_never_receives_a_salary_raise(self) -> None:
        state = GameState(modal="team", team_tab=1, selected_roster=-1)
        founder = state.studio.team[0]
        research_before = founder.research
        salary_before = founder.annual_salary

        handle_key(state, ord("l"))
        self.assertTrue(state.training_open)
        state.selected_training_skill = 4
        handle_key(state, 10)
        self.assertEqual(founder.training_weeks_left, 4)
        advance(state, 4)

        self.assertEqual(founder.research, research_before + 4)
        self.assertEqual(founder.annual_salary, salary_before)
        handle_key(state, ord("d"))
        self.assertEqual(len(state.studio.team), 1)
        self.assertTrue(any("founder cannot be dismissed" in message for message in state.logs))

    def test_two_early_generalists_produce_a_low_confidence_forecast(self) -> None:
        state = GameState()
        state.studio.team[0].research = 55
        candidate = state.studio.applicants[0]
        candidate.research = 65
        candidate.trait = "Pragmatic"
        self.assertTrue(hire_candidate(state))

        report = market_report(state)

        self.assertGreaterEqual(report["confidence"], 20)
        self.assertLessEqual(report["confidence"], 40)

    def test_paid_dlc_generates_post_launch_revenue(self) -> None:
        state = GameState()
        unlock(state, "paid_dlc")
        self.assertTrue(start_project(state))
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)
        game = state.studio.catalog[-1]
        advance(state, 1)
        game.update_size = "Paid DLC"
        revenue_before = game.net_revenue
        self.assertTrue(queue_game_update(state, game.game_id))
        job = state.studio.active_update
        job.work_done = job.required_work
        job.bugs_fixed = job.bugs_found
        advance(state, 1)
        self.assertEqual(game.dlcs_released, 1)
        self.assertGreater(game.dlc_revenue, 0)
        self.assertGreater(game.net_revenue, revenue_before)

    def release_first_game(self, state: GameState):
        self.assertTrue(start_project(state))
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)
        return state.studio.catalog[-1]

    def test_daily_ticks_move_money_continuously(self) -> None:
        state = GameState()
        game = self.release_first_game(state)
        sale = next(item for item in state.studio.active_sales if item.game_id == game.game_id)
        seen = set()
        for _ in range(7):
            state.clock.current_date += timedelta(days=1)
            advance_days(state, 1)
            seen.add(round(sale.gross_revenue, 2))
        self.assertGreater(len(seen), 3, "revenue should accrue day by day, not in weekly jumps")

    def test_release_founds_a_franchise_and_sequel_grows_it(self) -> None:
        state = GameState()
        game = self.release_first_game(state)
        franchise = franchise_by_id(state.studio, game.franchise_id)
        self.assertIsNotNone(franchise)
        self.assertEqual(franchise.entries, 1)
        awareness_after_first = franchise.awareness
        from simulation import prepare_sequel
        prepare_sequel(state, game)
        self.assertTrue(start_project(state))
        state.studio.current_project.work_done = state.studio.current_project.total_work - 1
        advance(state, 1)
        self.assertEqual(franchise.entries, 2)
        self.assertGreater(franchise.awareness, awareness_after_first)
        self.assertGreater(franchise.fatigue, 0)

    def test_media_ventures_are_gated_by_ip_rank(self) -> None:
        state = GameState()
        state.studio.cash = 5_000_000
        game = self.release_first_game(state)
        franchise = franchise_by_id(state.studio, game.franchise_id)
        franchise.awareness = 0
        franchise.reputation = 0
        franchise.total_units = 0
        self.assertFalse(buy_media_venture(state, franchise.franchise_id, 0))
        franchise.awareness = 400
        franchise.reputation = 80
        franchise.total_units = 10_000
        self.assertGreaterEqual(franchise.rank, 1)
        self.assertTrue(buy_media_venture(state, franchise.franchise_id, 0))
        self.assertFalse(buy_media_venture(state, franchise.franchise_id, 0), "same venture twice for one IP")
        film_index = next(i for i, item in enumerate(MEDIA_VENTURES) if item["key"] == "film")
        self.assertFalse(buy_media_venture(state, franchise.franchise_id, film_index))
        franchise.awareness = 2_500
        franchise.reputation = 92
        franchise.total_units = 2_500_000
        self.assertGreaterEqual(franchise.rank, MEDIA_VENTURES[film_index]["rank"])
        self.assertTrue(buy_media_venture(state, franchise.franchise_id, film_index))

    def test_film_adaptation_pays_out_on_completion(self) -> None:
        state = GameState()
        state.studio.cash = 5_000_000
        game = self.release_first_game(state)
        franchise = franchise_by_id(state.studio, game.franchise_id)
        franchise.awareness = 2_500
        franchise.reputation = 92
        franchise.total_units = 2_500_000
        film_index = next(i for i, item in enumerate(MEDIA_VENTURES) if item["key"] == "film")
        self.assertTrue(buy_media_venture(state, franchise.franchise_id, film_index))
        cash_before = state.studio.cash
        advance(state, MEDIA_VENTURES[film_index]["weeks"] + 1)
        self.assertFalse(state.studio.media_ventures)
        self.assertGreater(state.studio.cash, cash_before)
        self.assertTrue(any("film adaptation" in message for message in state.logs))

    def test_ip_ranks_require_lifetime_unit_milestones(self) -> None:
        state = GameState()
        game = self.release_first_game(state)
        franchise = franchise_by_id(state.studio, game.franchise_id)
        milestones = (
            (0, "Unknown"),
            (9_999, "Unknown"),
            (10_000, "Niche"),
            (99_999, "Niche"),
            (100_000, "Recognized"),
            (500_000, "Established"),
            (1_000_000, "Popular"),
            (2_500_000, "Famous"),
            (5_000_000, "Legendary"),
            (9_999_999, "Legendary"),
            (10_000_000, "Iconic"),
        )
        for units, expected in milestones:
            franchise.total_units = units
            self.assertEqual(franchise.rank_name, expected)

    def test_spinoff_shares_the_franchise_but_resets_generation(self) -> None:
        state = GameState()
        game = self.release_first_game(state)
        franchise = franchise_by_id(state.studio, game.franchise_id)
        self.assertTrue(prepare_spinoff(state, game))
        self.assertEqual(state.spinoff_franchise_id, franchise.franchise_id)
        self.assertIsNone(state.sequel_game_id)
        self.assertTrue(start_project(state))
        project = state.studio.current_project
        self.assertEqual(project.franchise_id, franchise.franchise_id)
        self.assertIsNone(project.sequel_of)
        self.assertEqual(project.generation, 1)

    def test_market_competitors_release_games_over_time(self) -> None:
        state = GameState()
        self.assertGreaterEqual(len(state.studio.competitors), 10)
        self.assertTrue(all(competitor.name not in ("Nintendo", "Sony", "Microsoft", "Xbox", "PlayStation") for competitor in state.studio.competitors))
        advance(state, 26)
        releases = sum(len(competitor.recent_releases) for competitor in state.studio.competitors)
        self.assertGreater(releases, 0)
        ips = sum(len(competitor.franchises) for competitor in state.studio.competitors)
        self.assertGreaterEqual(ips, 10)

    def test_charts_are_dominated_by_rival_releases_early(self) -> None:
        state = GameState()
        chart = market_chart(state)
        self.assertGreaterEqual(len(chart), 5)
        self.assertTrue(all(entry.game_id == 0 for entry in chart))
        self.assertTrue(all(entry.weekly_units > 0 for entry in chart))
        game = self.release_first_game(state)
        position = chart_positions(state).get(game.game_id)
        self.assertNotEqual(position, 1, "a first release from an unknown studio must not top the charts")
        advance(state, 26)
        self.assertTrue(any(entry.game_id == 0 for entry in market_chart(state)))

    def test_player_can_top_the_charts_with_enough_demand(self) -> None:
        state = GameState()
        game = self.release_first_game(state)
        sale = next(item for item in state.studio.active_sales if item.game_id == game.game_id)
        sale.weekly_units = 5_000_000
        advance(state, 1)
        self.assertEqual(chart_positions(state).get(game.game_id), 1)
        self.assertEqual(game.chart_peak, 1)
        self.assertTrue(any("topped the charts" in message for message in state.logs))
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "chart.json"
            state.save_path = str(save_path)
            save_game(state)
            loaded = load_game(str(save_path))
        loaded_game = loaded.studio.catalog[-1]
        self.assertEqual(loaded_game.chart_peak, 1)
        self.assertEqual(loaded_game.user_rating, game.user_rating)
        self.assertEqual(loaded_game.press_rating, game.press_rating)
        self.assertEqual(loaded_game.sales_history, game.sales_history)
        self.assertTrue(any(release.weekly_units > 0 for competitor in loaded.studio.competitors for release in competitor.recent_releases))

    def test_user_rating_falls_with_bugs_while_press_stays_settled(self) -> None:
        state = GameState()
        game = self.release_first_game(state)
        self.assertGreater(game.user_rating, 0)
        self.assertGreater(game.press_rating, 0)
        game.known_bugs = 20
        game.actual_bugs = 20
        advance(state, 4)
        self.assertLess(game.user_rating, game.press_rating)
        self.assertLess(game.user_rating, game.score)
        self.assertGreater(len(game.sales_history), 0)

    def test_market_and_ventures_survive_save_load(self) -> None:
        state = GameState()
        state.studio.cash = 5_000_000
        game = self.release_first_game(state)
        franchise = franchise_by_id(state.studio, game.franchise_id)
        franchise.awareness = 400
        franchise.reputation = 80
        franchise.total_units = 10_000
        self.assertTrue(buy_media_venture(state, franchise.franchise_id, 0))
        advance(state, 3)
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "market.json"
            state.save_path = str(save_path)
            save_game(state)
            loaded = load_game(str(save_path))
        self.assertEqual(len(loaded.studio.competitors), len(state.studio.competitors))
        self.assertEqual(franchise_by_id(loaded.studio, franchise.franchise_id).name, franchise.name)
        self.assertEqual(len(loaded.studio.media_ventures), 1)
        self.assertEqual(loaded.studio.media_ventures[0].kind, "merch")
        first = loaded.studio.competitors[0]
        self.assertTrue(first.franchises)

    def test_timed_research_unlocks_small_games(self) -> None:
        state = GameState(selected_scope=2)
        self.assertTrue(any("Small Production" in requirement for requirement in plan_requirements(state)))
        cash_before = state.studio.cash

        self.assertTrue(queue_research(state, "small_production"))
        self.assertLess(state.studio.cash, cash_before)
        self.assertIsNotNone(state.studio.active_research)
        advance(state, 20)

        self.assertTrue(has_research(state.studio, "small_production"))
        self.assertIsNone(state.studio.active_research)
        self.assertFalse(any("Small Production" in requirement for requirement in plan_requirements(state)))

    def test_scope_completion_times_scale_from_months_to_years(self) -> None:
        bands = {
            "Micro": (13, 26),
            "Compact": (26, 39),
            "Small": (39, 52),
            "Mid-size": (52, 78),
            "Ambitious": (104, 156),
            "Large": (208, 260),
            "Blockbuster": (312, 364),
        }
        completed = [node["key"] for node in RESEARCH_NODES]
        for scope_index, scope in enumerate(SCOPES):
            state = GameState(selected_scope=scope_index)
            state.studio.cash = 1_000_000_000
            state.studio.reputation = 100
            state.studio.completed_research = list(completed)
            founder = state.studio.team[0]
            while len(state.studio.team) < scope["team"]:
                employee = deepcopy(founder)
                employee.employee_id = 100 + len(state.studio.team)
                employee.founder = False
                employee.annual_salary = 50_000
                state.studio.team.append(employee)

            self.assertTrue(start_project(state))
            weeks = 0
            while state.studio.current_project and weeks <= bands[scope["name"]][1]:
                advance(state, 1)
                weeks += 1
            low, high = bands[scope["name"]]
            self.assertGreaterEqual(weeks, low, scope["name"])
            self.assertLessEqual(weeks, high, scope["name"])

    def test_soft_specialization_reduces_related_research_work(self) -> None:
        fresh = GameState()
        specialized = GameState()
        unlock(specialized, "small_production", "genre_story", "genre_systems", "theme_library_1")
        node = research_by_key("theme_library_2")

        self.assertLess(research_work_requirement(specialized.studio, node), research_work_requirement(fresh.studio, node))

    def test_activity_allocations_conserve_capacity_and_priorities(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        self.assertTrue(accept_contract(state))
        self.assertTrue(queue_research(state, "small_production"))
        allocations = activity_allocations(state.studio)
        self.assertAlmostEqual(sum(allocations.values()), 1.0)
        self.assertGreater(allocations["project"], 0)
        self.assertGreater(allocations["contract"], 0)
        self.assertGreater(allocations["research"], 0)

        unlock(state, "department_leads")
        low_research = activity_allocations(state.studio)["research"]
        cycle_work_priority(state, "research")
        normal_research = activity_allocations(state.studio)["research"]
        self.assertGreater(normal_research, low_research)
        self.assertAlmostEqual(sum(activity_allocations(state.studio).values()), 1.0)

    def test_vacation_removes_capacity_and_recovers_fatigue(self) -> None:
        state = GameState()
        employee = state.studio.team[0]
        employee.fatigue = 80
        self.assertTrue(start_project(state))
        self.assertTrue(start_employee_vacation(state, employee))
        self.assertEqual(projected_weekly_output(state.studio, state.studio.current_project.focus), 0.1)

        advance(state, 1)

        self.assertEqual(employee.vacation_weeks_left, 0)
        self.assertLess(employee.fatigue, 55)

    def test_contract_deadlines_and_work_experience_advance_weekly(self) -> None:
        state = GameState()
        self.assertTrue(accept_contract(state))
        deadline = state.studio.contract.weeks_left
        experience = state.studio.team[0].lifetime_experience

        advance(state, 1)

        self.assertLess(state.studio.contract.weeks_left, deadline)
        self.assertGreater(state.studio.team[0].lifetime_experience, experience)

    def test_promotions_and_paid_dlc_require_research(self) -> None:
        state = GameState()
        self.assertTrue(start_project(state))
        self.assertFalse(buy_promotion(state, 0, 0))
        state.studio.current_project.work_done = state.studio.current_project.total_work
        state.studio.current_project.defects = 0
        advance(state, 1)
        game = state.studio.catalog[-1]
        game.update_size = "Paid DLC"
        self.assertFalse(queue_game_update(state, game.game_id))

        unlock(state, "promotion_basics", "paid_dlc")
        self.assertTrue(buy_promotion(state, game.game_id, 0))
        self.assertTrue(queue_game_update(state, game.game_id))

    def test_portfolio_management_reduces_old_game_support_load(self) -> None:
        state = GameState()
        game = self.release_first_game(state)
        unlock(state, "portfolio_management")
        active_burn = monthly_fixed_cost(state.studio)
        self.assertEqual(activity_allocations(state.studio)["support"], 0.04)

        self.assertEqual(cycle_game_support(state, game.game_id), "Maintenance")
        self.assertEqual(activity_allocations(state.studio)["support"], 0.015)
        self.assertLess(monthly_fixed_cost(state.studio), active_burn)
        self.assertEqual(cycle_game_support(state, game.game_id), "Sunset")
        self.assertEqual(activity_allocations(state.studio)["support"], 0.0)

    def test_studio_development_tree_renders_wide_and_compact(self) -> None:
        for width, height in ((190, 50), (74, 24)):
            state = GameState(modal="upgrades")
            screen = MagicMock()
            panel = MagicMock()
            panel.getmaxyx.return_value = (height - 4, width)
            screen.derwin.return_value = panel
            with patch("main.curses.color_pair", return_value=0):
                draw_upgrades(screen, state, width, height)
            text = " ".join(call.args[2] for call in panel.addstr.call_args_list)
            self.assertIn("Studio Development", text)
            self.assertIn("Product Foundations", text)

    def test_marketing_screen_has_merch_and_media_tab(self) -> None:
        state = GameState()
        self.release_first_game(state)
        state.modal = "marketing"
        state.marketing_tab = 2
        text = rendered_marketing_text(state, 190, 50)
        self.assertTrue(any("Merch & Media" in line for line in text))
        self.assertTrue(any("Merchandise line" in line for line in text))
        self.assertTrue(any("Film adaptation" in line for line in text))
        self.assertTrue(any("IP" in line and "rank" in line for line in text))

if __name__ == "__main__":
    unittest.main()
