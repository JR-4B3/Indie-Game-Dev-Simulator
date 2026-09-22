"""Functional command transaction boundary for the M1 kernel clock (K2).

Validation order is frozen: envelope/types, receipt lookup, stale revision,
closed campaign, kind/payload semantics, then capacity and application.
Rejected commands change nothing and are never cached.
"""

from __future__ import annotations

import hashlib
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..domain.campaign import (
    Campaign,
    _MAX_EVENTS,
    _MAX_REVISION,
    _RECEIPT_LIMIT,
    _canonical_json_bytes,
    _is_int,
    _valid_identifier,
    from_validated_payload,
    to_payload,
)
from .commands import Command, CommandResult

StateMutator = Callable[[Dict[str, Any]], None]

_JSON_MAX_DEPTH = 32


def _plain_json(value: Any) -> bool:
    """True only for the exact JSON tree allowed in a command payload.

    Accepts exactly dict (string keys), list, str, int, bool and None.  Tuple,
    set, float, every subclass, ancestor cycles and containers nested deeper
    than 32 levels (payload root is level 1) are rejected.  Shared non-cyclic
    references stay valid because only the current ancestor path is tracked.
    """

    def allowed(node: Any, depth: int, ancestors: Tuple[int, ...]) -> bool:
        node_type = type(node)
        if node is None or node_type is bool or node_type is int or node_type is str:
            return True
        if depth > _JSON_MAX_DEPTH:
            return False
        if node_type is list:
            if id(node) in ancestors:
                return False
            nested = ancestors + (id(node),)
            return all(allowed(item, depth + 1, nested) for item in node)
        if node_type is dict:
            if id(node) in ancestors:
                return False
            nested = ancestors + (id(node),)
            for key, item in node.items():
                if type(key) is not str:
                    return False
                if not allowed(item, depth + 1, nested):
                    return False
            return True
        return False

    return allowed(value, 1, ())


def _fingerprint(command: Command) -> str:
    material = {
        "expected_revision": command.expected_revision,
        "kind": command.kind,
        "payload": command.payload,
    }
    return hashlib.sha256(_canonical_json_bytes(material)).hexdigest()


def _detached(campaign: Campaign) -> Campaign:
    return from_validated_payload(to_payload(campaign))


def _rejected(campaign: Campaign, code: str) -> CommandResult:
    return CommandResult(_detached(campaign), False, code, None, (), False)


def _capacity_reached(campaign: Campaign, event_count: int) -> bool:
    if campaign.revision + 1 > _MAX_REVISION:
        return True
    return len(campaign.events) + event_count > _MAX_EVENTS


def _emitted_event(
    campaign: Campaign,
    event_id: str,
    kind: str,
    source: str,
    subject_id: Optional[str],
    facts: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "id": event_id,
        "day": campaign.day,
        "kind": kind,
        "source": source,
        "subject_id": subject_id,
        "facts": facts,
    }


def _commit(
    campaign: Campaign,
    command: Command,
    fingerprint: str,
    events: List[Dict[str, Any]],
    mutate: Optional[StateMutator] = None,
) -> CommandResult:
    state = to_payload(campaign)
    if mutate is not None:
        mutate(state)
    revision = campaign.revision + 1
    state["revision"] = revision
    if events:
        state["events"].extend(events)
        state["next_event_id"] = campaign.next_event_id + len(events)
    event_ids = tuple(event["id"] for event in events)
    receipts = state["receipts"]
    receipts.append(
        {
            "command_id": command.command_id,
            "fingerprint": fingerprint,
            "applied_revision": revision,
            "event_ids": list(event_ids),
        }
    )
    if len(receipts) > _RECEIPT_LIMIT:
        del receipts[: len(receipts) - _RECEIPT_LIMIT]
    return CommandResult(from_validated_payload(state), True, "ok", revision, event_ids, False)


