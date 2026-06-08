from __future__ import annotations

import curses
import time
from dataclasses import dataclass, field
from datetime import date, timedelta


SECONDS_PER_WEEK = 30.0
START_DATE = date(1970, 1, 1)
TIME_SPEEDS = [0.0, 1.0, 1.5, 2.0]
TIME_LABELS = ["||", ">", ">>", ">>>"]
DEFAULT_TIME_SPEED_INDEX = 1
STATS = ["Gameplay", "Graphics", "Audio", "Tech"]
GENRES = ["Action", "RPG", "Puzzle", "Racing", "Strategy"]
TOPICS = [
    "Zombies",
    "Vampire",
    "Medieval",
    "Space",
    "Cyberpunk",
    "Pirates",
    "Detective",
    "Fantasy",
    "Sports",
    "Robots",
    "War",
    "Western",
    "Ninjas",
    "Aliens",
    "Superheroes",
    "Dinosaurs",
    "Farming",
    "School",
    "Cooking",
    "Underwater",
]
GOOD_MATCHES = {
    "Action": {"Zombies", "Vampire", "War", "Ninjas", "Aliens", "Superheroes", "Robots"},
    "RPG": {"Medieval", "Fantasy", "Cyberpunk", "Pirates", "Vampire", "Western", "Space"},
    "Puzzle": {"Detective", "Cooking", "School", "Underwater", "Robots", "Farming"},
    "Racing": {"Sports", "Cyberpunk", "Space", "Dinosaurs", "Western", "Pirates"},
    "Strategy": {"War", "Medieval", "Space", "Robots", "Pirates", "Farming", "Aliens"},
}
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
    selected_employee: int = 0
    selecting_topics: bool = False
    modal: str = "main"
    time_speed_index: int = DEFAULT_TIME_SPEED_INDEX
    resume_time_speed_index: int = DEFAULT_TIME_SPEED_INDEX
    logs: list[str] | None = None

    def __post_init__(self) -> None:
        if not self.studio.employees:
            self.studio.employees.append(Employee("You", 4, 3, 3, 4, 0))
        if self.logs is None:
            self.logs = [
                "1970 begins. Your tiny studio is ready.",
                "Press N to create games or E to hire employees.",
            ]

    def add_log(self, message: str) -> None:
        assert self.logs is not None
        self.logs.insert(0, message)
        del self.logs[60:]


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


