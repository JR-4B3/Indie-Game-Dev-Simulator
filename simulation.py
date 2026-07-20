from __future__ import annotations

import json
import math
import random
import re
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path

from game_data import GENRES, GENRE_PROFILES, GOOD_MATCHES, TOPICS


SAVE_VERSION = 5
START_DATE = date.today()
SECONDS_PER_WEEK = 20.0
SECONDS_PER_DAY = SECONDS_PER_WEEK / 7
SKILLS = ("Design", "Art", "Audio", "Code")
EMPLOYEE_SKILLS = SKILLS + ("Research",)
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
    {"name": "Micro", "work": 900, "setup": 1_800, "price": 9.99, "risk": 0, "team": 1, "rep": 0, "market": 0.55},
    {"name": "Compact", "work": 1_350, "setup": 3_200, "price": 12.99, "risk": 1, "team": 1, "rep": 0, "market": 0.75},
    {"name": "Small", "work": 1_900, "setup": 5_500, "price": 14.99, "risk": 4, "team": 1, "rep": 0, "market": 1.0},
    {"name": "Mid-size", "work": 2_700, "setup": 9_000, "price": 19.99, "risk": 7, "team": 2, "rep": 0, "market": 1.35},
    {"name": "Ambitious", "work": 3_600, "setup": 14_000, "price": 24.99, "risk": 10, "team": 3, "rep": 4, "market": 1.75},
    {"name": "Large", "work": 7_000, "setup": 80_000, "price": 39.99, "risk": 17, "team": 7, "rep": 18, "market": 2.8},
    {"name": "Blockbuster", "work": 15_000, "setup": 500_000, "price": 69.99, "risk": 28, "team": 18, "rep": 45, "market": 5.0},
)

AUDIENCES = (
    {"name": "Broad audience", "genres": set(GENRES), "market": 1.0, "price": 1.0},
    {"name": "Kids & families", "genres": {"Platformer", "Puzzle Game", "Racing", "Cozy Game", "Building Game"}, "market": 0.75, "price": 0.85},
    {"name": "Core players", "genres": {"Action", "First-Person Shooter", "Third-Person Shooter", "Role-Playing Game", "Soulslike", "Metroidvania", "Battle Royale", "Extraction Shooter"}, "market": 1.15, "price": 1.1},
    {"name": "Strategy enthusiasts", "genres": {"Strategy", "Real-Time Strategy", "Economic Simulation", "Building Game", "Automation", "Deckbuilder", "Roguelike"}, "market": 0.7, "price": 1.15},
    {"name": "Cozy & casual", "genres": {"Cozy Game", "Simulation", "Puzzle Game", "Visual Novel", "Skill Game"}, "market": 1.1, "price": 0.85},
    {"name": "Social groups", "genres": {"Social Deduction", "Battle Royale", "Sports Game", "Fighting Game", "Racing"}, "market": 1.0, "price": 0.9},
)

GAME_FORMATS = (
    {"name": "Offline solo", "work": 1.0, "setup": 0, "risk": 0, "team": 1, "rep": 0, "market": 0.9, "hosting": 0.0},
    {"name": "Online co-op", "work": 1.35, "setup": 12_000, "risk": 4, "team": 2, "rep": 0, "market": 1.15, "hosting": 0.04},
    {"name": "Competitive online", "work": 1.8, "setup": 40_000, "risk": 9, "team": 4, "rep": 8, "market": 1.5, "hosting": 0.08},
    {"name": "Persistent world", "work": 2.8, "setup": 180_000, "risk": 17, "team": 9, "rep": 25, "market": 2.2, "hosting": 0.16},
    {"name": "MMO", "work": 7.0, "setup": 2_500_000, "risk": 32, "team": 30, "rep": 60, "market": 5.0, "hosting": 0.35},
)

CREATIVE_DIRECTIONS = (
    {"name": "Refined core loop", "focus": (50, 12, 8, 30), "work": 1.0, "quality": 5, "market": 0, "risk": 0, "tradeoff": "Reliable quality; limited novelty"},
    {"name": "Bold new mechanic", "focus": (44, 12, 8, 36), "work": 1.12, "quality": 1, "market": 12, "risk": 7, "tradeoff": "Higher upside; prototype risk"},
    {"name": "Deep systemic play", "focus": (48, 8, 6, 38), "work": 1.16, "quality": 3, "market": 5, "risk": 4, "tradeoff": "Strong mastery; hard onboarding"},
    {"name": "A striking world", "focus": (24, 44, 22, 10), "work": 1.1, "quality": 4, "market": 5, "risk": 2, "tradeoff": "Trailer appeal; asset heavy"},
    {"name": "Narrative depth", "focus": (42, 30, 18, 10), "work": 1.08, "quality": 4, "market": 2, "risk": 2, "tradeoff": "Memorable story; low replayability"},
    {"name": "Endless mastery", "focus": (52, 10, 8, 30), "work": 1.2, "quality": 2, "market": 8, "risk": 5, "tradeoff": "Long retention; balance burden"},
    {"name": "Community first", "focus": (38, 12, 14, 36), "work": 1.18, "quality": 1, "market": 10, "risk": 6, "tradeoff": "Social growth; moderation burden"},
)

RELEASE_STRATEGIES = (
    {"name": "Complete package", "work": 1.0, "setup": 0, "risk": 0, "market": 0, "price": 1.0, "tradeoff": "Clear promise; short sales tail"},
    {"name": "Free update roadmap", "work": 1.08, "setup": 1_500, "risk": 2, "market": 5, "price": 1.0, "tradeoff": "Better retention; ongoing cost"},
    {"name": "DLC roadmap", "work": 1.05, "setup": 2_500, "risk": 3, "market": 2, "price": 1.05, "tradeoff": "Future revenue; fragments attention"},
    {"name": "Live service", "work": 1.3, "setup": 18_000, "risk": 10, "market": 12, "price": 0.75, "tradeoff": "Large upside; permanent content pressure"},
)

