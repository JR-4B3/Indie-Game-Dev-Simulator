"""Serializable domain events with bounded live delivery and full history."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date as date_type, datetime
from enum import Enum
import math
from threading import local
from typing import Any


DEFAULT_LIVE_EVENT_LIMIT = 100
DEFAULT_EVENT_HISTORY_LIMIT = 500
_log_guard = local()


@dataclass
class DomainEvent:
    """A fact emitted by the simulation for UI and historical consumers."""

    event_id: int
    date: str
    kind: str
    severity: str
    message: str
    entity_type: str = ""
    entity_id: int | str | None = None
    data: dict[str, Any] = field(default_factory=dict)


def _json_value(value: Any) -> Any:
    """Convert common stdlib and domain values to JSON-compatible values."""
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (datetime, date_type)):
        return value.isoformat()
    if isinstance(value, Enum):
        return _json_value(value.value)
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_value(item) for item in value]
    return str(value)


def _date_text(state: Any, value: Any) -> str:
    if value is None:
        for name in ("current_date", "date"):
            if hasattr(state, name):
                value = getattr(state, name)
                if value is not None:
                    break
        else:
            clock = getattr(state, "clock", None)
            value = getattr(clock, "current_date", "") if clock is not None else ""
    if isinstance(value, (datetime, date_type)):
        return value.isoformat()
    return str(value) if value is not None else ""


def _event_value(event: Any, name: str, default: Any = None) -> Any:
    if isinstance(event, Mapping):
        return event.get(name, default)
    return getattr(event, name, default)


def _field_collections(state: Any, names: tuple[str, ...]) -> list[tuple[str, Any]]:
    result: list[tuple[str, Any]] = []
    seen: set[int] = set()
    for name in names:
        if not hasattr(state, name):
            continue
        collection = getattr(state, name)
        if collection is not None and id(collection) in seen:
            continue
        if collection is not None:
            seen.add(id(collection))
        result.append((name, collection))
    return result


def _append_record(state: Any, name: str, collection: Any, record: dict[str, Any]) -> Any:
    stored = _json_value(record)
    if collection is None:
        collection = [stored]
        setattr(state, name, collection)
        return collection
    append = getattr(collection, "append", None)
    if callable(append):
        append(stored)
        return collection
    try:
        collection = [*collection, stored]
    except TypeError as exc:
        raise TypeError(f"{name} must be an appendable collection") from exc
    setattr(state, name, collection)
    return collection


def _next_event_id(state: Any) -> int:
    highest = 0
    for _, collection in _field_collections(
        state,
        ("events", "live_events", "event_history", "events_history", "history"),
    ):
        for event in collection or ():
            value = _event_value(event, "event_id", 0)
            if isinstance(value, int) and not isinstance(value, bool):
                highest = max(highest, value)
    if hasattr(state, "next_event_id"):
        candidate = getattr(state, "next_event_id")
        if isinstance(candidate, int) and not isinstance(candidate, bool) and candidate > 0:
            return max(candidate, highest + 1)
    return highest + 1


def _live_limit(state: Any, requested: int | None) -> int:
    if requested is not None:
        return int(requested)
    for name in ("max_live_events", "event_limit", "max_events"):
        if hasattr(state, name):
            try:
                return int(getattr(state, name))
            except (TypeError, ValueError):
                continue
    return DEFAULT_LIVE_EVENT_LIMIT


def _send_to_log(state: Any, message: str) -> None:
    logger = getattr(state, "log", None)
    if not callable(logger):
        return
    active = getattr(_log_guard, "active_states", None)
    if active is None:
        active = set()
        _log_guard.active_states = active
    state_id = id(state)
    if state_id in active:
        return
    active.add(state_id)
    try:
        logger(message)
    finally:
        active.discard(state_id)


def emit_event(
    state: Any,
    kind: str,
    message: str,
    severity: str = "info",
    entity_type: str = "",
    entity_id: int | str | None = None,
    data: Mapping[str, Any] | None = None,
    *,
    date: Any = None,
    live_limit: int | None = None,
    log_message: bool = False,
    send_to_log: bool | None = None,
    log: bool | None = None,
) -> dict[str, Any]:
    """Emit an event to fields already supported by ``state``.

    ``events`` and ``live_events`` are bounded to ``live_limit`` (or a limit
    exposed by the state). ``event_history``, ``events_history``, and
    ``history`` are append-only.  Set ``log_message``, ``send_to_log``, or ``log`` to
    mirror the message through ``state.log``; a thread-local guard prevents a
    logging implementation from recursively logging the same call chain.
    """
    event_id = _next_event_id(state)
    event = DomainEvent(
        event_id=event_id,
        date=_date_text(state, date),
        kind=str(kind),
        severity=str(severity),
        message=str(message),
        entity_type=str(entity_type),
        entity_id=_json_value(entity_id),
        data=_json_value(dict(data or {})),
    )
    record = asdict(event)
    record["read"] = False

    limit = _live_limit(state, live_limit)
    live_collection_ids = {
        id(collection)
        for _, collection in _field_collections(state, ("events", "live_events"))
        if collection is not None
    }
    for name in ("event_history", "events_history", "history"):
        if not hasattr(state, name):
            continue
        history = getattr(state, name)
        if history is not None and id(history) in live_collection_ids:
            setattr(state, name, list(history))

    appended_collections: set[int] = set()
    for name, collection in _field_collections(state, ("events", "live_events")):
        live = _append_record(state, name, collection, record)
        appended_collections.add(id(live))
        if limit >= 0 and len(live) > limit:
            del live[: len(live) - limit]

    for name, collection in _field_collections(
        state,
        ("event_history", "events_history", "history"),
    ):
        if collection is not None and id(collection) in appended_collections:
            continue
        history = _append_record(state, name, collection, record)
        appended_collections.add(id(history))
        # Keep the full-history collection bounded so saves and memory do not
        # grow without limit over long campaigns.
        if isinstance(history, list) and len(history) > DEFAULT_EVENT_HISTORY_LIMIT:
            del history[: len(history) - DEFAULT_EVENT_HISTORY_LIMIT]

    if hasattr(state, "next_event_id"):
        setattr(state, "next_event_id", event_id + 1)
    should_log = log_message if send_to_log is None else send_to_log
    if log is not None:
        should_log = log
    if should_log:
        _send_to_log(state, event.message)
    return record


def _query_collection(state: Any, *, prefer_history: bool) -> Any:
    history_names = ("event_history", "events_history", "history")
    live_names = ("events", "live_events")
    names = history_names + live_names if prefer_history else live_names + history_names
    empty = None
    for _, collection in _field_collections(state, names):
        if collection:
            return collection
        if empty is None:
            empty = collection
    return empty or ()


def _last_read_id(state: Any) -> int:
    for name in ("last_read_event_id", "last_event_read_id"):
        if hasattr(state, name):
            value = getattr(state, name)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
    return 0


def unread_events(state: Any) -> list[dict[str, Any]]:
    """Return unread live events, falling back to history when needed."""
    marker = _last_read_id(state)
    result = []
    for event in _query_collection(state, prefer_history=False):
        event_id = _event_value(event, "event_id", 0)
        is_read = bool(_event_value(event, "read", _event_value(event, "is_read", False)))
        if not is_read and (not isinstance(event_id, int) or event_id > marker):
            result.append(event)
    return result


def events_for_entity(
    state: Any,
    entity_type: str,
    entity_id: int | str | None,
) -> list[dict[str, Any]]:
    """Return historical events associated with an entity."""
    return [
        event
        for event in _query_collection(state, prefer_history=True)
        if _event_value(event, "entity_type", "") == entity_type
        and _event_value(event, "entity_id") == entity_id
    ]


def _selected_event_ids(event_ids: Any) -> set[Any] | None:
    if event_ids is None:
        return None
    if isinstance(event_ids, (str, int)):
        return {event_ids}
    if isinstance(event_ids, Mapping):
        return {_event_value(event_ids, "event_id")}
    if hasattr(event_ids, "event_id"):
        return {_event_value(event_ids, "event_id")}
    try:
        values: Iterable[Any] = event_ids
        return {
            _event_value(value, "event_id")
            if isinstance(value, Mapping) or hasattr(value, "event_id")
            else value
            for value in values
        }
    except TypeError:
        return {event_ids}


def mark_events_read(state: Any, event_ids: Any = None) -> int:
    """Mark selected event IDs, or all events, read and return the count."""
    selected = _selected_event_ids(event_ids)
    changed_ids: set[Any] = set()
    for _, collection in _field_collections(
        state,
        ("events", "live_events", "event_history", "events_history", "history"),
    ):
        for event in collection or ():
            event_id = _event_value(event, "event_id")
            if selected is not None and event_id not in selected:
                continue
            if isinstance(event, dict):
                if not bool(event.get("read", event.get("is_read", False))):
                    changed_ids.add(event_id if event_id is not None else id(event))
                event["read"] = True
    for name in ("last_read_event_id", "last_event_read_id"):
        if not hasattr(state, name):
            continue
        current = getattr(state, name)
        if not isinstance(current, int) or isinstance(current, bool):
            current = 0
        events = sorted(
            (
                event
                for event in _query_collection(state, prefer_history=True)
                if isinstance(_event_value(event, "event_id"), int)
                and not isinstance(_event_value(event, "event_id"), bool)
                and _event_value(event, "event_id") > current
            ),
            key=lambda event: _event_value(event, "event_id"),
        )
        for event in events:
            if not bool(_event_value(event, "read", _event_value(event, "is_read", False))):
                break
            current = _event_value(event, "event_id")
        setattr(state, name, current)
    return len(changed_ids)


__all__ = [
    "DEFAULT_LIVE_EVENT_LIMIT",
    "DomainEvent",
    "emit_event",
    "events_for_entity",
    "mark_events_read",
    "unread_events",
]
