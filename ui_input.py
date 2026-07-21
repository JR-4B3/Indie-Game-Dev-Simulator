"""Input handling: keyboard and mouse.\n\nGlobal rules (handled before page-specific keys): modal overlays (settings,\ntraining, production review, queue cancellation, insolvency) capture input\nfirst; then Esc/Tab/title-editing; then the H/G/T/S page shortcuts, quit,\npause, and the horizontal </> actions. Each page then gets Up/Down = move\nselection, Enter = primary action, Backspace = one level up.\n\nMouse hit-testing reuses the same layout helpers the chrome and screens\ndraw with (top_control_layout, footer_button_ranges, bottom_time_layout,\npanel geometry functions), so a layout change cannot desync clicks.\n"""

from __future__ import annotations

import curses
import json

from game_data import GENRES, TOPICS
from simulation import (
    AUDIENCES,
    CHANNELS,
    CREATIVE_DIRECTIONS,
    EMPLOYEE_SKILLS,
    GAME_FORMATS,
    MARKETING,
    MEDIA_VENTURES,
    PROMOTIONS,
    RELEASE_STRATEGIES,
    SCOPES,
    TIME_SPEEDS,
    UPGRADES,
    GameState,
    accept_contract_offer,
    buy_media_venture,
    buy_promotion,
    buy_upgrade,
    cancel_queued_promotion,
    cancel_queued_update,
    cycle_game_update_focus,
    cycle_game_update_size,
    dismiss_employee,
    franchise_for_game,
    game_by_id,
    hire_candidate,
    load_game,
    prepare_sequel,
    prepare_spinoff,
    queue_game_update,
    refresh_draft_title,
    resolve_project_decision,
    selected_roster_employee,
    start_project,
    toggle_auto_contracts,
)
from ui_chrome import (
    SETTINGS_ACTION_ROWS,
    TOP_TABS,
    activate_settings_action,
    activate_top_tab,
    active_top_tab,
    bottom_time_layout,
    close_settings,
    close_training,
    confirm_training,
    cycle_top_tab,
    delete_save_and_restart,
    footer_button_ranges,
    horizontal_actions,
    open_settings,
    open_training,
    production_review_geometry,
    save_state,
    settings_popup_geometry,
    top_context_uses_second_row,
    top_control_layout,
    training_popup_geometry,
)
from ui_common import catalogue_entries, list_start, live_games, promotion_targets
from ui_contracts import contract_board_width
from ui_games import catalogue_table_height, catalogue_table_width, games_list_width, summary_panel_width
from ui_newgame import PLAN_FIELDS, base_game_choices, new_game_panel_geometry, project_kind_choices, select_topic_at, topic_order, topic_position
from ui_stats import ANALYSIS_TABS
from ui_team import team_layout, visible_roster
from ui_title import TITLE_MENU, title_layout


CTRL_S = 19
ESCAPE_KEYS = (27, getattr(curses, "KEY_EXIT", -1))



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
    state.new_game_kind = ""
    state.mix_blend = False


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


def released_selection_index(state: GameState) -> int:
    """On the Game page ``selected_game`` indexes the catalogue entries, where
    the in-development project is row 0; convert to a released-games index for
    planner and marketing actions."""
    games = live_games(state)
    offset = 1 if state.modal == "games" and state.studio.current_project else 0
    return max(0, min(state.selected_game - offset, len(games) - 1))


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
        if live_games(state):
            state.selected_game = released_selection_index(state)
            state.modal = "update_planner"
            state.games_tab = 0
            state.queue_cancellation = ""
        else:
            state.log("Release a game before planning updates.")
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
            project_selected = state.modal == "games" and state.studio.current_project and state.selected_game == 0
            selected_id = 0 if project_selected else (games[released_selection_index(state)].game_id if games else 0)
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
        if state.marketing_tab == 2 and targets:
            target_id = targets[state.selected_promotion_target][0]
            target_game = game_by_id(state.studio, target_id) if target_id else None
            franchise = franchise_for_game(state.studio, target_game) if target_game else None
            if franchise is not None:
                buy_media_venture(state, franchise.franchise_id, state.selected_venture)
        elif targets:
            buy_promotion(state, targets[state.selected_promotion_target][0], state.selected_promotion)
    elif action == "marketing_selection":
        if state.marketing_tab == 0:
            targets = promotion_targets(state)
            if targets:
                state.selected_promotion_target = (state.selected_promotion_target + 1) % len(targets)
        elif state.marketing_tab == 2:
            state.selected_venture = (state.selected_venture + 1) % len(MEDIA_VENTURES)
        else:
            state.selected_promotion = (state.selected_promotion + 1) % len(PROMOTIONS)
    elif action == "toggle_marketing_panel":
        state.marketing_tab = 2 if state.marketing_tab == 1 else 1
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
            if state.marketing_tab in (1, 2):
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
        handle_new_game_key(state, curses.KEY_DOWN)
    elif action == "new_game_selection":
        handle_new_game_key(state, curses.KEY_DOWN)
    elif action == "toggle_blend":
        if state.modal == "new_game" and state.new_game_step in (0, 1):
            handle_new_game_key(state, ord("b"))
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


