"""Command envelope and result value types for the M1 kernel clock (K2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from ..domain.campaign import Campaign


@dataclass(frozen=True)
class Command:
    command_id: str
    expected_revision: int
    kind: str
    payload: Dict[str, Any]


@dataclass(frozen=True)
class CommandResult:
    campaign: Campaign
    accepted: bool
    code: str
    applied_revision: Optional[int]
    event_ids: Tuple[str, ...]
    duplicate: bool