def _execute_set_pause(campaign: Campaign, command: Command, fingerprint: str) -> CommandResult:
    if set(command.payload) != {"paused"} or not isinstance(command.payload["paused"], bool):
        return _rejected(campaign, "invalid_command")
    paused = command.payload["paused"]
    if paused == campaign.manual_paused:
        if _capacity_reached(campaign, 0):
            return _rejected(campaign, "capacity")
        return _commit(campaign, command, fingerprint, [])
    if _capacity_reached(campaign, 1):
        return _rejected(campaign, "capacity")
    event = _emitted_event(campaign, f"e-{campaign.next_event_id}", "pause_changed", f"cmd:{command.command_id}", None, {"paused": paused})

    def mutate(state: Dict[str, Any]) -> None:
        state["manual_paused"] = paused

    return _commit(campaign, command, fingerprint, [event], mutate)


def _execute_resolve_decision(campaign: Campaign, command: Command, fingerprint: str) -> CommandResult:
    if set(command.payload) != {"decision_id"} or not _valid_identifier(command.payload["decision_id"]):
        return _rejected(campaign, "invalid_command")
    decision_id = command.payload["decision_id"]
    target = None
    for decision in campaign.decisions:
        if decision["id"] == decision_id:
            target = decision
            break
    if target is None:
        return _rejected(campaign, "unknown_target")
    if target["due_day"] > campaign.day:
        return _rejected(campaign, "not_due")
    if target["resolved"]:
        return _rejected(campaign, "already_resolved")
    if _capacity_reached(campaign, 1):
        return _rejected(campaign, "capacity")
    event = _emitted_event(campaign, f"e-{campaign.next_event_id}", "decision_resolved", f"cmd:{command.command_id}", decision_id, {})

    def mutate(state: Dict[str, Any]) -> None:
        for decision in state["decisions"]:
            if decision["id"] == decision_id:
                decision["resolved"] = True
                break

    return _commit(campaign, command, fingerprint, [event], mutate)


def _execute_retire(campaign: Campaign, command: Command, fingerprint: str) -> CommandResult:
    if command.payload:
        return _rejected(campaign, "invalid_command")
    if _capacity_reached(campaign, 1):
        return _rejected(campaign, "capacity")
    event = _emitted_event(campaign, f"e-{campaign.next_event_id}", "campaign_closed", f"cmd:{command.command_id}", None, {"reason": "retired"})

    def mutate(state: Dict[str, Any]) -> None:
        state["status"] = "retired"
        state["closed_reason"] = "retired"

    return _commit(campaign, command, fingerprint, [event], mutate)


def execute(campaign: Campaign, command: Command) -> CommandResult:
    if not isinstance(command, Command):
        return _rejected(campaign, "invalid_command")
    if not _valid_identifier(command.command_id):
        return _rejected(campaign, "invalid_command")
    if not _is_int(command.expected_revision) or not 0 <= command.expected_revision <= _MAX_REVISION:
        return _rejected(campaign, "invalid_command")
    if not isinstance(command.kind, str):
        return _rejected(campaign, "invalid_command")
    if not isinstance(command.payload, dict) or not _plain_json(command.payload):
        return _rejected(campaign, "invalid_command")
    fingerprint = _fingerprint(command)

    for receipt in campaign.receipts:
        if receipt["command_id"] == command.command_id:
            if receipt["fingerprint"] == fingerprint:
                return CommandResult(
                    _detached(campaign),
                    True,
                    "duplicate",
                    receipt["applied_revision"],
                    tuple(receipt["event_ids"]),
                    True,
                )
            return _rejected(campaign, "id_conflict")
    if command.expected_revision != campaign.revision:
        return _rejected(campaign, "stale_revision")
    if campaign.status != "running":
        return _rejected(campaign, "ended")
    if command.kind == "set_pause":
        return _execute_set_pause(campaign, command, fingerprint)
    if command.kind == "resolve_decision":
        return _execute_resolve_decision(campaign, command, fingerprint)
    if command.kind == "retire":
        return _execute_retire(campaign, command, fingerprint)
    return _rejected(campaign, "unknown_command")
