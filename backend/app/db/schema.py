"""DDL statements for FinAlly's SQLite schema.

All tables include a user_id column defaulting to "default" to support a future
multi-user upgrade without a schema migration.
"""

# ---------------------------------------------------------------------------
# CREATE TABLE statements (IF NOT EXISTS — idempotent)
# ---------------------------------------------------------------------------

CREATE_USERS_PROFILE = """
CREATE TABLE IF NOT EXISTS users_profile (
    id           TEXT PRIMARY KEY,
    cash_balance REAL    NOT NULL DEFAULT 10000.0,
    created_at   TEXT    NOT NULL
)
"""

CREATE_WATCHLIST = """
CREATE TABLE IF NOT EXISTS watchlist (
    id       TEXT PRIMARY KEY,
    user_id  TEXT NOT NULL DEFAULT 'default',
    ticker   TEXT NOT NULL,
    added_at TEXT NOT NULL,
    UNIQUE (user_id, ticker)
)
"""

CREATE_POSITIONS = """
CREATE TABLE IF NOT EXISTS positions (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL DEFAULT 'default',
    ticker     TEXT NOT NULL,
    quantity   REAL NOT NULL,
    avg_cost   REAL NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (user_id, ticker)
)
"""

CREATE_TRADES = """
CREATE TABLE IF NOT EXISTS trades (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL DEFAULT 'default',
    ticker      TEXT NOT NULL,
    side        TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    quantity    REAL NOT NULL,
    price       REAL NOT NULL,
    executed_at TEXT NOT NULL
)
"""

CREATE_PORTFOLIO_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL DEFAULT 'default',
    total_value REAL NOT NULL,
    recorded_at TEXT NOT NULL
)
"""

CREATE_CHAT_MESSAGES = """
CREATE TABLE IF NOT EXISTS chat_messages (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL DEFAULT 'default',
    role       TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content    TEXT NOT NULL,
    actions    TEXT,
    created_at TEXT NOT NULL
)
"""

# Ordered list — execute in sequence to respect any future FK dependencies
ALL_DDL: list[str] = [
    CREATE_USERS_PROFILE,
    CREATE_WATCHLIST,
    CREATE_POSITIONS,
    CREATE_TRADES,
    CREATE_PORTFOLIO_SNAPSHOTS,
    CREATE_CHAT_MESSAGES,
]

# ---------------------------------------------------------------------------
# Default seed data
# ---------------------------------------------------------------------------

DEFAULT_USER_ID = "default"
DEFAULT_CASH_BALANCE = 10_000.0

DEFAULT_TICKERS: list[str] = [
    "AAPL",
    "GOOGL",
    "MSFT",
    "AMZN",
    "TSLA",
    "NVDA",
    "META",
    "JPM",
    "V",
    "NFLX",
]
