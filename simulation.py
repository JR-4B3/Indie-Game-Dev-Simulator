from __future__ import annotations

import json
import math
import random
import secrets
from dataclasses import asdict, dataclass, field, replace
from datetime import date, timedelta
from pathlib import Path

from game_data import GENRES, GENRE_PROFILES, GOOD_MATCHES, TOPICS
from sim_core.events import emit_event
from sim_core.finance import (
    financing_inflow,
    forward_runway_months,
    operating_expense,
    operating_revenue,
    principal_payment,
    record_transaction,
)
from sim_core.market import COHORTS, DemandResult, MacroSnapshot, ProductOffer, allocate_weekly_demand
from sim_core.products import (
    ANNOUNCEMENT_STRATEGIES,
    COMMUNITY_ACTIONS,
    MONETIZATION_MODELS,
    PRICE_POINTS,
    RELEASE_POLICIES,
    announcement_strategy_by_key,
    community_action_by_key,
    monetization_model_by_key,
    release_policy_by_key,
)


SAVE_VERSION = 10
START_DATE = date.today()
SECONDS_PER_WEEK = 120.0
SECONDS_PER_DAY = SECONDS_PER_WEEK / 7
SKILLS = ("Design", "Art", "Audio", "Code")
EMPLOYEE_SKILLS = SKILLS + ("Research",)
TIME_SPEEDS = (0.0, 12.0, 24.0, 48.0)
TIME_LABELS = ("||", "> 1x", ">> 2x", ">>> 4x")

CHANNELS = (
    {"name": "Steam", "category": "PC", "fee": 100, "cut": 0.30, "reach": 1.00, "visibility": 5},
    {"name": "itch.io", "category": "PC", "fee": 0, "cut": 0.10, "reach": 0.18, "visibility": 1},
    {"name": "Epic Games Store", "category": "PC", "fee": 100, "cut": 0.12, "reach": 0.32, "visibility": 3},
    {"name": "App Store", "category": "Mobile", "fee": 99, "cut": 0.30, "reach": 0.70, "visibility": 4},
    {"name": "Google Play", "category": "Mobile", "fee": 25, "cut": 0.30, "reach": 0.82, "visibility": 5},
    {"name": "PlayStation 5", "category": "Console", "fee": 12_500, "cut": 0.30, "reach": 0.58, "visibility": 5},
    {"name": "Xbox Series", "category": "Console", "fee": 8_000, "cut": 0.30, "reach": 0.42, "visibility": 4},
    {"name": "Switch 2", "category": "Handheld", "fee": 10_000, "cut": 0.30, "reach": 0.52, "visibility": 5},
)

# Storefronts bury unknown developers: nobody ships their first game on Steam.
# Free itch.io releases build the tiny audience and craft history that unlocks
# the big storefronts.
ITCH_RELEASES_BEFORE_STEAM = 10

# Weekly infrastructure rent online games pay while their servers run,
# multiplied by 1..5 depending on monthly players. This is the fixed cost
# that makes live games a liability even when development is done.
SERVER_RENT_PER_WEEK = {
    "Online co-op": 120.0,
    "Competitive online": 450.0,
    "Persistent world": 900.0,
    "MMO": 1_600.0,
}

LOAN_OFFERS = (
    {"name": "Bridge loan", "principal": 25_000, "weeks": 52, "rate": 0.13},
    {"name": "Production loan", "principal": 100_000, "weeks": 104, "rate": 0.11},
    {"name": "Growth loan", "principal": 500_000, "weeks": 156, "rate": 0.095},
)

PUBLISHER_OFFERS = (
    {"name": "Northstar Publishing", "min_rep": 0, "advance": 35_000, "recoup_share": 0.50, "post_recoup_share": 0.30, "hype": 12, "visibility": 1},
    {"name": "Cinder House", "min_rep": 12, "advance": 180_000, "recoup_share": 0.50, "post_recoup_share": 0.25, "hype": 30, "visibility": 1},
    {"name": "Atlas Interactive", "min_rep": 35, "advance": 900_000, "recoup_share": 0.55, "post_recoup_share": 0.22, "hype": 55, "visibility": 2},
)

# setup = cash outlay at greenlight (assets, middleware, outsourcing, tech). Payroll is separate.
# sales = commercial scale used for audience and unit potential.
SCOPES = (
    {"name": "Micro", "work": 1_200, "setup": 3_500, "price": 7.99, "risk": 0, "team": 1, "rep": 0, "market": 0.55, "sales": 1.0},
    {"name": "Compact", "work": 4_200, "setup": 24_000, "price": 11.99, "risk": 1, "team": 2, "rep": 0, "market": 0.75, "sales": 2.4},
    {"name": "Small", "work": 14_000, "setup": 90_000, "price": 14.99, "risk": 4, "team": 4, "rep": 0, "market": 1.0, "sales": 6.0},
    {"name": "Mid-size", "work": 55_000, "setup": 480_000, "price": 19.99, "risk": 7, "team": 10, "rep": 0, "market": 1.4, "sales": 18.0},
    {"name": "Ambitious", "work": 125_000, "setup": 2_400_000, "price": 29.99, "risk": 10, "team": 20, "rep": 4, "market": 1.9, "sales": 55.0},
    {"name": "Large", "work": 340_000, "setup": 14_000_000, "price": 49.99, "risk": 17, "team": 35, "rep": 18, "market": 3.2, "sales": 170.0},
    {"name": "Blockbuster", "work": 800_000, "setup": 65_000_000, "price": 69.99, "risk": 28, "team": 55, "rep": 45, "market": 5.5, "sales": 450.0},
    # Jam-sized experiments: the raw material of the itch.io years. Deliberately
    # last in the tuple so existing scope indexes stay stable.
    {"name": "Bite-size", "work": 220, "setup": 800, "price": 3.99, "risk": 0, "team": 1, "rep": 0, "market": 0.35, "sales": 0.5},
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
    {"name": "Offline solo", "work": 1.0, "setup": 0, "risk": 0, "team": 1, "rep": 0, "market": 0.9, "hosting": 0.0, "sales": 1.0},
    {"name": "Online co-op", "work": 1.45, "setup": 160_000, "risk": 4, "team": 3, "rep": 0, "market": 1.15, "hosting": 0.04, "sales": 1.2},
    {"name": "Competitive online", "work": 2.1, "setup": 1_250_000, "risk": 9, "team": 6, "rep": 8, "market": 1.55, "hosting": 0.09, "sales": 1.55},
    {"name": "Persistent world", "work": 3.4, "setup": 5_200_000, "risk": 17, "team": 12, "rep": 25, "market": 2.3, "hosting": 0.18, "sales": 2.1},
    {"name": "MMO", "work": 8.5, "setup": 26_000_000, "risk": 32, "team": 40, "rep": 60, "market": 5.0, "hosting": 0.38, "sales": 3.8},
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
    {"name": "Complete package", "work": 1.0, "setup": 0, "risk": 0, "market": 0, "price": 1.0, "sales": 1.0, "tail": -0.03, "expect_weeks": 0, "dlc_reception": 0.55, "tradeoff": "Clear promise; short tail, paid DLC feels like a cash grab"},
    {"name": "Free update roadmap", "work": 1.12, "setup": 45_000, "risk": 2, "market": 6, "price": 1.0, "sales": 1.12, "tail": 0.03, "expect_weeks": 14, "dlc_reception": 0.35, "tradeoff": "Fans expect steady free updates; paid DLC will enrage them"},
    {"name": "DLC roadmap", "work": 1.10, "setup": 125_000, "risk": 3, "market": 3, "price": 1.05, "sales": 1.08, "tail": 0.01, "expect_weeks": 0, "dlc_reception": 1.25, "tradeoff": "Future paid content; fragments attention"},
    {"name": "Live service", "work": 1.45, "setup": 1_200_000, "risk": 10, "market": 14, "price": 0.72, "sales": 1.45, "tail": 0.02, "expect_weeks": 9, "dlc_reception": 0.85, "tradeoff": "Large upside; players expect constant updates"},
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
    {"name": "Community", "cost": 8_000, "boost": 110},
    {"name": "Targeted", "cost": 35_000, "boost": 250},
    {"name": "Creator push", "cost": 95_000, "boost": 520},
    {"name": "Launch campaign", "cost": 280_000, "boost": 1_100},
    {"name": "Showcase launch", "cost": 750_000, "boost": 2_100},
)

PROMOTIONS = (
    {"key": "social", "name": "Social media push", "cost": 6_500, "weeks": 1, "hype": 8, "ceiling": 30, "team": 0.02, "rep": 0, "effect": "Small targeted awareness"},
    {"key": "press", "name": "Press outreach", "cost": 18_000, "weeks": 2, "hype": 16, "ceiling": 50, "team": 0.04, "rep": 2, "effect": "Reviews, previews, and interviews"},
    {"key": "creator", "name": "Creator key campaign", "cost": 42_000, "weeks": 2, "hype": 25, "ceiling": 75, "team": 0.05, "rep": 5, "effect": "Keys sent to relevant creators"},
    {"key": "streamer", "name": "Streamer placement", "cost": 85_000, "weeks": 2, "hype": 42, "ceiling": 105, "team": 0.03, "rep": 12, "effect": "Paid sponsored broadcast"},
    {"key": "festival", "name": "Digital festival demo", "cost": 55_000, "weeks": 3, "hype": 34, "ceiling": 85, "team": 0.12, "rep": 8, "effect": "Demo preparation consumes team time"},
    {"key": "event", "name": "Attend a games event", "cost": 175_000, "weeks": 4, "hype": 58, "ceiling": 125, "team": 0.18, "rep": 18, "effect": "Booth, travel, demo, and staff time"},
    {"key": "showcase", "name": "Premium showcase slot", "cost": 380_000, "weeks": 4, "hype": 105, "ceiling": 160, "team": 0.10, "rep": 35, "effect": "Large placement for established studios"},
)

UPDATE_FOCUSES = (
    {"name": "Bug fixes", "skill": "Code", "hype": 0.7, "players": 0.8},
    {"name": "Balance pass", "skill": "Design", "hype": 0.9, "players": 1.0},
    {"name": "Visual refresh", "skill": "Art", "hype": 1.1, "players": 1.0},
    {"name": "Audio pack", "skill": "Audio", "hype": 1.0, "players": 0.9},
    {"name": "New content", "skill": "Generalist", "hype": 1.35, "players": 1.4},
)

UPDATE_SIZES = (
    {"name": "Hotfix", "work": 16, "bugs": 3, "fixes": 4, "escaped": 0.2, "cost": 3_500, "hype": 2, "sales": 1, "version": (0, 0, 1), "team": 0.06},
    {"name": "Patch", "work": 45, "bugs": 8, "fixes": 10, "escaped": 0.8, "cost": 18_000, "hype": 7, "sales": 2, "version": (0, 0, 10), "team": 0.12},
    {"name": "Content", "work": 110, "bugs": 20, "fixes": 25, "escaped": 2.5, "cost": 95_000, "hype": 18, "sales": 4, "version": (0, 1, 0), "team": 0.20},
    {"name": "Expansion", "work": 240, "bugs": 45, "fixes": 55, "escaped": 6.0, "cost": 420_000, "hype": 42, "sales": 9, "version": (0, 10, 0), "team": 0.30},
    {"name": "Paid DLC", "work": 380, "bugs": 65, "fixes": 70, "escaped": 8.0, "cost": 850_000, "hype": 58, "sales": 12, "version": (1, 0, 0), "team": 0.38, "price": 14.99},
)

STARTER_RESEARCH = ("product_foundations", "garage_workflow", "basic_rest", "contract_basics", "basic_support")

RESEARCH_NODES = (
    # Product development
    {"key": "product_foundations", "branch": "Product", "tier": 0, "name": "Product Foundations", "cost": 0, "work": 0, "prereq": (), "effect": "Micro and Compact offline PC games"},
    {"key": "small_production", "branch": "Product", "tier": 1, "name": "Small Production", "cost": 4_500, "work": 260, "prereq": ("product_foundations",), "effect": "Unlock Small games"},
    {"key": "genre_story", "branch": "Product", "tier": 1, "name": "Story & Role-play Genres", "cost": 3_500, "work": 230, "prereq": ("product_foundations",), "effect": "Adventure, RPG, Visual Novel and related genres"},
    {"key": "genre_systems", "branch": "Product", "tier": 1, "name": "Systems & Strategy Genres", "cost": 3_500, "work": 230, "prereq": ("product_foundations",), "effect": "Strategy, simulation and building genres"},
    {"key": "theme_library_1", "branch": "Product", "tier": 1, "name": "Expanded Theme Library I", "cost": 2_500, "work": 180, "prereq": ("product_foundations",), "effect": "Unlock 25% of the extended theme catalogue"},
    {"key": "mid_production", "branch": "Product", "tier": 2, "name": "Mid-size Production", "cost": 28_000, "work": 700, "prereq": ("small_production", "production_pipeline"), "effect": "Unlock Mid-size games"},
    {"key": "online_coop", "branch": "Product", "tier": 2, "name": "Connected Games", "cost": 35_000, "work": 850, "prereq": ("small_production",), "effect": "Unlock online co-op"},
    {"key": "genre_action", "branch": "Product", "tier": 2, "name": "Action & Competition Genres", "cost": 18_000, "work": 620, "prereq": ("small_production",), "effect": "Shooters, fighting, racing and sports genres"},
    {"key": "genre_indie", "branch": "Product", "tier": 2, "name": "Modern Indie Genres", "cost": 18_000, "work": 620, "prereq": ("small_production",), "effect": "Roguelikes, deckbuilders, cozy and hybrid genres"},
    {"key": "theme_library_2", "branch": "Product", "tier": 2, "name": "Expanded Theme Library II", "cost": 14_000, "work": 500, "prereq": ("theme_library_1",), "effect": "Unlock another 25% of themes"},
    {"key": "ambitious_production", "branch": "Product", "tier": 3, "name": "Ambitious Production", "cost": 120_000, "work": 1_800, "prereq": ("mid_production", "department_leads"), "effect": "Unlock Ambitious games"},
    {"key": "competitive_online", "branch": "Product", "tier": 3, "name": "Competitive Networking", "cost": 160_000, "work": 2_000, "prereq": ("online_coop", "qa"), "effect": "Unlock competitive online games"},
    {"key": "theme_library_3", "branch": "Product", "tier": 3, "name": "Expanded Theme Library III", "cost": 55_000, "work": 1_400, "prereq": ("theme_library_2",), "effect": "Unlock another 25% of themes"},
    {"key": "large_production", "branch": "Product", "tier": 4, "name": "Large-scale Production", "cost": 650_000, "work": 5_000, "prereq": ("ambitious_production", "advanced_coordination"), "effect": "Unlock Large games"},
    {"key": "persistent_worlds", "branch": "Product", "tier": 4, "name": "Persistent Worlds", "cost": 850_000, "work": 6_000, "prereq": ("competitive_online", "live_operations"), "effect": "Unlock persistent-world games"},
    {"key": "theme_library_4", "branch": "Product", "tier": 4, "name": "Complete Theme Archive", "cost": 220_000, "work": 3_500, "prereq": ("theme_library_3",), "effect": "Unlock every theme"},
    {"key": "blockbuster_production", "branch": "Product", "tier": 5, "name": "Blockbuster Production", "cost": 4_500_000, "work": 12_000, "prereq": ("large_production", "executive_management"), "effect": "Unlock Blockbuster games"},
    {"key": "mmo_technology", "branch": "Product", "tier": 5, "name": "Massive Online Technology", "cost": 8_000_000, "work": 15_000, "prereq": ("persistent_worlds", "blockbuster_production"), "effect": "Unlock MMO development"},
    {"key": "internal_engine", "branch": "Product", "tier": 5, "name": "Internal Engine Program", "cost": 3_200_000, "work": 10_000, "prereq": ("large_production", "research_lab"), "effect": "Unlock engine projects (preview)"},

    # Studio operations
    {"key": "garage_workflow", "branch": "Operations", "tier": 0, "name": "Garage Workflow", "cost": 0, "work": 0, "prereq": (), "effect": "One project and manual management"},
    {"key": "hardware", "branch": "Operations", "tier": 1, "name": "Current Workstations", "cost": 12_000, "work": 300, "monthly": 180, "prereq": ("garage_workflow",), "effect": "+10% work output"},
    {"key": "tools", "branch": "Operations", "tier": 1, "name": "Professional Toolchain", "cost": 18_000, "work": 420, "monthly": 450, "prereq": ("garage_workflow",), "effect": "+4 release quality"},
    {"key": "production_pipeline", "branch": "Operations", "tier": 2, "name": "Production Pipeline", "cost": 42_000, "work": 900, "prereq": ("hardware",), "effect": "Better coordination for teams above five"},
    {"key": "qa", "branch": "Operations", "tier": 2, "name": "QA Device Library", "cost": 28_000, "work": 800, "monthly": 320, "prereq": ("tools",), "effect": "Fewer defects and faster discovery"},
    {"key": "research_lab", "branch": "Operations", "tier": 2, "name": "Research Lab", "cost": 55_000, "work": 1_100, "monthly": 650, "prereq": ("production_pipeline",), "effect": "+20% research output"},
    {"key": "department_leads", "branch": "Operations", "tier": 3, "name": "Department Leads", "cost": 140_000, "work": 2_200, "monthly": 1_400, "prereq": ("production_pipeline", "mentorship"), "effect": "Unlock automatic work priorities"},
    {"key": "portfolio_management", "branch": "Operations", "tier": 3, "name": "Portfolio Management", "cost": 160_000, "work": 2_600, "monthly": 850, "prereq": ("department_leads", "content_updates"), "effect": "Set released games to active, maintenance or sunset support"},
    {"key": "advanced_coordination", "branch": "Operations", "tier": 4, "name": "Advanced Coordination", "cost": 520_000, "work": 5_000, "monthly": 3_200, "prereq": ("department_leads",), "effect": "Large teams retain more marginal output"},
    {"key": "executive_management", "branch": "Operations", "tier": 5, "name": "Executive Management", "cost": 2_200_000, "work": 9_000, "monthly": 9_000, "prereq": ("advanced_coordination",), "effect": "Late-game automation and lower off-branch penalty"},

    # People and culture
    {"key": "basic_rest", "branch": "People", "tier": 0, "name": "Basic Rest Policy", "cost": 0, "work": 0, "prereq": (), "effect": "Manual one-week vacations"},
    {"key": "mentorship", "branch": "People", "tier": 1, "name": "Mentorship", "cost": 5_000, "work": 260, "prereq": ("basic_rest",), "effect": "+25% experience gain"},
    {"key": "structured_training", "branch": "People", "tier": 1, "name": "Structured Training", "cost": 8_000, "work": 380, "prereq": ("basic_rest",), "effect": "Training takes three weeks"},
    {"key": "paid_leave", "branch": "People", "tier": 2, "name": "Paid Leave Program", "cost": 16_000, "work": 650, "monthly": 180, "per_employee": 55, "prereq": ("structured_training",), "effect": "Vacations recover more fatigue and morale"},
    {"key": "health", "branch": "People", "tier": 2, "name": "Health Plan", "cost": 28_000, "work": 850, "monthly": 900, "per_employee": 380, "prereq": ("paid_leave",), "effect": "Slower fatigue and burnout recovery"},
    {"key": "coworking", "branch": "People", "tier": 2, "name": "Coworking Studio", "cost": 40_000, "work": 900, "monthly": 2_200, "prereq": ("paid_leave",), "effect": "+5 monthly morale"},
    {"key": "auto_leave", "branch": "People", "tier": 3, "name": "Sustainable Scheduling", "cost": 85_000, "work": 1_800, "prereq": ("health", "department_leads"), "effect": "Automatically schedule vacation at high fatigue"},
    {"key": "academy", "branch": "People", "tier": 4, "name": "Internal Academy", "cost": 420_000, "work": 4_500, "monthly": 4_500, "prereq": ("mentorship", "structured_training"), "effect": "+35% experience and stronger courses"},

    # Marketing and business
    {"key": "contract_basics", "branch": "Business", "tier": 0, "name": "Contract Basics", "cost": 0, "work": 0, "prereq": (), "effect": "Manual contract work"},
    {"key": "promotion_basics", "branch": "Business", "tier": 1, "name": "Community Marketing", "cost": 6_500, "work": 350, "prereq": ("contract_basics",), "effect": "Unlock community launch plans and social promotion"},
    {"key": "market_research", "branch": "Business", "tier": 1, "name": "Market Research", "cost": 8_000, "work": 420, "prereq": ("contract_basics",), "effect": "+10 forecast confidence"},
    {"key": "targeted_marketing", "branch": "Business", "tier": 2, "name": "Targeted Marketing", "cost": 32_000, "work": 900, "prereq": ("promotion_basics",), "effect": "Unlock targeted campaigns and press outreach"},
    {"key": "mobile_distribution", "branch": "Business", "tier": 2, "name": "Mobile Distribution", "cost": 45_000, "work": 1_000, "prereq": ("market_research",), "effect": "Unlock mobile storefronts"},
    {"key": "creator_relations", "branch": "Business", "tier": 3, "name": "Creator Relations", "cost": 110_000, "work": 2_000, "prereq": ("targeted_marketing",), "effect": "Unlock creator and streamer campaigns"},
    {"key": "console_certification", "branch": "Business", "tier": 3, "name": "Console Certification", "cost": 220_000, "work": 2_500, "prereq": ("mobile_distribution", "qa"), "effect": "Unlock console storefronts"},
    {"key": "analytics", "branch": "Business", "tier": 3, "name": "Store Analytics", "cost": 75_000, "work": 1_600, "monthly": 350, "prereq": ("market_research",), "effect": "+2% weekly sales retention"},
    {"key": "event_marketing", "branch": "Business", "tier": 4, "name": "Events & Showcases", "cost": 320_000, "work": 4_000, "prereq": ("creator_relations",), "effect": "Unlock events and premium showcases"},
    {"key": "contract_automation", "branch": "Business", "tier": 4, "name": "Client Relations Office", "cost": 260_000, "work": 3_500, "prereq": ("department_leads",), "effect": "Unlock automatic contract policies"},

    # Live operations
    {"key": "basic_support", "branch": "Live Ops", "tier": 0, "name": "Basic Support", "cost": 0, "work": 0, "prereq": (), "effect": "Hotfixes and patches"},
    {"key": "content_updates", "branch": "Live Ops", "tier": 1, "name": "Content Updates", "cost": 12_000, "work": 500, "prereq": ("basic_support",), "effect": "Unlock content updates"},
    {"key": "expansion_pipeline", "branch": "Live Ops", "tier": 2, "name": "Expansion Pipeline", "cost": 55_000, "work": 1_300, "prereq": ("content_updates", "production_pipeline"), "effect": "Unlock expansions"},
    {"key": "paid_dlc", "branch": "Live Ops", "tier": 3, "name": "Paid DLC Pipeline", "cost": 150_000, "work": 2_500, "prereq": ("expansion_pipeline", "targeted_marketing"), "effect": "Unlock Paid DLC and DLC roadmaps"},
    {"key": "live_operations", "branch": "Live Ops", "tier": 4, "name": "Live Operations Department", "cost": 520_000, "work": 5_000, "monthly": 4_500, "prereq": ("paid_dlc", "department_leads"), "effect": "Unlock live-service plans"},
    {"key": "automated_deployment", "branch": "Live Ops", "tier": 4, "name": "Automated Deployment", "cost": 280_000, "work": 3_800, "prereq": ("qa", "expansion_pipeline"), "effect": "+20% update and DLC output"},
)

# Kept as the public name used by the existing Upgrades page and tests.
UPGRADES = RESEARCH_NODES
RESEARCH_BY_KEY = {node["key"]: node for node in RESEARCH_NODES}
RESEARCH_BRANCHES = tuple(dict.fromkeys(node["branch"] for node in RESEARCH_NODES))

STARTER_GENRES = {
    "Action", "Adventure", "Platformer", "Puzzle Game", "Simulation", "Skill Game",
}
GENRE_UNLOCKS = {
    "genre_story": {"Interactive Movie", "Role-Playing Game", "Visual Novel", "Soulslike", "Metroidvania"},
    "genre_systems": {"Building Game", "Economic Simulation", "Real-Time Strategy", "Strategy", "Automation"},
    "genre_action": {"Fighting Game", "First-Person Shooter", "Racing", "Sports Game", "Survival Game", "Third-Person Shooter", "Battle Royale", "Extraction Shooter"},
    "genre_indie": {"Survivors-like", "Roguelike", "Roguelite", "Deckbuilder", "Cozy Game", "Social Deduction", "Immersive Sim"},
}
STARTER_TOPICS = set(TOPICS[::7])

FRANCHISE_RANKS = ("Unknown", "Niche", "Recognized", "Established", "Popular", "Famous", "Legendary", "Iconic")
FRANCHISE_RANK_THRESHOLDS = (10_000, 100_000, 500_000, 1_000_000, 2_500_000, 5_000_000, 10_000_000)

