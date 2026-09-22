"""Explicit campaign configuration, state and canonical snapshot helpers (M1-K1/K2).

This module is standard-library only and never reads a wall clock, global
randomness or the filesystem.  Every boundary function detaches its result from
caller-owned collections; nested records stay JSON-shaped on purpose.
"""

from __future__ import annotations

import copy
import datetime
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

_ID_PATTERN = re.compile(r"[a-z][a-z0-9_-]{0,47}\Z")
_DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")

_SIMULATION_VERSION = 1
_RULESET_ID = "m1-kernel-1"

_MAX_DAY = 36500
_MAX_REVISION = 10**9
_MAX_EVENTS = 8192
_MAX_DECISIONS = 64
_RECEIPT_LIMIT = 64
_MAX_OPENING_CASH_MINOR = 10**12
_MAX_MONTHLY_DRAW_MINOR = 10**9
_MAX_SEED = 2**64 - 1
_MIN_YEAR = 2000
_MAX_YEAR = 2199
_MAX_REASON_CHARS = 160

_MODES = ("normal", "ironman")


def _is_int(value: Any) -> bool:
    """True for exact integers; bool is rejected (K1: never bool)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _valid_identifier(value: Any) -> bool:
    return isinstance(value, str) and _ID_PATTERN.match(value) is not None


def _valid_reason(value: Any) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= _MAX_REASON_CHARS and "\x00" not in value


def _canonical_json_bytes(value: Any) -> bytes:
    """Canonical JSON exactly as frozen in K4."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _parse_start_date(value: Any) -> datetime.date:
    if not isinstance(value, str) or _DATE_PATTERN.match(value) is None:
        raise ValueError("start_date must be an exact ISO YYYY-MM-DD date")
    year, month, day = (int(part) for part in value.split("-"))
    if not _MIN_YEAR <= year <= _MAX_YEAR:
        raise ValueError("start_date year must be 2000..2199")
    try:
        return datetime.date(year, month, day)
    except ValueError as error:
        raise ValueError("start_date is not a valid calendar date") from error


@dataclass(frozen=True)
class CampaignConfig:
    campaign_id: str
    start_date: str
    seed: int
    mode: str
    opening_cash_minor: int
    monthly_draw_minor: int
    decisions: Tuple[Dict[str, Any], ...] = ()


@dataclass(frozen=True)
class Campaign:
    campaign_id: str
    start_date: str
    seed: int
    simulation_version: int
    ruleset_id: str
    mode: str
    day: int
    revision: int
    status: str
    closed_reason: Optional[str]
    manual_paused: bool
    next_event_id: int
    events: Tuple[Dict[str, Any], ...]
    decisions: Tuple[Dict[str, Any], ...]
    receipts: Tuple[Dict[str, Any], ...]
    finance: Dict[str, Any]


def _validate_config(config: Any) -> None:
    if not isinstance(config, CampaignConfig):
        raise ValueError("config must be a CampaignConfig")
    if not _valid_identifier(config.campaign_id):
        raise ValueError("campaign_id must match [a-z][a-z0-9_-]{0,47}")
    _parse_start_date(config.start_date)
    if not _is_int(config.seed) or not 0 <= config.seed <= _MAX_SEED:
        raise ValueError("seed must be an integer 0..2**64-1")
    if config.mode not in _MODES:
        raise ValueError("mode must be 'normal' or 'ironman'")
    if not _is_int(config.opening_cash_minor) or not 0 <= config.opening_cash_minor <= _MAX_OPENING_CASH_MINOR:
        raise ValueError("opening_cash_minor must be an integer 0..10**12")
    if not _is_int(config.monthly_draw_minor) or not 0 <= config.monthly_draw_minor <= _MAX_MONTHLY_DRAW_MINOR:
        raise ValueError("monthly_draw_minor must be an integer 0..10**9")
    decisions = config.decisions
    if not isinstance(decisions, (list, tuple)):
        raise ValueError("decisions must be a sequence of decision mappings")
    if len(decisions) > _MAX_DECISIONS:
        raise ValueError("decisions must contain at most 64 entries")
    seen = set()
    for decision in decisions:
        if not isinstance(decision, dict) or set(decision) != {"id", "due_day", "reason"}:
            raise ValueError("each config decision must have exactly id, due_day and reason")
        if not _valid_identifier(decision["id"]):
            raise ValueError("decision id must match [a-z][a-z0-9_-]{0,47}")
        if decision["id"] in seen:
            raise ValueError("decision ids must be unique")
        seen.add(decision["id"])
        if not _is_int(decision["due_day"]) or not 0 <= decision["due_day"] <= _MAX_DAY:
            raise ValueError("decision due_day must be an integer 0..36500")
        if not _valid_reason(decision["reason"]):
            raise ValueError("decision reason must be 1..160 characters without NUL")


