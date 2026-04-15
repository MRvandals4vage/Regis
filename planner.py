# planner.py — Converts a natural-language command into a list of action steps

import json
import re
import urllib.request
import urllib.error

from config import LLM_ENDPOINT, LLM_MODEL, LLM_TIMEOUT

# ─── Prompt template ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an AI assistant that controls a macOS computer.
Given a user command, output ONLY valid JSON — no prose, no markdown fences.

Respond strictly in this format:
{
  "steps": [
    {"action": "<action_name>", "params": {<key>: <value>}}
  ]
}

Available actions and their required params:
- open_app      : {"app_name": "Safari"}
- open_url      : {"url": "https://example.com"}
- type_text     : {"text": "hello world"}
- press_key     : {"key": "enter"}
- hotkey        : {"keys": ["command", "c"]}
- wait          : {"seconds": 2}
- run_command   : {"command": "ls -la"}
- click         : {"x": 100, "y": 200}
- get_screen_text: {}

Rules:
- Use open_url for web tasks, open_app for native apps.
- Chain steps logically.
- If opening an app and then typing text, ALWAYS add a `wait` step (2-3 seconds) between `open_app` and `type_text` so the app has time to load.
- Never include explanations outside the JSON.
"""


# ─── LLM call (swap this for any local model / OpenRouter) ───────────────────

def _call_llm(prompt: str) -> str:
    """
    Send a prompt to a local Ollama-compatible endpoint.

    To switch to OpenRouter:
        endpoint = "https://openrouter.ai/api/v1/chat/completions"
        Add header: Authorization: Bearer <your_key>
        Change body to OpenAI chat format.
    """
    body = json.dumps({
        "model":  LLM_MODEL,
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        LLM_ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # Ollama returns {"response": "..."}
            return data.get("response", data.get("choices", [{}])[0]
                            .get("message", {}).get("content", ""))
    except urllib.error.URLError as exc:
        print(f"[Planner] LLM request failed: {exc}")
        return ""


# ─── Fallback: stub planner used when LLM is unavailable ─────────────────────

def _stub_plan(text: str) -> dict:
    """
    Very simple keyword-based planner used as a fallback when no LLM is
    reachable.  Handles common one-step commands so the assistant is useful
    even without a running model.
    """
    t = text.lower()
    steps = []

    # 1. Open app
    app_match = re.search(r'open\s+([a-zA-Z0-9\-\s]+?)(?:\s+and\s+|$)', text, re.IGNORECASE)
    if app_match:
        app_name = app_match.group(1).strip()
        if app_name.lower() in ("browser", "safari"):
            app_name = "Safari"
        elif app_name.lower() in ("chrome", "google chrome"):
            app_name = "Google Chrome"
        steps.append({"action": "open_app", "params": {"app_name": app_name}})

    # 2. Type text
    type_match = re.search(r'(?:type|write)\s+(?:["\']([^"\']+)["\']|(.*))', text, re.IGNORECASE)
    if type_match:
        content = type_match.group(1) or type_match.group(2)
        if content:
            # If we just launched an app, wait briefly
            if steps and steps[-1]["action"] == "open_app":
                steps.append({"action": "wait", "params": {"seconds": 2}})
            steps.append({"action": "type_text", "params": {"text": content.strip()}})

    if steps:
        return {"steps": steps}

    if "screenshot" in t or "screen" in t:
        return {"steps": [{"action": "get_screen_text", "params": {}}]}

    if "wait" in t:
        return {"steps": [{"action": "wait", "params": {"seconds": 2}}]}

    # Default: try to run as a shell command
    return {"steps": [{"action": "run_command", "params": {"command": text}}]}


# ─── Public API ───────────────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict:
    """Pull the first valid JSON object out of a (possibly noisy) string."""
    # Strip markdown code fences if present
    raw = re.sub(r"```(?:json)?", "", raw).strip()

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM response")

    return json.loads(match.group())


def plan(user_text: str, screen_context: str = "") -> dict:
    """
    Return a structured action plan for *user_text*.

    Args:
        user_text:      The transcribed voice command.
        screen_context: Optional OCR text from the current screen.

    Returns:
        dict with key "steps" → list of {"action": str, "params": dict}
    """
    context_block = ""
    if screen_context:
        context_block = f"\nCurrent screen content:\n{screen_context[:1500]}\n"

    full_prompt = f"{SYSTEM_PROMPT}{context_block}\nUser command: {user_text}\n"

    raw = _call_llm(full_prompt)

    if not raw:
        print("[Planner] LLM unavailable — using stub planner.")
        return _stub_plan(user_text)

    try:
        plan_data = _extract_json(raw)
        # Validate top-level structure
        if "steps" not in plan_data or not isinstance(plan_data["steps"], list):
            raise ValueError("Missing 'steps' list")
        return plan_data
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"[Planner] Could not parse LLM response ({exc}), using stub.")
        return _stub_plan(user_text)
