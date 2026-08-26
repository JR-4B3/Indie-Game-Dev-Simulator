"""Version 10 product, launch, and community economics rules.

Money values are current US dollars. Multipliers are centered on 1.0, while
conversion, friction, decay, and risk values are fractions from 0.0 to 1.0.
"""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Final, TypeAlias


Rule: TypeAlias = dict[str, object]
RuleTable: TypeAlias = tuple[Rule, ...]

PRODUCT_RULES_VERSION: Final = 10


MONETIZATION_MODELS: Final[RuleTable] = (
    {
        "key": "premium",
        "name": "Premium",
        "default_price": 29.99,
        "work_multiplier": 1.00,
        "setup_cost": 0,
        "acquisition_multiplier": 0.92,
        "retention_modifier": 0.00,
        "payer_conversion": 1.00,
        "monthly_arppu": 0.00,
        "subscription_monthly_price": 0.00,
        "monetization_friction": 0.08,
        "recurring_cost_per_player": 0.01,
        "requires_online": False,
    },
    {
        "key": "premium_dlc",
        "name": "Premium + DLC",
        "default_price": 39.99,
        "work_multiplier": 1.14,
        "setup_cost": 125_000,
        "acquisition_multiplier": 0.96,
        "retention_modifier": 0.04,
        "payer_conversion": 1.00,
        "monthly_arppu": 1.25,
        "subscription_monthly_price": 0.00,
        "monetization_friction": 0.14,
        "recurring_cost_per_player": 0.03,
        "requires_online": False,
        "research_key": "paid_dlc",
    },
    {
        "key": "paid_early_access",
        "name": "Paid Early Access",
        "default_price": 24.99,
        "work_multiplier": 1.10,
        "setup_cost": 40_000,
        "acquisition_multiplier": 1.08,
        "retention_modifier": 0.03,
        "payer_conversion": 1.00,
        "monthly_arppu": 0.00,
        "subscription_monthly_price": 0.00,
        "monetization_friction": 0.18,
        "recurring_cost_per_player": 0.03,
        "requires_online": False,
        "research_key": "content_updates",
    },
    {
        "key": "free_to_play_cosmetics",
        "name": "Free-to-Play Cosmetics",
        "default_price": 0.00,
        "work_multiplier": 1.42,
        "setup_cost": 650_000,
        "acquisition_multiplier": 1.85,
        "retention_modifier": 0.08,
        "payer_conversion": 0.035,
        "monthly_arppu": 14.00,
        "subscription_monthly_price": 0.00,
        "monetization_friction": 0.06,
        "recurring_cost_per_player": 0.22,
        "requires_online": True,
        "research_key": "live_operations",
    },
    {
        "key": "battle_pass",
        "name": "Battle Pass",
        "default_price": 0.00,
        "work_multiplier": 1.58,
        "setup_cost": 1_200_000,
        "acquisition_multiplier": 1.65,
        "retention_modifier": 0.13,
        "payer_conversion": 0.075,
        "monthly_arppu": 10.50,
        "subscription_monthly_price": 0.00,
        "monetization_friction": 0.12,
        "recurring_cost_per_player": 0.31,
        "requires_online": True,
        "research_key": "live_operations",
    },
    {
        "key": "subscription",
        "name": "Subscription",
        "default_price": 0.00,
        "work_multiplier": 1.72,
        "setup_cost": 1_800_000,
        "acquisition_multiplier": 1.20,
        "retention_modifier": 0.16,
        "payer_conversion": 0.13,
        "monthly_arppu": 11.99,
        "subscription_monthly_price": 11.99,
        "monetization_friction": 0.20,
        "recurring_cost_per_player": 0.42,
        "requires_online": True,
        "research_key": "live_operations",
    },
    {
        "key": "box_subscription",
        "name": "Box + Subscription",
        "default_price": 39.99,
        "work_multiplier": 1.88,
        "setup_cost": 2_600_000,
        "acquisition_multiplier": 0.82,
        "retention_modifier": 0.18,
        "payer_conversion": 1.00,
        "monthly_arppu": 12.99,
        "subscription_monthly_price": 12.99,
        "monetization_friction": 0.36,
        "recurring_cost_per_player": 0.48,
        "requires_online": True,
        "research_key": "live_operations",
    },
    {
        "key": "platform_subscription_deal",
        "name": "Platform Subscription Deal",
        "default_price": 0.00,
        "work_multiplier": 1.08,
        "setup_cost": 180_000,
        "acquisition_multiplier": 1.55,
        "retention_modifier": 0.02,
        "payer_conversion": 0.00,
        "monthly_arppu": 0.00,
        "subscription_monthly_price": 0.00,
        "monetization_friction": 0.00,
        "recurring_cost_per_player": 0.04,
        "requires_online": False,
        "research_key": "targeted_marketing",
    },
)


