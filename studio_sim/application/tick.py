"""Deterministic day-advance loop and hold precedence for the M1 kernel clock (K2).

The core never reads a real clock: the caller supplies the active-play gate.
WP-01 owns day/revision bookkeeping, holds and capacity; WP-02 adds mandatory
K3 settlement and solvency evaluation inside the documented day order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Sequence, Tuple

from ..domain.campaign import (
    Campaign,
    _MAX_DAY,
    _MAX_REVISION,
    _is_int,
    _valid_identifier,
    from_validated_payload,
    to_payload,
)

_MAX_REQUESTED_DAYS = 3660


@dataclass(frozen=True)
class AdvanceGate:
    active_play: bool
    preview_holds: Tuple[str, ...] = ()


@dataclass(frozen=True)
class AdvanceResult:
    campaign: Campaign
    consumed_days: int
    stop_reason: str
    pending_decision_ids: Tuple[str, ...]


def _pending_decision_ids(decisions: Sequence[Dict[str, Any]], day: int) -> Tuple[str, ...]:
    return tuple(
        sorted(
            decision["id"]
            for decision in decisions
            if not decision["resolved"] and decision["due_day"] <= day
        )
    )


def _detached(campaign: Campaign) -> Campaign:
    return from_validated_payload(to_payload(campaign))


def _result(campaign: Campaign, consumed_days: int, stop_reason: str) -> AdvanceResult:
    return AdvanceResult(
        _detached(campaign),
        consumed_days,
        stop_reason,
        _pending_decision_ids(campaign.decisions, campaign.day),
    )


def _validate_request(requested_days: Any, gate: Any) -> None:
    if not _is_int(requested_days) or not 0 <= requested_days <= _MAX_REQUESTED_DAYS:
        raise ValueError("requested_days must be an integer 0..3660")
    if not isinstance(gate, AdvanceGate):
        raise ValueError("gate must be an AdvanceGate")
    if not isinstance(gate.active_play, bool):
        raise ValueError("gate.active_play must be bool")
    if not isinstance(gate.preview_holds, tuple):
        raise ValueError("gate.preview_holds must be a tuple of unique identifiers")
    seen = set()
    for hold in gate.preview_holds:
        if not _valid_identifier(hold) or hold in seen:
            raise ValueError("gate.preview_holds must be unique valid identifiers")
        seen.add(hold)


def advance(campaign: Campaign, requested_days: int, gate: AdvanceGate) -> AdvanceResult:
    _validate_request(requested_days, gate)
    if requested_days == 0:
        return _result(campaign, 0, "complete")
    if campaign.status != "running":
        return _result(campaign, 0, "ended")
    if not gate.active_play:
        return _result(campaign, 0, "inactive")
    if campaign.manual_paused:
        return _result(campaign, 0, "manual_pause")
    if gate.preview_holds:
        return _result(campaign, 0, "preview_hold")
    if _pending_decision_ids(campaign.decisions, campaign.day):
        return _result(campaign, 0, "decision")

    state = to_payload(campaign)
    consumed_days = 0
    stop_reason = "complete"
    for _ in range(requested_days):
        next_day = state["day"] + 1
        if next_day > _MAX_DAY:
            stop_reason = "capacity"
            break
        if state["revision"] + 1 > _MAX_REVISION:
            stop_reason = "capacity"
            break
        state["day"] = next_day
        consumed_days += 1
        # WP-02 inserts mandatory K3 settlement and solvency evaluation here,
        # before the review and revision steps of the frozen day order.
        state["revision"] += 1
        if state["status"] != "running":
            stop_reason = "ended"
            break
        if _pending_decision_ids(state["decisions"], state["day"]):
            stop_reason = "decision"
            break
    return AdvanceResult(
        from_validated_payload(state),
        consumed_days,
        stop_reason,
        _pending_decision_ids(state["decisions"], state["day"]),
    )
