#!/usr/bin/env bash
# CoworkMem — Launch the local memory viewer
# Usage: bash run_coworkmem.sh [--port 4242] [--no-browser]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MEMORIES_DIR="$SCRIPT_DIR/memories"
SERVER="$SCRIPT_DIR/scripts/memory_server.py"
PORT="${CLAUDEMEM_PORT:-4242}"

# ── Check Python ──────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 is required but not found."
  exit 1
fi

# ── Ensure memories dir exists ────────────────────────────────────────────────
mkdir -p "$MEMORIES_DIR"

# ── Kill any existing instance on this port ───────────────────────────────────
if lsof -ti tcp:$PORT &>/dev/null 2>&1; then
  echo "Stopping existing server on port $PORT…"
  lsof -ti tcp:$PORT | xargs kill -9 2>/dev/null || true
  sleep 0.5
fi

# ── Launch server ─────────────────────────────────────────────────────────────
exec python3 "$SERVER" \
  --port "$PORT" \
  --memories-dir "$MEMORIES_DIR" \
  "$@"
