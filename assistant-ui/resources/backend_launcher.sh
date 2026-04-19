#!/bin/bash
# backend_launcher.sh — Managed by Electron to start Regis Brain
# This script ensures a venv exists and starts the server.

ROOT="$(cd "$(dirname "$0")" && pwd)"
BRAIN="$ROOT/ai_assistant"

# Ensure Homebrew's bin is on PATH (needed for node/python on macOS)
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

cd "$BRAIN"

if [ ! -d ".venv" ]; then
  echo "⚙️  Creating Python virtual environment in $BRAIN..."
  python3 -m venv .venv
fi

PYTHON="./.venv/bin/python"
PIP="./.venv/bin/pip"

echo "📦 Checking Python dependencies..."
"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet -r requirements.txt || "$PIP" install --quiet faster-whisper sounddevice numpy pyautogui Pillow requests

echo "🧠 Starting Regis Brain..."
exec "$PYTHON" server.py
