"""Input handling: keyboard and mouse.\n\nGlobal rules (handled before page-specific keys): modal overlays (settings,\ntraining, production review, queue cancellation, insolvency) capture input\nfirst; then Esc/Tab/title-editing; then the H/G/T/S page shortcuts, quit,\npause, and the horizontal </> actions. Each page then gets Up/Down = move\nselection, Enter = primary action, Backspace = one level up.\n\nMouse hit-testing reuses the same layout helpers the chrome and screens\ndraw with (top_control_layout, footer_button_ranges, bottom_time_layout,\npanel geometry functions), so a layout change cannot desync clicks.\n"""

from __future__ import annotations

import curses
import json

from game_data import GENRES, TOPICS
from simulation import (
    ANNOUNCEMENT_STRATEGIES,
    AUDIENCES,
    CHANNELS,
    COMMUNITY_ACTIONS,
    CREATIVE_DIRECTIONS,
    EMPLOYEE_SKILLS,
    GAME_FORMATS,
    LOAN_OFFERS,
    MARKETING,
    MEDIA_VENTURES,
    MONETIZATION_MODELS,
    PRICE_POINTS,
    PROMOTIONS,
    PUBLISHER_OFFERS,
    RELEASE_POLICIES,
    RESEARCH_BRANCHES,
    RELEASE_STRATEGIES,
    SCOPES,
    TIME_SPEEDS,
    GameState,
    accept_contract_offer,
    buy_media_venture,
    take_loan,
    select_publisher,
    buy_promotion,
    buy_upgrade,
    cancel_queued_promotion,
    cancel_queued_research,
    cancel_queued_update,
    cycle_game_price,
    cycle_game_update_focus,
    cycle_game_update_size,
    cycle_game_support,
    cycle_price_point,
    cycle_work_priority,
    dismiss_employee,
    franchise_for_game,
    game_by_id,
    hire_candidate,
    load_game,
    queue_game_update,
    has_research,
    research_requirement_for_channel,
    channel_lock_reason,
    storefront_display_order,
    research_requirement_for_format,
    research_requirement_for_marketing,
    research_requirement_for_monetization,
    research_requirement_for_scope,
    research_requirement_for_strategy,
    research_nodes_for_branch,
    refresh_draft_title,
    launch_early_access,
    release_ready_project,
    resolve_project_decision,
    selected_roster_employee,
    start_employee_vacation,
    take_community_action,
    toggle_platform_selection,
    toggle_auto_contracts,
    start_concept_project,
    start_experiment,
    begin_design_review,
    shelve_concept,
    commit_design_plan,
    idea_engine,
)
from ui_chrome import (
    CANCEL_PROJECT_ACTION_ROWS,
    SETTINGS_ACTION_ROWS,
    TOP_TABS,
    activate_settings_action,
    activate_top_tab,
    active_top_tab,
    bottom_time_layout,
    cancel_project_popup_geometry,
    close_cancel_project,
    close_settings,
    close_training,
    confirm_cancel_project,
    confirm_training,
    cycle_top_tab,
    delete_save_and_restart,
    footer_button_ranges,
    horizontal_actions,
    open_cancel_project,
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
from ui_newgame import design_review_layout, shelf_rows, ordered_shelf, stage_banner_line
from ui_stats import ANALYSIS_TABS
from ui_team import team_layout, visible_roster
from ui_title import TITLE_MENU, title_layout
from ui_saves import close_save_picker, confirm_save_slot, open_save_picker


CTRL_S = 19
ESCAPE_KEYS = (27, getattr(curses, "KEY_EXIT", -1))



MARKETING_TAB_CYCLE = {0: 1, 1: 2, 2: 3, 3: 1}


def cycle_marketing_tab(state: GameState) -> None:
    """Rotate the planning tabs: catalogue → promotions → community → merch & media."""
    state.marketing_tab = MARKETING_TAB_CYCLE.get(state.marketing_tab, 1)


def toggle_pause(state: GameState) -> None:
    if state.time_speed_index == 0:
        state.time_speed_index = max(1, state.resume_speed_index)
    else:
        state.resume_speed_index = state.time_speed_index
        state.time_speed_index = 0


def open_idea_shelf(state: GameState, origin: str = "main") -> None:
    if state.studio.current_project:
        if state.studio.current_project.stage == "concept":
            state.modal = "concept"
            return
        state.log("Ship or cancel the current project before starting another.")
        return
    state.modal = "ideas"
    state.shelf_origin = origin
    state.selected_idea = 0
    state.sequel_game_id = None
    state.spinoff_franchise_id = None
    state.new_game_kind = ""


# Backwards-compatible name used by older call sites and tests.
open_new_game = open_idea_shelf


def design_review_row_count(state: GameState) -> int:
    packages = state.studio.current_project.gdd.get("presentation_options", []) if state.studio.current_project else []
    tweak_axes = 5 if state.tweak_presentation else 0
    plan_fields = 11
    return 1 + tweak_axes + plan_fields + 1 + 1  # presentation + axes + plan + storefront + commit


def handle_ideas_key(state: GameState, key: int) -> None:
    ideas = ordered_shelf(state)
    if key in (8, 127, curses.KEY_BACKSPACE, 27):
        state.modal = state.shelf_origin if state.shelf_origin in ("main", "games") else "main"
    elif key == curses.KEY_UP and ideas:
        state.selected_idea = (state.selected_idea - 1) % len(ideas)
    elif key == curses.KEY_DOWN and ideas:
        state.selected_idea = (state.selected_idea + 1) % len(ideas)
    elif key in (ord("d"), ord("D")) and ideas:
        idea = ideas[state.selected_idea]
        state.studio.idea_shelf.remove(idea)
        state.log(f"Discarded the idea {idea.title}.")
        state.selected_idea = min(state.selected_idea, max(0, len(state.studio.idea_shelf) - 1))
    elif key in (10, 13, curses.KEY_ENTER) and ideas:
        idea = ideas[state.selected_idea]
        if start_concept_project(state, idea):
            state.selected_experiment = 0


def handle_concept_key(state: GameState, key: int) -> None:
    project = state.studio.current_project
    if key in (8, 127, curses.KEY_BACKSPACE, 27):
        state.modal = "games"
        state.selected_game = 0
        state.log("Concept remains open. Select it in Games and press Enter or C to resume.")
        return
    if project is None or project.stage != "concept":
        state.modal = "games"
        return
    experiments = available_concept_experiments(state)
    if project.pending_decision is not None:
        return
    if key == curses.KEY_UP and experiments and not project.active_experiment:
        state.selected_experiment = (state.selected_experiment - 1) % len(experiments)
    elif key == curses.KEY_DOWN and experiments and not project.active_experiment:
        state.selected_experiment = (state.selected_experiment + 1) % len(experiments)
    elif key in (10, 13, curses.KEY_ENTER) and experiments and not project.active_experiment:
        start_experiment(state, experiments[state.selected_experiment].key)
    elif key in (ord("e"), ord("E")):
        begin_design_review(state)
    elif key in (ord("s"), ord("S")):
        shelve_concept(state)
    elif key in (ord("x"), ord("X")):
        open_cancel_project(state)


def available_concept_experiments(state: GameState):
    project = state.studio.current_project
    if project is None or project.stage != "concept":
        return []
    gdd = project.gdd

    class _View:
        hook = gdd.get("hook", "")
        technical_doubt = float(gdd.get("technical_doubt", 0.0))
        tags = gdd.get("tags", [])

    return idea_engine.available_experiments(_View())


def design_review_rows(state: GameState) -> list[tuple[str, str]]:
    """(kind, key) rows for the design review; drives cursor behavior."""
    rows = [("presentation", "")]
    if state.tweak_presentation:
        rows += [("tweak", key) for key in ("form", "style", "camera", "movement", "density")]
    rows += [
        ("plan", "selected_scope"),
        ("plan", "selected_format"),
        ("plan", "selected_audience"),
        ("plan", "selected_creative_primary"),
        ("plan", "selected_creative_secondary"),
        ("plan", "selected_monetization"),
        ("plan", "selected_price"),
        ("plan", "selected_announcement"),
        ("plan", "selected_release_policy"),
        ("plan", "selected_release_strategy"),
        ("plan", "selected_marketing"),
        ("store", ""),
        ("commit", ""),
    ]
    return rows


def handle_design_review_key(state: GameState, key: int) -> None:
    project = state.studio.current_project
    if project is None or project.stage != "design":
        state.modal = "games"
        return
    rows = design_review_rows(state)
    state.selected_design_focus = max(0, min(state.selected_design_focus, len(rows) - 1))
    kind, row_key = rows[state.selected_design_focus]
    packages = project.gdd.get("presentation_options", [])
    if key in (ord("e"), ord("E")):
        state.naming_game = True
        state.draft_title = ""
        return
    if key in (ord("r"), ord("R")):
        state.title_roll += 1
        refresh_draft_title(state)
        return
    if key in (8, 127, curses.KEY_BACKSPACE, 27):
        project.stage = "concept"
        state.modal = "concept"
        if state.design_review_resume_on_close and state.time_speed_index == 0:
            state.time_speed_index = max(1, state.resume_speed_index)
        state.design_review_resume_on_close = False
        return
    if key == curses.KEY_UP:
        state.selected_design_focus = (state.selected_design_focus - 1) % len(rows)
        return
    if key == curses.KEY_DOWN:
        state.selected_design_focus = (state.selected_design_focus + 1) % len(rows)
        return
    delta = -1 if key in (curses.KEY_LEFT, ord("<")) else 1 if key in (curses.KEY_RIGHT, ord(">")) else 0
    if key in (ord("t"), ord("T")):
        state.tweak_presentation = not state.tweak_presentation
        state.selected_design_focus = 0
        return
    if kind == "presentation":
        if delta:
            if packages:
                state.selected_presentation = (state.selected_presentation + delta) % len(packages)
        elif key in (10, 13, curses.KEY_ENTER):
            state.tweak_presentation = True
            state.selected_design_focus = 1
        return
    if kind == "tweak":
        from sim_core import ideas as idea_axes
        axes = {"form": idea_axes.FORMS, "style": idea_axes.STYLES, "camera": idea_axes.CAMERAS, "movement": idea_axes.MOVEMENTS, "density": idea_axes.DENSITIES}
        values = axes[row_key]
        if delta:
            current = state.design_tweaks.get(row_key) or (packages[state.selected_presentation][row_key] if packages else values[0])
            index = values.index(current) if current in values else 0
            state.design_tweaks[row_key] = values[(index + delta) % len(values)]
        return
    if kind == "plan":
        fields = (
            ("selected_scope", len(SCOPES)),
            ("selected_format", len(GAME_FORMATS)),
            ("selected_audience", len(AUDIENCES)),
            ("selected_creative_primary", len(CREATIVE_DIRECTIONS)),
            ("selected_creative_secondary", len(CREATIVE_DIRECTIONS)),
            ("selected_monetization", len(MONETIZATION_MODELS)),
            ("selected_price", len(PRICE_POINTS) + 1),
            ("selected_announcement", len(ANNOUNCEMENT_STRATEGIES)),
            ("selected_release_policy", len(RELEASE_POLICIES)),
            ("selected_release_strategy", len(RELEASE_STRATEGIES)),
            ("selected_marketing", len(MARKETING)),
        )
        plan_attributes = [row[1] for row in rows if row[0] == "plan"]
        attribute, count = fields[plan_attributes.index(row_key)]
        if attribute == "selected_price":
            if delta:
                cycle_price_point(state, delta)
        elif delta:
            cycle_plan_option(state, plan_attributes.index(row_key), attribute, count, delta)
        elif key in (10, 13, curses.KEY_ENTER):
            cycle_plan_option(state, plan_attributes.index(row_key), attribute, count, 1)
        return
    if kind == "store":
        if delta:
            cycle_channel_selection(state, delta)
        elif key in (ord("x"), ord("X")):
            toggle_platform_selection(state, state.selected_channel)
        return
    if kind == "commit" and key in (10, 13, curses.KEY_ENTER):
        commit_design_plan(state)


def handle_new_game_key(state: GameState, key: int) -> None:
    """Legacy name kept for old call sites: route to the new pipeline."""
    if state.modal == "ideas":
        handle_ideas_key(state, key)


def cycle_contract_selection(state: GameState, delta: int) -> None:
    offers = state.studio.contract_offers
    eligible = [index for index, offer in enumerate(offers) if offer.reputation_required <= state.studio.contractor_reputation]
    if not eligible:
        state.selected_contract = -1
        return
    if state.selected_contract not in eligible:
        state.selected_contract = eligible[0 if delta > 0 else -1]
        return
    position = eligible.index(state.selected_contract)
    state.selected_contract = eligible[(position + delta) % len(eligible)]


def plan_option_unlocked(state: GameState, field_index: int, option_index: int) -> bool:
    requirement_functions = {
        0: research_requirement_for_scope,
        1: research_requirement_for_format,
        5: research_requirement_for_monetization,
        9: research_requirement_for_strategy,
        10: research_requirement_for_marketing,
    }
    requirement = requirement_functions.get(field_index, lambda _: None)(option_index)
    return not requirement or has_research(state.studio, requirement)


def cycle_plan_option(state: GameState, field_index: int, attribute: str, count: int, delta: int) -> None:
    current = getattr(state, attribute)
    for offset in range(1, count + 1):
        candidate = (current + delta * offset) % count
        if plan_option_unlocked(state, field_index, candidate):
            setattr(state, attribute, candidate)
            return


def cycle_channel_selection(state: GameState, delta: int) -> None:
    for offset in range(1, len(CHANNELS) + 1):
        candidate = (state.selected_channel + delta * offset) % len(CHANNELS)
        if channel_lock_reason(state.studio, candidate):
            continue
        requirement = research_requirement_for_channel(candidate)
        if not requirement or has_research(state.studio, requirement):
            state.selected_channel = candidate
            return


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
        open_idea_shelf(state, "games" if state.modal == "games" else "main")
    elif action == "open_concept":
        if state.modal == "ideas":
            handle_ideas_key(state, 10)
    elif action == "resume_project":
        project = state.studio.current_project
        if project and project.stage == "concept":
            state.modal = "concept"
        elif project and project.stage == "design":
            state.modal = "design_review"
    elif action == "discard_idea":
        if state.modal == "ideas":
            handle_ideas_key(state, ord("d"))
    elif action == "run_experiment":
        if state.modal == "concept":
            handle_concept_key(state, 10)
    elif action == "end_concept":
        if state.modal == "concept":
            handle_concept_key(state, ord("e"))
    elif action == "shelve_concept":
        if state.modal == "concept":
            handle_concept_key(state, ord("s"))
    elif action == "toggle_tweak":
        if state.modal == "design_review":
            handle_design_review_key(state, ord("t"))
    elif action == "commit_design":
        if state.modal == "design_review":
            commit_design_plan(state)
    elif action == "contracts":
        state.modal = "contracts"
    elif action == "finance":
        state.modal = "finance"
        state.selected_finance_offer = 0
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
    elif action == "cycle_support":
        games = live_games(state)
        project_selected = state.modal == "games" and state.studio.current_project and state.selected_game == 0
        if games and not project_selected:
            cycle_game_support(state, games[released_selection_index(state)].game_id)
    elif action == "release_project":
        release_ready_project(state)
    elif action == "early_access":
        launch_early_access(state)
    elif action == "production_option":
        state.selected_project_decision = (state.selected_project_decision + 1) % 2
    elif action == "toggle_platform":
        if state.modal == "design_review":
            toggle_platform_selection(state, state.selected_channel)
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
    elif action == "open_cancel_project":
        open_cancel_project(state)
    elif action == "close_cancel_project":
        close_cancel_project(state)
    elif action == "cancel_project_option":
        state.selected_cancel_project_action = (state.selected_cancel_project_action + 1) % 2
    elif action == "confirm_cancel_project":
        confirm_cancel_project(state)
    elif action == "buy_promotion":
        targets = promotion_targets(state)
        if state.marketing_tab == 2 and targets:
            target_id = targets[state.selected_promotion_target][0]
            target_game = game_by_id(state.studio, target_id) if target_id else None
            franchise = franchise_for_game(state.studio, target_game) if target_game else None
            if franchise is not None:
                buy_media_venture(state, franchise.franchise_id, state.selected_venture)
        elif state.marketing_tab == 3 and targets:
            take_community_action(state, targets[state.selected_promotion_target][0])
        elif targets:
            buy_promotion(state, targets[state.selected_promotion_target][0], state.selected_promotion)
    elif action == "marketing_selection":
        if state.marketing_tab == 0:
            targets = promotion_targets(state)
            if targets:
                state.selected_promotion_target = (state.selected_promotion_target + 1) % len(targets)
        elif state.marketing_tab == 2:
            state.selected_venture = (state.selected_venture + 1) % len(MEDIA_VENTURES)
        elif state.marketing_tab == 3:
            state.selected_community_action = (state.selected_community_action + 1) % len(COMMUNITY_ACTIONS)
        else:
            state.selected_promotion = (state.selected_promotion + 1) % len(PROMOTIONS)
    elif action == "toggle_marketing_panel":
        cycle_marketing_tab(state)
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
        if state.modal == "ideas":
            handle_ideas_key(state, curses.KEY_BACKSPACE)
        elif state.modal == "concept":
            handle_concept_key(state, curses.KEY_BACKSPACE)
        elif state.modal == "design_review":
            handle_design_review_key(state, 27)
        elif state.modal == "marketing":
            if state.marketing_tab in (1, 2, 3):
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
        if state.modal == "ideas":
            handle_ideas_key(state, 10)
        elif state.modal == "concept":
            handle_concept_key(state, 10)
        elif state.modal == "design_review":
            handle_design_review_key(state, 10)
    elif action == "accept_title":
        if state.draft_title.strip():
            state.draft_title = state.draft_title.strip()
            state.naming_game = False
    elif action == "cancel_title":
        state.naming_game = False
    elif action == "project_choice":
        if state.modal == "ideas":
            handle_ideas_key(state, curses.KEY_DOWN)
    elif action == "new_game_selection":
        if state.modal == "ideas":
            handle_ideas_key(state, curses.KEY_DOWN)
        elif state.modal == "design_review":
            handle_design_review_key(state, curses.KEY_DOWN)
    elif action == "new_game_adjust_left":
        if state.modal == "design_review":
            handle_design_review_key(state, curses.KEY_LEFT)
    elif action == "new_game_adjust_right":
        if state.modal == "design_review":
            handle_design_review_key(state, curses.KEY_RIGHT)
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
    elif action == "vacation":
        if state.team_tab == 1:
            start_employee_vacation(state)
    elif action == "buy":
        buy_upgrade(state)
    elif action == "finance_selection":
        count = len(LOAN_OFFERS) if state.finance_tab == 0 else len(PUBLISHER_OFFERS)
        state.selected_finance_offer = (state.selected_finance_offer + 1) % count
    elif action == "finance_accept":
        if state.finance_tab == 0:
            take_loan(state, state.selected_finance_offer)
        else:
            select_publisher(state, state.selected_finance_offer)
    elif action == "cancel_research":
        cancel_queued_research(state)
    elif action == "previous_research_branch":
        state.selected_research_branch = (state.selected_research_branch - 1) % len(RESEARCH_BRANCHES)
        state.selected_upgrade = 0
    elif action == "next_research_branch":
        state.selected_research_branch = (state.selected_research_branch + 1) % len(RESEARCH_BRANCHES)
        state.selected_upgrade = 0
    elif action == "previous_view":
        state.analysis_view = (state.analysis_view - 1) % len(ANALYSIS_TABS)
        state.selected_stat = 0
    elif action == "next_view":
        state.analysis_view = (state.analysis_view + 1) % len(ANALYSIS_TABS)
        state.selected_stat = 0
    return True


def open_blend(state: GameState) -> None:
    """Deprecated: the genre/theme blend mechanic left with the wizard."""
    state.mix_blend = False


def close_blend(state: GameState, confirm: bool) -> None:
    """Deprecated: the genre/theme blend mechanic left with the wizard."""
    state.mix_blend = False


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
    elif key in (ord("v"), ord("V")) and state.team_tab == 1:
        start_employee_vacation(state)


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
        if state.cancel_project_open:
            delta = -1 if wheel_up else 1
            state.selected_cancel_project_action = (state.selected_cancel_project_action + delta) % 2
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
        elif state.modal == "design_review":
            handle_design_review_key(state, curses.KEY_LEFT if wheel_up else curses.KEY_RIGHT)
        elif state.modal == "team":
            handle_team_key(state, key)
        elif state.modal == "contracts" and state.studio.contract_offers:
            cycle_contract_selection(state, -1 if wheel_up else 1)
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
            nodes = research_nodes_for_branch(RESEARCH_BRANCHES[state.selected_research_branch])
            state.selected_upgrade = (state.selected_upgrade + (-1 if wheel_up else 1)) % len(nodes)
        elif state.modal == "ideas" and state.studio.idea_shelf:
            handle_ideas_key(state, key)
        elif state.modal == "concept":
            handle_concept_key(state, key)
        elif state.modal == "main":
            perform_footer_action(state, "faster" if wheel_up else "slower")
        return

    right_click = bool(buttons & (getattr(curses, "BUTTON3_CLICKED", 0) | getattr(curses, "BUTTON3_RELEASED", 0)))
    if state.queue_cancellation:
        return
    if right_click and state.settings_open:
        close_settings(state)
        return
    if right_click and state.cancel_project_open:
        close_cancel_project(state)
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
    if state.cancel_project_open:
        _, popup_width, popup_y, popup_x = cancel_project_popup_geometry(width, height)
        if popup_x <= x < popup_x + popup_width:
            for action_index, row in enumerate(CANCEL_PROJECT_ACTION_ROWS):
                if y == popup_y + row:
                    state.selected_cancel_project_action = action_index
                    if double_click:
                        confirm_cancel_project(state)
                    break
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
        if y == 3:
            branch_x = 2
            for index, branch_name in enumerate(RESEARCH_BRANCHES):
                label_width = len(branch_name) + 2
                if branch_x <= x < branch_x + label_width:
                    state.selected_research_branch = index
                    state.selected_upgrade = 0
                    return
                branch_x += label_width + 1
        nodes = research_nodes_for_branch(RESEARCH_BRANCHES[state.selected_research_branch])
        row = y - 5
        if 0 <= row < len(nodes):
            state.selected_upgrade = row
            if double_click:
                buy_upgrade(state)
        return

    if state.modal == "contracts":
        board_width = contract_board_width(width)
        row = y - 4
        if x <= board_width and 0 <= row < len(state.studio.contract_offers):
            if state.studio.contract_offers[row].reputation_required <= state.studio.contractor_reputation:
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
            elif x > summary_width and state.marketing_tab == 3 and 0 <= option_row < len(COMMUNITY_ACTIONS):
                state.selected_community_action = option_row
                if double_click and targets:
                    take_community_action(state, targets[state.selected_promotion_target][0], option_row)
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

    if state.modal == "ideas":
        ideas = ordered_shelf(state)
        row = y - 5
        if row >= 0 and row < len(ideas):
            state.selected_idea = row
            if double_click:
                handle_ideas_key(state, 10)
        return

    if state.modal == "concept":
        project = state.studio.current_project
        if project is None or project.stage != "concept" or project.active_experiment:
            return
        pitch_width = max(24, min(46, width // 3))
        if x > pitch_width:
            experiments = available_concept_experiments(state)
            row = y - 6
            if 0 <= row < len(experiments):
                state.selected_experiment = row
                if double_click:
                    handle_concept_key(state, 10)
        return

    if state.modal == "design_review":
        project = state.studio.current_project
        if project is None or project.stage != "design":
            return
        rows = design_review_rows(state)
        layout = design_review_layout(state, height)
        panel_row = y - 2
        if panel_row == layout["commit_row"]:
            state.selected_design_focus = len(rows) - 1
            if double_click:
                commit_design_plan(state)
        elif panel_row == layout["store_row"]:
            state.selected_design_focus = len(rows) - 2
        elif layout["plan_start"] <= panel_row < layout["plan_start"] + 11:
            state.selected_design_focus = layout["tweak_offset"] + panel_row - layout["plan_start"]
        elif state.tweak_presentation and layout["presentation_start"] <= panel_row < layout["presentation_start"] + 5:
            state.selected_design_focus = 1 + panel_row - layout["presentation_start"]
        elif not state.tweak_presentation and layout["presentation_start"] <= panel_row < layout["presentation_start"] + len(project.gdd.get("presentation_options", [])):
            state.selected_presentation = panel_row - layout["presentation_start"]
            state.selected_design_focus = 0
        return




def activate_title_choice(state: GameState) -> bool:
    choice = TITLE_MENU[state.title_menu_index]
    if choice == "New Game":
        fresh_state = GameState.new_campaign(save_path=state.save_path)
        state.__dict__.clear()
        state.__dict__.update(fresh_state.__dict__)
        state.log("Started a new studio from the title screen.")
        return True
    if choice == "Load Game":
        open_save_picker(state, "load")
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
    if state.save_picker_open:
        count = len(state.save_slots) + (1 if state.save_picker_mode == "save" else 0)
        if key in ESCAPE_KEYS or key in (8, 127, curses.KEY_BACKSPACE):
            close_save_picker(state)
        elif key == curses.KEY_UP and count:
            state.selected_save_slot = (state.selected_save_slot - 1) % count
        elif key == curses.KEY_DOWN and count:
            state.selected_save_slot = (state.selected_save_slot + 1) % count
        elif key in (10, 13, curses.KEY_ENTER):
            confirm_save_slot(state)
        return True
    if state.settings_open:
        if key in ESCAPE_KEYS:
            close_settings(state)
        elif key in (ord("q"), ord("Q")):
            return False
        elif key == curses.KEY_UP:
            state.selected_setting_action = (state.selected_setting_action - 1) % 4
        elif key == curses.KEY_DOWN:
            state.selected_setting_action = (state.selected_setting_action + 1) % 4
        elif key in (10, 13, curses.KEY_ENTER):
            return activate_settings_action(state)
        elif key == curses.KEY_MOUSE and dimensions is not None:
            return handle_mouse(state, dimensions) is not False
        return True
    if state.cancel_project_open:
        if key in ESCAPE_KEYS or key in (8, 127, curses.KEY_BACKSPACE):
            close_cancel_project(state)
        elif key == curses.KEY_UP:
            state.selected_cancel_project_action = (state.selected_cancel_project_action - 1) % 2
        elif key == curses.KEY_DOWN:
            state.selected_cancel_project_action = (state.selected_cancel_project_action + 1) % 2
        elif key in (10, 13, curses.KEY_ENTER):
            confirm_cancel_project(state)
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
    if state.modal in ("new_game", "design_review") and state.naming_game:
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
    # Context commands must win over same-letter global tab shortcuts.
    if state.modal == "concept" and key in (ord("s"), ord("S")):
        handle_concept_key(state, key)
        return True
    if state.modal == "design_review" and key in (ord("t"), ord("T")):
        handle_design_review_key(state, key)
        return True
    for index, (_, shortcut, _) in enumerate(TOP_TABS):
        if key in (ord(shortcut.lower()), ord(shortcut)):
            activate_top_tab(state, index)
            if shortcut == "T":
                state.team_tab = 1
            return True
    if key in (ord("q"), ord("Q")):
        return False
    if key in (ord("b"), ord("B")) and state.modal == "main":
        state.modal = "finance"
        state.selected_finance_offer = 0
        return True
    if state.modal == "finance" and key in (curses.KEY_LEFT, curses.KEY_RIGHT):
        state.finance_tab = 1 - state.finance_tab
        state.selected_finance_offer = 0
        return True
    if key == ord(" "):
        toggle_pause(state)
        return True
    if key in (ord("<"), curses.KEY_LEFT, ord(">"), curses.KEY_RIGHT):
        left_action, right_action = horizontal_actions(state)
        perform_footer_action(state, left_action if key in (ord("<"), curses.KEY_LEFT) else right_action)
        return True
    if key == curses.KEY_MOUSE and dimensions is not None:
        return handle_mouse(state, dimensions) is not False
    if state.modal == "ideas":
        handle_ideas_key(state, key)
    elif state.modal == "concept":
        handle_concept_key(state, key)
    elif state.modal == "design_review":
        handle_design_review_key(state, key)
    elif state.modal == "team":
        handle_team_key(state, key)
    elif state.modal == "contracts":
        if key in (8, 127, curses.KEY_BACKSPACE):
            state.modal = "main"
        elif key in (ord("c"), ord("C")):
            toggle_auto_contracts(state)
        elif key == curses.KEY_UP and state.studio.contract_offers:
            cycle_contract_selection(state, -1)
        elif key == curses.KEY_DOWN and state.studio.contract_offers:
            cycle_contract_selection(state, 1)
        elif key in (10, 13, curses.KEY_ENTER):
            accept_contract_offer(state)
    elif state.modal == "finance":
        if key in (8, 127, curses.KEY_BACKSPACE):
            state.modal = "main"
        elif key in (curses.KEY_LEFT, curses.KEY_RIGHT):
            state.finance_tab = 1 - state.finance_tab
            state.selected_finance_offer = 0
        elif key in (curses.KEY_UP, curses.KEY_DOWN):
            count = len(LOAN_OFFERS) if state.finance_tab == 0 else len(PUBLISHER_OFFERS)
            delta = -1 if key == curses.KEY_UP else 1
            state.selected_finance_offer = (state.selected_finance_offer + delta) % count
        elif key in (10, 13, curses.KEY_ENTER):
            if state.finance_tab == 0:
                take_loan(state, state.selected_finance_offer)
            else:
                select_publisher(state, state.selected_finance_offer)
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
            open_idea_shelf(state, "games")
        elif key in (10, 13, curses.KEY_ENTER, ord("c"), ord("C")) and project and project.stage in ("concept", "design") and state.selected_game == 0:
            state.modal = "concept" if project.stage == "concept" else "design_review"
        elif key == curses.KEY_UP and entry_count:
            state.selected_game = (state.selected_game - 1) % entry_count
        elif key == curses.KEY_DOWN and entry_count:
            state.selected_game = (state.selected_game + 1) % entry_count
        elif key in (ord("p"), ord("P")):
            perform_footer_action(state, "game_marketing")
        elif key in (ord("c"), ord("C")) and project and state.selected_game == 0:
            open_cancel_project(state)
        elif key in (ord("x"), ord("X")) and games:
            perform_footer_action(state, "cycle_support")
        elif key in (ord("r"), ord("R")) and project and state.selected_game == 0:
            release_ready_project(state)
        elif key in (ord("e"), ord("E")) and project and state.selected_game == 0:
            launch_early_access(state)
        elif key in (ord("["), ord("]")) and games and not (project and state.selected_game == 0):
            game_id = games[released_selection_index(state)].game_id
            cycle_game_price(state, game_id, -1 if key == ord("[") else 1)
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
        elif key in (ord("c"), ord("C")) and state.marketing_tab != 3:
            enter_queue_cancellation(state)
        elif key in (ord("m"), ord("M")):
            cycle_marketing_tab(state)
        elif key in (8, 127, curses.KEY_BACKSPACE):
            if state.marketing_tab in (1, 2, 3):
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
            elif state.marketing_tab == 3:
                state.selected_community_action = (state.selected_community_action + delta) % len(COMMUNITY_ACTIONS)
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
        elif key in (10, 13, curses.KEY_ENTER) and state.marketing_tab == 3 and targets:
            take_community_action(state, targets[state.selected_promotion_target][0])
        elif key in (10, 13, curses.KEY_ENTER) and targets:
            buy_promotion(state, targets[state.selected_promotion_target][0], state.selected_promotion)
    elif state.modal == "upgrades":
        if key in (8, 127, curses.KEY_BACKSPACE):
            state.modal = "main"
        elif key == curses.KEY_UP:
            nodes = research_nodes_for_branch(RESEARCH_BRANCHES[state.selected_research_branch])
            state.selected_upgrade = (state.selected_upgrade - 1) % len(nodes)
        elif key == curses.KEY_DOWN:
            nodes = research_nodes_for_branch(RESEARCH_BRANCHES[state.selected_research_branch])
            state.selected_upgrade = (state.selected_upgrade + 1) % len(nodes)
        elif key in (10, 13, curses.KEY_ENTER):
            buy_upgrade(state)
        elif key in (ord("c"), ord("C")):
            cancel_queued_research(state)
        elif key in (ord("1"), ord("2"), ord("3"), ord("4"), ord("5")):
            kind = ("project", "contract", "update", "promotion", "research")[key - ord("1")]
            cycle_work_priority(state, kind)
        elif key in (ord("a"), ord("A")):
            if "auto_leave" in state.studio.completed_research or "auto_leave" in state.studio.upgrades:
                state.studio.auto_vacation = not state.studio.auto_vacation
                state.log(f"Automatic vacation scheduling {'enabled' if state.studio.auto_vacation else 'disabled'}.")
            else:
                state.log("Automatic vacation requires Sustainable Scheduling research.")
    elif state.modal == "analysis":
        if key in (8, 127, curses.KEY_BACKSPACE):
            state.modal = "main"
        elif key in (curses.KEY_UP, curses.KEY_DOWN) and state.analysis_view in (2, 3, 4):
            count = len(GENRES) if state.analysis_view == 2 else len(state.studio.catalog) if state.analysis_view == 3 else len(state.studio.competitors)
            if count:
                state.selected_stat = (state.selected_stat + (-1 if key == curses.KEY_UP else 1)) % count
    elif state.modal == "main":
        if key in (ord("n"), ord("N")):
            open_idea_shelf(state, "main")
        elif key in (ord("u"), ord("U")):
            state.modal = "upgrades"
        elif key in (ord("c"), ord("C")):
            if state.studio.current_project and state.studio.current_project.stage == "concept":
                state.modal = "concept"
            else:
                toggle_auto_contracts(state)
        elif key in (ord("j"), ord("J")):
            state.modal = "contracts"
    return True
