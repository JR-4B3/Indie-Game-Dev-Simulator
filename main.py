from __future__ import annotations

import argparse
import curses
import json
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from game_data import GENRES, GENRE_PROFILES, GOOD_MATCHES, PLATFORMS, PLATFORM_PROFILES, TOPICS


SECONDS_PER_WEEK = 30.0
START_DATE = date(1976, 1, 1)
TIME_SPEEDS = [0.0, 1.0, 1.5, 2.0, 3.0]
TIME_LABELS = ["||", ">", ">>", ">>>", ">>>>"]
DEFAULT_TIME_SPEED_INDEX = 1
DEFAULT_SAVE_FILE = "gamedev_save.json"
STATS = ["Gameplay", "Graphics", "Audio", "Tech"]
NAVIGATION_KEYS = {curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT, curses.KEY_RIGHT}
PROJECT_LENGTH_WEEKS = 8
STUDIO_LEVEL_XP = [0, 100, 250, 500, 900, 1400]
EMPLOYEE_CANDIDATES = [
    ("Alex Code", 7, 2, 2, 8, 900),
    ("Mira Paint", 3, 9, 4, 3, 950),
    ("Sam Beats", 2, 3, 9, 4, 850),
    ("Rin Design", 9, 4, 3, 2, 1_000),
    ("Jo General", 5, 5, 5, 5, 800),
]


@dataclass
class GameClock:
    current_date: date = START_DATE
    week: int = 1
    _elapsed_seconds: float = 0.0

    def update(self, delta_seconds: float) -> int:
        self._elapsed_seconds += delta_seconds
        weeks_passed = 0

        while self._elapsed_seconds >= SECONDS_PER_WEEK:
            self._elapsed_seconds -= SECONDS_PER_WEEK
            self.week += 1
            self.current_date += timedelta(days=7)
            weeks_passed += 1

        return weeks_passed

    @property
    def week_progress(self) -> float:
        return self._elapsed_seconds / SECONDS_PER_WEEK


@dataclass
class Project:
    genre: str
    topic: str
    platform: str
    platform_category: str
    platform_user_base: int
    focus_percentages: tuple[int, int, int, int]
    started_week: int
    weeks_done: int = 0
    gameplay: int = 0
    graphics: int = 0
    audio: int = 0
    tech: int = 0


@dataclass
class Employee:
    name: str
    gameplay: int
    graphics: int
    audio: int
    tech: int
    wage: int

    def stat_value(self, stat: str) -> int:
        return getattr(self, stat.lower())


@dataclass
class ActiveSale:
    title: str
    press_score: int
    public_score: int
    weeks_left: int
    weekly_cash: int
    weekly_fans: int


@dataclass
class Studio:
    cash: int = 10_000
    fans: int = 0
    reputation: int = 0
    xp: int = 0
    level: int = 1
    released_games: int = 0
    current_project: Project | None = None
    employees: list[Employee] = field(default_factory=list)
    active_sales: list[ActiveSale] = field(default_factory=list)


@dataclass
class GameState:
    clock: GameClock
    studio: Studio
    selected_genre: int = 0
    selected_topic: int = 0
    selected_platform: int = 0
    selected_focus: int = 0
    topic_columns: int = 1
    selected_employee: int = 0
    selecting_topics: bool = False
    selecting_platforms: bool = False
    selecting_focus: bool = False
    focus_percentages: list[int] = field(default_factory=lambda: [25, 25, 25, 25])
    modal: str = "main"
    time_speed_index: int = DEFAULT_TIME_SPEED_INDEX
    resume_time_speed_index: int = DEFAULT_TIME_SPEED_INDEX
    save_path: str = DEFAULT_SAVE_FILE
    logs: list[str] | None = None

    def __post_init__(self) -> None:
        if not self.studio.employees:
            self.studio.employees.append(Employee("You", 4, 3, 3, 4, 0))
        if self.logs is None:
            self.logs = [
                "1976 begins. Your tiny studio is ready.",
                "Press N to create games or E to hire employees.",
            ]

    def add_log(self, message: str) -> None:
        assert self.logs is not None
        self.logs.insert(0, message)
        del self.logs[60:]


def project_to_data(project: Project | None) -> dict | None:
    if project is None:
        return None

    return {
        "genre": project.genre,
        "topic": project.topic,
        "platform": project.platform,
        "platform_category": project.platform_category,
        "platform_user_base": project.platform_user_base,
        "focus_percentages": list(project.focus_percentages),
        "started_week": project.started_week,
        "weeks_done": project.weeks_done,
        "gameplay": project.gameplay,
        "graphics": project.graphics,
        "audio": project.audio,
        "tech": project.tech,
    }