MEDIA_VENTURES = (
    {"key": "merch", "name": "Merchandise line", "cost": 28_000, "weeks": 26, "rank": 1, "effect": "Steady weekly merch revenue from the fanbase"},
    {"key": "convention", "name": "Fan convention", "cost": 180_000, "weeks": 3, "rank": 4, "effect": "Big awareness and hype surge for the whole IP"},
    {"key": "film", "name": "Film adaptation", "cost": 2_800_000, "weeks": 40, "rank": 5, "effect": "Box-office release after production; quality decides the payoff"},
    {"key": "series", "name": "Series adaptation", "cost": 6_500_000, "weeks": 52, "rank": 5, "effect": "Prestige streaming series; the largest transmedia payoff"},
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
    {"name": "Nocturne Labs", "tier": "studio", "size": 2.6, "genres": ("Survival Game", "Adventure", "Immersive Sim", "Visual Novel"), "fanbase": 210_000, "reputation": 74},
    {"name": "Quantum Quill", "tier": "studio", "size": 3.4, "genres": ("Strategy", "Deckbuilder", "Economic Simulation"), "fanbase": 380_000, "reputation": 79},
    {"name": "Vantage Point", "tier": "publisher", "size": 5.8, "genres": ("First-Person Shooter", "Extraction Shooter", "Battle Royale"), "fanbase": 1_100_000, "reputation": 66},
    {"name": "Lumen Works", "tier": "indie", "size": 1.4, "genres": ("Puzzle Game", "Cozy Game", "Automation"), "fanbase": 85_000, "reputation": 81},
    {"name": "Driftwood Games", "tier": "indie", "size": 1.2, "genres": ("Survival Game", "Building Game", "Simulation"), "fanbase": 95_000, "reputation": 71},
    {"name": "Redwood Arcade", "tier": "studio", "size": 2.2, "genres": ("Racing", "Sports Game", "Fighting Game"), "fanbase": 260_000, "reputation": 69},
    {"name": "Heliosoft", "tier": "publisher", "size": 6.8, "genres": ("Role-Playing Game", "Strategy", "Social Deduction", "Battle Royale"), "fanbase": 1_500_000, "reputation": 73},
    {"name": "Papercut Studio", "tier": "indie", "size": 0.9, "genres": ("Visual Novel", "Interactive Movie", "Cozy Game"), "fanbase": 40_000, "reputation": 76},
)

COMPETITOR_IP_NAMES = (
    "Starforged", "Emberfall", "Quantum Drift", "Shadowvale", "Iron Tide", "Moonlit Acres",
    "Gravball", "Night Circuit", "Deep Hollow", "Skybound Odyssey", "Crimson Pact", "Hollowlight",
    "Turbo Dynasty", "Whisker Works", "Astral Siege", "Frostline", "Byte Raiders", "Dune Runners",
    "Silent Grove", "Mecha Bloom", "Void Cartel", "Paper Kingdoms", "Thunder Vale", "Neon Harvest",
    "Ashen Circuit", "Briar Ritual", "Chrome Divide", "Dusk Harbor", "Echowild", "Flux Garden",
)

EXPANDED_COMPETITOR_NAMES = (
    "Blue Harbor", "Ironclad Softworks", "Mosslight", "Signal Peak", "Hearthfire", "Kiteframe",
    "Copper Owl", "Lighthouse Labs", "Mammoth Byte", "Pinecone Interactive", "Cobalt Fox",
    "Velvet Hammer", "Afterimage", "Lanternfish", "Morrow Digital", "Wild Orbit",
    "Blackbird Assembly", "Riverstone", "Glass Compass", "Firebreak", "Oxbow Studio",
    "Daybreak Collective", "Fableworks", "Snowcap", "Sundial Games", "Tangent Studio",
)

SEGMENT_KEYS = ("core", "casual", "enthusiast", "live")
SEGMENT_NAMES = {"core": "Core fans", "casual": "Casual players", "enthusiast": "Enthusiasts", "live": "Live players"}
SEGMENT_MOODS = ((85, "Euphoric"), (65, "Content"), (45, "Skeptical"), (25, "Angry"), (0, "Leaving"))
SCOPE_HYPE_CEILING = {"Micro": 45, "Compact": 60, "Small": 80, "Mid-size": 105, "Ambitious": 130, "Large": 165, "Blockbuster": 215}

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
    vacation_weeks_left: int = 0
    burnout_weeks_left: int = 0
    career_level: int = 1
    lifetime_experience: int = 0
    week_output: float = 0.0
    onboarding_weeks_left: int = 0
    salary_satisfaction: float = 70.0
    institutional_knowledge: float = 0.0
    last_review_year: int = 0

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
    market_score_start: int = 50
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
    known_defects: float = 0.0
    bug_work: float = 0.0
    bug_work_done: float = 0.0
    publisher: str = ""
    publisher_advance: float = 0.0
    publisher_recoup_share: float = 0.0
    publisher_post_recoup_share: float = 0.0
    publisher_visibility: int = 0
    monetization: str = "premium"
    announcement_strategy: str = "late_reveal"
    release_policy: str = "ship_when_ready"
    announced_week: int = 0
    promised_release_week: int = 0
    ready_for_release: bool = False
    ready_week: int = 0
    early_access: bool = False
    early_access_week: int = 0
    early_access_game_id: int = 0
    early_access_units: int = 0
    early_access_revenue: float = 0.0
    early_access_owners_by_cohort: dict[str, int] = field(default_factory=dict)
    early_access_rating: float = 0.0
    awareness_by_cohort: dict[str, float] = field(default_factory=dict)
    wishlists_by_cohort: dict[str, int] = field(default_factory=dict)
    promises: list[dict] = field(default_factory=list)
    quality_dimensions: dict[str, float] = field(default_factory=dict)
    technical_debt: float = 0.0
    trust: float = 50.0
    novelty: float = 50.0
    cultural_resonance: dict[str, float] = field(default_factory=dict)
    forecast_work_low: int = 0
    forecast_work_high: int = 0

    @property
    def progress(self) -> float:
        return min(1.0, self.work_done / self.total_work)

    @property
    def bug_progress(self) -> float:
        return min(1.0, self.bug_work_done / self.bug_work) if self.bug_work else 0.0

    @property
    def bugs_to_clear(self) -> int:
        if not self.bug_work:
            return 0
        return max(0, math.ceil((self.bug_work - self.bug_work_done) / BUG_FIX_WORK_PER_DEFECT))

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
    evergreen_units: float = 1.0
    week_units: float = 0.0
    publisher: str = ""
    publisher_recoup_share: float = 0.0
    publisher_post_recoup_share: float = 0.0
    publisher_recoupable: float = 0.0
    publisher_recouped: float = 0.0
    awareness_by_cohort: dict[str, float] = field(default_factory=dict)
    owners_by_cohort: dict[str, int] = field(default_factory=dict)
    refunded_by_cohort: dict[str, int] = field(default_factory=dict)
    interested_by_cohort: dict[str, int] = field(default_factory=dict)
    wishlists_by_cohort: dict[str, int] = field(default_factory=dict)
    payers_by_cohort: dict[str, int] = field(default_factory=dict)
    weekly_result_by_cohort: dict[str, int] = field(default_factory=dict)
    unmet_potential: int = 0
    demand_drivers: list[str] = field(default_factory=list)
    lifecycle_state: str = "launch"
    age_weeks: int = 0
    price_history: list[dict] = field(default_factory=list)

    @property
    def week_to_date(self) -> int:
        return round(self.week_units)


@dataclass
class Segment:
    key: str
    satisfaction: float = 70.0
    weight: float = 0.25
    expectation: float = 60.0
    mood: str = "Content"
    trend: float = 0.0
    note: str = ""


@dataclass
class ReleasedGame:
    game_id: int
    title: str
    genre: str
    topic: str
    channel: str
    score: int
    release_date: str
    release_week: int = 0
    sequel_of: int | None = None
    generation: int = 1
    franchise_id: int | None = None
    units_sold: int = 0
    net_revenue: float = 0.0
    hype: float = 0.0
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
    peak_weekly_sales: int = 0
    chart_peak: int = 0
    support_level: str = "Active"
    last_update_week: int = 0
    segments: list[Segment] = field(default_factory=list)
    patch_fatigue: float = 0.0
    hype_backlash: float = 0.0
    fans_betrayed: bool = False
    publisher: str = ""
    publisher_advance: float = 0.0
    publisher_recouped: float = 0.0
    monetization: str = "premium"
    announcement_strategy: str = "late_reveal"
    release_policy: str = "ship_when_ready"
    quality_dimensions: dict[str, float] = field(default_factory=dict)
    cultural_resonance: dict[str, float] = field(default_factory=dict)
    novelty: float = 50.0
    trust: float = 50.0
    sentiment: float = 50.0
    review_count: int = 0
    positive_reviews: int = 0
    negative_reviews: int = 0
    refunded_units: int = 0
    aware_players: int = 0
    interested_players: int = 0
    wishlists: int = 0
    payers: int = 0
    recurring_revenue: float = 0.0
    weekly_recurring_revenue: float = 0.0
    platform_deductions: float = 0.0
    publisher_deductions: float = 0.0
    refund_value: float = 0.0
    lifecycle_state: str = "launch"
    viral_coefficient: float = 0.0
    network_health: float = 100.0
    technical_debt: float = 0.0
    issues: list[dict] = field(default_factory=list)
    promises: list[dict] = field(default_factory=list)
    postmortem: dict = field(default_factory=dict)
    dlc_owners: dict[str, dict[str, int]] = field(default_factory=dict)
    early_access: bool = False
    early_access_week: int = 0

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
    cost_paid: int = 0

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
    client: str = ""
    focus: str = "Generalist"
    difficulty: int = 1
    required_work: float = 0.0
    work_done: float = 0.0
    reputation_required: int = 0
    auto_accepted: bool = False
    accepted_week: int = 0
    expires_week: int = 0
    original_deadline_week: int = 0
    deposit: int = 0
    late_penalty: int = 0
    quality_target: int = 50
    rework_rounds: int = 0
    labor_cost: float = 0.0


@dataclass
class LedgerMonth:
    month: str
    revenue: int
    expenses: int
    net: int
    categories: dict[str, int] = field(default_factory=dict)
    revenue_categories: dict[str, int] = field(default_factory=dict)


@dataclass
class Loan:
    name: str
    principal: float
    balance: float
    annual_rate: float
    weeks_left: int
    weekly_payment: float


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
        return sum(self.total_units >= threshold for threshold in FRANCHISE_RANK_THRESHOLDS)

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
    channel: str = "Steam"


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
    growth_points: float = 0.0
    tools_level: int = 0
    releases_completed: int = 0
    cash: float = 1_000_000.0
    monthly_burn: float = 50_000.0
    debt: float = 0.0
    risk_tolerance: float = 0.5
    closed: bool = False
    failures: int = 0


@dataclass
class ResearchJob:
    node_key: str
    required_work: float
    cost: int
    work_done: float = 0.0

    @property
    def progress(self) -> float:
        return min(1.0, self.work_done / max(1.0, self.required_work))


@dataclass
class Studio:
    cash: float = 100_000.0
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
    genre_heat: dict[str, float] = field(default_factory=dict)
    contractor_reputation: float = 0.0
    contracts_completed: int = 0
    contracts_failed: int = 0
    active_update: UpdateJob | None = None
    update_queue: list[UpdateJob] = field(default_factory=list)
    active_promotions: list[Promotion] = field(default_factory=list)
    franchises: list[Franchise] = field(default_factory=list)
    media_ventures: list[MediaVenture] = field(default_factory=list)
    competitors: list[Competitor] = field(default_factory=list)
    upgrades: list[str] = field(default_factory=list)
    completed_research: list[str] = field(default_factory=lambda: list(STARTER_RESEARCH))
    active_research: ResearchJob | None = None
    research_queue: list[ResearchJob] = field(default_factory=list)
    work_priorities: dict[str, int] = field(default_factory=lambda: {"project": 3, "contract": 2, "update": 2, "promotion": 1, "research": 1})
    auto_vacation: bool = False
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
    loans: list[Loan] = field(default_factory=list)
    pending_publisher: str = ""
    name: str = "New Studio"
    founded_date: str = ""
    transactions: list[dict] = field(default_factory=list)
    next_transaction_id: int = 1
    tax_loss_carryforward: float = 0.0
    tax_payable: float = 0.0
    committed_payments: list[dict] = field(default_factory=list)
    hosting_history: list[float] = field(default_factory=list)
    macro_spending: float = 1.0
    macro_confidence: float = 1.0
    platform_demand: dict[str, float] = field(default_factory=lambda: {"PC": 1.0, "Console": 1.0, "Handheld": 1.0, "Mobile": 1.0})
    inflation_index: float = 1.0
    wage_index: float = 1.0
    interest_rate: float = 0.055
    market_experience: dict[str, float] = field(default_factory=dict)
    forecast_calibration: dict[str, float] = field(default_factory=dict)
    client_relationships: dict[str, float] = field(default_factory=dict)
    studio_trust: float = 50.0
    community_capacity: float = 0.0
    active_community_actions: list[dict] = field(default_factory=list)
    community_cooldowns: dict[str, int] = field(default_factory=dict)
    itch_releases: int = 0


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
    selected_monetization: int = 0
    selected_price: int = -1
    selected_announcement: int = 1
    selected_release_policy: int = 0
    selected_community_action: int = 0
    selected_project_decision: int = 0
    selected_focus: int = 0
    mix_blend: bool = False
    mix_blend_backup: tuple = (0, 0)
    focus: list[int] = field(default_factory=lambda: [30, 25, 15, 30])
    selected_employee: int = 0
    selected_roster: int = 0
    selected_upgrade: int = 0
    selected_research_branch: int = 0
    selected_contract: int = 0
    selected_game: int = 0
    selected_promotion: int = 0
    selected_promotion_target: int = 0
    selected_venture: int = 0
    finance_tab: int = 0
    selected_finance_offer: int = 0
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
    save_picker_open: bool = False
    save_picker_mode: str = ""
    selected_save_slot: int = 0
    save_slots: list[str] = field(default_factory=list)
    training_open: bool = False
    training_resume_on_close: bool = False
    selected_training_skill: int = 0
    cancel_project_open: bool = False
    cancel_project_resume_on_close: bool = False
    selected_cancel_project_action: int = 0
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
    new_game_kind: str = ""
    time_speed_index: int = 1
    resume_speed_index: int = 1
    save_path: str = "saves/gamedev_save.json"
    logs: list[str] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    event_history: list[dict] = field(default_factory=list)
    next_event_id: int = 1
    last_read_event_id: int = 0

    def __post_init__(self) -> None:
        if not self.studio.team:
            self.studio.team.append(
                Employee(1, "You", "Founder / Generalist", 58, 48, 38, 62, 36_000, founder=True)
            )
        if not self.studio.accounting_month:
            self.studio.accounting_month = self.clock.current_date.strftime("%Y-%m")
        if not self.studio.founded_date:
            self.studio.founded_date = self.clock.current_date.isoformat()
        if not self.studio.applicants:
            refresh_applicants(self)
        if not self.studio.contract_offers:
            refresh_contract_offers(self, announce=False)
        if not self.draft_title:
            refresh_draft_title(self)
        if not self.studio.competitors:
            seed_market(self)
        if not self.logs:
            self.logs = [
                f"{self.clock.current_date:%d %b %Y}: you open a bootstrapped indie studio with $100,000.",
                "Cash is runway. Payroll, software, insurance, tax, refunds, and store cuts are real.",
                "Start in the Hub for an overview. Tab cycles pages; G opens Game, J opens Jobs, and T opens Team.",
            ]

    def log(self, message: str) -> None:
        self.logs.insert(0, message)
        del self.logs[100:]

    @classmethod
    def new_campaign(cls, save_path: str = "saves/gamedev_save.json", studio_name: str = "New Studio") -> GameState:
        """Create a unique campaign while direct construction stays deterministic for tests."""
        seed = secrets.randbits(63) or 1
        state = cls(studio=Studio(seed=seed, name=studio_name), save_path=save_path)
        # New developers start where everyone starts: tiny free games on itch.io.
        state.selected_channel = next(index for index, channel in enumerate(CHANNELS) if channel["name"] == "itch.io")
        state.selected_monetization = next(index for index, model in enumerate(MONETIZATION_MODELS) if model["key"] == "donationware")
        state.selected_scope = next(index for index, scope in enumerate(SCOPES) if scope["name"] == "Bite-size")
        return state


def channel_by_name(name: str) -> dict:
    return next(channel for channel in CHANNELS if channel["name"] == name)


def marketing_by_name(name: str) -> dict:
    return next(marketing for marketing in MARKETING if marketing["name"] == name)


def scope_by_name(name: str) -> dict:
    return next(scope for scope in SCOPES if scope["name"] == name)


def format_by_name(name: str) -> dict:
    return next((item for item in GAME_FORMATS if item["name"] == name), GAME_FORMATS[0])


def creative_by_name(name: str) -> dict:
    return next((item for item in CREATIVE_DIRECTIONS if item["name"] == name), CREATIVE_DIRECTIONS[0])


def release_strategy_by_name(name: str) -> dict:
    return next((item for item in RELEASE_STRATEGIES if item["name"] == name), RELEASE_STRATEGIES[0])


def selected_monetization_model(state: GameState) -> dict:
    return MONETIZATION_MODELS[state.selected_monetization % len(MONETIZATION_MODELS)]


def selected_price_point(state: GameState) -> dict:
    if state.selected_price >= 0:
        return PRICE_POINTS[state.selected_price % len(PRICE_POINTS)]
    model = selected_monetization_model(state)
    if float(model["default_price"]) <= 0:
        return PRICE_POINTS[0]
    scope = SCOPES[state.selected_scope]
    audience = AUDIENCES[state.selected_audience]
    strategy = RELEASE_STRATEGIES[state.selected_release_strategy]
    target = scope["price"] * audience["price"] * strategy["price"]
    return min(PRICE_POINTS, key=lambda point: abs(float(point["price"]) - target))


def selected_announcement_strategy(state: GameState) -> dict:
    return ANNOUNCEMENT_STRATEGIES[state.selected_announcement % len(ANNOUNCEMENT_STRATEGIES)]


def selected_release_policy(state: GameState) -> dict:
    return RELEASE_POLICIES[state.selected_release_policy % len(RELEASE_POLICIES)]


def monetization_by_key(key: str) -> dict:
    return monetization_model_by_key(key) or MONETIZATION_MODELS[0]


def studio_macro_snapshot(studio: Studio) -> MacroSnapshot:
    return MacroSnapshot(
        spending_multiplier=studio.macro_spending,
        consumer_confidence=studio.macro_confidence,
        inflation_rate=max(0.0, studio.inflation_index - 1.0),
        platform_demand_multipliers=studio.platform_demand,
    )


def initial_awareness_by_cohort(state: GameState, hype: float, marketing_boost: float, announcement_key: str) -> dict[str, float]:
    announcement = announcement_strategy_by_key(announcement_key) or ANNOUNCEMENT_STRATEGIES[1]
    # Reputation alone barely moves an algorithm; a studio the market knows
    # (high reputation AND followers) earns real brand awareness.
    brand = min(0.10, (state.studio.reputation / 100.0) ** 4 * 0.06 + state.studio.followers / 10_000_000)
    paid = min(0.22, marketing_boost / 60_000)
    hype_reach = min(0.15, max(0.0, hype) / 4_000)
    base = max(0.0001, min(0.75, (0.0001 + brand + paid + hype_reach) * float(announcement["awareness"])))
    awareness = {}
    for cohort in COHORTS:
        regional_variation = 0.90 + ((sum(ord(char) for char in cohort.key) + state.studio.seed) % 21) / 100
        awareness[cohort.key] = max(0.0001, min(0.95, base * regional_variation))
    return awareness


def studio_store_visibility(studio: Studio) -> float:
    """Storefront algorithmic reach for this studio's releases.

    Unknown developers are buried: their store pages convert far below the
    channel baseline. Followers and industry reputation are what lift you
    toward full visibility.
    """
    return 0.25 + 0.75 * min(1.0, studio.followers / 50_000 + studio.reputation / 300)


# Creative directions whose names carry a direct quality-dimension bonus.
# Keyed by exact direction name so renames in the tuple surface as missing
# bonuses instead of silently changing balance.
_DIRECTION_QUALITY_TRAITS = {
    "Bold new mechanic": {"originality": 10.0},
    "A striking world": {"originality": 4.0},
    "Deep systemic play": {"depth": 8.0},
    "Endless mastery": {"depth": 8.0},
}


def _direction_quality_traits(project: Project) -> dict[str, float]:
    bonuses: dict[str, float] = {}
    for name in (project.creative_primary, project.creative_secondary):
        for trait, value in _DIRECTION_QUALITY_TRAITS.get(name, {}).items():
            bonuses[trait] = bonuses.get(trait, 0.0) + value
    return bonuses


def project_quality_dimensions(studio: Studio, project: Project, average_skill: float, defect_penalty: float, focus_bonus: float) -> dict[str, float]:
    team_skills = [sum(employee.skills[index] for employee in studio.team) / max(1, len(studio.team)) for index in range(4)]
    traits = _direction_quality_traits(project)
    innovation = project.market_score + traits.get("originality", 0.0)
    depth = average_skill + traits.get("depth", 0.0)
    accessibility = average_skill + (8 if project.target_audience in ("Broad audience", "Kids & families", "Cozy & casual") else -3)
    stability = 92 - defect_penalty * 2 - project.technical_debt * 0.35
    online = team_skills[3] + (8 if project.game_format == "Offline solo" else -format_by_name(project.game_format)["risk"])
    return {
        "gameplay": max(10.0, min(99.0, average_skill + focus_bonus)),
        "depth": max(10.0, min(99.0, depth)),
        "content": max(10.0, min(99.0, average_skill + min(15, math.sqrt(max(1, len(studio.team))) * 3) - scope_by_name(project.scope)["risk"])),
        "originality": max(10.0, min(99.0, innovation)),
        "art": max(10.0, min(99.0, team_skills[1] + creative_by_name(project.creative_primary)["quality"])),
        "audio": max(10.0, min(99.0, team_skills[2])),
        "ux": max(10.0, min(99.0, accessibility)),
        "stability": max(5.0, min(99.0, stability)),
        "performance": max(5.0, min(99.0, team_skills[3] - project.technical_debt * 0.2)),
        "online": max(5.0, min(99.0, online)),
    }


def product_offer_for_game(state: GameState, game: ReleasedGame, sale: ActiveSale | None = None) -> ProductOffer:
    sale = sale or sale_for_game(state.studio, game.game_id)
    awareness = sale.awareness_by_cohort if sale else {}
    owners = sale.owners_by_cohort if sale else {}
    novelty = max(5.0, game.novelty - max(0, state.clock.week - game.release_week) * 0.28)
    strategy = release_strategy_by_name(game.release_strategy)
    expected_cadence = int(strategy.get("expect_weeks", 0))
    stale_weeks = max(0, state.clock.week - game.last_update_week - expected_cadence) if expected_cadence else 0
    stale_trust_drag = min(35.0, stale_weeks * 1.8)
    stale_network_multiplier = max(0.20, 1 - stale_weeks * 0.055)
    return ProductOffer(
        product_id=f"player:{game.game_id}",
        genre=game.genre,
        secondary_genre=game.secondary_genre,
        topic=game.topic,
        target_audience=game.target_audience,
        game_format=game.game_format,
        monetization=game.monetization,
        price=game.price,
        quality=game.score,
        user_rating=game.user_rating,
        awareness_by_cohort=awareness,
        owners_by_cohort=owners,
        age_weeks=max(0, state.clock.week - game.release_week),
        hype=game.hype,
        trust=max(0.0, (game.trust + state.studio.studio_trust) / 2 - stale_trust_drag),
        sentiment=max(0.0, (game.sentiment or game.user_rating) - stale_trust_drag * 0.8),
        novelty=novelty,
        network_health=game.network_health * stale_network_multiplier,
        store_reach=channel_by_name(game.channel)["reach"] * studio_store_visibility(state.studio),
        platform_category=channel_by_name(game.channel)["category"],
        cultural_resonance=game.cultural_resonance or 50.0,
        lifecycle_state=game.lifecycle_state,
    )


