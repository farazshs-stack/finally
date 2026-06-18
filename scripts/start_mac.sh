#!/usr/bin/env bash
# ============================================================
# start_mac.sh  — Start the FinAlly container (macOS / Linux)
# Usage:
#   ./scripts/start_mac.sh          # build only if image missing
#   ./scripts/start_mac.sh --build  # force a fresh image build
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IMAGE_NAME="finally:latest"
CONTAINER_NAME="finally-app"
VOLUME_NAME="finally-data"
HOST_PORT=8000
APP_URL="http://localhost:${HOST_PORT}"

# ── Colour helpers ────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}[FinAlly]${NC} $*"; }
warn()    { echo -e "${YELLOW}[FinAlly]${NC} $*"; }
error()   { echo -e "${RED}[FinAlly]${NC} $*" >&2; }

# ── Preflight checks ─────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    error "Docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if [ ! -f "$PROJECT_ROOT/.env" ]; then
    warn ".env file not found. Copying from .env.example …"
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    warn "Please edit .env and set OPENROUTER_API_KEY before running the app."
fi

# ── Determine whether to build ───────────────────────────────
BUILD=false
if [[ "${1:-}" == "--build" ]]; then
    BUILD=true
elif ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
    info "Image '$IMAGE_NAME' not found — building now …"
    BUILD=true
fi

if [ "$BUILD" = true ]; then
    info "Building Docker image '$IMAGE_NAME' …"
    docker build -t "$IMAGE_NAME" "$PROJECT_ROOT"
    info "Build complete."
fi

# ── Stop any existing container (idempotent) ─────────────────
if docker ps -q --filter "name=^${CONTAINER_NAME}$" | grep -q .; then
    warn "Stopping existing container '$CONTAINER_NAME' …"
    docker stop "$CONTAINER_NAME" >/dev/null
    docker rm   "$CONTAINER_NAME" >/dev/null
fi
if docker ps -aq --filter "name=^${CONTAINER_NAME}$" | grep -q .; then
    docker rm "$CONTAINER_NAME" >/dev/null
fi

# ── Ensure named volume exists ───────────────────────────────
docker volume create "$VOLUME_NAME" >/dev/null

# ── Start container ──────────────────────────────────────────
info "Starting FinAlly …"
docker run \
    --detach \
    --name "$CONTAINER_NAME" \
    --publish "${HOST_PORT}:8000" \
    --volume "${VOLUME_NAME}:/app/db" \
    --env-file "$PROJECT_ROOT/.env" \
    --restart unless-stopped \
    "$IMAGE_NAME"

info "Container started. Waiting for health check …"

# Poll /api/health for up to 30 seconds
for i in $(seq 1 15); do
    if curl -sf "${APP_URL}/api/health" >/dev/null 2>&1; then
        break
    fi
    sleep 2
done

echo ""
info "FinAlly is running at: ${APP_URL}"
echo ""

# Optionally open browser (macOS: open; Linux: xdg-open if available)
if command -v open &>/dev/null; then
    open "$APP_URL"
elif command -v xdg-open &>/dev/null; then
    xdg-open "$APP_URL" &>/dev/null &
fi