def project_from_data(data: dict | None) -> Project | None:
    if data is None:
        return None

    data = dict(data)
    data["focus_percentages"] = tuple(data["focus_percentages"])
    return Project(**data)


def state_to_data(state: GameState) -> dict:
    return {
        "clock": {
            "current_date": state.clock.current_date.isoformat(),
            "week": state.clock.week,
            "elapsed_seconds": state.clock._elapsed_seconds,
        },
        "studio": {
            "cash": state.studio.cash,
            "fans": state.studio.fans,
            "reputation": state.studio.reputation,
            "xp": state.studio.xp,
            "level": state.studio.level,
            "released_games": state.studio.released_games,
            "current_project": project_to_data(state.studio.current_project),
            "employees": [employee.__dict__ for employee in state.studio.employees],
            "active_sales": [sale.__dict__ for sale in state.studio.active_sales],
        },
        "selected_genre": state.selected_genre,
        "selected_topic": state.selected_topic,
        "selected_platform": state.selected_platform,
        "selected_focus": state.selected_focus,
        "focus_percentages": state.focus_percentages,
        "time_speed_index": state.time_speed_index,
        "resume_time_speed_index": state.resume_time_speed_index,
        "logs": state.logs or [],
    }


def state_from_data(data: dict, save_path: str) -> GameState:
    clock_data = data["clock"]
    studio_data = data["studio"]
    clock = GameClock(
        current_date=date.fromisoformat(clock_data["current_date"]),
        week=clock_data["week"],
        _elapsed_seconds=clock_data.get("elapsed_seconds", 0.0),
    )
    studio = Studio(
        cash=studio_data["cash"],
        fans=studio_data["fans"],
        reputation=studio_data["reputation"],
        xp=studio_data["xp"],
        level=studio_data["level"],
        released_games=studio_data["released_games"],
        current_project=project_from_data(studio_data.get("current_project")),
        employees=[Employee(**employee) for employee in studio_data.get("employees", [])],
        active_sales=[ActiveSale(**sale) for sale in studio_data.get("active_sales", [])],
    )
    return GameState(
        clock=clock,
        studio=studio,
        selected_genre=data.get("selected_genre", 0),
        selected_topic=data.get("selected_topic", 0),
        selected_platform=data.get("selected_platform", 0),
        selected_focus=data.get("selected_focus", 0),
        focus_percentages=data.get("focus_percentages", [25, 25, 25, 25]),
        time_speed_index=data.get("time_speed_index", DEFAULT_TIME_SPEED_INDEX),
        resume_time_speed_index=data.get("resume_time_speed_index", DEFAULT_TIME_SPEED_INDEX),
        save_path=save_path,
        logs=data.get("logs", []),
    )


def save_game(state: GameState) -> None:
    Path(state.save_path).write_text(json.dumps(state_to_data(state), indent=2), encoding="utf-8")


def load_game(save_path: str) -> GameState:
    data = json.loads(Path(save_path).read_text(encoding="utf-8"))
    return state_from_data(data, save_path)


def format_date(value: date) -> str:
    return value.strftime("%d %b %Y")


def xp_for_next_level(studio: Studio) -> int | None:
    if studio.level >= len(STUDIO_LEVEL_XP):
        return None

    return STUDIO_LEVEL_XP[studio.level]


def update_studio_level(studio: Studio) -> bool:
    leveled_up = False

    while studio.level < len(STUDIO_LEVEL_XP) and studio.xp >= STUDIO_LEVEL_XP[studio.level]:
        studio.level += 1
        leveled_up = True

    return leveled_up


def year_month(value: date) -> tuple[int, int]:
    return value.year, value.month


def is_platform_active(platform: tuple[str, tuple[int, int], tuple[int, int] | None, int, str], current_date: date) -> bool:
    current = year_month(current_date)
    release = platform[1]
    support_end = platform[2]
    return release <= current and (support_end is None or current <= support_end)


def available_platforms(state: GameState) -> list[tuple[str, tuple[int, int], tuple[int, int] | None, int, str]]:
    return [platform for platform in PLATFORMS if is_platform_active(platform, state.clock.current_date)]


def selected_platform_info(state: GameState) -> tuple[str, tuple[int, int], tuple[int, int] | None, int, str] | None:
    platforms = available_platforms(state)
    if not platforms:
        return None

    return platforms[min(state.selected_platform, len(platforms) - 1)]


