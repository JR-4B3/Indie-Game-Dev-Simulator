"""Team page: roster, applicants, and a person detail panel.

Layout (shared with the mouse handler via :func:`team_layout` so clicks
always match the drawing):

- Wide (>= 120 columns): a full-width roster table on top — wide enough to
  show every column, including untruncated style/quirk text — with the
  bottom split between the Applicants table and a Person Detail panel for
  whoever is selected on the active side.
- Narrow: the active side (Employ or Team) fills the width, with the
  Person Detail panel below it. E/T swaps sides without any layout jump.

Switching sides never changes geometry; it only moves the selection
highlight. Hiring shows its runway impact before you commit.
"""

from __future__ import annotations

import curses

from simulation import (
    EMPLOYEE_SKILLS,
    QUIRKS,
    TRAITS,
    UPGRADES,
    GameState,
    applicant_pool_size,
    monthly_fixed_cost,
    recommended_team_size,
    selected_roster_employee,
)
from ui_common import COLOR_BAD, COLOR_GOOD, add_text, cell, draw_box, list_start, meter, money, selected_attr, selection_marker, table_row

SKILL_HEADERS = ("DES", "ART", "AUD", "CODE", "RES")
SKILL_COLUMN_INDEX = {header: index for index, header in enumerate(SKILL_HEADERS)}


