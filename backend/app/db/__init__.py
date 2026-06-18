"""FinAlly database package.

Public API
----------

Initialisation
~~~~~~~~~~~~~~
    from app.db import init_db, get_connection

    init_db()                        # call once at startup (idempotent)
    with get_connection() as conn:   # per-operation connection
        ...

Path helpers
~~~~~~~~~~~~
    from app.db import get_db_path   # returns resolved Path to the .db file

Rounding helpers  (§13.B.3)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    from app.db import round_money, round_qty, display_money

Repository functions
~~~~~~~~~~~~~~~~~~~~
    from app.db import (
        # Profile
        get_profile, update_cash_balance, get_cash_balance, ensure_profile,
        # Watchlist
        list_watchlist, add_ticker, remove_ticker, ticker_in_watchlist,
        # Positions
        get_all_positions, get_position, upsert_position, delete_position,
        # Trades
        insert_trade, list_trades,
        # Snapshots
        insert_snapshot, list_snapshots,
        # Chat
        insert_message, list_recent_messages, list_all_messages,
    )

TypedDicts (for type hints in callers)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    from app.db import (
        UserProfile, WatchlistEntry, Position, Trade,
        PortfolioSnapshot, ChatMessage,
    )
"""

from .connection import get_connection, get_db_path
from .init import init_db
from .repositories import (
    # TypedDicts
    ChatMessage,
    PortfolioSnapshot,
    Position,
    Trade,
    UserProfile,
    WatchlistEntry,
    # Watchlist
    add_ticker,
    # Positions
    delete_position,
    # Profile
    ensure_profile,
    get_all_positions,
    get_cash_balance,
    get_position,
    get_profile,
    # Chat
    insert_message,
    # Snapshots
    insert_snapshot,
    # Trades
    insert_trade,
    list_all_messages,
    list_recent_messages,
    list_snapshots,
    list_trades,
    list_watchlist,
    remove_ticker,
    ticker_in_watchlist,
    update_cash_balance,
    upsert_position,
)
from .utils import display_money, round_money, round_qty

__all__ = [
    # Initialisation
    "init_db",
    "get_connection",
    "get_db_path",
    # Rounding
    "round_money",
    "round_qty",
    "display_money",
    # TypedDicts
    "UserProfile",
    "WatchlistEntry",
    "Position",
    "Trade",
    "PortfolioSnapshot",
    "ChatMessage",
    # Profile
    "get_profile",
    "update_cash_balance",
    "get_cash_balance",
    "ensure_profile",
    # Watchlist
    "list_watchlist",
    "add_ticker",
    "remove_ticker",
    "ticker_in_watchlist",
    # Positions
    "get_all_positions",
    "get_position",
    "upsert_position",
    "delete_position",
    # Trades
    "insert_trade",
    "list_trades",
    # Snapshots
    "insert_snapshot",
    "list_snapshots",
    # Chat
    "insert_message",
    "list_recent_messages",
    "list_all_messages",
]
