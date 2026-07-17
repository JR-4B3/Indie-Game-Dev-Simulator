from __future__ import annotations

import json
import math
import random
import re
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path

from game_data import GENRES, GENRE_PROFILES, GOOD_MATCHES, TOPICS


SAVE_VERSION = 2
START_DATE = date.today()
SECONDS_PER_WEEK = 20.0
SKILLS = ("Design", "Art", "Audio", "Code")
TIME_SPEEDS = (0.0, 1.0, 2.0, 4.0, 8.0)
TIME_LABELS = ("||", "> 1x", ">> 2x", ">>> 4x", ">>>> 8x")

CHANNELS = (
    {"name": "Steam", "category": "PC", "fee": 100, "cut": 0.30, "reach": 1.00},
    {"name": "itch.io", "category": "PC", "fee": 0, "cut": 0.10, "reach": 0.16},
    {"name": "Epic Games Store", "category": "PC", "fee": 100, "cut": 0.12, "reach": 0.28},
    {"name": "App Store", "category": "Mobile", "fee": 99, "cut": 0.30, "reach": 0.65},
    {"name": "Google Play", "category": "Mobile", "fee": 25, "cut": 0.30, "reach": 0.78},
    {"name": "PlayStation 5", "category": "Console", "fee": 2_500, "cut": 0.30, "reach": 0.54},
    {"name": "Xbox Series", "category": "Console", "fee": 1_800, "cut": 0.30, "reach": 0.39},
    {"name": "Switch 2", "category": "Handheld", "fee": 2_200, "cut": 0.30, "reach": 0.48},
)

SCOPES = (
    {"name": "Micro", "work": 900, "setup": 1_800, "price": 9.99, "risk": 0},
    {"name": "Small", "work": 1_900, "setup": 5_500, "price": 14.99, "risk": 4},
    {"name": "Ambitious", "work": 3_600, "setup": 14_000, "price": 24.99, "risk": 10},
)

MARKETING = (
    {"name": "Organic", "cost": 0, "boost": 0},
    {"name": "Community", "cost": 2_000, "boost": 120},
    {"name": "Targeted", "cost": 4_000, "boost": 260},
    {"name": "Creator push", "cost": 8_000, "boost": 520},
    {"name": "Launch campaign", "cost": 15_000, "boost": 1_050},
    {"name": "Showcase launch", "cost": 32_000, "boost": 2_000},
)

PROMOTIONS = (
    {"key": "social", "name": "Social media push", "cost": 1_200, "weeks": 1, "hype": 8, "team": 0.02, "rep": 0, "effect": "Small targeted awareness"},
    {"key": "press", "name": "Press outreach", "cost": 3_500, "weeks": 2, "hype": 16, "team": 0.04, "rep": 2, "effect": "Reviews, previews, and interviews"},
    {"key": "creator", "name": "Creator key campaign", "cost": 7_500, "weeks": 2, "hype": 25, "team": 0.05, "rep": 5, "effect": "Keys sent to relevant creators"},
    {"key": "streamer", "name": "Streamer placement", "cost": 15_000, "weeks": 2, "hype": 42, "team": 0.03, "rep": 12, "effect": "Paid sponsored broadcast"},
    {"key": "festival", "name": "Digital festival demo", "cost": 10_000, "weeks": 3, "hype": 34, "team": 0.12, "rep": 8, "effect": "Demo preparation consumes team time"},
    {"key": "event", "name": "Attend a games event", "cost": 24_000, "weeks": 4, "hype": 58, "team": 0.18, "rep": 18, "effect": "Booth, travel, demo, and staff time"},
    {"key": "showcase", "name": "Premium showcase slot", "cost": 55_000, "weeks": 4, "hype": 105, "team": 0.10, "rep": 35, "effect": "Large placement for established studios"},
)

UPDATE_FOCUSES = (
    {"name": "Bug fixes", "skill": "Code", "hype": 0.7, "players": 0.8},
    {"name": "Balance pass", "skill": "Design", "hype": 0.9, "players": 1.0},
    {"name": "Visual refresh", "skill": "Art", "hype": 1.1, "players": 1.0},
    {"name": "Audio pack", "skill": "Audio", "hype": 1.0, "players": 0.9},
    {"name": "New content", "skill": "Generalist", "hype": 1.35, "players": 1.4},
)

UPDATE_SIZES = (
    {"name": "Patch", "work": 70, "cost": 250, "hype": 7, "sales": 2},
    {"name": "Content", "work": 170, "cost": 900, "hype": 18, "sales": 4},
    {"name": "Expansion", "work": 380, "cost": 3_500, "hype": 42, "sales": 9},
)

LEGACY_MARKETING_NAMES = {
    "Campaign": "Launch campaign",
}

UPGRADES = (
    {"key": "hardware", "name": "Current workstations", "cost": 7_500, "monthly": 120, "effect": "+10% production"},
    {"key": "tools", "name": "Professional toolchain", "cost": 11_000, "monthly": 350, "effect": "+8% quality"},
    {"key": "qa", "name": "QA device library", "cost": 8_000, "monthly": 180, "effect": "-25% defects"},
    {"key": "coworking", "name": "Coworking studio", "cost": 3_500, "monthly": 1_450, "effect": "+5 morale/month"},
    {"key": "health", "name": "Health plan", "cost": 1_500, "monthly": 650, "per_employee": 280, "effect": "less burnout"},
    {"key": "analytics", "name": "Store analytics", "cost": 5_000, "monthly": 190, "effect": "+12% sales tail"},
)

FIRST_NAMES = (
    "Avery", "Maya", "Noah", "Priya", "Mateo", "Lena", "Sam", "Iris", "Owen", "Zara",
    "Kai", "Nia", "Theo", "June", "Emi", "Leo", "Rin", "Amara", "Jonah", "Sofia",
)
LAST_NAMES = (
    "Chen", "Patel", "Garcia", "Kim", "Nguyen", "Smith", "Okafor", "Silva", "Khan", "Miller",
    "Ito", "Brown", "Rossi", "Martin", "Wilson", "Lopez", "Singh", "Davis", "Anders", "Taylor",
)
ROLE_PROFILES = {
    "Game Designer": (78, 42, 28, 48),
    "Programmer": (46, 24, 18, 82),
    "2D/3D Artist": (42, 84, 30, 28),
    "Audio Designer": (38, 34, 86, 28),
    "Generalist": (58, 58, 52, 58),
    "Producer": (68, 38, 30, 52),
}
TRAITS = {
    "Methodical": "fewer defects",
    "Fast learner": "gains skill faster",
    "Collaborative": "team morale",
    "Night owl": "more output, more fatigue",
    "Perfectionist": "quality over speed",
    "Pragmatic": "steady production",
}


@dataclass
class GameClock:
    current_date: date = START_DATE
    week: int = 1
    elapsed_seconds: float = 0.0

    def update(self, delta_seconds: float) -> int:
        self.elapsed_seconds += delta_seconds
        weeks = 0
        while self.elapsed_seconds >= SECONDS_PER_WEEK:
            self.elapsed_seconds -= SECONDS_PER_WEEK
            self.current_date += timedelta(days=7)
            self.week += 1
            weeks += 1
        return weeks

    @property
    def progress(self) -> float:
        return self.elapsed_seconds / SECONDS_PER_WEEK


@dataclass
class Employee:
    employee_id: int
    name: str
    role: str
    design: int
    art: int
    audio: int
    code: int
    annual_salary: int
    morale: float = 72.0
    fatigue: float = 8.0
    experience: int = 0
    trait: str = "Pragmatic"
    weeks_employed: int = 0
    founder: bool = False

    @property
    def skills(self) -> tuple[int, int, int, int]:
        return self.design, self.art, self.audio, self.code

    @property
    def monthly_salary(self) -> int:
        return round(self.annual_salary / 12)