def competitor_product_offers(state: GameState) -> list[ProductOffer]:
    offers = []
    for competitor in state.studio.competitors:
        if competitor.closed:
            continue
        for index, release in enumerate(competitor.recent_releases):
            age = max(0, state.clock.week - release.released_week)
            if age > 104 or release.weekly_units < 1:
                continue
            awareness = min(0.75, 0.015 + competitor.fanbase / 8_000_000 + release.hype / 1_200)
            offers.append(
                ProductOffer(
                    product_id=f"rival:{competitor.competitor_id}:{index}",
                    genre=release.genre,
                    topic="",
                    game_format="Offline solo",
                    monetization="premium",
                    price=39.99,
                    quality=release.quality,
                    user_rating=release.quality,
                    awareness_by_cohort={cohort.key: awareness for cohort in COHORTS},
                    owners_by_cohort={},
                    age_weeks=age,
                    hype=release.hype,
                    trust=competitor.reputation,
                    sentiment=release.quality,
                    novelty=max(10, 85 - age),
                    network_health=70,
                    store_reach=channel_by_name(release.channel)["reach"],
                    platform_category=channel_by_name(release.channel)["category"],
                    cultural_resonance=50,
                    lifecycle_state="launch" if age <= 1 else "active" if age <= 30 else "mature",
                )
            )
    return offers


def allocate_weekly_market(state: GameState) -> dict[str, DemandResult]:
    """Allocate this week's finite demand once for the whole market.

    The player's catalog and every rival release compete in a single
    ``allocate_weekly_demand`` call so one shopper pool cannot be spent twice.
    Results are keyed by offer id: ``"player:{game_id}"`` for the studio's
    games and ``"rival:{competitor_id}:{index}"`` for competitor releases.
    """
    offers = []
    for game in state.studio.catalog:
        sale = sale_for_game(state.studio, game.game_id)
        if sale is None or game.lifecycle_state in ("delisted", "closed"):
            continue
        offers.append(product_offer_for_game(state, game, sale))
    offers.extend(competitor_product_offers(state))
    if not offers:
        return {}
    results = allocate_weekly_demand(offers, studio_macro_snapshot(state.studio), state.studio.seed + state.clock.week * 17_389)
    return {result.product_id: result for result in results}


def player_demand_result(market_results: dict[str, DemandResult], game_id: int) -> DemandResult | None:
    return market_results.get(f"player:{game_id}")


def segment_weights_for(game_format: str, target_audience: str) -> dict[str, float]:
    if game_format == "Offline solo":
        weights = {"core": 0.35, "casual": 0.40, "enthusiast": 0.25, "live": 0.0}
    else:
        weights = {"core": 0.30, "casual": 0.25, "enthusiast": 0.15, "live": 0.30}
    if target_audience in ("Cozy & casual", "Kids & families", "Social groups"):
        weights["casual"] += 0.10
        weights["core"] = max(0.10, weights["core"] - 0.10)
    elif target_audience in ("Core players", "Strategy enthusiasts"):
        weights["core"] += 0.10
        weights["casual"] = max(0.10, weights["casual"] - 0.10)
    return weights


def segment_mood(satisfaction: float) -> str:
    for threshold, mood in SEGMENT_MOODS:
        if satisfaction >= threshold:
            return mood
    return "Leaving"


def community_insight(studio: Studio) -> int:
    if has_research(studio, "analytics"):
        return 2
    if has_research(studio, "market_research"):
        return 1
    return 0


def segment_rating_anchor(game: ReleasedGame) -> float | None:
    """Weighted community-segment view of the game, or None without segments."""
    active = [segment for segment in game.segments if segment.weight > 0]
    total_weight = sum(segment.weight for segment in active)
    if not active or total_weight <= 0:
        return None
    return sum(segment.satisfaction * segment.weight for segment in active) / total_weight


def aggregate_user_rating(game: ReleasedGame) -> float:
    anchor = segment_rating_anchor(game)
    return game.user_rating if anchor is None else anchor


def community_factor(game: ReleasedGame) -> float:
    trust = max(0.2, min(1.25, game.trust / 65))
    return max(0.20, min(1.60, (aggregate_user_rating(game) / 72) * trust))


def build_segments(studio: Studio, project: Project, score: int, known_bugs: float, sequel_quality: int, sequel_fatigue: int, rating_rng: random.Random) -> list[Segment]:
    weights = segment_weights_for(project.game_format, project.target_audience)
    franchise = franchise_by_id(studio, project.franchise_id)
    marketing = marketing_by_name(project.marketing_name)
    expectation_base = 55 + studio.reputation * 0.25 + (franchise.rank * 2 if franchise else 0) + marketing["boost"] / 140
    fatigue = franchise.fatigue if franchise else 0.0
    backlash = max(0.0, project.hype - (SCOPE_HYPE_CEILING.get(project.scope, 100) + max(0, project.market_score - 55)))
    novelty = max(-8.0, min(8.0, (project.market_score - 60) / 5))
    segments = []
    for key in SEGMENT_KEYS:
        weight = weights[key]
        expectation = expectation_base + {"core": 4, "casual": -8, "enthusiast": 10, "live": 6}[key]
        adjustment = {
            "core": sequel_quality * 1.5,
            "casual": -min(25.0, known_bugs * 1.0),
            "enthusiast": novelty - fatigue * 0.1 - sequel_fatigue * 2,
            "live": -min(15.0, known_bugs * 0.6),
        }[key]
        if key in ("casual", "enthusiast"):
            adjustment -= min(15.0, backlash * 0.5)
        satisfaction = max(5.0, min(92.0, score - (expectation - 60) * 0.6 + adjustment + rating_rng.uniform(-6, 6)))
        segments.append(Segment(key, round(satisfaction, 1), weight, round(expectation, 1), segment_mood(satisfaction)))
    return segments


def segment_target(state: GameState, game: ReleasedGame, segment: Segment, franchise: Franchise | None, stale_weeks: int, years_old: float) -> tuple[float, str]:
    score = game.score
    bug_drag = min(28.0, game.known_bugs * 1.6)
    service = min(8.0, game.updates_released * 1.5)
    fatigue = franchise.fatigue if franchise else 0.0
    issue_drag = sum(float(issue.get("severity", 0.0)) for issue in game.issues if issue.get("status", "open") == "open")
    monetization_drag = float(monetization_by_key(game.monetization)["monetization_friction"]) * (24 if segment.key in ("core", "enthusiast") else 14)
    target = score - (segment.expectation - 60) * 0.6 + (game.trust - 50) * 0.18 - issue_drag * 1.8 - monetization_drag
    note = ""
    if segment.key == "core":
        target += min(6.0, service * 0.75) - game.patch_fatigue * 2.0 - min(12.0, stale_weeks * 0.8) - bug_drag * 0.35 - max(0.0, fatigue - 55) * 0.08
        if game.fans_betrayed:
            target -= 10
        if game.patch_fatigue >= 2.5:
            note = "tired of patches - they want New content"
        elif game.fans_betrayed:
            note = "still angry about the paid DLC"
        elif stale_weeks > 0:
            note = "waiting for the promised update"
        else:
            note = "loves the support" if segment.satisfaction >= 72 else "watching the roadmap"
    elif segment.key == "casual":
        target -= bug_drag * 0.9 + max(0.0, fatigue - 70) * 0.06
        target += min(4.0, service * 0.5)
        target -= min(18.0, game.hype_backlash * 0.35)
        if game.hype_backlash >= 15:
            note = "feels the game was overhyped"
        elif game.known_bug_count >= 6:
            note = "complaining about bugs"
        else:
            note = "happy with the polish" if segment.satisfaction >= 72 else "mildly entertained"
    elif segment.key == "enthusiast":
        target -= fatigue * 0.12 + max(0, game.generation - 2) * 3 + years_old * 1.5
        target -= min(18.0, game.hype_backlash * 0.35)
        if game.hype_backlash >= 15:
            note = "calls it all marketing, no substance"
        elif fatigue >= 60:
            note = "bored of the IP - wants a fresh concept"
        elif years_old >= 2:
            note = "wants something new"
        else:
            note = "intrigued by the direction"
    else:
        target -= stale_weeks * 1.5
        if stale_weeks <= 0 and game.game_format != "Offline solo":
            target += 4
        note = "feels abandoned - update cadence too slow" if stale_weeks > 0 else "engaged this season"
    return max(5.0, min(92.0, target)), note


def update_community_segments(state: GameState, game: ReleasedGame, franchise: Franchise | None, stale_weeks: int) -> None:
    if not game.segments:
        return
    years_old = max(0.0, (state.clock.week - game.release_week) / 52)
    for segment in game.segments:
        if segment.weight <= 0:
            continue
        target, note = segment_target(state, game, segment, franchise, stale_weeks, years_old)
        old = segment.satisfaction
        segment.satisfaction += (target - segment.satisfaction) * 0.12
        segment.trend = segment.satisfaction - old
        segment.mood = segment_mood(segment.satisfaction)
        segment.note = note
    # ``game.user_rating`` is owned by the review stream in process_sales;
    # segments shape it indirectly through segment_rating_anchor().
    quality_anchor = game.score * 0.6 + game.sentiment * 0.4
    if game.trust > quality_anchor:
        game.trust = max(quality_anchor, game.trust + (quality_anchor - game.trust) * 0.08)


def hype_marketing_effectiveness(current_hype: float) -> float:
    return max(0.25, 1.0 - max(0.0, current_hype - 60) / 140 * 0.75)


def promotion_hype_effectiveness(promotion: dict, current_hype: float) -> float:
    """Campaigns cannot substitute for broader awareness once their tier tops out."""
    remaining = max(0.0, promotion["ceiling"] - current_hype)
    tier_headroom = min(1.0, remaining / max(1.0, promotion["hype"]))
    return hype_marketing_effectiveness(current_hype) * tier_headroom


def market_growth_factor(week: int) -> float:
    """Audience spending expands over time for every studio, not just the player."""
    return 1 + min(0.35, max(0, week - 1) / 52 * 0.03)


def genre_market_capacity(genre: str, channel: str, week: int = 1) -> float:
    """Weekly attention available to one genre/storefront market."""
    storefront = channel_by_name(channel)
    modern_bonus = 1.25 if genre in {"Battle Royale", "Extraction Shooter", "Survivors-like", "Roguelike", "Roguelite", "Deckbuilder", "Automation", "Cozy Game", "Social Deduction", "Immersive Sim", "Soulslike", "Metroidvania"} else 1.0
    return 450_000 * storefront["reach"] * (0.55 + storefront["visibility"] / 10) * modern_bonus * market_growth_factor(week)


def market_share_multiplier(state: GameState, genre: str, channel: str, excluded_game_id: int = 0) -> float:
    """Demand left after currently visible games have claimed their share.

    A hit in the same genre and storefront takes real attention from the next
    launch and from catalog tails. Different storefronts overlap slightly,
    while the same storefront competes directly.
    """
    demand_taken = 0.0
    for competitor in state.studio.competitors:
        for game in competitor.recent_releases:
            if game.genre != genre or state.clock.week - game.released_week > 30:
                continue
            overlap = 1.0 if game.channel == channel else 0.20
            demand_taken += game.weekly_units * overlap
    for sale in state.studio.active_sales:
        if sale.game_id == excluded_game_id or sale.genre != genre:
            continue
        game = game_by_id(state.studio, sale.game_id)
        overlap = 1.0 if game and game.channel == channel else 0.20
        demand_taken += sale.weekly_units * overlap * 0.55
    load = demand_taken / max(1.0, genre_market_capacity(genre, channel, state.clock.week))
    return max(0.18, min(1.0, 1.0 - load * 0.55))


def update_genre_heat(state: GameState) -> None:
    studio = state.studio
    for index, genre in enumerate(GENRES):
        saturation = 0.0
        momentum = 0.0
        for competitor in studio.competitors:
            for release in competitor.recent_releases:
                if release.genre == genre and 0 <= state.clock.week - release.released_week <= 30:
                    age = state.clock.week - release.released_week
                    reach = min(0.45, release.weekly_units / genre_market_capacity(genre, release.channel, state.clock.week) * 0.70)
                    momentum += reach * max(0.4, release.quality / 75) * max(0.0, 1 - age / 14)
                    saturation += 0.025 + max(0.0, age - 6) / 400
        for game in studio.catalog:
            if game.genre == genre and 0 <= state.clock.week - game.release_week <= 30:
                age = state.clock.week - game.release_week
                sale = sale_for_game(studio, game.game_id)
                weekly = sale.weekly_units if sale else 0
                reach = min(0.45, weekly / genre_market_capacity(genre, game.channel, state.clock.week) * 0.70)
                momentum += reach * max(0.4, game.score / 75) * max(0.0, 1 - age / 14)
                saturation += 0.02 + max(0.0, age - 6) / 450
        drift_rng = random.Random(studio.seed + state.clock.week * 1_009 + index * 67)
        cultural_drift = drift_rng.uniform(-0.025, 0.025)
        current = studio.genre_heat.get(genre, 1.0)
        target = max(0.40, min(1.75, 1.0 + momentum - saturation + cultural_drift))
        studio.genre_heat[genre] = current * 0.88 + target * 0.12


def process_macro_week(state: GameState) -> None:
    studio = state.studio
    rng = random.Random(studio.seed + state.clock.week * 104_729)
    weekly_inflation = (0.028 + rng.uniform(-0.008, 0.012)) / 52
    studio.inflation_index *= 1 + weekly_inflation
    studio.wage_index *= 1 + weekly_inflation * 1.12
    confidence_target = 1.0 + rng.uniform(-0.035, 0.035)
    studio.macro_confidence += (confidence_target - studio.macro_confidence) * 0.10
    if rng.random() < 0.004:
        shock = rng.choice(("recession", "spending boom", "credit squeeze", "platform surge"))
        if shock == "recession":
            studio.macro_confidence = max(0.60, studio.macro_confidence - rng.uniform(0.16, 0.30))
            studio.macro_spending = max(0.68, studio.macro_spending - rng.uniform(0.10, 0.22))
        elif shock == "spending boom":
            studio.macro_confidence = min(1.25, studio.macro_confidence + rng.uniform(0.10, 0.20))
            studio.macro_spending = min(1.30, studio.macro_spending + rng.uniform(0.08, 0.16))
        elif shock == "credit squeeze":
            studio.interest_rate = min(0.16, studio.interest_rate + rng.uniform(0.015, 0.035))
        else:
            category = rng.choice(tuple(studio.platform_demand))
            studio.platform_demand[category] = min(1.50, studio.platform_demand[category] + rng.uniform(0.12, 0.30))
        emit_event(state, "macro_shock", f"Industry outlook changed: {shock}.", "warning", "market", shock)
        state.log(f"Industry outlook changed: {shock}. Consumer demand and financing conditions moved.")
    studio.macro_spending += (studio.macro_confidence - studio.macro_spending) * 0.025
    studio.interest_rate += (0.055 - studio.interest_rate) * 0.015
    for category in studio.platform_demand:
        studio.platform_demand[category] += (1.0 - studio.platform_demand[category]) * 0.003


def genre_heat(studio: Studio, genre: str) -> float:
    return studio.genre_heat.get(genre, 1.0)


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


def publisher_by_name(name: str) -> dict | None:
    return next((publisher for publisher in PUBLISHER_OFFERS if publisher["name"] == name), None)


def loan_payment(principal: float, annual_rate: float, weeks: int) -> float:
    weekly_rate = annual_rate / 52
    if weekly_rate <= 0:
        return principal / weeks
    return principal * weekly_rate / (1 - (1 + weekly_rate) ** -weeks)


def market_release_pressure(state: GameState, genre: str, target_weeks: int) -> float:
    """Weighted rival launches that will still compete when this project ships."""
    pressure = 0.0
    release_week = state.clock.week + target_weeks
    for competitor in state.studio.competitors:
        for game in competitor.recent_releases:
            age_at_launch = release_week - game.released_week
            if game.genre == genre and -2 <= age_at_launch <= 20:
                pressure += 0.35 + game.hype / 300 * (0.35 + competitor.size / 10)
        for game in competitor.in_development:
            if game.genre == genre and abs(game.weeks_left - target_weeks) <= 12:
                pressure += 0.45 + game.hype / 260 * (0.35 + competitor.size / 10)
    return min(8.0, pressure)


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
    monetization = selected_monetization_model(state)
    price = float(selected_price_point(state)["price"])
    announcement = selected_announcement_strategy(state)

    modern = {"Battle Royale", "Extraction Shooter", "Survivors-like", "Roguelike", "Roguelite", "Deckbuilder", "Automation", "Cozy Game", "Social Deduction", "Immersive Sim", "Soulslike", "Metroidvania"}
    heat = genre_heat(state.studio, genre)
    demand = (1.12 if genre in modern else 1.0) * max(0.5, min(1.6, heat))
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
    nominal_work = round(
        scope["work"]
        * game_format["work"]
        * strategy["work"]
        * float(monetization["work_multiplier"])
        * (primary_direction["work"] * 0.6 + secondary_direction["work"] * 0.4)
    )
    target_weeks = max(4, round(nominal_work / max(0.1, projected_weekly_output(state.studio, concept_focus(state)))))
    release_pressure = market_release_pressure(state, genre, target_weeks)
    open_market = market_share_multiplier(state, genre, channel["name"])
    score = round(
        42
        + (topic_score - 0.5) * 40
        + (16 if audience_matches == len({genre, secondary_genre}) else 7 if audience_fit else -14)
        + direction_market
        + strategy["market"]
        + category_fit
        + blend_fit
        + format_fit
        - float(monetization["monetization_friction"]) * 12
        + trend
        - release_pressure * 4
        + (open_market - 0.7) * 18
    )
    score = max(8, min(96, score + round((heat - 1.0) * 24)))
    competitors = max(1, round(2 + demand * 3 + (3 if genre in modern else 0) + release_pressure + max(0, trend) / 4 + rng.uniform(-2, 2)))
    cultural_resonance = {
        cohort.key: max(20.0, min(80.0, 50 + random.Random(seed + sum(ord(char) for char in cohort.key)).uniform(-18, 18)))
        for cohort in COHORTS
    }
    preview_hype = 5 + MARKETING[state.selected_marketing]["boost"] / 25
    draft_offer = ProductOffer(
        product_id="draft",
        genre=genre,
        secondary_genre=secondary_genre,
        topic=topic,
        target_audience=audience["name"],
        game_format=game_format["name"],
        monetization=str(monetization["key"]),
        price=price,
        quality=max(30, min(85, 42 + score * 0.40)),
        user_rating=55,
        awareness_by_cohort=initial_awareness_by_cohort(state, preview_hype, MARKETING[state.selected_marketing]["boost"], str(announcement["key"])),
        owners_by_cohort={},
        hype=preview_hype,
        trust=state.studio.studio_trust,
        sentiment=55,
        novelty=max(20, min(90, 50 + trend + direction_market)),
        network_health=70 if game_format["name"] != "Offline solo" else 100,
        store_reach=channel["reach"] * studio_store_visibility(state.studio),
        platform_category=channel["category"],
        cultural_resonance=cultural_resonance,
        lifecycle_state="launch",
    )
    market_results = allocate_weekly_demand(
        [draft_offer, *competitor_product_offers(state)],
        studio_macro_snapshot(state.studio),
        seed + 84_271,
    )
    draft_result = market_results[0]
    audience_size = max(1_000, sum(draft_result.interested_by_cohort.values()))
    opportunity = max(1, draft_result.units)
    risk = round(
        scope["risk"]
        + game_format["risk"]
        + strategy["risk"]
        + primary_direction["risk"] * 0.6
        + secondary_direction["risk"] * 0.4
        + float(monetization["monetization_friction"]) * 12
        + float(announcement["promise_risk"]) * 8
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
        "release_pressure": round(release_pressure, 1),
        "open_market": round(open_market, 2),
        "work": actual_work,
        "nominal_work": nominal_work,
        "launch_demand": opportunity,
        "price": price,
        "cultural_resonance": cultural_resonance,
        "demand_drivers": list(draft_result.explanation_drivers),
    }


def market_report_signature(state: GameState) -> tuple:
    """Inputs a cached market report depends on; anything else is noise.

    Week-keyed by design: genre heat, competitor moves, and macro drift all
    change at week boundaries, so they do not need individual fields here.
    """
    return (
        state.clock.week,
        state.selected_genre,
        state.selected_secondary_genre,
        state.selected_topic,
        state.selected_secondary_topic,
        state.selected_audience,
        state.selected_format,
        state.selected_scope,
        state.selected_channel,
        state.selected_marketing,
        state.selected_release_strategy,
        state.selected_creative_primary,
        state.selected_creative_secondary,
        state.selected_monetization,
        state.selected_price,
        state.selected_announcement,
        state.selected_release_policy,
        state.mix_blend,
        state.sequel_game_id,
        state.spinoff_franchise_id,
        state.studio.pending_publisher,
        len(state.studio.team),
        len(state.studio.completed_research),
        round(team_research_skill(state.studio)),
        round(sum(state.studio.market_experience.values()), 1),
        round(state.studio.reputation),
        state.studio.followers // 1_000,
    )


def market_report(state: GameState) -> dict:
    # The new-game screen redraws frequently and each uncached call runs a full
    # demand allocation against every rival offer, so memoize per signature.
    signature = market_report_signature(state)
    cached = getattr(state, "_market_report_cache", None)
    if cached is not None and cached[0] == signature:
        return dict(cached[1])
    truth = market_truth(state)
    research = team_research_skill(state.studio)
    genre_name = GENRES[state.selected_genre]
    experience = state.studio.market_experience.get(f"genre:{genre_name}", 0.0)
    format_experience = state.studio.market_experience.get(f"format:{GAME_FORMATS[state.selected_format]['name']}", 0.0)
    experience_bonus = min(0.16, math.log1p(experience + format_experience * 0.5) * 0.045)
    # Early generalists can spot broad signals, but reliable forecasts require
    # deliberate research development rather than a second hire alone.
    confidence = max(0.20, min(0.94, 0.12 + (research / 100) ** 3 * 0.62 + (0.10 if has_research(state.studio, "market_research") else 0) + experience_bonus))
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
    report = {
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
        "release_pressure": truth["release_pressure"],
        "open_market": truth["open_market"],
        "launch_units": max(1, round(truth["launch_demand"] * (0.82 + confidence * 0.12 + rng.uniform(-0.20, 0.20) * uncertainty))),
        "price": truth["price"],
        "demand_drivers": truth["demand_drivers"],
        "experience": round(experience + format_experience * 0.5, 1),
    }
    state._market_report_cache = (signature, report)
    return dict(report)


def plan_requirements(state: GameState) -> list[str]:
    studio = state.studio
    scope = SCOPES[state.selected_scope]
    game_format = GAME_FORMATS[state.selected_format]
    requirements = []
    required_team = max(scope["team"], game_format["team"])
    required_rep = max(scope["rep"], game_format["rep"])
    monetization = selected_monetization_model(state)
    if len(studio.team) < required_team:
        requirements.append(f"team {required_team} (have {len(studio.team)})")
    if studio.reputation < required_rep:
        requirements.append(f"reputation {required_rep} (have {studio.reputation:.0f})")
    if state.selected_release_strategy == 3 and state.selected_format == 0:
        requirements.append("an online game format")
    if monetization.get("requires_online") and state.selected_format == 0:
        requirements.append("an online game format for this monetization model")
    monetization_research = monetization.get("research_key")
    if monetization_research and not has_research(studio, str(monetization_research)):
        node = research_by_key(str(monetization_research))
        requirements.append(f"research: {node['name'] if node else monetization_research}")
    channel_lock = channel_lock_reason(studio, state.selected_channel)
    if channel_lock:
        if "itch.io" in channel_lock:
            requirements.append(f"{ITCH_RELEASES_BEFORE_STEAM} itch.io releases before Steam (have {studio.itch_releases})")
        else:
            requirements.append(channel_lock)
    unlock_requirements = (
        research_requirement_for_scope(state.selected_scope),
        research_requirement_for_format(state.selected_format),
        research_requirement_for_genre(GENRES[state.selected_genre]),
        research_requirement_for_topic(TOPICS[state.selected_topic]),
        research_requirement_for_channel(state.selected_channel),
        research_requirement_for_marketing(state.selected_marketing),
        research_requirement_for_strategy(state.selected_release_strategy),
    )
    for node_key in unlock_requirements:
        if node_key and not has_research(studio, node_key):
            node = research_by_key(node_key)
            label = node["name"] if node else node_key
            requirements.append(f"research: {label}")
    return requirements


def research_by_key(key: str) -> dict | None:
    return RESEARCH_BY_KEY.get(key)


def research_nodes_for_branch(branch: str) -> list[dict]:
    return [node for node in RESEARCH_NODES if node["branch"] == branch]


def has_research(studio: Studio, key: str) -> bool:
    return key in studio.completed_research or key in studio.upgrades


def completed_research_keys(studio: Studio) -> set[str]:
    return set(studio.completed_research) | set(studio.upgrades) | set(STARTER_RESEARCH)


def research_requirement_for_scope(index: int) -> str | None:
    # Jam-sized experiments are always available; the tuple lookup below only
    # knows the classic ascending scopes.
    if SCOPES[index]["name"] == "Bite-size":
        return None
    return (None, None, "small_production", "mid_production", "ambitious_production", "large_production", "blockbuster_production")[index]