def open_blend(state: GameState) -> None:
    """Enter blend picking: remember the current mix so B can cancel it."""
    attribute = "selected_secondary_genre" if state.new_game_step == 0 else "selected_secondary_topic"
    state.mix_blend_backup = (state.new_game_step, getattr(state, attribute))
    state.mix_blend = True


def close_blend(state: GameState, confirm: bool) -> None:
    """Leave blend picking: Enter keeps the new mix, B restores the old one."""
    if not state.mix_blend:
        return
    if not confirm:
        step, value = state.mix_blend_backup
        attribute = "selected_secondary_genre" if step == 0 else "selected_secondary_topic"
        setattr(state, attribute, value)
    state.mix_blend = False


def handle_new_game_key(state: GameState, key: int) -> None:
    if state.new_game_step == -1:
        choices = project_kind_choices(state)
        if key in (10, 13, curses.KEY_ENTER):
            kind, _, enabled = choices[state.selected_sequel_choice]
            if not enabled:
                if kind == "engine":
                    state.log("Building your own engine is not available yet.")
                else:
                    state.log("Release a game first to unlock this option.")
                return
            if kind == "new":
                state.new_game_kind = ""
                state.sequel_game_id = None
                state.selected_secondary_genre = state.selected_genre
                state.selected_secondary_topic = state.selected_topic
                state.new_game_step = 0
                state.title_roll += 1
                refresh_draft_title(state)
            else:
                state.new_game_kind = kind
                state.new_game_step = -2
                state.selected_sequel_choice = 0
        elif key in (8, 127, curses.KEY_BACKSPACE):
            state.modal = "games"
        elif key == curses.KEY_UP:
            state.selected_sequel_choice = (state.selected_sequel_choice - 1) % len(choices)
        elif key == curses.KEY_DOWN:
            state.selected_sequel_choice = (state.selected_sequel_choice + 1) % len(choices)
        return
    if state.new_game_step == -2:
        choices = base_game_choices(state)
        if not choices:
            state.new_game_step = -1
            return
        if key in (10, 13, curses.KEY_ENTER):
            choice = choices[state.selected_sequel_choice]
            if state.new_game_kind == "spinoff":
                if not prepare_spinoff(state, choice):
                    return
            else:
                prepare_sequel(state, choice)
        elif key in (8, 127, curses.KEY_BACKSPACE):
            state.new_game_step = -1
            state.selected_sequel_choice = 0
        elif key == curses.KEY_UP:
            state.selected_sequel_choice = (state.selected_sequel_choice - 1) % len(choices)
        elif key == curses.KEY_DOWN:
            state.selected_sequel_choice = (state.selected_sequel_choice + 1) % len(choices)
        return
    previous_concept = (state.selected_genre, state.selected_secondary_genre, state.selected_topic, state.selected_secondary_topic)
    if key in (10, 13, curses.KEY_ENTER):
        if state.mix_blend and state.new_game_step in (0, 1):
            close_blend(state, confirm=True)
        elif state.new_game_step < 3:
            state.new_game_step += 1
        else:
            start_project(state)
    elif key in (8, 127, curses.KEY_BACKSPACE):
        if state.mix_blend:
            close_blend(state, confirm=False)
        else:
            state.new_game_step = max(-1, state.new_game_step - 1)
    elif key in (ord("b"), ord("B")) and state.new_game_step in (0, 1):
        if state.mix_blend:
            close_blend(state, confirm=False)
        else:
            open_blend(state)
    elif key in (ord("e"), ord("E")):
        state.naming_game = True
        state.draft_title = ""
    elif key in (ord("r"), ord("R")):
        state.title_roll += 1
        refresh_draft_title(state)
    elif key == curses.KEY_UP:
        if state.new_game_step == 0:
            if state.mix_blend:
                state.selected_secondary_genre = (state.selected_secondary_genre - 1) % len(GENRES)
            else:
                had_blend = state.selected_secondary_genre != state.selected_genre
                state.selected_genre = (state.selected_genre - 1) % len(GENRES)
                if not had_blend:
                    state.selected_secondary_genre = state.selected_genre
        elif state.new_game_step == 1:
            order = topic_order(state)
            if state.mix_blend:
                current = TOPICS[state.selected_secondary_topic]
                position = next((index for index, (topic, _) in enumerate(order) if topic == current), 0)
                state.selected_secondary_topic = TOPICS.index(order[(position - 1) % len(order)][0])
            else:
                had_blend = state.selected_secondary_topic != state.selected_topic
                select_topic_at(state, order, topic_position(state, order) - 1)
                if not had_blend:
                    state.selected_secondary_topic = state.selected_topic
        elif state.new_game_step == 2:
            state.selected_focus = (state.selected_focus - 1) % 7
        else:
            state.selected_channel = (state.selected_channel - 1) % len(CHANNELS)
    elif key == curses.KEY_DOWN:
        if state.new_game_step == 0:
            if state.mix_blend:
                state.selected_secondary_genre = (state.selected_secondary_genre + 1) % len(GENRES)
            else:
                had_blend = state.selected_secondary_genre != state.selected_genre
                state.selected_genre = (state.selected_genre + 1) % len(GENRES)
                if not had_blend:
                    state.selected_secondary_genre = state.selected_genre
        elif state.new_game_step == 1:
            order = topic_order(state)
            if state.mix_blend:
                current = TOPICS[state.selected_secondary_topic]
                position = next((index for index, (topic, _) in enumerate(order) if topic == current), 0)
                state.selected_secondary_topic = TOPICS.index(order[(position + 1) % len(order)][0])
            else:
                had_blend = state.selected_secondary_topic != state.selected_topic
                select_topic_at(state, order, topic_position(state, order) + 1)
                if not had_blend:
                    state.selected_secondary_topic = state.selected_topic
        elif state.new_game_step == 2:
            state.selected_focus = (state.selected_focus + 1) % 7
        else:
            state.selected_channel = (state.selected_channel + 1) % len(CHANNELS)
    elif key in (curses.KEY_LEFT, curses.KEY_RIGHT) and state.new_game_step == 2:
        delta = -1 if key == curses.KEY_LEFT else 1
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
        if state.team_tab == 0:
            if state.studio.applicants:
                state.selected_employee = (state.selected_employee - 1) % len(state.studio.applicants)
        else:
            choices = len(state.studio.team)
            state.selected_roster = state.selected_roster % choices - 1
    elif key == curses.KEY_DOWN:
        if state.team_tab == 0:
            if state.studio.applicants:
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
        elif state.modal == "games" and (state.studio.catalog or state.studio.current_project):
            entry_count = len(state.studio.catalog) + (1 if state.studio.current_project else 0)
            state.selected_game = (state.selected_game + (-1 if wheel_up else 1)) % entry_count
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
        board_width = contract_board_width(width)
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
        rows = catalogue_entries(state) if state.modal == "games" else [(game.game_id, game) for game in games]
        top = 2
        if width >= 120:
            row = y - top - 2
            panel_height = height - 4
            catalog_height = catalogue_table_height(len(rows), panel_height)
            in_catalog = top + 2 <= y < top + catalog_height - 1 and x <= catalogue_table_width(width)
            visible = catalog_height - 3
        else:
            row = y - top - 1
            list_width = games_list_width(width, state.modal == "update_planner")
            in_catalog = x <= list_width and row >= 0
            visible = height - 6
        catalog_active = state.modal == "games" or state.games_tab == 0
        if catalog_active and in_catalog and row >= 0 and rows:
            start = list_start(state.selected_game, len(rows), visible)
            index = start + row
            if 0 <= index < len(rows):
                state.selected_game = index
                if double_click and state.modal == "update_planner":
                    state.games_tab = 1
        return

    if state.modal == "marketing":
        targets = promotion_targets(state)
        panel_height = height - 4
        catalog_height = catalogue_table_height(len(targets), panel_height)
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
            summary_width = summary_panel_width(width)
            option_row = y - (bottom_y + 2)
            if x > summary_width and state.marketing_tab == 2 and 0 <= option_row < len(MEDIA_VENTURES):
                state.selected_venture = option_row
                if double_click and targets:
                    target_id = targets[state.selected_promotion_target][0]
                    target_game = game_by_id(state.studio, target_id) if target_id else None
                    franchise = franchise_for_game(state.studio, target_game) if target_game else None
                    if franchise is not None:
                        buy_media_venture(state, franchise.franchise_id, option_row)
            elif x > summary_width and 0 <= option_row < len(PROMOTIONS):
                state.marketing_tab = 1
                state.selected_promotion = option_row
                if double_click and targets:
                    buy_promotion(state, targets[state.selected_promotion_target][0], option_row)
        return

    if state.modal == "team":
        layout = team_layout(state, width, height)
        rect = layout["roster"]
        if rect and rect[0] < y < rect[0] + rect[2] - 1 and rect[1] <= x < rect[1] + rect[3]:
            selected = selected_roster_employee(state)
            selected_index = state.studio.team.index(selected) if selected in state.studio.team else 0
            state.team_tab = 1
            row = y - rect[0] - 2
            visible_team = visible_roster(state.studio.team, rect[2], selected_index)
            if 0 <= row < len(visible_team):
                employee = visible_team[row]
                if employee.founder:
                    state.selected_roster = -1
                else:
                    removable = [item for item in state.studio.team if not item.founder]
                    state.selected_roster = removable.index(employee)
            return
        rect = layout["applicants"]
        if rect and rect[0] < y < rect[0] + rect[2] - 1 and rect[1] <= x < rect[1] + rect[3]:
            state.team_tab = 0
            visible = max(1, rect[2] - 3)
            index = list_start(state.selected_employee, len(state.studio.applicants), visible) + y - rect[0] - 2
            if 0 <= index < len(state.studio.applicants):
                state.selected_employee = index
                if double_click:
                    hire_candidate(state)
        return

    if state.modal == "new_game":
        if state.new_game_step in (-2, -1):
            choices = base_game_choices(state) if state.new_game_step == -2 else project_kind_choices(state)
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
        top_height, genre_width, theme_width, plan_width, storefront_height = new_game_panel_geometry(width, height)
        plan_x = genre_width + theme_width + 2
        if 4 <= y < 2 + top_height - 1:
            visible = top_height - 3
            row = y - 4
            target_step = 0 if x < genre_width else 1 if genre_width < x < plan_x else 2
            if state.mix_blend and target_step != state.new_game_step:
                close_blend(state, confirm=False)
            if x < genre_width:
                was_blend = state.mix_blend
                state.new_game_step = 0
                cursor = state.selected_secondary_genre if was_blend else state.selected_genre
                index = list_start(cursor, len(GENRES), visible) + row
                if was_blend:
                    state.selected_secondary_genre = min(index, len(GENRES) - 1)
                else:
                    had_blend = state.selected_secondary_genre != state.selected_genre
                    state.selected_genre = min(index, len(GENRES) - 1)
                    if not had_blend:
                        state.selected_secondary_genre = state.selected_genre
            elif genre_width < x < plan_x:
                was_blend = state.mix_blend
                state.new_game_step = 1
                order = topic_order(state)
                if was_blend:
                    current = TOPICS[state.selected_secondary_topic]
                    position = next((i for i, (topic, _) in enumerate(order) if topic == current), 0)
                    start = list_start(position, len(order), visible)
                    state.selected_secondary_topic = TOPICS.index(order[min(start + row, len(order) - 1)][0])
                else:
                    had_blend = state.selected_secondary_topic != state.selected_topic
                    start = list_start(topic_position(state, order), len(order), visible)
                    select_topic_at(state, order, min(start + row, len(order) - 1))
                    if not had_blend:
                        state.selected_secondary_topic = state.selected_topic
            elif x >= plan_x:
                was_step = state.new_game_step
                state.new_game_step = 2
                if y == 3:
                    state.naming_game = True
                    state.draft_title = ""
                    return
                if y == 13 and was_step == 2:
                    _, attribute, options = PLAN_FIELDS[state.selected_focus]
                    chip_x = 11
                    for index, option in enumerate(options):
                        chip = option["name"]
                        if chip_x + len(chip) > plan_width - 2:
                            break
                        if plan_x + chip_x <= x < plan_x + chip_x + len(chip):
                            setattr(state, attribute, index)
                            break
                        chip_x += len(chip) + 2
                    return
                field = y - 6
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