@dataclass
class Project:
    title: str
    genre: str
    topic: str
    channel: str
    category: str
    platform_cut: float
    reach: float
    scope: str
    price: float
    marketing_name: str
    marketing_budget: int
    focus: tuple[int, int, int, int]
    total_work: float
    work_done: float = 0.0
    quality_points: float = 0.0
    defects: float = 0.0
    weeks: int = 0
    planned_weeks: int = 0
    cash_cost: int = 0
    sequel_of: int | None = None
    generation: int = 1
    hype: float = 0.0
    production_cost: float = 0.0
    labor_cost: float = 0.0
    marketing_cost: float = 0.0
    cost_history_complete: bool = False

    @property
    def progress(self) -> float:
        return min(1.0, self.work_done / self.total_work)

    @property
    def phase(self) -> str:
        progress = self.progress
        if progress < 0.12:
            return "Prototype"
        if progress < 0.30:
            return "Pre-production"
        if progress < 0.72:
            return "Production"
        if progress < 0.90:
            return "Alpha / content lock"
        return "Beta / release prep"


@dataclass
class ActiveSale:
    title: str
    channel: str
    score: int
    price: float
    platform_cut: float
    refund_rate: float
    weekly_units: int
    weeks_left: int
    units_sold: int = 0
    gross_revenue: float = 0.0
    net_revenue: float = 0.0
    game_id: int = 0
    genre: str = ""
    evergreen_units: int = 1


@dataclass
class ReleasedGame:
    game_id: int
    title: str
    genre: str
    topic: str
    channel: str
    score: int
    release_date: str
    sequel_of: int | None = None
    generation: int = 1
    units_sold: int = 0
    net_revenue: float = 0.0
    hype: float = 0.0
    auto_updates: bool = False
    update_progress: float = 0.0
    updates_released: int = 0
    update_focus: str = "Bug fixes"
    update_size: str = "Patch"
    active_players: float = 0.0
    monthly_players: int = 0
    peak_monthly_players: int = 0
    production_cost: float = 0.0
    labor_cost: float = 0.0
    marketing_cost: float = 0.0
    post_launch_cost: float = 0.0
    cost_history_complete: bool = False


@dataclass
class Promotion:
    promotion_id: int
    name: str
    game_id: int
    target_title: str
    weeks_left: int
    total_weeks: int
    hype_total: float
    team_share: float


@dataclass
class Contract:
    title: str
    weeks_left: int
    payout: int
    contract_id: int = 0
    client: str = "Legacy client"
    focus: str = "Generalist"
    difficulty: int = 1
    required_work: float = 0.0
    work_done: float = 0.0
    reputation_required: int = 0
    auto_accepted: bool = False


@dataclass
class LedgerMonth:
    month: str
    revenue: int
    expenses: int
    net: int
    categories: dict[str, int] = field(default_factory=dict)
    revenue_categories: dict[str, int] = field(default_factory=dict)


@dataclass
class Studio:
    cash: float = 75_000.0
    followers: int = 40
    reputation: float = 0.0
    released_games: int = 0
    lifetime_revenue: float = 0.0
    lifetime_expenses: float = 0.0
    team: list[Employee] = field(default_factory=list)
    applicants: list[Employee] = field(default_factory=list)
    current_project: Project | None = None
    active_sales: list[ActiveSale] = field(default_factory=list)
    catalog: list[ReleasedGame] = field(default_factory=list)
    genre_fans: dict[str, int] = field(default_factory=dict)
    topic_fans: dict[str, int] = field(default_factory=dict)
    contract: Contract | None = None
    contract_offers: list[Contract] = field(default_factory=list)
    contract_queue: list[Contract] = field(default_factory=list)
    auto_contracts: bool = False
    contractor_reputation: float = 0.0
    contracts_completed: int = 0
    contracts_failed: int = 0
    legacy_auto_jobs_cancelled: int = 0
    active_promotions: list[Promotion] = field(default_factory=list)
    upgrades: list[str] = field(default_factory=list)
    ledger: list[LedgerMonth] = field(default_factory=list)
    period_revenue: float = 0.0
    period_revenue_categories: dict[str, float] = field(default_factory=dict)
    period_expenses: float = 0.0
    period_expense_categories: dict[str, float] = field(default_factory=dict)
    tax_reserve: float = 0.0
    accounting_month: str = ""
    next_employee_id: int = 2
    next_game_id: int = 1
    next_contract_id: int = 1
    next_promotion_id: int = 1
    seed: int = 481516
    insolvent_weeks: int = 0
    closed: bool = False


@dataclass
class GameState:
    clock: GameClock = field(default_factory=GameClock)
    studio: Studio = field(default_factory=Studio)
    selected_genre: int = 0
    selected_topic: int = 0
    selected_channel: int = 0
    selected_scope: int = 0
    selected_marketing: int = 0
    selected_focus: int = 0
    focus: list[int] = field(default_factory=lambda: [30, 25, 15, 30])
    selected_employee: int = 0
    selected_roster: int = 0
    selected_upgrade: int = 0
    selected_contract: int = 0
    selected_game: int = 0
    selected_promotion: int = 0
    selected_promotion_target: int = 0
    marketing_tab: int = 0
    modal: str = "main"
    new_game_step: int = 0
    team_tab: int = 0
    analysis_view: int = 0
    selected_stat: int = 0
    selected_sequel_choice: int = 0
    draft_title: str = ""
    title_roll: int = 0
    naming_game: bool = False
    sequel_game_id: int | None = None
    time_speed_index: int = 1
    resume_speed_index: int = 1
    save_path: str = "gamedev_save.json"
    logs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.studio.team:
            self.studio.team.append(
                Employee(1, "You", "Founder / Generalist", 58, 48, 38, 62, 36_000, founder=True)
            )
        if not self.studio.accounting_month:
            self.studio.accounting_month = self.clock.current_date.strftime("%Y-%m")
        if not self.studio.applicants:
            refresh_applicants(self)
        if not self.studio.contract_offers:
            refresh_contract_offers(self, announce=False)
        if not self.draft_title:
            refresh_draft_title(self)
        if self.studio.legacy_auto_jobs_cancelled:
            self.log(f"Removed {self.studio.legacy_auto_jobs_cancelled} legacy auto-accepted queued contract(s) because Auto Contracts is OFF.")
            self.studio.legacy_auto_jobs_cancelled = 0
        if not self.logs:
            self.logs = [
                f"{self.clock.current_date:%d %b %Y}: you open a bootstrapped indie studio with $75,000.",
                "Cash is runway. Payroll, software, insurance, tax, refunds, and store cuts are real.",
                "Start small: N plans a game, J opens the Contract Board, C toggles automatic contracts, and T manages the team (E also works).",
            ]

    def log(self, message: str) -> None:
        self.logs.insert(0, message)
        del self.logs[100:]


def channel_by_name(name: str) -> dict:
    return next(channel for channel in CHANNELS if channel["name"] == name)


def marketing_by_name(name: str) -> dict:
    resolved_name = LEGACY_MARKETING_NAMES.get(name, name)
    return next(marketing for marketing in MARKETING if marketing["name"] == resolved_name)


def scope_by_name(name: str) -> dict:
    return next(scope for scope in SCOPES if scope["name"] == name)


def upgrade_by_key(key: str) -> dict:
    return next(upgrade for upgrade in UPGRADES if upgrade["key"] == key)


def add_revenue(studio: Studio, amount: float, category: str = "Other revenue") -> None:
    studio.cash += amount
    studio.period_revenue += amount
    studio.lifetime_revenue += amount
    studio.period_revenue_categories[category] = studio.period_revenue_categories.get(category, 0.0) + amount


def add_expense(studio: Studio, amount: float, category: str = "Other") -> None:
    if amount <= 0:
        return
    studio.cash -= amount
    studio.period_expenses += amount
    studio.lifetime_expenses += amount
    studio.period_expense_categories[category] = studio.period_expense_categories.get(category, 0.0) + amount


def monthly_cost_breakdown(studio: Studio) -> dict[str, int]:
    salaries = sum(employee.monthly_salary for employee in studio.team)
    payroll_burden = round(sum(employee.monthly_salary for employee in studio.team if not employee.founder) * 0.13)
    costs = {
        "Payroll": salaries,
        "Employer costs": payroll_burden,
        "Operations": 250 + 310 + 85 * len(studio.team) + 150 * len(studio.active_sales),
    }
    for key in studio.upgrades:
        upgrade = upgrade_by_key(key)
        costs["Upgrades"] = costs.get("Upgrades", 0) + upgrade.get("monthly", 0) + upgrade.get("per_employee", 0) * len(studio.team)
    return {category: amount for category, amount in costs.items() if amount}


