import json
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from planner import plan
from executor import execute
from memory import Memory
from vision import Vision
from voice import VoiceInput

memory = Memory()
vision = Vision()
try:
    voice = VoiceInput()
except Exception as e:
    print(f"❌ Could not initialize voice: {e}")
    voice = None

class AssistantAPI(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()
        
    def do_POST(self):
        try:
            if self.path == '/voice':
                self._handle_voice()
            else:
                self._handle_command()
        except Exception as e:
            print(f"❌ Error handling request: {e}")
            traceback.print_exc()
            self.send_response(500)
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def _handle_command(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        data = json.loads(body) if body else {}
        command = data.get("command", "")
        
        print(f"🧠 Brain received: {command}")
        
        plan_data = plan(command)
        steps = plan_data.get("steps", [])
        
        results = []
        if steps:
            results = execute(steps)
            memory.save_steps(steps)
            memory.save_command(command)
            
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()
        
        self.wfile.write(json.dumps({
            "steps": steps, 
            "results": results,
            "message": f"Executed {len(results)} steps."
        }).encode('utf-8'))

    def _handle_voice(self):
        if not voice:
            raise RuntimeError("Voice system not initialized. Check server logs.")

        print("🎙️ Brain starting voice capture...")
        text = voice.listen_once()
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()
        
        self.wfile.write(json.dumps({
            "text": text or "",
            "success": text is not None
        }).encode('utf-8'))

if __name__ == '__main__':
    port = 8000
    print(f"🧠 Brain Online ! Listening on http://localhost:{port}")
    # Use ThreadingHTTPServer to prevent blocking during audio recording
    ThreadingHTTPServer(('0.0.0.0', port), AssistantAPI).serve_forever()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
        self.end_headers()
        
    def do_POST(self):
        if self.path == '/command' or self.path == '/':
            self._handle_command()
        elif self.path == '/voice':
            self._handle_voice()
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_command(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_response(400)
            self.end_headers()
            return
            
        data = json.loads(self.rfile.read(content_length))
        command = data.get("command", "")
        print(f"🧠 Brain received command: {command}")
        
        plan_data = plan(command)
        steps = plan_data.get("steps", [])
        
        results = []
        if steps:
            results = execute(steps)
            memory.save_steps(steps)
            memory.save_command(command)
            
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        self.wfile.write(json.dumps({
            "steps": steps, 
            "results": results,
            "message": f"Executed {len(results)} steps."
        }).encode('utf-8'))

    def _handle_voice(self):
        print("🎙️ Brain starting voice capture...")
        text = voice.listen_once()
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        self.wfile.write(json.dumps({
            "text": text or "",
            "success": text is not None
        }).encode('utf-8'))

if __name__ == '__main__':
    port = 8000
    print(f"🧠 Brain Online ! Listening on http://127.0.0.1:{port}")
    HTTPServer(('127.0.0.1', port), AssistantAPI).serve_forever()
