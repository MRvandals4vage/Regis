#!/usr/bin/env python3
# main.py — Entry point: voice → planner → executor loop

import sys
import argparse

from memory   import Memory
from planner  import plan
from executor import execute
from vision   import Vision


def process_command(text: str, memory: Memory, vision: Vision):
    """Full pipeline for a single user command."""
    memory.save_command(text)

    # Optionally include current screen context
    screen_ctx = ""
    lower = text.lower()
    if any(kw in lower for kw in ("screen", "see", "read", "look", "what")):
        print("[Main] Grabbing screen context for planner…")
        screen_ctx = vision.get_screen_text()

    # Generate plan
    action_plan = plan(text, screen_context=screen_ctx)
    steps = action_plan.get("steps", [])

    if not steps:
        print("[Main] Planner returned no steps.")
        return

    print(f"\n📋 Plan ({len(steps)} step{'s' if len(steps) != 1 else ''}):")
    for i, s in enumerate(steps, 1):
        print(f"  {i}. {s['action']}  →  {s.get('params', {})}")
    print()

    # Execute
    results = execute(steps)
    memory.save_steps(steps)

    # Summary
    ok    = sum(1 for r in results if r["status"] == "ok")
    total = len(results)
    print(f"✅ Executed {ok}/{total} steps.\n")


def run_voice_mode():
    """Main loop: continuously listen for voice commands."""
    from voice import VoiceInput

    memory = Memory()
    vision = Vision()
    voice  = VoiceInput()

    print("=" * 50)
    print("  🎙️  AI Assistant — Voice Mode")
    print("  Speak a command. Press Ctrl+C to quit.")
    print("=" * 50)

    voice.listen_loop(lambda text: process_command(text, memory, vision))


def run_text_mode():
    """Interactive text prompt for testing without a microphone."""
    memory = Memory()
    vision = Vision()

    print("=" * 50)
    print("  ⌨️  AI Assistant — Text Mode")
    print('  Type a command (or "quit" to exit).')
    print("=" * 50)

    while True:
        try:
            text = input("\n🟢 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not text or text.lower() in ("quit", "exit", "q"):
            break

        process_command(text, memory, vision)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="macOS AI Assistant")
    parser.add_argument("--text", action="store_true",
                        help="Run in text-input mode (no microphone needed)")
    args = parser.parse_args()

    try:
        if args.text:
            run_text_mode()
        else:
            run_voice_mode()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
