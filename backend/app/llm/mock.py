"""Deterministic mock LLM responses for testing (LLM_MOCK=true).

Public API
----------
    get_mock_response(user_message) -> ChatResponse

Deterministic rules (relied on by integration tests)
------------------------------------------------------
The mock inspects the *lower-cased* user message and matches the FIRST rule
that applies:

Rule 1 — BUY trade
  Pattern : message contains "buy" AND at least one known word that looks like
            a ticker (1-5 uppercase chars when extracted, or the word after "buy").
  Logic   : extract quantity (first integer in message, default 1) and
            ticker (first word after "buy", upper-cased, letters only).
  Response: message = "Buying <qty> <TICKER> as requested.",
            trades = [{"ticker": <TICKER>, "side": "buy", "quantity": <qty>}]

Rule 2 — SELL trade
  Same as Rule 1 but for "sell".
  Response: message = "Selling <qty> <TICKER> as requested.",
            trades = [{"ticker": <TICKER>, "side": "sell", "quantity": <qty>}]

Rule 3 — ADD watchlist
  Pattern : message contains "add" AND a word that looks like a ticker symbol
            (the first all-letter token that is NOT a common English stop-word
            and NOT the word "add" itself, length 1-10).
  Logic   : extract ticker = first word after "add" (upper-cased, letters only).
  Response: message = "Added <TICKER> to your watchlist.",
            watchlist_changes = [{"ticker": <TICKER>, "action": "add"}]

Rule 4 — REMOVE watchlist
  Pattern : message contains "remove" or "delete" AND a ticker-like token.
  Logic   : extract ticker = first word after "remove"/"delete" (upper-cased).
  Response: message = "Removed <TICKER> from your watchlist.",
            watchlist_changes = [{"ticker": <TICKER>, "action": "remove"}]

Rule 5 — Fallback (nothing matched)
  Response: message = "Your portfolio looks healthy. No action needed.",
            trades = [], watchlist_changes = []

Ticker extraction heuristic
----------------------------
After the keyword (buy/sell/add/remove/delete), take the next whitespace-
delimited token, strip non-alpha characters, upper-case it.  If the result is
empty or a stop-word, fall back to the first all-letter token of 1-10 chars in
the whole message that is not the keyword itself.

Stop-words (not treated as tickers): A, AN, THE, MY, YOUR, FROM, TO, ON, IN,
AT, FOR, WITH, AND, OR, NOT, SOME, ALL.

Quantity extraction
-------------------
First integer found anywhere in the message (regex ``r'\\d+'``).  Defaults to 1 if
no integer is present.
"""

from __future__ import annotations

import os
import re

from .schema import ChatResponse, TradeAction, WatchlistAction

# Words that should never be mistaken for ticker symbols
_STOP_WORDS: frozenset[str] = frozenset(
    {
        "A", "AN", "THE", "MY", "YOUR", "FROM", "TO", "ON", "IN", "AT",
        "FOR", "WITH", "AND", "OR", "NOT", "SOME", "ALL", "PLEASE", "ME",
        "IT", "IS", "DO", "BE", "BUY", "SELL", "ADD", "REMOVE", "DELETE",
    }
)


def _extract_quantity(text: str) -> float:
    """Return first integer in text as float, or 1.0 if none."""
    match = re.search(r"\d+", text)
    return float(match.group()) if match else 1.0


def _token_after_keyword(text_lower: str, keyword: str) -> str | None:
    """Return the token immediately following *keyword* in the lowercased text.

    Returns upper-cased alpha characters only (strips punctuation). None if
    no suitable token is found after the keyword.
    """
    pattern = rf"\b{re.escape(keyword)}\b\s+([A-Za-z]+)"
    m = re.search(pattern, text_lower)
    if m:
        candidate = re.sub(r"[^A-Za-z]", "", m.group(1)).upper()
        if candidate and candidate not in _STOP_WORDS:
            return candidate
    return None


def _fallback_ticker(text_lower: str, exclude: str) -> str | None:
    """Find the first all-letter token (1–10 chars) not in stop-words or exclude."""
    for token in re.findall(r"[A-Za-z]+", text_lower):
        candidate = token.upper()
        if candidate not in _STOP_WORDS and candidate != exclude.upper() and 1 <= len(candidate) <= 10:
            return candidate
    return None


def _is_mock_enabled() -> bool:
    return os.environ.get("LLM_MOCK", "").lower() == "true"


def get_mock_response(user_message: str) -> ChatResponse:
    """Return a deterministic mock ChatResponse (no network call).

    See module docstring for the exact matching rules.
    """
    text = user_message.lower()

    # Rule 1 — BUY
    if "buy" in text:
        qty = _extract_quantity(text)
        ticker = _token_after_keyword(text, "buy") or _fallback_ticker(text, "buy") or "AAPL"
        return ChatResponse(
            message=f"Buying {int(qty) if qty == int(qty) else qty} {ticker} as requested.",
            trades=[TradeAction(ticker=ticker, side="buy", quantity=qty)],
        )

    # Rule 2 — SELL
    if "sell" in text:
        qty = _extract_quantity(text)
        ticker = _token_after_keyword(text, "sell") or _fallback_ticker(text, "sell") or "AAPL"
        return ChatResponse(
            message=f"Selling {int(qty) if qty == int(qty) else qty} {ticker} as requested.",
            trades=[TradeAction(ticker=ticker, side="sell", quantity=qty)],
        )

    # Rule 3 — ADD watchlist
    if "add" in text:
        ticker = _token_after_keyword(text, "add") or _fallback_ticker(text, "add") or "PYPL"
        return ChatResponse(
            message=f"Added {ticker} to your watchlist.",
            watchlist_changes=[WatchlistAction(ticker=ticker, action="add")],
        )

    # Rule 4 — REMOVE / DELETE watchlist
    if "remove" in text or "delete" in text:
        keyword = "remove" if "remove" in text else "delete"
        ticker = (
            _token_after_keyword(text, keyword)
            or _fallback_ticker(text, keyword)
            or "NFLX"
        )
        return ChatResponse(
            message=f"Removed {ticker} from your watchlist.",
            watchlist_changes=[WatchlistAction(ticker=ticker, action="remove")],
        )

    # Rule 5 — Fallback
    return ChatResponse(message="Your portfolio looks healthy. No action needed.")
