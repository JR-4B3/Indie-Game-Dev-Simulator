"""Entry point and composition root for the Indie Studio Game Dev Sim.

The UI is layered; each module has one job:

- ``ui_common``    -- design-system primitives: text, panels, meters, lists.
- ``ui_chrome``    -- the frame around every page: top tabs/action bar,
                      bottom metric/date bars, and all popups.
- ``ui_hub``       -- Hub page (studio dashboard).
- ``ui_title``     -- fullscreen title screen (New Game / Load Game / Settings / Quit).
- ``ui_newgame``   -- New Game wizard.
- ``ui_team``      -- Team page.
- ``ui_contracts`` -- Contract Board page.
- ``ui_games``     -- Game catalogue page, Update Planner, Promotion Planning.
- ``ui_upgrades``  -- Upgrades page.
- ``ui_stats``     -- Statistics page.
- ``ui_input``     -- keyboard/mouse handling and context actions.

This file wires them together: it owns the screen dispatch table, the curses
run loop, the headless ``--simulate`` mode, and CLI parsing. Names are
re-exported here so existing tooling (and tests) can keep importing them
from ``main``.
"""

from __future__ import annotations

import argparse
import curses
import json
import time
from datetime import timedelta
from pathlib import Path

from simulation import TIME_SPEEDS, GameState, advance_days, advance_game, load_game, runway_months
from ui_chrome import (
    active_top_tab,
    bottom_time_layout,
    draw_footer,
    draw_header,
    draw_insolvency_popup,
    draw_production_review,
    draw_settings_popup,
    draw_training_popup,
    footer_button_ranges,
    footer_layout,
    global_action_layout,
    status_segments,
    top_context_uses_second_row,
    top_control_layout,
    top_tab_actions,
    top_tab_layout,
)
from ui_common import add_text, money
from ui_contracts import draw_contract_screen
from ui_games import draw_games_screen, draw_marketing_screen, draw_update_planner_screen
from ui_hub import draw_dashboard, draw_main_content
from ui_input import CTRL_S, handle_key, handle_mouse, handle_new_game_key, open_new_game
from ui_newgame import draw_new_game, new_game_panel_geometry
from ui_stats import draw_analysis
from ui_team import draw_team_screen, team_layout
from ui_title import draw_title_screen
from ui_upgrades import draw_upgrades


DEFAULT_SAVE_FILE = "saves/gamedev_save.json"
NAVIGATION_KEYS = {curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT, curses.KEY_RIGHT}


SCREEN_DRAWERS = {
    "new_game": draw_new_game,
    "team": draw_team_screen,
    "contracts": draw_contract_screen,
    "games": draw_games_screen,
    "update_planner": draw_update_planner_screen,
    "marketing": draw_marketing_screen,
    "upgrades": draw_upgrades,
    "analysis": draw_analysis,
}


_LAYOUT_STATE: tuple | None = None


def draw_screen(screen: curses.window, state: GameState) -> None:
    height, width = screen.getmaxyx()
    global _LAYOUT_STATE
    layout_state = (
        state.modal,
        state.title_screen,
        state.team_tab,
        state.games_tab,
        state.marketing_tab,
        state.analysis_view,
        state.new_game_step,
        state.settings_open,
        state.training_open,
        bool(state.studio.current_project),
        len(state.studio.team),
        len(state.studio.applicants),
        len(state.studio.catalog),
        height,
        width,
    )
    if layout_state != _LAYOUT_STATE:
        # Geometry changed: force a full repaint so cells from the previous
        # layout cannot linger (diff redraw alone can leave ghosts when
        # panels move or resize between frames).
        screen.clear()
        _LAYOUT_STATE = layout_state
    else:
        screen.erase()
    if height < 24 or width < 74:
        add_text(screen, 0, 0, "Terminal too small. Need at least 74x24. Resize or press Q.", width)
        return
    if state.title_screen:
        draw_title_screen(screen, state, width, height)
        if state.settings_open:
            draw_settings_popup(screen, state, width, height)
        return
    draw_header(screen, state, width)
    drawer = SCREEN_DRAWERS.get(state.modal)
    if drawer is None:
        y = draw_dashboard(screen, state, width)
        draw_main_content(screen, state, width, height, y)
    else:
        drawer(screen, state, width, height)
    draw_footer(screen, state, height, width)
    project = state.studio.current_project
    if project and project.pending_decision is not None:
        draw_production_review(screen, state, width, height)
    if state.training_open:
        draw_training_popup(screen, state, width, height)
    if state.settings_open:
        draw_settings_popup(screen, state, width, height)
    if state.studio.closed:
        draw_insolvency_popup(screen, state, width, height)