def research_requirement_for_format(index: int) -> str | None:
    return (None, "online_coop", "competitive_online", "persistent_worlds", "mmo_technology")[index]


def research_requirement_for_genre(genre: str) -> str | None:
    if genre in STARTER_GENRES:
        return None
    return next((key for key, genres in GENRE_UNLOCKS.items() if genre in genres), None)


def research_requirement_for_topic(topic: str) -> str | None:
    index = TOPICS.index(topic)
    if topic in STARTER_TOPICS:
        return None
    return f"theme_library_{index % 4 + 1}"


def channel_lock_reason(studio: Studio, index: int) -> str | None:
    """Return why this storefront is unavailable, or None when selectable."""
    channel = CHANNELS[index]
    if channel["name"] == "Steam" and studio.itch_releases < ITCH_RELEASES_BEFORE_STEAM:
        return f"{ITCH_RELEASES_BEFORE_STEAM - studio.itch_releases} more itch.io releases"
    requirement = research_requirement_for_channel(index)
    if requirement and not has_research(studio, requirement):
        node = research_by_key(requirement)
        return f"research: {node['name'] if node else requirement}"
    return None


def research_requirement_for_channel(index: int) -> str | None:
    category = CHANNELS[index]["category"]
    if index in (0, 1):
        return None
    if category == "Mobile":
        return "mobile_distribution"
    if category in ("Console", "Handheld"):
        return "console_certification"
    return "market_research"


def research_requirement_for_marketing(index: int) -> str | None:
    return (None, "promotion_basics", "targeted_marketing", "creator_relations", "creator_relations", "event_marketing")[index]


def research_requirement_for_strategy(index: int) -> str | None:
    return (None, "content_updates", "paid_dlc", "live_operations")[index]


def research_requirement_for_update(size_name: str) -> str | None:
    return {"Hotfix": None, "Patch": None, "Content": "content_updates", "Expansion": "expansion_pipeline", "Paid DLC": "paid_dlc"}.get(size_name)


def research_requirement_for_promotion(key: str) -> str | None:
    return {
        "social": "promotion_basics",
        "press": "targeted_marketing",
        "creator": "creator_relations",
        "streamer": "creator_relations",
        "festival": "event_marketing",
        "event": "event_marketing",
        "showcase": "event_marketing",
    }.get(key)


def upgrade_by_key(key: str) -> dict:
    return RESEARCH_BY_KEY.get(key, {"key": key, "name": key, "cost": 0, "monthly": 0, "effect": "Legacy capability"})


def add_revenue(studio: Studio, amount: float, category: str = "Other revenue") -> None:
    if amount <= 0:
        return
    operating_revenue(studio, amount, category, date=studio.accounting_month)


def add_expense(studio: Studio, amount: float, category: str = "Other") -> None:
    if amount <= 0:
        return
    operating_expense(studio, amount, category, date=studio.accounting_month)


def monthly_cost_breakdown(studio: Studio) -> dict[str, int]:
    salaries = sum(employee.monthly_salary for employee in studio.team)
    payroll_burden = round(sum(employee.monthly_salary for employee in studio.team if not employee.founder) * 0.13)
    game_by_sale = {game.game_id: game for game in studio.catalog}
    portfolio_operations = 0
    for sale in studio.active_sales:
        game = game_by_sale.get(sale.game_id)
        if game is None or game.support_level == "Sunset":
            continue
        portfolio_operations += 50 if game.support_level == "Maintenance" else 150
    costs = {
        "Payroll": salaries,
        "Employer costs": payroll_burden,
        "Operations": round((1_250 + 420 * len(studio.team) + portfolio_operations) * studio.inflation_index),
        "Office & equipment": round((900 + 260 * len(studio.team)) * studio.inflation_index),
    }
    for key in studio.upgrades:
        upgrade = upgrade_by_key(key)
        costs["Upgrades"] = costs.get("Upgrades", 0) + upgrade.get("monthly", 0) + upgrade.get("per_employee", 0) * len(studio.team)
    return {category: amount for category, amount in costs.items() if amount}


def monthly_fixed_cost(studio: Studio) -> int:
    return sum(monthly_cost_breakdown(studio).values())


def loan_weekly_obligation(studio: Studio) -> int:
    return round(sum(loan.weekly_payment for loan in studio.loans))


def take_loan(state: GameState, offer_index: int) -> bool:
    studio = state.studio
    offer = LOAN_OFFERS[offer_index]
    if studio.insolvent_days >= 14:
        state.log("The bank declined new ordinary credit while the studio is in sustained overdraft.")
        return False
    if offer["principal"] > max(25_000, studio.lifetime_revenue * 0.40 + 100_000):
        state.log(f"The bank declined the {offer['name'].lower()}: build more revenue history first.")
        return False
    if any(loan.name == offer["name"] for loan in studio.loans):
        state.log(f"The {offer['name'].lower()} is already outstanding.")
        return False
    risk_rate = offer["rate"] + max(0.0, studio.interest_rate - 0.055) + (0.04 if studio.insolvent_days else 0.0)
    payment = loan_payment(offer["principal"], risk_rate, offer["weeks"])
    studio.loans.append(Loan(offer["name"], offer["principal"], offer["principal"], risk_rate, offer["weeks"], payment))
    financing_inflow(studio, offer["principal"], "Bank loan", date=state.clock.current_date, counterparty="Bank", memo=offer["name"])
    state.log(f"Bank approved a ${offer['principal']:,} {offer['name'].lower()} at {offer['rate']:.1%}; ${payment:,.0f}/week for {offer['weeks']} weeks.")
    return True


def select_publisher(state: GameState, offer_index: int) -> bool:
    studio = state.studio
    offer = PUBLISHER_OFFERS[offer_index]
    if studio.reputation < offer["min_rep"]:
        state.log(f"{offer['name']} requires {offer['min_rep']} game reputation; you have {studio.reputation:.0f}.")
        return False
    studio.pending_publisher = "" if studio.pending_publisher == offer["name"] else offer["name"]
    status = "declined" if not studio.pending_publisher else "selected for your next project"
    state.log(f"{offer['name']} {status}. Their advance is recouped before the lower royalty share applies.")
    return True


