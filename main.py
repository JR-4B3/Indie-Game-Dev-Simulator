from __future__ import annotations

import curses
import time
from dataclasses import dataclass
from datetime import date, timedelta


SECONDS_PER_WEEK = 30.0
START_DATE = date(1970, 1, 1)


@dataclass
class GameClock:
    current_date: date = START_DATE
    week: int = 1
    _elapsed_seconds: float = 0.0

    def update(self, delta_seconds: float) -> None:
        self._elapsed_seconds += delta_seconds

        while self._elapsed_seconds >= SECONDS_PER_WEEK:
            self._elapsed_seconds -= SECONDS_PER_WEEK
            self.week += 1
            self.current_date += timedelta(days=7)

    @property
    def week_progress(self) -> float:
        return self._elapsed_seconds / SECONDS_PER_WEEK


def format_date(value: date) -> str:
    return value.strftime("%d %b %Y")


def draw_box(window: curses.window, height: int, width: int, title: str) -> None:
    if height < 3 or width < 4:
        return

    window.attron(curses.color_pair(2))
    window.border()
    window.attroff(curses.color_pair(2))

    if title:
        add_clipped(window, 0, 2, f" {title} ", width - 4, curses.color_pair(3) | curses.A_BOLD)


def add_clipped(window: curses.window, y: int, x: int, text: str, width: int, attr: int = 0) -> None:
    max_y, max_x = window.getmaxyx()
    if width <= 0 or y < 0 or y >= max_y or x < 0 or x >= max_x - 1:
        return

    safe_width = min(width, max_x - x - 1)
    window.addstr(y, x, text[:safe_width], attr)


def draw_overlay(screen: curses.window, clock: GameClock) -> None:
    height, width = screen.getmaxyx()
    screen.erase()

    if height < 15 or width < 45:
        add_clipped(screen, 0, 0, "Terminal too small. Resize or press Q to quit.", width)
        return

    header = f" GameDev Tycoon Terminal | {format_date(clock.current_date)} | Week {clock.week} "
    add_clipped(screen, 0, 0, header.ljust(width), width, curses.color_pair(1) | curses.A_BOLD)

    progress_width = max(10, width - 31)
    filled = int(progress_width * clock.week_progress)
    progress = "#" * filled + "-" * (progress_width - filled)
    add_clipped(screen, 1, 0, f" Next week: [{progress}] 30s/week", width, curses.color_pair(4))

    left_width = max(22, width // 2)
    right_width = width - left_width - 1


    studio = screen.derwin(7, left_width, 3, 0)
    draw_box(studio, 7, left_width, "Studio")
    add_clipped(studio, 1, 2, "Cash:       $10,000", left_width - 4)
    add_clipped(studio, 2, 2, "Reputation: Unknown", left_width - 4)
    add_clipped(studio, 3, 2, "Fans:       0", left_width - 4)
    add_clipped(studio, 5, 2, "Goal: survive your first year", left_width - 4, curses.color_pair(4))

    project = screen.derwin(7, right_width, 3, left_width + 1)
    draw_box(project, 7, right_width, "Current Game")
    add_clipped(project, 1, 2, "No project started", right_width - 4)
    add_clipped(project, 2, 2, "Next MVP: choose topic/genre", right_width - 4)
    add_clipped(project, 3, 2, "Keep creation varied with decisions", right_width - 4)

    log_height = height - 12
    log = screen.derwin(log_height, width, 10, 0)
    draw_box(log, log_height, width, "Activity")
    add_clipped(log, 1, 2, "1970 begins. Your tiny studio is ready.", width - 4)
    add_clipped(log, 2, 2, "The clock is now running: one week passes every 30 seconds.", width - 4)

    add_clipped(screen, height - 1, 0, " Q quit ".ljust(width), width, curses.color_pair(1))


def run(screen: curses.window) -> None:
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_GREEN, -1)

    screen.nodelay(True)
    clock = GameClock()
    previous_time = time.monotonic()

    while True:
        now = time.monotonic()
        clock.update(now - previous_time)
        previous_time = now

        draw_overlay(screen, clock)
        screen.refresh()

        key = screen.getch()
        if key in (ord("q"), ord("Q")):
            break

        time.sleep(0.1)


def main() -> None:
    curses.wrapper(run)


if __name__ == "__main__":
    main()