def monthly_fixed_cost(studio: Studio) -> int:
    return sum(monthly_cost_breakdown(studio).values())


def recommended_team_size(studio: Studio) -> int:
    growth = studio.followers // 250
    growth += studio.released_games // 2
    growth += max(0, int(studio.reputation) // 8)
    growth += int(studio.lifetime_revenue // 100_000)
    return max(1, min(25, 1 + growth))


def applicant_pool_size(studio: Studio) -> int:
    growth = studio.followers // 100 + studio.released_games // 2 + max(0, int(studio.reputation) // 5)
    return min(18, 6 + growth)


def expense_breakdown(studio: Studio, months: int = 12) -> dict[str, int]:
    totals: dict[str, int] = {}
    for entry in studio.ledger[:months]:
        for category, amount in entry.categories.items():
            totals[category] = totals.get(category, 0) + amount
    for category, amount in studio.period_expense_categories.items():
        totals[category] = totals.get(category, 0) + round(amount)
    return dict(sorted(totals.items(), key=lambda item: item[1], reverse=True))


def revenue_breakdown(studio: Studio, months: int = 12) -> dict[str, int]:
    totals: dict[str, int] = {}
    for entry in studio.ledger[:months]:
        for category, amount in entry.revenue_categories.items():
            totals[category] = totals.get(category, 0) + amount
    for category, amount in studio.period_revenue_categories.items():
        totals[category] = totals.get(category, 0) + round(amount)
    return dict(sorted(totals.items(), key=lambda item: item[1], reverse=True))


def runway_months(studio: Studio) -> float:
    burn = monthly_fixed_cost(studio)
    if studio.cash <= 0:
        return 0.0
    return studio.cash / max(1, burn)


def generate_candidate(studio: Studio, rng: random.Random) -> Employee:
    role = rng.choice(tuple(ROLE_PROFILES))
    base = ROLE_PROFILES[role]
    seniority = rng.choices(("Junior", "Mid-level", "Senior"), weights=(35, 45, 20))[0]
    modifier = {"Junior": -14, "Mid-level": 0, "Senior": 13}[seniority]
    skills = [max(18, min(96, value + modifier + rng.randint(-10, 10))) for value in base]
    annual = round((34_000 + sum(skills) * 115 + (12_000 if seniority == "Senior" else 0)) / 1_000) * 1_000
    employee = Employee(
        studio.next_employee_id,
        f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
        f"{seniority} {role}",
        *skills,
        annual,
        morale=float(rng.randint(62, 86)),
        fatigue=float(rng.randint(2, 12)),
        trait=rng.choice(tuple(TRAITS)),
    )
    studio.next_employee_id += 1
    return employee


def refresh_applicants(state: GameState) -> None:
    stamp = state.clock.current_date.year * 100 + state.clock.current_date.month
    rng = random.Random(state.studio.seed + stamp)
    count = applicant_pool_size(state.studio)
    state.studio.applicants = [generate_candidate(state.studio, rng) for _ in range(count)]
    state.selected_employee = 0


TITLE_NOUNS = {
    "Action": ("Protocol", "Strike", "Vanguard", "Fury"),
    "Adventure": ("Journey", "Chronicle", "Odyssey", "Secret"),
    "Building Game": ("Works", "Architect", "Foundations", "District"),
    "Economic Simulation": ("Ledger", "Markets", "Industries", "Capital"),
    "Fighting Game": ("Clash", "Arena", "Rivals", "Impact"),
    "First-Person Shooter": ("Directive", "Frontline", "Breach", "Zero"),
    "Platformer": ("Leap", "Dash", "Tales", "Quest"),
    "Puzzle Game": ("Paradox", "Patterns", "Logic", "Pieces"),
    "Racing": ("Velocity", "Circuit", "Rush", "Apex"),
    "Role-Playing Game": ("Legends", "Saga", "Realms", "Oath"),
    "Simulation": ("Simulator", "Life", "Systems", "Manager"),
    "Strategy": ("Command", "Tactics", "Dominion", "Doctrine"),
    "Survival Game": ("Aftermath", "Last Light", "Outlands", "Shelter"),
    "Visual Novel": ("Memories", "Letters", "Hearts", "After School"),
}
GENERIC_TITLE_NOUNS = ("Project", "World", "Story", "Legacy")
TITLE_ADJECTIVES = ("Hidden", "Neon", "Last", "Lost", "Infinite", "Quiet", "Iron", "Midnight")


def roman_number(value: int) -> str:
    numerals = ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))
    result = ""
    for amount, numeral in numerals:
        while value >= amount:
            result += numeral
            value -= amount
    return result


def generate_game_title(genre: str, topic: str, seed: int) -> str:
    rng = random.Random(seed)
    noun = rng.choice(TITLE_NOUNS.get(genre, GENERIC_TITLE_NOUNS))
    adjective = rng.choice(TITLE_ADJECTIVES)
    patterns = (
        f"{topic}: {noun}",
        f"{adjective} {topic}",
        f"{topic} {noun}",
        f"The {topic} {noun}",
    )
    return rng.choice(patterns)


def refresh_draft_title(state: GameState) -> None:
    genre = GENRES[state.selected_genre]
    topic = TOPICS[state.selected_topic]
    seed = state.studio.seed + state.clock.week * 101 + state.title_roll * 7919 + state.selected_genre * 31 + state.selected_topic
    state.draft_title = generate_game_title(genre, topic, seed)


def game_by_id(studio: Studio, game_id: int) -> ReleasedGame | None:
    return next((game for game in studio.catalog if game.game_id == game_id), None)


def sale_for_game(studio: Studio, game_id: int) -> ActiveSale | None:
    return next((sale for sale in studio.active_sales if sale.game_id == game_id), None)


def update_focus_by_name(name: str) -> dict:
    return next((focus for focus in UPDATE_FOCUSES if focus["name"] == name), UPDATE_FOCUSES[0])


def update_size_by_name(name: str) -> dict:
    return next((size for size in UPDATE_SIZES if size["name"] == name), UPDATE_SIZES[0])


def update_weekly_output(studio: Studio, game: ReleasedGame) -> float:
    focus = update_focus_by_name(game.update_focus)
    skill_index = {"Design": 0, "Art": 1, "Audio": 2, "Code": 3}.get(focus["skill"])
    output = 0.0
    for employee in studio.team:
        skill = sum(employee.skills) / 4 if skill_index is None else employee.skills[skill_index]
        availability = max(0.35, employee.morale / 100) * max(0.35, 1 - employee.fatigue / 130)
        output += skill * availability * 0.16
    active_updates = max(1, sum(item.auto_updates for item in studio.catalog))
    return max(1.0, output / active_updates)


def estimated_update_weeks(studio: Studio, game: ReleasedGame) -> int:
    size = update_size_by_name(game.update_size)
    remaining = size["work"] * max(0, 1 - game.update_progress / 100)
    return max(1, math.ceil(remaining / update_weekly_output(studio, game)))


def game_total_cost(game: ReleasedGame) -> float:
    return game.production_cost + game.labor_cost + game.marketing_cost + game.post_launch_cost


def game_profit(game: ReleasedGame) -> float:
    return game.net_revenue - game_total_cost(game)


def marketing_team_load(studio: Studio) -> float:
    return min(0.45, sum(promotion.team_share for promotion in studio.active_promotions))


def update_team_load(studio: Studio) -> float:
    return min(0.55, sum(0.12 for game in studio.catalog if game.auto_updates))


def prepare_sequel(state: GameState, game: ReleasedGame) -> None:
    state.selected_genre = GENRES.index(game.genre)
    state.selected_topic = TOPICS.index(game.topic)
    state.selected_channel = next((index for index, channel in enumerate(CHANNELS) if channel["name"] == game.channel), 0)
    state.sequel_game_id = game.game_id
    state.draft_title = f"{game.title} {roman_number(game.generation + 1)}"
    state.modal = "new_game"
    state.new_game_step = 3
    state.selected_focus = 0


