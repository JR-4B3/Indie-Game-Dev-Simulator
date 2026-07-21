"""Shared terminal UI primitives for the Indie Studio Game Dev Sim.

This module is the bottom layer of the UI design system. It owns every
primitive the screens are built from so that panels, lists, tables, meters,
and status lines look and behave the same everywhere:

- ``add_text`` / ``draw_box`` / ``make_panel`` are the only ways screens put
  text on a window or create a titled box.
- ``money`` / ``meter`` format the two recurring value types.
- ``list_start`` / ``draw_list`` implement the one shared scrolling
  selection-list idiom (``> `` marker, yellow-bold highlight when the pane
  is active).
- ``game_title`` / ``rating_text`` / ``update_status`` / ``game_recommendation``
  / ``live_games`` / ``promotion_targets`` are pure data-to-text helpers
  shared by several screens.

Nothing here imports from ``simulation``; helpers take duck-typed objects so
the layering stays ``simulation <- ui_common <- ui_chrome <- screens <-
ui_input <- main``.
"""

from __future__ import annotations

import curses


# Color pair semantics used across the whole UI (pairs are registered in
# ``main.run``): 1 = chrome (inverted bar), 2 = borders/dim, 3 = selection
# accent, 4 = positive, 5 = warning.
COLOR_CHROME = 1
COLOR_BORDER = 2
COLOR_ACCENT = 3
COLOR_GOOD = 4
COLOR_BAD = 5


def add_text(window: curses.window, y: int, x: int, text: str, width: int, attr: int = 0) -> None:
    """Draw ``text`` clipped to ``width`` and to the window's right edge."""
    max_y, max_x = window.getmaxyx()
    if width <= 0 or y < 0 or y >= max_y or x < 0 or x >= max_x - 1:
        return
    window.addstr(y, x, text[: min(width, max_x - x - 1)], attr)


def draw_box(window: curses.window, title: str) -> None:
    """Draw the standard titled panel border."""
    height, width = window.getmaxyx()
    if height < 3 or width < 4:
        return
    window.attron(curses.color_pair(COLOR_BORDER))
    window.border()
    window.attroff(curses.color_pair(COLOR_BORDER))
    add_text(window, 0, 2, f" {title} ", width - 4, curses.color_pair(COLOR_ACCENT) | curses.A_BOLD)


def make_panel(screen: curses.window, y: int, x: int, height: int, width: int, title: str) -> curses.window:
    """Create a boxed sub-window; the standard content area starts at (1, 2)."""
    panel = screen.derwin(height, width, y, x)
    draw_box(panel, title)
    return panel


def selected_attr(active: bool) -> int:
    """Highlight attribute for the selected row of the active pane."""
    return curses.color_pair(COLOR_ACCENT) | curses.A_BOLD if active else 0


def selection_marker(selected: bool) -> str:
    return "> " if selected else "  "


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:.2f}m"
    if value >= 100_000:
        return f"{sign}${value / 1_000:.0f}k"
    return f"{sign}${value:,.0f}"


def meter(value: float, maximum: float, width: int) -> str:
    filled = max(0, min(width, round(width * value / max(1, maximum))))
    return "█" * filled + "░" * (width - filled)


def range_meter(low: float, high: float, maximum: float, width: int) -> str:
    """Uncertainty bar: the [low, high] interval is filled on a 0..maximum scale."""
    start = max(0, min(width, round(width * low / max(1, maximum))))
    end = max(start, min(width, round(width * high / max(1, maximum))))
    return "░" * start + "█" * (end - start) + "░" * (width - end)


def update_status(game) -> str:
    return f"v{game.version} | {game.updates_released} update{'s' if game.updates_released != 1 else ''} shipped"


def game_title(game, width: int | None = None) -> str:
    suffix = f" v{game.version}"
    if width is None:
        return game.title + suffix
    return game.title[: max(1, width - len(suffix))] + suffix


def rating_text(game) -> str:
    return "n/a" if game.release_date == "Historical" else str(game.score)


def game_recommendation(game) -> tuple[str, int]:
    if game.score < 45:
        return "Low rating: updates have weak returns. Invest in the next game instead.", 5
    if game.monthly_players < 10 and game.score >= 70:
        return "Dormant but well rated: a Content update can revive former owners.", 4
    if game.monthly_players < 10:
        return "Very few monthly players: promotion or updates are financially risky.", 5
    if game.hype < 15 and game.score >= 65:
        return "Good reception, low hype: promotion or New content has strong potential.", 4
    if game.monthly_players > 1_000:
        return "Healthy audience: regular patches can protect retention.", 4
    return "Stable niche audience: compare update cost and estimated duration before committing.", 3


