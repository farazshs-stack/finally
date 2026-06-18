"""Shared fixtures for db tests.

Each test gets a fresh temporary database via the ``db_conn`` fixture.
The DATABASE_PATH env var is overridden so that init_db() writes to a
temp file rather than the real db/finally.db.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path

import pytest

from app.db.connection import get_connection
from app.db.init import init_db


@pytest.fixture()
def tmp_db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return a temp path and configure DATABASE_PATH to point at it."""
    db_file = tmp_path / "test_finally.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_file))
    return db_file


@pytest.fixture()
def initialized_db(tmp_db_path: Path) -> Path:
    """Run init_db() against the temp DB and return the path."""
    init_db()
    return tmp_db_path


@pytest.fixture()
def db_conn(initialized_db: Path) -> Generator[sqlite3.Connection, None, None]:
    """Open a connection to the initialized temp DB; auto-close after test."""
    conn = get_connection()
    yield conn
    conn.close()


@pytest.fixture()
def raw_conn(tmp_db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Open a connection to an *uninitialized* temp DB (no schema, no seed)."""
    conn = get_connection()
    yield conn
    conn.close()
