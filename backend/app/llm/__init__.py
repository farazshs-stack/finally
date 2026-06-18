"""FinAlly LLM integration package.

Public API
----------
    from app.llm import ChatResponse, call_llm, build_messages, get_mock_response
"""

from .client import call_llm
from .mock import get_mock_response
from .prompt import build_messages
from .schema import ChatResponse, TradeAction, WatchlistAction

__all__ = [
    "ChatResponse",
    "TradeAction",
    "WatchlistAction",
    "call_llm",
    "build_messages",
    "get_mock_response",
]