def activate_title_choice(state: GameState) -> bool:
    choice = TITLE_MENU[state.title_menu_index]
    if choice == "New Game":
        fresh_state = GameState(save_path=state.save_path)
        state.__dict__.clear()
        state.__dict__.update(fresh_state.__dict__)
        state.log("Started a new studio from the title screen.")
        return True
    if choice == "Load Game":
        try:
            loaded_state = load_game(state.save_path)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            state.title_message = f"Could not load save: {error}"
            return True
        state.__dict__.clear()
        state.__dict__.update(loaded_state.__dict__)
        state.log(f"Loaded studio from {state.save_path}.")
        return True
    if choice == "Settings":
        open_settings(state)
        return True
    return False


def handle_title_key(state: GameState, key: int, dimensions: tuple[int, int] | None = None) -> bool:
    if key == curses.KEY_UP:
        state.title_menu_index = (state.title_menu_index - 1) % len(TITLE_MENU)
        state.title_message = ""
    elif key == curses.KEY_DOWN:
        state.title_menu_index = (state.title_menu_index + 1) % len(TITLE_MENU)
        state.title_message = ""
    elif key in (10, 13, curses.KEY_ENTER):
        return activate_title_choice(state)
    elif key in ESCAPE_KEYS or key in (ord("q"), ord("Q")):
        return False
    elif key == curses.KEY_MOUSE and dimensions is not None:
        try:
            _, _x, y, _, buttons = curses.getmouse()
        except curses.error:
            return True
        height, width = dimensions
        if buttons & getattr(curses, "BUTTON4_PRESSED", 0):
            state.title_menu_index = (state.title_menu_index - 1) % len(TITLE_MENU)
            state.title_message = ""
        elif buttons & getattr(curses, "BUTTON5_PRESSED", 0):
            state.title_menu_index = (state.title_menu_index + 1) % len(TITLE_MENU)
            state.title_message = ""
        elif buttons & (
            getattr(curses, "BUTTON1_CLICKED", 0)
            | getattr(curses, "BUTTON1_RELEASED", 0)
            | getattr(curses, "BUTTON1_PRESSED", 0)
        ):
            for index, (row, _item_x, _label) in enumerate(title_layout(width, height)["items"]):
                if y == row:
                    state.title_menu_index = index
                    return activate_title_choice(state)
    return True


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
    if state.title_screen:
        return handle_title_key(state, key, dimensions)
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
        entry_count = len(games) + (1 if project else 0)
        if project and project.pending_decision is not None and key in (curses.KEY_UP, curses.KEY_DOWN):
            state.selected_project_decision = (state.selected_project_decision + 1) % 2
        elif project and project.pending_decision is not None and key in (10, 13, curses.KEY_ENTER):
            resolve_project_decision(state, state.selected_project_decision)
        elif key in (8, 127, curses.KEY_BACKSPACE):
            state.modal = "main"
        elif key in (ord("u"), ord("U")) and games:
            state.selected_game = released_selection_index(state)
            state.modal = "update_planner"
            state.games_tab = 0
        elif key in (ord("n"), ord("N")):
            open_new_game(state)
        elif key == curses.KEY_UP and entry_count:
            state.selected_game = (state.selected_game - 1) % entry_count
        elif key == curses.KEY_DOWN and entry_count:
            state.selected_game = (state.selected_game + 1) % entry_count
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
                if state.studio.current_project:
                    state.selected_game += 1
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
        elif key in (ord("m"), ord("M")):
            state.marketing_tab = 2 if state.marketing_tab == 1 else 1
        elif key in (8, 127, curses.KEY_BACKSPACE):
            if state.marketing_tab in (1, 2):
                state.marketing_tab = 0
            else:
                state.modal = "games"
        elif key in (curses.KEY_UP, curses.KEY_DOWN):
            delta = -1 if key == curses.KEY_UP else 1
            if state.marketing_tab == 0 and targets:
                state.selected_promotion_target = (state.selected_promotion_target + delta) % len(targets)
            elif state.marketing_tab == 1:
                state.selected_promotion = (state.selected_promotion + delta) % len(PROMOTIONS)
            elif state.marketing_tab == 2:
                state.selected_venture = (state.selected_venture + delta) % len(MEDIA_VENTURES)
        elif key in (10, 13, curses.KEY_ENTER) and state.marketing_tab == 0:
            state.marketing_tab = 1
        elif key in (10, 13, curses.KEY_ENTER) and state.marketing_tab == 2 and targets:
            target_id = targets[state.selected_promotion_target][0]
            target_game = game_by_id(state.studio, target_id) if target_id else None
            franchise = franchise_for_game(state.studio, target_game) if target_game else None
            if franchise is None:
                state.log("Merch and media deals need a released game with an IP.")
            else:
                buy_media_venture(state, franchise.franchise_id, state.selected_venture)
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
        elif key in (curses.KEY_UP, curses.KEY_DOWN) and state.analysis_view in (2, 3, 4):
            count = len(GENRES) if state.analysis_view == 2 else len(state.studio.catalog) if state.analysis_view == 3 else len(state.studio.competitors)
            if count:
                state.selected_stat = (state.selected_stat + (-1 if key == curses.KEY_UP else 1)) % count
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
