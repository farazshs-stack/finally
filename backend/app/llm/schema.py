"""Pydantic models for the LLM structured output (§9).

The LLM is instructed to respond with JSON matching the ChatResponse schema:

    {
        "message": "Your conversational response to the user",
        "trades": [
            {"ticker": "AAPL", "side": "buy", "quantity": 10}
        ],
        "watchlist_changes": [
            {"ticker": "PYPL", "action": "add"}
        ]
    }

- ``message``           required — conversational text shown to the user
- ``trades``            optional — auto-executed after validation
- ``watchlist_changes`` optional — add/remove from watchlist
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator


class TradeAction(BaseModel):
    """A single trade instruction from the LLM."""

    ticker: str
    side: Literal["buy", "sell"]
    quantity: float

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("quantity")
    @classmethod
    def positive_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("quantity must be greater than zero")
        return v


class WatchlistAction(BaseModel):
    """A single watchlist change instruction from the LLM."""

    ticker: str
    action: Literal["add", "remove"]

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.strip().upper()


class ChatResponse(BaseModel):
    """Top-level structured output schema from the LLM (§9).

    The LLM must always return valid JSON matching this model.
    """

    message: str
    trades: list[TradeAction] = []
    watchlist_changes: list[WatchlistAction] = []
