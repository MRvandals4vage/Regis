#!/bin/bash
# backend_launcher.sh — Managed by Electron to start Regis Brain
# This script ensures a venv exists and starts the server.

ROOT="$(cd "$(dirname "$0")" && pwd)"
BRAIN="$ROOT/ai_assistant"

# Ensure Homebrew's bin is on PATH
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

# Log to a file we can actually find
LOG_FILE="$HOME/Library/Logs/Regis_Backend.log"
echo "--- Starting Regis Brain at $(date) ---" >> "$LOG_FILE"
echo "ROOT: $ROOT" >> "$LOG_FILE"
echo "BRAIN: $BRAIN" >> "$LOG_FILE"

cd "$BRAIN" || { echo "❌ Could not cd to $BRAIN" >> "$LOG_FILE"; exit 1; }

if [ ! -d ".venv" ]; then
  echo "⚙️  Creating Python virtual environment..." >> "$LOG_FILE"
  python3 -m venv .venv >> "$LOG_FILE" 2>&1
fi

PYTHON="./.venv/bin/python"
PIP="./.venv/bin/pip"

echo "📦 Checking Python dependencies..." >> "$LOG_FILE"
"$PIP" install --quiet --upgrade pip >> "$LOG_FILE" 2>&1
"$PIP" install --quiet -r requirements.txt >> "$LOG_FILE" 2>&1 || "$PIP" install --quiet faster-whisper sounddevice numpy pyautogui Pillow requests >> "$LOG_FILE" 2>&1

echo "🧠 Starting Regis Brain..." >> "$LOG_FILE"
exec "$PYTHON" server.py >> "$LOG_FILE" 2>&1
