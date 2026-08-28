"""Creative pipeline screens: the idea shelf, the concept workspace, and the
design & technical plan review. Genre and theme are inferred from team ideas;
the player never picks them from a list."""

from __future__ import annotations

import curses

from game_data import GENRES, TOPICS
from simulation import (
    ANNOUNCEMENT_STRATEGIES,
    AUDIENCES,
    CHANNELS,
    RoughIdea,
    channel_lock_reason,
    selected_platform_indexes,
    storefront_display_order,
    toggle_platform_selection,
    CREATIVE_DIRECTIONS,
    GAME_FORMATS,
    MARKETING,
    MONETIZATION_MODELS,
    PRICE_POINTS,
    RELEASE_POLICIES,
    RELEASE_STRATEGIES,
    SCOPES,
    GameState,
    capacity_drains,
    concept_focus,
    has_research,
    market_report,
    monthly_fixed_cost,
    plan_requirements,
    publisher_by_name,
    projected_weekly_output,
    research_requirement_for_channel,
    research_requirement_for_format,
    research_requirement_for_marketing,
    research_requirement_for_monetization,
    research_requirement_for_scope,
    research_requirement_for_strategy,
    selected_announcement_strategy,
    selected_monetization_model,
    selected_price_point,
    selected_release_policy,
    commit_design_plan,
    begin_design_review,
    shelve_concept,
    start_experiment,
    idea_engine,
)
from ui_common import COLOR_GOOD, add_text, draw_box, draw_selectable_list, meter, money
from ui_theme import glyph


STAGE_BANNER = "IDEA > CONCEPT > DESIGN > DEVELOPMENT > TESTING > RELEASE"


def stage_banner_line(current: str, width: int) -> tuple[str, int]:
    """One-line stage ribbon; returns (text, highlight_offset) or (text, -1)."""
    stages = ("IDEA", "CONCEPT", "DESIGN", "DEVELOPMENT", "TESTING", "RELEASE")
    key_map = {"concept": "CONCEPT", "design": "DESIGN", "development": "DEVELOPMENT",
               "testing": "TESTING", "gold": "RELEASE"}
    label = key_map.get(current, "")
    text = STAGE_BANNER
    offset = -1
    if label:
        prefix = " > ".join(stages[: stages.index(label)])
        offset = len(prefix) + (3 if prefix else 0)
    return text, offset


def draw_stage_ribbon(panel: curses.window, row: int, stage: str, width: int) -> None:
    text, offset = stage_banner_line(stage, width)
    add_text(panel, row, 2, text, width - 4, curses.color_pair(6))
    if offset >= 0:
        label = dict(zip(("IDEA", "CONCEPT", "DESIGN", "DEVELOPMENT", "TESTING", "RELEASE"), range(6)))
        current = text[offset:offset + len(text[offset:].split(" > ")[0])]
        span = len(current)
        add_text(panel, row, 2 + offset, current, min(span, width - 4 - offset), curses.color_pair(3) | curses.A_BOLD | curses.A_REVERSE)


def ordered_shelf(state: GameState) -> list[RoughIdea]:
    """Shelf order shown to the player: fresh first, newest on top."""
    status_rank = {"fresh": 0, "cooling": 1, "dormant": 2}
    return sorted(state.studio.idea_shelf, key=lambda item: (status_rank.get(item.status, 0), -item.created_week))


def shelf_rows(state: GameState) -> list[tuple[str, int]]:
    rows = []
    for idea in ordered_shelf(state):
        signals = ", ".join(idea.signal_words())
        origin = {"release": "inspired by a release", "contract": "contract insight", "training": "training spark"}.get(idea.origin, f"{idea.source}'s idea")
        cool = "dormant" if idea.status == "dormant" else f"cools in {max(0, idea.cool_at_week - state.clock.week)}w"
        attr = curses.color_pair(6) if idea.status == "dormant" else curses.color_pair(2) if idea.status == "cooling" else 0
        rows.append((f"{idea.title}  [{signals}]  {origin} | {cool}", attr))
    return rows


