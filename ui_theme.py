"""Terminal theme and glyph portability layer.

This module sits below ``ui_common`` in the layering and fixes the two
ways a terminal can make the game unreadable:

- Colors: :func:`init_theme` picks the palette once at startup. Modern
  terminals keep their own palette, so a themed emulator (Ghostty with
  Tokyo Night, Windows Terminal) renders with its full native saturation.
  Legacy consoles (old Windows cmd) get a forced high-contrast scheme on
  an explicit dark background so light defaults cannot wash the bars out
  or hide text, and ``--theme tokyo`` forces the built-in Tokyo Night
  palette everywhere for a uniform look across machines.
- Glyphs: meters, charts, and the title logo are drawn through the
  ``GLYPHS`` table, which holds Unicode block characters where the
  terminal supports them and plain ASCII otherwise. Legacy Windows
  consoles misrender block characters, so ASCII is the default there
  unless a modern terminal (Windows Terminal) is detected. Override with
  ``--ascii`` / ``--unicode`` or the ``GAMEDEV_ASCII`` environment
  variable.

Pair ids mirror the ``COLOR_*`` semantics documented in ``ui_common``.
"""

from __future__ import annotations

import curses
import locale
import os


PAIR_CHROME = 1
PAIR_BORDER = 2
PAIR_ACCENT = 3
PAIR_GOOD = 4
PAIR_BAD = 5
PAIR_DIM = 6
PAIR_BASE = 7
COLOR_CHROME_TEXT = 24

TOKYO_NIGHT = {
    "bg": (0x1A, 0x1B, 0x26),
    "fg": (0xC0, 0xCA, 0xF5),
    "chrome": (0x7D, 0xCF, 0xFF),
    "border": (0x7D, 0xCF, 0xFF),
    "accent": (0xE0, 0xAF, 0x68),
    "good": (0x9E, 0xCE, 0x6A),
    "bad": (0xF7, 0x76, 0x8E),
    "dim": (0x3B, 0x42, 0x61),
}

UNICODE_GLYPHS = {
    "full": "█",
    "shade": "░",
    "hline": "─",
    "spark": "▁▂▃▄▅▆▇█",
    "pop_steps": "▁▂▃▄▅",
    "up": "▲",
    "down": "▼",
    "logo": "█",
}

ASCII_GLYPHS = {
    "full": "#",
    "shade": ".",
    "hline": "-",
    "spark": " .:-=+*#",
    "pop_steps": ".,:=#",
    "up": "^",
    "down": "v",
    "logo": "#",
}

GLYPHS = dict(UNICODE_GLYPHS)


def glyph(name: str) -> str:
    """The current mode's version of a named glyph (see ``GLYPHS``)."""
    return GLYPHS[name]


def _supports_unicode() -> bool:
    if os.name == "nt":
        # Legacy conhost misrenders block glyphs; Windows Terminal and
        # other modern emulators handle them fine.
        return "WT_SESSION" in os.environ or bool(os.environ.get("TERM_PROGRAM"))
    encoding = locale.getpreferredencoding(False) or "ascii"
    try:
        "".join(UNICODE_GLYPHS.values()).encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def configure_glyphs(ascii_mode: bool | None = None) -> None:
    """Pick the glyph set: explicit argument > env override > auto-detect."""
    if ascii_mode is None:
        override = os.environ.get("GAMEDEV_ASCII", "").strip().lower()
        if override in ("1", "true", "yes", "on"):
            ascii_mode = True
        elif override in ("0", "false", "no", "off"):
            ascii_mode = False
        else:
            ascii_mode = not _supports_unicode()
    GLYPHS.clear()
    GLYPHS.update(ASCII_GLYPHS if ascii_mode else UNICODE_GLYPHS)


