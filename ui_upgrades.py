"""Studio Development: timed, branching capability research."""

from __future__ import annotations

import curses

from simulation import (
    RESEARCH_BRANCHES,
    GameState,
    completed_research_keys,
    estimated_research_weeks,
    has_research,
    monthly_fixed_cost,
    research_branch_counts,
    research_nodes_for_branch,
    research_requirements,
    research_work_requirement,
)
from ui_common import add_text, draw_box, draw_selectable_list, meter, money, wrap_text


def selected_branch_nodes(state: GameState) -> list[dict]:
    branch = RESEARCH_BRANCHES[state.selected_research_branch % len(RESEARCH_BRANCHES)]
    return research_nodes_for_branch(branch)


def node_status(state: GameState, node: dict) -> tuple[str, int]:
    studio = state.studio
    if node["key"] in completed_research_keys(studio):
        return "COMPLETE", curses.color_pair(4)
    if studio.active_research and studio.active_research.node_key == node["key"]:
        return f"ACTIVE {studio.active_research.progress:.0%}", curses.color_pair(3) | curses.A_BOLD
    if any(job.node_key == node["key"] for job in studio.research_queue):
        return "QUEUED", curses.color_pair(2)
    if research_requirements(studio, node):
        return "LOCKED", curses.color_pair(5)
    return "AVAILABLE", 0


def draw_branch_tabs(panel: curses.window, state: GameState, width: int) -> None:
    x = 2
    for index, branch in enumerate(RESEARCH_BRANCHES):
        label = f" {branch} "
        attr = curses.color_pair(3) | curses.A_BOLD if index == state.selected_research_branch else curses.color_pair(2)
        if x + len(label) >= width - 2:
            break
        add_text(panel, 1, x, label, len(label), attr)
        x += len(label) + 1


def draw_upgrades(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel = screen.derwin(height - 4, width, 2, 0)
    draw_box(panel, "Studio Development")
    inner = width - 4
    draw_branch_tabs(panel, state, width)
    nodes = selected_branch_nodes(state)
    state.selected_upgrade = max(0, min(state.selected_upgrade, len(nodes) - 1))
    completed = completed_research_keys(state.studio)
    counts = research_branch_counts(state.studio)
    branch = RESEARCH_BRANCHES[state.selected_research_branch]

    if width < 120:
        list_height = max(7, (height - 6) // 2)
        rows = []
        for node in nodes:
            status, attr = node_status(state, node)
            rows.append((f"T{node['tier']} {node['name']:<27} {status:>12} {money(node['cost']):>9}", attr))
        draw_selectable_list(panel, rows, state.selected_upgrade, True, y=3, width=inner, visible=list_height - 1, highlight_wins=False)
        detail_y = list_height + 3
        detail_width = inner
    else:
        list_width = max(62, width * 2 // 3)
        detail_width = width - list_width - 5
        add_text(panel, 2, 2, f"  {'TIER':<4} {'CAPABILITY':<31} {'STATUS':>13} {'COST':>10} {'R&D WORK':>11}", list_width - 2, curses.A_BOLD)
        rows = []
        for node in nodes:
            status, attr = node_status(state, node)
            work = research_work_requirement(state.studio, node)
            rows.append((f"{node['tier']:<4} {node['name']:<31} {status:>13} {money(node['cost']):>10} {work:>11,.0f}", attr))
        draw_selectable_list(panel, rows, state.selected_upgrade, True, y=3, width=list_width - 2, visible=height - 8, highlight_wins=False)
        detail_y = 2
        add_text(panel, 2, list_width + 1, "SELECTED CAPABILITY", detail_width, curses.A_BOLD)

    node = nodes[state.selected_upgrade]
    status, status_attr = node_status(state, node)
    x = 2 if width < 120 else width * 2 // 3 + 1
    y = detail_y
    add_text(panel, y, x, node["name"], detail_width, curses.A_BOLD)
    add_text(panel, y + 1, x, f"{branch} tier {node['tier']} | {status}", detail_width, status_attr)
    add_text(panel, y + 2, x, f"Cost {money(node['cost'])} | R&D {research_work_requirement(state.studio, node):,.0f} | ETA ~{estimated_research_weeks(state.studio, node)}w", detail_width)
    requirements = research_requirements(state.studio, node)
    requirement_text = "; ".join(requirements) if requirements else "Ready to research"
    add_text(panel, y + 3, x, requirement_text, detail_width, curses.color_pair(5) if requirements else curses.color_pair(4))
    effect_lines = 1 if width < 120 else 2
    for offset, line in enumerate(wrap_text(node["effect"], detail_width)[:effect_lines], y + 5):
        add_text(panel, offset, x, line, detail_width)

    queue_y = y + 8
    if queue_y < height - 7:
        add_text(panel, queue_y, x, "R&D PIPELINE", detail_width, curses.A_BOLD)
        active = state.studio.active_research
        if active:
            active_node = next(item for item in nodes if item["key"] == active.node_key) if any(item["key"] == active.node_key for item in nodes) else None
            active_name = active_node["name"] if active_node else active.node_key
            add_text(panel, queue_y + 1, x, active_name, detail_width, curses.color_pair(3) | curses.A_BOLD)
            add_text(panel, queue_y + 2, x, f"[{meter(active.work_done, active.required_work, max(8, detail_width - 8))}] {active.progress:.0%}", detail_width, curses.color_pair(4))
        else:
            add_text(panel, queue_y + 1, x, "No active research", detail_width)
        for index, job in enumerate(state.studio.research_queue[: max(0, height - queue_y - 7)], 1):
            queued = next((item for item in nodes if item["key"] == job.node_key), None)
            add_text(panel, queue_y + 2 + index, x, f"{index}. {queued['name'] if queued else job.node_key}", detail_width)

    if has_research(state.studio, "department_leads"):
        labels = ("OFF", "LOW", "NORMAL", "HIGH")
        priorities = " ".join(f"[{index + 1}]{kind[:4].title()} {labels[state.studio.work_priorities.get(kind, 2)]}" for index, kind in enumerate(("project", "contract", "update", "promotion", "research")))
        add_text(panel, height - 7, 2, priorities + f" | [A] Auto leave {'ON' if state.studio.auto_vacation else 'OFF'}", inner, curses.color_pair(2))
    footer = f"Branch mastery {counts[branch]} | Completed {len(completed)}/{len(sum((research_nodes_for_branch(item) for item in RESEARCH_BRANCHES), []))} | Burn {money(monthly_fixed_cost(state.studio))}/mo"
    add_text(panel, height - 6, 2, footer, inner, curses.color_pair(4))
