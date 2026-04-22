# planner.py — Converts a natural-language command into a list of action steps

import json
import re
import urllib.request
import urllib.error

from config import LLM_ENDPOINT, LLM_MODEL, LLM_TIMEOUT

# ─── Prompt template ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an advanced AI agent that controls a macOS computer.
Your goal is to solve the user's request by planning and executing steps.
You use a "Thought-Action-Observation" loop.

Respond ONLY with a valid JSON object in this format:
{
  "thought": "Brief explanation of your reasoning and what you've seen so far",
  "steps": [
    {"action": "<action_name>", "params": {<key>: <value>}}
  ],
  "done": true/false,
  "reply": "Human-friendly update for the user"
}

Available actions:
- open_app      : {"app_name": "Safari"}
- close_app     : {"app_name": "Safari"}
- open_url      : {"url": "https://example.com"}
- type_text     : {"text": "hello world"}
- press_key     : {"key": "enter"}
- hotkey        : {"keys": ["command", "c"]}
- wait          : {"seconds": 2}
- run_command   : {"command": "ls -la"}
- click         : {"x": 100, "y": 200}
- get_screen_text: {}

Rules:
1. If you need to see what's on the screen to decide the next step, use `get_screen_text` and set `done: false`.
2. If you have finished the user's request, set `done: true`.
3. If you are opening an app, add a `wait` step (2-3s) before interacting with it.
4. Always provide a clear `thought` and a friendly `reply`.
5. NEVER include prose outside the JSON.
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

    # 2. Search
    search_match = re.search(r'search(?:\s+for)?\s+(?:["\']([^"\']+)["\']|(.*))', text, re.IGNORECASE)
    if search_match:
        query = search_match.group(1) or search_match.group(2)
        if query:
            import urllib.parse
            url = "https://www.google.com/search?q=" + urllib.parse.quote(query.strip())
            return {"steps": [{"action": "open_url", "params": {"url": url}}]}

    # 3. Type text
    type_match = re.search(r'(?:type|write)\s+(?:["\']([^"\']+)["\']|(.*))', text, re.IGNORECASE)
    if type_match:
        content = type_match.group(1) or type_match.group(2)
        if content:
            if steps and steps[-1]["action"] == "open_app":
                steps.append({"action": "wait", "params": {"seconds": 2}})
            steps.append({"action": "type_text", "params": {"text": content.strip()}})
            steps.append({"action": "press_key", "params": {"key": "enter"}})

    # 4. Close app
    close_match = re.search(r'(?:close|quit|stop|exit)\s+([a-zA-Z0-9\-\s]+?)(?:\s|$)', text, re.IGNORECASE)
    if close_match:
        app_name = close_match.group(1).strip()
        if app_name.lower() in ("browser", "safari"):
            app_name = "Safari"
        elif app_name.lower() in ("chrome", "google chrome"):
            app_name = "Google Chrome"
        elif app_name.lower() == "codex":
             # Handle special case if codex was what they meant
             app_name = "Google Chrome" # Example fallback if codex was a browser window
        steps.append({"action": "close_app", "params": {"app_name": app_name}})

    if steps:
        actions = ", ".join(s["action"] for s in steps)
        return {"steps": steps, "reply": f"On it — running: {actions}."}

    if "screenshot" in t or "screen" in t:
        return {"steps": [{"action": "get_screen_text", "params": {}}],
                "reply": "Capturing screen text…"}

    if "wait" in t:
        return {"steps": [{"action": "wait", "params": {"seconds": 2}}],
                "reply": "Waiting 2 seconds."}

    # Default: try to run as a shell command
    return {"steps": [{"action": "run_command", "params": {"command": text}}],
            "reply": f"Running: {text}"}


# ─── Public API ───────────────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict:
    """Pull the first valid JSON object out of a (possibly noisy) string."""
    # Strip markdown code fences if present
    raw = re.sub(r"```(?:json)?", "", raw).strip()

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM response")

    return json.loads(match.group())


def plan(user_text: str, screen_context: str = "", history: list = None) -> dict:
    """
    Return a structured action plan for *user_text*.
    """
    context_block = ""
    if screen_context:
        context_block = f"\n[Observation] Current screen content:\n{screen_context[:2000]}\n"

    history_block = ""
    if history:
        history_block = f"\n[History] Previous steps:\n{json.dumps(history[-3:], indent=2)}\n"

    full_prompt = f"{SYSTEM_PROMPT}{history_block}{context_block}\nUser command: {user_text}\n"

    raw = _call_llm(full_prompt)

    if not raw:
        print("[Planner] LLM unavailable — using stub planner.")
        return _stub_plan(user_text)

    try:
        plan_data = _extract_json(raw)
        # Ensure default values for new fields
        plan_data.setdefault("steps", [])
        plan_data.setdefault("done", True)
        plan_data.setdefault("thought", "No reasoning provided.")
        plan_data.setdefault("reply", "Done.")
        return plan_data
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"[Planner] Could not parse LLM response ({exc}), using stub.")
        return _stub_plan(user_text)