PRODUCTION_DECISIONS = (
    {
        "threshold": 0.12,
        "title": "Vertical slice review",
        "question": "The core loop works, but it is not distinctive yet.",
        "options": (
            {"name": "Commit to the proven loop", "effect": "-6% remaining work, +consistency, -4 market appeal", "work": 0.94, "quality": 2, "market": -4},
            {"name": "Fund the standout mechanic", "effect": "+14% remaining work, +10 market appeal, more defects", "work": 1.14, "quality": 1, "market": 10, "defects": 3, "fatigue": 3},
        ),
    },
    {
        "threshold": 0.30,
        "title": "Scope lock",
        "question": "The full feature list no longer fits the original schedule.",
        "options": (
            {"name": "Cut the weakest feature", "effect": "-12% remaining work, +focus, -4 hype", "work": 0.88, "quality": 2, "hype": -4},
            {"name": "Honor the full promise", "effect": "+16% remaining work, +quality and appeal, team fatigue", "work": 1.16, "quality": 3, "market": 5, "fatigue": 5},
        ),
    },
    {
        "threshold": 0.72,
        "title": "Alpha review",
        "question": "There is time for either stability or one more content push.",
        "options": (
            {"name": "Run a stabilization sprint", "effect": "+8% remaining work, remove 25% of defects", "work": 1.08, "quality": 2, "defect_multiplier": 0.75},
            {"name": "Add the late content beat", "effect": "+18% remaining work, +10 hype, more defects", "work": 1.18, "market": 5, "hype": 10, "defects": 7},
        ),
    },
    {
        "threshold": 0.90,
        "title": "Release candidate",
        "question": "Reviews could improve, but every extra week burns runway.",
        "options": (
            {"name": "Delay for polish", "effect": "+50% remaining work, remove 45% of defects, +quality", "work": 1.50, "quality": 4, "defect_multiplier": 0.55},
            {"name": "Hold the release date", "effect": "-20% remaining work, +4 hype, quality risk", "work": 0.80, "quality": -2, "hype": 4},
        ),
    },
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
    {"name": "Hotfix", "work": 24, "bugs": 3, "fixes": 4, "escaped": 0.2, "cost": 75, "hype": 2, "sales": 1, "version": (0, 0, 1), "team": 0.06},
    {"name": "Patch", "work": 70, "bugs": 8, "fixes": 10, "escaped": 0.8, "cost": 250, "hype": 7, "sales": 2, "version": (0, 0, 10), "team": 0.12},
    {"name": "Content", "work": 170, "bugs": 20, "fixes": 25, "escaped": 2.5, "cost": 900, "hype": 18, "sales": 4, "version": (0, 1, 0), "team": 0.20},
    {"name": "Expansion", "work": 380, "bugs": 45, "fixes": 55, "escaped": 6.0, "cost": 3_500, "hype": 42, "sales": 9, "version": (0, 10, 0), "team": 0.30},
    {"name": "Paid DLC", "work": 620, "bugs": 65, "fixes": 70, "escaped": 8.0, "cost": 8_000, "hype": 58, "sales": 12, "version": (1, 0, 0), "team": 0.38, "price": 9.99},
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

FRANCHISE_RANKS = ("Unknown", "Niche", "Recognized", "Popular", "Famous", "Iconic")
FRANCHISE_RANK_THRESHOLDS = (30, 120, 400, 1_100, 2_600)

MEDIA_VENTURES = (
    {"key": "merch", "name": "Merchandise line", "cost": 6_000, "weeks": 26, "rank": 1, "effect": "Steady weekly merch revenue from the fanbase"},
    {"key": "convention", "name": "Fan convention", "cost": 25_000, "weeks": 3, "rank": 3, "effect": "Big awareness and hype surge for the whole IP"},
    {"key": "film", "name": "Film adaptation", "cost": 120_000, "weeks": 40, "rank": 4, "effect": "Box-office release after production; quality decides the payoff"},
    {"key": "series", "name": "Series adaptation", "cost": 220_000, "weeks": 52, "rank": 4, "effect": "Prestige streaming series; the largest transmedia payoff"},
)

COMPETITOR_STUDIOS = (
    {"name": "Nintari", "tier": "platform", "size": 9.0, "genres": ("Platformer", "Cozy Game", "Racing", "Puzzle Game", "Skill Game"), "fanbase": 2_400_000, "reputation": 88},
    {"name": "Sunny Interactive", "tier": "platform", "size": 8.5, "genres": ("Action", "Third-Person Shooter", "Adventure", "Role-Playing Game"), "fanbase": 2_100_000, "reputation": 84},
    {"name": "Macrohard Games", "tier": "platform", "size": 8.0, "genres": ("First-Person Shooter", "Racing", "Strategy", "Simulation"), "fanbase": 1_800_000, "reputation": 78},
    {"name": "Ubicore", "tier": "publisher", "size": 7.0, "genres": ("Action", "Adventure", "Immersive Sim", "Survival Game"), "fanbase": 950_000, "reputation": 62},
    {"name": "Starfall Interactive", "tier": "publisher", "size": 6.5, "genres": ("Action", "Adventure", "Third-Person Shooter"), "fanbase": 1_200_000, "reputation": 90},
    {"name": "Frostmire Games", "tier": "publisher", "size": 6.0, "genres": ("Role-Playing Game", "Strategy", "Deckbuilder"), "fanbase": 1_050_000, "reputation": 81},
    {"name": "Electronic Frontiers", "tier": "publisher", "size": 7.5, "genres": ("Sports Game", "First-Person Shooter", "Racing", "Simulation"), "fanbase": 1_400_000, "reputation": 58},
    {"name": "Paragon Studios", "tier": "publisher", "size": 6.0, "genres": ("Battle Royale", "Third-Person Shooter", "Building Game"), "fanbase": 1_600_000, "reputation": 70},
    {"name": "Novacore", "tier": "publisher", "size": 5.5, "genres": ("Role-Playing Game", "Strategy", "Adventure"), "fanbase": 820_000, "reputation": 76},
    {"name": "Red Engine Studio", "tier": "studio", "size": 4.0, "genres": ("Role-Playing Game", "Action", "Adventure"), "fanbase": 700_000, "reputation": 85},
    {"name": "Runestone Forge", "tier": "studio", "size": 3.0, "genres": ("Role-Playing Game", "Strategy"), "fanbase": 420_000, "reputation": 88},
    {"name": "Pixel Forge", "tier": "indie", "size": 1.0, "genres": ("Roguelike", "Metroidvania", "Deckbuilder"), "fanbase": 45_000, "reputation": 72},
    {"name": "Moonpetal Games", "tier": "indie", "size": 0.8, "genres": ("Cozy Game", "Simulation", "Visual Novel"), "fanbase": 30_000, "reputation": 68},
    {"name": "Tiny Anvil", "tier": "indie", "size": 0.7, "genres": ("Platformer", "Puzzle Game", "Metroidvania"), "fanbase": 22_000, "reputation": 65},
    {"name": "Ghost Lantern", "tier": "indie", "size": 0.9, "genres": ("Survival Game", "Adventure", "Visual Novel"), "fanbase": 28_000, "reputation": 70},
    {"name": "Hyperbolt", "tier": "indie", "size": 1.1, "genres": ("Action", "Roguelike", "Skill Game"), "fanbase": 60_000, "reputation": 78},
)

COMPETITOR_IP_NAMES = (
    "Starforged", "Emberfall", "Quantum Drift", "Shadowvale", "Iron Tide", "Moonlit Acres",
    "Gravball", "Night Circuit", "Deep Hollow", "Skybound Odyssey", "Crimson Pact", "Hollowlight",
    "Turbo Dynasty", "Whisker Works", "Astral Siege", "Frostline", "Byte Raiders", "Dune Runners",
    "Silent Grove", "Mecha Bloom", "Void Cartel", "Paper Kingdoms", "Thunder Vale", "Neon Harvest",
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
ROLE_RESEARCH = {
    "Game Designer": 66,
    "Programmer": 48,
    "2D/3D Artist": 40,
    "Audio Designer": 38,
    "Generalist": 56,
    "Producer": 82,
}
TRAITS = {
    "Methodical": "fewer defects, slower output",
    "Fast learner": "learns quickly, introduces more defects",
    "Collaborative": "lifts team morale, lower personal output",
    "Night owl": "higher output, faster fatigue",
    "Perfectionist": "higher quality, slower output",
    "Pragmatic": "predictable output, less quality upside",
    "Inventive": "higher quality ceiling, inconsistent pace",
    "Resilient": "resists fatigue, slightly slower pace",
}
QUIRKS = {
    "Cautious": "fewer defects, slower delivery",
    "Overcommitted": "more output, more fatigue",
    "Independent": "more personal output, lowers team morale",
    "Burst worker": "large good and bad output swings",
    "Hasty": "more output, more defects",
    "Reserved": "strong research alone, weak collaboration",
}


@dataclass
class GameClock:
    current_date: date = START_DATE
    week: int = 1
    elapsed_seconds: float = 0.0
    day: int = 1

    def update(self, delta_seconds: float) -> int:
        self.elapsed_seconds += delta_seconds
        days = 0
        while self.elapsed_seconds >= SECONDS_PER_DAY:
            self.elapsed_seconds -= SECONDS_PER_DAY
            self.current_date += timedelta(days=1)
            self.day += 1
            self.week = (self.day - 1) // 7 + 1
            days += 1
        return days

    @property
    def progress(self) -> float:
        day_in_week = (self.day - 1) % 7
        return (day_in_week + self.elapsed_seconds / SECONDS_PER_DAY) / 7


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
    research: int = 45
    morale: float = 72.0
    fatigue: float = 8.0
    experience: int = 0
    trait: str = "Pragmatic"
    quirk: str = "Cautious"
    weeks_employed: int = 0
    founder: bool = False
    training_skill: str = ""
    training_weeks_left: int = 0
    week_output: float = 0.0

    @property
    def skills(self) -> tuple[int, int, int, int]:
        return self.design, self.art, self.audio, self.code

    @property
    def all_skills(self) -> tuple[int, int, int, int, int]:
        return self.design, self.art, self.audio, self.code, self.research

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
    secondary_genre: str = ""
    secondary_topic: str = ""
    target_audience: str = "Broad audience"
    game_format: str = "Offline solo"
    creative_primary: str = "Refined core loop"
    creative_secondary: str = "A striking world"
    release_strategy: str = "Complete package"
    addressable_audience: int = 0
    competitors: int = 0
    market_score: int = 50
    forecast_score_low: int = 1
    forecast_score_high: int = 99
    forecast_audience_low: int = 0
    forecast_audience_high: int = 0
    forecast_competitors_low: int = 1
    forecast_competitors_high: int = 1
    forecast_confidence: int = 0
    hosting_rate: float = 0.0
    next_decision: int = 0
    pending_decision: int | None = None
    pending_day: int = 0
    decisions_made: list[str] = field(default_factory=list)
    scheduled_decisions: list[int] = field(default_factory=list)
    decision_resume_on_close: bool = False
    sequel_of: int | None = None
    generation: int = 1
    franchise_id: int | None = None
    hype: float = 0.0
    production_cost: float = 0.0
    labor_cost: float = 0.0
    marketing_cost: float = 0.0
    cost_history_complete: bool = False
    known_defects: float = 0.0
    bug_work: float = 0.0
    bug_work_done: float = 0.0

    @property
    def progress(self) -> float:
        return min(1.0, self.work_done / self.total_work)

    @property
    def bug_progress(self) -> float:
        return min(1.0, self.bug_work_done / self.bug_work) if self.bug_work else 0.0

    @property
    def remaining_work(self) -> float:
        return max(0.0, self.total_work - self.work_done) + max(0.0, self.bug_work - self.bug_work_done)

    @property
    def phase(self) -> str:
        if self.bug_work > 0:
            return "Bug fixing"
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
    week_units: float = 0.0

    @property
    def week_to_date(self) -> int:
        return round(self.week_units)


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
    franchise_id: int | None = None
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
    version: str = "1.00.00"
    actual_bugs: float = 0.0
    known_bugs: float = 0.0
    reported_bug_count: int = 0
    scope: str = "Unknown"
    price: float = 9.99
    secondary_genre: str = ""
    secondary_topic: str = ""
    target_audience: str = "Broad audience"
    game_format: str = "Offline solo"
    creative_primary: str = "Refined core loop"
    creative_secondary: str = "A striking world"
    release_strategy: str = "Complete package"
    addressable_audience: int = 0
    competitors: int = 0
    market_score: int = 50
    hosting_rate: float = 0.0
    dlcs_released: int = 0
    dlc_revenue: float = 0.0
    production_decisions: list[str] = field(default_factory=list)
    user_rating: float = 0.0
    press_rating: float = 0.0
    user_trend: float = 0.0
    sales_history: list[int] = field(default_factory=list)
    chart_peak: int = 0

    @property
    def known_bug_count(self) -> int:
        return max(0, math.floor(self.known_bugs))


@dataclass
class UpdateJob:
    update_id: int
    game_id: int
    game_title: str
    focus: str
    size: str
    target_version: str
    required_work: float
    bugs_found: float
    work_done: float = 0.0
    bugs_fixed: float = 0.0

    @property
    def phase(self) -> str:
        return "Development" if self.work_done < self.required_work else "Bug fixing"

    @property
    def progress(self) -> float:
        total = self.required_work + self.bugs_found
        return min(1.0, (self.work_done + self.bugs_fixed) / max(1, total))


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
    cost: int = 0


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
class Franchise:
    franchise_id: int
    name: str
    genre: str
    topic: str
    owner: str = "studio"
    awareness: float = 0.0
    reputation: float = 0.0
    fatigue: float = 0.0
    entries: int = 0
    total_units: int = 0
    total_revenue: float = 0.0
    created: str = ""

    @property
    def value(self) -> float:
        base = self.awareness * (0.4 + self.reputation / 100)
        return max(0.0, base * (1 - min(0.6, self.fatigue / 150)))

    @property
    def rank(self) -> int:
        return sum(self.value >= threshold for threshold in FRANCHISE_RANK_THRESHOLDS)

    @property
    def rank_name(self) -> str:
        return FRANCHISE_RANKS[self.rank]


@dataclass
class MediaVenture:
    venture_id: int
    kind: str
    name: str
    franchise_id: int
    franchise_name: str
    weeks_left: int
    total_weeks: int
    cost: int
    weekly_revenue: float
    release_payout: float = 0.0
    revenue: float = 0.0


@dataclass
class CompetitorGame:
    title: str
    franchise_name: str
    genre: str
    quality: int
    hype: float
    weeks_left: int
    size: float
    released_week: int = 0
    weekly_units: float = 0.0
    units_sold: int = 0


@dataclass
class ChartEntry:
    title: str
    studio_name: str
    genre: str
    weekly_units: int
    score: int
    game_id: int = 0


@dataclass
class Competitor:
    competitor_id: int
    name: str
    tier: str
    size: float
    fanbase: int
    reputation: float
    genres: list[str] = field(default_factory=list)
    franchises: list[Franchise] = field(default_factory=list)
    in_development: list[CompetitorGame] = field(default_factory=list)
    recent_releases: list[CompetitorGame] = field(default_factory=list)
    cooldown: int = 0


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
    active_update: UpdateJob | None = None
    update_queue: list[UpdateJob] = field(default_factory=list)
    active_promotions: list[Promotion] = field(default_factory=list)
    franchises: list[Franchise] = field(default_factory=list)
    media_ventures: list[MediaVenture] = field(default_factory=list)
    competitors: list[Competitor] = field(default_factory=list)
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
    next_update_id: int = 1
    next_promotion_id: int = 1
    next_franchise_id: int = 1
    next_venture_id: int = 1
    seed: int = 481516
    insolvent_weeks: int = 0
    insolvent_days: int = 0
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
    selected_secondary_genre: int = 0
    selected_secondary_topic: int = 0
    selected_audience: int = 0
    selected_format: int = 0
    selected_creative_primary: int = 0
    selected_creative_secondary: int = 3
    selected_release_strategy: int = 0
    selected_project_decision: int = 0
    selected_focus: int = 0
    mix_blend: bool = False
    mix_blend_backup: tuple = (0, 0)
    focus: list[int] = field(default_factory=lambda: [30, 25, 15, 30])
    selected_employee: int = 0
    selected_roster: int = 0
    selected_upgrade: int = 0
    selected_contract: int = 0
    selected_game: int = 0
    selected_promotion: int = 0
    selected_promotion_target: int = 0
    selected_venture: int = 0
    queue_cancellation: str = ""
    selected_queue_cancellation: int = 0
    marketing_tab: int = 0
    games_tab: int = 0
    modal: str = "main"
    title_screen: bool = False
    title_menu_index: int = 0
    title_message: str = ""
    settings_open: bool = False
    settings_resume_on_close: bool = False
    selected_setting_action: int = 0
    training_open: bool = False
    training_resume_on_close: bool = False
    selected_training_skill: int = 0
    new_game_step: int = 0
    team_tab: int = 0
    analysis_view: int = 0
    selected_stat: int = 0
    selected_sequel_choice: int = 0
    draft_title: str = ""
    title_roll: int = 0
    naming_game: bool = False
    sequel_game_id: int | None = None
    spinoff_franchise_id: int | None = None
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
        if not self.studio.competitors:
            seed_market(self)
        if self.studio.legacy_auto_jobs_cancelled:
            self.log(f"Removed {self.studio.legacy_auto_jobs_cancelled} legacy auto-accepted queued contract(s) because Auto Contracts is OFF.")
            self.studio.legacy_auto_jobs_cancelled = 0
        if not self.logs:
            self.logs = [
                f"{self.clock.current_date:%d %b %Y}: you open a bootstrapped indie studio with $75,000.",
                "Cash is runway. Payroll, software, insurance, tax, refunds, and store cuts are real.",
                "Start in the Hub for an overview. Tab cycles pages; G opens Game, J opens Jobs, and T opens Team.",
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


def format_by_name(name: str) -> dict:
    return next((item for item in GAME_FORMATS if item["name"] == name), GAME_FORMATS[0])


def creative_by_name(name: str) -> dict:
    return next((item for item in CREATIVE_DIRECTIONS if item["name"] == name), CREATIVE_DIRECTIONS[0])


def release_strategy_by_name(name: str) -> dict:
    return next((item for item in RELEASE_STRATEGIES if item["name"] == name), RELEASE_STRATEGIES[0])


def concept_focus(state: GameState) -> tuple[int, int, int, int]:
    primary = CREATIVE_DIRECTIONS[state.selected_creative_primary]["focus"]
    secondary = CREATIVE_DIRECTIONS[state.selected_creative_secondary]["focus"]
    raw = [round(primary[index] * 0.6 + secondary[index] * 0.4) for index in range(4)]
    raw[0] += 100 - sum(raw)
    return tuple(raw)


def team_research_skill(studio: Studio) -> float:
    researchers = [employee for employee in studio.team if employee.training_weeks_left == 0]
    if not researchers:
        return 20.0
    lead = max(effective_research(employee) for employee in researchers)
    support = sum(effective_research(employee) for employee in researchers) / len(researchers)
    return min(99.0, lead * 0.7 + support * 0.3)


def market_truth(state: GameState) -> dict:
    genre = GENRES[state.selected_genre]
    secondary_genre = GENRES[state.selected_secondary_genre]
    topic = TOPICS[state.selected_topic]
    secondary_topic = TOPICS[state.selected_secondary_topic]
    audience = AUDIENCES[state.selected_audience]
    game_format = GAME_FORMATS[state.selected_format]
    scope = SCOPES[state.selected_scope]
    primary_direction = CREATIVE_DIRECTIONS[state.selected_creative_primary]
    secondary_direction = CREATIVE_DIRECTIONS[state.selected_creative_secondary]
    strategy = RELEASE_STRATEGIES[state.selected_release_strategy]
    channel = CHANNELS[state.selected_channel]

    modern = {"Battle Royale", "Extraction Shooter", "Survivors-like", "Roguelike", "Roguelite", "Deckbuilder", "Automation", "Cozy Game", "Social Deduction", "Immersive Sim", "Soulslike", "Metroidvania"}
    demand = 1.12 if genre in modern else 1.0
    if secondary_genre != genre:
        demand += 0.08
    topic_hits = sum(
        candidate in GOOD_MATCHES[selected_genre]
        for selected_genre in {genre, secondary_genre}
        for candidate in {topic, secondary_topic}
    )
    topic_score = topic_hits / (len({genre, secondary_genre}) * len({topic, secondary_topic}))
    audience_matches = sum(candidate in audience["genres"] for candidate in {genre, secondary_genre})
    audience_fit = audience_matches > 0
    direction_market = primary_direction["market"] * 0.6 + secondary_direction["market"] * 0.4
    category_fit = platform_fit_values(genre, secondary_genre, channel["category"])
    seed = state.studio.seed + state.clock.week // 13 * 101 + sum(ord(char) for char in genre + secondary_genre)
    rng = random.Random(seed)
    primary_ideal = GENRE_PROFILES[genre]["priorities"]
    secondary_ideal = GENRE_PROFILES[secondary_genre]["priorities"]
    blend_distance = sum(abs(left - right) for left, right in zip(primary_ideal, secondary_ideal))
    blend_fit = 8 if genre == secondary_genre else max(-10, round(8 - blend_distance / 5))
    online_genres = {"Battle Royale", "Extraction Shooter", "Social Deduction", "Fighting Game", "Racing", "Sports Game", "First-Person Shooter", "Third-Person Shooter"}
    online_matches = sum(candidate in online_genres for candidate in {genre, secondary_genre})
    if game_format["name"] == "Offline solo":
        format_fit = -18 if online_matches == len({genre, secondary_genre}) else 4
    else:
        format_fit = 12 if online_matches else -10
    trend = rng.randint(-14, 14)
    score = round(
        42
        + (topic_score - 0.5) * 40
        + (16 if audience_matches == len({genre, secondary_genre}) else 7 if audience_fit else -14)
        + direction_market
        + strategy["market"]
        + category_fit
        + blend_fit
        + format_fit
        + trend
    )
    score = max(8, min(96, score))
    competitors = max(1, round(2 + demand * 3 + (3 if genre in modern else 0) + max(0, trend) / 4 + rng.uniform(-2, 2)))
    audience_size = round(
        42_000
        * demand
        * audience["market"]
        * game_format["market"]
        * scope["market"]
        * (0.65 + score / 100)
    )
    opportunity = max(1, round(audience_size / competitors))
    risk = round(
        scope["risk"]
        + game_format["risk"]
        + strategy["risk"]
        + primary_direction["risk"] * 0.6
        + secondary_direction["risk"] * 0.4
    )
    nominal_work = round(
        scope["work"]
        * game_format["work"]
        * strategy["work"]
        * (primary_direction["work"] * 0.6 + secondary_direction["work"] * 0.4)
    )
    overrun_ceiling = 1.18 + min(0.35, risk / 100)
    actual_work = round(nominal_work * rng.uniform(0.92, overrun_ceiling))
    return {
        "score": score,
        "audience": audience_size,
        "competitors": competitors,
        "opportunity": opportunity,
        "risk": risk,
        "topic_fit": topic_score,
        "audience_fit": audience_fit,
        "trend": trend,
        "work": actual_work,
        "nominal_work": nominal_work,
    }


def market_report(state: GameState) -> dict:
    truth = market_truth(state)
    research = team_research_skill(state.studio)
    # Early generalists can spot broad signals, but reliable forecasts require
    # deliberate research development rather than a second hire alone.
    confidence = max(0.20, min(0.85, 0.12 + (research / 100) ** 3 * 0.72))
    uncertainty = 1 - confidence
    concept_seed = (
        state.studio.seed
        + state.clock.week // 13 * 101
        + state.selected_genre * 503
        + state.selected_secondary_genre * 307
        + state.selected_topic * 17
        + state.selected_secondary_topic * 11
        + state.selected_audience * 71
        + state.selected_format * 43
        + state.selected_creative_primary * 29
        + state.selected_creative_secondary * 23
    )
    rng = random.Random(concept_seed + round(research) * 13)
    score_center = max(1, min(99, round(truth["score"] + rng.uniform(-14, 14) * uncertainty)))
    score_spread = max(3, round(19 * uncertainty))
    audience_center = round(truth["audience"] * (1 + rng.uniform(-0.55, 0.55) * uncertainty))
    audience_spread = 0.08 + uncertainty * 0.65
    rival_center = max(1, round(truth["competitors"] + rng.uniform(-5, 5) * uncertainty))
    rival_spread = max(1, round(5 * uncertainty))
    work_center = round(truth["work"] * (0.84 + confidence * 0.14 + rng.uniform(-0.18, 0.12) * uncertainty))
    work_spread = 0.06 + uncertainty * 0.42
    score_low, score_high = max(1, score_center - score_spread), min(99, score_center + score_spread)
    audience_low = max(1_000, int(round(audience_center * (1 - audience_spread), -3)))
    audience_high = max(audience_low, int(round(audience_center * (1 + audience_spread), -3)))
    competitors_low = max(1, rival_center - rival_spread)
    competitors_high = rival_center + rival_spread
    work_low = max(100, int(round(work_center * (1 - work_spread), -2)))
    work_high = max(work_low, int(round(work_center * (1 + work_spread), -2)))
    if score_high < 38:
        outlook = "Dangerous premise"
    elif score_low < 45 < score_high:
        outlook = "Highly uncertain"
    elif score_low >= 68:
        outlook = "Strong signals"
    elif score_low >= 52:
        outlook = "Promising signals"
    else:
        outlook = "Mixed signals"
    return {
        "score": score_center,
        "score_low": score_low,
        "score_high": score_high,
        "audience": audience_center,
        "audience_low": audience_low,
        "audience_high": audience_high,
        "competitors": rival_center,
        "competitors_low": competitors_low,
        "competitors_high": competitors_high,
        "opportunity": max(1, round(audience_center / rival_center)),
        "risk": truth["risk"],
        "topic_fit": truth["topic_fit"],
        "audience_fit": truth["audience_fit"],
        "work": work_center,
        "work_low": work_low,
        "work_high": work_high,
        "confidence": round(confidence * 100),
        "research": round(research),
        "outlook": outlook,
    }


def plan_requirements(state: GameState) -> list[str]:
    studio = state.studio
    scope = SCOPES[state.selected_scope]
    game_format = GAME_FORMATS[state.selected_format]
    requirements = []
    required_team = max(scope["team"], game_format["team"])
    required_rep = max(scope["rep"], game_format["rep"])
    if len(studio.team) < required_team:
        requirements.append(f"team {required_team} (have {len(studio.team)})")
    if studio.reputation < required_rep:
        requirements.append(f"reputation {required_rep} (have {studio.reputation:.0f})")
    if state.selected_release_strategy == 3 and state.selected_format == 0:
        requirements.append("an online game format")
    return requirements


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


def employee_modifiers(employee: Employee) -> dict:
    values = {"output": 1.0, "quality": 0.0, "defects": 1.0, "fatigue": 1.0, "learning": 1.0, "variance_low": 0.91, "variance_high": 1.08, "team_morale": 0.0, "research": 0}
    if employee.trait == "Methodical":
        values.update(output=0.95, defects=0.88)
    elif employee.trait == "Fast learner":
        values.update(learning=1.5, defects=1.06)
    elif employee.trait == "Collaborative":
        values.update(output=0.96, team_morale=0.12)
    elif employee.trait == "Night owl":
        values.update(output=1.08, fatigue=1.45)
    elif employee.trait == "Perfectionist":
        values.update(output=0.92, quality=6.0)
    elif employee.trait == "Pragmatic":
        values.update(quality=-1.0, variance_low=1.0, variance_high=1.0, research=2)
    elif employee.trait == "Inventive":
        values.update(quality=4.0, defects=1.05, variance_low=0.86, variance_high=1.14, research=3)
    elif employee.trait == "Resilient":
        values.update(output=0.97, fatigue=0.70)

    if employee.quirk == "Cautious":
        values["output"] *= 0.94
        values["defects"] *= 0.85
    elif employee.quirk == "Overcommitted":
        values["output"] *= 1.06
        values["fatigue"] += 0.65
    elif employee.quirk == "Independent":
        values["output"] *= 1.04
        values["team_morale"] -= 0.08
    elif employee.quirk == "Burst worker":
        values["variance_low"] = min(values["variance_low"], 0.78)
        values["variance_high"] = max(values["variance_high"], 1.20)
    elif employee.quirk == "Hasty":
        values["output"] *= 1.05
        values["defects"] *= 1.15
    elif employee.quirk == "Reserved":
        values["team_morale"] -= 0.04
        values["research"] += 6
    return values


def effective_research(employee: Employee) -> int:
    return max(1, min(99, employee.research + employee_modifiers(employee)["research"]))


def selected_roster_employee(state: GameState) -> Employee | None:
    employees = [employee for employee in state.studio.team if not employee.founder]
    if not employees:
        return next((employee for employee in state.studio.team if employee.founder), None)
    if state.selected_roster < 0:
        return next((employee for employee in state.studio.team if employee.founder), None)
    return employees[min(state.selected_roster, len(employees) - 1)]


def training_cost(employee: Employee, skill_name: str) -> int:
    attribute = skill_name.lower()
    current = getattr(employee, attribute)
    return round((900 + current * 32) / 250) * 250


def grant_employee_skill(state: GameState, employee: Employee, skill_name: str, amount: int, source: str) -> int:
    attribute = skill_name.lower()
    before = getattr(employee, attribute)
    gain = max(0, min(amount, 99 - before))
    if gain == 0:
        return 0
    setattr(employee, attribute, before + gain)
    raise_amount = 0
    if not employee.founder:
        raise_amount = round(gain * (500 + before * 12) / 500) * 500
        employee.annual_salary += raise_amount
    salary_text = f"; salary demand +${raise_amount:,}/year" if raise_amount else ""
    state.log(f"{employee.name} improved {skill_name} {before}->{before + gain} through {source}{salary_text}.")
    return gain


def grant_employee_experience(state: GameState, employee: Employee, skill_name: str, points: int, source: str) -> None:
    employee.experience += round(points * employee_modifiers(employee)["learning"])
    while employee.experience >= 100:
        employee.experience -= 100
        if skill_name not in EMPLOYEE_SKILLS:
            index = max(range(len(employee.all_skills)), key=lambda candidate: employee.all_skills[candidate])
            resolved_skill = EMPLOYEE_SKILLS[index]
        else:
            resolved_skill = skill_name
        grant_employee_skill(state, employee, resolved_skill, 1, source)


def start_employee_training(state: GameState, skill_index: int | None = None) -> bool:
    employee = selected_roster_employee(state)
    if employee is None:
        state.log("Hire an employee before booking training.")
        return False
    if employee.training_weeks_left:
        state.log(f"{employee.name} is already studying {employee.training_skill} for {employee.training_weeks_left} more weeks.")
        return False
    index = state.selected_training_skill if skill_index is None else skill_index
    skill_name = EMPLOYEE_SKILLS[index]
    if getattr(employee, skill_name.lower()) >= 99:
        state.log(f"{employee.name} has already mastered {skill_name}.")
        return False
    cost = training_cost(employee, skill_name)
    if state.studio.cash < cost + monthly_fixed_cost(state.studio):
        state.log(f"Cannot fund {skill_name} training for {employee.name} without risking next month's bills.")
        return False
    add_expense(state.studio, cost, "Training")
    employee.training_skill = skill_name
    employee.training_weeks_left = 4
    state.log(f"Sent {employee.name} to four weeks of {skill_name} training for ${cost:,}; they are unavailable during the course.")
    return True


def process_employee_training(state: GameState, week_end: bool = True) -> None:
    if not week_end:
        return
    for employee in state.studio.team:
        if employee.training_weeks_left <= 0:
            continue
        employee.training_weeks_left -= 1
        employee.weeks_employed += 1
        if employee.training_weeks_left == 0:
            skill_name = employee.training_skill
            grant_employee_skill(state, employee, skill_name, 4, "professional training")
            employee.training_skill = ""
            employee.fatigue = max(0, employee.fatigue - 5)


def generate_candidate(studio: Studio, rng: random.Random) -> Employee:
    role = rng.choice(tuple(ROLE_PROFILES))
    base = ROLE_PROFILES[role]
    seniority = rng.choices(("Junior", "Mid-level", "Senior"), weights=(35, 45, 20))[0]
    modifier = {"Junior": -14, "Mid-level": 0, "Senior": 13}[seniority]
    skills = [max(18, min(96, value + modifier + rng.randint(-10, 10))) for value in base]
    research = max(18, min(96, ROLE_RESEARCH[role] + modifier + rng.randint(-10, 10)))
    annual = round((34_000 + (sum(skills) + research) * 100 + (12_000 if seniority == "Senior" else 0)) / 1_000) * 1_000
    employee = Employee(
        studio.next_employee_id,
        f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
        f"{seniority} {role}",
        *skills,
        annual,
        research=research,
        morale=float(rng.randint(62, 86)),
        fatigue=float(rng.randint(2, 12)),
        trait=rng.choice(tuple(TRAITS)),
        quirk=rng.choice(tuple(QUIRKS)),
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


def infer_legacy_game_bugs(game: ReleasedGame) -> None:
    game.actual_bugs = max(1.0, (75 - game.score) * 0.22 + 1.5)
    exposure = min(0.92, 0.25 + math.log10(max(1, game.units_sold) + 1) * 0.13)
    game.known_bugs = game.actual_bugs * exposure
    game.reported_bug_count = game.known_bug_count


def sale_for_game(studio: Studio, game_id: int) -> ActiveSale | None:
    return next((sale for sale in studio.active_sales if sale.game_id == game_id), None)


def update_focus_by_name(name: str) -> dict:
    return next((focus for focus in UPDATE_FOCUSES if focus["name"] == name), UPDATE_FOCUSES[0])


def update_size_by_name(name: str) -> dict:
    return next((size for size in UPDATE_SIZES if size["name"] == name), UPDATE_SIZES[1])


def team_speed_factor(workers: int) -> float:
    """Coordination overhead multiplier applied to a team's summed output.

    No studio finishes a game in weeks just because it has many developers:
    total speed flattens toward a 2x cap, so fifteen people ship at most
    twice as fast as one. What headcount really adds is content, quality —
    and, through communication overhead, more defects (see develop_project).
    """
    if workers <= 1:
        return 1.0
    return min(2.0, workers ** 0.35) / workers


def update_weekly_output(studio: Studio, game_or_focus: ReleasedGame | str) -> float:
    focus_name = game_or_focus.update_focus if isinstance(game_or_focus, ReleasedGame) else game_or_focus
    focus = update_focus_by_name(focus_name)
    skill_index = {"Design": 0, "Art": 1, "Audio": 2, "Code": 3}.get(focus["skill"])
    output = 0.0
    workers = 0
    for employee in studio.team:
        if employee.training_weeks_left:
            continue
        workers += 1
        skill = sum(employee.skills) / 4 if skill_index is None else employee.skills[skill_index]
        availability = max(0.35, employee.morale / 100) * max(0.35, 1 - employee.fatigue / 130)
        output += skill * availability * employee_modifiers(employee)["output"] * 0.16
    return max(1.0, output * team_speed_factor(workers))


def bump_version(version: str, size_name: str) -> str:
    try:
        major, minor, patch = (int(part) for part in version.split("."))
    except (AttributeError, TypeError, ValueError):
        major, minor, patch = 1, 0, 0
    delta = update_size_by_name(size_name)["version"]
    patch += delta[2]
    minor += delta[1] + patch // 100
    patch %= 100
    major += delta[0] + minor // 100
    minor %= 100
    return f"{major}.{minor:02d}.{patch:02d}"


def planned_update_version(studio: Studio, game: ReleasedGame, size_name: str) -> str:
    version = game.version
    jobs = ([studio.active_update] if studio.active_update else []) + studio.update_queue
    for job in jobs:
        if job.game_id == game.game_id:
            version = job.target_version
    return bump_version(version, size_name)


def estimated_update_weeks(studio: Studio, game: ReleasedGame) -> int:
    size = update_size_by_name(game.update_size)
    build_weeks = math.ceil(size["work"] / update_weekly_output(studio, game.update_focus))
    bug_weeks = math.ceil(size["bugs"] / update_weekly_output(studio, "Bug fixes"))
    return max(1, build_weeks + bug_weeks)


def estimated_update_job_weeks(studio: Studio, job: UpdateJob) -> int:
    build_remaining = max(0, job.required_work - job.work_done)
    bugs_remaining = max(0, job.bugs_found - job.bugs_fixed)
    build_weeks = math.ceil(build_remaining / update_weekly_output(studio, job.focus))
    bug_weeks = math.ceil(bugs_remaining / update_weekly_output(studio, "Bug fixes"))
    return build_weeks + bug_weeks


def estimated_update_delivery_weeks(studio: Studio, game: ReleasedGame) -> int:
    waiting = sum(
        estimated_update_job_weeks(studio, job)
        for job in ([studio.active_update] if studio.active_update else []) + studio.update_queue
    )
    return waiting + estimated_update_weeks(studio, game)


def game_total_cost(game: ReleasedGame) -> float:
    return game.production_cost + game.labor_cost + game.marketing_cost + game.post_launch_cost


def game_profit(game: ReleasedGame) -> float:
    return game.net_revenue - game_total_cost(game)


def clamp_player_counts(game: ReleasedGame) -> None:
    owners = max(0, game.units_sold)
    game.active_players = max(0.0, min(game.active_players, float(owners)))
    game.monthly_players = max(0, min(game.monthly_players, owners))
    game.peak_monthly_players = max(game.monthly_players, min(game.peak_monthly_players, owners))


def marketing_team_load(studio: Studio) -> float:
    return min(0.45, studio.active_promotions[0].team_share if studio.active_promotions else 0.0)


def update_team_load(studio: Studio) -> float:
    if studio.active_update is None:
        return 0.0
    return update_size_by_name(studio.active_update.size)["team"]


def live_title_count(studio: Studio) -> int:
    """Live games that consume live-ops capacity; the pre-studio
    back-catalogue titles are maintenance-free and don't count."""
    historical = {game.game_id for game in studio.catalog if game.release_date == "Historical"}
    return sum(1 for sale in studio.active_sales if sale.game_id not in historical)


def capacity_drains(studio: Studio) -> list[str]:
    """Human-readable list of everything currently slowing original work.

    Read-only presentation helper: mirrors the multipliers in
    :func:`projected_weekly_output` so screens can show *why* capacity is
    reduced instead of just that it is.
    """
    drains = []
    contract = studio.contract
    if contract:
        progress = 0 if contract.required_work <= 0 else contract.work_done / contract.required_work
        drains.append(f"JOB {contract.client} -45% ({progress:.0%} done, due {contract.weeks_left}w)")
    if marketing_team_load(studio) > 0:
        drains.append(f"promotions {marketing_team_load(studio):.0%}")
    if update_team_load(studio) > 0:
        drains.append(f"updates {update_team_load(studio):.0%}")
    training = sum(1 for employee in studio.team if employee.training_weeks_left)
    if training:
        drains.append(f"{training} in training")
    live_titles = live_title_count(studio)
    if live_titles:
        support_load = min(0.30, 0.04 * live_titles)
        noun = "title" if live_titles == 1 else "titles"
        drains.append(f"supporting {live_titles} live {noun} -{support_load:.0%}")
    return drains


def prepare_sequel(state: GameState, game: ReleasedGame) -> None:
    state.selected_genre = GENRES.index(game.genre)
    state.selected_topic = TOPICS.index(game.topic)
    state.selected_secondary_genre = GENRES.index(game.secondary_genre) if game.secondary_genre in GENRES else state.selected_genre
    state.selected_secondary_topic = TOPICS.index(game.secondary_topic) if game.secondary_topic in TOPICS else state.selected_topic
    state.selected_channel = next((index for index, channel in enumerate(CHANNELS) if channel["name"] == game.channel), 0)
    state.selected_scope = next((index for index, item in enumerate(SCOPES) if item["name"] == game.scope), state.selected_scope)
    state.selected_audience = next((index for index, item in enumerate(AUDIENCES) if item["name"] == game.target_audience), 0)
    state.selected_format = next((index for index, item in enumerate(GAME_FORMATS) if item["name"] == game.game_format), 0)
    state.selected_creative_primary = next((index for index, item in enumerate(CREATIVE_DIRECTIONS) if item["name"] == game.creative_primary), 0)
    state.selected_creative_secondary = next((index for index, item in enumerate(CREATIVE_DIRECTIONS) if item["name"] == game.creative_secondary), 3)
    state.selected_release_strategy = next((index for index, item in enumerate(RELEASE_STRATEGIES) if item["name"] == game.release_strategy), 0)
    state.sequel_game_id = game.game_id
    base_title = game.title
    if game.generation > 1:
        current_suffix = f" {roman_number(game.generation)}"
        if base_title.endswith(current_suffix):
            base_title = base_title[: -len(current_suffix)]
    state.draft_title = f"{base_title} {roman_number(game.generation + 1)}"
    state.modal = "new_game"
    state.new_game_step = 2
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
        game = ReleasedGame(
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
        infer_legacy_game_bugs(game)
        studio.catalog.append(game)
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
    workers = 0
    for employee in studio.team:
        if employee.training_weeks_left:
            continue
        workers += 1
        weighted_skill = sum(skill * percent for skill, percent in zip(employee.skills, focus)) / 100
        availability = max(0.35, employee.morale / 100) * max(0.35, 1 - employee.fatigue / 130)
        output += weighted_skill * availability * employee_modifiers(employee)["output"]
    output *= team_speed_factor(workers)
    if "hardware" in studio.upgrades:
        output *= 1.10
    if studio.contract:
        output *= 0.55
    output *= max(0.70, 1 - 0.04 * live_title_count(studio))
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
    game_format = GAME_FORMATS[state.selected_format]
    primary_direction = CREATIVE_DIRECTIONS[state.selected_creative_primary]
    secondary_direction = CREATIVE_DIRECTIONS[state.selected_creative_secondary]
    strategy = RELEASE_STRATEGIES[state.selected_release_strategy]
    requirements = plan_requirements(state)
    if requirements:
        state.log(f"Plan not production-ready: requires {', '.join(requirements)}.")
        return False
    cost = scope["setup"] + channel["fee"] + marketing["cost"] + game_format["setup"] + strategy["setup"]
    if studio.cash < cost + monthly_fixed_cost(studio):
        state.log(f"Plan rejected: ${cost:,} setup would leave less than one month of runway.")
        return False
    focus = concept_focus(state)
    state.focus = list(focus)
    output = projected_weekly_output(studio, focus)
    truth = market_truth(state)
    report = market_report(state)
    total_work = truth["work"]
    planned_weeks = max(4, round(report["work"] / output))
    topic = TOPICS[state.selected_topic]
    genre = GENRES[state.selected_genre]
    secondary_topic = TOPICS[state.selected_secondary_topic]
    secondary_genre = GENRES[state.selected_secondary_genre]
    audience = AUDIENCES[state.selected_audience]
    event_rng = random.Random(studio.seed + state.clock.week * 409 + state.selected_scope * 37 + state.selected_genre * 19)
    if state.selected_scope <= 1:
        event_count = 1 if event_rng.random() < 0.45 else 0
    elif state.selected_scope <= 3:
        event_count = 1
    else:
        event_count = 2 if event_rng.random() < 0.65 else 1
    scheduled_decisions = sorted(event_rng.sample(range(len(PRODUCTION_DECISIONS)), event_count))
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
        price=round(scope["price"] * audience["price"] * strategy["price"], 2),
        marketing_name=marketing["name"],
        marketing_budget=marketing["cost"],
        focus=focus,
        total_work=float(total_work),
        planned_weeks=planned_weeks,
        cash_cost=cost,
        secondary_genre=secondary_genre,
        secondary_topic=secondary_topic,
        target_audience=audience["name"],
        game_format=game_format["name"],
        creative_primary=primary_direction["name"],
        creative_secondary=secondary_direction["name"],
        release_strategy=strategy["name"],
        addressable_audience=truth["audience"],
        competitors=truth["competitors"],
        market_score=truth["score"],
        forecast_score_low=report["score_low"],
        forecast_score_high=report["score_high"],
        forecast_audience_low=report["audience_low"],
        forecast_audience_high=report["audience_high"],
        forecast_competitors_low=report["competitors_low"],
        forecast_competitors_high=report["competitors_high"],
        forecast_confidence=report["confidence"],
        hosting_rate=game_format["hosting"],
        scheduled_decisions=scheduled_decisions,
        sequel_of=previous_game.game_id if previous_game else None,
        generation=generation,
        franchise_id=state.spinoff_franchise_id if state.spinoff_franchise_id else (previous_game.franchise_id if previous_game else None),
        hype=5 + marketing["boost"] / 25,
        production_cost=scope["setup"] + channel["fee"] + game_format["setup"] + strategy["setup"],
        marketing_cost=marketing["cost"],
        cost_history_complete=True,
    )
    add_expense(studio, scope["setup"] + game_format["setup"] + strategy["setup"], "Development")
    add_expense(studio, channel["fee"], "Store fees")
    add_expense(studio, marketing["cost"], "Marketing")
    studio.current_project = project
    state.modal = "games"
    state.new_game_step = 0
    state.naming_game = False
    state.sequel_game_id = None
    state.spinoff_franchise_id = None
    state.title_roll += 1
    refresh_draft_title(state)
    mix = genre if secondary_genre == genre else f"{genre} / {secondary_genre}"
    state.log(f"Greenlit {project.title}, a {scope['name'].lower()} {mix} game for {audience['name']}.")
    state.log(f"Paid ${cost:,}. Research forecast: {report['audience_low']:,}-{report['audience_high']:,} interested, {report['competitors_low']}-{report['competitors_high']} rivals, about {planned_weeks} weeks.")
    runway_weeks = studio.cash / max(1, monthly_fixed_cost(studio)) * 4.33
    forecast_high_weeks = max(4, round(report["work_high"] / output))
    if runway_weeks < forecast_high_weeks:
        state.log(f"Runway warning: roughly {runway_weeks:.0f} funded weeks remain against a workload forecast reaching {forecast_high_weeks} weeks; overruns could kill the studio.")
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
    employee = selected_roster_employee(state)
    if employee is None or employee.founder:
        state.log("The founder cannot be dismissed.")
        return False
    if not removable:
        state.log("There are no employees to dismiss.")
        return False
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
    workers = 0
    for employee in studio.team:
        if employee.training_weeks_left:
            continue
        workers += 1
        skill = sum(employee.skills) / 4 if skill_index is None else employee.skills[skill_index]
        availability = max(0.35, employee.morale / 100) * max(0.35, 1 - employee.fatigue / 130)
        output += skill * availability * employee_modifiers(employee)["output"] * 0.55
    if "hardware" in studio.upgrades:
        output *= 1.10
    return max(1.0, output * team_speed_factor(workers))


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


def platform_fit_values(genre: str, secondary_genre: str, category: str) -> int:
    category_preferences = {
        "PC": {"Strategy", "Real-Time Strategy", "Role-Playing Game", "Simulation", "Economic Simulation", "Building Game", "Adventure", "Visual Novel", "Extraction Shooter", "Roguelike", "Roguelite", "Deckbuilder", "Automation", "Immersive Sim", "Survivors-like"},
        "Console": {"Action", "Platformer", "Racing", "Sports Game", "Fighting Game", "Third-Person Shooter", "First-Person Shooter", "Battle Royale", "Soulslike", "Metroidvania"},
        "Handheld": {"Puzzle Game", "Skill Game", "Platformer", "Racing", "Visual Novel", "Cozy Game", "Roguelite", "Deckbuilder", "Metroidvania", "Survivors-like"},
        "Mobile": {"Puzzle Game", "Skill Game", "Simulation", "Visual Novel", "Economic Simulation", "Cozy Game", "Survivors-like", "Social Deduction"},
    }
    matches = sum(candidate in category_preferences[category] for candidate in {genre, secondary_genre})
    return 7 if matches == len({genre, secondary_genre}) else 3 if matches else -3


def platform_fit(project: Project) -> int:
    return platform_fit_values(project.genre, project.secondary_genre or project.genre, project.category)


def finish_project(state: GameState) -> None:
    studio = state.studio
    project = studio.current_project
    if project is None:
        return
    average_skill = project.quality_points / max(1, project.work_done)
    match = 8 if project.topic in GOOD_MATCHES[project.genre] else -5
    primary_ideal = GENRE_PROFILES[project.genre]["priorities"]
    secondary_ideal = GENRE_PROFILES[project.secondary_genre or project.genre]["priorities"]
    focus_ideal = tuple(round((primary + secondary) / 2) for primary, secondary in zip(primary_ideal, secondary_ideal))
    focus_distance = sum(abs(actual - ideal) for actual, ideal in zip(project.focus, focus_ideal))
    focus_bonus = max(-9, 8 - focus_distance // 6)
    defect_rate = project.defects / max(1, project.work_done)
    defect_penalty = min(24, round(defect_rate * 170))
    scope_risk = scope_by_name(project.scope)["risk"] + format_by_name(project.game_format)["risk"]
    direction_bonus = round((creative_by_name(project.creative_primary)["quality"] + creative_by_name(project.creative_secondary)["quality"]) / 2)
    tools_bonus = 4 if "tools" in studio.upgrades else 0
    content_bonus = min(12, max(0, len(studio.team) - 1))
    previous_game = next((game for game in studio.catalog if game.game_id == project.sequel_of), None)
    sequel_quality = 0 if previous_game is None else round((previous_game.score - 50) / 8)
    sequel_fatigue = max(0, project.generation - 3) * 2
    market_quality = round((project.market_score - 50) / 10)
    score = max(24, min(94, round(22 + average_skill * 0.66 + match + focus_bonus + platform_fit(project) + direction_bonus + market_quality + tools_bonus + content_bonus + sequel_quality - sequel_fatigue - defect_penalty - scope_risk)))
    refund_rate = max(0.03, min(0.24, 0.16 - score / 1_000 + defect_rate * 0.35))
    marketing = marketing_by_name(project.marketing_name)
    genre_audience = studio.genre_fans.get(project.genre, 0)
    sequel_audience = genre_audience * 0.45 if project.sequel_of else genre_audience * 0.10
    discoverability = 75 + marketing["boost"] + project.hype * 8 + studio.followers * 0.12 + studio.reputation * 3 + sequel_audience
    quality_multiplier = max(0.12, (score / 72) ** 3)
    scope_multiplier = scope_by_name(project.scope)["market"] * 1.7
    market_multiplier = max(0.4, project.market_score / 60) * max(0.55, 1 - project.competitors * 0.025) * max(0.6, 1 - genre_release_pressure(studio, project.genre) * 0.12)
    units = max(12, round(discoverability * quality_multiplier * scope_multiplier * project.reach * market_multiplier))
    units = min(max(12, round(project.addressable_audience * 0.18)), units) if project.addressable_audience else units
    evergreen_units = max(1, round((score / 100) ** 4 * scope_multiplier * 10 + genre_audience / 800))
    game_id = studio.next_game_id
    studio.next_game_id += 1
    known_bugs = min(project.known_defects, max(0, project.defects - 0.01))
    rating_rng = random.Random(studio.seed + game_id * 37 + state.clock.week)
    press_rating = max(20.0, min(98.0, score + rating_rng.uniform(-5, 4)))
    user_rating = max(15.0, min(99.0, score + rating_rng.uniform(-4, 6) - math.floor(known_bugs) * 0.8))
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
        active_players=0.0,
        monthly_players=0,
        peak_monthly_players=0,
        production_cost=project.production_cost,
        labor_cost=project.labor_cost,
        marketing_cost=project.marketing_cost,
        cost_history_complete=project.cost_history_complete,
        actual_bugs=project.defects,
        known_bugs=known_bugs,
        reported_bug_count=math.floor(known_bugs),
        scope=project.scope,
        price=project.price,
        secondary_genre=project.secondary_genre,
        secondary_topic=project.secondary_topic,
        target_audience=project.target_audience,
        game_format=project.game_format,
        creative_primary=project.creative_primary,
        creative_secondary=project.creative_secondary,
        release_strategy=project.release_strategy,
        addressable_audience=project.addressable_audience,
        competitors=project.competitors,
        market_score=project.market_score,
        hosting_rate=project.hosting_rate,
        production_decisions=list(project.decisions_made),
        user_rating=round(user_rating, 1),
        press_rating=round(press_rating, 1),
    )
    studio.catalog.append(game)
    ensure_franchise_for_release(state, project, game, units, score)
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
    launch_followers = max(5, round(units * (0.05 + (score / 100) ** 2 * 0.4)))
    studio.followers += launch_followers
    studio.genre_fans[project.genre] = studio.genre_fans.get(project.genre, 0) + launch_followers
    studio.topic_fans[project.topic] = studio.topic_fans.get(project.topic, 0) + launch_followers
    if project.secondary_genre and project.secondary_genre != project.genre:
        studio.genre_fans[project.secondary_genre] = studio.genre_fans.get(project.secondary_genre, 0) + launch_followers // 2
    if project.secondary_topic and project.secondary_topic != project.topic:
        studio.topic_fans[project.secondary_topic] = studio.topic_fans.get(project.secondary_topic, 0) + launch_followers // 2
    state.log(f"Released {project.title} after {project.weeks} weeks: {score}/100, {refund_rate:.0%} expected refunds, {math.floor(known_bugs)} known bugs.")
    state.log(f"The store predicts {units:,} first-week units. You keep {(1 - project.platform_cut):.0%} before refunds.")


def resolve_project_decision(state: GameState, option_index: int, automatic: bool = False) -> bool:
    project = state.studio.current_project
    if project is None or project.pending_decision is None:
        return False
    decision = PRODUCTION_DECISIONS[project.pending_decision]
    option = decision["options"][option_index]
    remaining = max(0, project.total_work - project.work_done)
    project.total_work += remaining * (option.get("work", 1.0) - 1)
    project.quality_points += project.work_done * option.get("quality", 0)
    project.defects = project.defects * option.get("defect_multiplier", 1.0) + option.get("defects", 0)
    project.known_defects = min(project.known_defects, project.defects)
    project.hype = max(0, min(200, project.hype + option.get("hype", 0)))
    project.market_score = max(10, min(100, project.market_score + option.get("market", 0)))
    fatigue = option.get("fatigue", 0)
    for employee in state.studio.team:
        employee.fatigue = min(100, employee.fatigue + fatigue)
    project.decisions_made.append(f"{decision['title']}: {option['name']}")
    project.next_decision += 1
    project.pending_decision = None
    state.selected_project_decision = 0
    if not automatic and project.decision_resume_on_close and state.time_speed_index == 0:
        state.time_speed_index = max(1, state.resume_speed_index)
    project.decision_resume_on_close = False
    source = "Auto-selected" if automatic else "Committed to"
    state.log(f"{source} '{option['name']}' at {decision['title'].lower()} for {project.title}. {option['effect']}.")
    return True


def develop_project(state: GameState, day_number: int = 0, week_end: bool = True, workday: bool = True) -> None:
    studio = state.studio
    project = studio.current_project
    if project is None:
        return
    if project.pending_decision is not None:
        if day_number < project.pending_day + 7:
            return
        resolve_project_decision(state, 0, automatic=True)
    weekly_salary = sum(employee.annual_salary / 52 for employee in studio.team)
    weekly_burden = sum(employee.annual_salary / 52 for employee in studio.team if not employee.founder) * 0.13
    project.labor_cost += (weekly_salary + weekly_burden) / 7
    project.hype *= 0.985 ** (1 / 7)
    if not workday:
        for employee in studio.team:
            employee.fatigue = max(0, employee.fatigue - 3)
            if week_end:
                employee.weeks_employed += 1
                if employee.week_output > 0:
                    experience_gain = max(1, round(employee.week_output / 25))
                    grant_employee_experience(state, employee, "Generalist", experience_gain, "project experience")
                    employee.week_output = 0.0
        if week_end:
            project.weeks += 1
        return
    while (
        project.next_decision < len(project.scheduled_decisions)
        and project.progress > PRODUCTION_DECISIONS[project.scheduled_decisions[project.next_decision]]["threshold"] + 0.02
    ):
        decision = PRODUCTION_DECISIONS[project.scheduled_decisions[project.next_decision]]
        project.decisions_made.append(f"{decision['title']}: inherited production plan")
        project.next_decision += 1
    rng = random.Random(studio.seed + day_number * 7919)
    total_output = 0.0
    quality = 0.0
    defect_factor = 1.0
    contributors = 0
    for employee in studio.team:
        if employee.training_weeks_left:
            continue
        contributors += 1
        modifiers = employee_modifiers(employee)
        weighted = sum(skill * percent for skill, percent in zip(employee.skills, project.focus)) / 100
        availability = max(0.35, employee.morale / 100) * max(0.35, 1 - employee.fatigue / 130)
        variance = rng.uniform(modifiers["variance_low"], modifiers["variance_high"])
        personal_output = weighted * availability * variance * modifiers["output"] / 5
        weighted += modifiers["quality"]
        defect_factor *= modifiers["defects"]
        if modifiers["team_morale"]:
            for teammate in studio.team:
                if teammate is not employee:
                    teammate.morale = max(0, min(100, teammate.morale + modifiers["team_morale"] / 5))
        total_output += personal_output
        quality += personal_output * weighted
        employee.week_output += personal_output
        if week_end:
            employee.weeks_employed += 1
            experience_gain = max(1, round(employee.week_output / 25))
            grant_employee_experience(state, employee, "Generalist", experience_gain, "project experience")
            employee.week_output = 0.0
        fatigue_gain = ((2.5 if studio.contract else 1.2) / 5) * modifiers["fatigue"]
        employee.fatigue = min(100, employee.fatigue + fatigue_gain)
    speed_factor = team_speed_factor(contributors)
    total_output *= speed_factor
    quality *= speed_factor
    if "hardware" in studio.upgrades:
        total_output *= 1.10
    if studio.contract:
        total_output *= 0.55
        quality *= 0.55
    support_factor = max(0.70, 1 - 0.04 * live_title_count(studio))
    total_output *= support_factor
    quality *= support_factor
    operations_factor = max(0.25, 1 - marketing_team_load(studio) - update_team_load(studio))
    total_output *= operations_factor
    quality *= operations_factor
    uncapped_output = total_output
    bug_fixing = project.bug_work > 0
    if bug_fixing:
        total_output = min(total_output, project.bug_work - project.bug_work_done)
        quality = 0.0
    else:
        total_output = min(total_output, project.total_work - project.work_done)
        if project.next_decision < len(project.scheduled_decisions):
            gate = PRODUCTION_DECISIONS[project.scheduled_decisions[project.next_decision]]
            gate_work = project.total_work * gate["threshold"]
            total_output = min(total_output, max(0, gate_work - project.work_done))
    quality *= total_output / max(1, uncapped_output)
    code_skill = sum(employee.code for employee in studio.team) / len(studio.team)
    if contributors:
        defect_factor = defect_factor ** (1 / contributors)
    defect_factor *= 0.75 if "qa" in studio.upgrades else 1.0
    defect_factor *= 1 + 0.07 * max(0, contributors - 1)
    if bug_fixing:
        project.bug_work_done += total_output
        fixed = min(project.known_defects, total_output / BUG_FIX_WORK_PER_DEFECT)
        project.defects = max(0.0, project.defects - fixed)
        project.known_defects = max(0.0, project.known_defects - fixed)
    else:
        project.work_done += total_output
        project.quality_points += quality
        project.defects += total_output * max(0.015, (0.13 - code_skill / 900)) * defect_factor
    daily_fix = min(project.known_defects, project.known_defects * 0.012 * code_skill / 55)
    project.defects = max(0.0, project.defects - daily_fix)
    project.known_defects = max(0.0, project.known_defects - daily_fix)
    if bug_fixing:
        discovery_rate = 0.50
    elif project.progress < 0.30:
        discovery_rate = 0.04
    elif project.progress < 0.72:
        discovery_rate = 0.09
    elif project.progress < 0.90:
        discovery_rate = 0.18
    else:
        discovery_rate = 0.32
    if "qa" in studio.upgrades:
        discovery_rate *= 1.25
    undiscovered = max(0, project.defects - project.known_defects)
    project.known_defects = min(project.defects * 0.98, project.known_defects + undiscovered * discovery_rate / 7)
    if week_end:
        project.weeks += 1
    if project.next_decision < len(project.scheduled_decisions):
        event_index = project.scheduled_decisions[project.next_decision]
        gate = PRODUCTION_DECISIONS[event_index]
        if project.progress >= gate["threshold"] - 0.0001:
            project.pending_decision = event_index
            project.pending_day = day_number
            state.selected_project_decision = 0
            project.decision_resume_on_close = state.time_speed_index != 0
            if state.time_speed_index:
                state.resume_speed_index = state.time_speed_index
                state.time_speed_index = 0
            state.log(f"Production paused for {project.title}: {gate['title']} requires a decision.")
            return
    if project.bug_work > 0:
        if project.bug_work_done >= project.bug_work - 0.01:
            finish_project(state)
    elif project.work_done >= project.total_work - 0.01:
        if project.defects > 0.5:
            project.bug_work = project.defects * BUG_FIX_WORK_PER_DEFECT
            state.log(f"{project.title} entered bug fixing: {project.defects:.0f} defects from development must be cleared before release.")
        else:
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
    queued = Promotion(
        studio.next_promotion_id,
        promotion["name"],
        game_id,
        target_title,
        promotion["weeks"],
        promotion["weeks"],
        float(promotion["hype"]),
        promotion["team"],
        promotion["cost"],
    )
    was_idle = not studio.active_promotions
    studio.active_promotions.append(queued)
    studio.next_promotion_id += 1
    status = "Started" if was_idle else "Queued"
    state.log(f"{status} {promotion['name']} for {target_title}: ${promotion['cost']:,}, {promotion['weeks']} weeks, +{promotion['hype']} potential hype.")
    return True


def cancel_queued_promotion(state: GameState, index: int | None = None) -> bool:
    waiting = state.studio.active_promotions[1:]
    if not waiting:
        state.log("There are no waiting promotions to cancel; the active promotion must finish.")
        return False
    selected = min(state.selected_queue_cancellation if index is None else index, len(waiting) - 1)
    promotion = waiting[selected]
    cost = promotion.cost or next((item["cost"] for item in PROMOTIONS if item["name"] == promotion.name), 0)
    refund = round(cost * 0.80)
    state.studio.active_promotions.remove(promotion)
    add_revenue(state.studio, refund, "Promotion refunds")
    if promotion.game_id == 0 and state.studio.current_project:
        state.studio.current_project.marketing_cost = max(0, state.studio.current_project.marketing_cost - refund)
    elif promotion.game_id:
        game = game_by_id(state.studio, promotion.game_id)
        if game:
            game.marketing_cost = max(0, game.marketing_cost - refund)
    loss = cost - refund
    state.selected_queue_cancellation = min(selected, max(0, len(waiting) - 2))
    state.log(f"Cancelled queued {promotion.name} for {promotion.target_title}; recovered ${refund:,} and lost ${loss:,} in committed costs.")
    return True


def process_promotions(state: GameState, week_end: bool = True) -> None:
    if not state.studio.active_promotions:
        return
    promotion = state.studio.active_promotions[0]
    weekly_hype = promotion.hype_total / promotion.total_weeks
    hype_gain = weekly_hype / 7
    if promotion.game_id == 0 and state.studio.current_project:
        state.studio.current_project.hype = min(200, state.studio.current_project.hype + hype_gain)
    else:
        game = game_by_id(state.studio, promotion.game_id)
        if game:
            game.hype = min(200, game.hype + hype_gain)
            if week_end:
                sale = sale_for_game(state.studio, game.game_id)
                if sale:
                    sale.weekly_units += max(1, round(weekly_hype / 4))
    if not week_end:
        return
    promotion.weeks_left -= 1
    if promotion.weeks_left <= 0:
        state.studio.active_promotions.pop(0)
        state.log(f"{promotion.name} for {promotion.target_title} finished.")
        if state.studio.active_promotions:
            next_promotion = state.studio.active_promotions[0]
            state.log(f"Started queued {next_promotion.name} for {next_promotion.target_title}.")


def cycle_game_update_focus(state: GameState, game_id: int, delta: int = 1) -> str | None:
    game = game_by_id(state.studio, game_id)
    if game is None:
        return None
    index = next((index for index, focus in enumerate(UPDATE_FOCUSES) if focus["name"] == game.update_focus), 0)
    game.update_focus = UPDATE_FOCUSES[(index + delta) % len(UPDATE_FOCUSES)]["name"]
    state.log(f"{game.title} planned update area changed to {game.update_focus}.")
    return game.update_focus


def cycle_game_update_size(state: GameState, game_id: int, delta: int = 1) -> str | None:
    game = game_by_id(state.studio, game_id)
    if game is None:
        return None
    index = next((index for index, size in enumerate(UPDATE_SIZES) if size["name"] == game.update_size), 0)
    game.update_size = UPDATE_SIZES[(index + delta) % len(UPDATE_SIZES)]["name"]
    state.log(f"{game.title} planned update scope changed to {game.update_size}.")
    return game.update_size


def start_next_update(state: GameState) -> None:
    studio = state.studio
    while studio.active_update is None and studio.update_queue:
        job = studio.update_queue.pop(0)
        if game_by_id(studio, job.game_id) is None:
            state.log(f"Cancelled queued update for missing game {job.game_title}.")
            continue
        studio.active_update = job
        state.log(f"Started {job.size} {job.focus} update for {job.game_title}; target v{job.target_version}.")


def queue_game_update(state: GameState, game_id: int) -> bool:
    studio = state.studio
    game = game_by_id(studio, game_id)
    if game is None:
        return False
    size = update_size_by_name(game.update_size)
    job = UpdateJob(
        studio.next_update_id,
        game.game_id,
        game.title,
        game.update_focus,
        game.update_size,
        planned_update_version(studio, game, game.update_size),
        float(size["work"]),
        float(size["bugs"]),
    )
    studio.next_update_id += 1
    studio.update_queue.append(job)
    state.log(f"Queued {job.size} {job.focus} update for {game.title}; planned v{job.target_version}.")
    start_next_update(state)
    return True


def rebuild_queued_update_versions(studio: Studio) -> None:
    versions = {game.game_id: game.version for game in studio.catalog}
    if studio.active_update:
        versions[studio.active_update.game_id] = studio.active_update.target_version
    for job in studio.update_queue:
        base = versions.get(job.game_id, "1.00.00")
        job.target_version = bump_version(base, job.size)
        versions[job.game_id] = job.target_version


def cancel_queued_update(state: GameState, index: int | None = None) -> bool:
    queue = state.studio.update_queue
    if not queue:
        state.log("There are no waiting updates to cancel; the active update must finish.")
        return False
    selected = min(state.selected_queue_cancellation if index is None else index, len(queue) - 1)
    job = queue.pop(selected)
    size = update_size_by_name(job.size)
    fee = max(50, round(size["cost"] * 0.15))
    add_expense(state.studio, fee, "Cancelled production")
    game = game_by_id(state.studio, job.game_id)
    if game:
        game.post_launch_cost += fee
    rebuild_queued_update_versions(state.studio)
    state.selected_queue_cancellation = min(selected, max(0, len(queue) - 1))
    state.log(f"Cancelled queued {job.size} {job.focus} update for {job.game_title}; abandoned preparation cost ${fee:,}.")
    return True


def finish_game_update(state: GameState, job: UpdateJob, game: ReleasedGame) -> None:
    size = update_size_by_name(job.size)
    focus = update_focus_by_name(job.focus)
    game.updates_released += 1
    game.version = job.target_version
    game.update_progress = 0
    fixed_existing = 0.0
    if job.focus == "Bug fixes":
        fixed_existing = min(game.actual_bugs, float(size["fixes"]))
        known_fixed = min(game.known_bugs, fixed_existing)
        game.actual_bugs -= fixed_existing
        game.known_bugs -= known_fixed
    escaped_bugs = float(size["escaped"])
    if job.focus == "Bug fixes":
        escaped_bugs = min(escaped_bugs, fixed_existing * 0.1)
    game.actual_bugs += escaped_bugs
    if game.actual_bugs > 0:
        game.known_bugs = min(game.known_bugs, game.actual_bugs * 0.98)
    game.reported_bug_count = min(game.reported_bug_count, game.known_bug_count)
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
    clamp_player_counts(game)
    sale = sale_for_game(state.studio, game.game_id)
    if sale:
        sale.weekly_units += max(1, round(sale.evergreen_units * size["sales"] * rating_factor))
    if job.size == "Paid DLC":
        roadmap_bonus = 1.25 if game.release_strategy == "DLC roadmap" else 0.8
        dlc_units = min(game.units_sold, round(game.units_sold * (0.05 + game.score / 500) * roadmap_bonus))
        dlc_net = dlc_units * size["price"] * 0.70
        add_revenue(state.studio, dlc_net, "DLC sales")
        game.net_revenue += dlc_net
        game.dlc_revenue += dlc_net
        game.dlcs_released += 1
        state.log(f"{game.title}'s paid DLC sold {dlc_units:,} copies at launch and added ${dlc_net:,.0f} studio net.")
    add_expense(state.studio, size["cost"], "Live operations")
    game.post_launch_cost += size["cost"]
    state.log(
        f"Released v{game.version} ({job.size} {job.focus}) for {game.title} after fixing "
        f"{job.bugs_found:.0f} update bugs"
        f"{' and ' + format(fixed_existing, '.0f') + ' existing bugs' if fixed_existing else ''}: "
        f"+{hype_gain:.1f} hype, about {returning_players:,} players returned."
    )


def process_game_updates(state: GameState, week_end: bool = True, workday: bool = True) -> None:
    studio = state.studio
    start_next_update(state)
    job = studio.active_update
    if job is None:
        return
    if not workday:
        return
    game = game_by_id(studio, job.game_id)
    if game is None:
        studio.active_update = None
        start_next_update(state)
        return
    for employee in state.studio.team:
        if not employee.training_weeks_left:
            employee.fatigue = min(100, employee.fatigue + (0.5 / 5) * employee_modifiers(employee)["fatigue"])
            if week_end:
                update_skill = update_focus_by_name(job.focus)["skill"] if job.phase == "Development" else "Code"
                grant_employee_experience(state, employee, update_skill, 1, "live-operations experience")
    if job.phase == "Development":
        job.work_done = min(job.required_work, job.work_done + update_weekly_output(studio, job.focus) / 5)
        if job.work_done >= job.required_work:
            state.log(f"v{job.target_version} for {job.game_title} entered bug fixing with {job.bugs_found:.0f} issues found.")
    else:
        job.bugs_fixed = min(job.bugs_found, job.bugs_fixed + update_weekly_output(studio, "Bug fixes") / 5)
    game.update_progress = job.progress * 100
    if job.work_done >= job.required_work and job.bugs_fixed >= job.bugs_found:
        finish_game_update(state, job, game)
        studio.active_update = None
        start_next_update(state)


def process_sales(state: GameState, week_end: bool = True, day_number: int = 0) -> None:
    studio = state.studio
    week_start = day_number % 7 == 1
    for sale in studio.active_sales:
        if week_start:
            sale.week_units = 0.0
        rng = random.Random(studio.seed + day_number * 131 + sale.game_id * 17)
        units = max(0.0, sale.weekly_units / 7 * rng.uniform(0.8, 1.25))
        sale.week_units += units
        gross = units * sale.price
        net = gross * (1 - sale.refund_rate) * (1 - sale.platform_cut)
        add_revenue(studio, net, "Game sales")
        game = next((item for item in studio.catalog if item.game_id == sale.game_id), None)
        hosting_rate = game.hosting_rate if game else 0.0
        hosting_cost = max(10 / 7, units * (0.03 + hosting_rate) + (game.monthly_players * hosting_rate * 0.02 / 7 if game else 0))
        add_expense(studio, hosting_cost, "Hosting")
        sale.units_sold += round(units)
        sale.gross_revenue += gross
        sale.net_revenue += net
        gained = round(units * max(0.01, (sale.score / 100) ** 2 * 0.2))
        studio.followers += gained
        if sale.genre:
            studio.genre_fans[sale.genre] = studio.genre_fans.get(sale.genre, 0) + gained
        if game:
            game.units_sold += round(units)
            game.net_revenue += net
            game.post_launch_cost += hosting_cost
            studio.topic_fans[game.topic] = studio.topic_fans.get(game.topic, 0) + gained
            game.hype *= 0.965 ** (1 / 7)
            strategy_retention = {"Complete package": 0.0, "Free update roadmap": 0.025, "DLC roadmap": 0.015, "Live service": 0.06}.get(game.release_strategy, 0)
            format_retention = 0.03 if game.game_format != "Offline solo" else 0
            retention = min(0.95, 0.58 + game.score * 0.0037 + strategy_retention + format_retention)
            game.active_players = game.active_players * retention ** (1 / 7) + units * 0.70
            game.monthly_players = max(0, round(game.active_players * 3.2))
            game.peak_monthly_players = max(game.peak_monthly_players, game.monthly_players)
            clamp_player_counts(game)
            franchise = franchise_by_id(studio, game.franchise_id)
            if franchise:
                franchise.total_units += round(units)
                franchise.total_revenue += net
                franchise.awareness = min(6_000, franchise.awareness + units / 60)
        if not week_end:
            continue
        week_units = sale.week_units
        if game:
            hype_lift = game.hype / 14
            undiscovered = max(0, game.actual_bugs - game.known_bugs)
            if undiscovered > 0:
                discovery_rate = min(0.35, 0.015 + week_units / 10_000 + game.monthly_players / 100_000)
                game.known_bugs = min(game.actual_bugs * 0.98, game.known_bugs + undiscovered * discovery_rate)
                newly_reported = game.known_bug_count - game.reported_bug_count
                if newly_reported > 0:
                    game.reported_bug_count = game.known_bug_count
                    game.hype = max(0, game.hype - newly_reported * 0.35)
                    state.log(f"Players reported {newly_reported} newly discovered bug(s) in {game.title} and complained online.")
            franchise = franchise_by_id(studio, game.franchise_id)
            if franchise:
                franchise.reputation += (game.score - franchise.reputation) * 0.05
            service = min(8.0, game.updates_released * 1.5)
            bug_drag = min(28.0, game.known_bugs * 1.6)
            user_target = max(5.0, min(99.0, game.score + service - bug_drag))
            previous_user = game.user_rating
            game.user_rating += (user_target - game.user_rating) * 0.12
            game.user_trend = game.user_rating - previous_user
            game.press_rating += (game.score - game.press_rating) * 0.03
            game.sales_history.append(round(week_units))
            del game.sales_history[:-16]
        else:
            hype_lift = 0
        tail = min(0.91, 0.55 + sale.score * 0.0035 + (0.02 if "analytics" in studio.upgrades else 0))
        sale.weekly_units = max(sale.evergreen_units, round(week_units * tail + hype_lift))
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


def process_contract(state: GameState, week_end: bool = True, workday: bool = True) -> None:
    studio = state.studio
    start_next_contract(state)
    contract = studio.contract
    if contract is None:
        return
    if not workday:
        return
    if contract.required_work <= 0:
        for employee in studio.team:
            if not employee.training_weeks_left:
                employee.fatigue = min(100, employee.fatigue + (2 / 5) * employee_modifiers(employee)["fatigue"])
                if week_end:
                    grant_employee_experience(state, employee, "Generalist", 1, "contract experience")
        if not week_end:
            return
        contract.weeks_left -= 1
        if contract.weeks_left <= 0:
            add_revenue(studio, contract.payout, "Contracts")
            studio.contractor_reputation = min(100, studio.contractor_reputation + 1)
            studio.contracts_completed += 1
            state.log(f"Delivered the legacy {contract.title}; client paid ${contract.payout:,}.")
            studio.contract = None
            start_next_contract(state)
        return

    output = contract_weekly_output(studio, contract.focus) / 5
    contract.work_done = min(contract.required_work, contract.work_done + output)
    for employee in studio.team:
        if not employee.training_weeks_left:
            employee.fatigue = min(100, employee.fatigue + (2 / 5) * employee_modifiers(employee)["fatigue"])
            if week_end:
                grant_employee_experience(state, employee, contract.focus, 1, "contract experience")
    if week_end:
        contract.weeks_left -= 1
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


def process_day(state: GameState, day_date: date) -> None:
    studio = state.studio
    month = day_date.strftime("%Y-%m")
    if month != studio.accounting_month:
        begin_month(state, month)
    day_number = day_date.toordinal()
    week_end = day_number % 7 == 0
    workday = day_date.weekday() < 5
    process_employee_training(state, week_end)
    process_promotions(state, week_end)
    process_game_updates(state, week_end, workday)
    process_sales(state, week_end, day_number)
    process_contract(state, week_end, workday)
    develop_project(state, day_number, week_end, workday)
    if week_end:
        process_franchises_week(state)
        process_media_ventures_week(state)
        process_market_week(state)
    if studio.cash < 0:
        studio.insolvent_days += 1
        studio.insolvent_weeks = studio.insolvent_days // 7
        if studio.insolvent_days == 1:
            state.log("The bank balance is negative. You have eight weeks to recover before closure.")
        if studio.insolvent_days >= 56:
            studio.closed = True
            state.time_speed_index = 0
            state.log("The studio is insolvent and has closed. Load an earlier save or begin again.")
    else:
        studio.insolvent_days = 0
        studio.insolvent_weeks = 0


def process_week(state: GameState, week_date: date) -> None:
    for offset in range(7):
        process_day(state, week_date - timedelta(days=6 - offset))


def advance_days(state: GameState, days: int) -> None:
    for offset in range(days):
        day_date = state.clock.current_date - timedelta(days=days - offset - 1)
        process_day(state, day_date)


def advance_game(state: GameState, weeks: int) -> None:
    advance_days(state, weeks * 7)


def franchise_by_id(studio: Studio, franchise_id: int | None) -> Franchise | None:
    if franchise_id is None:
        return None
    return next((item for item in studio.franchises if item.franchise_id == franchise_id), None)


def franchise_for_game(studio: Studio, game: ReleasedGame) -> Franchise | None:
    return franchise_by_id(studio, game.franchise_id)


def base_title_for(game: ReleasedGame) -> str:
    base = game.title
    if game.generation > 1:
        suffix = f" {roman_number(game.generation)}"
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    return base


def ensure_franchise_for_release(state: GameState, project: Project, game: ReleasedGame, units: int, score: int) -> Franchise:
    studio = state.studio
    franchise = franchise_by_id(studio, project.franchise_id)
    if franchise is None and project.sequel_of:
        previous = next((item for item in studio.catalog if item.game_id == project.sequel_of), None)
        if previous:
            franchise = franchise_by_id(studio, previous.franchise_id)
    if franchise is None:
        franchise = Franchise(
            studio.next_franchise_id,
            base_title_for(game)[:40],
            game.genre,
            game.topic,
            created=state.clock.current_date.isoformat(),
        )
        studio.next_franchise_id += 1
        studio.franchises.append(franchise)
    franchise.entries += 1
    franchise.awareness = min(6_000, franchise.awareness + units / 30 + score / 8)
    if franchise.entries <= 1:
        franchise.reputation = float(score)
    else:
        franchise.reputation += (score - franchise.reputation) * 0.35
    if project.sequel_of or project.franchise_id:
        franchise.fatigue = min(120, franchise.fatigue + max(0, 14 - franchise.entries * 2))
    game.franchise_id = franchise.franchise_id
    rank = franchise.rank_name
    state.log(f"The {franchise.name} IP now stands at {rank} rank ({franchise.entries} release{'s' if franchise.entries != 1 else ''}).")
    return franchise


def prepare_spinoff(state: GameState, game: ReleasedGame) -> bool:
    franchise = franchise_for_game(state.studio, game)
    if franchise is None:
        state.log("Only games attached to an IP can spawn a spin-off.")
        return False
    prepare_sequel(state, game)
    state.spinoff_franchise_id = franchise.franchise_id
    state.sequel_game_id = None
    spinoff_name = generate_game_title(game.genre, game.topic, state.studio.seed + state.clock.week + franchise.franchise_id)
    state.draft_title = f"{franchise.name}: {spinoff_name}"[:48]
    state.new_game_step = 0
    state.log(f"Planning a spin-off in the {franchise.name} IP ({franchise.rank_name}); pick any genre and theme.")
    return True


def process_franchises_week(state: GameState) -> None:
    for franchise in state.studio.franchises:
        franchise.awareness *= 0.997
        franchise.fatigue *= 0.95


def media_venture_available(studio: Studio, franchise: Franchise, venture: dict) -> str:
    if franchise.rank < venture["rank"]:
        return f"requires {FRANCHISE_RANKS[venture['rank']]} IP rank"
    if any(item.franchise_id == franchise.franchise_id and item.kind == venture["key"] for item in studio.media_ventures):
        return "already active for this IP"
    return ""


def buy_media_venture(state: GameState, franchise_id: int, venture_index: int) -> bool:
    studio = state.studio
    venture = MEDIA_VENTURES[venture_index]
    franchise = franchise_by_id(studio, franchise_id)
    if franchise is None:
        state.log("The selected game is not attached to an IP yet.")
        return False
    blocker = media_venture_available(studio, franchise, venture)
    if blocker:
        state.log(f"{venture['name']} for {franchise.name} {blocker}.")
        return False
    if studio.cash < venture["cost"] + monthly_fixed_cost(studio):
        state.log(f"Cannot fund {venture['name']} without risking next month's bills.")
        return False
    add_expense(studio, venture["cost"], "Merch & Media")
    weekly_revenue = 0.0
    release_payout = 0.0
    if venture["key"] == "merch":
        weekly_revenue = round(60 + franchise.value * 2.4 + studio.followers * 0.02, 2)
    elif venture["key"] == "convention":
        weekly_revenue = round(venture["cost"] * 0.22 / venture["weeks"], 2)
    elif venture["key"] == "film":
        release_payout = round(venture["cost"] * (0.4 + franchise.value / 220 + franchise.reputation / 90), 2)
    elif venture["key"] == "series":
        release_payout = round(venture["cost"] * (0.5 + franchise.value / 160 + franchise.reputation / 70), 2)
    studio.media_ventures.append(
        MediaVenture(
            studio.next_venture_id,
            venture["key"],
            venture["name"],
            franchise.franchise_id,
            franchise.name,
            venture["weeks"],
            venture["weeks"],
            venture["cost"],
            weekly_revenue,
            release_payout,
        )
    )
    studio.next_venture_id += 1
    state.log(f"Started {venture['name']} for the {franchise.name} IP: ${venture['cost']:,}, {venture['weeks']} weeks.")
    return True


def process_media_ventures_week(state: GameState) -> None:
    studio = state.studio
    for venture in list(studio.media_ventures):
        franchise = franchise_by_id(studio, venture.franchise_id)
        if venture.weekly_revenue:
            add_revenue(studio, venture.weekly_revenue, "Merch & Media")
            venture.revenue += venture.weekly_revenue
        venture.weeks_left -= 1
        if venture.weeks_left > 0:
            continue
        studio.media_ventures.remove(venture)
        if franchise is None:
            continue
        if venture.kind == "convention":
            franchise.awareness = min(6_000, franchise.awareness + 60 + franchise.value * 0.12)
            franchise.fatigue = max(0, franchise.fatigue - 12)
            for game in studio.catalog:
                if game.franchise_id == franchise.franchise_id:
                    game.hype = min(200, game.hype + 25)
            state.log(f"The {franchise.name} convention wrapped: fans loved it, awareness surged across the IP.")
        elif venture.kind in ("film", "series"):
            rng = random.Random(studio.seed + state.clock.week * 53 + venture.venture_id)
            quality_roll = 0.5 + franchise.reputation / 130 + rng.uniform(-0.15, 0.25)
            payout = round(venture.release_payout * max(0.15, quality_roll))
            add_revenue(studio, payout, "Merch & Media")
            venture.revenue += payout
            franchise.awareness = min(6_000, franchise.awareness + 120 + franchise.value * 0.2)
            studio.followers += round(200 + franchise.value * 3)
            label = "film" if venture.kind == "film" else "series"
            verdict = "a hit" if quality_roll >= 1.0 else "mixed" if quality_roll >= 0.6 else "a flop"
            state.log(f"{franchise.name}: the {label} adaptation released to {verdict} reception: ${payout:,} in licensing and royalties.")


BUG_FIX_WORK_PER_DEFECT = 1.6


def seed_market(state: GameState) -> None:
    studio = state.studio
    rng = random.Random(studio.seed * 3 + 77)
    ip_names = list(COMPETITOR_IP_NAMES)
    rng.shuffle(ip_names)
    for index, archetype in enumerate(COMPETITOR_STUDIOS):
        competitor = Competitor(
            index + 1,
            archetype["name"],
            archetype["tier"],
            archetype["size"],
            archetype["fanbase"],
            float(archetype["reputation"]),
            genres=list(archetype["genres"]),
        )
        ip_count = 2 if archetype["tier"] in ("platform", "publisher") else 1
        for _ in range(ip_count):
            if not ip_names:
                break
            name = ip_names.pop()
            genre = rng.choice(competitor.genres)
            competitor.franchises.append(
                Franchise(
                    0,
                    name,
                    genre,
                    rng.choice(TOPICS),
                    owner=competitor.name,
                    awareness=rng.uniform(120, 900) * (0.5 + competitor.size / 6),
                    reputation=max(30.0, min(95.0, competitor.reputation + rng.uniform(-10, 8))),
                    entries=rng.randint(1, 5),
                )
            )
        competitor.cooldown = rng.randint(1, 6)
        for seed_index, weeks_ago in enumerate((rng.randint(2, 6), rng.randint(8, 14))):
            franchise = competitor.franchises[0] if competitor.franchises and rng.random() < 0.6 else None
            genre = franchise.genre if franchise else rng.choice(competitor.genres)
            quality = max(25, min(96, round(competitor.reputation + rng.uniform(-12, 10))))
            hype = min(200, (25 + competitor.size * 10 + (franchise.value / 14 if franchise else 0)) * rng.uniform(0.7, 1.3))
            title = f"{franchise.name} {roman_number(max(1, franchise.entries - seed_index))}" if franchise else generate_game_title(genre, rng.choice(TOPICS), studio.seed + competitor.competitor_id * 7 + weeks_ago)
            launch = hype * 11 * (0.4 + competitor.size / 5) * (0.5 + competitor.fanbase / 600_000) * (0.55 + quality / 150)
            weekly = max(40.0, launch * min(0.90, 0.50 + quality * 0.004) ** weeks_ago)
            competitor.recent_releases.append(
                CompetitorGame(title, franchise.name if franchise else "", genre, quality, round(hype, 1), 0, competitor.size, released_week=1, weekly_units=weekly, units_sold=round(launch * weeks_ago * 0.6))
            )
        studio.competitors.append(competitor)


def process_market_week(state: GameState) -> None:
    studio = state.studio
    rng = random.Random(studio.seed * 7 + state.clock.week * 31)
    for competitor in studio.competitors:
        for game in list(competitor.in_development):
            game.weeks_left -= 1
        finished = [game for game in competitor.in_development if game.weeks_left <= 0]
        for game in finished:
            competitor.in_development.remove(game)
            game.released_week = state.clock.week
            competitor.recent_releases.insert(0, game)
            del competitor.recent_releases[6:]
        competitor.cooldown -= 1
        if competitor.cooldown <= 0 and len(competitor.in_development) < (2 if competitor.size >= 5 else 1):
            busy = {game.franchise_name for game in competitor.in_development}
            available_ips = [item for item in competitor.franchises if item.name not in busy]
            franchise = rng.choice(available_ips) if available_ips and rng.random() < 0.5 else None
            genre = franchise.genre if franchise else rng.choice(competitor.genres)
            dev_weeks = max(4, round(rng.uniform(10, 30) / (0.5 + competitor.size / 6)))
            quality = max(25, min(96, round(competitor.reputation + rng.uniform(-12, 10))))
            hype = min(200, (25 + competitor.size * 10 + (franchise.value / 14 if franchise else 0)) * rng.uniform(0.7, 1.3))
            title = f"{franchise.name} {roman_number(franchise.entries + 1)}" if franchise else generate_game_title(genre, rng.choice(TOPICS), studio.seed + state.clock.week + competitor.competitor_id)
            competitor.in_development.append(CompetitorGame(title, franchise.name if franchise else "", genre, quality, round(hype, 1), dev_weeks, competitor.size))
            competitor.cooldown = rng.randint(8, max(12, round(52 - competitor.size * 4)))
        for game in finished:
            release = game
            franchise = next((item for item in competitor.franchises if item.name == release.franchise_name), None)
            competitor.fanbase += round(1_000 * competitor.size * release.quality / 80)
            launch_units = round(
                release.hype
                * 11
                * (0.4 + competitor.size / 5)
                * (0.5 + competitor.fanbase / 600_000)
                * (0.55 + release.quality / 150)
                * rng.uniform(0.85, 1.15)
            )
            release.weekly_units = float(max(40, launch_units))
            release.units_sold += max(40, launch_units)
            if franchise:
                franchise.entries += 1
                franchise.awareness = min(6_000, franchise.awareness + 20 + release.hype / 4)
                franchise.reputation += (release.quality - franchise.reputation) * 0.25
                franchise.fatigue = min(120, franchise.fatigue + 6)
            notable = competitor.size >= 3 or release.quality >= 80
            if notable:
                state.log(f"{competitor.name} released {release.title} ({release.genre}, {release.quality}/100). The market took notice.")
            impact = min(0.45, release.hype / 400 * (0.5 + competitor.size / 10))
            player_genre_games = [item for item in studio.catalog if item.genre == release.genre]
            for player_game in player_genre_games:
                sale = sale_for_game(studio, player_game.game_id)
                if sale and impact > 0.02:
                    sale.weekly_units = max(sale.evergreen_units, round(sale.weekly_units * (1 - impact)))
            if player_genre_games and impact > 0.08:
                state.log(f"Your {release.genre} sales dipped as {release.title} pulled players away ({impact:.0%} demand shift).")
        for game in competitor.recent_releases:
            if game.released_week and game.released_week < state.clock.week and game.weekly_units > 0:
                tail = min(0.90, 0.50 + game.quality * 0.004)
                game.weekly_units *= tail
                game.units_sold += round(game.weekly_units)
    positions = chart_positions(state)
    for game in studio.catalog:
        position = positions.get(game.game_id)
        if position is None:
            continue
        if position == 1 and game.chart_peak != 1:
            state.log(f"{game.title} topped the charts this week - your studio now leads the market.")
        if not game.chart_peak or position < game.chart_peak:
            game.chart_peak = position


def market_chart(state: GameState, limit: int = 10) -> list[ChartEntry]:
    entries = []
    for competitor in state.studio.competitors:
        for game in competitor.recent_releases:
            if game.weekly_units >= 100 and state.clock.week - game.released_week <= 30:
                entries.append(ChartEntry(game.title, competitor.name, game.genre, round(game.weekly_units), game.quality))
    for sale in state.studio.active_sales:
        game = game_by_id(state.studio, sale.game_id)
        if game is not None:
            entries.append(ChartEntry(game.title, "Your studio", game.genre, sale.weekly_units, game.score, game.game_id))
    entries.sort(key=lambda item: item.weekly_units, reverse=True)
    return entries[:limit]


def chart_positions(state: GameState, limit: int = 10) -> dict[int, int]:
    return {entry.game_id: rank for rank, entry in enumerate(market_chart(state, limit), 1) if entry.game_id}


def genre_release_pressure(studio: Studio, genre: str) -> float:
    pressure = 0.0
    for competitor in studio.competitors:
        for game in competitor.recent_releases:
            if game.genre == genre:
                pressure += game.hype / 120 * (0.4 + competitor.size / 8)
    return min(3.0, pressure)


def employee_from_data(data: dict) -> Employee:
    values = dict(data)
    if "research" not in values:
        role = next((name for name in ROLE_RESEARCH if values.get("role", "").endswith(name)), "Generalist")
        values["research"] = max(20, min(85, round((ROLE_RESEARCH[role] + sum(values.get(skill.lower(), 45) for skill in SKILLS) / 4) / 2)))
    return Employee(**values)


def state_to_data(state: GameState) -> dict:
    return {
        "version": SAVE_VERSION,
        "clock": {
            "current_date": state.clock.current_date.isoformat(),
            "week": state.clock.week,
            "day": state.clock.day,
            "elapsed_seconds": state.clock.elapsed_seconds,
        },
        "studio": asdict(state.studio),
        "ui": {
            "selected_genre": state.selected_genre,
            "selected_topic": state.selected_topic,
            "selected_channel": state.selected_channel,
            "selected_scope": state.selected_scope,
            "selected_marketing": state.selected_marketing,
            "selected_secondary_genre": state.selected_secondary_genre,
            "selected_secondary_topic": state.selected_secondary_topic,
            "selected_audience": state.selected_audience,
            "selected_format": state.selected_format,
            "selected_creative_primary": state.selected_creative_primary,
            "selected_creative_secondary": state.selected_creative_secondary,
            "selected_release_strategy": state.selected_release_strategy,
            "marketing_tab": state.marketing_tab,
            "games_tab": state.games_tab,
            "focus": state.focus,
            "time_speed_index": state.time_speed_index,
            "resume_speed_index": state.resume_speed_index,
            "draft_title": state.draft_title,
            "title_roll": state.title_roll,
            "sequel_game_id": state.sequel_game_id,
            "spinoff_franchise_id": state.spinoff_franchise_id,
            "selected_venture": state.selected_venture,
        },
        "logs": state.logs,
    }


def studio_from_data(data: dict) -> Studio:
    values = dict(data)
    values["team"] = [employee_from_data(item) for item in values.get("team", [])]
    values["applicants"] = [employee_from_data(item) for item in values.get("applicants", [])]
    if values.get("current_project"):
        project_data = dict(values["current_project"])
        if "known_defects" not in project_data:
            project_data["known_defects"] = project_data.get("defects", 0) * 0.4
        if "scheduled_decisions" not in project_data:
            if "next_decision" in project_data:
                next_event = project_data.get("pending_decision")
                start = project_data.get("next_decision", 0)
                project_data["scheduled_decisions"] = list(range(start, len(PRODUCTION_DECISIONS)))
                if next_event is not None and (not project_data["scheduled_decisions"] or project_data["scheduled_decisions"][0] != next_event):
                    project_data["scheduled_decisions"].insert(0, next_event)
                project_data["next_decision"] = 0
            else:
                project_data["scheduled_decisions"] = []
        values["current_project"] = Project(**project_data)
    values["active_sales"] = [ActiveSale(**item) for item in values.get("active_sales", [])]
    for sale in values["active_sales"]:
        sale.units_sold = round(sale.units_sold)
    catalog = []
    for item in values.get("catalog", []):
        game = ReleasedGame(**item)
        game.units_sold = round(game.units_sold)
        if "user_rating" not in item:
            game.user_rating = float(game.score)
            game.press_rating = float(game.score)
        if "actual_bugs" not in item:
            infer_legacy_game_bugs(game)
        if "version" not in item:
            for _ in range(game.updates_released):
                game.version = bump_version(game.version, game.update_size)
        clamp_player_counts(game)
        catalog.append(game)
    if not catalog:
        for sale in values["active_sales"]:
            topic, separator, genre = sale.title.partition(": ")
            if separator and genre in GENRES and topic in TOPICS:
                game_id = len(catalog) + 1
                sale.game_id = game_id
                sale.genre = genre
                game = ReleasedGame(
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
                infer_legacy_game_bugs(game)
                catalog.append(game)
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
    if values.get("active_update"):
        values["active_update"] = UpdateJob(**values["active_update"])
    values["update_queue"] = [UpdateJob(**item) for item in values.get("update_queue", [])]
    update_ids = [job.update_id for job in values["update_queue"]]
    if values.get("active_update"):
        update_ids.append(values["active_update"].update_id)
    values["next_update_id"] = max(values.get("next_update_id", 1), max(update_ids, default=0) + 1)
    values["active_promotions"] = [Promotion(**item) for item in values.get("active_promotions", [])]
    values["next_promotion_id"] = max(
        values.get("next_promotion_id", 1),
        max((promotion.promotion_id for promotion in values["active_promotions"]), default=0) + 1,
    )
    values["franchises"] = [Franchise(**item) for item in values.get("franchises", [])]
    for franchise in values["franchises"]:
        franchise.total_units = round(franchise.total_units)
    values["next_franchise_id"] = max(
        values.get("next_franchise_id", 1),
        max((franchise.franchise_id for franchise in values["franchises"]), default=0) + 1,
    )
    values["media_ventures"] = [MediaVenture(**item) for item in values.get("media_ventures", [])]
    values["next_venture_id"] = max(
        values.get("next_venture_id", 1),
        max((venture.venture_id for venture in values["media_ventures"]), default=0) + 1,
    )
    competitors = []
    for item in values.get("competitors", []):
        entry = dict(item)
        entry["franchises"] = [Franchise(**franchise) for franchise in entry.get("franchises", [])]
        entry["in_development"] = [CompetitorGame(**game) for game in entry.get("in_development", [])]
        entry["recent_releases"] = [CompetitorGame(**game) for game in entry.get("recent_releases", [])]
        competitors.append(Competitor(**entry))
    values["competitors"] = competitors
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


def migrate_studio_franchises(studio: Studio) -> None:
    if studio.franchises:
        return
    by_id = {game.game_id: game for game in studio.catalog}
    for game in studio.catalog:
        if game.franchise_id is not None:
            continue
        root = game
        while root.sequel_of in by_id:
            root = by_id[root.sequel_of]
        franchise = franchise_by_id(studio, root.franchise_id)
        if franchise is None:
            franchise = Franchise(
                studio.next_franchise_id,
                base_title_for(root)[:40],
                root.genre,
                root.topic,
                created=root.release_date,
                awareness=min(6_000, root.units_sold / 40 + root.score),
                reputation=float(root.score),
                entries=0,
            )
            studio.next_franchise_id += 1
            studio.franchises.append(franchise)
            root.franchise_id = franchise.franchise_id
            franchise.entries += 1
            franchise.total_units += root.units_sold
            franchise.total_revenue += root.net_revenue
        if game is not root:
            game.franchise_id = franchise.franchise_id
            franchise.entries += 1
            franchise.total_units += game.units_sold
            franchise.total_revenue += game.net_revenue
            franchise.reputation += (game.score - franchise.reputation) * 0.35


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
    if data.get("version") not in (2, 3, 4, SAVE_VERSION):
        return migrate_legacy(data, save_path)
    clock_data = data["clock"]
    clock = GameClock(date.fromisoformat(clock_data["current_date"]), clock_data["week"], clock_data.get("elapsed_seconds", 0.0), clock_data.get("day", clock_data["week"] * 7 - 6))
    ui = data.get("ui", {})
    selected_scope = ui.get("selected_scope", 0)
    if data.get("version") == 2:
        selected_scope = {0: 0, 1: 2, 2: 4}.get(selected_scope, 0)
    studio = studio_from_data(data["studio"])
    recover_catalog_from_logs(studio, data.get("logs", []))
    recover_contractor_history(studio, data.get("logs", []))
    migrate_studio_franchises(studio)
    ensure_catalog_sales(studio)
    state = GameState(
        clock=clock,
        studio=studio,
        selected_genre=ui.get("selected_genre", 0),
        selected_topic=ui.get("selected_topic", 0),
        selected_channel=ui.get("selected_channel", 0),
        selected_scope=selected_scope,
        selected_marketing=ui.get("selected_marketing", 0),
        selected_secondary_genre=ui.get("selected_secondary_genre", ui.get("selected_genre", 0)),
        selected_secondary_topic=ui.get("selected_secondary_topic", ui.get("selected_topic", 0)),
        selected_audience=ui.get("selected_audience", 0),
        selected_format=ui.get("selected_format", 0),
        selected_creative_primary=ui.get("selected_creative_primary", 0),
        selected_creative_secondary=ui.get("selected_creative_secondary", 3),
        selected_release_strategy=ui.get("selected_release_strategy", 0),
        marketing_tab=ui.get("marketing_tab", 0),
        games_tab=ui.get("games_tab", 0),
        focus=ui.get("focus", [30, 25, 15, 30]),
        time_speed_index=ui.get("time_speed_index", 1),
        resume_speed_index=ui.get("resume_speed_index", 1),
        draft_title=ui.get("draft_title", ""),
        title_roll=ui.get("title_roll", 0),
        sequel_game_id=ui.get("sequel_game_id"),
        spinoff_franchise_id=ui.get("spinoff_franchise_id"),
        selected_venture=ui.get("selected_venture", 0),
        save_path=save_path,
        logs=data.get("logs", []),
    )
    old_update_model = "active_update" not in data["studio"] and "update_queue" not in data["studio"]
    if old_update_model:
        raw_games = {item.get("game_id"): item for item in data["studio"].get("catalog", [])}
        old_plans = []
        for index, game in enumerate(studio.catalog):
            previous_progress = game.update_progress
            was_automatic = raw_games.get(game.game_id, {}).get("auto_updates", False)
            game.auto_updates = False
            if previous_progress > 0 or was_automatic:
                old_plans.append((not was_automatic, index, game, previous_progress))
        for _, _, game, previous_progress in sorted(old_plans):
            queue_game_update(state, game.game_id)
            job = next(
                candidate
                for candidate in ([studio.active_update] if studio.active_update else []) + studio.update_queue
                if candidate.game_id == game.game_id
            )
            job.work_done = job.required_work * min(1, previous_progress / 100)
            game.update_progress = job.progress * 100
    return state


def save_game(state: GameState) -> None:
    Path(state.save_path).write_text(json.dumps(state_to_data(state), indent=2), encoding="utf-8")


def load_game(save_path: str) -> GameState:
    return state_from_data(json.loads(Path(save_path).read_text(encoding="utf-8")), save_path)
