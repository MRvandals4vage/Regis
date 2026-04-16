#!/usr/bin/env bash
# start.sh — Launch Regis: Python brain + Electron UI together
# Usage: bash start.sh

set -e
# Ensure Homebrew's bin is on PATH (needed for npm/node on macOS)
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"
ROOT="$(cd "$(dirname "$0")" && pwd)"
BRAIN="$ROOT/ai_assistant"
UI="$ROOT/assistant-ui"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

echo -e "\n${BOLD}${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║        🧠  Regis Launcher             ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════╝${NC}\n"

# ── Check venv ────────────────────────────────────────────────────────────────
if [ ! -d "$BRAIN/.venv" ]; then
  echo -e "${YELLOW}⚙️  Creating Python virtual environment…${NC}"
  python3 -m venv "$BRAIN/.venv"
fi

PYTHON="$BRAIN/.venv/bin/python"
PIP="$BRAIN/.venv/bin/pip"

# ── Install Python deps ───────────────────────────────────────────────────────
echo -e "${YELLOW}📦 Checking Python dependencies…${NC}"
$PIP install --quiet --upgrade pip
$PIP install --quiet faster-whisper sounddevice numpy pyautogui Pillow requests

# ── Install Node deps ─────────────────────────────────────────────────────────
if [ ! -d "$UI/node_modules" ]; then
  echo -e "${YELLOW}📦 Installing Node dependencies…${NC}"
  cd "$UI" && npm install
fi

# ── Kill any stale server on port 8000 ───────────────────────────────────────
OLD_PID=$(lsof -ti:8000 2>/dev/null || true)
if [ -n "$OLD_PID" ]; then
  echo -e "${YELLOW}🔪 Stopping old server (PID $OLD_PID)…${NC}"
  kill -9 $OLD_PID 2>/dev/null || true
  sleep 1
fi

# ── Start Python brain ────────────────────────────────────────────────────────
echo -e "${GREEN}🧠 Starting Regis Brain (server.py)…${NC}"
cd "$BRAIN"
$PYTHON server.py &
BRAIN_PID=$!
echo -e "   Brain PID: ${BOLD}$BRAIN_PID${NC}"

# Wait until /health responds
echo -e "${YELLOW}⏳ Waiting for brain to come online…${NC}"
MAX=20; COUNT=0
until curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1; do
  sleep 0.5; COUNT=$((COUNT+1))
  if [ $COUNT -ge $MAX ]; then
    echo -e "${RED}❌ Brain did not start in time. Check ai_assistant/server.py.${NC}"
    kill $BRAIN_PID 2>/dev/null || true
    exit 1
  fi
done
echo -e "${GREEN}✅ Brain is online at http://localhost:8000${NC}"

# ── Start Electron UI ─────────────────────────────────────────────────────────
echo -e "${GREEN}🖥️  Starting Electron UI…${NC}"
cd "$UI"
npm run dev &
UI_PID=$!
echo -e "   UI PID: ${BOLD}$UI_PID${NC}\n"

# ── Trap Ctrl-C → clean shutdown ──────────────────────────────────────────────
cleanup() {
  echo -e "\n${YELLOW}👋 Shutting down Regis…${NC}"
  kill $BRAIN_PID 2>/dev/null || true
  kill $UI_PID    2>/dev/null || true
  # Kill any child processes
  pkill -P $UI_PID 2>/dev/null || true
  echo -e "${GREEN}✅ Goodbye!${NC}"
  exit 0
}
trap cleanup INT TERM

echo -e "${BOLD}${CYAN}Regis is running. Press Ctrl+C to quit.${NC}\n"
wait