def estimate_platform_users(platform: tuple[str, tuple[int, int], tuple[int, int] | None, int, str], current_date: date) -> int:
    name, release, support_end, dev_cost, category = platform
    age_months = max(0, (current_date.year - release[0]) * 12 + current_date.month - release[1])
    if support_end is None:
        lifespan_months = 96
    else:
        lifespan_months = max(12, (support_end[0] - release[0]) * 12 + support_end[1] - release[1])

    maturity = min(1.0, (age_months + 4) / max(8, lifespan_months // 2))
    decline = 1.0 if support_end is None else max(0.35, 1.0 - max(0, age_months - lifespan_months * 0.7) / max(1, lifespan_months))
    category_base = {"PC": 180_000, "Console": 220_000, "Handheld": 150_000, "Arcade": 90_000, "Mobile": 260_000}[category]
    cost_reach = max(0.8, min(3.2, dev_cost / 12_000))
    long_support = 1.15 if support_end is None or lifespan_months >= 96 else 1.0
    return max(25_000, int(category_base * cost_reach * maturity * decline * long_support))


def platform_fit(genre: str, topic: str, platform_category: str) -> tuple[int, str]:
    profile = PLATFORM_PROFILES[platform_category]
    genre_bonus = 12 if genre in profile["genres"] else -4
    topic_bonus = 8 if topic in profile["topics"] else 0
    genre_targets = set(GENRE_PROFILES[genre]["targets"])
    audience_overlap = genre_targets & set(profile["audiences"])
    audience_bonus = min(8, len(audience_overlap) * 4)
    score = genre_bonus + topic_bonus + audience_bonus
    label = "strong" if score >= 20 else "good" if score >= 12 else "niche" if score >= 4 else "weak"
    return score, label


def focus_fit(genre: str, focus_percentages: tuple[int, int, int, int]) -> tuple[int, str]:
    ideal = GENRE_PROFILES[genre]["priorities"]
    distance = sum(abs(focus_percentages[index] - ideal[index]) for index in range(len(STATS)))
    score = max(-12, 16 - distance // 4)
    label = "excellent" if score >= 12 else "good" if score >= 6 else "risky" if score >= 0 else "bad"
    return score, label


def normalize_focus(values: list[int]) -> list[int]:
    total = sum(values)
    if total == 100:
        return values

    values[-1] += 100 - total
    return values


def adjust_focus(state: GameState, delta: int) -> None:
    index = state.selected_focus
    values = state.focus_percentages
    if delta > 0:
        donor = max((candidate for candidate in range(len(values)) if candidate != index), key=lambda candidate: values[candidate])
        amount = min(delta, values[donor], 100 - values[index])
        values[index] += amount
        values[donor] -= amount
    elif delta < 0:
        amount = min(-delta, values[index])
        receiver = (index + 1) % len(values)
        values[index] -= amount
        values[receiver] += amount

    state.focus_percentages = normalize_focus(values)


def reset_new_game_steps(state: GameState) -> None:
    state.selecting_topics = False
    state.selecting_platforms = False
    state.selecting_focus = False


def move_topic_selection(state: GameState, delta_columns: int, delta_rows: int) -> None:
    columns = max(1, state.topic_columns)
    current_column = state.selected_topic % columns
    target = state.selected_topic + delta_columns + delta_rows * columns

    if delta_columns < 0 and current_column == 0:
        return
    if delta_columns > 0 and current_column >= columns - 1:
        return
    if 0 <= target < len(TOPICS):
        state.selected_topic = target


def review_game(project: Project, studio: Studio) -> tuple[int, int, int, int, int, int, int, int]:
    match_bonus = 26 if project.topic in GOOD_MATCHES[project.genre] else 4
    experience_bonus = min(18, studio.level * 3 + studio.released_games)
    topic_variety = (TOPICS.index(project.topic) * 7 + GENRES.index(project.genre) * 11) % 13
    priorities = project.focus_percentages
    weighted_quality = (
        project.gameplay * priorities[0]
        + project.graphics * priorities[1]
        + project.audio * priorities[2]
        + project.tech * priorities[3]
    ) // 100
    quality_bonus = min(35, weighted_quality // 2)
    platform_bonus, _ = platform_fit(project.genre, project.topic, project.platform_category)
    focus_bonus, _ = focus_fit(project.genre, project.focus_percentages)
    user_bonus = min(16, project.platform_user_base // 120_000)
    press_score = max(15, min(100, 16 + match_bonus + experience_bonus + topic_variety + quality_bonus + platform_bonus // 2 + focus_bonus))
    public_score = max(10, min(100, press_score + platform_bonus + user_bonus + (studio.fans // 25) - 10))

    launch_fans = max(1, public_score // 8)
    reputation = max(1, press_score // 12)
    xp = 40 + press_score
    sale_weeks = 2 + press_score // 18 + public_score // 25
    market_scale = max(0.8, min(4.5, project.platform_user_base / 180_000))
    weekly_cash = int((250 + press_score * 12 + public_score * 10) * market_scale)
    weekly_fans = max(1, public_score // 12)
    return press_score, public_score, sale_weeks, weekly_cash, weekly_fans, launch_fans, reputation, xp


def start_project(state: GameState) -> None:
    if state.studio.current_project is not None:
        state.add_log("A game is already in development.")
        return

    platform = selected_platform_info(state)
    if platform is None:
        state.add_log("No active platforms are available for development.")
        return

    platform_name, _, _, cost, platform_category = platform
    if state.studio.cash < cost:
        state.add_log(f"Not enough cash to develop for {platform_name}.")
        return

    genre = GENRES[state.selected_genre]
    topic = TOPICS[state.selected_topic]
    user_base = estimate_platform_users(platform, state.clock.current_date)
    state.studio.cash -= cost
    state.studio.current_project = Project(
        genre=genre,
        topic=topic,
        platform=platform_name,
        platform_category=platform_category,
        platform_user_base=user_base,
        focus_percentages=tuple(state.focus_percentages),
        started_week=state.clock.week,
    )
    state.modal = "main"
    reset_new_game_steps(state)
    state.add_log(f"Started a {topic} {genre} game for {platform_name}. Budget spent: ${cost:,}.")


def hire_employee(state: GameState) -> None:
    name, gameplay, graphics, audio, tech, wage = EMPLOYEE_CANDIDATES[state.selected_employee]
    if any(employee.name == name for employee in state.studio.employees):
        state.add_log(f"{name} already works here.")
        return

    signing_cost = wage
    if state.studio.cash < signing_cost:
        state.add_log(f"Not enough cash to hire {name}.")
        return

    state.studio.cash -= signing_cost
    state.studio.employees.append(Employee(name, gameplay, graphics, audio, tech, wage))
    state.modal = "main"
    state.add_log(f"Hired {name}. Monthly wage: ${wage:,}.")


def finish_project(state: GameState) -> None:
    project = state.studio.current_project
    if project is None:
        return

    press_score, public_score, sale_weeks, weekly_cash, weekly_fans, fans, reputation, xp = review_game(project, state.studio)
    state.studio.fans += fans
    state.studio.reputation += reputation
    state.studio.xp += xp
    state.studio.released_games += 1
    state.studio.active_sales.append(
        ActiveSale(f"{project.topic} {project.genre} ({project.platform})", press_score, public_score, sale_weeks, weekly_cash, weekly_fans)
    )
    state.studio.current_project = None

    state.add_log(f"Released {project.topic} {project.genre} on {project.platform}: press {press_score}/100, public {public_score}/100.")
    state.add_log(f"Focus fit was {focus_fit(project.genre, project.focus_percentages)[1]}: GP {project.focus_percentages[0]}%, GR {project.focus_percentages[1]}%, AU {project.focus_percentages[2]}%, TE {project.focus_percentages[3]}%.")
    state.add_log(f"Sales forecast: ${weekly_cash:,}/week and +{weekly_fans} fans/week for {sale_weeks} weeks.")
    state.add_log(f"Launch buzz: +{fans} fans, +{reputation} rep, +{xp} studio XP.")
    if update_studio_level(state.studio):
        state.add_log(f"Studio reached level {state.studio.level}.")


def add_employee_points(project: Project, employees: list[Employee]) -> None:
    project.gameplay += sum(employee.gameplay for employee in employees)
    project.graphics += sum(employee.graphics for employee in employees)
    project.audio += sum(employee.audio for employee in employees)
    project.tech += sum(employee.tech for employee in employees)


def process_sales(state: GameState) -> None:
    finished_sales = []
    for sale in state.studio.active_sales:
        state.studio.cash += sale.weekly_cash
        state.studio.fans += sale.weekly_fans
        sale.weeks_left -= 1
        state.add_log(f"{sale.title} sales: +${sale.weekly_cash:,}, +{sale.weekly_fans} fans.")
        sale.weekly_cash = max(100, int(sale.weekly_cash * 0.78))
        sale.weekly_fans = max(0, int(sale.weekly_fans * 0.7))
        if sale.weeks_left <= 0:
            finished_sales.append(sale)

    for sale in finished_sales:
        state.studio.active_sales.remove(sale)
        state.add_log(f"{sale.title} left the market.")


def pay_wages(state: GameState) -> None:
    total_wages = sum(employee.wage for employee in state.studio.employees)
    if total_wages <= 0:
        return

    state.studio.cash -= total_wages
    state.add_log(f"Paid monthly wages: ${total_wages:,}.")


def advance_game(state: GameState, weeks_passed: int) -> None:
    for _ in range(weeks_passed):
        process_sales(state)
        if state.clock.week % 4 == 1:
            pay_wages(state)

        project = state.studio.current_project
        if project is None:
            continue

        add_employee_points(project, state.studio.employees)
        project.weeks_done += 1
        if project.weeks_done >= PROJECT_LENGTH_WEEKS:
            finish_project(state)
        else:
            state.add_log(f"Development progress: week {project.weeks_done}/{PROJECT_LENGTH_WEEKS}.")


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


def draw_overlay(screen: curses.window, state: GameState) -> None:
    height, width = screen.getmaxyx()
    clock = state.clock
    studio_state = state.studio
    screen.erase()

    if height < 22 or width < 55:
        add_clipped(screen, 0, 0, "Terminal too small. Resize or press Q to quit.", width)
        return

    header = f" GameDev Tycoon Terminal | {format_date(clock.current_date)} | Week {clock.week} "
    add_clipped(screen, 0, 0, header.ljust(width), width, curses.color_pair(1) | curses.A_BOLD)

    progress_width = max(10, width - 31)
    filled = int(progress_width * clock.week_progress)
    progress = "#" * filled + "-" * (progress_width - filled)
    speed = f"Time: {TIME_LABELS[state.time_speed_index]} {TIME_SPEEDS[state.time_speed_index]:g}x"
    if state.modal == "new_game":
        mode = "New Game"
    elif state.modal == "hire":
        mode = "Hiring"
    else:
        mode = "Main"
    add_clipped(screen, 1, 0, f" Next week: [{progress}] | {speed} | Screen: {mode}", width, curses.color_pair(4))

    left_width = max(22, width // 2)
    right_width = width - left_width - 1


    studio = screen.derwin(7, left_width, 3, 0)
    draw_box(studio, 7, left_width, "Studio")
    next_xp = xp_for_next_level(studio_state)
    xp_text = "max" if next_xp is None else f"{studio_state.xp}/{next_xp}"
    add_clipped(studio, 1, 2, f"Cash:       ${studio_state.cash:,}", left_width - 4)
    add_clipped(studio, 2, 2, f"Level:      {studio_state.level}  XP: {xp_text}", left_width - 4)
    add_clipped(studio, 3, 2, f"Reputation: {studio_state.reputation}", left_width - 4)
    add_clipped(studio, 4, 2, f"Fans:       {studio_state.fans}", left_width - 4)
    add_clipped(studio, 5, 2, f"Released:   {studio_state.released_games}", left_width - 4, curses.color_pair(4))

    project = screen.derwin(7, right_width, 3, left_width + 1)
    draw_box(project, 7, right_width, "Current Game")
    current_project = studio_state.current_project
    if current_project is None:
        genre = GENRES[state.selected_genre]
        topic = TOPICS[state.selected_topic]
        platform = selected_platform_info(state)
        match = "good fit" if topic in GOOD_MATCHES[genre] else "risky fit"
        platform_text = "No active platform"
        if platform is not None:
            fit = platform_fit(genre, topic, platform[4])[1]
            users = estimate_platform_users(platform, clock.current_date)
            platform_text = f"{platform[0]} ({platform[4]}, {fit}, {users:,} users)"
        add_clipped(project, 1, 2, "No project in development", right_width - 4)
        add_clipped(project, 2, 2, f"Next idea: {topic} {genre}", right_width - 4)
        add_clipped(project, 3, 2, f"Combo:    {match}", right_width - 4)
        add_clipped(project, 4, 2, f"Platform: {platform_text}", right_width - 4)
        add_clipped(project, 5, 2, "Press N to open new game", right_width - 4, curses.color_pair(4))
    else:
        bar_width = max(5, right_width - 18)
        filled_project = int(bar_width * current_project.weeks_done / PROJECT_LENGTH_WEEKS)
        project_bar = "#" * filled_project + "-" * (bar_width - filled_project)
        add_clipped(project, 1, 2, f"{current_project.topic} {current_project.genre} on {current_project.platform}", right_width - 4)
        add_clipped(project, 2, 2, f"Progress: [{project_bar}]", right_width - 4)
        add_clipped(project, 3, 2, f"Week {current_project.weeks_done}/{PROJECT_LENGTH_WEEKS}", right_width - 4)
        add_clipped(project, 4, 2, format_project_stats(current_project), right_width - 4)
        add_clipped(project, 5, 2, "Employees add stat points weekly", right_width - 4, curses.color_pair(4))

    content_bottom = draw_middle_content(screen, state, width, height)

    if state.modal != "new_game":
        log_height = height - content_bottom - 2
        log = screen.derwin(log_height, width, content_bottom, 0)
        visible_logs = max(0, log_height - 2)
        logs = state.logs or []
        shown_logs = logs[:visible_logs]
        draw_box(log, log_height, width, "Activity")
        for row, message in enumerate(shown_logs, start=1):
            add_clipped(log, row, 2, message, width - 4)

    if state.modal == "new_game":
        controls = " Enter next/start | Backspace back | Arrows choose/adjust | S save | Q quit "
    elif state.modal == "hire":
        controls = " Enter hire selected | Backspace back | Up/Down choose | S save | Q quit "
    else:
        controls = " N new game | E employees | S save | Right faster | Left slower | Space pause/resume | Q quit "
    add_clipped(screen, height - 1, 0, controls.ljust(width), width, curses.color_pair(1))


def format_project_stats(project: Project) -> str:
    return f"GP {project.gameplay} | GR {project.graphics} | AU {project.audio} | TE {project.tech}"


def draw_middle_content(screen: curses.window, state: GameState, width: int, height: int) -> int:
    if state.modal == "new_game":
        draw_new_game_screen(screen, state, width, 10, height - 11)
        return height - 1

    if state.modal == "hire":
        draw_hiring_screen(screen, state, width, 10)
        return 17

    draw_main_middle(screen, state, width, 10)
    return 17


def draw_main_middle(screen: curses.window, state: GameState, width: int, y: int) -> None:
    panel_height = 7
    left_width = max(28, width // 2)
    right_width = width - left_width - 1
    employees = screen.derwin(panel_height, left_width, y, 0)
    sales = screen.derwin(panel_height, right_width, y, left_width + 1)
    draw_box(employees, panel_height, left_width, "Employees")
    draw_box(sales, panel_height, right_width, "Sales")

    total_wage = sum(employee.wage for employee in state.studio.employees)
    add_clipped(employees, 1, 2, f"Monthly wages: ${total_wage:,}", left_width - 4)
    for row, employee in enumerate(state.studio.employees[:4], start=2):
        text = f"{employee.name}: Gp{employee.gameplay} Gr{employee.graphics} Au{employee.audio} Te{employee.tech}"
        add_clipped(employees, row, 2, text, left_width - 4)

    if not state.studio.active_sales:
        add_clipped(sales, 1, 2, "No games currently selling", right_width - 4)
    for row, sale in enumerate(state.studio.active_sales[:5], start=1):
        text = f"{sale.title}: {sale.weeks_left}w, ${sale.weekly_cash:,}/w, +{sale.weekly_fans} fans/w"
        add_clipped(sales, row, 2, text, right_width - 4)


def draw_new_game_screen(screen: curses.window, state: GameState, width: int, y: int, available_height: int) -> None:
    picker_height = max(8, available_height - 5)
    genre_width = max(18, min(28, width // 4))
    platform_width = max(18, min(34, width // 3))
    topics_width = width - genre_width - platform_width - 2
    genre_picker = screen.derwin(picker_height, genre_width, y, 0)
    topic_picker = screen.derwin(picker_height, topics_width, y, genre_width + 1)
    platform_picker = screen.derwin(picker_height, platform_width, y, genre_width + topics_width + 2)
    active_column = 3 if state.selecting_focus else 2 if state.selecting_platforms else 1 if state.selecting_topics else 0
    platforms = available_platforms(state)
    platform_names = [f"{item[0]} ${item[3]:,}" for item in platforms]
    state.topic_columns = topic_grid_columns(topics_width)

    draw_picker(genre_picker, picker_height, genre_width, "Genres", GENRES, state.selected_genre, active_column == 0)
    draw_topic_picker(topic_picker, picker_height, topics_width, TOPICS, state.selected_topic, active_column == 1)
    draw_picker(platform_picker, picker_height, platform_width, "Platforms", platform_names, state.selected_platform, active_column == 2)

    genre = GENRES[state.selected_genre]
    focus_y = y + picker_height
    focus_height = max(3, available_height - picker_height)
    focus_panel = screen.derwin(focus_height, width, focus_y, 0)
    draw_box(focus_panel, focus_height, width, "Focus Percentages")
    focus_text = " | ".join(f"{STATS[index]} {state.focus_percentages[index]}%" for index in range(len(STATS)))
    add_clipped(focus_panel, 1, 2, f"{genre}: {focus_text}", width - 4, curses.color_pair(3) | curses.A_BOLD if active_column == 3 else 0)
    if focus_height > 3:
        selected = state.selected_focus
        add_clipped(focus_panel, 2, 2, f"Adjusting: {STATS[selected]} ({state.focus_percentages[selected]}%). Total stays 100%.", width - 4, curses.color_pair(4) if active_column == 3 else 0)


def draw_picker(window: curses.window, height: int, width: int, title: str, items: list[str], selected: int, active: bool) -> None:
    draw_box(window, height, width, title)
    if not items:
        add_clipped(window, 1, 2, "None available", width - 4)
        return

    visible = height - 2
    start = max(0, min(selected - visible // 2, len(items) - visible))
    for row, item in enumerate(items[start : start + visible], start=1):
        index = start + row - 1
        marker = ">" if index == selected else " "
        attr = curses.color_pair(3) | curses.A_BOLD if index == selected and active else 0
        add_clipped(window, row, 2, f"{marker} {item}", width - 4, attr)


def topic_grid_columns(width: int) -> int:
    return max(1, (width - 4) // 18)


def draw_topic_picker(window: curses.window, height: int, width: int, items: list[str], selected: int, active: bool) -> None:
    draw_box(window, height, width, "Topics")
    if not items:
        add_clipped(window, 1, 2, "None available", width - 4)
        return

    rows = height - 2
    columns = topic_grid_columns(width)
    page_size = rows * columns
    page_start = (selected // page_size) * page_size
    column_width = max(12, (width - 4) // columns)

    for offset, item in enumerate(items[page_start : page_start + page_size]):
        index = page_start + offset
        row = offset // columns + 1
        column = offset % columns
        x = 2 + column * column_width
        marker = ">" if index == selected else " "
        attr = curses.color_pair(3) | curses.A_BOLD if index == selected and active else 0
        add_clipped(window, row, x, f"{marker} {item}", column_width - 1, attr)

    page = page_start // page_size + 1
    pages = (len(items) + page_size - 1) // page_size
    add_clipped(window, 0, max(2, width - 14), f" {page}/{pages} ", 12, curses.color_pair(4))


def draw_hiring_screen(screen: curses.window, state: GameState, width: int, y: int) -> None:
    panel_height = 7
    panel = screen.derwin(panel_height, width, y, 0)
    draw_box(panel, panel_height, width, "Hire Employees")

    for row, candidate in enumerate(EMPLOYEE_CANDIDATES[: panel_height - 2], start=1):
        name, gameplay, graphics, audio, tech, wage = candidate
        marker = ">" if row - 1 == state.selected_employee else " "
        attr = curses.color_pair(3) | curses.A_BOLD if row - 1 == state.selected_employee else 0
        text = f"{marker} {name}: Gameplay {gameplay}, Graphics {graphics}, Audio {audio}, Tech {tech}, ${wage:,}/month"
        add_clipped(panel, row, 2, text, width - 4, attr)


def handle_key(state: GameState, key: int) -> bool:
    if key in (ord("q"), ord("Q")):
        return False

    if key == ord(" "):
        toggle_pause(state)
        return True

    if key in (ord("s"), ord("S")):
        try:
            save_game(state)
        except OSError as error:
            state.add_log(f"Save failed: {error}.")
        else:
            state.add_log(f"Saved game to {state.save_path}.")
        return True

    if key == 27:
        state.modal = "main"
        return True

    if state.modal == "main":
        if key in (ord("n"), ord("N")):
            if state.studio.current_project is None:
                state.modal = "new_game"
                reset_new_game_steps(state)
            else:
                state.add_log("Finish the current game before starting another.")
        elif key in (ord("e"), ord("E")):
            state.modal = "hire"
        elif key == curses.KEY_RIGHT:
            increase_time_speed(state)
        elif key == curses.KEY_LEFT:
            decrease_time_speed(state)
        return True

    if state.modal == "new_game":
        return handle_new_game_key(state, key)

    if state.modal == "hire":
        return handle_hiring_key(state, key)

    return True


def handle_new_game_key(state: GameState, key: int) -> bool:
    if key in (10, 13, curses.KEY_ENTER):
        if state.selecting_focus:
            start_project(state)
        elif state.selecting_platforms:
            state.selecting_platforms = False
            state.selecting_focus = True
        elif state.selecting_topics:
            state.selecting_topics = False
            state.selecting_platforms = True
        else:
            state.selecting_topics = True
    elif key in (8, 127, curses.KEY_BACKSPACE):
        if state.selecting_focus:
            state.selecting_focus = False
            state.selecting_platforms = True
        elif state.selecting_platforms:
            state.selecting_platforms = False
            state.selecting_topics = True
        elif state.selecting_topics:
            state.selecting_topics = False
        else:
            state.modal = "main"
    elif key == curses.KEY_UP:
        if state.selecting_focus:
            state.selected_focus = (state.selected_focus - 1) % len(STATS)
        elif state.selecting_platforms:
            platforms = available_platforms(state)
            if platforms:
                state.selected_platform = (state.selected_platform - 1) % len(platforms)
        elif state.selecting_topics:
            move_topic_selection(state, 0, -1)
        else:
            state.selected_genre = (state.selected_genre - 1) % len(GENRES)
    elif key == curses.KEY_DOWN:
        if state.selecting_focus:
            state.selected_focus = (state.selected_focus + 1) % len(STATS)
        elif state.selecting_platforms:
            platforms = available_platforms(state)
            if platforms:
                state.selected_platform = (state.selected_platform + 1) % len(platforms)
        elif state.selecting_topics:
            move_topic_selection(state, 0, 1)
        else:
            state.selected_genre = (state.selected_genre + 1) % len(GENRES)
    elif key == curses.KEY_LEFT:
        if state.selecting_focus:
            adjust_focus(state, -5)
        elif state.selecting_topics:
            move_topic_selection(state, -1, 0)
    elif key == curses.KEY_RIGHT:
        if state.selecting_focus:
            adjust_focus(state, 5)
        elif state.selecting_topics:
            move_topic_selection(state, 1, 0)

    return True


def handle_hiring_key(state: GameState, key: int) -> bool:
    if key in (10, 13, curses.KEY_ENTER):
        hire_employee(state)
    elif key in (8, 127, curses.KEY_BACKSPACE):
        state.modal = "main"
    elif key == curses.KEY_UP:
        state.selected_employee = (state.selected_employee - 1) % len(EMPLOYEE_CANDIDATES)
    elif key == curses.KEY_DOWN:
        state.selected_employee = (state.selected_employee + 1) % len(EMPLOYEE_CANDIDATES)

    return True


def toggle_pause(state: GameState) -> None:
    if state.time_speed_index == 0:
        state.time_speed_index = max(DEFAULT_TIME_SPEED_INDEX, state.resume_time_speed_index)
        return

    state.resume_time_speed_index = state.time_speed_index
    state.time_speed_index = 0


def increase_time_speed(state: GameState) -> None:
    if state.time_speed_index == 0:
        state.time_speed_index = max(DEFAULT_TIME_SPEED_INDEX, state.resume_time_speed_index)
    else:
        state.time_speed_index = min(len(TIME_SPEEDS) - 1, state.time_speed_index + 1)
    state.resume_time_speed_index = max(DEFAULT_TIME_SPEED_INDEX, state.time_speed_index)


def decrease_time_speed(state: GameState) -> None:
    if state.time_speed_index == 0:
        state.time_speed_index = max(DEFAULT_TIME_SPEED_INDEX, state.resume_time_speed_index)
    else:
        state.time_speed_index = max(DEFAULT_TIME_SPEED_INDEX, state.time_speed_index - 1)
    state.resume_time_speed_index = max(DEFAULT_TIME_SPEED_INDEX, state.time_speed_index)


def run(screen: curses.window, load_save: bool, save_path: str) -> None:
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_GREEN, -1)

    screen.nodelay(True)
    screen.keypad(True)
    if load_save:
        try:
            state = load_game(save_path)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            state = GameState(clock=GameClock(), studio=Studio(), save_path=save_path)
            state.add_log(f"Could not load {save_path}: {error}.")
        else:
            state.add_log(f"Loaded game from {save_path}.")
    else:
        state = GameState(clock=GameClock(), studio=Studio(), save_path=save_path)
    previous_time = time.monotonic()
    running = True

    while running:
        now = time.monotonic()
        weeks_passed = state.clock.update((now - previous_time) * TIME_SPEEDS[state.time_speed_index])
        previous_time = now
        advance_game(state, weeks_passed)

        draw_overlay(screen, state)
        screen.refresh()

        key = screen.getch()
        while key != -1:
            running = handle_key(state, key)
            if not running:
                break
            if key in NAVIGATION_KEYS:
                curses.flushinp()
                break
            key = screen.getch()

        time.sleep(0.03)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GameDev Tycoon Terminal.")
    parser.add_argument("--load", action="store_true", help="load the saved game before starting")
    parser.add_argument("--save-file", default=DEFAULT_SAVE_FILE, help=f"save file path (default: {DEFAULT_SAVE_FILE})")
    args = parser.parse_args()
    curses.wrapper(run, args.load, args.save_file)


if __name__ == "__main__":
    main()