def recover_catalog_from_logs(studio: Studio, logs: list[str]) -> None:
    known_titles = {game.title for game in studio.catalog}
    pattern = re.compile(r"^(.+) settled at ([\d,]+) units and \$([\d,]+) studio net\.$")
    for message in reversed(logs):
        match = pattern.match(message)
        if not match:
            continue
        title, units_text, revenue_text = match.groups()
        topic, separator, genre = title.partition(": ")
        if not separator or genre not in GENRES or topic not in TOPICS or title in known_titles:
            continue
        game_id = studio.next_game_id
        studio.next_game_id += 1
        studio.catalog.append(
            ReleasedGame(
                game_id,
                title,
                genre,
                topic,
                "Historical store",
                50,
                "Historical",
                units_sold=int(units_text.replace(",", "")),
                net_revenue=float(revenue_text.replace(",", "")),
            )
        )
        known_titles.add(title)
    if studio.catalog and not studio.genre_fans:
        legacy_fans = max(0, studio.followers - 40)
        per_game = legacy_fans // len(studio.catalog)
        for game in studio.catalog:
            studio.genre_fans[game.genre] = studio.genre_fans.get(game.genre, 0) + per_game
            studio.topic_fans[game.topic] = studio.topic_fans.get(game.topic, 0) + per_game


def recover_contractor_history(studio: Studio, logs: list[str]) -> None:
    if studio.contracts_completed or studio.contractor_reputation:
        return
    completed = sum(message.startswith("Delivered the ") and "client paid $" in message for message in logs)
    if completed:
        studio.contracts_completed = completed
        studio.contractor_reputation = min(30.0, completed * 1.5)


def ensure_catalog_sales(studio: Studio) -> None:
    active_ids = {sale.game_id for sale in studio.active_sales}
    for game in studio.catalog:
        evergreen = max(1, round((max(20, game.score) / 100) ** 4 * 10 + studio.genre_fans.get(game.genre, 0) / 800))
        existing = sale_for_game(studio, game.game_id)
        if existing:
            existing.evergreen_units = max(existing.evergreen_units, evergreen)
            existing.weeks_left = -1
            continue
        if game.game_id not in active_ids:
            studio.active_sales.append(
                ActiveSale(
                    game.title,
                    game.channel,
                    game.score,
                    9.99,
                    0.30,
                    0.10,
                    evergreen,
                    -1,
                    units_sold=game.units_sold,
                    net_revenue=game.net_revenue,
                    game_id=game.game_id,
                    genre=game.genre,
                    evergreen_units=evergreen,
                )
            )


def projected_weekly_output(studio: Studio, focus: list[int] | tuple[int, ...]) -> float:
    output = 0.0
    for employee in studio.team:
        weighted_skill = sum(skill * percent for skill, percent in zip(employee.skills, focus)) / 100
        availability = max(0.35, employee.morale / 100) * max(0.35, 1 - employee.fatigue / 130)
        output += weighted_skill * availability
    if "hardware" in studio.upgrades:
        output *= 1.10
    if studio.contract:
        output *= 0.55
    output *= max(0.70, 1 - 0.04 * len(studio.active_sales))
    output *= max(0.25, 1 - marketing_team_load(studio) - update_team_load(studio))
    return max(1.0, output)


def adjust_focus(state: GameState, delta: int) -> None:
    index = state.selected_focus
    if delta > 0:
        donors = [i for i in range(4) if i != index and state.focus[i] >= delta]
        if donors:
            donor = max(donors, key=lambda i: state.focus[i])
            state.focus[donor] -= delta
            state.focus[index] += delta
    elif delta < 0 and state.focus[index] >= -delta:
        receiver = (index + 1) % 4
        state.focus[index] += delta
        state.focus[receiver] -= delta


def start_project(state: GameState) -> bool:
    studio = state.studio
    if studio.closed or studio.current_project:
        state.log("The studio cannot start another project right now.")
        return False
    channel = CHANNELS[state.selected_channel]
    scope = SCOPES[state.selected_scope]
    marketing = MARKETING[state.selected_marketing]
    cost = scope["setup"] + channel["fee"] + marketing["cost"]
    if studio.cash < cost + monthly_fixed_cost(studio):
        state.log(f"Plan rejected: ${cost:,} setup would leave less than one month of runway.")
        return False
    output = projected_weekly_output(studio, state.focus)
    planned_weeks = max(4, round(scope["work"] / output))
    topic = TOPICS[state.selected_topic]
    genre = GENRES[state.selected_genre]
    previous_game = next((game for game in studio.catalog if game.game_id == state.sequel_game_id), None)
    generation = previous_game.generation + 1 if previous_game else 1
    title = state.draft_title.strip() or generate_game_title(genre, topic, studio.seed + state.clock.week)
    project = Project(
        title=title[:48],
        genre=genre,
        topic=topic,
        channel=channel["name"],
        category=channel["category"],
        platform_cut=channel["cut"],
        reach=channel["reach"],
        scope=scope["name"],
        price=scope["price"],
        marketing_name=marketing["name"],
        marketing_budget=marketing["cost"],
        focus=tuple(state.focus),
        total_work=float(scope["work"]),
        planned_weeks=planned_weeks,
        cash_cost=cost,
        sequel_of=previous_game.game_id if previous_game else None,
        generation=generation,
        hype=5 + marketing["boost"] / 25,
        production_cost=scope["setup"] + channel["fee"],
        marketing_cost=marketing["cost"],
        cost_history_complete=True,
    )
    add_expense(studio, scope["setup"], "Development")
    add_expense(studio, channel["fee"], "Store fees")
    add_expense(studio, marketing["cost"], "Marketing")
    studio.current_project = project
    state.modal = "main"
    state.new_game_step = 0
    state.naming_game = False
    state.sequel_game_id = None
    state.title_roll += 1
    refresh_draft_title(state)
    state.log(f"Greenlit {project.title}, a {scope['name'].lower()} game for {channel['name']}.")
    state.log(f"Paid ${cost:,} in setup and marketing. Current team estimate: {planned_weeks} weeks.")
    return True


def hire_candidate(state: GameState) -> bool:
    studio = state.studio
    if not studio.applicants:
        return False
    candidate = studio.applicants[state.selected_employee]
    recruiting = max(500, round(candidate.monthly_salary * 0.20))
    if studio.cash < recruiting + monthly_fixed_cost(studio) + candidate.monthly_salary:
        state.log(f"Cannot responsibly hire {candidate.name}; there is not enough runway.")
        return False
    add_expense(studio, recruiting, "Recruiting")
    studio.team.append(candidate)
    studio.applicants.pop(state.selected_employee)
    state.selected_employee = min(state.selected_employee, max(0, len(studio.applicants) - 1))
    state.log(f"Hired {candidate.name}, {candidate.role}, at ${candidate.annual_salary:,}/year.")
    return True


def dismiss_employee(state: GameState) -> bool:
    studio = state.studio
    removable = [employee for employee in studio.team if not employee.founder]
    if not removable:
        state.log("There are no employees to dismiss.")
        return False
    employee = removable[min(state.selected_roster, len(removable) - 1)]
    severance = round(employee.annual_salary / 26)
    add_expense(studio, severance, "Severance")
    studio.team.remove(employee)
    state.selected_roster = min(state.selected_roster, max(0, len(removable) - 2))
    for teammate in studio.team:
        teammate.morale = max(0, teammate.morale - 5)
    state.log(f"Let {employee.name} go. Two weeks of severance cost ${severance:,}; team morale fell.")
    return True


def buy_upgrade(state: GameState) -> bool:
    upgrade = UPGRADES[state.selected_upgrade]
    studio = state.studio
    if upgrade["key"] in studio.upgrades:
        state.log(f"{upgrade['name']} is already active.")
        return False
    if studio.cash < upgrade["cost"] + monthly_fixed_cost(studio):
        state.log(f"Cannot buy {upgrade['name']} without risking next month's bills.")
        return False
    add_expense(studio, upgrade["cost"], "Equipment")
    studio.upgrades.append(upgrade["key"])
    state.log(f"Purchased {upgrade['name']} for ${upgrade['cost']:,}; recurring costs also increased.")
    return True