def team_layout(state: GameState, width: int, height: int) -> dict:
    """Panel rectangles for the Team page: (y, x, h, w) per panel.

    Wide mode stacks a full-width roster over an applicants/detail split;
    compact mode gives the active side the full width above the detail
    panel. Geometry is identical for both team tabs.
    """
    content_height = height - 4
    team_count = len(state.studio.team)
    applicant_count = len(state.studio.applicants)
    if width >= 120:
        roster_height = min(max(9, team_count + 6), max(9, content_height // 2))
        bottom_y = 2 + roster_height
        bottom_height = content_height - roster_height
        applicant_width = max(52, width * 55 // 100)
        if width >= 160:
            applicant_width = width - 57
        detail_width = width - applicant_width - 1
        return {
            "mode": "wide",
            "roster": (2, 0, roster_height, width),
            "applicants": (bottom_y, 0, bottom_height, applicant_width),
            "detail": (bottom_y, applicant_width + 1, bottom_height, detail_width),
        }
    top_rows = team_count if state.team_tab == 1 else applicant_count
    detail_min = 13
    top_height = min(max(7, top_rows + 4), max(7, content_height - detail_min))
    return {
        "mode": "compact",
        "roster": (2, 0, top_height, width) if state.team_tab == 1 else None,
        "applicants": (2, 0, top_height, width) if state.team_tab == 0 else None,
        "detail": (2 + top_height, 0, content_height - top_height, width),
    }


def recruiting_fee(employee) -> int:
    return max(500, round(employee.monthly_salary * 0.20))


def hire_burn_delta(state: GameState, candidate) -> int:
    per_head = 85 + sum(upgrade.get("per_employee", 0) for upgrade in UPGRADES if upgrade["key"] in state.studio.upgrades)
    burden = 0 if candidate.founder else round(candidate.monthly_salary * 0.13)
    return candidate.monthly_salary + burden + per_head


def can_afford_hire(state: GameState, candidate) -> bool:
    studio = state.studio
    return studio.cash >= recruiting_fee(candidate) + monthly_fixed_cost(studio) + candidate.monthly_salary


def roster_visible_count(team: list, panel_height: int) -> int:
    """Roster row capacity, reserving overview space only when all rows fit."""
    if panel_height >= len(team) + 7:
        return max(0, panel_height - 7)
    return max(0, panel_height - 3)


def visible_roster(team: list, panel_height: int, selected_index: int = 0) -> list:
    """Roster window that keeps the selected employee visible."""
    visible = roster_visible_count(team, panel_height)
    start = list_start(selected_index, len(team), visible)
    return team[start : start + visible]


def roster_columns(inner_width: int) -> list[tuple[str, int, str]]:
    skills = [(header, 4 if header == "CODE" else 3, ">") for header in SKILL_HEADERS]
    if inner_width >= 100:
        return [("NAME", 18, "<"), ("ROLE", 24, "<"), *skills, ("MOR", 3, ">"), ("FAT", 3, ">"), ("TRN", 3, ">"), ("COST/MO", 8, ">"), ("STYLE / QUIRK", inner_width - 87, "<")]
    return [("NAME", 12, "<"), ("ROLE", 17, "<"), *skills, ("MOR", 3, ">"), ("FAT", 3, ">"), ("TRN", 3, ">"), ("COST", 7, ">")]


def applicant_columns(inner_width: int) -> list[tuple[str, int, str]]:
    skills = [(header, 4 if header == "CODE" else 3, ">") for header in SKILL_HEADERS]
    if inner_width >= 88:
        return [("NAME", 16, "<"), ("ROLE", 22, "<"), *skills, ("ASK/YR", 9, ">"), ("STYLE / QUIRK", inner_width - 69, "<")]
    if inner_width >= 60:
        return [("NAME", 14, "<"), ("ROLE", 18, "<"), *skills, ("ASK/YR", 8, ">")]
    return [("NAME", 12, "<"), ("ROLE", 14, "<"), *skills[:4], ("ASK", 7, ">")]


def header_line(columns: list[tuple[str, int, str]]) -> str:
    return table_row(*columns)


def draw_people_rows(panel: curses.window, columns: list[tuple[str, int, str]], entries: list[tuple[list, list[int], int]], selected: int, active: bool, y: int, visible: int) -> None:
    """People table body: one row per ``(values, skills, row_attr)`` entry.

    Follows the shared selection idiom (``> `` marker, highlight on the
    active pane's selected row) and crowns exactly one winner per skill
    column — the best value in each column is drawn in green bold so every
    column has a single, scannable standout.
    """
    if not entries:
        return
    column_best = [max(skills[index] for _, skills, _ in entries) for index in range(len(SKILL_HEADERS))]
    start = list_start(selected, len(entries), visible) if len(entries) > visible else 0
    for offset, (values, skills, row_attr) in enumerate(entries[start : start + visible]):
        index = start + offset
        is_selected = index == selected
        highlight = selected_attr(active and is_selected)
        add_text(panel, y + offset, 2, selection_marker(is_selected), 2, highlight)
        x = 4
        for (header, cell_width, align), value in zip(columns, values):
            attr = highlight or row_attr
            skill_index = SKILL_COLUMN_INDEX.get(header)
            if skill_index is not None and skills[skill_index] == column_best[skill_index]:
                attr = curses.color_pair(COLOR_GOOD) | curses.A_BOLD
            add_text(panel, y + offset, x, cell(value, cell_width, align), cell_width, attr)
            x += cell_width + 1


def draw_person_detail(panel: curses.window, state: GameState, width: int, height: int) -> None:
    """Full, untruncated facts about the selected person on the active side."""
    studio = state.studio
    hiring = state.team_tab == 0
    if hiring:
        if not studio.applicants:
            draw_box(panel, "Person Detail | Applicants")
            add_text(panel, 2, 2, "No applicants right now. The pool refreshes monthly.", width - 4)
            return
        index = min(state.selected_employee, len(studio.applicants) - 1)
        person = studio.applicants[index]
    else:
        person = selected_roster_employee(state)
        if person is None:
            draw_box(panel, "Person Detail | Team")
            add_text(panel, 2, 2, "No team member selected.", width - 4)
            return
    draw_box(panel, f"Person Detail | {person.name}")

    inner = width - 4
    left_width = min(30, max(20, inner - 36))
    meter_width = left_width - 12
    right_x = 4 + left_width
    right_width = width - right_x - 2
    bottom_row = height - 2

    add_text(panel, 1, 2, f"{person.role} | {person.trait} / {person.quirk}", inner, curses.A_BOLD)
    add_text(panel, 2, 2, f"Style: {TRAITS.get(person.trait, 'unclassified')}", inner, curses.color_pair(4))
    add_text(panel, 3, 2, f"Quirk: {QUIRKS.get(person.quirk, 'unclassified')}", inner, curses.color_pair(4))

    row = 5
    step = 2 if bottom_row - row >= 10 else 1
    add_text(panel, row, 2, "SKILLS", left_width, curses.A_BOLD)
    for offset, (name, value) in enumerate(zip(EMPLOYEE_SKILLS, person.all_skills)):
        line_y = row + 1 + offset * step
        if line_y > bottom_row:
            break
        add_text(panel, line_y, 2, f"{name:<8} {value:>2}", 11)
        add_text(panel, line_y, 14, meter(value, 99, meter_width), meter_width, curses.color_pair(3))

    def put(offset: int, text: str, attr: int = 0) -> None:
        if row + offset <= bottom_row:
            add_text(panel, row + offset, right_x, text, right_width, attr)

    if hiring:
        fee = recruiting_fee(person)
        burn = monthly_fixed_cost(state.studio)
        new_burn = burn + hire_burn_delta(state, person)
        runway_after = state.studio.cash / max(1, new_burn)
        affordable = can_afford_hire(state, person)
        put(0, "OFFER", curses.A_BOLD)
        put(1, f"Ask {money(person.annual_salary)}/yr ({money(person.monthly_salary)}/mo)")
        put(2, f"Fee {money(fee)}")
        put(3, f"Burn {money(burn)} -> {money(new_burn)}/mo", curses.color_pair(COLOR_GOOD) if affordable else curses.color_pair(COLOR_BAD) | curses.A_BOLD)
        put(4, f"Runway after hire {runway_after:.1f} mo")
        put(5, "Enter  hire" if affordable else "Blocked: runway under 1 mo", curses.color_pair(4) if affordable else curses.color_pair(5))
        return

    put(0, "WELLBEING", curses.A_BOLD)
    warn = curses.color_pair(COLOR_BAD) if person.morale < 30 or person.fatigue > 70 else 0
    put(1, f"Morale {person.morale:.0f}/100 | Fatigue {person.fatigue:.0f}/100", warn)
    put(2, f"Pay {money(person.annual_salary)}/yr ({money(person.monthly_salary)}/mo)")
    put(3, f"Employed {person.weeks_employed}w | XP {person.experience}/100")
    if person.training_weeks_left:
        put(4, f"In training: {person.training_skill}, {person.training_weeks_left}w left", curses.color_pair(3) | curses.A_BOLD)
    else:
        put(4, "Available for training [L]", curses.color_pair(4))
    if person.founder:
        add_text(panel, bottom_row, 2, "Founder: cannot be dismissed; draw instead of salary.", inner)
    else:
        severance = round(person.annual_salary / 26)
        add_text(panel, bottom_row, 2, f"[D] dismiss: severance {money(severance)}, team morale -5", inner, curses.color_pair(5))


def draw_roster(panel: curses.window, state: GameState, width: int, height: int) -> None:
    studio = state.studio
    target = recommended_team_size(studio)
    draw_box(panel, f"Team | {len(studio.team)}/{target} suggested")
    inner = width - 4
    columns = roster_columns(inner)
    add_text(panel, 1, 4, header_line(columns), inner - 2, curses.A_BOLD)

    show_overview = height >= len(studio.team) + 7
    selected_member = selected_roster_employee(state) if state.team_tab == 1 else None
    selected_index = next((index for index, employee in enumerate(studio.team) if employee is selected_member), -1)
    entries = []
    for employee in studio.team:
        training = f"{employee.training_weeks_left}w" if employee.training_weeks_left else ""
        name = employee.name + (" *" if employee.founder else "")
        personality = f"{employee.trait} / {employee.quirk}"
        values = [name, employee.role, *employee.all_skills, f"{employee.morale:.0f}", f"{employee.fatigue:.0f}", training, money(employee.monthly_salary)]
        if len(columns) > len(values):
            values.append(personality)
        attr = curses.color_pair(COLOR_BAD) if employee.morale < 30 or employee.fatigue > 70 else 0
        entries.append((values, employee.all_skills, attr))
    visible = roster_visible_count(studio.team, height)
    draw_people_rows(panel, columns, entries, selected_index, state.team_tab == 1, y=2, visible=visible)

    overview_y = height - 4
    if show_overview and overview_y >= len(studio.team) + 3:
        payroll = sum(employee.monthly_salary for employee in studio.team)
        avg_morale = sum(employee.morale for employee in studio.team) / len(studio.team)
        avg_fatigue = sum(employee.fatigue for employee in studio.team) / len(studio.team)
        averages = [sum(employee.all_skills[i] for employee in studio.team) / len(studio.team) for i in range(len(EMPLOYEE_SKILLS))]
        skills = "  ".join(f"{name} {value:.0f}" for name, value in zip(SKILL_HEADERS, averages))
        add_text(panel, overview_y, 2, f"Payroll {money(payroll)}/mo ({money(payroll * 12)}/yr) | Avg morale {avg_morale:.0f} | Avg fatigue {avg_fatigue:.0f}", inner)
        add_text(panel, overview_y + 1, 2, f"Team skills  {skills}", inner, curses.color_pair(2))


def draw_applicants(panel: curses.window, state: GameState, width: int, height: int) -> None:
    studio = state.studio
    next_pool = applicant_pool_size(studio)
    draw_box(panel, f"Applicants | {len(studio.applicants)} available | Next pool {next_pool}")
    inner = width - 4
    columns = applicant_columns(inner)
    add_text(panel, 1, 4, header_line(columns), inner - 2, curses.A_BOLD)
    if not studio.applicants:
        add_text(panel, 3, 2, "No applicants right now. The pool refreshes monthly.", inner)
        return
    state.selected_employee = min(state.selected_employee, len(studio.applicants) - 1)
    entries = []
    for employee in studio.applicants:
        personality = f"{employee.trait} / {employee.quirk}"
        values = [employee.name, employee.role, *employee.all_skills, money(employee.annual_salary)]
        if len(columns) > len(values):
            values.append(personality)
        entries.append((values, employee.all_skills, 0))
    draw_people_rows(panel, columns, entries, state.selected_employee, state.team_tab == 0, y=2, visible=max(1, height - 3))


def draw_team_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    layout = team_layout(state, width, height)
    rect = layout["roster"]
    if rect:
        draw_roster(screen.derwin(rect[2], rect[3], rect[0], rect[1]), state, rect[3], rect[2])
    rect = layout["applicants"]
    if rect:
        draw_applicants(screen.derwin(rect[2], rect[3], rect[0], rect[1]), state, rect[3], rect[2])
    rect = layout["detail"]
    draw_person_detail(screen.derwin(rect[2], rect[3], rect[0], rect[1]), state, rect[3], rect[2])