def run(screen: curses.window, load_save: bool, save_path: str) -> None:
    curses.curs_set(0)
    curses.raw()
    curses.set_escdelay(25)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_GREEN, -1)
    curses.init_pair(5, curses.COLOR_RED, -1)
    screen.nodelay(True)
    screen.keypad(True)
    try:
        curses.mouseinterval(100)
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
    except curses.error:
        pass
    if load_save:
        try:
            state = load_game(save_path)
            state.log(f"Loaded studio from {save_path}.")
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            state = GameState(save_path=save_path)
            state.log(f"Could not load save: {error}. Started a new studio.")
    else:
        state = GameState(save_path=save_path)
    state.title_screen = True
    previous_time = time.monotonic()
    running = True
    while running:
        now = time.monotonic()
        days = 0 if state.title_screen else state.clock.update((now - previous_time) * TIME_SPEEDS[min(state.time_speed_index, len(TIME_SPEEDS) - 1)])
        previous_time = now
        advance_days(state, days)
        draw_screen(screen, state)
        screen.refresh()
        key = screen.getch()
        while key != -1:
            running = handle_key(state, key, screen.getmaxyx())
            if not running:
                break
            if key in NAVIGATION_KEYS:
                curses.flushinp()
                break
            key = screen.getch()
        time.sleep(0.03)


def simulate(weeks: int, load_save: bool, save_path: str) -> None:
    state = load_game(save_path) if load_save else GameState(save_path=save_path)
    for _ in range(weeks):
        state.clock.current_date += timedelta(days=7)
        state.clock.week += 1
        advance_game(state, 1)
    print(f"Date: {state.clock.current_date:%d %b %Y}")
    print(f"Cash: {money(state.studio.cash)} | Runway: {runway_months(state.studio):.1f} months")
    print(f"Team: {len(state.studio.team)} | Released: {state.studio.released_games} | Followers: {state.studio.followers:,}")
    for message in state.logs[:8]:
        print(f"- {message}")


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the realistic indie studio simulation.")
    parser.add_argument("save_path", nargs="?", help="save file to load (for example: saves/gamedev_save.json)")
    parser.add_argument("--load", action="store_true", help="load a studio; optionally put its path after this flag")
    parser.add_argument("--save-file", dest="save_file_option", help=f"explicit save path (default: {DEFAULT_SAVE_FILE})")
    parser.add_argument("--simulate", type=int, metavar="WEEKS", help="advance without curses and print a summary")
    args = parser.parse_args(arguments)
    if args.save_path and args.save_file_option:
        parser.error("choose either a positional save path or --save-file, not both")
    positional_path = args.save_path
    args.save_path = positional_path or args.save_file_option or DEFAULT_SAVE_FILE
    args.load = args.load or positional_path is not None
    return args


def main() -> None:
    args = parse_args()
    if args.load and not Path(args.save_path).is_file():
        available = ", ".join(
            str(path) for path in sorted(Path.cwd().glob("*.json")) + sorted(Path("saves").glob("*.json"))
        ) or "none"
        raise SystemExit(f"Save file not found: {args.save_path}\nAvailable JSON saves: {available}")
    if args.simulate is not None:
        simulate(max(0, args.simulate), args.load, args.save_path)
    else:
        curses.wrapper(run, args.load, args.save_path)


if __name__ == "__main__":
    main()
