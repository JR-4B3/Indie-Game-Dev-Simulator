"""Screen chrome: the bars and popups that frame every page.

The chrome owns the persistent frame of the app so pages only draw their
content area:

- Top bar (rows 0-1): page tabs (Hub / Game / Team / Statistics), the
  current page's context actions, and the global Settings control.
- Bottom bars (rows h-2, h-1): studio metrics with the week progress meter,
  then date plus playback/speed controls.
- Centered popups: Settings, Professional Training, Production Event, and
  the blocking insolvency notice, plus the settings/training open-close
  state machines (which pause and restore the sim).

Layout helpers return ``(label, action, x)`` triples so the mouse handler
hit-tests exactly what the header/footer drew — geometry is never
duplicated between drawing and input.
"""

from __future__ import annotations

import curses
from pathlib import Path

from simulation import (
    EMPLOYEE_SKILLS,
    PRODUCTION_DECISIONS,
    TIME_LABELS,
    GameState,
    runway_months,
    save_game,
    selected_roster_employee,
    start_employee_training,
    training_cost,
)
from ui_common import add_text, draw_box, live_games, meter, money


SETTINGS_ACTIONS = ("Close", "Save", "Quit")
SETTINGS_ACTION_ROWS = (6, 8, 10)
TOP_TABS = (
    ("Hub", "H", "main"),
    ("Game", "G", "games"),
    ("Team", "T", "team"),
    ("Statistics", "S", "analysis"),
)
MODAL_TAB_INDEX = {
    "main": 0,
    "contracts": 0,
    "upgrades": 0,
    "settings": 0,
    "games": 1,
    "update_planner": 1,
    "new_game": 1,
    "marketing": 1,
    "team": 2,
    "analysis": 3,
}


def active_top_tab(state: GameState) -> int:
    return MODAL_TAB_INDEX.get(state.modal, 0)


def activate_top_tab(state: GameState, index: int) -> None:
    state.naming_game = False
    state.queue_cancellation = ""
    state.modal = TOP_TABS[index % len(TOP_TABS)][2]
    if state.modal == "games":
        state.games_tab = 0


def cycle_top_tab(state: GameState, delta: int = 1) -> None:
    activate_top_tab(state, (active_top_tab(state) + delta) % len(TOP_TABS))


