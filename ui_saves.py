"""Save-slot discovery and the shared save/load picker."""

from __future__ import annotations

import curses
import json
import re
from pathlib import Path

from simulation import GameState, load_game, save_game
from ui_common import add_text, draw_box


def save_directory(state: GameState) -> Path:
    return Path(state.save_path).parent


def discover_save_slots(state: GameState) -> list[str]:
    directory = save_directory(state)
    if not directory.is_dir():
        return []
    return [str(path) for path in sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)]


def slot_label(path_text: str) -> str:
    path = Path(path_text)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        studio = data.get("studio", {})
        project = studio.get("current_project") or {}
        catalog = studio.get("catalog") or []
        title = project.get("title") or (catalog[-1].get("title") if catalog else "New studio")
        date = data.get("clock", {}).get("current_date", "unknown date")
        return f"{title} | {date} | {path.name}"
    except (OSError, json.JSONDecodeError, AttributeError, TypeError):
        return f"Unreadable save | {path.name}"


def next_save_path(state: GameState) -> str:
    directory = save_directory(state)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = state.clock.current_date.strftime("%Y-%m-%d")
    project = state.studio.current_project
    title = project.title if project else (state.studio.catalog[-1].title if state.studio.catalog else "New Studio")
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "studio"
    index = 1
    while True:
        path = directory / f"{slug}-{stamp}-{index:02}.json"
        if not path.exists():
            return str(path)
        index += 1


def open_save_picker(state: GameState, mode: str) -> None:
    state.save_picker_mode = mode
    state.save_slots = discover_save_slots(state)
    state.selected_save_slot = 0
    state.save_picker_open = True


def close_save_picker(state: GameState) -> None:
    state.save_picker_open = False
    state.save_picker_mode = ""
    state.save_slots = []
    state.selected_save_slot = 0


def confirm_save_slot(state: GameState) -> bool:
    if not state.save_picker_open:
        return False
    if state.save_picker_mode == "save":
        if state.selected_save_slot == 0:
            state.save_path = next_save_path(state)
        elif state.selected_save_slot - 1 < len(state.save_slots):
            state.save_path = state.save_slots[state.selected_save_slot - 1]
        try:
            save_game(state)
        except OSError as error:
            state.log(f"Save failed: {error}.")
            return False
        state.log(f"Saved studio to {state.save_path}.")
        close_save_picker(state)
        return True
    if state.selected_save_slot >= len(state.save_slots):
        return False
    try:
        loaded = load_game(state.save_slots[state.selected_save_slot])
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        state.title_message = f"Could not load save: {error}"
        return False
    state.__dict__.clear()
    state.__dict__.update(loaded.__dict__)
    state.log(f"Loaded studio from {state.save_path}.")
    return True


def save_picker_geometry(width: int, height: int) -> tuple[int, int, int, int]:
    popup_width = min(90, max(56, width - 20))
    popup_height = min(max(12, height - 10), 20)
    return popup_height, popup_width, max(2, (height - popup_height) // 2), max(1, (width - popup_width) // 2)


def draw_save_picker(screen: curses.window, state: GameState, width: int, height: int) -> None:
    popup_height, popup_width, popup_y, popup_x = save_picker_geometry(width, height)
    panel = screen.derwin(popup_height, popup_width, popup_y, popup_x)
    panel.erase()
    draw_box(panel, "New Save" if state.save_picker_mode == "save" else "Load Game")
    entries = ([f"Create new save: {Path(next_save_path(state)).name}"] if state.save_picker_mode == "save" else []) + [slot_label(path) for path in state.save_slots]
    if not entries:
        add_text(panel, 3, 3, "No save files found in this save folder.", popup_width - 6, curses.color_pair(5))
    else:
        visible = popup_height - 6
        start = max(0, min(state.selected_save_slot - visible + 1, len(entries) - visible))
        for index, entry in enumerate(entries[start : start + visible], start):
            selected = index == state.selected_save_slot
            label = f"> {entry}" if selected else f"  {entry}"
            add_text(panel, 2 + index - start, 3, label, popup_width - 6, curses.color_pair(3) | curses.A_BOLD if selected else 0)
    add_text(panel, popup_height - 2, 3, "Up/Down selects | Enter confirms | Backspace returns", popup_width - 6, curses.color_pair(4))
