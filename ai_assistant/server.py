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

# ── Global singletons ────────────────────────────────────────────────────────
memory = Memory()
vision = Vision()

try:
    voice = VoiceInput()
    print("✅ Voice system ready.")
except Exception as e:
    print(f"⚠️  Could not initialize voice: {e}")
    voice = None


# ── Request Handler ──────────────────────────────────────────────────────────
class AssistantAPI(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Suppress default noisy HTTP logs; we print our own
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
        command = data.get("command", "").strip()

        if not command:
            self._send_json(400, {"error": "Empty command"})
            return

        print(f"🧠 Command received: {command!r}")

        plan_data = plan(command)
        steps = plan_data.get("steps", [])

        results = []
        if steps:
            results = execute(steps)
            ok_count = sum(1 for r in results if r.get("status") == "ok")
            
            # Build a human-readable reply
            reply = plan_data.get("reply") or plan_data.get("message") or f"Done — executed {ok_count} of {len(steps)} steps."
            
            memory.save_steps(steps, reply=reply)
            memory.save_command(command)
        else:
            reply = "I couldn't figure out how to do that."
            ok_count = 0
            
        print(f"✅ Executed {ok_count}/{len(results)} steps.")
        
        self._send_json(200, {
            "reply": reply,
            "steps": steps,
            "results": results,
            "message": reply
        })

    def _handle_voice(self):
        if voice is None:
            self._send_json(503, {
                "error": "Voice system not available. Check server logs.",
                "success": False,
                "text": ""
            })
            return

        print("🎙️  Starting voice capture…")
        try:
            text = voice.listen_once()
        except Exception as e:
            print(f"❌ Voice capture failed: {e}")
            self._send_json(500, {"error": str(e), "success": False, "text": ""})
            return

        print(f"🎙️  Heard: {text!r}")
        self._send_json(200, {
            "text": text or "",
            "success": bool(text)
        })


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = 8000
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