CONTRACT_TYPES = {
    "Design": ("systems design brief", "level-design blockout", "economy rebalance", "prototype design"),
    "Art": ("environment art pack", "UI art production", "character asset batch", "marketing art kit"),
    "Audio": ("soundtrack commission", "sound-effects pass", "dialogue editing", "audio implementation"),
    "Code": ("platform port", "networking prototype", "tools programming", "performance optimization"),
    "Generalist": ("vertical slice", "game-jam prototype", "educational game", "interactive installation"),
}
CONTRACT_CLIENTS = ("Northstar Media", "Copper Finch", "Atlas Learning", "Pixel Harbor", "Redwood Interactive", "Civic Lab", "Moonshot Agency")


def contract_weekly_output(studio: Studio, focus: str) -> float:
    skill_index = {"Design": 0, "Art": 1, "Audio": 2, "Code": 3}.get(focus)
    output = 0.0
    for employee in studio.team:
        skill = sum(employee.skills) / 4 if skill_index is None else employee.skills[skill_index]
        availability = max(0.35, employee.morale / 100) * max(0.35, 1 - employee.fatigue / 130)
        output += skill * availability * 0.55
    if "hardware" in studio.upgrades:
        output *= 1.10
    return max(1.0, output)


def estimated_contract_weeks(studio: Studio, contract: Contract) -> int:
    remaining = max(0, contract.required_work - contract.work_done)
    if contract.required_work <= 0:
        return max(1, contract.weeks_left)
    return max(1, math.ceil(remaining / contract_weekly_output(studio, contract.focus)))


def generate_contract_offer(studio: Studio, rng: random.Random, difficulty: int) -> Contract:
    focus = rng.choice(tuple(CONTRACT_TYPES))
    required_work = 65 + difficulty * 55 + rng.randint(0, 45)
    reputation_required = max(0, (difficulty - 1) * 15)
    rate = 58 + difficulty * 17 + studio.contractor_reputation * 0.35
    payout = round(required_work * rate / 500) * 500
    provisional = Contract(
        rng.choice(CONTRACT_TYPES[focus]),
        1,
        max(3_000, payout),
        studio.next_contract_id,
        rng.choice(CONTRACT_CLIENTS),
        focus,
        difficulty,
        float(required_work),
        reputation_required=reputation_required,
    )
    studio.next_contract_id += 1
    provisional.weeks_left = estimated_contract_weeks(studio, provisional) + 2 + difficulty // 2
    return provisional


