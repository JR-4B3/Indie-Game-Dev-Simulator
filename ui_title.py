"""Fullscreen title screen shown when the game starts.

Unlike the settings/training popups this is not an overlay: it owns the
whole window (border, ASCII-art logo, centered menu) and the run loop
freezes the simulation clock while it is up. The menu offers New Game,
Load Game, Settings, and Quit; input handling lives in ``ui_input`` and
reuses :func:`title_layout` for mouse hit-testing so drawing and clicks
cannot desync.
"""

from __future__ import annotations

import curses

from ui_common import COLOR_ACCENT, COLOR_BAD, COLOR_BORDER, COLOR_GOOD, add_text


TITLE_MENU = ("New Game", "Load Game", "Settings", "Quit")

TITLE_FONT = {
    "A": [" ███ ", "█   █", "█████", "█   █", "█   █"],
    "D": ["████ ", "█   █", "█   █", "█   █", "████ "],
    "E": ["█████", "█    ", "████ ", "█    ", "█████"],
    "G": [" ████", "█    ", "█  ██", "█   █", " ████"],
    "I": ["█████", "  █  ", "  █  ", "  █  ", "█████"],
    "M": ["█   █", "██ ██", "█ █ █", "█   █", "█   █"],
    "N": ["█   █", "██  █", "█ █ █", "█  ██", "█   █"],
    "S": [" ████", "█    ", " ███ ", "    █", "████ "],
    "V": ["█   █", "█   █", "█   █", " █ █ ", "  █  "],
}

SUBTITLE = "a bootstrapped studio simulation"
HINT = "Up/Down select | Enter confirm | Q quit"


def render_art(text: str) -> list[str]:
    rows = ["", "", "", "", ""]
    for index, char in enumerate(text):
        glyph = TITLE_FONT.get(char, ["   "] * 5)
        for row in range(5):
            rows[row] += ("" if index == 0 else " ") + glyph[row]
    return rows


TITLE_ART_LINES = render_art("INDIE GAME") + [""] + render_art("DEV SIM")


def title_layout(width: int, height: int) -> dict:
    """Centered geometry for every title-screen element (draw + mouse)."""
    menu_height = len(TITLE_MENU) * 2 - 1
    total_height = len(TITLE_ART_LINES) + 1 + 1 + menu_height + 1 + 1
    start_y = 1 + max(0, (height - 2 - total_height) // 2)
    art = []
    for offset, line in enumerate(TITLE_ART_LINES):
        if line:
            art.append((start_y + offset, max(1, (width - len(line)) // 2), line))
    subtitle_y = start_y + len(TITLE_ART_LINES)
    menu_y = subtitle_y + 2
    items = []
    for index, name in enumerate(TITLE_MENU):
        label = f"[ {name} ]"
        items.append((menu_y + index * 2, max(1, (width - len(label)) // 2), label))
    message_y = menu_y + menu_height
    return {
        "art": art,
        "subtitle_y": subtitle_y,
        "items": items,
        "message_y": message_y,
        "hint_y": message_y + 1,
    }


def draw_title_screen(screen: curses.window, state, width: int, height: int) -> None:
    screen.erase()
    screen.attron(curses.color_pair(COLOR_BORDER))
    screen.border()
    screen.attroff(curses.color_pair(COLOR_BORDER))
    layout = title_layout(width, height)
    for y, x, line in layout["art"]:
        add_text(screen, y, x, line, width - x - 1, curses.color_pair(COLOR_BORDER) | curses.A_BOLD)
    add_text(screen, layout["subtitle_y"], max(1, (width - len(SUBTITLE)) // 2), SUBTITLE, len(SUBTITLE), curses.color_pair(COLOR_ACCENT))
    for index, (y, x, label) in enumerate(layout["items"]):
        selected = index == state.title_menu_index
        attr = curses.color_pair(COLOR_ACCENT) | curses.A_BOLD if selected else 0
        add_text(screen, y, x, label, len(label), attr)
    if state.title_message:
        message = state.title_message[: width - 4]
        add_text(screen, layout["message_y"], max(1, (width - len(message)) // 2), message, len(message), curses.color_pair(COLOR_BAD))
    add_text(screen, layout["hint_y"], max(1, (width - len(HINT)) // 2), HINT, len(HINT), curses.color_pair(COLOR_GOOD))