PRICE_POINTS: Final[RuleTable] = (
    {"key": "free", "name": "Free", "price": 0.00},
    {"key": "usd_4_99", "name": "$4.99", "price": 4.99},
    {"key": "usd_7_99", "name": "$7.99", "price": 7.99},
    {"key": "usd_9_99", "name": "$9.99", "price": 9.99},
    {"key": "usd_14_99", "name": "$14.99", "price": 14.99},
    {"key": "usd_19_99", "name": "$19.99", "price": 19.99},
    {"key": "usd_24_99", "name": "$24.99", "price": 24.99},
    {"key": "usd_29_99", "name": "$29.99", "price": 29.99},
    {"key": "usd_39_99", "name": "$39.99", "price": 39.99},
    {"key": "usd_49_99", "name": "$49.99", "price": 49.99},
    {"key": "usd_59_99", "name": "$59.99", "price": 59.99},
    {"key": "usd_69_99", "name": "$69.99", "price": 69.99},
    {"key": "usd_79_99", "name": "$79.99", "price": 79.99},
)


ANNOUNCEMENT_STRATEGIES: Final[RuleTable] = (
    {
        "key": "stealth",
        "name": "Stealth",
        "awareness": 0.35,
        "trust": 0,
        "hype_decay": 0.00,
        "feedback": 0.05,
        "promise_risk": 0.00,
    },
    {
        "key": "late_reveal",
        "name": "Late Reveal",
        "awareness": 0.85,
        "trust": 1,
        "hype_decay": 0.015,
        "feedback": 0.25,
        "promise_risk": 0.06,
    },
    {
        "key": "open_development",
        "name": "Open Development",
        "awareness": 1.25,
        "trust": 5,
        "hype_decay": 0.035,
        "feedback": 1.00,
        "promise_risk": 0.22,
    },
    {
        "key": "public_roadmap",
        "name": "Public Roadmap",
        "awareness": 1.15,
        "trust": 3,
        "hype_decay": 0.025,
        "feedback": 0.70,
        "promise_risk": 0.35,
    },
)


RELEASE_POLICIES: Final[RuleTable] = (
    {
        "key": "ship_when_ready",
        "name": "Ship When Ready",
        "timing": "ready",
        "timing_flexibility": 1.00,
        "promise_risk": 0.00,
    },
    {
        "key": "manual_window",
        "name": "Manual Window",
        "timing": "window",
        "timing_flexibility": 0.55,
        "promise_risk": 0.12,
    },
    {
        "key": "announced_date",
        "name": "Announced Date",
        "timing": "date",
        "timing_flexibility": 0.05,
        "promise_risk": 0.38,
    },
)


COMMUNITY_ACTIONS: Final[RuleTable] = (
    {
        "key": "dev_diary",
        "name": "Dev Diary",
        "cash_cost": 1_500,
        "team_load": 0.08,
        "duration_weeks": 1,
        "trust": 1,
        "awareness": 2,
        "issue_effect": -0.02,
    },
    {
        "key": "open_beta",
        "name": "Open Beta",
        "cash_cost": 25_000,
        "team_load": 0.25,
        "duration_weeks": 4,
        "trust": 4,
        "awareness": 7,
        "issue_effect": -0.15,
    },
    {
        "key": "roadmap",
        "name": "Roadmap",
        "cash_cost": 4_000,
        "team_load": 0.12,
        "duration_weeks": 2,
        "trust": 3,
        "awareness": 3,
        "issue_effect": 0.00,
    },
    {
        "key": "apology",
        "name": "Apology",
        "cash_cost": 0,
        "team_load": 0.06,
        "duration_weeks": 1,
        "trust": 3,
        "awareness": 0,
        "issue_effect": -0.05,
    },
    {
        "key": "emergency_response",
        "name": "Emergency Response",
        "cash_cost": 50_000,
        "team_load": 0.55,
        "duration_weeks": 2,
        "trust": 7,
        "awareness": -2,
        "issue_effect": -0.40,
    },
    {
        "key": "community_event",
        "name": "Community Event",
        "cash_cost": 18_000,
        "team_load": 0.20,
        "duration_weeks": 2,
        "trust": 4,
        "awareness": 5,
        "issue_effect": -0.06,
    },
)


