"""Repository for the chat_messages table.

Stores conversation history between the user and the LLM assistant.
The ``actions`` column stores a JSON-encoded dict of executed trades and
watchlist changes (None for user messages).
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Literal, TypedDict

from ..schema import DEFAULT_USER_ID
from ..utils import new_uuid, utc_now

ChatRole = Literal["user", "assistant"]


class ChatMessage(TypedDict):
    id: str
    user_id: str
    role: str           # "user" | "assistant"
    content: str
    actions: dict | None   # parsed from JSON; None for user messages
    created_at: str


def insert_message(
    conn: sqlite3.Connection,
    role: ChatRole,
    content: str,
    actions: dict[str, Any] | None = None,
    user_id: str = DEFAULT_USER_ID,
) -> ChatMessage:
    """Insert a chat message.

    Args:
        conn: Open SQLite connection.
        role: "user" or "assistant".
        content: Message text.
        actions: Dict of executed actions (trades, watchlist_changes) or None.
        user_id: User identifier.

    Returns:
        The inserted ChatMessage dict with actions already parsed back to dict.

    Raises:
        ValueError: If role is not "user" or "assistant".
    """
    if role not in ("user", "assistant"):
        raise ValueError(f"role must be 'user' or 'assistant', got {role!r}")

    msg_id = new_uuid()
    now = utc_now()
    actions_json = json.dumps(actions) if actions is not None else None

    conn.execute(
        """
        INSERT INTO chat_messages (id, user_id, role, content, actions, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (msg_id, user_id, role, content, actions_json, now),
    )

    return ChatMessage(
        id=msg_id,
        user_id=user_id,
        role=role,
        content=content,
        actions=actions,
        created_at=now,
    )


def list_recent_messages(
    conn: sqlite3.Connection,
    n: int = 20,
    user_id: str = DEFAULT_USER_ID,
) -> list[ChatMessage]:
    """Return the N most recent messages in chronological order (oldest first).

    This is what gets fed into the LLM context window.  Limiting to N guards
    against context overflow (§13.A.5 — conversation history window).

    Args:
        conn: Open SQLite connection.
        n: Number of most-recent messages to return (default 20).
        user_id: User identifier.

    Returns:
        List of ChatMessage dicts ordered oldest→newest, length ≤ n.
    """
    rows = conn.execute(
        """
        SELECT id, user_id, role, content, actions, created_at
        FROM (
            SELECT id, user_id, role, content, actions, created_at, rowid
            FROM chat_messages
            WHERE user_id = ?
            ORDER BY created_at DESC, rowid DESC
            LIMIT ?
        )
        ORDER BY created_at ASC, rowid ASC
        """,
        (user_id, n),
    ).fetchall()
    return [_row_to_message(r) for r in rows]


def list_all_messages(
    conn: sqlite3.Connection,
    user_id: str = DEFAULT_USER_ID,
) -> list[ChatMessage]:
    """Return all messages for a user in chronological order.

    Prefer ``list_recent_messages`` for LLM context; this is mainly for tests
    and admin tooling.
    """
    rows = conn.execute(
        """
        SELECT id, user_id, role, content, actions, created_at
        FROM chat_messages
        WHERE user_id = ?
        ORDER BY created_at ASC, rowid ASC
        """,
        (user_id,),
    ).fetchall()
    return [_row_to_message(r) for r in rows]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_message(row: sqlite3.Row) -> ChatMessage:
    actions_raw = row["actions"]
    actions = json.loads(actions_raw) if actions_raw is not None else None
    return ChatMessage(
        id=row["id"],
        user_id=row["user_id"],
        role=row["role"],
        content=row["content"],
        actions=actions,
        created_at=row["created_at"],
    )
