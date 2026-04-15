# 🤖 macOS AI Assistant

A local, privacy-first AI assistant that accepts voice commands, plans actions with an LLM, and executes them on your Mac — no paid APIs required.

---

## Architecture

```
Voice → faster-whisper → Text → LLM Planner → JSON Steps → Executor → macOS
```

| Module        | Purpose                                       |
|---------------|-----------------------------------------------|
| `voice.py`    | Captures audio, transcribes via faster-whisper |
| `planner.py`  | Sends text to LLM, returns structured steps   |
| `executor.py` | Runs each step (open app, type, click, etc.)   |
| `vision.py`   | Screenshot + OCR for screen understanding      |
| `memory.py`   | Stores recent commands & action history        |
| `config.py`   | All tuneable settings in one place             |
| `main.py`     | CLI entry point (voice or text mode)           |

---

## Setup

### 1. Prerequisites

- **Python 3.10+**
- **Tesseract OCR**
  ```bash
  brew install tesseract
  ```
- **PortAudio** (needed by `sounddevice`)
  ```bash
  brew install portaudio
  ```

### 2. Create a virtual environment

```bash
cd ai_assistant
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Grant macOS Permissions

Go to **System Settings → Privacy & Security** and allow:

| Permission          | Required for       |
|---------------------|--------------------|
| Accessibility       | `pyautogui` clicks/typing |
| Screen Recording    | Screenshots & OCR  |
| Microphone          | Voice input        |

---

## Running

### Voice mode (default)

```bash
python main.py
```

### Text mode (no mic needed — good for testing)

```bash
python main.py --text
```

---

## Connecting an LLM

The planner calls a local **Ollama**-compatible endpoint by default.

### Option A — Ollama (recommended)

```bash
# Install Ollama: https://ollama.com
ollama pull gemma2        # or qwen2, llama3, mistral, etc.
ollama serve              # starts on http://localhost:11434
```

Edit `config.py` if you use a different model:

```python
LLM_MODEL = "gemma2"     # change to your model name
```

### Option B — OpenRouter (cloud, optional)

In `planner.py`, replace `_call_llm()` with an OpenAI-compatible request:

```python
import os, json, urllib.request

def _call_llm(prompt: str) -> str:
    body = json.dumps({
        "model": "google/gemma-2-9b-it:free",
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]
```

Then set your key:

```bash
export OPENROUTER_API_KEY="sk-or-..."
```

---

## Supported Actions

| Action            | Description                     | Example params                        |
|-------------------|---------------------------------|---------------------------------------|
| `open_app`        | Launch a macOS application      | `{"app_name": "Safari"}`              |
| `open_url`        | Open a URL in default browser   | `{"url": "https://google.com"}`       |
| `type_text`       | Type text at cursor position    | `{"text": "Hello"}`                   |
| `press_key`       | Press a single key              | `{"key": "enter"}`                    |
| `hotkey`          | Key combination                 | `{"keys": ["command", "v"]}`          |
| `wait`            | Pause execution                 | `{"seconds": 2}`                      |
| `run_command`     | Execute a shell command         | `{"command": "ls"}`                   |
| `click`           | Click at screen coordinates     | `{"x": 500, "y": 300}`               |
| `get_screen_text` | OCR the current screen          | `{}`                                  |

---

## Safety

- Commands containing `rm -rf`, `sudo rm`, `mkfs`, etc. are **automatically blocked**.
- `run_command` actions always **prompt for user confirmation** before executing.
- All patterns are configurable in `config.py`.

---

## Example Session

```
⌨️  AI Assistant — Text Mode
  Type a command (or "quit" to exit).

🟢 You: open safari and go to youtube

📋 Plan (2 steps):
  1. open_app  →  {'app_name': 'Safari'}
  2. open_url  →  {'url': 'https://www.youtube.com'}

✅ Executed 2/2 steps.
```

---

## License

MIT
