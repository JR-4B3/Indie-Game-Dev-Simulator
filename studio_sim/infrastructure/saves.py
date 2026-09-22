"""Strict K1 snapshot codec and crash-safe local save store (M1-K1 K4, WP-03).

This module is an independent dictionary-to-bytes codec and Linux filesystem
repository. It imports no domain/application module: callers hand it exact K1
snapshot dictionaries. Standard library only.

Public API (frozen by K4):

    class SaveError(Exception): code: str
    encode(payload: dict) -> bytes
    decode(data: bytes) -> dict
    SaveStore(root: pathlib.Path)
        save(payload) -> None
        load(campaign_id, source="primary") -> dict
        recover_backup(campaign_id) -> pathlib.Path
        invalidate_failed(payload) -> None

Decode order: UTF-8/JSON strictness (``invalid_json``/``too_large``), envelope
exactness (``invalid_payload``), format/version
(``unsupported_format``/``unsupported_version``), complete strict K1 payload
validation (``invalid_payload``), then the digest claim (``integrity``). The
payload itself is therefore always validated with precise errors; a stale
digest over an otherwise valid payload is the only ``integrity`` failure.

Failure inference rule: I/O errors never infer an Ironman failure. Only a
validated failed/insolvent Ironman payload may write the permanent
non-resumable failure marker; missing or unreadable marker files never create
one, and corrupt files are never deleted or rewritten to signal failure.
"""

from __future__ import annotations

import errno
import datetime
import fcntl
import hashlib
import json
import os
import pathlib
import re
import stat
import tempfile
from contextlib import contextmanager

__all__ = ["SaveError", "encode", "decode", "SaveStore"]

FORMAT_ID = "studio-rewrite"
SCHEMA_VERSION = 1
FAILURE_FORMAT_ID = "studio-rewrite-failure"
FAILURE_SCHEMA_VERSION = 1
RULESET_ID = "m1-kernel-1"
SIMULATION_VERSION = 1

MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024
MAX_MONEY_MINOR = 10 ** 12
MAX_MONTHLY_DRAW_MINOR = 10 ** 9
MAX_REVISION = 10 ** 9
MAX_DAY = 36500
MAX_SEED = 2 ** 64 - 1

MAX_DECISIONS = 64
MAX_RECEIPTS = 64
MAX_EVENTS = 8192
MAX_POSTINGS = 8192
MAX_OBLIGATIONS = 512
MAX_LABOR = 4096

PRIMARY_NAME = "autosave.studio.json"
BACKUP_NAME = "autosave.studio.json.bak"
RECOVERY_NAME = "recovery.studio.json"
LOCK_NAME = ".lock"
FAILURE_MARKER_NAME = "failed.json"

_SOURCE_FILES = {
    "primary": PRIMARY_NAME,
    "backup": BACKUP_NAME,
    "recovery": RECOVERY_NAME,
}

_ID_RE = re.compile(r"[a-z][a-z0-9_-]{0,47}\Z")
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")
_EVENT_ID_RE = re.compile(r"e-[1-9][0-9]*\Z")
_POSTING_ID_RE = re.compile(r"p-[1-9][0-9]*\Z")

_SNAPSHOT_KEYS = frozenset(
    {
        "campaign_id",
        "start_date",
        "seed",
        "simulation_version",
        "ruleset_id",
        "mode",
        "day",
        "revision",
        "status",
        "closed_reason",
        "manual_paused",
        "next_event_id",
        "events",
        "decisions",
        "receipts",
        "finance",
    }
)
_DECISION_KEYS = frozenset({"id", "due_day", "reason", "resolved"})
_EVENT_KEYS = frozenset({"id", "day", "kind", "source", "subject_id", "facts"})
_RECEIPT_KEYS = frozenset(
    {"command_id", "fingerprint", "applied_revision", "event_ids"}
)
_FINANCE_KEYS = frozenset(
    {
        "opening_cash_minor",
        "cash_minor",
        "monthly_draw_minor",
        "negative_since_day",
        "next_posting_id",
        "postings",
        "obligations",
        "labor",
    }
)
_POSTING_KEYS = frozenset(
    {"id", "day", "category", "amount_minor", "source", "product_id"}
)
_OBLIGATION_KEYS = frozenset(
    {"id", "due_day", "category", "amount_minor", "product_id", "paid"}
)
_LABOR_KEYS = frozenset({"posting_id", "product_id", "amount_minor"})
_ENVELOPE_KEYS = frozenset({"format_id", "schema_version", "payload", "sha256"})
_MARKER_KEYS = frozenset(
    {
        "format_id",
        "schema_version",
        "campaign_id",
        "mode",
        "revision",
        "day",
        "reason",
    }
)

_EVENT_KINDS = (
    "pause_changed",
    "decision_resolved",
    "campaign_closed",
    "cash_posted",
    "obligation_added",
    "labor_attributed",
    "liquidity_warning",
)
_FACTS_KEYS = {
    "pause_changed": frozenset({"paused"}),
    "decision_resolved": frozenset(),
    "campaign_closed": frozenset({"reason"}),
    "cash_posted": frozenset({"posting_id"}),
    "obligation_added": frozenset(),
    "labor_attributed": frozenset({"posting_id", "amount_minor"}),
    "liquidity_warning": frozenset({"negative_since_day"}),
}
_POSTING_CATEGORIES = ("income", "expense", "draw", "financing")
_OBLIGATION_CATEGORIES = ("income", "expense", "financing")

# Decode-time failures of an existing snapshot file (as opposed to path/IO
# failures). Used to translate a corrupt primary into ``corrupt_primary``.
_SNAPSHOT_DECODE_CODES = frozenset(
    {
        "invalid_payload",
        "invalid_json",
        "unsupported_format",
        "unsupported_version",
        "integrity",
        "too_large",
    }
)


class SaveError(Exception):
    """Save failure with a frozen K4 ``code`` attribute."""

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        text = code if not message else f"{code}: {message}"
        super().__init__(text)


# ---------------------------------------------------------------------------
# Canonical JSON and envelope
# ---------------------------------------------------------------------------


def _canonical_json_bytes(value) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, RecursionError):
        raise SaveError("invalid_payload", "value is not canonical JSON") from None


