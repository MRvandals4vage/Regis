# server.py — Local API server exposing the Assistant Brain to Electron
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from planner import plan
from executor import execute
from memory import Memory
from vision import Vision

memory = Memory()
vision = Vision()

class AssistantAPI(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
        self.end_headers()
        
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_response(400)
            self.end_headers()
            return
            
        data = json.loads(self.rfile.read(content_length))
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
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        self.wfile.write(json.dumps({
            "steps": steps, 
            "results": results,
            "message": f"Executed {len(results)} steps."
        }).encode('utf-8'))

if __name__ == '__main__':
    port = 8000
    print(f"🧠 Brain Online ! Listening on http://127.0.0.1:{port}")
    HTTPServer(('127.0.0.1', port), AssistantAPI).serve_forever()