def refresh_contract_offers(state: GameState, announce: bool = True) -> None:
    studio = state.studio
    stamp = state.clock.current_date.year * 100 + state.clock.current_date.month
    rng = random.Random(studio.seed + stamp * 17 + 404)
    max_difficulty = min(5, 2 + int(studio.contractor_reputation // 20))
    difficulties = [1] + [rng.randint(1, max_difficulty) for _ in range(5)]
    studio.contract_offers = [generate_contract_offer(studio, rng, difficulty) for difficulty in difficulties]
    state.selected_contract = 0
    if announce:
        state.log(f"The Contract Board refreshed with {len(studio.contract_offers)} offers.")
    if studio.auto_contracts:
        queue_all_contracts(state)


def start_next_contract(state: GameState) -> None:
    studio = state.studio
    if studio.contract is None and studio.contract_queue:
        studio.contract = studio.contract_queue.pop(0)
        state.log(f"Started {studio.contract.client}'s {studio.contract.title} ({studio.contract.focus}).")


def accept_contract_offer(state: GameState, index: int | None = None, automatic: bool = False) -> bool:
    studio = state.studio
    if studio.closed or not studio.contract_offers:
        return False
    selected = state.selected_contract if index is None else index
    selected = min(selected, len(studio.contract_offers) - 1)
    contract = studio.contract_offers[selected]
    if studio.contractor_reputation < contract.reputation_required:
        state.log(f"{contract.client} requires {contract.reputation_required} contractor reputation; you have {studio.contractor_reputation:.0f}.")
        return False
    contract.auto_accepted = automatic
    studio.contract_offers.pop(selected)
    if studio.contract is None:
        studio.contract = contract
        state.log(f"Accepted {contract.client}'s {contract.title}: ${contract.payout:,}, {contract.focus}, due in {contract.weeks_left} weeks.")
    else:
        studio.contract_queue.append(contract)
        state.log(f"Queued {contract.client}'s {contract.title} behind {len(studio.contract_queue)} accepted contract(s).")
    state.selected_contract = min(state.selected_contract, max(0, len(studio.contract_offers) - 1))
    return True


def queue_all_contracts(state: GameState) -> int:
    accepted = 0
    for contract in list(state.studio.contract_offers):
        if state.studio.contractor_reputation >= contract.reputation_required:
            index = state.studio.contract_offers.index(contract)
            if accept_contract_offer(state, index, automatic=True):
                accepted += 1
    if accepted:
        state.log(f"Automatic contracts accepted {accepted} eligible offer(s); deadlines begin when each contract becomes active.")
    return accepted


def toggle_auto_contracts(state: GameState) -> bool:
    studio = state.studio
    studio.auto_contracts = not studio.auto_contracts
    if studio.auto_contracts:
        accepted = queue_all_contracts(state)
        state.log(f"Automatic Contracts ON: {accepted} board offer(s) added to the queue.")
    else:
        cancelled = [contract for contract in studio.contract_queue if contract.auto_accepted]
        studio.contract_queue = [contract for contract in studio.contract_queue if not contract.auto_accepted]
        message = f"Automatic Contracts OFF. Cancelled {len(cancelled)} unstarted automatic contract(s)."
        if studio.contract and studio.contract.auto_accepted:
            message += " The active automatic contract will finish, then automation stops."
        state.log(message)
    return studio.auto_contracts


def accept_contract(state: GameState) -> bool:
    return accept_contract_offer(state)


def platform_fit(project: Project) -> int:
    category_preferences = {
        "PC": {"Strategy", "Real-Time Strategy", "Role-Playing Game", "Simulation", "Economic Simulation", "Building Game", "Adventure", "Visual Novel"},
        "Console": {"Action", "Platformer", "Racing", "Sports Game", "Fighting Game", "Third-Person Shooter", "First-Person Shooter"},
        "Handheld": {"Puzzle Game", "Skill Game", "Platformer", "Racing", "Visual Novel"},
        "Mobile": {"Puzzle Game", "Skill Game", "Simulation", "Visual Novel", "Economic Simulation"},
    }
    return 7 if project.genre in category_preferences[project.category] else -3


def finish_project(state: GameState) -> None:
    studio = state.studio
    project = studio.current_project
    if project is None:
        return
    average_skill = project.quality_points / max(1, project.work_done)
    match = 8 if project.topic in GOOD_MATCHES[project.genre] else -5
    focus_ideal = GENRE_PROFILES[project.genre]["priorities"]
    focus_distance = sum(abs(actual - ideal) for actual, ideal in zip(project.focus, focus_ideal))
    focus_bonus = max(-9, 8 - focus_distance // 6)
    defect_rate = project.defects / max(1, project.work_done)
    defect_penalty = min(24, round(defect_rate * 170))
    scope_risk = scope_by_name(project.scope)["risk"]
    tools_bonus = 4 if "tools" in studio.upgrades else 0
    previous_game = next((game for game in studio.catalog if game.game_id == project.sequel_of), None)
    sequel_quality = 0 if previous_game is None else round((previous_game.score - 50) / 8)
    sequel_fatigue = max(0, project.generation - 3) * 2
    score = max(24, min(94, round(22 + average_skill * 0.66 + match + focus_bonus + platform_fit(project) + tools_bonus + sequel_quality - sequel_fatigue - defect_penalty - scope_risk)))
    refund_rate = max(0.03, min(0.24, 0.16 - score / 1_000 + defect_rate * 0.35))
    marketing = marketing_by_name(project.marketing_name)
    genre_audience = studio.genre_fans.get(project.genre, 0)
    sequel_audience = genre_audience * 0.45 if project.sequel_of else genre_audience * 0.10
    discoverability = 75 + marketing["boost"] + project.hype * 8 + studio.followers * 0.12 + studio.reputation * 3 + sequel_audience
    quality_multiplier = max(0.12, (score / 72) ** 3)
    scope_multiplier = {"Micro": 1.0, "Small": 1.7, "Ambitious": 2.7}[project.scope]
    units = max(12, round(discoverability * quality_multiplier * scope_multiplier * project.reach))
    evergreen_units = max(1, round((score / 100) ** 4 * scope_multiplier * 10 + genre_audience / 800))
    game_id = studio.next_game_id
    studio.next_game_id += 1
    game = ReleasedGame(
        game_id,
        project.title,
        project.genre,
        project.topic,
        project.channel,
        score,
        state.clock.current_date.isoformat(),
        project.sequel_of,
        project.generation,
        hype=min(150, project.hype + score / 5),
        active_players=units * 0.75,
        monthly_players=max(1, round(units * 0.9)),
        peak_monthly_players=max(1, round(units * 0.9)),
        production_cost=project.production_cost,
        labor_cost=project.labor_cost,
        marketing_cost=project.marketing_cost,
        cost_history_complete=project.cost_history_complete,
    )
    studio.catalog.append(game)
    for promotion in studio.active_promotions:
        if promotion.game_id == 0:
            promotion.game_id = game_id
    sale = ActiveSale(
        project.title,
        project.channel,
        score,
        project.price,
        project.platform_cut,
        refund_rate,
        units,
        52,
        game_id=game_id,
        genre=project.genre,
        evergreen_units=evergreen_units,
    )
    studio.active_sales.append(sale)
    studio.current_project = None
    studio.released_games += 1
    studio.reputation = max(0, studio.reputation + (score - 50) / 12)
    launch_followers = max(5, round(units * (0.05 + score / 2_000)))
    studio.followers += launch_followers
    studio.genre_fans[project.genre] = studio.genre_fans.get(project.genre, 0) + launch_followers
    studio.topic_fans[project.topic] = studio.topic_fans.get(project.topic, 0) + launch_followers
    state.log(f"Released {project.title} after {project.weeks} weeks: {score}/100, {refund_rate:.0%} expected refunds.")
    state.log(f"The store predicts {units:,} first-week units. You keep {(1 - project.platform_cut):.0%} before refunds.")


def develop_project(state: GameState) -> None:
    studio = state.studio
    project = studio.current_project
    if project is None:
        return
    weekly_salary = sum(employee.annual_salary / 52 for employee in studio.team)
    weekly_burden = sum(employee.annual_salary / 52 for employee in studio.team if not employee.founder) * 0.13
    project.labor_cost += weekly_salary + weekly_burden
    rng = random.Random(studio.seed + state.clock.week * 7919)
    total_output = 0.0
    quality = 0.0
    defect_factor = 1.0
    for employee in studio.team:
        weighted = sum(skill * percent for skill, percent in zip(employee.skills, project.focus)) / 100
        availability = max(0.35, employee.morale / 100) * max(0.35, 1 - employee.fatigue / 130)
        variance = 1.0 if employee.trait == "Pragmatic" else rng.uniform(0.91, 1.08)
        personal_output = weighted * availability * variance
        if employee.trait == "Perfectionist":
            personal_output *= 0.92
            weighted += 6
        elif employee.trait == "Night owl":
            personal_output *= 1.08
            employee.fatigue += 1.5
        elif employee.trait == "Methodical":
            defect_factor *= 0.94
        elif employee.trait == "Collaborative":
            for teammate in studio.team:
                teammate.morale = min(100, teammate.morale + 0.12)
        total_output += personal_output
        quality += personal_output * weighted
        employee.weeks_employed += 1
        experience_gain = max(1, round(personal_output / 25))
        employee.experience += round(experience_gain * (1.5 if employee.trait == "Fast learner" else 1.0))
        if employee.experience >= 100:
            employee.experience -= 100
            strongest = max(range(4), key=lambda index: employee.skills[index])
            attribute = ("design", "art", "audio", "code")[strongest]
            setattr(employee, attribute, min(99, getattr(employee, attribute) + 1))
            state.log(f"{employee.name} improved their {SKILLS[strongest].lower()} skill through project experience.")
        employee.fatigue = min(100, employee.fatigue + (2.5 if studio.contract else 1.2))
    if "hardware" in studio.upgrades:
        total_output *= 1.10
    if studio.contract:
        total_output *= 0.55
        quality *= 0.55
    support_factor = max(0.70, 1 - 0.04 * len(studio.active_sales))
    total_output *= support_factor
    quality *= support_factor
    operations_factor = max(0.25, 1 - marketing_team_load(studio) - update_team_load(studio))
    total_output *= operations_factor
    quality *= operations_factor
    uncapped_output = total_output
    total_output = min(total_output, project.total_work - project.work_done)
    quality *= total_output / max(1, uncapped_output)
    project.work_done += total_output
    project.quality_points += quality
    code_skill = sum(employee.code for employee in studio.team) / len(studio.team)
    defect_factor *= 0.75 if "qa" in studio.upgrades else 1.0
    project.defects += total_output * max(0.015, (0.13 - code_skill / 900)) * defect_factor
    project.weeks += 1
    project.hype *= 0.985
    if project.work_done >= project.total_work - 0.01:
        finish_project(state)


def buy_promotion(state: GameState, game_id: int, promotion_index: int) -> bool:
    studio = state.studio
    promotion = PROMOTIONS[promotion_index]
    target_title = ""
    if game_id == 0 and studio.current_project:
        target_title = studio.current_project.title
    elif game_id:
        game = game_by_id(studio, game_id)
        if game:
            target_title = game.title
    if not target_title:
        state.log("Choose a current project or released game before buying promotion.")
        return False
    if studio.reputation < promotion["rep"]:
        state.log(f"{promotion['name']} requires {promotion['rep']} game reputation; you have {studio.reputation:.1f}.")
        return False
    if studio.cash < promotion["cost"] + monthly_fixed_cost(studio):
        state.log(f"Cannot fund {promotion['name']} without risking next month's bills.")
        return False
    add_expense(studio, promotion["cost"], "Marketing")
    if game_id == 0 and studio.current_project:
        studio.current_project.marketing_cost += promotion["cost"]
    elif game_id:
        game = game_by_id(studio, game_id)
        if game:
            game.marketing_cost += promotion["cost"]
    studio.active_promotions.append(
        Promotion(
            studio.next_promotion_id,
            promotion["name"],
            game_id,
            target_title,
            promotion["weeks"],
            promotion["weeks"],
            float(promotion["hype"]),
            promotion["team"],
        )
    )
    studio.next_promotion_id += 1
    state.log(f"Started {promotion['name']} for {target_title}: ${promotion['cost']:,}, {promotion['weeks']} weeks, +{promotion['hype']} potential hype.")
    return True


def process_promotions(state: GameState) -> None:
    finished = []
    for promotion in state.studio.active_promotions:
        hype_gain = promotion.hype_total / promotion.total_weeks
        if promotion.game_id == 0 and state.studio.current_project:
            state.studio.current_project.hype = min(200, state.studio.current_project.hype + hype_gain)
        else:
            game = game_by_id(state.studio, promotion.game_id)
            if game:
                game.hype = min(200, game.hype + hype_gain)
                sale = sale_for_game(state.studio, game.game_id)
                if sale:
                    sale.weekly_units += max(1, round(hype_gain / 4))
        promotion.weeks_left -= 1
        if promotion.weeks_left <= 0:
            finished.append(promotion)
    for promotion in finished:
        state.studio.active_promotions.remove(promotion)
        state.log(f"{promotion.name} for {promotion.target_title} finished.")


def toggle_game_updates(state: GameState, game_id: int) -> bool:
    game = game_by_id(state.studio, game_id)
    if game is None:
        return False
    game.auto_updates = not game.auto_updates
    status = "ON" if game.auto_updates else "OFF"
    state.log(f"Continuous updates {status} for {game.title}.")
    return game.auto_updates


def cycle_game_update_focus(state: GameState, game_id: int, delta: int = 1) -> str | None:
    game = game_by_id(state.studio, game_id)
    if game is None:
        return None
    index = next((index for index, focus in enumerate(UPDATE_FOCUSES) if focus["name"] == game.update_focus), 0)
    game.update_focus = UPDATE_FOCUSES[(index + delta) % len(UPDATE_FOCUSES)]["name"]
    game.update_progress = 0
    state.log(f"{game.title} update focus changed to {game.update_focus}; update progress reset.")
    return game.update_focus


def cycle_game_update_size(state: GameState, game_id: int, delta: int = 1) -> str | None:
    game = game_by_id(state.studio, game_id)
    if game is None:
        return None
    index = next((index for index, size in enumerate(UPDATE_SIZES) if size["name"] == game.update_size), 0)
    game.update_size = UPDATE_SIZES[(index + delta) % len(UPDATE_SIZES)]["name"]
    game.update_progress = 0
    state.log(f"{game.title} update size changed to {game.update_size}; update progress reset.")
    return game.update_size


def process_game_updates(state: GameState) -> None:
    games = [game for game in state.studio.catalog if game.auto_updates]
    if not games:
        return
    for employee in state.studio.team:
        employee.fatigue = min(100, employee.fatigue + 0.35 * len(games))
    for game in games:
        size = update_size_by_name(game.update_size)
        focus = update_focus_by_name(game.update_focus)
        game.update_progress += update_weekly_output(state.studio, game) / size["work"] * 100
        while game.update_progress >= 100:
            game.update_progress -= 100
            game.updates_released += 1
            rating_factor = max(0.10, (game.score / 100) ** 2)
            hype_gain = size["hype"] * focus["hype"] * rating_factor
            game.hype = min(200, game.hype + hype_gain)
            returning_players = round(
                (game.monthly_players * 0.20 + game.units_sold * 0.012)
                * size["sales"]
                * focus["players"]
                * rating_factor
            )
            game.active_players += returning_players / 3
            sale = sale_for_game(state.studio, game.game_id)
            if sale:
                sale.weekly_units += max(1, round(sale.evergreen_units * size["sales"] * rating_factor))
            add_expense(state.studio, size["cost"], "Live operations")
            game.post_launch_cost += size["cost"]
            state.log(
                f"Released update #{game.updates_released} ({game.update_size} {game.update_focus}) for {game.title}: "
                f"+{hype_gain:.1f} hype, about {returning_players:,} players returned."
            )


def process_sales(state: GameState) -> None:
    studio = state.studio
    for sale in studio.active_sales:
        units = max(0, sale.weekly_units)
        gross = units * sale.price
        net = gross * (1 - sale.refund_rate) * (1 - sale.platform_cut)
        add_revenue(studio, net, "Game sales")
        hosting_cost = max(10, units * 0.03)
        add_expense(studio, hosting_cost, "Hosting")
        sale.units_sold += units
        sale.gross_revenue += gross
        sale.net_revenue += net
        gained = round(units * max(0.01, sale.score / 1_500))
        studio.followers += gained
        if sale.genre:
            studio.genre_fans[sale.genre] = studio.genre_fans.get(sale.genre, 0) + gained
        game = next((item for item in studio.catalog if item.game_id == sale.game_id), None)
        if game:
            game.units_sold += units
            game.net_revenue += net
            game.post_launch_cost += hosting_cost
            studio.topic_fans[game.topic] = studio.topic_fans.get(game.topic, 0) + gained
            hype_lift = game.hype / 14
            game.hype *= 0.965
            retention = min(0.93, 0.58 + game.score * 0.0037)
            game.active_players = game.active_players * retention + units * 0.70
            game.monthly_players = max(0, round(game.active_players * 3.2))
            game.peak_monthly_players = max(game.peak_monthly_players, game.monthly_players)
        else:
            hype_lift = 0
        tail = min(0.91, 0.55 + sale.score * 0.0035 + (0.02 if "analytics" in studio.upgrades else 0))
        sale.weekly_units = max(sale.evergreen_units, round(units * tail + hype_lift))
        sale.weeks_left = -1


def close_month(state: GameState, previous_month: str) -> None:
    studio = state.studio
    revenue = round(studio.period_revenue)
    expenses = round(studio.period_expenses)
    categories = {category: round(amount) for category, amount in studio.period_expense_categories.items()}
    revenue_categories = {category: round(amount) for category, amount in studio.period_revenue_categories.items()}
    pre_tax_net = revenue - expenses
    if pre_tax_net > 0:
        studio.tax_reserve += pre_tax_net * 0.18
    previous_month_number = int(previous_month[-2:])
    if previous_month_number in (3, 6, 9, 12) and studio.tax_reserve >= 1:
        payment = round(studio.tax_reserve)
        studio.cash -= payment
        studio.lifetime_expenses += payment
        expenses += payment
        categories["Taxes"] = categories.get("Taxes", 0) + payment
        studio.tax_reserve = 0
        state.log(f"Quarterly estimated income tax paid: ${payment:,}.")
    net = revenue - expenses
    studio.ledger.insert(0, LedgerMonth(previous_month, revenue, expenses, net, categories, revenue_categories))
    del studio.ledger[12:]
    studio.period_revenue = 0
    studio.period_revenue_categories = {}
    studio.period_expenses = 0
    studio.period_expense_categories = {}
    state.log(f"Closed {previous_month}: revenue ${revenue:,}, expenses ${expenses:,}, net ${net:+,}.")


def begin_month(state: GameState, month: str) -> None:
    studio = state.studio
    close_month(state, studio.accounting_month)
    studio.accounting_month = month
    costs = monthly_cost_breakdown(studio)
    bill = sum(costs.values())
    for category, amount in costs.items():
        add_expense(studio, amount, category)
    state.log(f"Monthly operating costs paid: ${bill:,} including salaries, burden, tools, and admin.")
    for employee in list(studio.team):
        recovery = 15 if "health" in studio.upgrades else 10
        employee.fatigue = max(0, employee.fatigue - recovery)
        morale_change = 5 if "coworking" in studio.upgrades else 0
        if employee.fatigue > 65:
            morale_change -= 8
        elif employee.fatigue < 25:
            morale_change += 2
        employee.morale = max(0, min(100, employee.morale + morale_change))
        if not employee.founder and employee.morale < 22:
            rng = random.Random(studio.seed + state.clock.week + employee.employee_id)
            if rng.random() < 0.35:
                studio.team.remove(employee)
                state.log(f"{employee.name} resigned after sustained low morale. No replacement was automatic.")
    refresh_applicants(state)
    state.log(f"The applicant market refreshed with {len(studio.applicants)} candidates as the studio's reach changed.")
    refresh_contract_offers(state)
    target = recommended_team_size(studio)
    if len(studio.team) < target:
        state.log(f"Growth analysis recommends {target} staff; the current team of {len(studio.team)} is understaffed. Hire only if runway allows.")
    elif len(studio.team) > target + 1:
        state.log(f"The {len(studio.team)}-person team is above the current demand signal of {target}; monitor payroll closely.")


def process_contract(state: GameState) -> None:
    studio = state.studio
    start_next_contract(state)
    contract = studio.contract
    if contract is None:
        return
    if contract.required_work <= 0:
        contract.weeks_left -= 1
        for employee in studio.team:
            employee.fatigue = min(100, employee.fatigue + 2)
        if contract.weeks_left <= 0:
            add_revenue(studio, contract.payout, "Contracts")
            studio.contractor_reputation = min(100, studio.contractor_reputation + 1)
            studio.contracts_completed += 1
            state.log(f"Delivered the legacy {contract.title}; client paid ${contract.payout:,}.")
            studio.contract = None
            start_next_contract(state)
        return

    output = contract_weekly_output(studio, contract.focus)
    contract.work_done = min(contract.required_work, contract.work_done + output)
    contract.weeks_left -= 1
    for employee in studio.team:
        employee.fatigue = min(100, employee.fatigue + 2)
    if contract.work_done >= contract.required_work:
        add_revenue(studio, contract.payout, "Contracts")
        reputation_gain = contract.difficulty * 2 + max(0, contract.weeks_left) * 0.25
        studio.contractor_reputation = min(100, studio.contractor_reputation + reputation_gain)
        studio.contracts_completed += 1
        state.log(f"Delivered {contract.client}'s {contract.title}; paid ${contract.payout:,}, contractor reputation +{reputation_gain:.1f}.")
        studio.contract = None
        start_next_contract(state)
    elif contract.weeks_left <= 0:
        reputation_loss = max(2, contract.difficulty * 3)
        studio.contractor_reputation = max(0, studio.contractor_reputation - reputation_loss)
        studio.contracts_failed += 1
        state.log(f"Missed {contract.client}'s {contract.title} deadline; no payment and contractor reputation -{reputation_loss}.")
        studio.contract = None
        start_next_contract(state)


def process_week(state: GameState, week_date: date) -> None:
    studio = state.studio
    month = week_date.strftime("%Y-%m")
    if month != studio.accounting_month:
        begin_month(state, month)
    process_promotions(state)
    process_game_updates(state)
    process_sales(state)
    process_contract(state)
    develop_project(state)
    if studio.cash < 0:
        studio.insolvent_weeks += 1
        if studio.insolvent_weeks == 1:
            state.log("The bank balance is negative. You have eight weeks to recover before closure.")
        if studio.insolvent_weeks >= 8:
            studio.closed = True
            state.time_speed_index = 0
            state.log("The studio is insolvent and has closed. Load an earlier save or begin again.")
    else:
        studio.insolvent_weeks = 0


def advance_game(state: GameState, weeks: int) -> None:
    for offset in range(weeks):
        week_date = state.clock.current_date - timedelta(days=7 * (weeks - offset - 1))
        process_week(state, week_date)


def employee_from_data(data: dict) -> Employee:
    return Employee(**data)


def state_to_data(state: GameState) -> dict:
    return {
        "version": SAVE_VERSION,
        "clock": {
            "current_date": state.clock.current_date.isoformat(),
            "week": state.clock.week,
            "elapsed_seconds": state.clock.elapsed_seconds,
        },
        "studio": asdict(state.studio),
        "ui": {
            "selected_genre": state.selected_genre,
            "selected_topic": state.selected_topic,
            "selected_channel": state.selected_channel,
            "selected_scope": state.selected_scope,
            "selected_marketing": state.selected_marketing,
            "marketing_tab": state.marketing_tab,
            "focus": state.focus,
            "time_speed_index": state.time_speed_index,
            "resume_speed_index": state.resume_speed_index,
            "draft_title": state.draft_title,
            "title_roll": state.title_roll,
            "sequel_game_id": state.sequel_game_id,
        },
        "logs": state.logs,
    }


def studio_from_data(data: dict) -> Studio:
    values = dict(data)
    values["team"] = [employee_from_data(item) for item in values.get("team", [])]
    values["applicants"] = [employee_from_data(item) for item in values.get("applicants", [])]
    if values.get("current_project"):
        values["current_project"] = Project(**values["current_project"])
    values["active_sales"] = [ActiveSale(**item) for item in values.get("active_sales", [])]
    catalog = [ReleasedGame(**item) for item in values.get("catalog", [])]
    if not catalog:
        for sale in values["active_sales"]:
            topic, separator, genre = sale.title.partition(": ")
            if separator and genre in GENRES and topic in TOPICS:
                game_id = len(catalog) + 1
                sale.game_id = game_id
                sale.genre = genre
                catalog.append(
                    ReleasedGame(
                        game_id,
                        sale.title,
                        genre,
                        topic,
                        sale.channel,
                        sale.score,
                        "Historical",
                        units_sold=sale.units_sold,
                        net_revenue=sale.net_revenue,
                    )
                )
    values["catalog"] = catalog
    values["next_game_id"] = max(values.get("next_game_id", 1), max((game.game_id for game in catalog), default=0) + 1)
    if catalog and not values.get("genre_fans"):
        legacy_fans = max(0, values.get("followers", 40) - 40)
        per_game = legacy_fans // len(catalog)
        values["genre_fans"] = {}
        values["topic_fans"] = {}
        for game in catalog:
            values["genre_fans"][game.genre] = values["genre_fans"].get(game.genre, 0) + per_game
            values["topic_fans"][game.topic] = values["topic_fans"].get(game.topic, 0) + per_game
    if values.get("contract"):
        values["contract"] = Contract(**values["contract"])
    values["contract_offers"] = [Contract(**item) for item in values.get("contract_offers", [])]
    raw_queue = values.get("contract_queue", [])
    legacy_queue_without_source = bool(raw_queue) and any("auto_accepted" not in item for item in raw_queue)
    values["contract_queue"] = [Contract(**item) for item in raw_queue]
    if not values.get("auto_contracts", False) and legacy_queue_without_source:
        values["legacy_auto_jobs_cancelled"] = len(values["contract_queue"])
        values["contract_queue"] = []
        if values.get("contract") and "auto_accepted" not in data.get("contract", {}):
            values["contract"].auto_accepted = True
    contract_ids = [contract.contract_id for contract in values["contract_offers"] + values["contract_queue"]]
    if values.get("contract"):
        contract_ids.append(values["contract"].contract_id)
    values["next_contract_id"] = max(values.get("next_contract_id", 1), max(contract_ids, default=0) + 1)
    values["active_promotions"] = [Promotion(**item) for item in values.get("active_promotions", [])]
    values["next_promotion_id"] = max(
        values.get("next_promotion_id", 1),
        max((promotion.promotion_id for promotion in values["active_promotions"]), default=0) + 1,
    )
    ledger = [LedgerMonth(**item) for item in values.get("ledger", [])]
    for entry in ledger:
        if entry.expenses and not entry.categories:
            entry.categories = {"Historical total": entry.expenses}
        if entry.revenue and not entry.revenue_categories:
            entry.revenue_categories = {"Historical revenue": entry.revenue}
    values["ledger"] = ledger
    if values.get("period_expenses", 0) and not values.get("period_expense_categories"):
        values["period_expense_categories"] = {"Historical current": values["period_expenses"]}
    if values.get("period_revenue", 0) and not values.get("period_revenue_categories"):
        values["period_revenue_categories"] = {"Historical revenue": values["period_revenue"]}
    return Studio(**values)


def migrate_legacy(data: dict, save_path: str) -> GameState:
    old = data.get("studio", {})
    studio = Studio(
        cash=max(25_000, float(old.get("cash", 10_000)) * 3),
        followers=int(old.get("fans", 0)) + 40,
        reputation=float(old.get("reputation", 0)),
        released_games=int(old.get("released_games", 0)),
    )
    state = GameState(studio=studio, save_path=save_path)
    state.logs = [
        f"{state.clock.current_date:%d %b %Y}: legacy progress became a modern studio with ${studio.cash:,.0f}.",
        "Cash is runway. Payroll, software, insurance, tax, refunds, and store cuts are real.",
    ]
    state.log("Migrated a legacy 1976 save into the modern indie simulation; incompatible projects and hires were retired.")
    return state


def state_from_data(data: dict, save_path: str) -> GameState:
    if data.get("version") != SAVE_VERSION:
        return migrate_legacy(data, save_path)
    clock_data = data["clock"]
    clock = GameClock(date.fromisoformat(clock_data["current_date"]), clock_data["week"], clock_data.get("elapsed_seconds", 0.0))
    ui = data.get("ui", {})
    studio = studio_from_data(data["studio"])
    recover_catalog_from_logs(studio, data.get("logs", []))
    recover_contractor_history(studio, data.get("logs", []))
    ensure_catalog_sales(studio)
    return GameState(
        clock=clock,
        studio=studio,
        selected_genre=ui.get("selected_genre", 0),
        selected_topic=ui.get("selected_topic", 0),
        selected_channel=ui.get("selected_channel", 0),
        selected_scope=ui.get("selected_scope", 0),
        selected_marketing=ui.get("selected_marketing", 0),
        marketing_tab=ui.get("marketing_tab", 0),
        focus=ui.get("focus", [30, 25, 15, 30]),
        time_speed_index=ui.get("time_speed_index", 1),
        resume_speed_index=ui.get("resume_speed_index", 1),
        draft_title=ui.get("draft_title", ""),
        title_roll=ui.get("title_roll", 0),
        sequel_game_id=ui.get("sequel_game_id"),
        save_path=save_path,
        logs=data.get("logs", []),
    )


def save_game(state: GameState) -> None:
    Path(state.save_path).write_text(json.dumps(state_to_data(state), indent=2), encoding="utf-8")


def load_game(save_path: str) -> GameState:
    return state_from_data(json.loads(Path(save_path).read_text(encoding="utf-8")), save_path)