def lookup_by_key(table: RuleTable, key: str) -> Rule | None:
    """Return the table entry with an exact stable key, if present."""
    return next((entry for entry in table if entry.get("key") == key), None)


def lookup_by_name(table: RuleTable, name: str) -> Rule | None:
    """Return an entry by display name using case-insensitive matching."""
    wanted = name.casefold()
    return next(
        (
            entry
            for entry in table
            if isinstance(entry.get("name"), str)
            and str(entry["name"]).casefold() == wanted
        ),
        None,
    )


def monetization_model_by_key(key: str) -> Rule | None:
    """Look up a monetization model by stable key."""
    return lookup_by_key(MONETIZATION_MODELS, key)


def monetization_model_by_name(name: str) -> Rule | None:
    """Look up a monetization model by display name."""
    return lookup_by_name(MONETIZATION_MODELS, name)


def price_point_by_key(key: str) -> Rule | None:
    """Look up a price point by stable key."""
    return lookup_by_key(PRICE_POINTS, key)


def price_point_by_name(name: str) -> Rule | None:
    """Look up a price point by display name."""
    return lookup_by_name(PRICE_POINTS, name)


def announcement_strategy_by_key(key: str) -> Rule | None:
    """Look up an announcement strategy by stable key."""
    return lookup_by_key(ANNOUNCEMENT_STRATEGIES, key)


def announcement_strategy_by_name(name: str) -> Rule | None:
    """Look up an announcement strategy by display name."""
    return lookup_by_name(ANNOUNCEMENT_STRATEGIES, name)


def release_policy_by_key(key: str) -> Rule | None:
    """Look up a release policy by stable key."""
    return lookup_by_key(RELEASE_POLICIES, key)


def release_policy_by_name(name: str) -> Rule | None:
    """Look up a release policy by display name."""
    return lookup_by_name(RELEASE_POLICIES, name)


def community_action_by_key(key: str) -> Rule | None:
    """Look up a community action by stable key."""
    return lookup_by_key(COMMUNITY_ACTIONS, key)


def community_action_by_name(name: str) -> Rule | None:
    """Look up a community action by display name."""
    return lookup_by_name(COMMUNITY_ACTIONS, name)


def nearest_price_point(price: float) -> Rule:
    """Return the configured price point nearest to a non-negative price."""
    value = float(price)
    if not isfinite(value) or value < 0.0:
        raise ValueError("price must be finite and non-negative")
    return min(PRICE_POINTS, key=lambda point: abs(float(point["price"]) - value))


def choose_nearest_price(price: float) -> float:
    """Return the numeric configured price nearest to the requested price."""
    return float(nearest_price_point(price)["price"])


def default_price_for(model: str | Mapping[str, object]) -> float:
    """Return a monetization model's configured default price.

    A string may be either the model's stable key or its display name.
    """
    if isinstance(model, str):
        entry = monetization_model_by_key(model) or monetization_model_by_name(model)
        if entry is None:
            raise KeyError(f"unknown monetization model: {model}")
    else:
        entry = model

    price = entry.get("default_price")
    if isinstance(price, bool) or not isinstance(price, (int, float)):
        raise TypeError("monetization model has no numeric default_price")
    value = float(price)
    if not isfinite(value) or value < 0.0:
        raise ValueError("default_price must be finite and non-negative")
    return value


def default_price_point(model: str | Mapping[str, object]) -> Rule:
    """Return the nearest configured price point for a model's default."""
    return nearest_price_point(default_price_for(model))


def choose_default_price(model: str | Mapping[str, object]) -> float:
    """Return a model's default normalized to a configured price point."""
    return float(default_price_point(model)["price"])


__all__ = (
    "ANNOUNCEMENT_STRATEGIES",
    "COMMUNITY_ACTIONS",
    "MONETIZATION_MODELS",
    "PRICE_POINTS",
    "PRODUCT_RULES_VERSION",
    "RELEASE_POLICIES",
    "announcement_strategy_by_key",
    "announcement_strategy_by_name",
    "choose_default_price",
    "choose_nearest_price",
    "community_action_by_key",
    "community_action_by_name",
    "default_price_for",
    "default_price_point",
    "lookup_by_key",
    "lookup_by_name",
    "monetization_model_by_key",
    "monetization_model_by_name",
    "nearest_price_point",
    "price_point_by_key",
    "price_point_by_name",
    "release_policy_by_key",
    "release_policy_by_name",
)