def new_campaign(config: CampaignConfig) -> Campaign:
    """Build the explicit day-0 snapshot; invalid config raises ValueError."""
    _validate_config(config)
    decisions = tuple(
        {
            "id": decision["id"],
            "due_day": decision["due_day"],
            "reason": decision["reason"],
            "resolved": False,
        }
        for decision in sorted(config.decisions, key=lambda decision: decision["id"])
    )
    finance = {
        "opening_cash_minor": config.opening_cash_minor,
        "cash_minor": config.opening_cash_minor,
        "monthly_draw_minor": config.monthly_draw_minor,
        "negative_since_day": None,
        "next_posting_id": 1,
        "postings": [],
        "obligations": [],
        "labor": [],
    }
    return Campaign(
        campaign_id=config.campaign_id,
        start_date=config.start_date,
        seed=config.seed,
        simulation_version=_SIMULATION_VERSION,
        ruleset_id=_RULESET_ID,
        mode=config.mode,
        day=0,
        revision=0,
        status="running",
        closed_reason=None,
        manual_paused=False,
        next_event_id=1,
        events=(),
        decisions=decisions,
        receipts=(),
        finance=finance,
    )


def to_payload(campaign: Campaign) -> Dict[str, Any]:
    """Full internal snapshot; detached from the campaign it is read from."""
    return {
        "campaign_id": campaign.campaign_id,
        "start_date": campaign.start_date,
        "seed": campaign.seed,
        "simulation_version": campaign.simulation_version,
        "ruleset_id": campaign.ruleset_id,
        "mode": campaign.mode,
        "day": campaign.day,
        "revision": campaign.revision,
        "status": campaign.status,
        "closed_reason": campaign.closed_reason,
        "manual_paused": campaign.manual_paused,
        "next_event_id": campaign.next_event_id,
        "events": [copy.deepcopy(event) for event in campaign.events],
        "decisions": [copy.deepcopy(decision) for decision in campaign.decisions],
        "receipts": [copy.deepcopy(receipt) for receipt in campaign.receipts],
        "finance": copy.deepcopy(campaign.finance),
    }


def from_validated_payload(payload: Dict[str, Any]) -> Campaign:
    """Copy an already-validated K1 snapshot; trust only the strict codec seam."""
    return Campaign(
        campaign_id=payload["campaign_id"],
        start_date=payload["start_date"],
        seed=payload["seed"],
        simulation_version=payload["simulation_version"],
        ruleset_id=payload["ruleset_id"],
        mode=payload["mode"],
        day=payload["day"],
        revision=payload["revision"],
        status=payload["status"],
        closed_reason=payload["closed_reason"],
        manual_paused=payload["manual_paused"],
        next_event_id=payload["next_event_id"],
        events=tuple(copy.deepcopy(payload["events"])),
        decisions=tuple(copy.deepcopy(payload["decisions"])),
        receipts=tuple(copy.deepcopy(payload["receipts"])),
        finance=copy.deepcopy(payload["finance"]),
    )


def calendar_date(campaign: Campaign) -> str:
    """Current in-game date derived from start_date plus day (never persisted)."""
    return (_parse_start_date(campaign.start_date) + datetime.timedelta(days=campaign.day)).isoformat()
