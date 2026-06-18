#!/usr/bin/env bash
# ============================================================
# stop_mac.sh  — Stop the FinAlly container (macOS / Linux)
# The named volume (finally-data) is NOT removed — data persists.
# ============================================================
set -euo pipefail

CONTAINER_NAME="finally-app"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[FinAlly]${NC} $*"; }
warn() { echo -e "${YELLOW}[FinAlly]${NC} $*"; }

if docker ps -q --filter "name=^${CONTAINER_NAME}$" | grep -q .; then
    info "Stopping container '$CONTAINER_NAME' …"
    docker stop "$CONTAINER_NAME" >/dev/null
    info "Container stopped."
else
    warn "Container '$CONTAINER_NAME' is not running."
fi

if docker ps -aq --filter "name=^${CONTAINER_NAME}$" | grep -q .; then
    docker rm "$CONTAINER_NAME" >/dev/null
    info "Container removed."
fi

info "Done. Portfolio data is preserved in the 'finally-data' Docker volume."
