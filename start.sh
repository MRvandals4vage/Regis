#!/usr/bin/env bash
# start.sh — Launch Regis: Python brain + Electron UI together
# Usage: bash start.sh

set -e

# ── Environment Setup ─────────────────────────────────────────────────────────
# Ensure Homebrew's bin is on PATH (needed for npm/node on macOS)
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

# Get absolute paths to handle spaces in directory names
ROOT="$(cd "$(dirname "$0")" && pwd)"
BRAIN="$ROOT/ai_assistant"
UI="$ROOT/assistant-ui"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

printf "\n${BOLD}${CYAN}╔══════════════════════════════════════╗${NC}\n"
printf "${BOLD}${CYAN}║        🧠  Regis Launcher             ║${NC}\n"
printf "${BOLD}${CYAN}╚══════════════════════════════════════╝${NC}\n\n"

# ── Check venv ────────────────────────────────────────────────────────────────
if [ ! -d "$BRAIN/.venv" ]; then
  printf "${YELLOW}⚙️  Creating Python virtual environment…${NC}\n"
  python3 -m venv "$BRAIN/.venv"
fi

PYTHON="$BRAIN/.venv/bin/python"
PIP="$BRAIN/.venv/bin/pip"

# ── Install Python deps ───────────────────────────────────────────────────────
printf "${YELLOW}📦 Checking Python dependencies…${NC}\n"
"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet faster-whisper sounddevice numpy pyautogui Pillow requests

# ── Install Node deps ─────────────────────────────────────────────────────────
if [ ! -d "$UI/node_modules" ]; then
  printf "${YELLOW}📦 Installing Node dependencies…${NC}\n"
  cd "$UI" && npm install
fi

# ── Kill any stale server on port 8000 ───────────────────────────────────────
OLD_PID=$(lsof -ti:8000 2>/dev/null || true)
if [ -n "$OLD_PID" ]; then
  printf "${YELLOW}🔪 Stopping old server (PID $OLD_PID)…${NC}\n"
  kill -9 "$OLD_PID" 2>/dev/null || true
  sleep 1
fi

# ── Start Python brain ────────────────────────────────────────────────────────
printf "${GREEN}🧠 Starting Regis Brain (server.py)…${NC}\n"
cd "$BRAIN"
"$PYTHON" server.py &
BRAIN_PID=$!
printf "   Brain PID: ${BOLD}$BRAIN_PID${NC}\n"

# Wait until /health responds
printf "${YELLOW}⏳ Waiting for brain to come online…${NC}\n"
MAX=20; COUNT=0
until curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1; do
  sleep 0.5; COUNT=$((COUNT+1))
  if [ $COUNT -ge $MAX ]; then
    printf "${RED}❌ Brain did not start in time. Check ai_assistant/server.py.${NC}\n"
    kill "$BRAIN_PID" 2>/dev/null || true
    exit 1
  fi
done
printf "${GREEN}✅ Brain is online at http://localhost:8000${NC}\n"

# ── Start Electron UI ─────────────────────────────────────────────────────────
printf "${GREEN}🖥️  Starting Electron UI…${NC}\n"
cd "$UI"
npm run dev &
UI_PID=$!
printf "   UI PID: ${BOLD}$UI_PID${NC}\n\n"

# ── Trap Ctrl-C → clean shutdown ──────────────────────────────────────────────
cleanup() {
  printf "\n${YELLOW}👋 Shutting down Regis…${NC}\n"
  kill "$BRAIN_PID" 2>/dev/null || true
  kill "$UI_PID"    2>/dev/null || true
  # Kill any child processes
  pkill -P "$UI_PID" 2>/dev/null || true
  printf "${GREEN}✅ Goodbye!${NC}\n"
  exit 0
}
trap cleanup INT TERM

printf "${BOLD}${CYAN}Regis is running. Press Ctrl+C to quit.${NC}\n\n"
wait
