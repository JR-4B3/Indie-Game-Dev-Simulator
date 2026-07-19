"""Team page: roster and applicant tables plus the team overview block.\nThe active side gets the wider table; panel geometry is shared with the\nmouse handler via :func:`team_panel_widths`."""

from __future__ import annotations

import curses

from simulation import (
    EMPLOYEE_SKILLS,
    QUIRKS,
    TRAITS,
    GameState,
    applicant_pool_size,
    recommended_team_size,
    selected_roster_employee,
)
from ui_common import add_text, draw_box, draw_lines, draw_selectable_list, meter, money


def team_panel_widths(state: GameState, width: int) -> tuple[int, int]:
    if width < 120:
        roster_width = width // 2
    elif state.team_tab == 1:
        roster_width = round(width * 0.64)
    else:
        roster_width = round(width * 0.36)
    roster_width = max(35, min(width - 36, roster_width))
    return roster_width, width - roster_width - 1


def draw_team_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel_height = height - 4
    roster_width, applicant_width = team_panel_widths(state, width)
    roster = screen.derwin(panel_height, roster_width, 2, 0)
    applicants = screen.derwin(panel_height, applicant_width, 2, roster_width + 1)
    target = recommended_team_size(state.studio)
    draw_box(roster, f"Team | {len(state.studio.team)}/{target} suggested")
    next_pool = applicant_pool_size(state.studio)
    draw_box(applicants, f"Applicants | {len(state.studio.applicants)} available | Next pool {next_pool}")

    roster_expanded = roster_width >= 112
    applicant_expanded = applicant_width >= 100
    if roster_expanded:
        roster_inner = roster_width - 4
        flexible_width = roster_inner - 62
        name_width = min(20, max(16, flexible_width // 3))
        trait_width = min(18, max(14, flexible_width - name_width - 20))
        role_width = flexible_width - name_width - trait_width
        roster_header = f"  {'NAME':<{name_width}} {'ROLE':<{role_width}} {'DES':>3} {'ART':>3} {'AUD':>3} {'CODE':>4} {'RES':>3} {'MORALE':>6} {'FATIGUE':>7} {'SALARY/YR':>11} {'COST/MO':>9} {'STYLE / QUIRK':<{trait_width}}"
    else:
        roster_header = f"  {'NAME':<14} {'DES':>3} {'ART':>3} {'AUD':>3} {'CODE':>4} {'MOR':>3} {'FAT':>3} {'PERSONALITY':<12}"
    add_text(roster, 1, 2, roster_header, roster_width - 4, curses.A_BOLD)

    visible_team = state.studio.team[: panel_height - 3]
    selected_member = selected_roster_employee(state) if state.team_tab == 1 else None
    selected_index = next((index for index, employee in enumerate(visible_team) if employee is selected_member), -1)
    roster_rows = []
    for employee in visible_team:
        salary = "owner draw" if employee.founder else f"${employee.annual_salary:,}"
        personality = f"{employee.trait} / {employee.quirk}"
        display_name = f"{employee.name} [TRAIN {employee.training_weeks_left}w]" if employee.training_weeks_left else employee.name
        if roster_expanded:
            line = f"{display_name[:name_width]:<{name_width}} {employee.role[:role_width]:<{role_width}} {employee.design:>3} {employee.art:>3} {employee.audio:>3} {employee.code:>4} {employee.research:>3} {employee.morale:>6.0f} {employee.fatigue:>7.0f} {salary:>11} {money(employee.monthly_salary):>9} {personality[:trait_width]:<{trait_width}}"
        else:
            line = f"{display_name[:14]:<14} {employee.design:>3} {employee.art:>3} {employee.audio:>3} {employee.code:>4} {employee.morale:>3.0f} {employee.fatigue:>3.0f} {personality[:12]:<12}"
        roster_rows.append((line, 0))
    draw_selectable_list(roster, roster_rows, selected_index, state.team_tab == 1, y=2, width=roster_width - 4, scroll=False)

    summary_row = len(state.studio.team[: panel_height - 3]) + 3
    if roster_expanded and summary_row + 5 < panel_height:
        team = state.studio.team
        payroll = sum(employee.monthly_salary for employee in team)
        average_morale = sum(employee.morale for employee in team) / len(team)
        average_fatigue = sum(employee.fatigue for employee in team) / len(team)
        average_tenure = sum(employee.weeks_employed for employee in team) / len(team)
        overview = [
            ("TEAM OVERVIEW", curses.A_BOLD),
            (f"Headcount {len(team)}/{target} suggested | Payroll {money(payroll)}/month | {money(payroll * 12)}/year", 0),
            (f"Average morale {average_morale:.0f}/100 | Fatigue {average_fatigue:.0f}/100 | Tenure {average_tenure:.1f} weeks", 0),
            ("TEAM CAPABILITY", curses.A_BOLD),
        ]
        for skill_index, skill_name in enumerate(EMPLOYEE_SKILLS):
            average_skill = sum(employee.all_skills[skill_index] for employee in team) / len(team)
            lead = max(team, key=lambda employee: employee.all_skills[skill_index])
            overview.append((f"{skill_name:<8} [{meter(average_skill, 100, 18)}] avg {average_skill:>4.0f} | Lead {lead.name} {lead.all_skills[skill_index]}", 0))

        selected_member = selected_roster_employee(state) or team[0]
        overview.extend(
            [
                ("SELECTED TEAM MEMBER", curses.A_BOLD),
                (f"{selected_member.name} | {selected_member.role} | {selected_member.trait} / {selected_member.quirk}", 0),
                (f"Skills  Design {selected_member.design} | Art {selected_member.art} | Audio {selected_member.audio} | Code {selected_member.code} | Research {selected_member.research}", 0),
                (f"Wellbeing  Morale {selected_member.morale:.0f}/100 | Fatigue {selected_member.fatigue:.0f}/100 | Employed {selected_member.weeks_employed}w", 0),
                (f"Compensation  {money(selected_member.annual_salary)}/year | {money(selected_member.monthly_salary)}/month", 0),
                (f"Development  XP {selected_member.experience}/100 | {'TRAINING ' + selected_member.training_skill + ' ' + str(selected_member.training_weeks_left) + 'w' if selected_member.training_weeks_left else 'Available for training'}", 0),
                (f"Style: {TRAITS.get(selected_member.trait, 'unclassified')} | Quirk: {QUIRKS.get(selected_member.quirk, 'unclassified')}", 0),
            ]
        )
        draw_lines(roster, overview[: panel_height - summary_row - 1], summary_row, 2, roster_width - 4)

    if applicant_expanded:
        applicant_header = f"  {'NAME':<16} {'ROLE':<22} {'DES':>3} {'ART':>3} {'AUD':>3} {'CODE':>4} {'RES':>3} {'SALARY/YR':>11} {'STYLE / QUIRK':<14}"
    else:
        applicant_header = f"  {'NAME':<14} {'ROLE':<17} {'DES':>3} {'ART':>3} {'AUD':>3} {'CODE':>4} {'SALARY':>9} {'TRAIT':<10}"
    add_text(applicants, 1, 2, applicant_header, applicant_width - 4, curses.A_BOLD)
    applicant_rows = []
    for employee in state.studio.applicants[: panel_height - 3]:
        personality = f"{employee.trait}/{employee.quirk}"
        if applicant_expanded:
            text = f"{employee.name[:16]:<16} {employee.role[:22]:<22} {employee.design:>3} {employee.art:>3} {employee.audio:>3} {employee.code:>4} {employee.research:>3} {money(employee.annual_salary):>11} {personality[:14]:<14}"
        else:
            text = f"{employee.name[:14]:<14} {employee.role[:17]:<17} {employee.design:>3} {employee.art:>3} {employee.audio:>3} {employee.code:>4} {money(employee.annual_salary):>9} {personality[:10]:<10}"
        applicant_rows.append((text, 0))
    draw_selectable_list(applicants, applicant_rows, state.selected_employee, state.team_tab == 0, y=2, width=applicant_width - 4, scroll=False)