def review_game(project: Project, studio: Studio) -> tuple[int, int, int, int, int, int, int, int]:
    match_bonus = 22 if project.topic in GOOD_MATCHES[project.genre] else 6
    experience_bonus = min(18, studio.level * 3 + studio.released_games)
    topic_variety = (TOPICS.index(project.topic) * 7 + GENRES.index(project.genre) * 11) % 13
    stat_average = (project.gameplay + project.graphics + project.audio + project.tech) // 4
    quality_bonus = min(35, stat_average // 2)
    press_score = max(15, min(100, 20 + match_bonus + experience_bonus + topic_variety + quality_bonus))
    public_score = max(10, min(100, press_score + (studio.fans // 20) - 5))

    launch_fans = max(1, public_score // 8)
    reputation = max(1, press_score // 12)
    xp = 40 + press_score
    sale_weeks = 2 + press_score // 18 + public_score // 25
    weekly_cash = 250 + press_score * 12 + public_score * 10
    weekly_fans = max(1, public_score // 12)
    return press_score, public_score, sale_weeks, weekly_cash, weekly_fans, launch_fans, reputation, xp


def start_project(state: GameState) -> None:
    if state.studio.current_project is not None:
        state.add_log("A game is already in development.")
        return

    cost = 1_500
    if state.studio.cash < cost:
        state.add_log("Not enough cash to start a new game.")
        return

    genre = GENRES[state.selected_genre]
    topic = TOPICS[state.selected_topic]
    state.studio.cash -= cost
    state.studio.current_project = Project(genre=genre, topic=topic, started_week=state.clock.week)
    state.modal = "main"
    state.add_log(f"Started a {topic} {genre} game. Budget spent: ${cost:,}.")


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
        ActiveSale(f"{project.topic} {project.genre}", press_score, public_score, sale_weeks, weekly_cash, weekly_fans)
    )
    state.studio.current_project = None

    state.add_log(f"Released {project.topic} {project.genre}: press {press_score}/100, public {public_score}/100.")
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
        match = "good fit" if topic in GOOD_MATCHES[genre] else "risky fit"
        add_clipped(project, 1, 2, "No project in development", right_width - 4)
        add_clipped(project, 2, 2, f"Next idea: {topic} {genre}", right_width - 4)
        add_clipped(project, 3, 2, f"Combo:    {match}", right_width - 4)
        add_clipped(project, 5, 2, "Press N to open new game", right_width - 4, curses.color_pair(4))
    else:
        bar_width = max(5, right_width - 18)
        filled_project = int(bar_width * current_project.weeks_done / PROJECT_LENGTH_WEEKS)
        project_bar = "#" * filled_project + "-" * (bar_width - filled_project)
        add_clipped(project, 1, 2, f"{current_project.topic} {current_project.genre}", right_width - 4)
        add_clipped(project, 2, 2, f"Progress: [{project_bar}]", right_width - 4)
        add_clipped(project, 3, 2, f"Week {current_project.weeks_done}/{PROJECT_LENGTH_WEEKS}", right_width - 4)
        add_clipped(project, 4, 2, format_project_stats(current_project), right_width - 4)
        add_clipped(project, 5, 2, "Employees add stat points weekly", right_width - 4, curses.color_pair(4))

    content_bottom = draw_middle_content(screen, state, width)

    log_height = height - content_bottom - 2
    log = screen.derwin(log_height, width, content_bottom, 0)
    visible_logs = max(0, log_height - 2)
    logs = state.logs or []
    shown_logs = logs[:visible_logs]
    draw_box(log, log_height, width, "Activity")
    for row, message in enumerate(shown_logs, start=1):
        add_clipped(log, row, 2, message, width - 4)

    if state.modal == "new_game":
        controls = " Enter select/start | Backspace back | Up/Down choose | Q quit "
    elif state.modal == "hire":
        controls = " Enter hire selected | Backspace back | Up/Down choose | Q quit "
    else:
        controls = " N new game | E employees | Right faster | Left slower | Space pause/resume | Q quit "
    add_clipped(screen, height - 1, 0, controls.ljust(width), width, curses.color_pair(1))


def format_project_stats(project: Project) -> str:
    return f"GP {project.gameplay} | GR {project.graphics} | AU {project.audio} | TE {project.tech}"


def draw_middle_content(screen: curses.window, state: GameState, width: int) -> int:
    if state.modal == "new_game":
        draw_new_game_screen(screen, state, width, 10)
        return 17

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


def draw_new_game_screen(screen: curses.window, state: GameState, width: int, y: int) -> None:
    picker_height = 7
    genre_width = min(24, width // 3)
    topics_width = width - genre_width - 1
    genre_picker = screen.derwin(picker_height, genre_width, y, 0)
    topic_picker = screen.derwin(picker_height, topics_width, y, genre_width + 1)
    draw_box(genre_picker, picker_height, genre_width, "Genres")
    draw_box(topic_picker, picker_height, topics_width, "Topics")

    for index, genre in enumerate(GENRES[: picker_height - 2]):
        marker = ">" if index == state.selected_genre else " "
        attr = curses.color_pair(3) | curses.A_BOLD if index == state.selected_genre and not state.selecting_topics else 0
        add_clipped(genre_picker, index + 1, 2, f"{marker} {genre}", genre_width - 4, attr)

    topic_start = max(0, min(state.selected_topic - 2, len(TOPICS) - (picker_height - 2)))
    for row, topic in enumerate(TOPICS[topic_start : topic_start + picker_height - 2], start=1):
        index = topic_start + row - 1
        marker = ">" if index == state.selected_topic else " "
        attr = curses.color_pair(3) | curses.A_BOLD if index == state.selected_topic and state.selecting_topics else 0
        add_clipped(topic_picker, row, 2, f"{marker} {topic}", topics_width - 4, attr)


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

    if key == 27:
        state.modal = "main"
        return True

    if state.modal == "main":
        if key in (ord("n"), ord("N")):
            if state.studio.current_project is None:
                state.modal = "new_game"
                state.selecting_topics = False
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
        if state.selecting_topics:
            start_project(state)
        else:
            state.selecting_topics = True
    elif key in (8, 127, curses.KEY_BACKSPACE):
        if state.selecting_topics:
            state.selecting_topics = False
        else:
            state.modal = "main"
    elif key == curses.KEY_UP:
        if state.selecting_topics:
            state.selected_topic = (state.selected_topic - 1) % len(TOPICS)
        else:
            state.selected_genre = (state.selected_genre - 1) % len(GENRES)
    elif key == curses.KEY_DOWN:
        if state.selecting_topics:
            state.selected_topic = (state.selected_topic + 1) % len(TOPICS)
        else:
            state.selected_genre = (state.selected_genre + 1) % len(GENRES)

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


def run(screen: curses.window) -> None:
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_GREEN, -1)

    screen.nodelay(True)
    screen.keypad(True)
    state = GameState(clock=GameClock(), studio=Studio())
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
        if key != -1:
            running = handle_key(state, key)

        time.sleep(0.1)


def main() -> None:
    curses.wrapper(run)


if __name__ == "__main__":
    main()
