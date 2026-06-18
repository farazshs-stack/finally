"""Utility helpers shared across the db package."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def new_uuid() -> str:
    """Return a new UUID4 string."""
    return str(uuid.uuid4())


def utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Rounding helpers (§13.B.3 — avoid float drift)
# ---------------------------------------------------------------------------

_MONEY_PLACES = 6  # sub-cent precision for intermediate math; display rounds to 2
_QTY_PLACES = 6  # fractional shares to 6 decimal places


def round_money(value: float) -> float:
    """Round a monetary value to 6 decimal places (storage precision).

    Display layers should further round to 2 d.p. for human presentation, but
    storing 6 d.p. prevents compounding drift across repeated buy/sell cycles.
    """
    return round(value, _MONEY_PLACES)


def round_qty(value: float) -> float:
    """Round a share quantity to 6 decimal places."""
    return round(value, _QTY_PLACES)


def display_money(value: float) -> float:
    """Round money to 2 decimal places for display / comparison."""
    return round(value, 2)
