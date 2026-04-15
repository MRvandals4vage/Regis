# Regis

A local AI-powered macOS automation agent that uses voice commands, vision (OCR), and LLM-based planning to execute real-time tasks such as opening applications, controlling the browser, and running system workflows.

---

## Overview

Regis is a modular AI assistant designed to operate directly on your machine without relying on paid APIs. It combines speech recognition, structured LLM planning, and deterministic execution to automate everyday tasks on macOS.

Pipeline:

Voice → Text → Plan → Execute → Feedback

---

## Features

- Voice-controlled task execution (offline speech-to-text)
- Browser automation (open URLs, search, navigation)
- Application control (open, close, switch apps)
- OCR-based screen understanding for basic UI awareness
- Structured LLM planning with deterministic execution
- Local-first design (no mandatory paid services)

---

## Architecture

User Input (Voice)
↓
Speech-to-Text (Whisper)
↓
LLM Planner (Gemma / Qwen)
↓
Structured JSON Plan
↓
Execution Engine (Python + macOS tools)
↓
System Actions

---

## Project Structure

ai_assistant/
│
├── main.py        # main loop and orchestration
├── planner.py     # converts input into structured action plans
├── executor.py    # executes system and UI actions
├── voice.py       # speech-to-text processing
├── vision.py      # OCR-based screen analysis
├── memory.py      # stores session state
├── config.py      # configuration settings
├── requirements.txt
└── README.md

---

## Installation

### 1. Clone the repository
git clone https://github.com/MRvandals4vage/Regis.git
cd Regis/ai_assistant

### 2. Install dependencies
pip install -r requirements.txt

### 3. Install system dependencies (macOS)
brew install tesseract

---

## Usage

Run the assistant:
python main.py

Example voice commands:

- "Open Chrome and go to YouTube"
- "Open VS Code"
- "Search GitHub for Python projects"

Flow:
1. Speech is converted to text
2. LLM generates a structured plan
3. System executes the plan

---

## LLM Integration

The planner supports:

- Gemma (local or API)
- Qwen (OpenRouter / HuggingFace)
- Any LLM that returns structured JSON

To integrate:
- Replace the placeholder function in `planner.py`
- Ensure output follows the required format

---

## Example Output Format
{
“steps”: [
{
“action”: “open_app”,
“params”: {
“app_name”: “Google Chrome”
}
},
{
“action”: “open_url”,
“params”: {
“url”: “https://www.youtube.com”
}
}
]
}
---

## Safety

- Basic filtering of dangerous commands
- Avoids destructive shell operations
- Recommended to review execution layer before full automation

---

## Limitations

- OCR-based vision is approximate and may fail on complex UIs
- Free-tier LLMs may introduce latency
- Not fully autonomous for long multi-step workflows
- UI interactions depend on screen consistency

---

## Future Improvements

- Real UI element detection (beyond OCR)
- Persistent memory and task tracking
- Browser DOM-level automation
- Hotword activation for hands-free usage
- Multi-agent architecture for planning and execution

---

## License

MIT License