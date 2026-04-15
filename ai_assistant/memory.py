# memory.py — Simple in-memory store for command/step history

from collections import deque
from config import MAX_HISTORY_ENTRIES

class Memory:
    def __init__(self):
        self._store = {
            "last_command": None,       # raw text from voice / user
            "last_steps":  [],          # list of step dicts from planner
            "history":     deque(maxlen=MAX_HISTORY_ENTRIES),
        }

    # ── write ────────────────────────────────────────────────────────────────

    def save_command(self, text: str):
        self._store["last_command"] = text

    def save_steps(self, steps: list):
        self._store["last_steps"] = steps
        self._store["history"].append({"command": self._store["last_command"],
                                       "steps": steps})

    # ── read ─────────────────────────────────────────────────────────────────

    def get_last_command(self) -> str | None:
        return self._store["last_command"]

    def get_last_steps(self) -> list:
        return self._store["last_steps"]

    def get_history(self) -> list:
        return list(self._store["history"])

    def clear(self):
        self._store["last_command"] = None
        self._store["last_steps"]   = []
        self._store["history"].clear()
