import json
import os
from collections import deque
from config import MAX_HISTORY_ENTRIES, MEMORY_FILE_PATH

class Memory:
    def __init__(self):
        self._store = {
            "last_command": None,
            "last_steps":  [],
            "history":     deque(maxlen=MAX_HISTORY_ENTRIES),
        }
        self._load()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _load(self):
        """Load memory from disk if it exists."""
        if not os.path.exists(MEMORY_FILE_PATH):
            return

        try:
            with open(MEMORY_FILE_PATH, 'r') as f:
                data = json.load(f)
                self._store["last_command"] = data.get("last_command")
                self._store["last_steps"] = data.get("last_steps", [])
                
                # Load history into deque
                history_list = data.get("history", [])
                self._store["history"] = deque(history_list, maxlen=MAX_HISTORY_ENTRIES)
                print(f"[Memory] Loaded {len(history_list)} entries from disk.")
        except Exception as e:
            print(f"[Memory] ⚠️ Failed to load memory: {e}")

    def _save(self):
        """Save current memory state to disk."""
        try:
            data = {
                "last_command": self._store["last_command"],
                "last_steps":   self._store["last_steps"],
                "history":      list(self._store["history"])
            }
            with open(MEMORY_FILE_PATH, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Memory] ❌ Failed to save memory: {e}")

    # ── write ────────────────────────────────────────────────────────────────

    def save_command(self, text: str):
        self._store["last_command"] = text
        self._save()

    def save_steps(self, steps: list, reply: str = None):
        self._store["last_steps"] = steps
        self._store["history"].append({
            "command": self._store["last_command"],
            "steps": steps,
            "reply": reply
        })
        self._save()

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
        if os.path.exists(MEMORY_FILE_PATH):
            try:
                os.remove(MEMORY_FILE_PATH)
            except Exception as e:
                print(f"[Memory] ⚠️ Failed to delete memory file: {e}")
