# config.py — Central configuration for the AI assistant

import os

# ─── Whisper / Voice ──────────────────────────────────────────────────────────
WHISPER_MODEL_SIZE = "base"          # tiny | base | small | medium | large
WHISPER_DEVICE     = "cpu"           # cpu | cuda
WHISPER_LANGUAGE   = "en"

# ─── LLM ─────────────────────────────────────────────────────────────────────
# Swap this URL / model for Gemma (Ollama) or OpenRouter
LLM_ENDPOINT = "http://localhost:11434/api/generate"   # Ollama default
LLM_MODEL    = "gemma2"                                # or "qwen2", etc.
LLM_TIMEOUT  = 60   # seconds

# ─── Safety ──────────────────────────────────────────────────────────────────
DANGEROUS_PATTERNS = [
    "rm -rf", "sudo rm", "mkfs", "dd if=", ":(){:|:&};:",
    "chmod 777 /", "curl | sh", "wget | sh",
]

# Commands requiring explicit user confirmation before execution
REQUIRES_CONFIRMATION = ["run_command"]

# ─── Vision ──────────────────────────────────────────────────────────────────
SCREENSHOT_PATH = "/tmp/ai_assistant_screenshot.png"

# ─── Memory ──────────────────────────────────────────────────────────────────
MAX_HISTORY_ENTRIES = 20    # how many past commands to keep