def _scale(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(round(channel * 1000 / 255) for channel in rgb)


def _init_native_pairs() -> bool:
    """Inherit the terminal's own palette — the vivid pre-theme look on
    themed emulators (Ghostty, Windows Terminal). False if the console
    cannot do transparent backgrounds."""
    try:
        chrome_text = curses.COLOR_BLACK
        # Windows' standard palette maps COLOR_BLACK to dark gray. Reserve a
        # color slot for true black so controls remain readable on light bars.
        if os.name == "nt" and curses.can_change_color() and curses.COLORS > COLOR_CHROME_TEXT:
            curses.init_color(COLOR_CHROME_TEXT, 0, 0, 0)
            chrome_text = COLOR_CHROME_TEXT
        curses.init_pair(PAIR_CHROME, chrome_text, curses.COLOR_CYAN)
        curses.init_pair(PAIR_BORDER, curses.COLOR_CYAN, -1)
        curses.init_pair(PAIR_ACCENT, curses.COLOR_YELLOW, -1)
        curses.init_pair(PAIR_GOOD, curses.COLOR_GREEN, -1)
        curses.init_pair(PAIR_BAD, curses.COLOR_RED, -1)
        curses.init_pair(PAIR_DIM, curses.COLOR_BLACK, curses.COLOR_BLACK)
    except curses.error:
        return False
    return True


def _init_fallback_pairs() -> None:
    """High-contrast 16-color scheme on an explicit dark background for
    legacy consoles (old Windows cmd) whose palette is unreadable."""
    curses.init_pair(PAIR_CHROME, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(PAIR_BORDER, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(PAIR_ACCENT, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(PAIR_GOOD, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(PAIR_BAD, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(PAIR_DIM, curses.COLOR_BLACK, curses.COLOR_BLACK)
    curses.init_pair(PAIR_BASE, curses.COLOR_WHITE, curses.COLOR_BLACK)


def _init_tokyo_night_pairs() -> bool:
    """Exact palette via redefinable color slots; False if unsupported."""
    if not curses.can_change_color() or curses.COLORS < 16 + len(TOKYO_NIGHT):
        return False
    try:
        slots = {}
        for index, (name, rgb) in enumerate(TOKYO_NIGHT.items()):
            slot = 16 + index
            curses.init_color(slot, *_scale(rgb))
            slots[name] = slot
        curses.init_pair(PAIR_CHROME, slots["bg"], slots["chrome"])
        curses.init_pair(PAIR_BORDER, slots["border"], slots["bg"])
        curses.init_pair(PAIR_ACCENT, slots["accent"], slots["bg"])
        curses.init_pair(PAIR_GOOD, slots["good"], slots["bg"])
        curses.init_pair(PAIR_BAD, slots["bad"], slots["bg"])
        curses.init_pair(PAIR_DIM, slots["dim"], slots["bg"])
        curses.init_pair(PAIR_BASE, slots["fg"], slots["bg"])
    except curses.error:
        return False
    return True


def _legacy_console() -> bool:
    """Old Windows conhost: fixed palette, poor contrast, mangled glyphs."""
    return os.name == "nt" and "WT_SESSION" not in os.environ and not os.environ.get("TERM_PROGRAM")


def init_theme(screen: curses.window, ascii_mode: bool | None = None, theme: str = "auto") -> None:
    """Register the palette and glyph mode, and theme the window background.

    ``theme="auto"`` keeps the terminal's own palette (most saturated on
    themed emulators) and only forces colors on legacy consoles;
    ``theme="tokyo"`` always forces the built-in Tokyo Night palette.
    """
    configure_glyphs(ascii_mode)
    try:
        curses.use_default_colors()
    except curses.error:
        pass
    if theme == "tokyo" and _init_tokyo_night_pairs():
        screen.bkgd(" ", curses.color_pair(PAIR_BASE))
        return
    if theme != "tokyo" and not _legacy_console() and _init_native_pairs():
        return
    _init_fallback_pairs()
    # Painting the background with the base pair makes every cell use the
    # scheme even where text is drawn with the default attribute, so the
    # console's own default colors never show through.
    screen.bkgd(" ", curses.color_pair(PAIR_BASE))
