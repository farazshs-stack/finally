"""Repository sub-package — lightweight data-access functions for every table."""

from .chat import ChatMessage, insert_message, list_all_messages, list_recent_messages
from .positions import Position, delete_position, get_all_positions, get_position, upsert_position
from .profile import UserProfile, ensure_profile, get_cash_balance, get_profile, update_cash_balance
from .snapshots import PortfolioSnapshot, insert_snapshot, list_snapshots
from .trades import Trade, insert_trade, list_trades
from .watchlist import (
    WatchlistEntry,
    add_ticker,
    list_watchlist,
    remove_ticker,
    ticker_in_watchlist,
)

__all__ = [
    # Profile
    "UserProfile",
    "get_profile",
    "update_cash_balance",
    "get_cash_balance",
    "ensure_profile",
    # Watchlist
    "WatchlistEntry",
    "list_watchlist",
    "add_ticker",
    "remove_ticker",
    "ticker_in_watchlist",
    # Positions
    "Position",
    "get_all_positions",
    "get_position",
    "upsert_position",
    "delete_position",
    # Trades
    "Trade",
    "insert_trade",
    "list_trades",
    # Snapshots
    "PortfolioSnapshot",
    "insert_snapshot",
    "list_snapshots",
    # Chat
    "ChatMessage",
    "insert_message",
    "list_recent_messages",
    "list_all_messages",
]