def recommended_team_size(studio: Studio) -> int:
    growth = studio.followers // 250
    growth += studio.released_games // 2
    growth += max(0, int(studio.reputation) // 8)
    growth += int(studio.lifetime_revenue // 100_000)
    return max(1, min(60, 1 + growth))


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
    return forward_runway_months(studio, fixed_burn=monthly_fixed_cost(studio))


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
    multiplier = employee_modifiers(employee)["learning"]
    if has_research(state.studio, "academy"):
        multiplier *= 1.35
    elif has_research(state.studio, "mentorship"):
        multiplier *= 1.25
    gained = max(1, round(points * multiplier))
    employee.experience += gained
    employee.lifetime_experience += gained
    new_level = min(5, 1 + employee.lifetime_experience // 500)
    if new_level > employee.career_level:
        employee.career_level = new_level
        state.log(f"{employee.name} reached career level {new_level} through sustained studio work.")
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
    employee.training_weeks_left = 2 if has_research(state.studio, "academy") else 3 if has_research(state.studio, "structured_training") else 4
    state.log(f"Sent {employee.name} to {employee.training_weeks_left} weeks of {skill_name} training for ${cost:,}; they are unavailable during the course.")
    return True


def process_employee_training(state: GameState, week_end: bool = True) -> None:
    if not week_end:
        return
    for employee in state.studio.team:
        if employee.training_weeks_left <= 0:
            continue
        employee.training_weeks_left -= 1
        if employee.training_weeks_left == 0:
            skill_name = employee.training_skill
            gain = 6 if has_research(state.studio, "academy") else 4
            grant_employee_skill(state, employee, skill_name, gain, "professional training")
            employee.training_skill = ""
            employee.fatigue = max(0, employee.fatigue - 5)


def start_employee_vacation(state: GameState, employee: Employee | None = None) -> bool:
    employee = employee or selected_roster_employee(state)
    if employee is None:
        return False
    if employee.training_weeks_left or employee.vacation_weeks_left or employee.burnout_weeks_left:
        state.log(f"{employee.name} is already unavailable.")
        return False
    employee.vacation_weeks_left = 1
    state.log(f"Scheduled one week of vacation for {employee.name}; salary continues while they recover.")
    return True


def dominant_work_skill(studio: Studio) -> str:
    allocations = activity_allocations(studio)
    kind = max(("project", "contract", "update", "promotion", "research", "support"), key=lambda item: allocations[item])
    if allocations[kind] <= 0:
        return ""
    if kind == "project" and studio.current_project:
        return SKILLS[max(range(4), key=lambda index: studio.current_project.focus[index])]
    if kind == "contract" and studio.contract:
        return studio.contract.focus
    if kind == "update" and studio.active_update:
        return update_focus_by_name(studio.active_update.focus)["skill"] if studio.active_update.phase == "Development" else "Code"
    if kind == "research":
        return "Research"
    if kind == "support":
        return "Code"
    return "Generalist"


def process_employee_wellbeing(state: GameState, week_end: bool, workday: bool) -> None:
    studio = state.studio
    allocations = activity_allocations(studio)
    workload = sum(allocations.values())
    if workday and workload > 0:
        for employee in studio.team:
            if employee_available(employee):
                gain = 0.35 * max(0.35, workload) * employee_modifiers(employee)["fatigue"]
                if has_research(studio, "health"):
                    gain *= 0.82
                employee.fatigue = min(100, employee.fatigue + gain)
    if not week_end:
        return

    work_skill = dominant_work_skill(studio)
    for employee in studio.team:
        employee.weeks_employed += 1
        employee.onboarding_weeks_left = max(0, employee.onboarding_weeks_left - 1)
        employee.institutional_knowledge = min(25.0, employee.institutional_knowledge + (0.15 if employee_available(employee) else 0.05))
        if employee.vacation_weeks_left:
            employee.vacation_weeks_left -= 1
            recovery = 38 if has_research(studio, "paid_leave") else 30
            employee.fatigue = max(0, employee.fatigue - recovery)
            employee.morale = min(100, employee.morale + (6 if has_research(studio, "paid_leave") else 3))
            continue
        if employee.burnout_weeks_left:
            employee.burnout_weeks_left -= 1
            employee.fatigue = max(55, employee.fatigue - 16)
            continue
        if employee.fatigue >= 100:
            employee.burnout_weeks_left = 2
            employee.fatigue = 88
            employee.morale = max(0, employee.morale - 10)
            state.log(f"{employee.name} burned out and will be unavailable for two weeks.")
            continue
        employee.fatigue = max(0, employee.fatigue - (2.5 if has_research(studio, "health") else 1.5))
        if work_skill and employee_available(employee):
            points = max(1, round(workload * 3 + employee.week_output / 30))
            grant_employee_experience(state, employee, work_skill, points, f"{work_skill.lower()} work")
        employee.week_output = 0.0

    if has_research(studio, "auto_leave") and studio.auto_vacation:
        vacation_limit = max(1, math.ceil(len(studio.team) * 0.25))
        already_away = sum(bool(employee.vacation_weeks_left) for employee in studio.team)
        candidates = sorted(
            (employee for employee in studio.team if employee_available(employee) and employee.fatigue >= 72),
            key=lambda employee: employee.fatigue,
            reverse=True,
        )
        for employee in candidates[: max(0, vacation_limit - already_away)]:
            employee.vacation_weeks_left = 1
            state.log(f"Sustainable Scheduling placed {employee.name} on vacation at {employee.fatigue:.0f} fatigue.")


def generate_candidate(studio: Studio, rng: random.Random) -> Employee:
    role = rng.choice(tuple(ROLE_PROFILES))
    base = ROLE_PROFILES[role]
    seniority = rng.choices(("Junior", "Mid-level", "Senior"), weights=(35, 45, 20))[0]
    modifier = {"Junior": -14, "Mid-level": 0, "Senior": 13}[seniority]
    skills = [max(18, min(96, value + modifier + rng.randint(-10, 10))) for value in base]
    research = max(18, min(96, ROLE_RESEARCH[role] + modifier + rng.randint(-10, 10)))
    annual = round((34_000 + (sum(skills) + research) * 100 + (12_000 if seniority == "Senior" else 0)) * studio.wage_index / 1_000) * 1_000
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


def cycle_game_support(state: GameState, game_id: int) -> str | None:
    game = game_by_id(state.studio, game_id)
    if game is None:
        return None
    if not has_research(state.studio, "portfolio_management"):
        state.log("Support levels require Portfolio Management research.")
        return game.support_level
    levels = ("Active", "Maintenance", "Sunset")
    game.support_level = levels[(levels.index(game.support_level) + 1) % len(levels)]
    state.log(f"{game.title} moved to {game.support_level.lower()} support.")
    return game.support_level


def cycle_game_price(state: GameState, game_id: int, delta: int) -> float | None:
    game = game_by_id(state.studio, game_id)
    sale = sale_for_game(state.studio, game_id)
    if game is None or sale is None:
        return None
    previous = sale.price
    current = min(range(len(PRICE_POINTS)), key=lambda index: abs(float(PRICE_POINTS[index]["price"]) - sale.price))
    target_index = max(0, min(len(PRICE_POINTS) - 1, current + delta))
    price = float(PRICE_POINTS[target_index]["price"])
    if price == previous:
        state.log(f"{game.title} is already at the {'cheapest' if delta < 0 else 'highest'} store price point ({money_text(price)}).")
        return price
    sale.price = price
    game.price = price
    sale.price_history.append({"week": state.clock.week, "price": price, "reason": "studio pricing decision"})
    if price > previous:
        increase = (price - previous) / max(1.0, previous)
        if increase >= 0.25:
            trust_loss = min(12.0, 2 + increase * 4)
            game.trust = max(0.0, game.trust - trust_loss)
            game.sentiment = max(0.0, game.sentiment - trust_loss * 0.7)
            game.issues.append({"kind": "pricing", "severity": min(8.0, trust_loss / 2), "status": "open", "opened_week": state.clock.week})
            state.log(f"Players accuse the studio of opportunistic pricing after {game.title} rose from {money_text(previous)} to {money_text(price)}; trust fell {trust_loss:.1f}.")
    state.log(f"{game.title} is now priced at {money_text(price)}. Cohort demand will react next week.")
    return price


def sale_for_game(studio: Studio, game_id: int) -> ActiveSale | None:
    return next((sale for sale in studio.active_sales if sale.game_id == game_id), None)


def update_focus_by_name(name: str) -> dict:
    return next((focus for focus in UPDATE_FOCUSES if focus["name"] == name), UPDATE_FOCUSES[0])


def update_size_by_name(name: str) -> dict:
    return next((size for size in UPDATE_SIZES if size["name"] == name), UPDATE_SIZES[1])


def employee_available(employee: Employee) -> bool:
    return not (employee.training_weeks_left or employee.vacation_weeks_left or employee.burnout_weeks_left)


def employee_availability(employee: Employee) -> float:
    morale = max(0.35, employee.morale / 100)
    fatigue = 1.0 if employee.fatigue <= 50 else max(0.5, 1 - (employee.fatigue - 50) / 100)
    onboarding = 1.0 if employee.onboarding_weeks_left <= 0 else max(0.40, 1 - employee.onboarding_weeks_left * 0.15)
    return morale * fatigue * onboarding


def coordination_weights(studio: Studio, contributions: list[float]) -> list[float]:
    """Declining but always-positive marginal contribution weights.

    Sorting by contribution means adding a weaker employee cannot reduce the
    established team's output. Management research improves later workers.
    """
    order = sorted(range(len(contributions)), key=lambda index: contributions[index], reverse=True)
    weights = [0.0] * len(contributions)
    for rank, index in enumerate(order):
        if rank < 5:
            weight = 1.0
        elif rank < 12:
            weight = 0.84 if has_research(studio, "production_pipeline") else 0.70
        else:
            weight = 0.72 if has_research(studio, "advanced_coordination") else 0.48
        weights[index] = weight
    return weights


def team_speed_factor(workers: int) -> float:
    """Compatibility helper: average marginal efficiency for equal workers."""
    if workers <= 0:
        return 0.0
    first = min(5, workers)
    middle = min(7, max(0, workers - 5)) * 0.70
    later = max(0, workers - 12) * 0.48
    return (first + middle + later) / workers


def coordinated_team_output(studio: Studio, focus: str | list[int] | tuple[int, ...]) -> float:
    contributions = []
    for employee in studio.team:
        if not employee_available(employee):
            continue
        if isinstance(focus, str):
            skill_index = {"Design": 0, "Art": 1, "Audio": 2, "Code": 3}.get(focus)
            if focus == "Research":
                skill = effective_research(employee)
            else:
                skill = sum(employee.skills) / 4 if skill_index is None else employee.skills[skill_index]
        else:
            skill = sum(value * percent for value, percent in zip(employee.skills, focus)) / 100
        contributions.append(skill * employee_availability(employee) * employee_modifiers(employee)["output"])
    weights = coordination_weights(studio, contributions)
    output = sum(value * weight for value, weight in zip(contributions, weights))
    if has_research(studio, "hardware"):
        output *= 1.10
    return output


def activity_allocations(studio: Studio, assume_project: bool = False) -> dict[str, float]:
    support = live_support_load(studio)
    available = max(0.0, 1.0 - support)
    requests: dict[str, float] = {}
    if studio.contract:
        requests["contract"] = 0.42
    if studio.active_update:
        requests["update"] = update_size_by_name(studio.active_update.size)["team"]
    if studio.active_promotions:
        requests["promotion"] = marketing_team_load(studio)
    if studio.active_research:
        requests["research"] = 0.22
    if studio.active_community_actions:
        requests["community"] = max(float(item.get("team_load", 0.0)) for item in studio.active_community_actions)

    if has_research(studio, "department_leads"):
        priority_multiplier = {0: 0.0, 1: 0.55, 2: 1.0, 3: 1.35}
        for kind in list(requests):
            requests[kind] *= priority_multiplier.get(studio.work_priorities.get(kind, 2), 1.0)

    allocations = {kind: 0.0 for kind in ("project", "contract", "update", "promotion", "research", "community", "support")}
    allocations["support"] = support
    total_requested = sum(requests.values())
    if studio.current_project or assume_project:
        project_priority = studio.work_priorities.get("project", 3) if has_research(studio, "department_leads") else 3
        project_reserve = available * {0: 0.0, 1: 0.20, 2: 0.35, 3: 0.50}.get(project_priority, 0.35)
        task_budget = max(0.0, available - project_reserve)
        scale = min(1.0, task_budget / total_requested) if total_requested else 0.0
        for kind, request in requests.items():
            allocations[kind] = request * scale
        allocations["project"] = max(0.0, available - sum(allocations[kind] for kind in requests))
    elif total_requested:
        for kind, request in requests.items():
            allocations[kind] = available * request / total_requested
    return allocations


def update_weekly_output(studio: Studio, game_or_focus: ReleasedGame | str) -> float:
    focus_name = game_or_focus.update_focus if isinstance(game_or_focus, ReleasedGame) else game_or_focus
    focus = update_focus_by_name(focus_name)
    share = activity_allocations(studio)["update"]
    if share <= 0 and studio.active_update is None:
        demand = update_size_by_name(game_or_focus.update_size)["team"] if isinstance(game_or_focus, ReleasedGame) else 0.20
        share = min(demand, max(0.10, (1 - live_support_load(studio)) * (0.50 if studio.current_project else 1.0)))
    output = coordinated_team_output(studio, focus["skill"]) * share
    if has_research(studio, "automated_deployment"):
        output *= 1.20
    return max(0.0, output)


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
    build_weeks = math.ceil(size["work"] / max(0.1, update_weekly_output(studio, game.update_focus)))
    bug_weeks = math.ceil(size["bugs"] / max(0.1, update_weekly_output(studio, "Bug fixes")))
    return max(1, build_weeks + bug_weeks)


def estimated_update_job_weeks(studio: Studio, job: UpdateJob) -> int:
    build_remaining = max(0, job.required_work - job.work_done)
    bugs_remaining = max(0, job.bugs_found - job.bugs_fixed)
    build_weeks = math.ceil(build_remaining / max(0.1, update_weekly_output(studio, job.focus)))
    bug_weeks = math.ceil(bugs_remaining / max(0.1, update_weekly_output(studio, "Bug fixes")))
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
    supported = {game.game_id for game in studio.catalog if game.support_level != "Sunset"}
    known = {game.game_id for game in studio.catalog}
    return sum(1 for sale in studio.active_sales if sale.game_id in supported or sale.game_id not in known)


def live_support_load(studio: Studio) -> float:
    load = 0.0
    known = set()
    for game in studio.catalog:
        known.add(game.game_id)
        if game.support_level == "Active":
            load += 0.04
        elif game.support_level == "Maintenance":
            load += 0.015
    load += sum(0.04 for sale in studio.active_sales if sale.game_id not in known)
    return min(0.30, load)


def capacity_drains(studio: Studio) -> list[str]:
    """Human-readable list of everything currently slowing original work.

    Read-only presentation helper: mirrors the multipliers in
    :func:`projected_weekly_output` so screens can show *why* capacity is
    reduced instead of just that it is.
    """
    drains = []
    allocations = activity_allocations(studio)
    contract = studio.contract
    if contract:
        progress = 0 if contract.required_work <= 0 else contract.work_done / contract.required_work
        drains.append(f"JOB {contract.client} {allocations['contract']:.0%} ({progress:.0%} done, due {contract.weeks_left}w)")
    if allocations["promotion"] > 0:
        drains.append(f"promotions {allocations['promotion']:.0%}")
    if allocations["update"] > 0:
        drains.append(f"updates {allocations['update']:.0%}")
    if allocations["research"] > 0:
        drains.append(f"R&D {allocations['research']:.0%}")
    if allocations.get("community", 0) > 0:
        drains.append(f"community {allocations['community']:.0%}")
    unavailable = sum(1 for employee in studio.team if not employee_available(employee))
    if unavailable:
        drains.append(f"{unavailable} unavailable")
    live_titles = live_title_count(studio)
    if live_titles:
        support_load = allocations["support"]
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
    state.spinoff_franchise_id = game.franchise_id
    base_title = game.title
    if game.generation > 1:
        current_suffix = f" {roman_number(game.generation)}"
        if base_title.endswith(current_suffix):
            base_title = base_title[: -len(current_suffix)]
    state.draft_title = f"{base_title} {roman_number(game.generation + 1)}"
    state.modal = "new_game"
    state.new_game_step = 2
    state.selected_focus = 0


def projected_weekly_output(studio: Studio, focus: list[int] | tuple[int, ...]) -> float:
    output = coordinated_team_output(studio, focus) * activity_allocations(studio, assume_project=True)["project"]
    return max(0.1, output)


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
    monetization = selected_monetization_model(state)
    price_point = selected_price_point(state)
    announcement = selected_announcement_strategy(state)
    release_policy = selected_release_policy(state)
    publisher = publisher_by_name(studio.pending_publisher)
    requirements = plan_requirements(state)
    if requirements:
        state.log(f"Plan not production-ready: requires {', '.join(requirements)}.")
        return False
    cost = scope["setup"] + channel["fee"] + marketing["cost"] + game_format["setup"] + strategy["setup"] + int(monetization["setup_cost"])
    publisher_advance = publisher["advance"] if publisher else 0
    if studio.cash + publisher_advance < cost + monthly_fixed_cost(studio):
        state.log(f"Plan rejected: ${cost:,} setup would leave less than one month of runway.")
        return False
    focus = concept_focus(state)
    state.focus = list(focus)
    output = projected_weekly_output(studio, focus)
    truth = market_truth(state)
    report = market_report(state)
    total_work = truth["work"]
    planned_weeks = max(4, round(report["work"] / output))
    promised_release_week = state.clock.week + planned_weeks if release_policy["key"] == "announced_date" else 0
    initial_hype = 5 + marketing["boost"] / 25 + (publisher["hype"] if publisher else 0)
    awareness = initial_awareness_by_cohort(state, initial_hype, marketing["boost"], str(announcement["key"]))
    promises = []
    if promised_release_week:
        promises.append({"kind": "release_date", "due_week": promised_release_week, "status": "open", "risk": release_policy["promise_risk"]})
    if strategy.get("expect_weeks"):
        promises.append({"kind": "update_cadence", "due_week": 0, "interval_weeks": strategy["expect_weeks"], "status": "planned", "risk": 0.20})
    if announcement["key"] == "public_roadmap":
        promises.append({"kind": "public_roadmap", "due_week": promised_release_week or state.clock.week + planned_weeks, "status": "open", "risk": announcement["promise_risk"]})
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
        price=float(price_point["price"]),
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
        market_score_start=truth["score"],
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
        hype=initial_hype,
        production_cost=scope["setup"] + channel["fee"] + game_format["setup"] + strategy["setup"] + int(monetization["setup_cost"]),
        marketing_cost=marketing["cost"],
        publisher=publisher["name"] if publisher else "",
        publisher_advance=publisher_advance,
        publisher_recoup_share=publisher["recoup_share"] if publisher else 0.0,
        publisher_post_recoup_share=publisher["post_recoup_share"] if publisher else 0.0,
        publisher_visibility=publisher["visibility"] if publisher else 0,
        monetization=str(monetization["key"]),
        announcement_strategy=str(announcement["key"]),
        release_policy=str(release_policy["key"]),
        announced_week=state.clock.week if announcement["key"] != "stealth" else 0,
        promised_release_week=promised_release_week,
        awareness_by_cohort=awareness,
        promises=promises,
        quality_dimensions={"gameplay": 0.0, "content": 0.0, "stability": 0.0, "performance": 0.0},
        trust=max(5.0, min(95.0, studio.studio_trust + float(announcement["trust"]))),
        novelty=max(10.0, min(95.0, 50 + truth["trend"] + primary_direction["market"])),
        cultural_resonance=truth["cultural_resonance"],
        forecast_work_low=report["work_low"],
        forecast_work_high=report["work_high"],
    )
    add_expense(studio, scope["setup"] + game_format["setup"] + strategy["setup"] + int(monetization["setup_cost"]), "Development")
    add_expense(studio, channel["fee"], "Store fees")
    add_expense(studio, marketing["cost"], "Marketing")
    if publisher:
        financing_inflow(studio, publisher_advance, "Publisher advance", date=state.clock.current_date, counterparty=publisher["name"], memo=f"Recoupable advance for {title[:48]}")
        studio.pending_publisher = ""
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
    funding_note = f" {publisher['name']} advanced ${publisher_advance:,}; it recoups from sales." if publisher else ""
    state.log(f"Paid ${cost:,}. Research forecast: {report['audience_low']:,}-{report['audience_high']:,} interested, {report['competitors_low']}-{report['competitors_high']} rivals, about {planned_weeks} weeks.{funding_note}")
    emit_event(
        state,
        "project_greenlit",
        f"{project.title} entered production as {monetization['name']} at ${project.price:.2f}.",
        "info",
        "project",
        project.title,
        {"price": project.price, "monetization": project.monetization, "release_policy": project.release_policy},
    )
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
    burden = round(candidate.monthly_salary * 0.13)
    per_head = round((420 + 260) * studio.inflation_index) + sum(upgrade_by_key(key).get("per_employee", 0) for key in studio.upgrades)
    if studio.cash < recruiting + monthly_fixed_cost(studio) + candidate.monthly_salary + burden + per_head:
        state.log(f"Cannot responsibly hire {candidate.name}; there is not enough runway.")
        return False
    add_expense(studio, recruiting, "Recruiting")
    candidate.onboarding_weeks_left = 4
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
    if studio.followers >= 5_000:
        studio.studio_trust = max(0.0, studio.studio_trust - 0.5)
    state.log(f"Let {employee.name} go. Two weeks of severance cost ${severance:,}; team morale fell.")
    return True


def research_branch_counts(studio: Studio) -> dict[str, int]:
    counts = {branch: 0 for branch in RESEARCH_BRANCHES}
    for key in completed_research_keys(studio):
        node = research_by_key(key)
        if node and node["tier"] > 0:
            counts[node["branch"]] += 1
    return counts


def research_work_requirement(studio: Studio, node: dict) -> float:
    base = float(node["work"])
    if base <= 0:
        return 0.0
    counts = research_branch_counts(studio)
    own = counts[node["branch"]]
    strongest = max(counts.values(), default=0)
    discount = min(0.20, own * 0.035)
    penalty = min(0.30, max(0, strongest - own - 1) * 0.07)
    if has_research(studio, "executive_management"):
        penalty *= 0.5
    return max(1.0, round(base * (1 - discount + penalty), 1))


def research_requirements(studio: Studio, node: dict) -> list[str]:
    requirements = []
    completed = completed_research_keys(studio)
    missing = [key for key in node.get("prereq", ()) if key not in completed]
    if missing:
        names = [research_by_key(key)["name"] for key in missing if research_by_key(key)]
        requirements.append("requires " + ", ".join(names))
    tier = node.get("tier", 0)
    team_required = (1, 1, 2, 4, 8, 18)[min(5, tier)]
    reputation_required = (0, 0, 0, 4, 15, 35)[min(5, tier)]
    if len(studio.team) < team_required:
        requirements.append(f"team {team_required}")
    if studio.reputation < reputation_required:
        requirements.append(f"reputation {reputation_required}")
    return requirements


def queue_research(state: GameState, node_key: str) -> bool:
    studio = state.studio
    node = research_by_key(node_key)
    if node is None:
        return False
    queued_keys = {job.node_key for job in ([studio.active_research] if studio.active_research else []) + studio.research_queue}
    if has_research(studio, node_key):
        state.log(f"{node['name']} is already completed.")
        return False
    if node_key in queued_keys:
        state.log(f"{node['name']} is already in the R&D queue.")
        return False
    requirements = research_requirements(studio, node)
    if requirements:
        state.log(f"Cannot start {node['name']}: {'; '.join(requirements)}.")
        return False
    if studio.cash < node["cost"] + monthly_fixed_cost(studio):
        state.log(f"Cannot start {node['name']} without risking next month's bills.")
        return False
    add_expense(studio, node["cost"], "Research & development")
    job = ResearchJob(node_key, research_work_requirement(studio, node), node["cost"])
    if studio.active_research is None:
        studio.active_research = job
        status = "Started"
    else:
        studio.research_queue.append(job)
        status = "Queued"
    state.log(f"{status} R&D: {node['name']} for ${node['cost']:,} and {job.required_work:,.0f} research work.")
    return True


def buy_upgrade(state: GameState) -> bool:
    branch = RESEARCH_BRANCHES[state.selected_research_branch % len(RESEARCH_BRANCHES)]
    nodes = research_nodes_for_branch(branch)
    state.selected_upgrade = max(0, min(state.selected_upgrade, len(nodes) - 1))
    return queue_research(state, nodes[state.selected_upgrade]["key"])


def start_next_research(state: GameState) -> None:
    if state.studio.active_research is None and state.studio.research_queue:
        state.studio.active_research = state.studio.research_queue.pop(0)
        node = research_by_key(state.studio.active_research.node_key)
        if node:
            state.log(f"Started queued R&D: {node['name']}.")


def cancel_queued_research(state: GameState, index: int = 0) -> bool:
    if not state.studio.research_queue:
        state.log("There is no waiting research to cancel; active R&D can only be paused by lowering its priority.")
        return False
    index = max(0, min(index, len(state.studio.research_queue) - 1))
    job = state.studio.research_queue.pop(index)
    node = research_by_key(job.node_key)
    refund = round(job.cost * 0.75)
    add_revenue(state.studio, refund, "Research refunds")
    state.log(f"Cancelled {node['name'] if node else job.node_key}; recovered ${refund:,} of the committed budget.")
    return True


def research_weekly_output(studio: Studio) -> float:
    share = activity_allocations(studio)["research"]
    output = coordinated_team_output(studio, "Research") * share
    if has_research(studio, "research_lab"):
        output *= 1.20
    return max(0.0, output)


def estimated_research_weeks(studio: Studio, node: dict) -> int:
    job = studio.active_research if studio.active_research and studio.active_research.node_key == node["key"] else None
    required = max(0.0, (job.required_work - job.work_done) if job else research_work_requirement(studio, node))
    output = research_weekly_output(studio)
    if output <= 0:
        share = 0.22 if studio.current_project else 1.0
        output = coordinated_team_output(studio, "Research") * share * (1.20 if has_research(studio, "research_lab") else 1.0)
    return max(0, math.ceil(required / max(0.1, output)))


def process_research(state: GameState, workday: bool = True) -> None:
    start_next_research(state)
    studio = state.studio
    job = studio.active_research
    if job is None or not workday:
        return
    output = research_weekly_output(studio) / 5
    job.work_done = min(job.required_work, job.work_done + output)
    if job.work_done < job.required_work:
        return
    node = research_by_key(job.node_key)
    if job.node_key not in studio.completed_research:
        studio.completed_research.append(job.node_key)
    if job.node_key not in studio.upgrades:
        studio.upgrades.append(job.node_key)
    if job.node_key == "auto_leave":
        studio.auto_vacation = True
    studio.active_research = None
    state.log(f"Completed R&D: {node['name'] if node else job.node_key}. {node['effect'] if node else ''}")
    start_next_research(state)


def cycle_work_priority(state: GameState, kind: str) -> int:
    if not has_research(state.studio, "department_leads"):
        state.log("Automatic work priorities require Department Leads research.")
        return state.studio.work_priorities.get(kind, 2)
    value = (state.studio.work_priorities.get(kind, 2) + 1) % 4
    state.studio.work_priorities[kind] = value
    labels = ("PAUSED", "LOW", "NORMAL", "HIGH")
    state.log(f"{kind.title()} priority set to {labels[value]}.")
    return value


CONTRACT_TYPES = {
    "Design": ("systems design brief", "level-design blockout", "economy rebalance", "prototype design"),
    "Art": ("environment art pack", "UI art production", "character asset batch", "marketing art kit"),
    "Audio": ("soundtrack commission", "sound-effects pass", "dialogue editing", "audio implementation"),
    "Code": ("platform port", "networking prototype", "tools programming", "performance optimization"),
    "Generalist": ("vertical slice", "game-jam prototype", "educational game", "interactive installation"),
}
CONTRACT_CLIENTS = ("Northstar Media", "Copper Finch", "Atlas Learning", "Pixel Harbor", "Redwood Interactive", "Civic Lab", "Moonshot Agency")


def contract_weekly_output(studio: Studio, focus: str) -> float:
    share = activity_allocations(studio)["contract"]
    if share <= 0 and studio.contract is None:
        available = 1 - live_support_load(studio)
        share = min(0.42, available * (0.50 if studio.current_project else 1.0))
    output = coordinated_team_output(studio, focus) * share
    return max(0.0, output)


def estimated_contract_weeks(studio: Studio, contract: Contract) -> int:
    remaining = max(0, contract.required_work - contract.work_done)
    if contract.required_work <= 0:
        return max(1, contract.weeks_left)
    return max(1, math.ceil(remaining / max(0.1, contract_weekly_output(studio, contract.focus))))


def contract_offer_eta_weeks(contract: Contract) -> int:
    """Return the workload estimate quoted when this offer was generated."""
    return max(1, contract.weeks_left - 2 - contract.difficulty // 2)


# Below this contractor reputation (and before a few delivered jobs) clients
# only offer unpaid portfolio work: you build contacts, not savings.
PAID_CONTRACT_REPUTATION = 12
UNPAID_CONTRACT_HEAD_START = 3


def generate_contract_offer(studio: Studio, rng: random.Random, difficulty: int) -> Contract:
    focus = rng.choice(tuple(CONTRACT_TYPES))
    required_work = 65 + difficulty * 55 + rng.randint(0, 45)
    reputation_required = max(0, (difficulty - 1) * 15)
    client = rng.choice(CONTRACT_CLIENTS)
    relationship = studio.client_relationships.get(client, 0.0)
    unpaid = (
        studio.contractor_reputation < PAID_CONTRACT_REPUTATION
        and studio.contracts_completed < UNPAID_CONTRACT_HEAD_START
    )
    rate = (85 + difficulty * 28 + studio.contractor_reputation * 1.1 + relationship * 0.8) * studio.inflation_index
    payout = 0 if unpaid else max(5_000, round(required_work * rate / 500) * 500)
    provisional = Contract(
        rng.choice(CONTRACT_TYPES[focus]),
        1,
        payout,
        studio.next_contract_id,
        client,
        focus,
        difficulty,
        float(required_work),
        reputation_required=reputation_required,
        deposit=0 if unpaid else max(500, round(payout * 0.15 / 100) * 100),
        late_penalty=0 if unpaid else max(500, round(payout * 0.12 / 100) * 100),
        quality_target=45 + difficulty * 7,
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
    for offer in studio.contract_offers:
        offer.expires_week = state.clock.week + 4
    state.selected_contract = next((index for index, offer in enumerate(studio.contract_offers) if offer.reputation_required <= studio.contractor_reputation), -1)
    if announce:
        state.log(f"The Contract Board refreshed with {len(studio.contract_offers)} offers.")
    if studio.auto_contracts:
        queue_all_contracts(state)


def start_next_contract(state: GameState) -> None:
    studio = state.studio
    if studio.contract is None and studio.contract_queue:
        studio.contract = studio.contract_queue.pop(0)
        contract = studio.contract
        state.log(f"Started {studio.contract.client}'s {studio.contract.title} ({studio.contract.focus}).")


def accept_contract_offer(state: GameState, index: int | None = None, automatic: bool = False) -> bool:
    studio = state.studio
    if studio.closed or not studio.contract_offers:
        return False
    selected = state.selected_contract if index is None else index
    if selected < 0:
        return False
    selected = min(selected, len(studio.contract_offers) - 1)
    contract = studio.contract_offers[selected]
    if studio.contractor_reputation < contract.reputation_required:
        state.log(f"{contract.client} requires {contract.reputation_required} contractor reputation; you have {studio.contractor_reputation:.0f}.")
        return False
    if len(studio.contract_queue) >= 3:
        state.log("The contract queue is full. Deliver existing commitments before accepting another client.")
        return False
    contract.auto_accepted = automatic
    contract.accepted_week = state.clock.week
    contract.original_deadline_week = state.clock.week + contract.weeks_left
    studio.contract_offers.pop(selected)
    if studio.contract is None:
        studio.contract = contract
        if contract.payout:
            state.log(f"Accepted {contract.client}'s {contract.title}: ${contract.payout:,}, {contract.focus}, due in {contract.weeks_left} weeks.")
        else:
            state.log(f"Accepted {contract.client}'s {contract.title}: unpaid portfolio work, {contract.focus}, due in {contract.weeks_left} weeks.")
    else:
        studio.contract_queue.append(contract)
        state.log(f"Queued {contract.client}'s {contract.title} behind {len(studio.contract_queue)} accepted contract(s).")
    if contract.deposit:
        add_revenue(studio, contract.deposit, "Contract deposits")
    state.selected_contract = next((index for index, offer in enumerate(studio.contract_offers) if offer.reputation_required <= studio.contractor_reputation), -1)
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
    if not has_research(studio, "contract_automation"):
        state.log("Automatic contracts require the Client Relations Office.")
        return False
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
    tools_bonus = 2 if "tools" in studio.upgrades else 0
    content_bonus = min(14, round(4 * math.sqrt(max(0, len(studio.team) - 1))))
    previous_game = next((game for game in studio.catalog if game.game_id == project.sequel_of), None)
    sequel_quality = 0 if previous_game is None else round((previous_game.score - 50) / 8)
    sequel_fatigue = max(0, project.generation - 3) * 2
    market_quality = round((project.market_score - 50) / 10)
    formula_score = 22 + average_skill * 0.66 + match + focus_bonus + platform_fit(project) + direction_bonus + market_quality + tools_bonus + content_bonus + sequel_quality - sequel_fatigue - defect_penalty - scope_risk
    quality_dimensions = project_quality_dimensions(studio, project, average_skill, defect_penalty, focus_bonus)
    dimensions_score = (
        quality_dimensions["gameplay"] * 0.24
        + quality_dimensions["depth"] * 0.10
        + quality_dimensions["content"] * 0.14
        + quality_dimensions["originality"] * 0.12
        + quality_dimensions["art"] * 0.10
        + quality_dimensions["audio"] * 0.05
        + quality_dimensions["ux"] * 0.08
        + quality_dimensions["stability"] * 0.10
        + quality_dimensions["performance"] * 0.07
    )
    score = max(20, min(96, round(formula_score * 0.48 + dimensions_score * 0.52)))
    refund_rate = max(0.03, min(0.24, 0.16 - score / 1_000 + defect_rate * 0.35))
    marketing = marketing_by_name(project.marketing_name)
    genre_audience = studio.genre_fans.get(project.genre, 0)
    franchise = franchise_by_id(studio, project.franchise_id)
    freshness = 1 - min(0.6, franchise.fatigue / 150) if franchise else 1.0
    comeback = 1.0
    if franchise and project.sequel_of:
        franchise_games = [game for game in studio.catalog if game.franchise_id == franchise.franchise_id]
        last_activity = max(max(game.release_week, game.last_update_week) for game in franchise_games)
        quiet_years = max(0.0, (state.clock.week - last_activity) / 52)
        comeback += min(0.35, max(0.0, quiet_years - 1) * 0.12)
    sequel_audience = (genre_audience * 0.45 if project.sequel_of else genre_audience * 0.10) * freshness * comeback
    scope_data = scope_by_name(project.scope)
    format_data = format_by_name(project.game_format)
    strategy_data = release_strategy_by_name(project.release_strategy)
    scope_multiplier = (
        scope_data.get("sales", scope_data["market"])
        * format_data.get("sales", 1.0)
        * strategy_data.get("sales", 1.0)
    )
    open_market = market_share_multiplier(state, project.genre, project.channel)
    model = monetization_by_key(project.monetization)
    launch_awareness = dict(project.awareness_by_cohort)
    franchise_reach = min(0.35, (franchise.awareness / 8_000 if franchise else 0.0) + sequel_audience / 2_000_000)
    for cohort in COHORTS:
        launch_awareness[cohort.key] = min(
            0.98,
            launch_awareness.get(cohort.key, 0.0)
            * float(model["acquisition_multiplier"])
            * (1 + project.publisher_visibility * 0.12)
            + franchise_reach,
        )
    launch_offer = ProductOffer(
        product_id="launch",
        genre=project.genre,
        secondary_genre=project.secondary_genre,
        topic=project.topic,
        target_audience=project.target_audience,
        game_format=project.game_format,
        monetization=project.monetization,
        price=project.price,
        quality=score,
        user_rating=score,
        awareness_by_cohort=launch_awareness,
        owners_by_cohort={},
        age_weeks=0,
        hype=project.hype,
        trust=(project.trust + studio.studio_trust) / 2,
        sentiment=score,
        novelty=project.novelty,
        network_health=70 if project.game_format != "Offline solo" else 100,
        store_reach=project.reach * studio_store_visibility(studio),
        platform_category=project.category,
        cultural_resonance=project.cultural_resonance,
        lifecycle_state="launch",
    )
    launch_results = allocate_weekly_demand(
        [launch_offer, *competitor_product_offers(state)],
        studio_macro_snapshot(studio),
        studio.seed + state.clock.week * 65_537 + studio.next_game_id,
    )
    launch_result = launch_results[0]
    viral_rng = random.Random(studio.seed + state.clock.week * 97_409 + studio.next_game_id)
    viral_chance = min(0.18, max(0.005, (score - 55) / 400 + project.novelty / 1_500 + project.hype / 4_000))
    viral_coefficient = 0.0
    if viral_rng.random() < viral_chance:
        viral_coefficient = viral_rng.uniform(1.15, 3.5)
        viral_awareness = {key: min(0.99, value * viral_coefficient) for key, value in launch_awareness.items()}
        launch_offer = replace(launch_offer, awareness_by_cohort=viral_awareness, hype=min(100, project.hype + 25))
        launch_result = allocate_weekly_demand(
            [launch_offer, *competitor_product_offers(state)],
            studio_macro_snapshot(studio),
            studio.seed + state.clock.week * 65_537 + studio.next_game_id,
        )[0]
        launch_awareness = viral_awareness
    units = max(0, launch_result.units)
    evergreen_units = 0
    game_id = studio.next_game_id
    studio.next_game_id += 1
    known_bugs = min(project.known_defects, max(0, project.defects - 0.01))
    rating_rng = random.Random(studio.seed + game_id * 37 + state.clock.week)
    press_rating = max(20.0, min(98.0, score + rating_rng.uniform(-5, 4)))
    segments = build_segments(studio, project, score, known_bugs, sequel_quality, sequel_fatigue, rating_rng)
    segment_weight = sum(segment.weight for segment in segments if segment.weight > 0)
    user_rating = max(15.0, min(99.0, sum(segment.satisfaction * segment.weight for segment in segments if segment.weight > 0) / segment_weight if segment_weight else float(score)))
    hype_backlash = max(0.0, project.hype - (SCOPE_HYPE_CEILING.get(project.scope, 100) + max(0, project.market_score - 55)))
    game = ReleasedGame(
        game_id,
        project.title,
        project.genre,
        project.topic,
        project.channel,
        score,
        state.clock.current_date.isoformat(),
        state.clock.week,
        project.sequel_of,
        project.generation,
        units_sold=project.early_access_units,
        net_revenue=project.early_access_revenue,
        hype=min(150, project.hype + score / 5),
        active_players=0.0,
        monthly_players=0,
        peak_monthly_players=0,
        production_cost=project.production_cost,
        labor_cost=project.labor_cost,
        marketing_cost=project.marketing_cost,
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
        last_update_week=state.clock.week,
        segments=segments,
        hype_backlash=round(hype_backlash, 1),
        publisher=project.publisher,
        publisher_advance=project.publisher_advance,
        monetization=project.monetization,
        announcement_strategy=project.announcement_strategy,
        release_policy=project.release_policy,
        quality_dimensions=quality_dimensions,
        cultural_resonance=dict(project.cultural_resonance),
        novelty=project.novelty,
        trust=project.trust,
        sentiment=round(user_rating, 1),
        review_count=0,
        lifecycle_state="launch",
        viral_coefficient=viral_coefficient,
        network_health=70.0 if project.game_format != "Offline solo" else 100.0,
        technical_debt=project.technical_debt,
        promises=[dict(item) for item in project.promises],
        postmortem={
            "forecast_audience": [project.forecast_audience_low, project.forecast_audience_high],
            "forecast_work": [project.forecast_work_low, project.forecast_work_high],
            "actual_work": round(project.total_work),
            "planned_weeks": project.planned_weeks,
            "actual_weeks": project.weeks,
            "launch_demand": units,
            "drivers": list(launch_result.explanation_drivers),
        },
        early_access=project.early_access,
        early_access_week=project.early_access_week,
    )
    studio.catalog.append(game)
    if hype_backlash >= 15:
        state.log(f"Players feel {project.title} was overhyped: a {project.scope} game with a familiar pitch cannot carry {project.hype:.0f} hype. Expect reviews to cool and retention to fade.")
    if score < 45:
        lost_followers = round(studio.followers * 0.15)
        studio.followers = max(0, studio.followers - lost_followers)
        studio.reputation = max(0, studio.reputation - 4)
        state.log(f"Players turn on the studio: {game.title} shipped underdeveloped (score {score}); {lost_followers:,} followers left.")
    elif defect_rate > 0.08:
        lost_followers = round(studio.followers * 0.05)
        studio.followers = max(0, studio.followers - lost_followers)
        state.log(f"Fans complain that {game.title} needed more time in QA; {lost_followers:,} followers left.")
    ensure_franchise_for_release(state, project, game, project.early_access_units, score)
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
        publisher=project.publisher,
        publisher_recoup_share=project.publisher_recoup_share,
        publisher_post_recoup_share=project.publisher_post_recoup_share,
        publisher_recoupable=project.publisher_advance,
        awareness_by_cohort=dict(launch_awareness),
        owners_by_cohort={cohort.key: 0 for cohort in COHORTS},
        refunded_by_cohort={cohort.key: 0 for cohort in COHORTS},
        interested_by_cohort=dict(launch_result.interested_by_cohort),
        wishlists_by_cohort=dict(launch_result.wishlists_by_cohort),
        payers_by_cohort={cohort.key: 0 for cohort in COHORTS},
        weekly_result_by_cohort=dict(launch_result.units_by_cohort),
        unmet_potential=launch_result.unmet_potential,
        demand_drivers=list(launch_result.explanation_drivers),
        lifecycle_state="launch",
        price_history=[{"week": state.clock.week, "price": project.price, "reason": "launch"}],
        units_sold=project.early_access_units,
    )
    studio.active_sales.append(sale)
    studio.current_project = None
    studio.released_games += 1
    if project.channel == "itch.io":
        studio.itch_releases += 1
        remaining = ITCH_RELEASES_BEFORE_STEAM - studio.itch_releases
        if remaining == 0:
            state.log(f"Steam approves your developer page after {studio.itch_releases} itch.io releases; the paid storefronts are watching you now.")
            emit_event(state, "storefront_unlocked", "Steam developer page approved.", "success", "studio", studio.name)
        elif remaining > 0:
            state.log(f"itch.io release {studio.itch_releases} of {ITCH_RELEASES_BEFORE_STEAM} - {remaining} more free games before paid storefronts take you seriously.")
    studio.reputation = max(0, studio.reputation + (score - 50) / 12)
    for key in (f"genre:{project.genre}", f"format:{project.game_format}", f"monetization:{project.monetization}", f"scope:{project.scope}"):
        studio.market_experience[key] = studio.market_experience.get(key, 0.0) + 1.0
    forecast_center = (project.forecast_audience_low + project.forecast_audience_high) / 2
    calibration_error = abs(units - forecast_center) / max(1.0, forecast_center)
    studio.forecast_calibration[project.genre] = studio.forecast_calibration.get(project.genre, 0.5) * 0.75 + min(2.0, calibration_error) * 0.25
    game.postmortem["forecast_error"] = round(calibration_error, 3)
    game.postmortem["quality_dimensions"] = dict(quality_dimensions)
    # Even an unknown studio's first release reaches friends, lurkers, and one
    # small curator - never zero traction, never enough to get rich either.
    # A genuine hit converts launch attention into lasting audience.
    launch_followers = max(12, round((project.early_access_units + units) * (0.005 + (score / 100) ** 2 * 0.02)))
    studio.followers += launch_followers
    studio.genre_fans[project.genre] = studio.genre_fans.get(project.genre, 0) + launch_followers
    studio.topic_fans[project.topic] = studio.topic_fans.get(project.topic, 0) + launch_followers
    if project.secondary_genre and project.secondary_genre != project.genre:
        studio.genre_fans[project.secondary_genre] = studio.genre_fans.get(project.secondary_genre, 0) + launch_followers // 2
    if project.secondary_topic and project.secondary_topic != project.topic:
        studio.topic_fans[project.secondary_topic] = studio.topic_fans.get(project.secondary_topic, 0) + launch_followers // 2
    state.log(f"Released {project.title} after {project.weeks} weeks: {score}/100, {refund_rate:.0%} expected refunds, {math.floor(known_bugs)} known bugs.")
    state.log(f"The market currently supports {units:,} first-week acquisitions from a finite audience. You keep {(1 - project.platform_cut):.0%} before refunds; {open_market:.0%} of this storefront's genre demand remains open.")
    if viral_coefficient:
        state.log(f"Unexpected creator and community momentum is multiplying awareness of {project.title} by {viral_coefficient:.1f}x.")
    emit_event(
        state,
        "game_released",
        f"{project.title} launched to {units:,} expected first-week acquisitions.",
        "success" if viral_coefficient else "info",
        "game",
        game_id,
        {"units": units, "score": score, "viral_coefficient": viral_coefficient, "drivers": list(launch_result.explanation_drivers)},
    )
    if units >= 40_000:
        copycat_rng = random.Random(studio.seed + state.clock.week * 911)
        candidates = [item for item in studio.competitors if item.size >= 4 and len(item.in_development) < 2]
        for copycat in copycat_rng.sample(candidates, min(2, len(candidates))):
            quality = max(25, min(96, round(copycat.reputation + copycat_rng.uniform(-10, 8))))
            weeks = max(10, round(copycat_rng.uniform(14, 30) / (0.5 + copycat.size / 6)))
            title = generate_game_title(project.genre, copycat_rng.choice(TOPICS), studio.seed + state.clock.week + copycat.competitor_id)
            copycat.in_development.append(CompetitorGame(title, "", project.genre, quality, round(copycat_rng.uniform(60, 120), 1), weeks, copycat.size))
        if candidates:
            state.log(f"Competitors noticed {project.title}; similar projects are already in production.")


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
    roll_rng = random.Random(state.studio.seed + state.clock.week * 17 + project.next_decision * 31 + len(project.decisions_made))
    if not automatic and option_index == 1 and roll_rng.random() < 0.35:
        extra_defects = round(remaining / 400) + 3
        project.defects += extra_defects
        for employee in state.studio.team:
            employee.fatigue = min(100, employee.fatigue + 4)
        state.log(f"The gamble backfired: crunch produced {extra_defects} extra defects and left the team exhausted.")
    elif not automatic and option_index == 0 and project.market_score >= 62 and roll_rng.random() < 0.30:
        project.market_score = max(10, project.market_score - 5)
        state.log("Commentators call the safe choice predictable; market interest cools.")
    if not automatic and project.decision_resume_on_close and state.time_speed_index == 0:
        state.time_speed_index = max(1, state.resume_speed_index)
    project.decision_resume_on_close = False
    source = "Auto-selected" if automatic else "Committed to"
    state.log(f"{source} '{option['name']}' at {decision['title'].lower()} for {project.title}. {option['effect']}.")
    return True


def project_ready_for_launch(state: GameState) -> None:
    project = state.studio.current_project
    if project is None:
        return
    if project.release_policy == "ship_when_ready":
        finish_project(state)
        return
    project.ready_for_release = True
    project.ready_week = state.clock.week
    if project.release_policy == "announced_date" and project.promised_release_week and state.clock.week >= project.promised_release_week:
        finish_project(state)
        return
    state.log(f"{project.title} has gone gold. Choose when to release it; every held week carries payroll and attention risk.")
    emit_event(state, "release_ready", f"{project.title} is ready for release.", "action", "project", project.title)


def release_ready_project(state: GameState) -> bool:
    project = state.studio.current_project
    if project is None or not project.ready_for_release:
        state.log("No finished game is waiting for release.")
        return False
    if project.promised_release_week and state.clock.week > project.promised_release_week:
        delay = state.clock.week - project.promised_release_week
        project.trust = max(0.0, project.trust - min(20.0, delay * 1.5))
        state.studio.studio_trust = max(0.0, state.studio.studio_trust - min(8.0, delay * 0.5))
    finish_project(state)
    return True


def launch_early_access(state: GameState) -> bool:
    project = state.studio.current_project
    if project is None or project.monetization != "paid_early_access":
        state.log("This project is not planned for paid Early Access.")
        return False
    if project.early_access:
        state.log(f"{project.title} is already in Early Access.")
        return False
    if project.progress < 0.45:
        state.log("Early Access requires a playable build at least 45% through production.")
        return False
    project.early_access = True
    project.early_access_week = state.clock.week
    project.trust = max(0.0, project.trust - max(0.0, 65 - project.progress * 100) * 0.15)
    project.hype = min(200.0, project.hype + 12)
    project.promises.append({"kind": "early_access_1_0", "due_week": state.clock.week + max(12, project.planned_weeks - project.weeks), "status": "open", "risk": 0.45})
    state.log(f"{project.title} entered paid Early Access at {project.progress:.0%} completion. Revenue and public reviews now arrive before 1.0.")
    emit_event(state, "early_access_started", f"{project.title} entered paid Early Access.", "warning", "project", project.title)
    return True


def process_early_access_week(state: GameState, project: Project) -> None:
    if not project.early_access:
        return
    owners = project.early_access_owners_by_cohort or {cohort.key: 0 for cohort in COHORTS}
    public_quality = max(20.0, min(88.0, 30 + project.progress * 52 - project.known_defects * 0.7))
    if project.early_access_rating <= 0:
        project.early_access_rating = public_quality
    else:
        project.early_access_rating += (public_quality - project.early_access_rating) * 0.18
    awareness = dict(project.awareness_by_cohort)
    for cohort in COHORTS:
        awareness[cohort.key] = min(0.45, awareness.get(cohort.key, 0.001) * 1.012 + project.early_access_units / max(1, cohort.population) * 0.15)
    offer = ProductOffer(
        product_id="early_access",
        genre=project.genre,
        secondary_genre=project.secondary_genre,
        topic=project.topic,
        target_audience=project.target_audience,
        game_format=project.game_format,
        monetization=project.monetization,
        price=project.price,
        quality=public_quality,
        user_rating=project.early_access_rating,
        awareness_by_cohort=awareness,
        owners_by_cohort=owners,
        age_weeks=max(0, state.clock.week - project.early_access_week),
        hype=project.hype,
        trust=project.trust,
        sentiment=project.early_access_rating,
        novelty=project.novelty,
        network_health=60,
        store_reach=project.reach,
        platform_category=project.category,
        cultural_resonance=project.cultural_resonance,
        lifecycle_state="active",
    )
    result = allocate_weekly_demand(
        [offer, *competitor_product_offers(state)],
        studio_macro_snapshot(state.studio),
        state.studio.seed + state.clock.week * 31_337,
    )[0]
    units = result.units
    gross = units * project.price
    refund_rate = max(0.05, min(0.34, 0.30 - project.early_access_rating / 500 + project.known_defects / 250))
    receipts = gross * (1 - refund_rate) * (1 - project.platform_cut)
    if receipts:
        add_revenue(state.studio, receipts, "Early Access sales")
    project.early_access_units += units
    project.early_access_revenue += receipts
    project.awareness_by_cohort = awareness
    project.wishlists_by_cohort = dict(result.wishlists_by_cohort)
    for key, amount in result.units_by_cohort.items():
        owners[key] = owners.get(key, 0) + amount
    project.early_access_owners_by_cohort = owners
    feedback_discovery = min(max(0.0, project.defects - project.known_defects), max(0.0, units / 2_500))
    project.known_defects = min(project.defects, project.known_defects + feedback_discovery)
    if project.early_access_rating < 45:
        project.trust = max(0.0, project.trust - 1.5)
    elif project.early_access_rating >= 75:
        project.trust = min(100.0, project.trust + 0.5)
    if units > 0:
        state.log(f"Early Access: {project.title} added {units:,} owners, {money_text(receipts)} net, rating {project.early_access_rating:.0f}%.")


def money_text(amount: float) -> str:
    return f"${amount:,.0f}"


def develop_project(state: GameState, day_number: int = 0, week_end: bool = True, workday: bool = True) -> None:
    studio = state.studio
    project = studio.current_project
    if project is None:
        return
    if project.ready_for_release:
        if week_end:
            project.weeks += 1
            hold_decay = 0.985 if project.announcement_strategy == "stealth" else 0.96
            project.hype *= hold_decay
            process_early_access_week(state, project)
            if project.release_policy == "announced_date" and project.promised_release_week and state.clock.week >= project.promised_release_week:
                finish_project(state)
        return
    if project.pending_decision is not None:
        if day_number < project.pending_day + 7:
            return
        resolve_project_decision(state, 0, automatic=True)
    weekly_salary = sum(employee.annual_salary / 52 for employee in studio.team)
    weekly_burden = sum(employee.annual_salary / 52 for employee in studio.team if not employee.founder) * 0.13
    project.labor_cost += (weekly_salary + weekly_burden) / 7 * activity_allocations(studio)["project"]
    if week_end:
        heat_score = max(10, min(100, project.market_score_start + (genre_heat(studio, project.genre) - 1.0) * 80))
        project.market_score = round(max(10, min(100, project.market_score + (heat_score - project.market_score) * 0.02)))
    if not workday:
        if week_end:
            project.weeks += 1
            announcement = announcement_strategy_by_key(project.announcement_strategy) or ANNOUNCEMENT_STRATEGIES[1]
            project.hype *= max(0.90, 1 - float(announcement["hype_decay"]))
            process_early_access_week(state, project)
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
    personal_rows: list[tuple[Employee, float, float]] = []
    for employee in studio.team:
        if not employee_available(employee):
            continue
        contributors += 1
        modifiers = employee_modifiers(employee)
        weighted = sum(skill * percent for skill, percent in zip(employee.skills, project.focus)) / 100
        availability = employee_availability(employee)
        variance = rng.uniform(modifiers["variance_low"], modifiers["variance_high"])
        personal_output = weighted * availability * variance * modifiers["output"] / 5
        weighted += modifiers["quality"]
        defect_factor *= modifiers["defects"]
        if modifiers["team_morale"]:
            for teammate in studio.team:
                if teammate is not employee:
                    teammate.morale = max(0, min(100, teammate.morale + modifiers["team_morale"] / 5))
        personal_rows.append((employee, personal_output, weighted))
    weights = coordination_weights(studio, [row[1] for row in personal_rows])
    for (employee, personal_output, weighted), weight in zip(personal_rows, weights):
        contribution = personal_output * weight
        total_output += contribution
        quality += contribution * weighted
        employee.week_output += contribution
    if has_research(studio, "hardware"):
        total_output *= 1.10
        quality *= 1.10
    project_share = activity_allocations(studio)["project"]
    minimum_team = max(scope_by_name(project.scope)["team"], format_by_name(project.game_format)["team"])
    if len(studio.team) < minimum_team:
        capability_ratio = max(0.15, len(studio.team) / minimum_team)
        total_output *= capability_ratio
        quality *= capability_ratio
        project.technical_debt += (1 - capability_ratio) * 0.08
    total_output *= project_share
    quality *= project_share
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
        announcement = announcement_strategy_by_key(project.announcement_strategy) or ANNOUNCEMENT_STRATEGIES[1]
        project.hype *= max(0.90, 1 - float(announcement["hype_decay"]))
        process_early_access_week(state, project)
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
            project_ready_for_launch(state)
    elif project.work_done >= project.total_work - 0.01:
        if project.defects > 0.5:
            project.bug_work = project.defects * BUG_FIX_WORK_PER_DEFECT * QA_CLEAR_FRACTION
            state.log(f"{project.title} entered bug fixing: {project.defects:.0f} defects from development must be cleared before release.")
        else:
            project_ready_for_launch(state)


def buy_promotion(state: GameState, game_id: int, promotion_index: int) -> bool:
    studio = state.studio
    promotion = PROMOTIONS[promotion_index]
    required_research = research_requirement_for_promotion(promotion["key"])
    if required_research and not has_research(studio, required_research):
        node = research_by_key(required_research)
        state.log(f"{promotion['name']} is locked; complete {node['name'] if node else required_research} first.")
        return False
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
    current_hype = studio.current_project.hype if game_id == 0 and studio.current_project else (game_by_id(studio, game_id).hype if game_by_id(studio, game_id) else 0)
    effectiveness = promotion_hype_effectiveness(promotion, current_hype)
    if effectiveness < 0.6:
        state.log(f"Hype around {target_title} is saturated for {promotion['name']}; only {effectiveness:.0%} will convert before its {promotion['ceiling']} hype ceiling.")
    return True


def project_cash_spent(project: Project) -> float:
    """Cash charged to the project (setup, fees, marketing). Labor is payroll, not a project debit."""
    return project.production_cost + project.marketing_cost


def cancel_current_project(state: GameState) -> bool:
    project = state.studio.current_project
    if project is None:
        state.log("There is no project in development to cancel.")
        return False
    franchise = franchise_by_id(state.studio, project.franchise_id)
    if franchise:
        franchise.fatigue = min(120, franchise.fatigue + 6)
    spent = project_cash_spent(project)
    refund = round(spent * 0.20)
    state.studio.active_promotions = [item for item in state.studio.active_promotions if item.game_id != 0]
    if refund:
        add_revenue(state.studio, refund, "Production refunds")
    cancellation_liability = 0.0
    if project.publisher_advance:
        cancellation_liability += project.publisher_advance * 1.05
        principal_payment(
            state.studio,
            cancellation_liability,
            "Publisher cancellation repayment",
            date=state.clock.current_date,
            counterparty=project.publisher,
            memo=project.title,
        )
    if project.early_access_units:
        customer_refunds = project.early_access_units * project.price
        add_expense(state.studio, customer_refunds, "Early Access refunds")
        cancellation_liability += customer_refunds
        state.studio.studio_trust = max(0.0, state.studio.studio_trust - min(30.0, 8 + project.early_access_units / 5_000))
    if project.hype >= 30 or project.announced_week:
        lost_followers = min(state.studio.followers, round(state.studio.followers * min(0.25, project.hype / 800)))
        state.studio.followers -= lost_followers
        state.studio.studio_trust = max(0.0, state.studio.studio_trust - min(10.0, project.hype / 25))
        state.log(f"Cancelling the publicly known project cost {lost_followers:,} followers and damaged studio trust.")
    title = project.title
    state.studio.current_project = None
    catalogue_count = len(state.studio.catalog)
    state.selected_game = min(state.selected_game, max(0, catalogue_count - 1)) if catalogue_count else 0
    loss = spent - refund + cancellation_liability
    state.log(f"Cancelled {title}; recovered ${refund:,.0f} (20%) and wrote off ${loss:,.0f} including contractual liabilities.")
    emit_event(state, "project_cancelled", f"{title} was cancelled with ${loss:,.0f} lost.", "critical", "project", title, {"loss": loss})
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
    if activity_allocations(state.studio)["promotion"] <= 0:
        return
    promotion = state.studio.active_promotions[0]
    promotion_data = next((item for item in PROMOTIONS if item["name"] == promotion.name), None)
    if promotion_data is None:
        return
    weekly_hype = promotion.hype_total / promotion.total_weeks
    if promotion.game_id == 0 and state.studio.current_project:
        project = state.studio.current_project
        hype_gain = weekly_hype / 7 * promotion_hype_effectiveness(promotion_data, project.hype)
        project.hype = min(200, project.hype + hype_gain)
    else:
        game = game_by_id(state.studio, promotion.game_id)
        if game:
            hype_gain = weekly_hype / 7 * promotion_hype_effectiveness(promotion_data, game.hype)
            game.hype = min(200, game.hype + hype_gain)
            if week_end:
                sale = sale_for_game(state.studio, game.game_id)
                if sale:
                    sale.weekly_units += max(1, round(weekly_hype / 4 * promotion_hype_effectiveness(promotion_data, game.hype)))
    if not week_end:
        return
    promotion.weeks_left -= 1
    if promotion.weeks_left <= 0:
        state.studio.active_promotions.pop(0)
        state.log(f"{promotion.name} for {promotion.target_title} finished.")
        if state.studio.active_promotions:
            next_promotion = state.studio.active_promotions[0]
            state.log(f"Started queued {next_promotion.name} for {next_promotion.target_title}.")


def take_community_action(state: GameState, game_id: int, action_index: int | None = None) -> bool:
    index = state.selected_community_action if action_index is None else action_index
    action = COMMUNITY_ACTIONS[index % len(COMMUNITY_ACTIONS)]
    game = game_by_id(state.studio, game_id) if game_id else None
    project = state.studio.current_project if game_id == 0 else None
    if game is None and project is None:
        state.log("Choose a project or released game before addressing its community.")
        return False
    cost = int(action["cash_cost"])
    if state.studio.cash < cost + monthly_fixed_cost(state.studio):
        state.log(f"Cannot fund {action['name']} without risking committed bills.")
        return False
    if cost:
        add_expense(state.studio, cost, "Community relations")
    target_title = game.title if game else project.title
    job = {
        "action": action["key"],
        "name": action["name"],
        "game_id": game_id,
        "target_title": target_title,
        "weeks_left": int(action["duration_weeks"]),
        "team_load": float(action["team_load"]),
    }
    state.studio.active_community_actions.append(job)
    cooldown_until = state.studio.community_cooldowns.get(str(game_id), 0)
    spamming = state.clock.week < cooldown_until
    effectiveness = 0.25 if spamming else 1.0
    state.studio.community_cooldowns[str(game_id)] = state.clock.week + (4 if action["key"] == "dev_diary" else 8)
    trust_gain = float(action["trust"]) * effectiveness
    awareness_gain = float(action["awareness"]) / 100 * effectiveness
    if spamming:
        state.log("The audience is saturated with studio messaging; this action has a muted effect.")
    if project:
        project.trust = min(100.0, project.trust + trust_gain)
        for cohort in COHORTS:
            current = project.awareness_by_cohort.get(cohort.key, 0.0)
            project.awareness_by_cohort[cohort.key] = max(0.0001, min(0.18, current + awareness_gain * max(0.15, 1 - current)))
        if action["key"] == "open_beta":
            discovered = max(0.0, project.defects - project.known_defects) * 0.45
            project.known_defects = min(project.defects, project.known_defects + discovered)
            project.technical_debt = max(0.0, project.technical_debt - 2)
        elif action["key"] == "roadmap":
            project.promises.append({"kind": "community_roadmap", "due_week": state.clock.week + 16, "status": "open", "risk": 0.30})
    else:
        game.trust = min(100.0, game.trust + trust_gain)
        released_awareness_gain = awareness_gain * 0.4
        issue_effect = float(action["issue_effect"])
        for issue in game.issues:
            if issue.get("status", "open") == "open":
                issue["severity"] = max(0.0, float(issue.get("severity", 0.0)) + issue_effect * 10)
                if issue["severity"] <= 0.25:
                    issue["status"] = "resolved"
        sale = sale_for_game(state.studio, game.game_id)
        if sale:
            for cohort in COHORTS:
                current = sale.awareness_by_cohort.get(cohort.key, 0.0)
                sale.awareness_by_cohort[cohort.key] = max(0.0001, min(0.04, current + released_awareness_gain * max(0.15, 1 - current)))
        if action["key"] == "roadmap":
            game.promises.append({"kind": "content_roadmap", "due_week": state.clock.week + 12, "status": "open", "risk": 0.35})
        elif action["key"] == "apology":
            game.sentiment = min(100.0, game.sentiment + 3)
        elif action["key"] == "community_event":
            game.hype = min(200.0, game.hype + 5)
    state.log(f"Started {action['name']} for {target_title}; it consumes {float(action['team_load']):.0%} team capacity for {action['duration_weeks']}w.")
    emit_event(state, "community_action", f"{action['name']} started for {target_title}.", "info", "game" if game else "project", game_id or target_title)
    return True


def process_community_week(state: GameState) -> None:
    for job in list(state.studio.active_community_actions):
        job["weeks_left"] = int(job.get("weeks_left", 1)) - 1
        if job["weeks_left"] <= 0:
            state.studio.active_community_actions.remove(job)
            state.log(f"{job.get('name', 'Community action')} for {job.get('target_title', 'the community')} finished.")
    for game in state.studio.catalog:
        broken = 0
        for promise in game.promises:
            due = int(promise.get("due_week", 0) or 0)
            if promise.get("status") == "open" and due and state.clock.week > due:
                promise["status"] = "broken"
                broken += 1
        if broken:
            trust_loss = sum(float(item.get("risk", 0.2)) * 12 for item in game.promises if item.get("status") == "broken")
            game.trust = max(0.0, game.trust - trust_loss)
            game.sentiment = max(0.0, game.sentiment - trust_loss * 0.6)
            game.issues.append({"kind": "broken_promise", "severity": min(10.0, trust_loss / 2), "status": "open", "opened_week": state.clock.week})
            state.studio.studio_trust = max(0.0, state.studio.studio_trust - min(3.0, trust_loss * 0.1))
            state.log(f"{game.title}'s community says the studio broke {broken} public promise{'s' if broken != 1 else ''}.")


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
    available = [size for size in UPDATE_SIZES if not research_requirement_for_update(size["name"]) or has_research(state.studio, research_requirement_for_update(size["name"]))]
    index = next((index for index, size in enumerate(available) if size["name"] == game.update_size), 0)
    game.update_size = available[(index + delta) % len(available)]["name"]
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
    required_research = research_requirement_for_update(game.update_size)
    if required_research and not has_research(studio, required_research):
        node = research_by_key(required_research)
        state.log(f"{game.update_size} is locked; complete {node['name'] if node else required_research} first.")
        return False
    size = update_size_by_name(game.update_size)
    if studio.cash < size["cost"] + monthly_fixed_cost(studio):
        state.log(f"Cannot fund {game.update_size} for {game.title} without risking next month's bills.")
        return False
    add_expense(studio, size["cost"], "Live operations")
    game.post_launch_cost += size["cost"]
    job = UpdateJob(
        studio.next_update_id,
        game.game_id,
        game.title,
        game.update_focus,
        game.update_size,
        planned_update_version(studio, game, game.update_size),
        float(size["work"]),
        float(size["bugs"]),
        cost_paid=size["cost"],
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
    refund = round(job.cost_paid * 0.75) if job.cost_paid else 0
    fee = max(50, round(size["cost"] * 0.15)) if not job.cost_paid else job.cost_paid - refund
    if refund:
        add_revenue(state.studio, refund, "Production refunds")
    elif fee:
        add_expense(state.studio, fee, "Cancelled production")
    game = game_by_id(state.studio, job.game_id)
    if game:
        game.post_launch_cost = max(0, game.post_launch_cost - refund)
    rebuild_queued_update_versions(state.studio)
    state.selected_queue_cancellation = min(selected, max(0, len(queue) - 1))
    state.log(f"Cancelled queued {job.size} {job.focus} update for {job.game_title}; abandoned preparation cost ${fee:,}.")
    return True


def finish_game_update(state: GameState, job: UpdateJob, game: ReleasedGame) -> None:
    size = update_size_by_name(job.size)
    focus = update_focus_by_name(job.focus)
    game.updates_released += 1
    game.last_update_week = state.clock.week
    game.version = job.target_version
    game.update_progress = 0
    if job.focus == "New content" or job.size in ("Content", "Expansion"):
        for promise in game.promises:
            if promise.get("status") == "open" and promise.get("kind") in ("content_roadmap", "update_cadence"):
                promise["status"] = "fulfilled"
        game.trust = min(100.0, game.trust + 2.5)
    fixed_existing = 0.0
    if job.focus == "Bug fixes":
        fixed_existing = min(game.actual_bugs, float(size["fixes"]))
        known_fixed = min(game.known_bugs, fixed_existing)
        game.actual_bugs -= fixed_existing
        game.known_bugs -= known_fixed
        for issue in game.issues:
            if issue.get("kind") == "bugs" and issue.get("status", "open") == "open":
                issue["severity"] = max(0.0, float(issue.get("severity", 0.0)) - fixed_existing / 5)
                if issue["severity"] <= 0.25:
                    issue["status"] = "resolved"
    escaped_bugs = float(size["escaped"])
    if job.focus == "Bug fixes":
        escaped_bugs = min(escaped_bugs, fixed_existing * 0.1)
    game.actual_bugs += escaped_bugs
    if game.actual_bugs > 0:
        game.known_bugs = min(game.known_bugs, game.actual_bugs * 0.98)
    game.reported_bug_count = min(game.reported_bug_count, game.known_bug_count)
    rating_factor = max(0.10, (game.score / 100) ** 2)
    if job.focus == "New content":
        game.patch_fatigue = max(0.0, game.patch_fatigue - 3)
    else:
        game.patch_fatigue += {"Hotfix": 0.7, "Patch": 1.5, "Content": 0.5, "Expansion": 0.2, "Paid DLC": 0.3}.get(job.size, 0.5)
    engagement = max(0.3, 1 - game.patch_fatigue * 0.15)
    hype_gain = size["hype"] * focus["hype"] * rating_factor * engagement * max(0.25, 1 - game.hype / 240)
    game.hype = min(200, game.hype + hype_gain)
    returning_players = round(
        (game.monthly_players * 0.20 + game.units_sold * 0.012)
        * size["sales"]
        * focus["players"]
        * rating_factor
        * engagement
    )
    game.active_players += returning_players / 3
    clamp_player_counts(game)
    franchise = franchise_by_id(state.studio, game.franchise_id)
    if franchise:
        if job.focus == "New content":
            franchise.fatigue = max(0, franchise.fatigue - 3)
        elif job.size == "Paid DLC":
            franchise.fatigue = min(120, franchise.fatigue + 3)
        elif job.size == "Expansion":
            franchise.fatigue = max(0, franchise.fatigue - 1)
        elif game.patch_fatigue >= 4:
            franchise.fatigue = min(120, franchise.fatigue + 1)
    if job.size == "Paid DLC":
        studio = state.studio
        strategy = release_strategy_by_name(game.release_strategy)
        reception = strategy.get("dlc_reception", 1.0)
        sale = sale_for_game(studio, game.game_id)
        owner_cohorts = sale.owners_by_cohort if sale else {"all": game.units_sold}
        saturation = 0.72 ** game.dlcs_released
        attachment = max(0.01, min(0.55, (0.05 + game.score / 500) * reception * saturation * community_factor(game)))
        dlc_cohorts = {key: min(owners, round(owners * attachment)) for key, owners in owner_cohorts.items()}
        dlc_units = sum(dlc_cohorts.values())
        gross = dlc_units * size["price"]
        refund_rate = min(0.30, max(0.02, 0.10 - game.user_rating / 2_000 + game.patch_fatigue * 0.01))
        receipts = gross * (1 - refund_rate) * (1 - (sale.platform_cut if sale else 0.30))
        publisher_share = receipts * (sale.publisher_post_recoup_share if sale and sale.publisher else 0.0)
        add_revenue(studio, receipts, "DLC sales")
        if publisher_share:
            add_expense(studio, publisher_share, "Publisher royalties")
        dlc_net = receipts - publisher_share
        game.net_revenue += dlc_net
        game.dlc_revenue += dlc_net
        game.dlcs_released += 1
        game.dlc_owners[str(game.dlcs_released)] = dlc_cohorts
        state.log(f"{game.title}'s paid DLC sold {dlc_units:,} copies at launch and added ${dlc_net:,.0f} studio net.")
        if game.release_strategy == "Free update roadmap":
            game.fans_betrayed = True
            game.user_rating = max(5.0, game.user_rating - 10)
            game.sentiment = max(0.0, game.sentiment - 12)
            game.hype = max(0, game.hype - 25)
            game.issues.append({"kind": "betrayal", "severity": 7.0, "status": "open", "opened_week": state.clock.week})
            lost_followers = min(studio.followers, max(10, round(studio.followers * 0.20)))
            studio.followers = max(0, studio.followers - lost_followers)
            studio.reputation = max(0, studio.reputation - 3)
            franchise = franchise_by_id(studio, game.franchise_id)
            if franchise:
                franchise.fatigue = min(120, franchise.fatigue + 12)
            state.log(f"Fans feel betrayed by the paid DLC for {game.title} after the free-update promise; {lost_followers:,} followers left.")
        elif game.release_strategy == "Complete package":
            game.user_rating = max(5.0, game.user_rating - 2)
            state.log(f"Some players call the paid DLC for {game.title} a cash grab.")
    if not job.cost_paid:
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


def process_sales(state: GameState, week_end: bool = True, day_number: int = 0, market_results: dict[str, DemandResult] | None = None) -> None:
    studio = state.studio
    week_start = day_number % 7 == 1
    if week_end and market_results is None:
        # Direct callers (tests, tooling) get the old allocate-on-demand
        # behavior; the day loop passes one shared allocation for the market.
        market_results = allocate_weekly_market(state)
    else:
        market_results = market_results or {}
    for sale in studio.active_sales:
        if week_start:
            sale.week_units = 0.0
        rng = random.Random(studio.seed + day_number * 131 + sale.game_id * 17)
        game = next((item for item in studio.catalog if item.game_id == sale.game_id), None)
        if game is None:
            continue
        raw_units = max(0.0, sale.weekly_units / 7 * rng.uniform(0.88, 1.12))
        issue_pressure = sum(float(issue.get("severity", 0.0)) for issue in game.issues if issue.get("status", "open") == "open")
        dynamic_refund_rate = max(0.0, min(0.45, sale.refund_rate + game.known_bug_count * 0.002 + issue_pressure * 0.015 - game.updates_released * 0.001))
        if sale.price <= 0:
            dynamic_refund_rate = 0.0
        refunded_units = raw_units * dynamic_refund_rate
        units = max(0.0, raw_units - refunded_units)
        sale.week_units += units
        gross = raw_units * sale.price
        refund_value = refunded_units * sale.price
        platform_deduction = max(0.0, gross - refund_value) * sale.platform_cut
        receipts = max(0.0, gross - refund_value - platform_deduction)
        publisher_share = 0.0
        if sale.publisher:
            remaining_recoup = max(0.0, sale.publisher_recoupable - sale.publisher_recouped)
            if remaining_recoup > 0 and sale.publisher_recoup_share > 0:
                recoup_receipts = min(receipts, remaining_recoup / sale.publisher_recoup_share)
                recoup_payment = min(remaining_recoup, recoup_receipts * sale.publisher_recoup_share)
                post_recoup_receipts = max(0.0, receipts - recoup_receipts)
                publisher_share = recoup_payment + post_recoup_receipts * sale.publisher_post_recoup_share
                sale.publisher_recouped += recoup_payment
            else:
                publisher_share = receipts * sale.publisher_post_recoup_share
            game.publisher_recouped = sale.publisher_recouped
        if receipts:
            add_revenue(studio, receipts, "Game sales")
        if publisher_share:
            add_expense(studio, publisher_share, "Publisher royalties")
        net = receipts - publisher_share
        hosting_rate = game.hosting_rate
        model = monetization_by_key(game.monetization)
        if game.support_level == "Sunset":
            # Servers are shut down; nobody can play and nothing runs.
            hosting_cost = 0.0
        else:
            support_factor = 0.45 if game.support_level == "Maintenance" else 1.0
            per_player = float(model["recurring_cost_per_player"])
            # Variable hosting only; fixed infrastructure rent is charged
            # separately as "Server rent" in the weekly block below.
            hosting_cost = max(
                0.0,
                (units * (0.01 + hosting_rate) + game.monthly_players * (hosting_rate * 0.02 + per_player) / 30) * support_factor,
            )
        add_expense(studio, hosting_cost, "Hosting")
        sale.units_sold += round(units)
        sale.gross_revenue += gross
        sale.net_revenue += net
        game.units_sold += round(units)
        game.refunded_units += round(refunded_units)
        game.refund_value += refund_value
        game.platform_deductions += platform_deduction
        game.publisher_deductions += publisher_share
        game.net_revenue += net
        game.post_launch_cost += hosting_cost
        weekly_mix = sale.weekly_result_by_cohort
        mix_total = max(1, sum(weekly_mix.values()))
        allocated = 0
        for index, cohort in enumerate(COHORTS):
            if index == len(COHORTS) - 1:
                cohort_units = max(0, round(units) - allocated)
            else:
                cohort_units = max(0, round(units * weekly_mix.get(cohort.key, 0) / mix_total))
                allocated += cohort_units
            sale.owners_by_cohort[cohort.key] = min(cohort.population, sale.owners_by_cohort.get(cohort.key, 0) + cohort_units)
            cohort_refunds = max(0, round(refunded_units * weekly_mix.get(cohort.key, 0) / mix_total))
            sale.refunded_by_cohort[cohort.key] = sale.refunded_by_cohort.get(cohort.key, 0) + cohort_refunds
        gained = round(units * max(0.0001, (sale.score / 100) ** 2 * 0.005))
        if sale.price <= 0:
            # Free games are how unknown developers build an audience: a small
            # slice of players follows the dev, and good ones travel fast.
            gained = round(units * max(0.004, (sale.score / 100) ** 2 * 0.03))
            if sale.score >= 75:
                gained *= 3
        studio.followers += gained
        if sale.genre:
            studio.genre_fans[sale.genre] = studio.genre_fans.get(sale.genre, 0) + gained
        studio.topic_fans[game.topic] = studio.topic_fans.get(game.topic, 0) + gained
        game.hype *= 0.965 ** (1 / 7)
        community = community_factor(game)
        strategy_retention = {"Complete package": 0.0, "Free update roadmap": 0.025, "DLC roadmap": 0.015, "Live service": 0.06}.get(game.release_strategy, 0)
        format_retention = 0.03 if game.game_format != "Offline solo" else 0
        model_retention = float(model["retention_modifier"])
        retention = min(0.93, max(0.18, 0.50 + game.score * 0.0038 + strategy_retention + format_retention + model_retention - min(0.12, game.hype_backlash * 0.0015) - max(0.0, 0.8 - community) * 0.35 - issue_pressure * 0.02))
        game.active_players = game.active_players * retention ** (1 / 7) + units * (0.82 if sale.price <= 0 else 0.62)
        game.monthly_players = max(0, round(game.active_players * 2.6))
        game.peak_monthly_players = max(game.peak_monthly_players, game.monthly_players)
        if game.game_format != "Offline solo":
            critical_mass = 12_000 if game.game_format == "MMO" else 6_000 if game.game_format in ("Competitive online", "Persistent world") else 800
            game.network_health = max(5.0, min(100.0, game.monthly_players / critical_mass * 100))
        clamp_player_counts(game)
        franchise = franchise_by_id(studio, game.franchise_id)
        if franchise:
            previous_rank = franchise.rank
            franchise.total_units += round(units)
            franchise.total_revenue += net
            franchise.awareness = min(6_000, franchise.awareness + units / 60)
            if franchise.rank > previous_rank:
                state.log(f"The {franchise.name} IP reached {franchise.rank_name} rank after {franchise.total_units:,} lifetime units.")
        if not week_end:
            continue
        week_units = sale.week_units
        stale_weeks = 0
        strategy_tail = 0.0
        if game:
            strategy = release_strategy_by_name(game.release_strategy)
            expect_weeks = strategy.get("expect_weeks", 0)
            if expect_weeks:
                stale_weeks = max(0, state.clock.week - game.last_update_week - expect_weeks)
            strategy_tail = strategy.get("tail", 0.0)
            active_update = studio.active_update
            bugfix_in_flight = bool(active_update and active_update.game_id == game.game_id and active_update.focus == "Bug fixes")
            just_patched = game.updates_released > 0 and game.last_update_week == state.clock.week
            undiscovered = 0 if just_patched or bugfix_in_flight else max(0, game.actual_bugs - game.known_bugs)
            if undiscovered > 0:
                discovery_rate = min(0.35, 0.015 + week_units / 10_000 + game.monthly_players / 100_000)
                if game.release_week and 0 <= state.clock.week - game.release_week <= LAUNCH_DISCOVERY_WEEKS:
                    discovery_rate = min(0.5, discovery_rate + 0.12)
                game.known_bugs = min(game.actual_bugs * 0.98, game.known_bugs + undiscovered * discovery_rate)
                newly_reported = game.known_bug_count - game.reported_bug_count
                if newly_reported > 0:
                    game.reported_bug_count = game.known_bug_count
                    game.hype = max(0, game.hype - newly_reported * 0.35)
                    game.issues.append({"kind": "bugs", "severity": min(10.0, newly_reported / 2), "status": "open", "opened_week": state.clock.week})
                    state.log(f"Players reported {newly_reported} newly discovered bug(s) in {game.title} and complained online.")
            franchise = franchise_by_id(studio, game.franchise_id)
            if franchise:
                franchise.reputation += (game.score - franchise.reputation) * 0.05
            update_community_segments(state, game, franchise, stale_weeks)
            if stale_weeks > 0:
                game.hype *= max(0.85, 1 - min(0.12, stale_weeks * 0.01))
                if game.release_strategy == "Live service":
                    follower_rate = max(0.0001, (sale.score / 100) ** 2 * 0.0025)
                    weekly_gains = round(week_units * follower_rate)
                    studio.followers = max(0, studio.followers - max(10 + weekly_gains, round(studio.followers * 0.02)))
                    game.trust = max(0.0, game.trust - min(4.0, stale_weeks * 0.25))
                if stale_weeks in (1, 5, 9):
                    state.log(f"Players are losing patience with {game.title}: the {game.release_strategy.lower()} promise needs new content.")
            game.patch_fatigue *= 0.92
            game.press_rating += (game.score - game.press_rating) * 0.03
            game.sales_history.append(round(week_units))
            game.peak_weekly_sales = max(game.peak_weekly_sales, round(week_units))
            del game.sales_history[:-260]
            new_reviews = max(0, round(week_units * 0.025 + game.monthly_players * 0.0005))
            if new_reviews:
                monetization_drag = float(model["monetization_friction"]) * 22
                issue_drag = issue_pressure * 2.5
                community_view = segment_rating_anchor(game)
                base = game.score if community_view is None else 0.45 * game.score + 0.55 * community_view
                review_signal = max(5.0, min(90.0, base - monetization_drag - issue_drag - game.known_bug_count * 0.6 + (game.trust - 50) * 0.12 + (game.sentiment - 50) * 0.06 + rng.uniform(-4, 4)))
                previous_reviews = game.review_count
                rating_before_week = game.user_rating
                game.review_count += new_reviews
                game.user_rating = (game.user_rating * previous_reviews + review_signal * new_reviews) / max(1, game.review_count)
                game.user_trend = game.user_rating - rating_before_week
                game.positive_reviews += round(new_reviews * max(0.0, min(1.0, (review_signal - 40) / 55)))
                game.negative_reviews = max(0, game.review_count - game.positive_reviews)
            game.sentiment += (game.user_rating - game.sentiment) * 0.16
            positive_advocacy = max(0.0, (game.sentiment - 62) / 100) * game.active_players
            negative_advocacy = max(0.0, (48 - game.sentiment) / 100) * game.active_players
            for cohort in COHORTS:
                current = sale.awareness_by_cohort.get(cohort.key, 0.0)
                word_of_mouth = max(-0.02, min(0.015, (positive_advocacy - negative_advocacy) * cohort.social_susceptibility / max(1, cohort.population)))
                sale.awareness_by_cohort[cohort.key] = max(0.0001, min(0.45, current * 0.985 + word_of_mouth))

        payer_conversion = float(model["payer_conversion"])
        if float(model["monthly_arppu"]) > 0 and game.monthly_players > 0:
            game.payers = min(game.monthly_players, round(game.monthly_players * payer_conversion))
            recurring_gross = game.payers * float(model["monthly_arppu"]) / 4.33
            recurring_receipts = recurring_gross * (1 - sale.platform_cut)
            recurring_publisher = recurring_receipts * (sale.publisher_post_recoup_share if sale.publisher else 0.0)
            add_revenue(studio, recurring_receipts, "Recurring game revenue")
            if recurring_publisher:
                add_expense(studio, recurring_publisher, "Publisher royalties")
            recurring_net = recurring_receipts - recurring_publisher
            game.weekly_recurring_revenue = recurring_net
            game.recurring_revenue += recurring_net
            game.net_revenue += recurring_net
            sale.net_revenue += recurring_net
        elif game.monetization == "platform_subscription_deal":
            recurring_net = game.monthly_players * 0.12
            add_revenue(studio, recurring_net, "Platform engagement deal")
            game.weekly_recurring_revenue = recurring_net
            game.recurring_revenue += recurring_net
            game.net_revenue += recurring_net
        elif game.monetization == "donationware":
            recurring_net = game.monthly_players * 0.05
            add_revenue(studio, recurring_net, "Donations")
            game.weekly_recurring_revenue = recurring_net
            game.recurring_revenue += recurring_net
            game.net_revenue += recurring_net
        else:
            game.weekly_recurring_revenue = 0.0

        # Online games pay for their infrastructure every week, players or not.
        if game.game_format != "Offline solo":
            if game.support_level == "Sunset":
                # Servers are off: the community disperses and trust craters.
                if game.active_players > 0.5:
                    game.active_players *= 0.55
                    game.network_health = max(0.0, game.network_health * 0.5)
                    game.trust = max(0.0, game.trust - 1.5)
                    clamp_player_counts(game)
                    if state.clock.week % 4 == 0:
                        state.log(f"{game.title}'s servers are dark; remaining players are migrating away.")
            else:
                rent = SERVER_RENT_PER_WEEK.get(game.game_format, 0.0)
                if rent:
                    rent *= 1 + min(4.0, game.monthly_players / 50_000)
                    add_expense(studio, rent, "Server rent")
                    game.post_launch_cost += rent

        result = player_demand_result(market_results, game.game_id)
        if result:
            sale.weekly_units = max(0, result.units)
            sale.weekly_result_by_cohort = dict(result.units_by_cohort)
            sale.interested_by_cohort = dict(result.interested_by_cohort)
            sale.wishlists_by_cohort = dict(result.wishlists_by_cohort)
            sale.unmet_potential = result.unmet_potential
            sale.demand_drivers = list(result.explanation_drivers)
        else:
            sale.weekly_units = 0
        sale.age_weeks += 1
        age = state.clock.week - game.release_week
        if game.support_level == "Sunset":
            game.lifecycle_state = sale.lifecycle_state = "sunset"
            sale.weekly_units = round(sale.weekly_units * 0.20)
        elif age <= 2:
            game.lifecycle_state = sale.lifecycle_state = "launch"
        elif game.viral_coefficient and age <= 12:
            game.lifecycle_state = sale.lifecycle_state = "growth"
        elif age <= 52:
            game.lifecycle_state = sale.lifecycle_state = "active"
        elif age <= 156:
            game.lifecycle_state = sale.lifecycle_state = "mature"
        else:
            game.lifecycle_state = sale.lifecycle_state = "legacy"
        game.aware_players = round(sum(sale.awareness_by_cohort.get(cohort.key, 0.0) * cohort.population for cohort in COHORTS))
        game.interested_players = sum(sale.interested_by_cohort.values())
        game.wishlists = sum(sale.wishlists_by_cohort.values())
        sale.weeks_left = -1


def close_month(state: GameState, previous_month: str) -> None:
    studio = state.studio
    revenue = round(studio.period_revenue)
    expenses = round(studio.period_expenses)
    categories = {category: round(amount) for category, amount in studio.period_expense_categories.items()}
    revenue_categories = {category: round(amount) for category, amount in studio.period_revenue_categories.items()}
    pre_tax_net = revenue - expenses
    if pre_tax_net < 0:
        studio.tax_loss_carryforward += -pre_tax_net
    elif pre_tax_net > 0:
        taxable = max(0.0, pre_tax_net - studio.tax_loss_carryforward)
        studio.tax_loss_carryforward = max(0.0, studio.tax_loss_carryforward - pre_tax_net)
        studio.tax_reserve += taxable * 0.18
        studio.tax_payable = studio.tax_reserve
    previous_month_number = int(previous_month[-2:])
    if previous_month_number in (3, 6, 9, 12) and studio.tax_reserve >= 1:
        payment = round(studio.tax_reserve)
        studio.cash -= payment
        studio.lifetime_expenses += payment
        expenses += payment
        categories["Taxes"] = categories.get("Taxes", 0) + payment
        studio.tax_reserve = 0
        studio.tax_payable = 0
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
    year, month_number = (int(part) for part in month.split("-"))
    for employee in list(studio.team):
        if has_research(studio, "health"):
            employee.fatigue = max(0, employee.fatigue - 2)
        morale_change = 5 if has_research(studio, "coworking") else 0
        if employee.fatigue > 65:
            morale_change -= 8
        elif employee.fatigue < 25:
            morale_change += 2
        employee.morale = max(0, min(100, employee.morale + morale_change))
        if not employee.founder and month_number == 1 and employee.last_review_year < year:
            expected_raise = max(0.02, min(0.09, (studio.wage_index - 1.0) * 0.15 + employee.career_level * 0.008))
            raise_amount = round(employee.annual_salary * expected_raise / 500) * 500
            if studio.cash >= monthly_fixed_cost(studio) * 2:
                employee.annual_salary += raise_amount
                employee.salary_satisfaction = min(100.0, employee.salary_satisfaction + 8)
                employee.morale = min(100.0, employee.morale + 3)
                state.log(f"Annual review: {employee.name} received a ${raise_amount:,} market adjustment.")
            else:
                employee.salary_satisfaction = max(0.0, employee.salary_satisfaction - 15)
                employee.morale = max(0.0, employee.morale - 7)
                state.log(f"Annual review: cash pressure prevented {employee.name}'s expected raise; retention risk increased.")
            employee.last_review_year = year
        if not employee.founder and employee.career_level >= 3 and employee.salary_satisfaction < 45:
            poach_rng = random.Random(studio.seed + state.clock.week * 41 + employee.employee_id)
            if poach_rng.random() < 0.08:
                studio.team.remove(employee)
                if studio.current_project:
                    studio.current_project.technical_debt += 4 + employee.institutional_knowledge * 0.1
                state.log(f"A competitor poached {employee.name} after salary and career concerns. Their project knowledge left with them.")
                continue
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


def process_loans_week(state: GameState) -> None:
    studio = state.studio
    for loan in list(studio.loans):
        weekly_rate = loan.annual_rate / 52
        interest = loan.balance * weekly_rate
        payment = min(loan.weekly_payment, loan.balance + interest)
        principal_paid = max(0.0, payment - interest)
        loan.balance = max(0.0, loan.balance - principal_paid)
        loan.weeks_left -= 1
        add_expense(studio, interest, "Loan interest")
        principal_payment(studio, principal_paid, "Loan principal", date=state.clock.current_date, counterparty="Bank", memo=loan.name)
        if loan.balance <= 1 or loan.weeks_left <= 0:
            studio.loans.remove(loan)
            state.log(f"Repaid the {loan.name.lower()}; the bank has released its claim on future cash flow.")


def process_contract(state: GameState, week_end: bool = True, workday: bool = True) -> None:
    studio = state.studio
    start_next_contract(state)
    contract = studio.contract
    if contract is None:
        return
    if week_end:
        contract.weeks_left -= 1
        for queued in list(studio.contract_queue):
            queued.weeks_left -= 1
            if queued.weeks_left <= 0:
                studio.contract_queue.remove(queued)
                penalty = queued.late_penalty
                if penalty:
                    add_expense(studio, penalty, "Contract penalties")
                studio.contractor_reputation = max(0, studio.contractor_reputation - max(2, queued.difficulty * 2))
                studio.contracts_failed += 1
                state.log(f"{queued.client} withdrew {queued.title} after its deadline expired in your queue; penalty ${penalty:,}.")
    if contract.required_work <= 0:
        if week_end and contract.weeks_left <= 0:
            add_revenue(studio, max(0, contract.payout - contract.deposit), "Contracts")
            studio.contractor_reputation = min(100, studio.contractor_reputation + 1)
            studio.contracts_completed += 1
            state.log(f"Delivered the legacy {contract.title}; client paid the remaining ${max(0, contract.payout - contract.deposit):,}.")
            studio.contract = None
            start_next_contract(state)
        return
    if not workday:
        if contract.weeks_left <= 0:
            reputation_loss = max(2, contract.difficulty * 3)
            if contract.late_penalty:
                add_expense(studio, contract.late_penalty, "Contract penalties")
            studio.contractor_reputation = max(0, studio.contractor_reputation - reputation_loss)
            studio.contracts_failed += 1
            state.log(f"Missed {contract.client}'s {contract.title} deadline; no payment and contractor reputation -{reputation_loss}.")
            studio.contract = None
            start_next_contract(state)
        return

    output = contract_weekly_output(studio, contract.focus) / 5
    contract.work_done = min(contract.required_work, contract.work_done + output)
    payroll = sum(employee.annual_salary / 52 for employee in studio.team) + sum(employee.annual_salary / 52 for employee in studio.team if not employee.founder) * 0.13
    contract.labor_cost += payroll / 5 * activity_allocations(studio)["contract"]
    if contract.work_done >= contract.required_work:
        delivery_quality = coordinated_team_output(studio, contract.focus) / max(1, len(studio.team))
        if delivery_quality < contract.quality_target and contract.rework_rounds < 1:
            contract.rework_rounds += 1
            contract.required_work *= 1.18
            state.log(f"{contract.client} rejected the first delivery of {contract.title}; quality {delivery_quality:.0f} missed target {contract.quality_target}. Rework is required under the same deadline.")
            return
        add_revenue(studio, max(0, contract.payout - contract.deposit), "Contracts")
        reputation_gain = contract.difficulty * 0.5 + min(0.75, max(0, contract.weeks_left) * 0.05)
        if contract.payout <= 0:
            # Portfolio work pays in contacts: double reputation, plus a
            # little client relationship for delivering anyway.
            reputation_gain = reputation_gain * 2 + 1.0
            studio.client_relationships[contract.client] = min(100.0, studio.client_relationships.get(contract.client, 0.0) + 2)
        studio.contractor_reputation = min(100, studio.contractor_reputation + reputation_gain)
        studio.contracts_completed += 1
        studio.client_relationships[contract.client] = min(100.0, studio.client_relationships.get(contract.client, 0.0) + 3 + contract.difficulty)
        if contract.payout:
            state.log(f"Delivered {contract.client}'s {contract.title}; paid ${contract.payout:,} against ${contract.labor_cost:,.0f} labor, contractor reputation +{reputation_gain:.1f}.")
        else:
            state.log(f"Delivered {contract.client}'s {contract.title} for free; they will vouch for you (reputation +{reputation_gain:.1f}).")
        studio.contract = None
        start_next_contract(state)
    elif contract.weeks_left <= 0:
        reputation_loss = max(2, contract.difficulty * 3)
        if contract.late_penalty:
            add_expense(studio, contract.late_penalty, "Contract penalties")
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
    weekly_market = allocate_weekly_market(state) if week_end else {}
    process_sales(state, week_end, day_number, weekly_market)
    process_contract(state, week_end, workday)
    develop_project(state, day_number, week_end, workday)
    process_research(state, workday)
    process_employee_wellbeing(state, week_end, workday)
    if week_end:
        process_loans_week(state)
        process_community_week(state)
        process_franchises_week(state)
        process_media_ventures_week(state)
        process_macro_week(state)
        process_market_week(state, weekly_market)
    if studio.cash < 0:
        studio.insolvent_days += 1
        studio.insolvent_weeks = studio.insolvent_days // 7
        if studio.insolvent_days == 1:
            state.log("The bank balance is negative. You have eight weeks to recover before closure.")
        if studio.insolvent_days % 7 == 0:
            weeks_left = max(0, 8 - studio.insolvent_weeks)
            overdraft_fee = max(150.0, abs(studio.cash) * 0.0025)
            add_expense(studio, overdraft_fee, "Overdraft fees")
            for employee in studio.team:
                employee.morale = max(0.0, employee.morale - 3)
                employee.salary_satisfaction = max(0.0, employee.salary_satisfaction - 5)
            state.log(f"INSOLVENCY: {weeks_left} weeks remain. Overdraft fee ${overdraft_fee:,.0f}; employees fear missed payroll.")
            emit_event(state, "insolvency_warning", f"Studio has {weeks_left} weeks to restore solvency.", "critical", "studio", studio.name, {"weeks_left": weeks_left})
        if studio.insolvent_days >= 56:
            studio.closed = True
            state.time_speed_index = 0
            state.log("The studio is insolvent and has closed. Load an earlier save or begin again.")
            emit_event(state, "studio_closed", f"{studio.name} closed in insolvency.", "critical", "studio", studio.name)
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
        scope_scale = {"Micro": 1.3, "Compact": 1.15, "Small": 1.0, "Mid-size": 0.75, "Ambitious": 0.6, "Large": 0.45, "Blockbuster": 0.35}.get(project.scope, 1.0)
        if project.release_strategy == "Live service":
            scope_scale *= 0.5
        franchise.fatigue = min(120, franchise.fatigue + max(0, 14 - franchise.entries * 2) * scope_scale)
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


def franchise_fatigue_target(state: GameState, franchise: Franchise) -> float:
    games = [game for game in state.studio.catalog if game.franchise_id == franchise.franchise_id]
    if not games:
        return 0.0
    oldest_week = min(game.release_week for game in games if game.release_week)
    years_active = max(0.0, (state.clock.week - oldest_week) / 52)
    dlcs = sum(game.dlcs_released for game in games)
    updates = sum(game.updates_released for game in games)
    live_years = sum(
        max(0.0, (state.clock.week - game.release_week) / 52)
        for game in games
        if game.release_strategy in ("DLC roadmap", "Live service")
    )
    last_activity_week = max(max(game.release_week, game.last_update_week) for game in games)
    quiet_years = max(0.0, (state.clock.week - last_activity_week) / 52)
    unit_pressure = max(0.0, franchise.total_units / 1_000_000 - 0.5) * 8.5
    longevity_pressure = max(0.0, years_active - 1) * 4.0 + live_years * 2.0
    content_pressure = dlcs * 6.0 + max(0, updates - 5) * 1.25
    sequel_pressure = max(0, franchise.entries - 1) * 7.0
    # Audiences eventually miss an IP after it stops asking for attention. A
    # quiet break resets sequel appetite even when the old game sold millions.
    cooldown_factor = max(0.08, 1 - quiet_years * 0.30)
    return min(120.0, (unit_pressure + longevity_pressure + content_pressure + sequel_pressure) * cooldown_factor)


def process_franchises_week(state: GameState) -> None:
    state.studio.reputation *= 0.997
    for franchise in state.studio.franchises:
        franchise.awareness *= 0.997
        games = [game for game in state.studio.catalog if game.franchise_id == franchise.franchise_id]
        if not games:
            continue
        target = franchise_fatigue_target(state, franchise)
        quiet_years = max(0.0, (state.clock.week - max(max(game.release_week, game.last_update_week) for game in games)) / 52)
        rate = 0.035 if target > franchise.fatigue else 0.025 if quiet_years >= 1.5 else 0.008
        franchise.fatigue = max(0.0, min(120.0, franchise.fatigue + (target - franchise.fatigue) * rate))


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
        release_payout = round(venture["cost"] * min(2.2, 0.35 + franchise.rank * 0.18 + franchise.reputation / 180), 2)
    elif venture["key"] == "series":
        release_payout = round(venture["cost"] * min(2.6, 0.40 + franchise.rank * 0.22 + franchise.reputation / 165), 2)
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
            payout = round(venture.release_payout * max(0.05, min(1.45, quality_roll)))
            add_revenue(studio, payout, "Merch & Media")
            venture.revenue += payout
            if quality_roll < 0.45:
                franchise.reputation = max(0.0, franchise.reputation - 8)
                franchise.awareness *= 0.92
                lost = min(studio.followers, round(studio.followers * 0.03))
                studio.followers -= lost
            else:
                franchise.awareness = min(6_000, franchise.awareness + 120 + franchise.value * 0.08)
                studio.followers += round(100 + franchise.value * 0.6)
            label = "film" if venture.kind == "film" else "series"
            verdict = "a hit" if quality_roll >= 1.0 else "mixed" if quality_roll >= 0.6 else "a flop"
            state.log(f"{franchise.name}: the {label} adaptation released to {verdict} reception: ${payout:,} in licensing and royalties.")


BUG_FIX_WORK_PER_DEFECT = 1.6
QA_CLEAR_FRACTION = 0.75
LAUNCH_DISCOVERY_WEEKS = 4


def competitor_channel(genre: str, rng: random.Random) -> str:
    mobile = {"Puzzle Game", "Skill Game", "Simulation", "Visual Novel", "Economic Simulation", "Cozy Game", "Survivors-like", "Social Deduction"}
    console = {"Action", "Platformer", "Racing", "Sports Game", "Fighting Game", "Third-Person Shooter", "First-Person Shooter", "Battle Royale", "Soulslike", "Metroidvania"}
    if genre in mobile:
        choices = ("Google Play", "App Store", "Steam", "Epic Games Store")
    elif genre in console:
        choices = ("PlayStation 5", "Xbox Series", "Switch 2", "Steam")
    else:
        choices = ("Steam", "Steam", "Epic Games Store", "itch.io")
    return rng.choice(choices)


def competitor_launch_units(state: GameState, competitor: Competitor, release: CompetitorGame, rng: random.Random) -> int:
    """A small studio can still break out; scale helps, but does not decide hits."""
    channel = channel_by_name(release.channel)
    tier_scale = {"platform": 2.5, "publisher": 1.5, "studio": 1.0, "indie": 0.8}.get(competitor.tier, 1.0)
    studio_scale = (0.55 + competitor.size / 5) * (1 + competitor.fanbase / 150_000) * tier_scale
    quality_scale = 0.35 + release.quality / 125 + competitor.tools_level * 0.025
    visibility_scale = 0.55 + channel["visibility"] / 10
    breakout_chance = min(0.08, (0.01 + max(0, release.quality - 65) / 500 + release.hype / 4_000) / (1 + competitor.size / 5))
    # A viral game can briefly stand beside a giant, but it is exceptional.
    breakout = rng.uniform(4.0, 12.0) if rng.random() < breakout_chance else 1.0
    open_share = market_share_multiplier(state, release.genre, release.channel)
    launch = release.hype * 45 * studio_scale * quality_scale * visibility_scale * market_growth_factor(state.clock.week) * breakout * open_share
    return max(40, min(competitor_weekly_sales_cap(state, competitor), round(launch)))


def competitor_weekly_sales_cap(state: GameState, competitor: Competitor) -> int:
    caps = {"platform": 650_000, "publisher": 450_000, "studio": 250_000, "indie": 120_000}
    return round(caps.get(competitor.tier, 200_000) * market_growth_factor(state.clock.week))


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
            tools_level={"platform": 4, "publisher": 3, "studio": 2, "indie": 1}[archetype["tier"]],
            cash={"platform": 240_000_000, "publisher": 90_000_000, "studio": 18_000_000, "indie": 1_400_000}[archetype["tier"]],
            monthly_burn={"platform": 5_000_000, "publisher": 2_000_000, "studio": 420_000, "indie": 55_000}[archetype["tier"]] * max(0.5, archetype["size"] / 3),
            risk_tolerance=rng.uniform(0.25, 0.85),
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
                    total_units=round(competitor.fanbase * rng.uniform(1.5, 6.0)),
                )
            )
        competitor.cooldown = rng.randint(1, 6)
        for seed_index, weeks_ago in enumerate((rng.randint(2, 6), rng.randint(8, 14))):
            franchise = competitor.franchises[0] if competitor.franchises and rng.random() < 0.6 else None
            genre = franchise.genre if franchise else rng.choice(competitor.genres)
            quality = max(25, min(96, round(competitor.reputation + rng.uniform(-12, 10))))
            hype = min(200, (25 + competitor.size * 10 + (franchise.value / 14 if franchise else 0)) * rng.uniform(0.7, 1.3))
            title = f"{franchise.name} {roman_number(max(1, franchise.entries - seed_index))}" if franchise else generate_game_title(genre, rng.choice(TOPICS), studio.seed + competitor.competitor_id * 7 + weeks_ago)
            channel = competitor_channel(genre, rng)
            release = CompetitorGame(title, franchise.name if franchise else "", genre, quality, round(hype, 1), 0, competitor.size, released_week=1, channel=channel)
            launch = competitor_launch_units(state, competitor, release, rng)
            weekly = max(40.0, launch * min(0.90, 0.50 + quality * 0.004) ** weeks_ago)
            competitor.recent_releases.append(
                CompetitorGame(title, franchise.name if franchise else "", genre, quality, round(hype, 1), 0, competitor.size, released_week=1, weekly_units=weekly, units_sold=round(launch * weeks_ago * 0.6), channel=channel)
            )
        studio.competitors.append(competitor)
    # The long tail matters: most launches do not fight a handful of named giants,
    # but a crowded field of capable small studios releasing into the same windows.
    for name in EXPANDED_COMPETITOR_NAMES:
        genres = rng.sample(list(GENRES), 3)
        size = round(rng.uniform(0.6, 3.8), 1)
        competitor = Competitor(
            len(studio.competitors) + 1,
            name,
            "indie" if size < 1.8 else "studio",
            size,
            round(rng.uniform(18_000, 420_000) * size),
            round(rng.uniform(52, 84)),
            genres=genres,
            tools_level=1 if size < 1.8 else 2,
            cash=rng.uniform(350_000, 4_000_000) * size,
            monthly_burn=rng.uniform(28_000, 90_000) * size,
            risk_tolerance=rng.uniform(0.20, 0.90),
        )
        competitor.cooldown = rng.randint(1, 16)
        studio.competitors.append(competitor)


def process_market_week(state: GameState, market_results: dict[str, DemandResult] | None = None) -> None:
    studio = state.studio
    rng = random.Random(studio.seed * 7 + state.clock.week * 31)
    for competitor in studio.competitors:
        if competitor.closed:
            continue
        competitor.cash -= competitor.monthly_burn / 4.33
        competitor.cash -= competitor.debt * max(0.0, studio.interest_rate) / 52
        if competitor.cash < -competitor.monthly_burn * 6:
            competitor.closed = True
            competitor.in_development.clear()
            state.log(f"{competitor.name} closed after its finances collapsed. Its audience and IPs are now in play.")
            emit_event(state, "competitor_closed", f"{competitor.name} closed.", "critical", "competitor", competitor.competitor_id)
            continue
        if competitor.cash < 0 and competitor.size > 0.7:
            competitor.size = max(0.5, competitor.size * 0.92)
            competitor.monthly_burn *= 0.88
            competitor.fanbase = round(competitor.fanbase * 0.97)
            competitor.failures += 1
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
            production_capacity = 0.5 + competitor.size / 6 + competitor.tools_level * 0.15
            dev_weeks = max(4, round(rng.uniform(10, 30) / production_capacity))
            quality = max(25, min(96, round(competitor.reputation + competitor.tools_level * 2 + rng.uniform(-12, 10))))
            hype = min(200, (25 + competitor.size * 10 + competitor.tools_level * 7 + (franchise.value / 14 if franchise else 0)) * rng.uniform(0.7, 1.3))
            title = f"{franchise.name} {roman_number(franchise.entries + 1)}" if franchise else generate_game_title(genre, rng.choice(TOPICS), studio.seed + state.clock.week + competitor.competitor_id)
            competitor.in_development.append(CompetitorGame(title, franchise.name if franchise else "", genre, quality, round(hype, 1), dev_weeks, competitor.size, channel=competitor_channel(genre, rng)))
            competitor.cooldown = rng.randint(10, max(14, round(52 - competitor.size * 4 - competitor.tools_level)))
        for game in finished:
            release = game
            franchise = next((item for item in competitor.franchises if item.name == release.franchise_name), None)
            launch_units = competitor_launch_units(state, competitor, release, rng)
            release.weekly_units = float(launch_units)
            release.units_sold += max(40, launch_units)
            launch_revenue = launch_units * 39.99 * 0.65
            competitor.cash += launch_revenue
            competitor.releases_completed += 1
            competitor.growth_points += launch_units / 20_000 + release.quality / 25
            competitor.fanbase += round(launch_units * (0.025 + release.quality / 4_000))
            competitor.reputation = max(20.0, min(98.0, competitor.reputation + (release.quality - competitor.reputation) * 0.08))
            growth_step = 300 + competitor.tools_level * 100
            while competitor.growth_points >= growth_step and competitor.cash > competitor.monthly_burn * 8:
                competitor.growth_points -= growth_step
                competitor.tools_level = min(8, competitor.tools_level + 1)
                competitor.size = min(14.0, round(competitor.size + 0.25, 2))
                growth_step = 300 + competitor.tools_level * 100
                state.log(f"{competitor.name} expanded its production capability to tools level {competitor.tools_level}.")
            if franchise:
                franchise.entries += 1
                franchise.awareness = min(6_000, franchise.awareness + 20 + release.hype / 4)
                franchise.reputation += (release.quality - franchise.reputation) * 0.25
                franchise.fatigue = min(120, franchise.fatigue + 6)
            notable = competitor.size >= 3 or release.quality >= 80
            if notable:
                state.log(f"{competitor.name} released {release.title} ({release.genre}, {release.quality}/100). The market took notice.")
        for game in competitor.recent_releases:
            if game.released_week and game.released_week < state.clock.week and game.weekly_units > 0:
                tail = min(0.90, 0.50 + game.quality * 0.004)
                game.weekly_units = min(competitor_weekly_sales_cap(state, competitor), game.weekly_units * tail)
                game.units_sold += round(game.weekly_units)
                competitor.cash += game.weekly_units * 39.99 * 0.65

    # Rival demand comes from the same single weekly allocation the studio's
    # sales used (see allocate_weekly_market), so one shopper pool serves all
    # products. Releases launched after the allocation keep their launch
    # estimate until next week.
    if market_results is None:
        market_results = allocate_weekly_market(state)
    for competitor in studio.competitors:
        if competitor.closed:
            continue
        for index, game in enumerate(competitor.recent_releases):
            result = market_results.get(f"rival:{competitor.competitor_id}:{index}")
            if result:
                game.weekly_units = float(result.units)
    positions = chart_positions(state)
    update_genre_heat(state)
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
            "selected_monetization": state.selected_monetization,
            "selected_price": state.selected_price,
            "selected_announcement": state.selected_announcement,
            "selected_release_policy": state.selected_release_policy,
            "selected_community_action": state.selected_community_action,
            "marketing_tab": state.marketing_tab,
            "games_tab": state.games_tab,
            "focus": state.focus,
            "time_speed_index": state.time_speed_index,
            "resume_speed_index": state.resume_speed_index,
            "draft_title": state.draft_title,
            "title_roll": state.title_roll,
            "sequel_game_id": state.sequel_game_id,
            "spinoff_franchise_id": state.spinoff_franchise_id,
            "new_game_kind": state.new_game_kind,
            "selected_venture": state.selected_venture,
            "selected_research_branch": state.selected_research_branch,
            "finance_tab": state.finance_tab,
            "selected_finance_offer": state.selected_finance_offer,
        },
        "logs": state.logs,
        "events": state.events,
        "event_history": state.event_history,
        "next_event_id": state.next_event_id,
        "last_read_event_id": state.last_read_event_id,
    }


