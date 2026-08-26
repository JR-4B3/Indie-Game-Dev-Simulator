"""Finite, cohort-based demand allocation for a current-day games market.

The module is deliberately independent from the main simulation.  A weekly
shopper can choose at most one supplied product or the outside option, so
adding products redistributes a finite market rather than creating buyers.

Product signals accept either fractions (0..1) or scores (0..100).  Values in
``awareness_by_cohort`` above 100 are interpreted as absolute aware consumers;
``owners_by_cohort`` always contains absolute consumer counts.  Free product
"units" are acquisitions rather than paid sales.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import NamedTuple


@dataclass(frozen=True)
class ConsumerCohort:
    """An aggregate group whose members share purchasing preferences.

    ``disposable_budget`` is the typical weekly entertainment budget in USD.
    Affinity and preference values use a 0..1 scale.
    """

    key: str
    name: str
    region: str
    behavior: str
    population: int
    weekly_purchase_propensity: float
    disposable_budget: float
    price_sensitivity: float
    genre_affinities: Mapping[str, float]
    format_affinities: Mapping[str, float]
    platform_categories: Mapping[str, float]
    monetization_tolerance: float
    social_susceptibility: float
    complexity_preference: float


@dataclass(frozen=True)
class MacroSnapshot:
    """Economy-wide multipliers for one allocation week.

    Multipliers are neutral at 1.0.  ``inflation_rate`` is a decimal rate, so
    0.03 means three percent.  Mapping keys may be cohort keys, region names,
    platform categories, or ``"default"``.
    """

    spending_multiplier: float = 1.0
    consumer_confidence: float = 1.0
    inflation_rate: float = 0.0
    regional_spending_multipliers: Mapping[str, float] = field(default_factory=dict)
    platform_demand_multipliers: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ProductOffer:
    """The market-facing state of one product during the current week."""

    product_id: str
    genre: str
    secondary_genre: str = ""
    topic: str = ""
    target_audience: str = "Broad audience"
    game_format: str = "Offline solo"
    monetization: str = "Premium"
    price: float = 0.0
    quality: float = 50.0
    user_rating: float = 50.0
    awareness_by_cohort: Mapping[str, float] = field(default_factory=dict)
    owners_by_cohort: Mapping[str, float] = field(default_factory=dict)
    age_weeks: int = 0
    hype: float = 0.0
    trust: float = 50.0
    sentiment: float = 50.0
    novelty: float = 50.0
    network_health: float = 50.0
    store_reach: float = 100.0
    platform_category: str = "PC"
    cultural_resonance: float | Mapping[str, float] = 50.0
    lifecycle_state: str = "active"


@dataclass(frozen=True)
class DemandResult:
    """Allocated acquisitions and the remaining product-level opportunity."""

    product_id: str
    units: int
    units_by_cohort: Mapping[str, int]
    interested_by_cohort: Mapping[str, int]
    wishlists_by_cohort: Mapping[str, int]
    explanation_drivers: tuple[str, ...]
    unmet_potential: int


def _affinities(
    primary: Sequence[str],
    secondary: Sequence[str] = (),
    tertiary: Sequence[str] = (),
) -> dict[str, float]:
    values = {name: 0.96 for name in primary}
    values.update({name: 0.78 for name in secondary})
    values.update({name: 0.61 for name in tertiary})
    return values


_CORE_GENRES = (
    "Action",
    "First-Person Shooter",
    "Third-Person Shooter",
    "Role-Playing Game",
    "Soulslike",
    "Metroidvania",
)
_CASUAL_GENRES = (
    "Cozy Game",
    "Puzzle Game",
    "Skill Game",
    "Simulation",
    "Visual Novel",
)
_STRATEGY_GENRES = (
    "Strategy",
    "Real-Time Strategy",
    "Economic Simulation",
    "Building Game",
    "Automation",
    "Deckbuilder",
)
_SOCIAL_GENRES = (
    "Social Deduction",
    "Battle Royale",
    "Sports Game",
    "Fighting Game",
    "Racing",
)
_FAMILY_GENRES = (
    "Platformer",
    "Puzzle Game",
    "Racing",
    "Cozy Game",
    "Building Game",
)
_MOBILE_GENRES = (
    "Puzzle Game",
    "Skill Game",
    "Simulation",
    "Cozy Game",
    "Visual Novel",
)

_SOLO_FORMATS = _affinities(("Offline solo",), ("Online co-op",))
_SOCIAL_FORMATS = _affinities(
    ("Online co-op", "Competitive online"),
    ("Persistent world", "MMO"),
    ("Offline solo",),
)
_LIVE_FORMATS = _affinities(
    ("Competitive online", "Persistent world"),
    ("Online co-op", "MMO"),
    ("Offline solo",),
)


COHORTS: tuple[ConsumerCohort, ...] = (
    ConsumerCohort(
        "na_core",
        "North American core players",
        "NA",
        "core",
        54_000_000,
        0.0105,
        38.0,
        0.68,
        _affinities(_CORE_GENRES, _SOCIAL_GENRES, _STRATEGY_GENRES),
        _affinities(("Offline solo", "Online co-op"), ("Competitive online", "Persistent world")),
        {"PC": 0.94, "Console": 0.98, "Handheld": 0.58, "Mobile": 0.34},
        0.38,
        0.58,
        0.74,
    ),
    ConsumerCohort(
        "na_casual_family",
        "North American casual families",
        "NA",
        "family",
        61_000_000,
        0.0068,
        28.0,
        1.08,
        _affinities(_FAMILY_GENRES, _CASUAL_GENRES, ("Adventure", "Sports Game")),
        _SOLO_FORMATS,
        {"Console": 0.94, "Handheld": 0.82, "Mobile": 0.78, "PC": 0.46},
        0.25,
        0.63,
        0.31,
    ),
    ConsumerCohort(
        "na_social",
        "North American social competitors",
        "NA",
        "social",
        47_000_000,
        0.0110,
        32.0,
        0.82,
        _affinities(_SOCIAL_GENRES, _CORE_GENRES, ("Social Deduction", "Survival Game")),
        _SOCIAL_FORMATS,
        {"Console": 0.96, "PC": 0.82, "Mobile": 0.66, "Handheld": 0.52},
        0.62,
        0.92,
        0.49,
    ),
    ConsumerCohort(
        "eu_core",
        "European core players",
        "EU",
        "core",
        62_000_000,
        0.0094,
        34.0,
        0.76,
        _affinities(_CORE_GENRES, ("Adventure", "Racing", "Simulation"), _STRATEGY_GENRES),
        _affinities(("Offline solo", "Online co-op"), ("Competitive online",)),
        {"PC": 0.98, "Console": 0.88, "Handheld": 0.52, "Mobile": 0.36},
        0.31,
        0.54,
        0.76,
    ),
    ConsumerCohort(
        "eu_strategy",
        "European strategy enthusiasts",
        "EU",
        "strategy",
        34_000_000,
        0.0076,
        36.0,
        0.72,
        _affinities(_STRATEGY_GENRES, ("Role-Playing Game", "Roguelike", "Simulation")),
        _affinities(("Offline solo",), ("Online co-op", "Persistent world")),
        {"PC": 1.0, "Console": 0.42, "Handheld": 0.48, "Mobile": 0.25},
        0.22,
        0.39,
        0.94,
    ),
    ConsumerCohort(
        "eu_casual_family",
        "European casual and family players",
        "EU",
        "casual",
        57_000_000,
        0.0063,
        27.0,
        1.13,
        _affinities(_CASUAL_GENRES, _FAMILY_GENRES, ("Adventure", "Racing")),
        _SOLO_FORMATS,
        {"Mobile": 0.86, "Console": 0.78, "Handheld": 0.73, "PC": 0.53},
        0.29,
        0.57,
        0.28,
    ),
    ConsumerCohort(
        "east_asia_core",
        "East Asian core players",
        "East Asia",
        "core",
        76_000_000,
        0.0118,
        31.0,
        0.74,
        _affinities(
            ("Role-Playing Game", "Action", "Fighting Game", "Soulslike"),
            ("Visual Novel", "Adventure", "Monster Hunter", "Strategy"),
            _SOCIAL_GENRES,
        ),
        _affinities(("Offline solo", "Online co-op"), ("Competitive online", "MMO")),
        {"Console": 0.93, "PC": 0.76, "Handheld": 0.91, "Mobile": 0.54},
        0.49,
        0.68,
        0.72,
    ),
    ConsumerCohort(
        "east_asia_social_mobile",
        "East Asian social mobile players",
        "East Asia",
        "mobile",
        132_000_000,
        0.0132,
        18.0,
        1.02,
        _affinities(_MOBILE_GENRES, _SOCIAL_GENRES, ("Role-Playing Game", "Racing")),
        _LIVE_FORMATS,
        {"Mobile": 1.0, "Handheld": 0.72, "PC": 0.58, "Console": 0.45},
        0.81,
        0.94,
        0.46,
    ),
    ConsumerCohort(
        "east_asia_strategy",
        "East Asian strategy and MMO players",
        "East Asia",
        "strategy",
        39_000_000,
        0.0101,
        27.0,
        0.83,
        _affinities(_STRATEGY_GENRES, ("Role-Playing Game", "Roguelike", "Battle Royale")),
        _affinities(("Persistent world", "MMO"), ("Offline solo", "Competitive online")),
        {"PC": 1.0, "Mobile": 0.69, "Console": 0.48, "Handheld": 0.44},
        0.68,
        0.75,
        0.91,
    ),
    ConsumerCohort(
        "emerging_mobile",
        "Emerging-market mobile players",
        "Emerging",
        "mobile",
        286_000_000,
        0.0054,
        9.0,
        1.58,
        _affinities(_MOBILE_GENRES, _SOCIAL_GENRES, ("Sports Game", "Racing")),
        _LIVE_FORMATS,
        {"Mobile": 1.0, "PC": 0.35, "Console": 0.20, "Handheld": 0.31},
        0.86,
        0.91,
        0.35,
    ),
    ConsumerCohort(
        "emerging_social",
        "Emerging-market social competitors",
        "Emerging",
        "social",
        143_000_000,
        0.0062,
        12.0,
        1.43,
        _affinities(_SOCIAL_GENRES, ("Action", "First-Person Shooter", "Survival Game"), _MOBILE_GENRES),
        _SOCIAL_FORMATS,
        {"Mobile": 0.94, "PC": 0.59, "Console": 0.32, "Handheld": 0.37},
        0.74,
        0.96,
        0.47,
    ),
    ConsumerCohort(
        "emerging_family_casual",
        "Emerging-market family and casual players",
        "Emerging",
        "family",
        104_000_000,
        0.0037,
        8.0,
        1.67,
        _affinities(_FAMILY_GENRES, _CASUAL_GENRES, ("Sports Game", "Adventure")),
        _SOLO_FORMATS,
        {"Mobile": 0.96, "Handheld": 0.51, "PC": 0.32, "Console": 0.23},
        0.45,
        0.72,
        0.25,
    ),
)

# Descriptive alias for callers that prefer an explicit exported name.
CONSUMER_COHORTS = COHORTS
_COHORTS_BY_KEY = {cohort.key: cohort for cohort in COHORTS}


def cohort_by_key(key: str) -> ConsumerCohort:
    """Return a configured cohort, raising ``KeyError`` for an unknown key."""

    try:
        return _COHORTS_BY_KEY[key]
    except KeyError:
        normalized = str(key).strip().casefold()
        for cohort in COHORTS:
            if cohort.key.casefold() == normalized:
                return cohort
        raise KeyError(f"unknown consumer cohort: {key!r}") from None


class _OfferMetrics(NamedTuple):
    eligible: int
    interested: int
    choice_utility: float
    wishlist_rate: float
    purchase_enabled: bool
    drivers: tuple[tuple[str, float], ...]


def _number(value: object, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _ratio(value: object, default: float = 0.0) -> float:
    """Normalize a fraction or a percentage-like score to 0..1."""

    number = _number(value, default)
    if number > 1.0:
        number /= 100.0
    return _clamp(number, 0.0, 1.0)


def _multiplier(value: object, default: float = 1.0) -> float:
    number = _number(value, default)
    if number > 10.0:
        number /= 100.0
    return _clamp(number, 0.0, 4.0)


def _mapping_value(
    values: Mapping[str, float],
    cohort: ConsumerCohort,
    default: float,
) -> float:
    for key in (cohort.key, cohort.region, cohort.behavior, "default", "*"):
        if key in values:
            return _number(values[key], default)
    normalized = {
        str(key).strip().casefold(): value for key, value in values.items()
    }
    for key in (cohort.key, cohort.region, cohort.behavior, "default", "*"):
        if key.casefold() in normalized:
            return _number(normalized[key.casefold()], default)
    return default


def _lookup_affinity(values: Mapping[str, float], key: str, default: float) -> float:
    if key in values:
        return _clamp(_number(values[key], default), 0.0, 1.0)
    normalized = str(key).strip().casefold()
    for candidate, value in values.items():
        if str(candidate).strip().casefold() == normalized:
            return _clamp(_number(value, default), 0.0, 1.0)
    return default


def _awareness(offer: ProductOffer, cohort: ConsumerCohort) -> float:
    raw = _mapping_value(offer.awareness_by_cohort, cohort, 0.0)
    if raw <= 1.0:
        return _clamp(raw, 0.0, 1.0)
    if raw <= 100.0:
        return _clamp(raw / 100.0, 0.0, 1.0)
    return _clamp(raw / max(1, cohort.population), 0.0, 1.0)


def _cultural_fit(offer: ProductOffer, cohort: ConsumerCohort) -> float:
    resonance = offer.cultural_resonance
    if isinstance(resonance, Mapping):
        return _ratio(_mapping_value(resonance, cohort, 0.5), 0.5)
    return _ratio(resonance, 0.5)


def _audience_fit(target_audience: str, behavior: str) -> float:
    target = str(target_audience).strip().casefold()
    if not target or "broad" in target or target == "all":
        return 0.82
    matches = {
        "family": ("kid", "famil"),
        "core": ("core",),
        "strategy": ("strateg", "enthusiast"),
        "casual": ("casual", "cozy"),
        "social": ("social", "group"),
        "mobile": ("mobile", "casual", "social"),
    }
    if any(token in target for token in matches.get(behavior, ())):
        return 1.0
    if behavior == "family" and ("casual" in target or "cozy" in target):
        return 0.86
    if behavior == "core" and ("strateg" in target or "social" in target):
        return 0.72
    if behavior == "strategy" and "core" in target:
        return 0.78
    if behavior == "social" and "core" in target:
        return 0.76
    return 0.43


def _complexity_for(genre: str, game_format: str) -> float:
    text = f"{genre} {game_format}".casefold()
    if any(token in text for token in ("strategy", "economic", "automation", "mmo")):
        return 0.93
    if any(token in text for token in ("role-playing", "deckbuilder", "persistent", "simulation")):
        return 0.76
    if any(token in text for token in ("shooter", "souls", "survival", "competitive")):
        return 0.62
    if any(token in text for token in ("puzzle", "adventure", "co-op", "visual novel")):
        return 0.46
    if any(token in text for token in ("cozy", "skill", "platformer", "racing")):
        return 0.29
    return 0.52


def _monetization_fit(monetization: str, tolerance: float) -> float:
    text = str(monetization).strip().casefold().replace("_", " ")
    tolerance = _clamp(tolerance, 0.0, 1.0)
    if not text or text in {"none", "free", "premium", "one time", "complete package", "donationware", "donations"}:
        return 0.96
    if "loot" in text or "gacha" in text:
        return 0.08 + 0.78 * tolerance
    if "ad" in text:
        return 0.18 + 0.70 * tolerance
    if "battle pass" in text or "microtransaction" in text or "live service" in text:
        return 0.22 + 0.68 * tolerance
    if "subscription" in text:
        return 0.38 + 0.52 * tolerance
    if "free" in text or "f2p" in text:
        return 0.42 + 0.52 * tolerance
    if "dlc" in text or "expansion" in text:
        return 0.58 + 0.35 * tolerance
    return 0.48 + 0.42 * tolerance


def _lifecycle_effect(state: str) -> tuple[bool, float]:
    normalized = str(state).strip().casefold().replace("_", " ").replace("-", " ")
    if normalized in {"announced", "prelaunch", "pre release", "upcoming", "development"}:
        return False, 0.18
    if normalized in {"cancelled", "delisted", "retired", "closed", "unavailable"}:
        return False, -4.0
    if normalized in {"launch", "launch week", "new", "released"}:
        return True, 0.36
    if normalized in {"mature", "maintenance"}:
        return True, -0.22
    if normalized in {"legacy", "long tail"}:
        return True, -0.48
    if normalized in {"sunset", "sunsetting"}:
        return True, -0.88
    return True, 0.0


def _macro_factor(macro: MacroSnapshot, cohort: ConsumerCohort) -> float:
    spending = _multiplier(macro.spending_multiplier)
    confidence = _ratio(macro.consumer_confidence, 1.0)
    regional = _multiplier(
        _mapping_value(macro.regional_spending_multipliers, cohort, 1.0)
    )
    return _clamp(spending * (0.62 + 0.38 * confidence) * regional, 0.0, 3.0)


def _platform_macro_factor(macro: MacroSnapshot, platform: str) -> float:
    values = macro.platform_demand_multipliers
    if platform in values:
        return _multiplier(values[platform])
    normalized = str(platform).strip().casefold()
    for key, value in values.items():
        if str(key).strip().casefold() == normalized:
            return _multiplier(value)
    return _multiplier(values.get("default", 1.0))


def _sigmoid(value: float) -> float:
    if value >= 0.0:
        inverse = math.exp(-min(value, 60.0))
        return 1.0 / (1.0 + inverse)
    direct = math.exp(max(value, -60.0))
    return direct / (1.0 + direct)


def _offer_metrics(
    offer: ProductOffer,
    cohort: ConsumerCohort,
    macro: MacroSnapshot,
) -> _OfferMetrics:
    population = max(0, int(cohort.population))
    owners = int(_clamp(
        _mapping_value(offer.owners_by_cohort, cohort, 0.0),
        0.0,
        float(population),
    ))
    eligible = max(0, population - owners)
    awareness = _awareness(offer, cohort)
    store_reach = _ratio(offer.store_reach, 1.0)
    access = (awareness ** 0.75) * store_reach

    primary_fit = _lookup_affinity(cohort.genre_affinities, offer.genre, 0.44)
    if offer.secondary_genre and offer.secondary_genre != offer.genre:
        secondary_fit = _lookup_affinity(
            cohort.genre_affinities, offer.secondary_genre, 0.44
        )
        genre_fit = primary_fit * 0.78 + secondary_fit * 0.22
    else:
        genre_fit = primary_fit
    format_fit = _lookup_affinity(cohort.format_affinities, offer.game_format, 0.42)
    platform_fit = _lookup_affinity(
        cohort.platform_categories, offer.platform_category, 0.18
    )
    audience_fit = _audience_fit(offer.target_audience, cohort.behavior)
    complexity_fit = 1.0 - abs(
        _clamp(cohort.complexity_preference, 0.0, 1.0)
        - _complexity_for(offer.genre, offer.game_format)
    )
    monetization_fit = _monetization_fit(
        offer.monetization, cohort.monetization_tolerance
    )

    quality = _ratio(offer.quality, 0.5)
    rating = _ratio(offer.user_rating, 0.5)
    hype = _ratio(offer.hype)
    trust = _ratio(offer.trust, 0.5)
    sentiment = _ratio(offer.sentiment, 0.5)
    novelty = _ratio(offer.novelty, 0.5)
    network = _ratio(offer.network_health, 0.5)
    culture = _cultural_fit(offer, cohort)
    age_weeks = max(0, int(_number(offer.age_weeks)))
    purchase_enabled, lifecycle = _lifecycle_effect(offer.lifecycle_state)

    game_format = str(offer.game_format).casefold()
    online = any(
        token in game_format
        for token in ("online", "competitive", "persistent", "mmo", "co-op")
    )
    network_weight = 1.0 if online else 0.20
    social_signal = (
        0.42 * hype + 0.35 * sentiment + 0.23 * (network * network_weight + 0.5 * (1.0 - network_weight))
    )

    macro_factor = _macro_factor(macro, cohort)
    inflation = _number(macro.inflation_rate)
    if abs(inflation) > 1.0:
        inflation /= 100.0
    inflation = _clamp(inflation, -0.50, 2.0)
    effective_budget = max(
        0.01,
        cohort.disposable_budget * max(0.10, macro_factor) / (1.0 + inflation),
    )
    price = max(0.0, _number(offer.price))
    price_ratio = price / effective_budget
    if price <= 0.0:
        price_effect = 0.52
        wishlist_rate = 0.025
    else:
        price_effect = -1.18 * max(0.0, cohort.price_sensitivity) * math.log1p(price_ratio)
        barrier = price_ratio / (1.0 + price_ratio)
        wishlist_rate = _clamp(
            0.07 + 0.46 * barrier + 0.10 * (1.0 - trust), 0.04, 0.68
        )

    fit_driver = 1.48 * (genre_fit - 0.50) + 0.82 * (audience_fit - 0.50)
    format_driver = 0.88 * (format_fit - 0.50) + 1.02 * (platform_fit - 0.50)
    quality_driver = 1.14 * (quality - 0.50) + 0.96 * (rating - 0.50)
    complexity_driver = 0.68 * (complexity_fit - 0.50)
    monetization_driver = 0.90 * (monetization_fit - 0.50)
    social_driver = (
        1.28
        * _clamp(cohort.social_susceptibility, 0.0, 1.0)
        * (social_signal - 0.50)
    )
    trust_driver = 0.42 * (trust - 0.50)
    culture_driver = 0.78 * (culture - 0.50)
    age_driver = 0.62 * (novelty - 0.50) - 1.10 * math.log1p(age_weeks / 12.0) + lifecycle
    macro_driver = 0.38 * math.log(max(0.05, macro_factor))

    intrinsic_utility = _clamp(
        -1.55
        + fit_driver
        + format_driver
        + quality_driver
        + complexity_driver
        + monetization_driver
        + social_driver
        + trust_driver
        + culture_driver
        + age_driver
        + macro_driver
        + price_effect,
        -50.0,
        50.0,
    )

    unavailable = str(offer.lifecycle_state).strip().casefold() in {
        "cancelled",
        "delisted",
        "retired",
        "closed",
        "unavailable",
    }
    if unavailable or eligible <= 0 or access <= 0.0:
        interested = 0
    else:
        interested = min(
            eligible,
            max(0, int(math.floor(eligible * access * _sigmoid(intrinsic_utility + 0.30) + 0.5))),
        )

    if not purchase_enabled:
        normalized_state = str(offer.lifecycle_state).strip().casefold()
        wishlist_rate = 0.0 if unavailable else _clamp(0.58 + 0.24 * hype, 0.0, 0.88)

    if purchase_enabled and interested > 0:
        eligible_share = eligible / max(1, population)
        platform_macro = _platform_macro_factor(macro, offer.platform_category)
        if platform_macro <= 0.0:
            choice_utility = -60.0
        else:
            choice_utility = _clamp(
                intrinsic_utility
                + math.log(max(access, 1e-15))
                + math.log(max(eligible_share, 1e-15))
                + math.log(platform_macro)
                - 2.2,
                -60.0,
                60.0,
            )
    else:
        choice_utility = -60.0

    access_driver = 1.10 * (access - 0.45)
    drivers = (
        ("fit", fit_driver),
        ("format", format_driver + complexity_driver),
        ("quality", quality_driver + trust_driver),
        ("price", price_effect),
        ("access", access_driver),
        ("social", social_driver),
        ("monetization", monetization_driver),
        ("age", age_driver),
        ("culture", culture_driver),
        ("macro", macro_driver),
    )
    return _OfferMetrics(
        eligible,
        interested,
        choice_utility,
        wishlist_rate,
        purchase_enabled,
        drivers,
    )


def _stable_choice_shares(utilities: Sequence[float]) -> list[float]:
    """Return product shares from a stable softmax with utility-zero outside."""

    if not utilities:
        return []
    maximum = max(0.0, max(utilities))
    outside_weight = math.exp(-maximum)
    weights = [math.exp(_clamp(value - maximum, -120.0, 0.0)) for value in utilities]
    denominator = outside_weight + math.fsum(weights)
    if denominator <= 0.0 or not math.isfinite(denominator):
        return [0.0 for _ in utilities]
    return [weight / denominator for weight in weights]


def _integer_allocations(
    expected: Sequence[float],
    capacities: Sequence[int],
    shopper_pool: int,
    rng: random.Random,
) -> list[int]:
    bounded = [
        min(max(0.0, _number(value)), float(max(0, capacity)))
        for value, capacity in zip(expected, capacities)
    ]
    allocations = [int(math.floor(value)) for value in bounded]
    total_expected = min(float(max(0, shopper_pool)), math.fsum(bounded))
    target = int(math.floor(total_expected))
    if rng.random() < total_expected - target:
        target += 1
    target = min(target, max(0, shopper_pool), sum(max(0, value) for value in capacities))

    remainder = max(0, target - sum(allocations))
    candidates = [
        (bounded[index] - allocations[index], rng.random(), index)
        for index in range(len(bounded))
        if allocations[index] < max(0, capacities[index])
    ]
    candidates.sort(reverse=True)
    for _, _, index in candidates[:remainder]:
        allocations[index] += 1
    return allocations


_DRIVER_TEXT = {
    "fit": ("Strong genre and audience fit", "Weak genre or audience fit"),
    "format": ("Good format, platform, and complexity fit", "Format or platform mismatch"),
    "quality": ("Quality and reviews support demand", "Quality or reviews suppress demand"),
    "price": ("Free acquisition lowers friction", "Price resistance"),
    "access": ("Broad awareness and store reach", "Limited awareness or store reach"),
    "social": ("Strong social and network momentum", "Weak social or network momentum"),
    "monetization": ("Accepted monetization", "Monetization hostility"),
    "age": ("Fresh lifecycle momentum", "Age and lifecycle drag"),
    "culture": ("Strong cultural resonance", "Weak cultural resonance"),
    "macro": ("Supportive consumer spending", "Weak consumer spending"),
}


def _explanation_drivers(
    metrics: Sequence[_OfferMetrics],
    offer: ProductOffer,
) -> tuple[str, ...]:
    totals = {key: 0.0 for key in _DRIVER_TEXT}
    total_weight = 0.0
    for item in metrics:
        weight = max(1.0, float(item.interested))
        total_weight += weight
        for key, value in item.drivers:
            totals[key] += value * weight
    if total_weight > 0.0:
        totals = {key: value / total_weight for key, value in totals.items()}
    if max(0.0, _number(offer.price)) <= 0.0:
        totals["price"] = max(0.52, totals["price"])

    ranked = sorted(totals.items(), key=lambda item: abs(item[1]), reverse=True)
    explanations = [
        _DRIVER_TEXT[key][0 if value >= 0.0 else 1]
        for key, value in ranked
        if abs(value) >= 0.05
    ][:5]
    return tuple(explanations or ("Balanced demand factors",))


def allocate_weekly_demand(
    offers: Sequence[ProductOffer],
    macro: MacroSnapshot,
    seed: int,
) -> list[DemandResult]:
    """Allocate one finite week of demand among all supplied products.

    For each cohort, utilities enter a numerically stable multinomial logit
    alongside an outside option.  Aggregate allocations are capped by both the
    cohort's shopper pool and each product's interested non-owner population.
    The seed controls small aggregate taste shocks and unbiased integer
    rounding; identical inputs and seeds produce identical results.
    """

    products = list(offers)
    if not products:
        return []

    rng = random.Random(seed)
    metrics_by_product: list[list[_OfferMetrics]] = [
        [] for _ in products
    ]
    units_by_product: list[dict[str, int]] = [
        {cohort.key: 0 for cohort in COHORTS} for _ in products
    ]

    for cohort in COHORTS:
        cohort_metrics = [
            _offer_metrics(offer, cohort, macro) for offer in products
        ]
        for index, item in enumerate(cohort_metrics):
            metrics_by_product[index].append(item)

        macro_factor = _macro_factor(macro, cohort)
        shopper_pool = min(
            max(0, int(cohort.population)),
            max(
                0,
                int(
                    math.floor(
                        max(0, cohort.population)
                        * max(0.0, cohort.weekly_purchase_propensity)
                        * macro_factor
                    )
                ),
            ),
        )
        if shopper_pool <= 0:
            continue

        # One shock per offer represents unobserved aggregate taste without
        # simulating millions of individual consumers.
        utilities = [
            item.choice_utility + rng.normalvariate(0.0, 0.035)
            if item.purchase_enabled and item.interested > 0
            else -60.0
            for item in cohort_metrics
        ]
        shares = _stable_choice_shares(utilities)
        capacities = [item.interested for item in cohort_metrics]
        expected = [
            min(float(capacity), shopper_pool * share)
            for capacity, share in zip(capacities, shares)
        ]
        allocations = _integer_allocations(
            expected, capacities, shopper_pool, rng
        )
        for index, units in enumerate(allocations):
            units_by_product[index][cohort.key] = max(0, units)

    results: list[DemandResult] = []
    for index, offer in enumerate(products):
        product_metrics = metrics_by_product[index]
        interested_by_cohort = {
            cohort.key: max(0, product_metrics[position].interested)
            for position, cohort in enumerate(COHORTS)
        }
        wishlists_by_cohort: dict[str, int] = {}
        for position, cohort in enumerate(COHORTS):
            item = product_metrics[position]
            remaining_interest = max(
                0,
                item.interested - units_by_product[index][cohort.key],
            )
            wishlists_by_cohort[cohort.key] = min(
                remaining_interest,
                max(0, int(math.floor(remaining_interest * item.wishlist_rate + 0.5))),
            )

        units = max(0, sum(units_by_product[index].values()))
        interested = max(0, sum(interested_by_cohort.values()))
        results.append(
            DemandResult(
                product_id=str(offer.product_id),
                units=units,
                units_by_cohort=units_by_product[index],
                interested_by_cohort=interested_by_cohort,
                wishlists_by_cohort=wishlists_by_cohort,
                explanation_drivers=_explanation_drivers(product_metrics, offer),
                unmet_potential=max(0, interested - units),
            )
        )
    return results


def single_product_demand(
    offer: ProductOffer,
    macro: MacroSnapshot,
    seed: int,
) -> DemandResult:
    """Allocate demand for one product against the same outside option."""

    return allocate_weekly_demand((offer,), macro, seed)[0]


__all__ = (
    "COHORTS",
    "CONSUMER_COHORTS",
    "ConsumerCohort",
    "DemandResult",
    "MacroSnapshot",
    "ProductOffer",
    "allocate_weekly_demand",
    "cohort_by_key",
    "single_product_demand",
)
