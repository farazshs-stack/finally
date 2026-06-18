"""Prompt builder for the FinAlly LLM chat assistant (§9).

Public API
----------
    build_messages(user_message, portfolio, watchlist_prices, history) -> list[dict]

The system prompt establishes "FinAlly, an AI trading assistant" persona.
Portfolio context (cash, positions w/ P&L, watchlist, total value) is injected
as a system-role context block immediately after the system prompt.
Recent conversation history (capped at 20 messages — §13.A.5) follows, then
the new user message.
"""

from __future__ import annotations

from app.db import ChatMessage
from app.services.portfolio import PortfolioData

# Maximum number of past messages included in each LLM call (§13.A.5).
# Older messages are silently dropped to stay within model context limits.
HISTORY_MESSAGE_CAP = 20

SYSTEM_PROMPT = """You are FinAlly, an expert AI trading assistant embedded in a \
live trading workstation. You have real-time access to the user's portfolio, cash \
balance, open positions, unrealized P&L, and watchlist prices.

Your responsibilities:
- Analyse portfolio composition, risk concentration, and unrealized P&L on request.
- Suggest trades with concise reasoning based on portfolio state.
- Execute trades immediately when the user asks you to buy or sell.
- Manage the watchlist proactively (add tickers the user mentions, remove ones they \
want gone).
- Be concise, data-driven, and professional — like a Bloomberg terminal copilot, not \
a chatbot.
- Never fabricate prices; always base analysis on the context provided.

Response format:
You MUST always respond with a single valid JSON object and nothing else. The schema is:
{
  "message": "<your conversational reply>",
  "trades": [{"ticker": "<SYMBOL>", "side": "buy"|"sell", "quantity": <number>}],
  "watchlist_changes": [{"ticker": "<SYMBOL>", "action": "add"|"remove"}]
}
Both "trades" and "watchlist_changes" are optional arrays (omit or use [] if none).
Do NOT wrap the JSON in markdown code fences. Do NOT add any text outside the JSON.
"""


def _format_portfolio_context(
    portfolio: PortfolioData,
    watchlist_prices: dict[str, float | None],
) -> str:
    """Render portfolio + watchlist into a concise text block for the LLM."""
    lines: list[str] = []
    lines.append("=== CURRENT PORTFOLIO CONTEXT ===")
    lines.append(f"Cash: ${portfolio['cash']:.2f}")
    lines.append(f"Total value: ${portfolio['total_value']:.2f}")
    lines.append(
        f"Total unrealized P&L: ${portfolio['total_unrealized_pnl']:.2f}"
    )

    positions = portfolio["positions"]
    if positions:
        lines.append("\nPositions:")
        for pos in positions:
            pnl_sign = "+" if pos["unrealized_pnl"] >= 0 else ""
            lines.append(
                f"  {pos['ticker']}: {pos['quantity']:.4f} shares @ avg cost "
                f"${pos['avg_cost']:.2f} | current ${pos['current_price']:.2f} | "
                f"P&L {pnl_sign}${pos['unrealized_pnl']:.2f} "
                f"({pnl_sign}{pos['pnl_percent']:.2f}%)"
            )
    else:
        lines.append("\nPositions: none")

    if watchlist_prices:
        lines.append("\nWatchlist (live prices):")
        for ticker, price in sorted(watchlist_prices.items()):
            price_str = f"${price:.2f}" if price is not None else "N/A"
            lines.append(f"  {ticker}: {price_str}")

    lines.append("=== END PORTFOLIO CONTEXT ===")
    return "\n".join(lines)


def build_messages(
    user_message: str,
    portfolio: PortfolioData,
    watchlist_prices: dict[str, float | None],
    history: list[ChatMessage],
) -> list[dict[str, str]]:
    """Construct the messages list for a LiteLLM completion call.

    Message layout:
    1. system: SYSTEM_PROMPT
    2. system: portfolio context block (injected as a second system message so
       it is always at the top of the model's attention)
    3. user/assistant: up to HISTORY_MESSAGE_CAP recent past messages
    4. user: the new user message

    Args:
        user_message:     The raw text the user just typed.
        portfolio:        Point-in-time portfolio from portfolio.get_portfolio().
        watchlist_prices: {ticker: price | None} for all watchlist tickers.
        history:          Recent messages from list_recent_messages() (chronological).
                          This function enforces the HISTORY_MESSAGE_CAP cap itself.

    Returns:
        A list of {"role": ..., "content": ...} dicts ready for litellm.completion.
    """
    messages: list[dict[str, str]] = []

    # 1. Main system prompt
    messages.append({"role": "system", "content": SYSTEM_PROMPT})

    # 2. Portfolio context as a second system message
    context = _format_portfolio_context(portfolio, watchlist_prices)
    messages.append({"role": "system", "content": context})

    # 3. Recent conversation history (cap to last HISTORY_MESSAGE_CAP entries)
    capped_history = history[-HISTORY_MESSAGE_CAP:]
    for msg in capped_history:
        role = msg["role"]  # "user" or "assistant"
        content = msg["content"]
        messages.append({"role": role, "content": content})

    # 4. New user message
    messages.append({"role": "user", "content": user_message})

    return messages