def studio_from_data(data: dict) -> Studio:
    values = dict(data)
    values["team"] = [employee_from_data(item) for item in values.get("team", [])]
    values["applicants"] = [employee_from_data(item) for item in values.get("applicants", [])]
    if values.get("current_project"):
        values["current_project"] = Project(**values["current_project"])
    values["active_sales"] = [ActiveSale(**item) for item in values.get("active_sales", [])]
    for sale in values["active_sales"]:
        sale.units_sold = round(sale.units_sold)
    catalog = []
    for item in values.get("catalog", []):
        item = dict(item)
        item["segments"] = [Segment(**segment) for segment in item.get("segments", [])]
        game = ReleasedGame(**item)
        game.units_sold = round(game.units_sold)
        if not game.last_update_week:
            game.last_update_week = game.release_week
        clamp_player_counts(game)
        catalog.append(game)
    values["catalog"] = catalog
    if values.get("contract"):
        values["contract"] = Contract(**values["contract"])
    values["contract_offers"] = [Contract(**item) for item in values.get("contract_offers", [])]
    values["contract_queue"] = [Contract(**item) for item in values.get("contract_queue", [])]
    if values.get("active_update"):
        values["active_update"] = UpdateJob(**values["active_update"])
    values["update_queue"] = [UpdateJob(**item) for item in values.get("update_queue", [])]
    values["active_promotions"] = [Promotion(**item) for item in values.get("active_promotions", [])]
    values["franchises"] = [Franchise(**item) for item in values.get("franchises", [])]
    for franchise in values["franchises"]:
        franchise.total_units = round(franchise.total_units)
    values["media_ventures"] = [MediaVenture(**item) for item in values.get("media_ventures", [])]
    values["loans"] = [Loan(**item) for item in values.get("loans", [])]
    competitors = []
    for item in values.get("competitors", []):
        entry = dict(item)
        entry["franchises"] = [Franchise(**franchise) for franchise in entry.get("franchises", [])]
        entry["in_development"] = [CompetitorGame(**game) for game in entry.get("in_development", [])]
        entry["recent_releases"] = [CompetitorGame(**game) for game in entry.get("recent_releases", [])]
        competitors.append(Competitor(**entry))
    values["competitors"] = competitors
    if values.get("active_research"):
        values["active_research"] = ResearchJob(**values["active_research"])
    values["research_queue"] = [ResearchJob(**item) for item in values.get("research_queue", [])]
    values["completed_research"] = list(dict.fromkeys(values["completed_research"]))
    ledger = [LedgerMonth(**item) for item in values.get("ledger", [])]
    values["ledger"] = ledger
    return Studio(**values)


