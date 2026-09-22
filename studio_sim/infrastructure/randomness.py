"""Stateless named SHA-256 random draws for the M1 kernel (K2).

There is no global RNG, wall clock or hidden draw counter: callers supply the
protocol seed, system, day, entity, purpose and an explicit ordinal.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

_PROTOCOL = "studio-rng-v1"
_ID_PATTERN = re.compile(r"[a-z][a-z0-9_-]{0,47}\Z")

_MAX_SEED = 2**64 - 1
_MAX_DAY = 36500
_MAX_ORDINAL = 2**32 - 1


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _valid_identifier(value: Any) -> bool:
    return isinstance(value, str) and _ID_PATTERN.match(value) is not None


def draw_u64(seed: int, system: str, day: int, entity: str, purpose: str, ordinal: int) -> int:
    """First eight big-endian SHA-256 bytes of the canonical named argument list."""
    if not _is_int(seed) or not 0 <= seed <= _MAX_SEED:
        raise ValueError("seed must be an integer 0..2**64-1")
    if not _valid_identifier(system):
        raise ValueError("system must match [a-z][a-z0-9_-]{0,47}")
    if not _is_int(day) or not 0 <= day <= _MAX_DAY:
        raise ValueError("day must be an integer 0..36500")
    if not _valid_identifier(entity):
        raise ValueError("entity must match [a-z][a-z0-9_-]{0,47}")
    if not _valid_identifier(purpose):
        raise ValueError("purpose must match [a-z][a-z0-9_-]{0,47}")
    if not _is_int(ordinal) or not 0 <= ordinal <= _MAX_ORDINAL:
        raise ValueError("ordinal must be an integer 0..2**32-1")
    material = json.dumps(
        [_PROTOCOL, seed, system, day, entity, purpose, ordinal],
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