def draw_idea_shelf(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel = screen.derwin(height - 4, width, 2, 0)
    draw_box(panel, "Idea Shelf | Rough Pitches")
    add_text(panel, 1, 2, "Rested teammates jot down rough ideas over time. Choose one to explore in Concept.", width - 4, curses.color_pair(4))
    ideas = state.studio.idea_shelf
    if not ideas:
        add_text(panel, 3, 2, "The shelf is empty. Give the team time to think; tired teams pitch nothing.", width - 4, curses.color_pair(2))
        add_text(panel, 4, 2, "Contracts, releases, and training can also spark ideas.", width - 4, curses.color_pair(6))
    state.selected_idea = min(state.selected_idea, max(0, len(ideas) - 1))
    draw_selectable_list(panel, shelf_rows(state), state.selected_idea, bool(ideas), y=3, width=width - 4, visible=max(1, height - 9))
    add_text(panel, height - 3, 2, "Enter: open concept   D: discard idea   Esc: back", width - 4, curses.color_pair(4))
    if ideas:
        idea = ordered_shelf(state)[state.selected_idea]
        row = height - 5
        for index, line in enumerate(idea.pitch_lines()):
            add_text(panel, row + index, 2, line[: width - 4], width - 4, curses.A_BOLD)
        add_text(panel, row + len(idea.pitch_lines()), 2, f"Unanswered: {idea.uncertainty}", width - 4, curses.color_pair(3))


def draw_concept_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    project = state.studio.current_project
    panel = screen.derwin(height - 4, width, 2, 0)
    if project is None or project.stage != "concept":
        draw_box(panel, "Concept")
        add_text(panel, 1, 2, "No concept is open.", width - 4, curses.color_pair(2))
        return
    draw_box(panel, f"Concept | {project.title}")
    draw_stage_ribbon(panel, 1, "concept", width)
    gdd = project.gdd
    pitch_width = max(24, min(46, width // 3))
    pitch = panel.derwin(height - 6, pitch_width, 3, 0)
    draw_box(pitch, "The Pitch")
    add_text(pitch, 1, 2, f'Fantasy: {gdd.get("fantasy", "")}', pitch_width - 4, curses.color_pair(3))
    for index, line in enumerate(gdd.get("pitch_lines", [])):
        add_text(pitch, 3 + index * 2, 2, line, pitch_width - 4, curses.A_BOLD)
    uncertainty_row = 3 + len(gdd.get("pitch_lines", [])) * 2 + 1
    add_text(pitch, uncertainty_row, 2, "Unanswered:", pitch_width - 4, curses.color_pair(2) | curses.A_BOLD)
    add_text(pitch, uncertainty_row + 1, 2, gdd.get("uncertainty", ""), pitch_width - 4, curses.color_pair(2))
    clarity = float(gdd.get("clarity", 0.5))
    doubt = float(gdd.get("technical_doubt", 0.2))
    originality = float(gdd.get("originality", 0.5))
    signals = ["clear fantasy" if clarity >= 0.75 else "interesting but vague" if clarity >= 0.45 else "incoherent pitch"]
    if originality >= 0.8:
        signals.append("striking concept")
    if doubt >= 0.6:
        signals.append("technically doubtful")
    elif doubt <= 0.25:
        signals.append("proven tech")
    if gdd.get("hook"):
        signals.append("unusual hook")
    add_text(pitch, height - 9, 2, ", ".join(signals), pitch_width - 4, curses.color_pair(6))
    if gdd.get("findings"):
        add_text(pitch, height - 8, 2, f"{len(gdd['findings'])} finding(s) recorded", pitch_width - 4, curses.color_pair(4))

    work_width = width - pitch_width - 1
    work = panel.derwin(height - 6, work_width, 3, pitch_width + 1)
    draw_box(work, "Experiments")
    if project.active_experiment:
        experiment = idea_engine.experiment_by_key(project.active_experiment)
        add_text(work, 1, 2, f"Running: {experiment.name}", work_width - 4, curses.color_pair(3) | curses.A_BOLD)
        add_text(work, 2, 2, f"~{project.experiment_days_left} workdays left", work_width - 4, curses.color_pair(2))
    else:
        available = idea_engine.available_experiments(type("V", (), {"hook": gdd.get("hook", ""), "technical_doubt": gdd.get("technical_doubt", 0.0), "tags": gdd.get("tags", [])})())
        rows = []
        for index, experiment in enumerate(available):
            cursor = index == state.selected_experiment
            rows.append((f"{experiment.name}  ({experiment.weeks}w) - {experiment.blurb}", curses.color_pair(3) | curses.A_BOLD if cursor else 0))
        draw_selectable_list(work, rows, state.selected_experiment, not project.active_experiment, y=1, width=work_width - 4, visible=height - 12)
    findings_row = height - 10
    add_text(work, findings_row, 2, "FINDINGS", work_width - 4, curses.A_BOLD)
    recent = list(reversed(gdd.get("findings", [])))[:3]
    for offset, finding in enumerate(recent):
        add_text(work, findings_row + 1 + offset * 2, 2, f"W{finding['week']} {finding['experiment']} ({finding['confidence']}):", work_width - 4, curses.color_pair(6))
        add_text(work, findings_row + 2 + offset * 2, 2, finding["text"], work_width - 4, curses.color_pair(4))
    add_text(panel, height - 3, 2, "Enter: run selected experiment   E: end concept > design   S: shelve idea   Esc: games", width - 4, curses.color_pair(4))


def draw_design_review(screen: curses.window, state: GameState, width: int, height: int) -> None:
    project = state.studio.current_project
    panel = screen.derwin(height - 4, width, 2, 0)
    if project is None or project.stage != "design":
        draw_box(panel, "Design Review")
        add_text(panel, 1, 2, "No design review is open.", width - 4, curses.color_pair(2))
        return
    draw_box(panel, f"Design & Technical Plan | {project.title}")
    draw_stage_ribbon(panel, 1, "design", width)
    packages = project.gdd.get("presentation_options", [])
    advice = project.gdd.get("team_advice", [])
    row = 3
    if advice:
        add_text(panel, row, 2, "TEAM ADVICE", width - 4, curses.A_BOLD)
        row += 1
        for entry in advice:
            marker = "  (experienced)" if entry.get("reliable") else "  (green team - may be off)"
            add_text(panel, row, 2, f"{entry['who']} {marker}: {entry['text']}", width - 4, curses.color_pair(3) if entry.get("reliable") else curses.color_pair(2))
            row += 1
        row += 1
    add_text(panel, row, 2, "PRESENTATION DIRECTION" + ("  [T: tweak axes]" if not state.tweak_presentation else "  [T: back to packages]"), width - 4, curses.A_BOLD)
    row += 1
    if not state.tweak_presentation:
        rows = []
        for index, package in enumerate(packages):
            marker = " <" if index == state.selected_presentation else ""
            attr = curses.color_pair(3) | curses.A_BOLD if index == state.selected_presentation else 0
            rows.append((f"{package['name']}  x{package['work']:.2f} work{marker}", attr))
        draw_selectable_list(panel, rows, state.selected_presentation, state.selected_design_focus == 0, y=row, width=width - 4, visible=min(len(packages) + 1, 5))
        row += len(packages) + 1
        if 0 <= state.selected_presentation < len(packages):
            add_text(panel, row, 2, packages[state.selected_presentation]["note"], width - 4, curses.color_pair(6))
            row += 1
    else:
        from sim_core.ideas import FORMS, STYLES, CAMERAS, MOVEMENTS, DENSITIES
        axes = [("form", "Form", FORMS), ("style", "Style", STYLES), ("camera", "Camera", CAMERAS), ("movement", "Movement", MOVEMENTS), ("density", "Density", DENSITIES)]
        for axis_offset, (key, label, values) in enumerate(axes):
            current = state.design_tweaks.get(key) or (packages[state.selected_presentation][key] if packages else values[0])
            index = values.index(current) if current in values else 0
            marker = " <" if state.selected_design_focus == axis_offset + 1 else ""
            attr = curses.color_pair(3) | curses.A_BOLD if state.selected_design_focus == axis_offset + 1 else 0
            add_text(panel, row + axis_offset, 2, f"{label:<10} <{current}>{marker}", width - 4, attr)
        row += len(axes) + 1
    plan_specs = (
        ("Scope", "selected_scope", SCOPES),
        ("Game format", "selected_format", GAME_FORMATS),
        ("Audience", "selected_audience", AUDIENCES),
        ("Lead pillar", "selected_creative_primary", CREATIVE_DIRECTIONS),
        ("Support pillar", "selected_creative_secondary", CREATIVE_DIRECTIONS),
        ("Monetization", "selected_monetization", MONETIZATION_MODELS),
        ("Price", "selected_price", PRICE_POINTS),
        ("Announcement", "selected_announcement", ANNOUNCEMENT_STRATEGIES),
        ("Release policy", "selected_release_policy", RELEASE_POLICIES),
        ("Launch life", "selected_release_strategy", RELEASE_STRATEGIES),
        ("Marketing", "selected_marketing", MARKETING),
    )
    tweak_offset = 6 if state.tweak_presentation else 1
    add_text(panel, row, 2, "PRODUCTION PLAN", width - 4, curses.A_BOLD)
    row += 1
    plan_start = row
    for index, (label, attribute, options) in enumerate(plan_specs):
        value_index = getattr(state, attribute)
        value_index = value_index % len(options) if value_index >= 0 else value_index
        option = options[value_index]
        shown = option["name"]
        cursor = state.selected_design_focus == tweak_offset + index
        attr = curses.color_pair(3) | curses.A_BOLD if cursor else 0
        requirement = None
        if attribute == "selected_scope":
            requirement = research_requirement_for_scope(value_index)
        elif attribute == "selected_format":
            requirement = research_requirement_for_format(value_index)
        elif attribute == "selected_monetization":
            requirement = research_requirement_for_monetization(value_index)
        elif attribute == "selected_release_strategy":
            requirement = research_requirement_for_strategy(value_index)
        elif attribute == "selected_marketing":
            requirement = research_requirement_for_marketing(value_index)
        locked = bool(requirement and not has_research(state.studio, requirement))
        if locked:
            attr = curses.color_pair(5)
        add_text(panel, row + index, 2, f"{label:<15} <{shown}>{' | LOCKED' if locked else ''}", width - 4, attr)
    row += len(plan_specs)
    # Storefront line
    cursor_store = state.selected_design_focus == tweak_offset + len(plan_specs)
    attr = curses.color_pair(3) | curses.A_BOLD if cursor_store else 0
    platforms = [CHANNELS[i]["name"] for i in selected_platform_indexes(state)]
    add_text(panel, row, 2, f"{'Storefronts':<15} {', '.join(platforms) or CHANNELS[state.selected_channel]['name']}  ([T] tags extra stores)", width - 4, attr)
    row += 1
    commit_cursor = state.selected_design_focus == tweak_offset + len(plan_specs) + 1
    attr = curses.color_pair(4) | curses.A_BOLD | curses.A_REVERSE if commit_cursor else curses.color_pair(4) | curses.A_BOLD
    add_text(panel, row + 1, 2, "COMMIT TO PRODUCTION", width - 4, attr)
    requirements = plan_requirements(state)
    if requirements:
        add_text(panel, row + 2, 2, f"Blocked: needs {', '.join(requirements)}", width - 4, curses.color_pair(5))
    else:
        report = market_report(state)
        output = projected_weekly_output(state.studio, concept_focus(state))
        weeks = max(4, round(report["work"] / output))
        add_text(panel, row + 2, 2, f"Forecast {report['score_low']}-{report['score_high']} score | {weeks}w | confidence {report['confidence']}%", width - 4, curses.color_pair(6))
    add_text(panel, height - 3, 2, "Up/Down: move   Left/Right: change   Enter: confirm   T: tweak presentation   Esc: back to concept", width - 4, curses.color_pair(4))