def state_from_data(data: dict, save_path: str) -> GameState:
    if data.get("version") != SAVE_VERSION:
        raise ValueError(f"Legacy save version {data.get('version')!r} cannot be loaded by the version {SAVE_VERSION} economy; start a new campaign")
    clock_data = data["clock"]
    clock = GameClock(date.fromisoformat(clock_data["current_date"]), clock_data["week"], clock_data.get("elapsed_seconds", 0.0), clock_data.get("day", clock_data["week"] * 7 - 6))
    ui = data.get("ui", {})
    studio = studio_from_data(data["studio"])
    state = GameState(
        clock=clock,
        studio=studio,
        selected_genre=ui.get("selected_genre", 0),
        selected_topic=ui.get("selected_topic", 0),
        selected_channel=ui.get("selected_channel", 0),
        selected_scope=ui.get("selected_scope", 0),
        selected_marketing=ui.get("selected_marketing", 0),
        selected_secondary_genre=ui.get("selected_secondary_genre", ui.get("selected_genre", 0)),
        selected_secondary_topic=ui.get("selected_secondary_topic", ui.get("selected_topic", 0)),
        selected_audience=ui.get("selected_audience", 0),
        selected_format=ui.get("selected_format", 0),
        selected_creative_primary=ui.get("selected_creative_primary", 0),
        selected_creative_secondary=ui.get("selected_creative_secondary", 3),
        selected_release_strategy=ui.get("selected_release_strategy", 0),
        selected_monetization=ui.get("selected_monetization", 0),
        selected_price=ui.get("selected_price", -1),
        selected_announcement=ui.get("selected_announcement", 1),
        selected_release_policy=ui.get("selected_release_policy", 0),
        selected_community_action=ui.get("selected_community_action", 0),
        marketing_tab=ui.get("marketing_tab", 0),
        games_tab=ui.get("games_tab", 0),
        focus=ui.get("focus", [30, 25, 15, 30]),
        time_speed_index=min(ui.get("time_speed_index", 1), len(TIME_SPEEDS) - 1),
        resume_speed_index=max(1, min(ui.get("resume_speed_index", 1), len(TIME_SPEEDS) - 1)),
        draft_title=ui.get("draft_title", ""),
        title_roll=ui.get("title_roll", 0),
        sequel_game_id=ui.get("sequel_game_id"),
        spinoff_franchise_id=ui.get("spinoff_franchise_id"),
        new_game_kind=ui.get("new_game_kind", ""),
        selected_venture=ui.get("selected_venture", 0),
        selected_research_branch=ui.get("selected_research_branch", 0),
        finance_tab=ui.get("finance_tab", 0),
        selected_finance_offer=ui.get("selected_finance_offer", 0),
        save_path=save_path,
        logs=data.get("logs", []),
        events=data.get("events", []),
        event_history=data.get("event_history", []),
        next_event_id=data.get("next_event_id", 1),
        last_read_event_id=data.get("last_read_event_id", 0),
    )
    return state


def save_game(state: GameState) -> None:
    path = Path(state.save_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    backup = path.with_suffix(path.suffix + ".bak")
    temporary.write_text(json.dumps(state_to_data(state), indent=2), encoding="utf-8")
    if path.exists():
        backup.write_bytes(path.read_bytes())
    temporary.replace(path)


def load_game(save_path: str) -> GameState:
    return state_from_data(json.loads(Path(save_path).read_text(encoding="utf-8")), save_path)
