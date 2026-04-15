# executor.py — Runs the action steps produced by the planner

import subprocess
import time
import pyautogui
from config import DANGEROUS_PATTERNS, REQUIRES_CONFIRMATION


# ─── Safety ───────────────────────────────────────────────────────────────────

def _is_dangerous(command: str) -> bool:
    """Return True if the command matches any known dangerous pattern."""
    cmd_lower = command.lower()
    return any(pat in cmd_lower for pat in DANGEROUS_PATTERNS)


def _confirm(action: str, params: dict) -> bool:
    """Ask user for Y/n confirmation.  Returns True to proceed."""
    print(f"\n⚠️  Action requires confirmation:")
    print(f"    {action} → {params}")
    answer = input("    Proceed? [Y/n]: ").strip().lower()
    return answer in ("", "y", "yes")


# ─── Individual action handlers ──────────────────────────────────────────────

def _open_app(params: dict):
    name = params["app_name"]
    print(f"[Exec] Opening app: {name}")
    subprocess.Popen(["open", "-a", name])


def _open_url(params: dict):
    url = params["url"]
    print(f"[Exec] Opening URL: {url}")
    subprocess.Popen(["open", url])


def _type_text(params: dict):
    text = params["text"]
    print(f"[Exec] Typing: {text!r}")
    time.sleep(0.3)
    # Use osascript natively for much higher reliability on macOS
    safe_text = text.replace('\\', '\\\\').replace('"', '\\"')
    script = f'tell application "System Events" to keystroke "{safe_text}"'
    subprocess.run(["osascript", "-e", script])


def _press_key(params: dict):
    key = params["key"].lower()
    print(f"[Exec] Pressing key: {key}")
    if key == "enter" or key == "return":
        script = 'tell application "System Events" to key code 36'
        subprocess.run(["osascript", "-e", script])
    else:
        # Fallback to pyautogui for other special keys
        pyautogui.press(key)


def _hotkey(params: dict):
    keys = params["keys"]
    print(f"[Exec] Hotkey: {'+'.join(keys)}")
    pyautogui.hotkey(*keys)


def _wait(params: dict):
    secs = params.get("seconds", 1)
    print(f"[Exec] Waiting {secs}s…")
    time.sleep(secs)


def _run_command(params: dict):
    cmd = params["command"]

    if _is_dangerous(cmd):
        print(f"[Exec] ❌ Blocked dangerous command: {cmd!r}")
        return

    print(f"[Exec] Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                            timeout=30)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(f"[stderr] {result.stderr.strip()}")


def _click(params: dict):
    x, y = int(params["x"]), int(params["y"])
    print(f"[Exec] Clicking ({x}, {y})")
    pyautogui.click(x, y)


def _get_screen_text(params: dict):
    from vision import Vision
    text = Vision().get_screen_text()
    print(f"[Exec] Screen text ({len(text)} chars):\n{text[:500]}")
    return text


# ─── Dispatch table ──────────────────────────────────────────────────────────

ACTION_MAP = {
    "open_app":        _open_app,
    "open_url":        _open_url,
    "type_text":       _type_text,
    "press_key":       _press_key,
    "hotkey":          _hotkey,
    "wait":            _wait,
    "run_command":     _run_command,
    "click":           _click,
    "get_screen_text": _get_screen_text,
}


# ─── Public API ───────────────────────────────────────────────────────────────

def execute(steps: list) -> list[dict]:
    """
    Execute a list of action steps.

    Each step is {"action": str, "params": dict}.
    Returns a list of result dicts (one per step).
    """
    results = []
    for i, step in enumerate(steps, 1):
        action = step.get("action", "")
        params = step.get("params", {})

        handler = ACTION_MAP.get(action)
        if handler is None:
            msg = f"Unknown action: {action!r}"
            print(f"[Exec] ⚠️  {msg}")
            results.append({"step": i, "action": action, "status": "skipped",
                            "reason": msg})
            continue

        # Ask for confirmation on risky actions
        if action in REQUIRES_CONFIRMATION:
            if not _confirm(action, params):
                print("[Exec] Skipped by user.")
                results.append({"step": i, "action": action,
                                "status": "skipped", "reason": "user declined"})
                continue

        try:
            ret = handler(params)
            results.append({"step": i, "action": action, "status": "ok",
                            "output": ret})
        except Exception as exc:
            print(f"[Exec] ❌ Step {i} failed: {exc}")
            results.append({"step": i, "action": action, "status": "error",
                            "error": str(exc)})

    return results
