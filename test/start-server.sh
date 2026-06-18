#!/usr/bin/env bash
# Start the FinAlly backend for E2E testing
# Run from the project root (test/../)
set -e

# Resolve project root (one level up from test/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export DATABASE_PATH="$PROJECT_ROOT/test/.tmp/e2e.db"
export LLM_MOCK=true
export MASSIVE_API_KEY=

# Ensure .tmp directory exists and remove stale DB
mkdir -p "$PROJECT_ROOT/test/.tmp"
rm -f "$DATABASE_PATH"
echo "[start-server] Removed stale e2e.db (if any)"

cd "$PROJECT_ROOT/backend"
exec uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
