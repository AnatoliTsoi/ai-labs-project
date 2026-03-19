#!/usr/bin/env bash
# dev.sh — start backend (port 8000) and frontend (port 5173) for local development

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$REPO_ROOT/hotel-concierge"
FRONTEND_DIR="$REPO_ROOT/frontend"
BACKEND_PORT=8000
FRONTEND_PORT=5173
PIDS=()

# ── colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RESET='\033[0m'

log()  { echo -e "${GREEN}[dev]${RESET} $*"; }
warn() { echo -e "${YELLOW}[dev]${RESET} $*"; }
err()  { echo -e "${RED}[dev]${RESET} $*" >&2; }

# ── port check ────────────────────────────────────────────────────────────────
port_in_use() {
  lsof -ti :"$1" >/dev/null 2>&1
}

kill_port() {
  local port=$1
  local pids
  pids=$(lsof -ti :"$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    warn "Port $port is busy (PIDs: $pids). Killing..."
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 0.5
  fi
}

# ── cleanup on exit ───────────────────────────────────────────────────────────
cleanup() {
  echo ""
  log "Shutting down..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  log "Done."
}
trap cleanup EXIT INT TERM

# ── arg parsing ───────────────────────────────────────────────────────────────
FORCE=false
for arg in "$@"; do
  case $arg in
    --force|-f) FORCE=true ;;
    --help|-h)
      echo "Usage: $0 [--force]"
      echo "  --force   kill processes on busy ports instead of prompting"
      exit 0 ;;
  esac
done

# ── port handling ─────────────────────────────────────────────────────────────
for port in $BACKEND_PORT $FRONTEND_PORT; do
  if port_in_use "$port"; then
    if $FORCE; then
      kill_port "$port"
    else
      read -r -p "$(echo -e "${YELLOW}Port $port is busy. Kill existing process? [y/N]:${RESET} ")" answer
      if [[ "$answer" =~ ^[Yy]$ ]]; then
        kill_port "$port"
      else
        err "Port $port is in use. Aborting. Use --force to kill automatically."
        exit 1
      fi
    fi
  fi
done

# ── backend ───────────────────────────────────────────────────────────────────
VENV="$BACKEND_DIR/.venv"
if [[ ! -d "$VENV" ]]; then
  err "Virtualenv not found at $VENV. Run: python -m venv $VENV && pip install -e '$BACKEND_DIR[dev]'"
  exit 1
fi

log "Starting backend on http://localhost:$BACKEND_PORT ..."
(
  cd "$BACKEND_DIR"
  source "$VENV/bin/activate"
  uvicorn concierge.server:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    --reload \
    2>&1 | sed 's/^/[backend] /'
) &
PIDS+=($!)

# ── frontend ──────────────────────────────────────────────────────────────────
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  warn "node_modules not found — installing dependencies..."
  (cd "$FRONTEND_DIR" && bun install)
fi

log "Starting frontend on http://localhost:$FRONTEND_PORT ..."
(
  cd "$FRONTEND_DIR"
  bun run dev 2>&1 | sed 's/^/[frontend] /'
) &
PIDS+=($!)

# ── ready ─────────────────────────────────────────────────────────────────────
log "Both services starting. Press Ctrl+C to stop."
echo ""
echo -e "  Backend:  ${GREEN}http://localhost:$BACKEND_PORT${RESET}"
echo -e "  Frontend: ${GREEN}http://localhost:$FRONTEND_PORT${RESET}"
echo ""

wait