def centered_layout(actions: list[tuple[str, str]], width: int) -> list[tuple[str, str, int]]:
    available = max(1, width - 2)
    total = sum(len(label) for label, _ in actions) + max(0, len(actions) - 1)
    x = 1 + max(0, (available - total) // 2)
    layout = []
    for label, action in actions:
        if x + len(label) > width - 1:
            break
        layout.append((label, action, x))
        x += len(label) + 1
    return layout


def control_label(control: str, text: str) -> str:
    matches = len(control) == 1 and text[:1].lower() == control.lower()
    suffix = text[1:] if matches else f" {text}"
    return f"[{control}]{suffix}"


def top_tab_actions(state: GameState) -> list[tuple[str, str]]:
    active = active_top_tab(state)
    actions = []
    for index, (name, key, _) in enumerate(TOP_TABS):
        label = f">[{key}]{name[1:]}<" if index == active else f"[{key}]{name[1:]}"
        actions.append((label, f"top_tab_{index}"))
    return actions


def top_tab_layout(state: GameState, width: int) -> list[tuple[str, int, int]]:
    x = 2
    layout = []
    for label, action in top_tab_actions(state):
        layout.append((action, x, x + len(label)))
        x += len(label) + 1
    return layout


def top_context_uses_second_row(state: GameState, width: int) -> bool:
    context = footer_layout(state, width)
    if not context:
        return False
    tab_end = top_tab_layout(state, width)[-1][2]
    global_start = global_action_layout(state, width)[0][2]
    context_start = context[0][2]
    context_end = context[-1][2] + len(context[-1][0])
    return context_start <= tab_end or context_end >= global_start


def top_control_layout(state: GameState, width: int) -> list[tuple[str, str, int]]:
    labels = {action: label for label, action in top_tab_actions(state)}
    layout = [(labels[action], action, start) for action, start, _ in top_tab_layout(state, width)]
    if not top_context_uses_second_row(state, width):
        layout.extend(footer_layout(state, width))
    layout.extend(global_action_layout(state, width))
    return layout


def draw_header(screen: curses.window, state: GameState, width: int) -> None:
    bar_width = width - 2
    add_text(screen, 0, 1, " " * bar_width, bar_width, curses.color_pair(1))
    for label, _, x in top_control_layout(state, width):
        draw_footer_label(screen, 0, x, label, width)
    if top_context_uses_second_row(state, width):
        add_text(screen, 1, 1, " " * bar_width, bar_width, curses.color_pair(1))
        for label, _, x in footer_layout(state, width):
            draw_footer_label(screen, 1, x, label, width)


def footer_actions(state: GameState, width: int | None = None) -> list[tuple[str, str]]:
    """Context actions shown on the top bar for the current page/mode."""
    compact = width is not None and width < 120
    dense = width is not None and width < 150
    if state.modal == "main":
        return [("[N]" if compact else control_label("N", "New Game"), "new"), ("[J]" if compact else control_label("J", "Jobs"), "contracts"), ("[U]" if compact else control_label("U", "Upgrades"), "upgrades")]
    if state.modal == "new_game":
        if state.naming_game:
            return [("[Enter]" if compact else control_label("Enter", "Accept title"), "accept_title")]
        if state.new_game_step == -2:
            return [("[Bksp]" if compact else control_label("Backspace", "Project type"), "back"), ("[Up/Dn]" if dense else control_label("Up/Down", "Game"), "project_choice"), ("[Enter]" if compact else control_label("Enter", "Choose"), "confirm")]
        if state.new_game_step == -1:
            return [("[Bksp]" if compact else control_label("Backspace", "Catalogue"), "back"), ("[Up/Dn]" if dense else control_label("Up/Down", "Option"), "project_choice"), ("[Enter]" if compact else control_label("Enter", "Choose"), "confirm")]
        panel_names = ("Genre", "Theme", "Production Plan", "Storefront")
        if compact:
            actions = [(control_label("Bksp", "Prev"), "back"), ("[Up/Dn]", "new_game_selection")]
            if state.new_game_step in (0, 1):
                actions.append(("[B]", "toggle_blend"))
            actions.extend([("[E]", "type_title"), ("[R]", "random_title")])
            actions.append((control_label("Enter", "Green" if state.new_game_step == 3 else "Next"), "confirm"))
        else:
            actions = [(control_label("Backspace", "Previous"), "back"), (control_label("Up/Down", panel_names[state.new_game_step]), "new_game_selection")]
            enter_label = control_label("Enter", "Greenlight" if state.new_game_step == 3 else "Next")
            if state.new_game_step in (0, 1):
                actions.append((control_label("B", "Blend"), "toggle_blend"))
            elif state.new_game_step == 2:
                actions.append((control_label("</>", "Change"), "new_game_adjust_right"))
            actions.extend([(control_label("E", "Edit title"), "type_title"), (control_label("R", "Random"), "random_title"), (enter_label, "confirm")])
        return actions
    if state.modal == "team":
        hiring = state.team_tab == 0
        employ = control_label("E", "Employ") if not compact else "[E]"
        team = control_label("T", "Team") if not compact else "[T]"
        actions = [(f">{employ}<" if hiring else employ, "applicants"), (team if hiring else f">{team}<", "roster")]
        if hiring:
            if state.studio.applicants:
                actions.append(("[Enter]" if compact else control_label("Enter", "Hire"), "hire"))
        else:
            selected = selected_roster_employee(state)
            if selected:
                actions.append(("[L]" if compact else control_label("L", "Learn"), "train"))
                if not selected.founder:
                    actions.append(("[D]" if compact else control_label("D", "Dismiss"), "dismiss"))
        return actions
    if state.modal == "contracts":
        auto = "ON" if state.studio.auto_contracts else "OFF"
        return [("[Bksp]" if compact else control_label("Backspace", "Hub"), "back"), ("[Enter]" if compact else control_label("Enter", "Accept"), "accept_contract"), (control_label("C", "Auto") if compact else control_label("C", f"Auto {auto}"), "toggle_contracts")]
    if state.modal == "games":
        project = state.studio.current_project
        if project and project.pending_decision is not None:
            return [
                ("[Up/Dn]" if compact else control_label("Up/Down", "Option"), "production_option"),
                ("[Enter]" if compact else control_label("Enter", "Commit Decision"), "resolve_decision"),
            ]
        return [("[N]" if compact else control_label("N", "New Game"), "new"), ("[U]" if compact else control_label("U", "Update Planner"), "open_update_planner"), ("[P]" if compact else control_label("P", "Promotion"), "game_marketing")]
    if state.modal == "update_planner":
        if state.queue_cancellation == "update":
            return [("[Bksp]" if compact else control_label("Backspace", "Return to planning"), "leave_queue_cancellation"), ("[Up/Dn]" if compact else control_label("Up/Down", "Queued update"), "queue_cancellation_selection"), ("[Enter]" if compact else control_label("Enter", "Cancel selected"), "cancel_selected_queue_item")]
        games = live_games(state)
        if not games:
            return [("[Bksp]" if compact else control_label("Backspace", "Game"), "back")]
        if state.games_tab == 0:
            actions = [("[Bksp]" if compact else control_label("Backspace", "Game"), "back"), ("[Up/Dn]" if compact else control_label("Up/Down", "Game"), "update_game_selection"), ("[Enter]" if compact else control_label("Enter", "Select"), "select_update_game")]
            actions.append(("[C]" if compact else control_label("C", "Cancel"), "enter_queue_cancellation"))
            return actions
        if state.games_tab == 1:
            actions = [("[Bksp]" if compact else control_label("Backspace", "Game"), "back"), ("[Up/Dn]" if compact else control_label("Up/Down", "Scope"), "update_scope_selection"), ("[Enter]" if compact else control_label("Enter", "Select"), "select_update_scope")]
        else:
            actions = [("[Bksp]" if compact else control_label("Backspace", "Scope"), "back"), ("[Up/Dn]" if compact else control_label("Up/Down", "Area"), "update_area_selection"), ("[Enter]" if compact else control_label("Enter", "Queue Update"), "enter_only")]
        actions.append(("[C]" if compact else control_label("C", "Cancel"), "enter_queue_cancellation"))
        return actions
    if state.modal == "marketing":
        if state.queue_cancellation == "promotion":
            return [("[Bksp]" if compact else control_label("Backspace", "Return to planning"), "leave_queue_cancellation"), ("[Up/Dn]" if compact else control_label("Up/Down", "Queued promotion"), "queue_cancellation_selection"), ("[Enter]" if compact else control_label("Enter", "Cancel selected"), "cancel_selected_queue_item")]
        if state.marketing_tab == 0:
            actions = [("[Bksp]" if compact else control_label("Backspace", "Catalogue"), "back"), ("[Up/Dn]" if compact else control_label("Up/Down", "Game"), "marketing_selection"), ("[Enter]" if compact else control_label("Enter", "Select"), "select_marketing_target")]
        elif state.marketing_tab == 2:
            actions = [("[Bksp]" if compact else control_label("Backspace", "Planning"), "back"), ("[Up/Dn]" if compact else control_label("Up/Down", "Venture"), "marketing_selection"), ("[Enter]" if compact else control_label("Enter", "Fund"), "buy_promotion"), ("[M]" if compact else control_label("M", "Promotions"), "toggle_marketing_panel")]
        else:
            actions = [("[Bksp]" if compact else control_label("Backspace", "Planning"), "back"), ("[Up/Dn]" if compact else control_label("Up/Down", "Promotion"), "marketing_selection"), ("[Enter]" if compact else control_label("Enter", "Buy"), "buy_promotion"), ("[M]" if compact else control_label("M", "Merch & Media"), "toggle_marketing_panel")]
        actions.append(("[C]" if compact else control_label("C", "Cancel"), "enter_queue_cancellation"))
        return actions
    if state.modal == "upgrades":
        return [("[Bksp]" if compact else control_label("Backspace", "Hub"), "back"), ("[Enter]" if compact else control_label("Enter", "Buy"), "buy")]
    return []


def global_actions(state: GameState, width: int) -> list[tuple[str, str]]:
    return [("[Esc]" if width < 120 else control_label("Esc", "Settings"), "settings")]


def global_action_layout(state: GameState, width: int) -> list[tuple[str, str, int]]:
    actions = global_actions(state, width)
    total = sum(len(label) for label, _ in actions) + max(0, len(actions) - 1)
    x = max(2, width - total - 2)
    layout = []
    for label, action in actions:
        layout.append((label, action, x))
        x += len(label) + 1
    return layout


def bottom_date_text(state: GameState, width: int) -> str:
    year = (state.clock.week - 1) // 52 + 1
    week = (state.clock.week - 1) % 52 + 1
    if width >= 100:
        return f"{state.clock.current_date:%d %b %Y}  Y {year}  W {week}"
    return f"{state.clock.current_date:%d%b%y} Y{year} W{week}"


def horizontal_actions(state: GameState) -> tuple[str, str]:
    """What </> and Left/Right mean in the current context."""
    if state.modal == "new_game" and state.new_game_step == 2:
        return "new_game_adjust_left", "new_game_adjust_right"
    if state.modal == "analysis":
        return "previous_view", "next_view"
    return "slower", "faster"


def bottom_time_layout(state: GameState, width: int) -> list[tuple[str, str, int]]:
    speed = "||" if state.time_speed_index == 0 else ">" * state.time_speed_index
    left_action, right_action = horizontal_actions(state)
    actions = [("[<]", left_action), (f"[Space]{speed}", "pause"), ("[>]", right_action)]
    x = 3 + len(bottom_date_text(state, width))
    layout = []
    for label, action in actions:
        layout.append((label, action, x))
        x += len(label) + 1
    return layout


def footer_layout(state: GameState, width: int) -> list[tuple[str, str, int]]:
    return centered_layout(footer_actions(state, width), width)


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


def status_segments(state: GameState, width: int) -> list[tuple[str, int]]:
    """The persistent studio status shown on every page, most critical first.

    Cash and runway lead as bare values; in-progress production and contract
    work follow with live meters (the contract meter stays narrower than the
    development meter, mirroring the overview) whenever they exist so their
    progress is visible from any page.
    """
    studio = state.studio
    runway = runway_months(studio)
    segments = [
        (money(studio.cash), curses.A_BOLD if studio.cash >= 0 else curses.color_pair(5) | curses.A_BOLD),
        (f"{runway:.1f} mo" if runway < 99 else "99+ mo", curses.color_pair(5) | curses.A_BOLD if runway < 4 else 0),
    ]
    if width >= 150:
        dev_width, job_width = 16, 8
    elif width >= 120:
        dev_width, job_width = 12, 6
    elif width >= 100:
        dev_width, job_width = 10, 5
    else:
        dev_width, job_width = 8, 4
    project = studio.current_project
    if project is not None:
        segments.append((f"DEV {meter(project.progress, 1, dev_width)}", curses.color_pair(4) | curses.A_BOLD))
    contract = studio.contract
    if contract is not None:
        progress = 0 if contract.required_work <= 0 else contract.work_done / contract.required_work
        segments.append((f"JOB {meter(progress, 1, job_width)}", curses.color_pair(4) | curses.A_BOLD))
    if width >= 150:
        segments.append((f"Fans {studio.followers:,}", 0))
        segments.append((f"PTrust {studio.reputation:.1f}", 0))
        segments.append((f"CTrust {studio.contractor_reputation:.1f}", 0))
    elif width >= 100:
        segments.append((f"Fans {studio.followers:,}", 0))
    return segments


def draw_status_segments(screen: curses.window, y: int, x: int, segments: list[tuple[str, int]], width: int) -> None:
    cursor = x
    for index, (text, attr) in enumerate(segments):
        start = cursor + (3 if index else 0)
        if width - start < len(text):
            break
        if index:
            add_text(screen, y, cursor, " | ", 3, curses.color_pair(4))
        if not attr & curses.A_COLOR:
            attr |= curses.color_pair(4)
        add_text(screen, y, start, text, len(text), attr)
        cursor = start + len(text)


def draw_footer(screen: curses.window, state: GameState, height: int, width: int) -> None:
    title = "INDIE GAME DEV SIM"
    if width >= 150:
        progress_width = 34
    elif width >= 100:
        progress_width = 28
    else:
        progress_width = 20
    bar_width = width - 2
    progress = meter(state.clock.progress, 1, progress_width)
    add_text(screen, height - 2, 1, f" [{progress}] ".ljust(bar_width), bar_width, curses.color_pair(4))
    draw_status_segments(screen, height - 2, 4 + progress_width, status_segments(state, width), bar_width)
    add_text(screen, height - 1, 1, " " * bar_width, bar_width, curses.color_pair(1))
    date_text = bottom_date_text(state, width)
    add_text(screen, height - 1, 2, date_text, len(date_text), curses.color_pair(1) | curses.A_BOLD)
    for label, _, x in bottom_time_layout(state, width):
        draw_footer_label(screen, height - 1, x, label, width)
    if width >= 120:
        title_x = width - len(title) - 2
        add_text(screen, height - 1, title_x, title, len(title), curses.color_pair(1) | curses.A_BOLD)


def settings_popup_geometry(width: int, height: int) -> tuple[int, int, int, int]:
    popup_width = min(52, max(40, width // 3))
    popup_height = 15
    popup_y = max(2, (height - popup_height) // 2)
    popup_x = max(1, (width - popup_width) // 2)
    return popup_height, popup_width, popup_y, popup_x


def draw_settings_popup(screen: curses.window, state: GameState, width: int, height: int) -> None:
    popup_height, popup_width, popup_y, popup_x = settings_popup_geometry(width, height)
    panel = screen.derwin(popup_height, popup_width, popup_y, popup_x)
    panel.erase()
    draw_box(panel, "Settings")
    add_text(panel, 1, 2, "GAME STATUS", popup_width - 4, curses.A_BOLD)
    add_text(panel, 2, 2, f"Simulation speed   {TIME_LABELS[state.time_speed_index]}", popup_width - 4)
    add_text(panel, 3, 2, f"Save file          {state.save_path}", popup_width - 4)
    add_text(panel, 5, 2, "ACTIONS", popup_width - 4, curses.A_BOLD)
    for index, (row, name) in enumerate(zip(SETTINGS_ACTION_ROWS, SETTINGS_ACTIONS)):
        selected = index == state.selected_setting_action
        label = f"[{name}]" if selected else name
        x = max(2, (popup_width - len(label)) // 2)
        add_text(panel, row, x, label, len(label), curses.A_BOLD if selected else 0)


def training_popup_geometry(width: int, height: int) -> tuple[int, int, int, int]:
    popup_width = min(76, max(58, width - 16))
    popup_height = 17
    return popup_height, popup_width, max(2, (height - popup_height) // 2), max(1, (width - popup_width) // 2)


def draw_training_popup(screen: curses.window, state: GameState, width: int, height: int) -> None:
    employee = selected_roster_employee(state)
    popup_height, popup_width, popup_y, popup_x = training_popup_geometry(width, height)
    panel = screen.derwin(popup_height, popup_width, popup_y, popup_x)
    panel.erase()
    draw_box(panel, "Professional Training")
    if employee is None:
        add_text(panel, 2, 3, "Hire and select an employee before booking education.", popup_width - 6)
        return
    add_text(panel, 1, 3, f"{employee.name} | {employee.role}", popup_width - 6, curses.A_BOLD)
    add_text(panel, 2, 3, f"Current salary {money(employee.annual_salary)}/year | XP {employee.experience}/100", popup_width - 6)
    if employee.training_weeks_left:
        add_text(panel, 4, 3, f"Already studying {employee.training_skill}: {employee.training_weeks_left} weeks remaining.", popup_width - 6, curses.color_pair(5))
    add_text(panel, 4 if not employee.training_weeks_left else 6, 3, "COURSE                         SKILL   COST       RESULT", popup_width - 6, curses.A_BOLD)
    start_row = 5 if not employee.training_weeks_left else 7
    for index, skill_name in enumerate(EMPLOYEE_SKILLS):
        value = employee.all_skills[index]
        selected = index == state.selected_training_skill
        cost = training_cost(employee, skill_name)
        result = "mastered" if value >= 99 else "+4 skill, salary review"
        text = f"{'> ' if selected else '  '}{skill_name:<25} {value:>3}/99  {money(cost):>9}  {result}"
        add_text(panel, start_row + index, 3, text, popup_width - 6, curses.color_pair(3) | curses.A_BOLD if selected else 0)
    add_text(panel, popup_height - 3, 3, "Course length: 4 weeks away from projects, updates, and contracts.", popup_width - 6, curses.color_pair(5))
    add_text(panel, popup_height - 2, 3, "Up/Down chooses | Enter enrolls | Backspace closes", popup_width - 6, curses.color_pair(4))


def production_review_geometry(width: int, height: int) -> tuple[int, int, int, int]:
    popup_width = min(100, max(66, width - 12))
    popup_height = 20
    return popup_height, popup_width, max(2, (height - popup_height) // 2), max(1, (width - popup_width) // 2)


def draw_production_review(screen: curses.window, state: GameState, width: int, height: int) -> None:
    project = state.studio.current_project
    if project is None or project.pending_decision is None:
        return
    decision = PRODUCTION_DECISIONS[project.pending_decision]
    popup_height, popup_width, popup_y, popup_x = production_review_geometry(width, height)
    panel = screen.derwin(popup_height, popup_width, popup_y, popup_x)
    panel.erase()
    draw_box(panel, f"Production Event | {decision['title']}")
    genre_mix = project.genre if project.secondary_genre == project.genre else f"{project.genre} / {project.secondary_genre}"
    add_text(panel, 1, 3, project.title, popup_width - 6, curses.A_BOLD)
    add_text(panel, 2, 3, f"{genre_mix} | {project.target_audience} | {project.game_format}", popup_width - 6)
    add_text(panel, 3, 3, f"Progress {project.progress:.0%} | week {project.weeks}/{project.planned_weeks} forecast | known bugs {int(project.known_defects)}", popup_width - 6)
    add_text(panel, 5, 3, decision["question"], popup_width - 6, curses.color_pair(5) | curses.A_BOLD)
    for index, option in enumerate(decision["options"]):
        selected = index == state.selected_project_decision
        row = 8 + index * 4
        add_text(panel, row, 5, f"{'> ' if selected else '  '}{option['name']}", popup_width - 10, curses.color_pair(3) | curses.A_BOLD if selected else 0)
        add_text(panel, row + 1, 9, option["effect"], popup_width - 14, curses.color_pair(4) if selected else 0)
    if project.decisions_made:
        add_text(panel, 16, 3, f"Earlier: {project.decisions_made[-1]}", popup_width - 6)
    add_text(panel, popup_height - 2, 3, "Up/Down chooses. Enter commits. Other controls are locked.", popup_width - 6, curses.color_pair(4))


def draw_insolvency_popup(screen: curses.window, state: GameState, width: int, height: int) -> None:
    popup_width = min(62, max(46, width - 24))
    popup_height = 11
    popup_y = max(2, (height - popup_height) // 2)
    popup_x = max(1, (width - popup_width) // 2)
    panel = screen.derwin(popup_height, popup_width, popup_y, popup_x)
    panel.erase()
    draw_box(panel, "Studio Insolvent")
    add_text(panel, 2, 2, "The studio remained insolvent for eight weeks and has closed.", popup_width - 4, curses.color_pair(5) | curses.A_BOLD)
    add_text(panel, 4, 2, "This run cannot continue.", popup_width - 4)
    add_text(panel, 5, 2, "Delete its save to start a new studio.", popup_width - 4)
    label = "[Delete Save]"
    add_text(panel, 7, (popup_width - len(label)) // 2, label, len(label), curses.A_BOLD)
    add_text(panel, 9, 2, "Press Enter", popup_width - 4, curses.color_pair(4))


def save_state(state: GameState) -> None:
    runtime_speed = state.time_speed_index
    try:
        if state.settings_open and state.settings_resume_on_close:
            state.time_speed_index = state.resume_speed_index
        save_game(state)
        state.log(f"Saved studio to {state.save_path}.")
    except OSError as error:
        state.log(f"Save failed: {error}.")
    finally:
        state.time_speed_index = runtime_speed


def delete_save_and_restart(state: GameState) -> bool:
    save_path = state.save_path
    try:
        Path(save_path).unlink(missing_ok=True)
    except OSError as error:
        state.log(f"Could not delete save: {error}.")
        return False
    fresh_state = GameState(save_path=save_path)
    state.__dict__.clear()
    state.__dict__.update(fresh_state.__dict__)
    return True


def open_settings(state: GameState) -> None:
    if state.settings_open:
        return
    state.settings_resume_on_close = state.time_speed_index != 0
    if state.settings_resume_on_close:
        state.resume_speed_index = state.time_speed_index
        state.time_speed_index = 0
    state.selected_setting_action = 0
    state.settings_open = True


def close_settings(state: GameState) -> None:
    if not state.settings_open:
        return
    state.settings_open = False
    if state.settings_resume_on_close and not state.studio.closed:
        state.time_speed_index = max(1, state.resume_speed_index)
    state.settings_resume_on_close = False


def open_training(state: GameState) -> None:
    if state.training_open or selected_roster_employee(state) is None:
        if selected_roster_employee(state) is None:
            state.log("Hire and select an employee before booking training.")
        return
    state.training_resume_on_close = state.time_speed_index != 0
    if state.training_resume_on_close:
        state.resume_speed_index = state.time_speed_index
        state.time_speed_index = 0
    state.selected_training_skill = 0
    state.training_open = True


def close_training(state: GameState) -> None:
    if not state.training_open:
        return
    state.training_open = False
    if state.training_resume_on_close and not state.studio.closed:
        state.time_speed_index = max(1, state.resume_speed_index)
    state.training_resume_on_close = False


def confirm_training(state: GameState) -> bool:
    if not start_employee_training(state):
        return False
    close_training(state)
    return True


def activate_settings_action(state: GameState) -> bool:
    if state.selected_setting_action == 0:
        close_settings(state)
        return True
    if state.selected_setting_action == 1:
        save_state(state)
        return True
    return False