def list_start(selected: int, item_count: int, visible: int) -> int:
    """First visible index that keeps ``selected`` centered in ``visible`` rows."""
    return max(0, min(selected - visible // 2, item_count - visible))


def draw_selectable_list(
    window: curses.window,
    rows: list[tuple[str, int]],
    selected: int,
    active: bool,
    y: int = 1,
    x: int = 2,
    width: int | None = None,
    visible: int | None = None,
    scroll: bool = True,
    highlight_wins: bool = True,
) -> None:
    """Render the one shared selection list used by every page.

    ``rows`` are ``(text, attr)`` pairs without the selection marker; the
    marker column and highlight are added here so every list behaves the
    same: ``> `` marks the selected row, accent+bold highlights it when the
    pane is active, and long lists scroll around the selection.

    With ``highlight_wins`` (default) a selected row takes the highlight;
    otherwise a non-zero row ``attr`` (e.g. locked/owned state colors) takes
    precedence over the highlight. With ``scroll=False`` the list truncates
    instead of scrolling (used by panes that size themselves to content).
    """
    _, win_width = window.getmaxyx()
    if width is None:
        width = win_width - 2 * x
    if visible is None:
        visible = len(rows)
    start = list_start(selected, len(rows), visible) if scroll else 0
    for offset, (text, row_attr) in enumerate(rows[start : start + visible]):
        index = start + offset
        is_selected = index == selected
        if highlight_wins:
            attr = selected_attr(active and is_selected) or row_attr
        else:
            attr = row_attr or selected_attr(active and is_selected)
        add_text(window, y + offset, x, f"{selection_marker(is_selected)}{text}", width, attr)


def draw_list(window: curses.window, items: list[str], selected: int, active: bool) -> None:
    """Plain-string variant of :func:`draw_selectable_list` filling a panel."""
    height, width = window.getmaxyx()
    rows = [(item, 0) for item in items]
    draw_selectable_list(window, rows, selected, active, width=width - 4, visible=max(1, height - 2))


def draw_chart_rows(window: curses.window, chart: list, selected_game_id: int, y: int, inner: int, count: int) -> int:
    """Top-chart rows with unit bars; the selected game is highlighted and any
    studio title is dimmed. Returns the first free row below the block."""
    bar_width = 7
    peak_units = max((entry.weekly_units for entry in chart), default=1) or 1
    studio_width = max(10, min(20, inner - 40))
    title_width = max(10, inner - studio_width - bar_width - 14)
    for index, entry in enumerate(chart[:count], 1):
        filled = max(1, round(bar_width * entry.weekly_units / peak_units))
        if selected_game_id and entry.game_id == selected_game_id:
            entry_attr = curses.color_pair(COLOR_ACCENT) | curses.A_BOLD
        elif entry.game_id:
            entry_attr = curses.color_pair(COLOR_BORDER)
        else:
            entry_attr = 0
        studio_name = "YOU" if entry.game_id else entry.studio_name
        add_text(window, y + index - 1, 2, f"{index:>2} {entry.title[:title_width]:<{title_width}} {studio_name[:studio_width]:<{studio_width}} {'█' * filled:<{bar_width}} {entry.weekly_units:>7,}", inner, entry_attr)
    return y + min(len(chart), count)


def draw_lines(window: curses.window, lines: list[tuple[str, int]], y: int, x: int, width: int) -> None:
    """Render a stack of ``(text, attr)`` lines; the standard detail-block idiom."""
    for offset, (text, attr) in enumerate(lines):
        add_text(window, y + offset, x, text, width, attr)


def section(title: str) -> tuple[str, int]:
    """A bold section heading line for use inside :func:`draw_lines` blocks."""
    return (title, curses.A_BOLD)


def cell(text: object, width: int, align: str = "<") -> str:
    """One table cell: truncate to ``width`` then pad using ``align``."""
    clipped = str(text)[:width]
    return f"{clipped:>{width}}" if align == ">" else f"{clipped:<{width}}"


def table_row(*cells: tuple[object, int] | tuple[object, int, str]) -> str:
    """Join cells into one single-spaced table line (header or body)."""
    parts = []
    for spec in cells:
        text, width = spec[0], spec[1]
        align = spec[2] if len(spec) > 2 else "<"
        parts.append(cell(text, width, align))
    return " ".join(parts)


def queue_header(title: str, active: int, waiting: int, suffix: str = "") -> str:
    """The uniform queue status line: ``TITLE (total) | a active | w waiting``."""
    extra = f" | {suffix}" if suffix else ""
    return f"{title} ({active + waiting}) | {active} active | {waiting} waiting{extra}"


def wrap_text(text: str, width: int) -> list[str]:
    """Word-wrap ``text`` to ``width`` columns (no mid-word breaks)."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def live_games(state) -> list:
    """Released games, newest first, as shown in every catalogue list."""
    return list(reversed(state.studio.catalog))


def catalogue_entries(state) -> list:
    """Catalogue rows for the Game page: the in-development project (id 0)
    first, then released games newest first."""
    entries = []
    if state.studio.current_project:
        entries.append((0, state.studio.current_project))
    entries.extend((game.game_id, game) for game in live_games(state))
    return entries


def promotion_targets(state) -> list[tuple[int, str, float, str]]:
    targets = []
    if state.studio.current_project:
        project = state.studio.current_project
        targets.append((0, project.title, project.hype, "In development"))
    for game in live_games(state):
        targets.append((game.game_id, game_title(game), game.hype, f"rating {rating_text(game)} | {game.monthly_players:,} monthly | {update_status(game)}"))
    return targets