def _envelope_document(payload: dict) -> tuple[bytes, bytes]:
    """Returns (canonical payload bytes, canonical envelope bytes)."""
    canonical = _canonical_json_bytes(payload)
    document = {
        "format_id": FORMAT_ID,
        "schema_version": SCHEMA_VERSION,
        "payload": payload,
        "sha256": hashlib.sha256(canonical).hexdigest(),
    }
    return canonical, _canonical_json_bytes(document)


def _encode_validated(payload: dict) -> tuple[bytes, bytes]:
    canonical, envelope = _envelope_document(payload)
    if len(envelope) > MAX_SNAPSHOT_BYTES:
        raise SaveError("too_large", "serialized save exceeds 4 MiB")
    return canonical, envelope


def encode(payload: dict) -> bytes:
    """Validates a complete K1 snapshot and returns canonical envelope bytes."""
    _validate_snapshot(payload)
    return _encode_validated(payload)[1]


def decode(data: bytes) -> dict:
    """Strictly validates canonical-or-equivalent envelope bytes to a snapshot."""
    document = _parse_json_document(data)
    if not isinstance(document, dict):
        _invalid("envelope", "expected an object")
    _exact_keys(document, _ENVELOPE_KEYS, "envelope")
    format_id = document["format_id"]
    if not isinstance(format_id, str):
        _invalid("envelope.format_id", "expected text")
    if format_id != FORMAT_ID:
        raise SaveError("unsupported_format", f"unsupported format_id {format_id!r}")
    version = document["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int):
        _invalid("envelope.schema_version", "expected an integer")
    if version != SCHEMA_VERSION:
        raise SaveError("unsupported_version", f"unsupported schema_version {version!r}")
    payload = document["payload"]
    _validate_snapshot(payload)
    declared = document["sha256"]
    if not isinstance(declared, str) or _HEX64_RE.match(declared) is None:
        _invalid("envelope.sha256", "expected 64 lowercase hex digits")
    canonical = _canonical_json_bytes(payload)
    if hashlib.sha256(canonical).hexdigest() != declared:
        raise SaveError("integrity", "payload digest does not match envelope")
    return payload


# ---------------------------------------------------------------------------
# Strict JSON parsing
# ---------------------------------------------------------------------------


def _parse_json_document(data):
    if isinstance(data, (bytes, bytearray, memoryview)):
        raw = bytes(data)
    else:
        raise SaveError("invalid_json", "save data must be bytes")
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise SaveError("too_large", "serialized input exceeds 4 MiB")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise SaveError("invalid_json", "input is not valid UTF-8") from None
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except SaveError:
        raise
    except (ValueError, RecursionError):
        raise SaveError("invalid_json", "input is not strict JSON") from None


def _reject_duplicate_keys(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise SaveError("invalid_json", f"duplicate key {key!r}")
        seen[key] = value
    return seen


def _reject_json_constant(value):
    raise SaveError("invalid_json", f"invalid JSON literal {value!r}")


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _invalid(where: str, problem: str):
    raise SaveError("invalid_payload", f"{where}: {problem}")


def _exact_keys(value, expected, where: str) -> None:
    if not isinstance(value, dict):
        _invalid(where, "expected an object")
    if set(value.keys()) != expected:
        _invalid(where, "unexpected, missing or non-string field")


def _strict_int(value, low: int, high: int, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _invalid(where, "expected an integer (booleans and floats are invalid)")
    if value < low or value > high:
        _invalid(where, f"out of range {low}..{high}")
    return value


def _strict_bool(value, where: str) -> bool:
    if not isinstance(value, bool):
        _invalid(where, "expected a boolean")
    return value


def _text(value, where: str, low: int = 1, high: int = 160) -> str:
    if not isinstance(value, str):
        _invalid(where, "expected text")
    if len(value) < low or len(value) > high:
        _invalid(where, f"length must be {low}..{high}")
    if "\x00" in value:
        _invalid(where, "NUL is not allowed")
    return value


def _identifier(value, where: str) -> str:
    if not isinstance(value, str) or _ID_RE.match(value) is None:
        _invalid(where, "invalid identifier")
    return value


def _optional_identifier(value, where: str):
    if value is None:
        return None
    return _identifier(value, where)


def _calendar_date(value, where: str) -> datetime.date:
    if not isinstance(value, str) or _DATE_RE.match(value) is None:
        _invalid(where, "expected an ISO YYYY-MM-DD date")
    try:
        parsed = datetime.date.fromisoformat(value)
    except ValueError:
        _invalid(where, "not a valid calendar date")
    if parsed.year < 2000 or parsed.year > 2199:
        _invalid(where, "start year must be 2000..2199")
    return parsed


def _enum(value, allowed, where: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        _invalid(where, f"expected one of {allowed}")
    return value


def _list_of(value, where: str) -> list:
    if not isinstance(value, list):
        _invalid(where, "expected a list")
    return value


def _canonical_event_id(value, where: str) -> str:
    if not isinstance(value, str) or _EVENT_ID_RE.match(value) is None:
        _invalid(where, "expected canonical e-N reference")
    return value


def _canonical_posting_id(value, where: str) -> str:
    if not isinstance(value, str) or _POSTING_ID_RE.match(value) is None:
        _invalid(where, "expected canonical p-N reference")
    return value


def _parse_source(value, where: str):
    """Returns (kind, value) for cmd/obligation/draw/tick/clock sources."""
    if not isinstance(value, str):
        _invalid(where, "expected source text")
    if value == "tick":
        return ("tick", None)
    if value == "clock":
        return ("clock", None)
    if value.startswith("cmd:"):
        return ("cmd", _identifier(value[4:], where))
    if value.startswith("obligation:"):
        return ("obligation", _identifier(value[11:], where))
    if value.startswith("draw:"):
        return ("draw", _calendar_date(value[5:], where))
    _invalid(where, "unknown source")


def _check_money_sign(category: str, amount_minor: int, where: str) -> None:
    if category == "income":
        if amount_minor <= 0:
            _invalid(where, "income must be positive")
    elif category == "expense":
        if amount_minor >= 0:
            _invalid(where, "expense must be negative")
    elif category == "draw":
        if amount_minor >= 0:
            _invalid(where, "draw must be negative")
    else:  # financing
        if amount_minor == 0:
            _invalid(where, "financing must be nonzero")


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (datetime.date(year, month + 1, 1) - datetime.date(year, month, 1)).days


def _founder_draw_charge(monthly_draw_minor: int, derived: datetime.date) -> int:
    length = _days_in_month(derived.year, derived.month)
    n = derived.day
    return (monthly_draw_minor * n) // length - (monthly_draw_minor * (n - 1)) // length


# ---------------------------------------------------------------------------
# K1 snapshot validation
# ---------------------------------------------------------------------------


def _validate_snapshot(payload) -> None:
    if not isinstance(payload, dict):
        _invalid("snapshot", "expected an object")
    _exact_keys(payload, _SNAPSHOT_KEYS, "snapshot")
    campaign_id = _identifier(payload["campaign_id"], "snapshot.campaign_id")
    start_date = _calendar_date(payload["start_date"], "snapshot.start_date")
    _strict_int(payload["seed"], 0, MAX_SEED, "snapshot.seed")
    _strict_int(
        payload["simulation_version"],
        SIMULATION_VERSION,
        SIMULATION_VERSION,
        "snapshot.simulation_version",
    )
    _enum(payload["ruleset_id"], (RULESET_ID,), "snapshot.ruleset_id")
    mode = _enum(payload["mode"], ("normal", "ironman"), "snapshot.mode")
    day = _strict_int(payload["day"], 0, MAX_DAY, "snapshot.day")
    revision = _strict_int(payload["revision"], 0, MAX_REVISION, "snapshot.revision")
    status = _enum(payload["status"], ("running", "retired", "failed"), "snapshot.status")
    closed_reason = payload["closed_reason"]
    if closed_reason is not None and closed_reason not in ("retired", "insolvent"):
        _invalid("snapshot.closed_reason", "expected null, 'retired' or 'insolvent'")
    manual_paused = _strict_bool(payload["manual_paused"], "snapshot.manual_paused")
    next_event_id = _strict_int(
        payload["next_event_id"], 1, MAX_EVENTS + 1, "snapshot.next_event_id"
    )

    decisions = _validate_decisions(payload["decisions"], day)
    events = _validate_events(payload["events"], day)
    receipts = _validate_receipts(payload["receipts"], revision)
    finance = _validate_finance(payload["finance"], start_date, day)

    if next_event_id != len(events) + 1:
        _invalid("snapshot.next_event_id", "must equal len(events) + 1")
    if finance["next_posting_id"] != len(finance["postings"]) + 1:
        _invalid("finance.next_posting_id", "must equal len(postings) + 1")

    _cross_validate(
        campaign_id=campaign_id,
        start_date=start_date,
        mode=mode,
        day=day,
        status=status,
        closed_reason=closed_reason,
        manual_paused=manual_paused,
        decisions=decisions,
        events=events,
        receipts=receipts,
        finance=finance,
    )


def _validate_decisions(raw, day: int) -> list:
    decisions = _list_of(raw, "snapshot.decisions")
    if len(decisions) > MAX_DECISIONS:
        _invalid("snapshot.decisions", f"at most {MAX_DECISIONS} allowed")
    seen = set()
    for index, decision in enumerate(decisions):
        where = f"decisions[{index}]"
        _exact_keys(decision, _DECISION_KEYS, where)
        decision_id = _identifier(decision["id"], f"{where}.id")
        due_day = _strict_int(decision["due_day"], 0, MAX_DAY, f"{where}.due_day")
        _text(decision["reason"], f"{where}.reason")
        resolved = _strict_bool(decision["resolved"], f"{where}.resolved")
        if decision_id in seen:
            _invalid(f"{where}.id", "duplicate decision id")
        seen.add(decision_id)
        if resolved and due_day > day:
            _invalid(where, "resolved decision is due after the current day")
    identifiers = [decision["id"] for decision in decisions]
    if identifiers != sorted(identifiers):
        _invalid("snapshot.decisions", "must be sorted by id")
    return decisions


def _validate_events(raw, day: int) -> list:
    events = _list_of(raw, "snapshot.events")
    if len(events) > MAX_EVENTS:
        _invalid("snapshot.events", f"at most {MAX_EVENTS} allowed")
    previous_day = -1
    for index, event in enumerate(events, start=1):
        where = f"events[{index - 1}]"
        _exact_keys(event, _EVENT_KEYS, where)
        if event["id"] != f"e-{index}":
            _invalid(f"{where}.id", "must be canonical and contiguous from e-1")
        event_day = _strict_int(event["day"], 0, MAX_DAY, f"{where}.day")
        if event_day > day:
            _invalid(f"{where}.day", "after the current day")
        if event_day < previous_day:
            _invalid(f"{where}.day", "events must be in creation order")
        previous_day = event_day
        kind = _enum(event["kind"], _EVENT_KINDS, f"{where}.kind")
        source_kind, source_value = _parse_source(event["source"], f"{where}.source")
        subject = event["subject_id"]
        if subject is not None:
            _identifier(subject, f"{where}.subject_id")
        facts = event["facts"]
        _exact_keys(facts, _FACTS_KEYS[kind], f"{where}.facts")

        if kind == "pause_changed":
            _strict_bool(facts["paused"], f"{where}.facts.paused")
            if source_kind != "cmd" or subject is not None:
                _invalid(where, "pause_changed requires cmd source and null subject")
        elif kind == "decision_resolved":
            if source_kind != "cmd":
                _invalid(where, "decision_resolved requires a cmd source")
            if subject is None:
                _invalid(where, "decision_resolved requires a decision subject")
        elif kind == "campaign_closed":
            reason = _enum(facts["reason"], ("retired", "insolvent"), f"{where}.facts.reason")
            if subject is not None:
                _invalid(where, "campaign_closed requires a null subject")
            if reason == "retired":
                if source_kind != "cmd":
                    _invalid(where, "voluntary retirement requires a cmd source")
            elif event["source"] != "tick":
                _invalid(where, "insolvency requires a tick source")
        elif kind == "cash_posted":
            _canonical_posting_id(facts["posting_id"], f"{where}.facts.posting_id")
            if subject is not None:
                _invalid(where, "cash_posted requires a null subject")
            if source_kind not in ("cmd", "obligation", "draw"):
                _invalid(where, "cash_posted source must be a posting source")
        elif kind == "obligation_added":
            if source_kind != "cmd":
                _invalid(where, "obligation_added requires a cmd source")
            if subject is None:
                _invalid(where, "obligation_added requires an obligation subject")
        elif kind == "labor_attributed":
            if source_kind != "cmd":
                _invalid(where, "labor_attributed requires a cmd source")
            if subject is None:
                _invalid(where, "labor_attributed requires a product subject")
            _canonical_posting_id(facts["posting_id"], f"{where}.facts.posting_id")
            _strict_int(facts["amount_minor"], 1, MAX_MONEY_MINOR, f"{where}.facts.amount_minor")
        else:  # liquidity_warning
            if event["source"] != "tick":
                _invalid(where, "liquidity_warning requires a tick source")
            if subject is not None:
                _invalid(where, "liquidity_warning requires a null subject")
            start = _strict_int(
                facts["negative_since_day"], 1, MAX_DAY, f"{where}.facts.negative_since_day"
            )
            if start != event_day:
                _invalid(where, "warning must start on its own event day")
    return events


def _validate_receipts(raw, revision: int) -> list:
    receipts = _list_of(raw, "snapshot.receipts")
    if len(receipts) > MAX_RECEIPTS:
        _invalid("snapshot.receipts", f"at most {MAX_RECEIPTS} allowed")
    seen = set()
    previous_revision = 0
    for index, receipt in enumerate(receipts):
        where = f"receipts[{index}]"
        _exact_keys(receipt, _RECEIPT_KEYS, where)
        command_id = _identifier(receipt["command_id"], f"{where}.command_id")
        if command_id in seen:
            _invalid(f"{where}.command_id", "duplicate receipt id")
        seen.add(command_id)
        fingerprint = receipt["fingerprint"]
        if not isinstance(fingerprint, str) or _HEX64_RE.match(fingerprint) is None:
            _invalid(f"{where}.fingerprint", "expected 64 lowercase hex digits")
        applied = _strict_int(
            receipt["applied_revision"], 1, MAX_REVISION, f"{where}.applied_revision"
        )
        if applied > revision:
            _invalid(f"{where}.applied_revision", "ahead of the campaign revision")
        if applied <= previous_revision:
            _invalid(f"{where}.applied_revision", "must strictly increase in list order")
        previous_revision = applied
        event_ids = _list_of(receipt["event_ids"], f"{where}.event_ids")
        for event_index, event_id in enumerate(event_ids):
            _canonical_event_id(event_id, f"{where}.event_ids[{event_index}]")
    return receipts


def _validate_postings(raw, day: int) -> list:
    postings = _list_of(raw, "finance.postings")
    if len(postings) > MAX_POSTINGS:
        _invalid("finance.postings", f"at most {MAX_POSTINGS} allowed")
    previous_day = -1
    for index, posting in enumerate(postings, start=1):
        where = f"postings[{index - 1}]"
        _exact_keys(posting, _POSTING_KEYS, where)
        if posting["id"] != f"p-{index}":
            _invalid(f"{where}.id", "must be canonical and contiguous from p-1")
        posting_day = _strict_int(posting["day"], 0, MAX_DAY, f"{where}.day")
        if posting_day > day:
            _invalid(f"{where}.day", "after the current day")
        if posting_day < previous_day:
            _invalid(f"{where}.day", "postings must be in creation order")
        previous_day = posting_day
        category = _enum(posting["category"], _POSTING_CATEGORIES, f"{where}.category")
        amount = _strict_int(
            posting["amount_minor"], -MAX_MONEY_MINOR, MAX_MONEY_MINOR, f"{where}.amount_minor"
        )
        _check_money_sign(category, amount, where)
        _parse_source(posting["source"], f"{where}.source")
        _optional_identifier(posting["product_id"], f"{where}.product_id")
    return postings


def _validate_obligations(raw, day: int) -> list:
    obligations = _list_of(raw, "finance.obligations")
    if len(obligations) > MAX_OBLIGATIONS:
        _invalid("finance.obligations", f"at most {MAX_OBLIGATIONS} allowed")
    seen = set()
    for index, obligation in enumerate(obligations):
        where = f"obligations[{index}]"
        _exact_keys(obligation, _OBLIGATION_KEYS, where)
        obligation_id = _identifier(obligation["id"], f"{where}.id")
        if obligation_id in seen:
            _invalid(f"{where}.id", "duplicate obligation id")
        seen.add(obligation_id)
        due_day = _strict_int(obligation["due_day"], 0, MAX_DAY, f"{where}.due_day")
        category = _enum(
            obligation["category"], _OBLIGATION_CATEGORIES, f"{where}.category"
        )
        amount = _strict_int(
            obligation["amount_minor"],
            -MAX_MONEY_MINOR,
            MAX_MONEY_MINOR,
            f"{where}.amount_minor",
        )
        _check_money_sign(category, amount, where)
        _optional_identifier(obligation["product_id"], f"{where}.product_id")
        paid = _strict_bool(obligation["paid"], f"{where}.paid")
        if paid and due_day > day:
            _invalid(where, "paid obligation is due after the current day")
        if not paid and due_day <= day:
            _invalid(where, "unpaid obligation must be due after the current day")
    identifiers = [obligation["id"] for obligation in obligations]
    if identifiers != sorted(identifiers):
        _invalid("finance.obligations", "must be sorted by id")
    return obligations


def _validate_labor(raw) -> list:
    labor = _list_of(raw, "finance.labor")
    if len(labor) > MAX_LABOR:
        _invalid("finance.labor", f"at most {MAX_LABOR} allowed")
    seen = set()
    for index, entry in enumerate(labor):
        where = f"labor[{index}]"
        _exact_keys(entry, _LABOR_KEYS, where)
        posting_id = _canonical_posting_id(entry["posting_id"], f"{where}.posting_id")
        product_id = _identifier(entry["product_id"], f"{where}.product_id")
        _strict_int(entry["amount_minor"], 1, MAX_MONEY_MINOR, f"{where}.amount_minor")
        key = (posting_id, product_id)
        if key in seen:
            _invalid(where, "duplicate (posting_id, product_id) allocation")
        seen.add(key)
    return labor


def _validate_finance(raw, start_date: datetime.date, day: int) -> dict:
    _exact_keys(raw, _FINANCE_KEYS, "finance")
    opening_cash = _strict_int(
        raw["opening_cash_minor"], 0, MAX_MONEY_MINOR, "finance.opening_cash_minor"
    )
    cash = _strict_int(
        raw["cash_minor"], -MAX_MONEY_MINOR, MAX_MONEY_MINOR, "finance.cash_minor"
    )
    monthly_draw = _strict_int(
        raw["monthly_draw_minor"], 0, MAX_MONTHLY_DRAW_MINOR, "finance.monthly_draw_minor"
    )
    negative_since_day = raw["negative_since_day"]
    if negative_since_day is not None:
        negative_since_day = _strict_int(
            negative_since_day, 1, MAX_DAY, "finance.negative_since_day"
        )
    next_posting_id = _strict_int(
        raw["next_posting_id"], 1, MAX_POSTINGS + 1, "finance.next_posting_id"
    )
    postings = _validate_postings(raw["postings"], day)
    obligations = _validate_obligations(raw["obligations"], day)
    labor = _validate_labor(raw["labor"])

    total = opening_cash
    for posting in postings:
        total += posting["amount_minor"]
    if total != cash:
        _invalid("finance.cash_minor", "cash does not equal opening plus postings")
    return {
        "opening_cash_minor": opening_cash,
        "cash_minor": cash,
        "monthly_draw_minor": monthly_draw,
        "negative_since_day": negative_since_day,
        "next_posting_id": next_posting_id,
        "postings": postings,
        "obligations": obligations,
        "labor": labor,
    }


def _cross_validate(
    *,
    campaign_id: str,
    start_date: datetime.date,
    mode: str,
    day: int,
    status: str,
    closed_reason,
    manual_paused: bool,
    decisions: list,
    events: list,
    receipts: list,
    finance: dict,
) -> None:
    del campaign_id, mode  # already validated; kept for an explicit seam
    postings = finance["postings"]
    obligations = finance["obligations"]
    labor = finance["labor"]
    cash = finance["cash_minor"]
    monthly_draw = finance["monthly_draw_minor"]
    negative_since_day = finance["negative_since_day"]

    posting_index = {posting["id"]: posting for posting in postings}
    obligation_index = {obligation["id"]: obligation for obligation in obligations}
    decision_index = {decision["id"]: decision for decision in decisions}
    event_index = {event["id"]: event for event in events}

    for receipt in receipts:
        for event_id in receipt["event_ids"]:
            if event_id not in event_index:
                _invalid("receipts", f"unknown event reference {event_id!r}")

    allocations = {}
    for entry in labor:
        posting = posting_index.get(entry["posting_id"])
        if posting is None:
            _invalid("labor", f"unknown posting {entry['posting_id']!r}")
        if posting["category"] != "expense":
            _invalid("labor", "labor may only target expense postings")
        allocations[entry["posting_id"]] = (
            allocations.get(entry["posting_id"], 0) + entry["amount_minor"]
        )
    for posting_id, allocated in allocations.items():
        if allocated > abs(posting_index[posting_id]["amount_minor"]):
            _invalid("labor", "allocation exceeds the posting amount")

    draw_dates = set()
    obligation_postings = {}
    for posting in postings:
        source_kind, source_value = _parse_source(posting["source"], "posting.source")
        if source_kind in ("tick", "clock"):
            _invalid("posting.source", "postings require a cmd/obligation/draw source")
        if source_kind == "obligation":
            obligation_postings.setdefault(source_value, []).append(posting)
        if posting["category"] == "draw":
            if source_kind != "draw":
                _invalid("posting", "only draw sources may use the draw category")
            if posting["day"] == 0:
                _invalid("posting", "no founder draw posting on day 0")
            if posting["product_id"] is not None:
                _invalid("posting", "draw posting cannot be attributed to a product")
            derived = start_date + datetime.timedelta(days=posting["day"])
            if source_value != derived:
                _invalid("posting.source", "draw source date must equal the derived date")
            expected = _founder_draw_charge(monthly_draw, derived)
            if posting["amount_minor"] != -expected:
                _invalid("posting.amount_minor", "does not match the founder draw formula")
            if derived in draw_dates:
                _invalid("posting", "at most one draw posting per date")
            draw_dates.add(derived)
        elif source_kind == "draw":
            _invalid("posting", "draw source requires the draw category")
        elif posting["category"] == "income" and source_kind == "obligation":
            pass  # settlement shape checked below
        if source_kind == "cmd" and posting["category"] == "draw":
            _invalid("posting", "immediate postings cannot use the draw category")

    for obligation in obligations:
        matches = obligation_postings.get(obligation["id"], [])
        if obligation["paid"]:
            if len(matches) != 1:
                _invalid(
                    "obligations",
                    f"paid obligation {obligation['id']!r} needs exactly one posting",
                )
            posting = matches[0]
            if (
                posting["category"] != obligation["category"]
                or posting["amount_minor"] != obligation["amount_minor"]
                or posting["product_id"] != obligation["product_id"]
                or posting["day"] != obligation["due_day"]
            ):
                _invalid("obligations", "settlement posting does not match obligation")
        elif matches:
            _invalid("obligations", "unpaid obligation must not have a settlement posting")
    for obligation_id in obligation_postings:
        if obligation_id not in obligation_index:
            _invalid("obligations", f"unknown obligation source {obligation_id!r}")

    resolved_decisions = set()
    posted_references = {}
    closed_events = []
    warning_starts = []
    last_pause_value = None
    for event in events:
        kind = event["kind"]
        facts = event["facts"]
        if kind == "pause_changed":
            last_pause_value = facts["paused"]
        elif kind == "decision_resolved":
            subject = event["subject_id"]
            if subject not in decision_index:
                _invalid("events", f"unknown decision subject {subject!r}")
            resolved_decisions.add(subject)
        elif kind == "campaign_closed":
            closed_events.append(event)
        elif kind == "cash_posted":
            posting = posting_index.get(facts["posting_id"])
            if posting is None:
                _invalid("events", "cash_posted references an unknown posting")
            if event["source"] != posting["source"] or event["day"] != posting["day"]:
                _invalid("events", "cash_posted must share source and day with its posting")
            posted_references.setdefault(posting["id"], []).append(event)
        elif kind == "obligation_added":
            subject = event["subject_id"]
            if subject not in obligation_index:
                _invalid("events", f"unknown obligation subject {subject!r}")
        elif kind == "labor_attributed":
            posting_id = facts["posting_id"]
            product_id = event["subject_id"]
            amount = facts["amount_minor"]
            matched = any(
                entry["posting_id"] == posting_id
                and entry["product_id"] == product_id
                and entry["amount_minor"] == amount
                for entry in labor
            )
            if not matched:
                _invalid("events", "labor_attributed has no matching LABOR entry")
        else:  # liquidity_warning
            warning_starts.append(facts["negative_since_day"])

    for posting in postings:
        references = posted_references.get(posting["id"], [])
        if len(references) != 1:
            _invalid("events", f"posting {posting['id']!r} needs exactly one cash_posted")

    for decision in decisions:
        if decision["resolved"] != (decision["id"] in resolved_decisions):
            _invalid("decisions", "resolved flag does not match decision_resolved events")

    if last_pause_value is None:
        if manual_paused:
            _invalid("manual_paused", "paused state has no matching pause_changed event")
    elif last_pause_value != manual_paused:
        _invalid("manual_paused", "must equal the latest pause_changed value")

    if status == "running":
        if closed_reason is not None:
            _invalid("closed_reason", "running campaigns have a null reason")
        if closed_events:
            _invalid("events", "running campaign must not carry campaign_closed")
    else:
        expected_reason = "retired" if status == "retired" else "insolvent"
        if closed_reason != expected_reason:
            _invalid("closed_reason", "does not match status")
        if len(closed_events) != 1:
            _invalid("events", "closed campaign needs exactly one campaign_closed event")
        if closed_events[0]["facts"]["reason"] != expected_reason:
            _invalid("events", "campaign_closed reason does not match status")

    if (cash < 0) != (negative_since_day is not None):
        _invalid("negative_since_day", "must be set exactly while cash is negative")
    if negative_since_day is not None:
        if negative_since_day > day:
            _invalid("negative_since_day", "after the current day")
        if status == "running" and day - negative_since_day + 1 >= 7:
            _invalid("negative_since_day", "running campaign cannot hold seven negative days")
        if status == "failed" and day - negative_since_day + 1 < 7:
            _invalid("negative_since_day", "failed campaign needs seven negative days")

    for index in range(1, len(warning_starts)):
        if warning_starts[index] <= warning_starts[index - 1]:
            _invalid("events", "liquidity warnings must start strictly increasing episodes")
    if negative_since_day is not None:
        if not warning_starts or warning_starts[-1] != negative_since_day:
            _invalid("events", "current negative episode has no matching warning")


# ---------------------------------------------------------------------------
# Filesystem primitives
# ---------------------------------------------------------------------------


def _lstat(path):
    try:
        return os.lstat(str(path))
    except FileNotFoundError:
        return None
    except OSError:
        return None


def _reject_symlink(path: pathlib.Path, where: str = "path") -> None:
    info = _lstat(path)
    if info is not None and stat.S_ISLNK(info.st_mode):
        raise SaveError("unsafe_path", f"{where} may not be a symlink: {path}")


def _reject_symlink_components(path: pathlib.Path) -> None:
    for component in [path, *path.parents]:
        _reject_symlink(component, "path component")


def _require_campaign_id(campaign_id) -> str:
    if not isinstance(campaign_id, str) or _ID_RE.match(campaign_id) is None:
        raise SaveError("unsafe_path", "campaign id must match [a-z][a-z0-9_-]{0,47}")
    return campaign_id


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while len(view):
        written = os.write(fd, view)
        if written <= 0:
            raise OSError(errno.EIO, "write made no progress")
        view = view[written:]


def _close_quietly(fd: int) -> None:
    try:
        os.close(fd)
    except OSError:
        pass


def _unlink_quietly(path: pathlib.Path) -> None:
    try:
        os.unlink(str(path))
    except OSError:
        pass


def _read_file_bytes(path: pathlib.Path) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(str(path), flags)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise SaveError("unsafe_path", f"refusing to follow symlink: {path}") from None
        raise SaveError("io", f"cannot open {path}: {exc}") from None
    chunks = []
    total = 0
    try:
        size = os.fstat(fd).st_size
        if size > MAX_SNAPSHOT_BYTES:
            raise SaveError("too_large", "serialized input exceeds 4 MiB")
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_SNAPSHOT_BYTES:
                raise SaveError("too_large", "serialized input exceeds 4 MiB")
            chunks.append(chunk)
    except OSError as exc:
        raise SaveError("io", f"cannot read {path}: {exc}") from None
    finally:
        _close_quietly(fd)
    return b"".join(chunks)


def _fsync_directory(directory: pathlib.Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    fd = os.open(str(directory), flags)
    try:
        os.fsync(fd)
    finally:
        _close_quietly(fd)


def _write_verified_temp(directory: pathlib.Path, name: str, data: bytes, verify):
    try:
        fd, raw_path = tempfile.mkstemp(
            prefix=f".{name}.tmp.", suffix=".part", dir=str(directory)
        )
    except OSError as exc:
        raise SaveError("io", f"cannot create temporary save file: {exc}") from None
    path = pathlib.Path(raw_path)
    try:
        _write_all(fd, data)
        os.fsync(fd)
    except OSError as exc:
        _close_quietly(fd)
        _unlink_quietly(path)
        raise SaveError("io", f"cannot write temporary save file: {exc}") from None
    try:
        os.close(fd)
    except OSError as exc:
        _unlink_quietly(path)
        raise SaveError("io", f"cannot close temporary save file: {exc}") from None
    try:
        on_disk = _read_file_bytes(path)
        if on_disk != data:
            raise SaveError("io", "temporary save file does not match written bytes")
        verify(on_disk)
    except SaveError:
        _unlink_quietly(path)
        raise
    except OSError as exc:
        _unlink_quietly(path)
        raise SaveError("io", f"cannot verify temporary save file: {exc}") from None
    return path


def _verify_envelope(expected_payload):
    def check(raw: bytes) -> None:
        decoded = decode(raw)
        if decoded != expected_payload:
            raise SaveError("io", "temporary envelope payload mismatch")

    return check


def _replace(source: pathlib.Path, target: pathlib.Path) -> None:
    os.replace(str(source), str(target))


# ---------------------------------------------------------------------------
# SaveStore
# ---------------------------------------------------------------------------


class SaveStore:
    """Campaign-scoped save repository under a trusted root directory."""

    def __init__(self, root) -> None:
        root = pathlib.Path(root)
        _reject_symlink_components(root)
        if root.exists():
            if not root.is_dir():
                raise SaveError("unsafe_path", f"save root is not a directory: {root}")
        else:
            try:
                root.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise SaveError("io", f"cannot create save root: {exc}") from None
        self._root = root

    # -- paths and locks ---------------------------------------------------

    def _campaign_directory(self, campaign_id: str, create: bool) -> pathlib.Path:
        directory = self._root / campaign_id
        _reject_symlink(directory, "campaign directory")
        if directory.exists():
            if not directory.is_dir():
                raise SaveError("unsafe_path", f"campaign path is not a directory: {directory}")
            return directory
        if not create:
            raise SaveError("not_found", f"campaign {campaign_id!r} has no save directory")
        try:
            directory.mkdir()
        except FileExistsError:
            if not directory.is_dir():
                raise SaveError("unsafe_path", f"campaign path is not a directory: {directory}")
        except OSError as exc:
            raise SaveError("io", f"cannot create campaign directory: {exc}") from None
        return directory

    @contextmanager
    def _locked(self, campaign_directory: pathlib.Path, exclusive: bool):
        lock_path = campaign_directory / LOCK_NAME
        _reject_symlink(lock_path, "lock file")
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(str(lock_path), flags, 0o600)
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise SaveError("unsafe_path", f"lock file may not be a symlink: {lock_path}") from None
            raise SaveError("io", f"cannot open lock file: {exc}") from None
        try:
            operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            try:
                fcntl.flock(fd, operation | fcntl.LOCK_NB)
            except OSError as exc:
                if exc.errno in (errno.EACCES, errno.EAGAIN):
                    raise SaveError("conflict", "another process holds the campaign lock") from None
                raise SaveError("io", f"cannot lock campaign: {exc}") from None
            yield
        finally:
            _close_quietly(fd)

    # -- reads -------------------------------------------------------------

    def _read_marker(self, campaign_directory: pathlib.Path, campaign_id: str):
        path = campaign_directory / FAILURE_MARKER_NAME
        _reject_symlink(path, "failure marker")
        if not path.exists():
            return None
        try:
            raw = _read_file_bytes(path)
        except SaveError:
            raise
        try:
            return _validate_marker_bytes(raw, campaign_id)
        except SaveError:
            raise SaveError("integrity", "failure marker is malformed") from None

    def _read_validated_file(
        self, path: pathlib.Path, campaign_id: str, mode=None
    ) -> dict:
        _reject_symlink(path, "save file")
        if not path.exists():
            raise SaveError("not_found", f"save file does not exist: {path.name}")
        payload = decode(_read_file_bytes(path))
        if payload["campaign_id"] != campaign_id:
            raise SaveError("ownership", "save file belongs to another campaign")
        if mode is not None and payload["mode"] != mode:
            raise SaveError("ownership", "save file mode cannot change")
        return payload

    # -- save --------------------------------------------------------------

    def save(self, payload: dict) -> None:
        _validate_snapshot(payload)
        campaign_id = payload["campaign_id"]
        if payload["mode"] == "ironman" and payload["status"] == "failed":
            self.invalidate_failed(payload)
            return
        canonical, envelope = _encode_validated(payload)
        revision = payload["revision"]
        mode = payload["mode"]

        campaign_directory = self._campaign_directory(campaign_id, create=True)
        with self._locked(campaign_directory, exclusive=True):
            if self._read_marker(campaign_directory, campaign_id) is not None:
                raise SaveError("ironman_failed", "campaign was invalidated by Ironman failure")

            primary_path = campaign_directory / PRIMARY_NAME
            backup_path = campaign_directory / BACKUP_NAME
            _reject_symlink(primary_path, "primary save file")

            primary_payload = None
            if primary_path.exists():
                try:
                    primary_payload = self._read_validated_file(primary_path, campaign_id, mode)
                except SaveError as exc:
                    if exc.code in _SNAPSHOT_DECODE_CODES:
                        raise SaveError(
                            "corrupt_primary",
                            "existing primary is corrupt; backup left untouched",
                        ) from None
                    raise
            backup_payload = None
            if primary_payload is None:
                _reject_symlink(backup_path, "backup save file")
                if backup_path.exists():
                    try:
                        backup_payload = self._read_validated_file(backup_path, campaign_id, mode)
                    except SaveError as exc:
                        if exc.code in _SNAPSHOT_DECODE_CODES:
                            backup_payload = None
                        else:
                            raise

            if primary_payload is not None:
                primary_revision = primary_payload["revision"]
                if revision < primary_revision:
                    raise SaveError("conflict", "incoming revision is older than primary")
                if revision == primary_revision:
                    if canonical == _canonical_json_bytes(primary_payload):
                        return  # identical payload at identical revision: idempotent no-op
                    raise SaveError("conflict", "same revision with different payload")
            elif backup_payload is not None:
                backup_revision = backup_payload["revision"]
                if revision < backup_revision:
                    raise SaveError("conflict", "incoming revision is older than backup")
                if revision == backup_revision and canonical != _canonical_json_bytes(backup_payload):
                    raise SaveError("conflict", "same revision with different payload")

            self._commit_primary(
                campaign_directory,
                primary_path,
                backup_path,
                envelope,
                payload,
                primary_payload,
            )

    def _commit_primary(
        self,
        campaign_directory: pathlib.Path,
        primary_path: pathlib.Path,
        backup_path: pathlib.Path,
        envelope: bytes,
        payload: dict,
        primary_payload,
    ) -> None:
        pending = []
        try:
            new_primary_temp = _write_verified_temp(
                campaign_directory, PRIMARY_NAME, envelope, _verify_envelope(payload)
            )
            pending.append(new_primary_temp)
            if primary_payload is not None:
                _, backup_envelope = _envelope_document(primary_payload)
                backup_temp = _write_verified_temp(
                    campaign_directory,
                    BACKUP_NAME,
                    backup_envelope,
                    _verify_envelope(primary_payload),
                )
                pending.append(backup_temp)
                _replace(backup_temp, backup_path)
                pending.remove(backup_temp)
                _fsync_directory(campaign_directory)
            _replace(new_primary_temp, primary_path)
            pending.remove(new_primary_temp)
        except OSError as exc:
            raise SaveError("io", f"save write failed before commit: {exc}") from None
        finally:
            for temp_path in pending:
                _unlink_quietly(temp_path)
        try:
            _fsync_directory(campaign_directory)
        except OSError as exc:
            raise SaveError(
                "durability_uncertain",
                "primary replaced but directory sync failed; inspect primary and backup",
            ) from None

    # -- public reads ------------------------------------------------------

    def load(self, campaign_id: str, source: str = "primary") -> dict:
        campaign_id = _require_campaign_id(campaign_id)
        filename = _SOURCE_FILES.get(source) if isinstance(source, str) else None
        if filename is None:
            raise SaveError("unsafe_path", f"unknown save source {source!r}")
        campaign_directory = self._campaign_directory(campaign_id, create=False)
        with self._locked(campaign_directory, exclusive=False):
            if self._read_marker(campaign_directory, campaign_id) is not None:
                raise SaveError("ironman_failed", "campaign was invalidated by Ironman failure")
            return self._read_validated_file(campaign_directory / filename, campaign_id)

    def recover_backup(self, campaign_id: str) -> pathlib.Path:
        campaign_id = _require_campaign_id(campaign_id)
        campaign_directory = self._campaign_directory(campaign_id, create=False)
        with self._locked(campaign_directory, exclusive=True):
            if self._read_marker(campaign_directory, campaign_id) is not None:
                raise SaveError("ironman_failed", "campaign was invalidated by Ironman failure")
            backup_payload = self._read_validated_file(
                campaign_directory / BACKUP_NAME, campaign_id
            )
            _, envelope = _encode_validated(backup_payload)
            target = campaign_directory / RECOVERY_NAME
            _reject_symlink(target, "recovery file")
            self._create_recovery(campaign_directory, target, envelope, backup_payload)
            return target

    def _create_recovery(
        self,
        campaign_directory: pathlib.Path,
        target: pathlib.Path,
        envelope: bytes,
        backup_payload: dict,
    ) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(str(target), flags, 0o600)
        except FileExistsError:
            raise SaveError("conflict", "recovery file already exists") from None
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise SaveError("unsafe_path", f"recovery file may not be a symlink: {target}") from None
            raise SaveError("io", f"cannot create recovery file: {exc}") from None
        try:
            _write_all(fd, envelope)
            os.fsync(fd)
        except OSError as exc:
            _close_quietly(fd)
            _unlink_quietly(target)
            raise SaveError("io", f"cannot write recovery file: {exc}") from None
        try:
            os.close(fd)
        except OSError as exc:
            _unlink_quietly(target)
            raise SaveError("io", f"cannot close recovery file: {exc}") from None
        try:
            on_disk = _read_file_bytes(target)
            if on_disk != envelope or decode(on_disk) != backup_payload:
                raise SaveError("io", "recovery file failed verification")
        except SaveError:
            _unlink_quietly(target)
            raise
        except OSError as exc:
            _unlink_quietly(target)
            raise SaveError("io", f"cannot verify recovery file: {exc}") from None
        try:
            _fsync_directory(campaign_directory)
        except OSError as exc:
            raise SaveError(
                "durability_uncertain",
                "recovery file written but directory sync failed; inspect recovery file",
            ) from None

    # -- Ironman invalidation ---------------------------------------------

    def invalidate_failed(self, payload: dict) -> None:
        _validate_snapshot(payload)
        if payload["mode"] != "ironman" or payload["status"] != "failed":
            raise SaveError(
                "invalid_payload",
                "only a validated failed Ironman snapshot may invalidate its save set",
            )
        campaign_id = payload["campaign_id"]
        marker = {
            "format_id": FAILURE_FORMAT_ID,
            "schema_version": FAILURE_SCHEMA_VERSION,
            "campaign_id": campaign_id,
            "mode": "ironman",
            "revision": payload["revision"],
            "day": payload["day"],
            "reason": "insolvent",
        }
        marker_bytes = _canonical_json_bytes(marker)

        campaign_directory = self._campaign_directory(campaign_id, create=True)
        with self._locked(campaign_directory, exclusive=True):
            existing = self._read_marker(campaign_directory, campaign_id)
            if existing is not None:
                if _canonical_json_bytes(existing) == marker_bytes:
                    return  # identical marker: idempotent
                raise SaveError("conflict", "a different failure marker already exists")

            revision_floor = 0
            for name in (PRIMARY_NAME, BACKUP_NAME):
                path = campaign_directory / name
                _reject_symlink(path, "save file")
                if not path.exists():
                    continue
                try:
                    owned = self._read_validated_file(path, campaign_id, "ironman")
                except SaveError as exc:
                    if exc.code in _SNAPSHOT_DECODE_CODES:
                        continue  # a corrupt file is not proof of failure
                    raise
                revision_floor = max(revision_floor, owned["revision"])
            if payload["revision"] < revision_floor:
                raise SaveError("conflict", "failure marker revision is behind an owned snapshot")

            temp = _write_verified_temp(
                campaign_directory,
                FAILURE_MARKER_NAME,
                marker_bytes,
                _marker_verifier(campaign_id),
            )
            try:
                _replace(temp, campaign_directory / FAILURE_MARKER_NAME)
            except OSError as exc:
                _unlink_quietly(temp)
                raise SaveError("io", f"cannot write failure marker: {exc}") from None
            try:
                _fsync_directory(campaign_directory)
            except OSError as exc:
                raise SaveError(
                    "durability_uncertain",
                    "failure marker replaced but directory sync failed; inspect failed.json",
                ) from None


def _validate_marker_bytes(raw: bytes, campaign_id: str) -> dict:
    document = _parse_json_document(raw)
    if not isinstance(document, dict):
        _invalid("failure marker", "expected an object")
    _exact_keys(document, _MARKER_KEYS, "failure marker")
    if document["format_id"] != FAILURE_FORMAT_ID:
        _invalid("failure marker.format_id", "unexpected format")
    version = document["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int) or version != FAILURE_SCHEMA_VERSION:
        _invalid("failure marker.schema_version", "unsupported marker version")
    if _identifier(document["campaign_id"], "failure marker.campaign_id") != campaign_id:
        _invalid("failure marker.campaign_id", "belongs to another campaign")
    if document["mode"] != "ironman":
        _invalid("failure marker.mode", "marker mode must be ironman")
    if document["reason"] != "insolvent":
        _invalid("failure marker.reason", "marker reason must be insolvent")
    _strict_int(document["revision"], 0, MAX_REVISION, "failure marker.revision")
    _strict_int(document["day"], 0, MAX_DAY, "failure marker.day")
    return document


def _marker_verifier(campaign_id: str):
    def check(raw: bytes) -> None:
        _validate_marker_bytes(raw, campaign_id)

    return check
