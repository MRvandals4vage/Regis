#!/usr/bin/env python3
# server.py — Threaded HTTP API bridge between Electron UI and AI brain

import json
import traceback
import sys
import os

# Ensure the directory of this file is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from planner import plan
from executor import execute
from memory import Memory
from vision import Vision
from voice import VoiceInput
from speaker import say
from hotword import HotwordListener
from config import TTS_ENABLED, HOTWORD, HOTWORD_ENABLED

# ── Global singletons ────────────────────────────────────────────────────────
memory = Memory()
vision = Vision()

try:
    voice = VoiceInput()
    print("✅ Voice system ready.")
except Exception as e:
    print(f"⚠️  Could not initialize voice: {e}")
    voice = None


def process_full_command(command: str) -> dict:
    """
    Advanced agentic loop: Plan -> Execute -> Observe -> Repeat
    """
    command = command.strip()
    if not command:
        return {"error": "Empty command", "reply": "I didn't catch that."}

    print(f"🧠 Starting agentic loop for: {command!r}")
    
    current_screen = ""
    all_steps = []
    all_results = []
    max_iterations = 5
    final_reply = "Task completed."

    for i in range(max_iterations):
        print(f"🔄 Loop iteration {i+1}...")
        
        # 1. Plan
        plan_data = plan(command, screen_context=current_screen, history=all_steps)
        
        thought = plan_data.get("thought", "")
        steps = plan_data.get("steps", [])
        done = plan_data.get("done", True)
        final_reply = plan_data.get("reply", final_reply)
        
        if thought:
            print(f"💭 Thought: {thought}")

        if not steps and done:
            break

        # 2. Execute
        results = execute(steps)
        all_steps.extend(steps)
        all_results.extend(results)

        # 3. Observe (if any step was get_screen_text, update context)
        for res in results:
            if res.get("action") == "get_screen_text" and res.get("status") == "ok":
                current_screen = res.get("output", "")

        if done:
            break
        
        # Small pause between rounds
        import time
        time.sleep(1)

    # Finalize
    memory.save_command(command)
    memory.save_steps(all_steps, reply=final_reply)
    
    if TTS_ENABLED:
        say(final_reply)
        
    return {
        "reply": final_reply,
        "steps": all_steps,
        "results": all_results,
        "message": final_reply
    }


# ── Request Handler ──────────────────────────────────────────────────────────
class AssistantAPI(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == '/health':
            self._send_json(200, {
                "status": "ok",
                "voice_ready": voice is not None
            })
        elif self.path == '/history':
            self._send_json(200, {
                "history": memory.get_history()
            })
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        try:
            if self.path in ('/', '/command'):
                self._handle_command()
            elif self.path == '/voice':
                self._handle_voice()
            else:
                self._send_json(404, {"error": f"Unknown path: {self.path}"})
        except Exception as e:
            print(f"❌ Server error on {self.path}: {e}")
            traceback.print_exc()
            self._send_json(500, {"error": str(e)})

    def _read_body(self) -> dict:
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length) if length > 0 else b'{}'
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _handle_command(self):
        data = self._read_body()
        command = data.get("command", "")
        response = process_full_command(command)
        status = 400 if "error" in response else 200
        self._send_json(status, response)

    def _handle_voice(self):
        if voice is None:
            self._send_json(503, {"error": "Voice system not available", "success": False})
            return

        print("🎙️  Starting voice capture…")
        try:
            text = voice.listen_once()
            self._send_json(200, {"text": text or "", "success": bool(text)})
        except Exception as e:
            print(f"❌ Voice capture failed: {e}")
            self._send_json(500, {"error": str(e), "success": False})


# ── Hotword Callback ──────────────────────────────────────────────────────────
def on_hotword():
    if voice is None:
        return
    
    # Optional: play a short beep here
    print("✨ Hotword triggered internally!")
    try:
        text = voice.listen_once()
        if text:
            process_full_command(text)
    except Exception as e:
        print(f"[Hotword] Trigger failed: {e}")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = 8000
    
    # Start Hotword Listener if enabled
    if HOTWORD_ENABLED:
        try:
            hw = HotwordListener(hotword=HOTWORD)
            hw.start(on_hotword)
            print(f"👂 Background listener active for '{HOTWORD}'")
        except Exception as e:
            print(f"⚠️  Could not start Hotword Listener: {e}")

    print(f"\n{'='*50}")
    print(f"  🧠 Regis Brain  —  http://localhost:{port}")
    print(f"  Routes: GET /health  |  POST /command  |  POST /voice")
    print(f"{'='*50}\n")
    
    server = ThreadingHTTPServer(('0.0.0.0', port), AssistantAPI)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server shutting down.")
        server.shutdown()
