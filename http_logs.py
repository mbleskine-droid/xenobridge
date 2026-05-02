#!/usr/bin/env python3
"""Script Lua -> HTTP -> Console temps reel"""
import subprocess
import time
import requests
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 9999

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    
    def do_POST(self):
        if self.path == '/log':
            n = int(self.headers.get('Content-Length', 0))
            msg = self.rfile.read(n).decode('utf-8', errors='ignore')
            print(f"[RBX] {msg}")
            sys.stdout.flush()
            self.send_response(200)
            self.end_headers()

def main():
    # Serveur HTTP
    server = HTTPServer(('127.0.0.1', PORT), Handler)
    import threading
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"[+] Serveur http://127.0.0.1:{PORT}")
    
    # XenoBridge
    bridge = r"c:\Users\Zenith__\Documents\windsurf\xeno-re\XenoBridge\bin\Release\net8.0-windows\win-x64\XenoBridge.exe"
    subprocess.Popen([bridge], creationflags=subprocess.CREATE_NEW_CONSOLE)
    time.sleep(3)
    
    # PID Roblox
    r = requests.get("http://localhost:3111/clients", timeout=5)
    pid = r.json()['clients'][0]['pid']
    print(f"[+] PID: {pid}")
    
    # Attacher
    requests.post("http://localhost:3111/attach", timeout=5)
    
    # Script Lua avec HTTP
    script = f'''
local http = game:GetService("HttpService")
local url = "http://127.0.0.1:{PORT}/log"

local function log(msg)
    pcall(function()
        http:PostAsync(url, msg, Enum.HttpContentType.TextPlain)
    end)
end

log("=== DEMARRAGE ===")

-- Boucle d'envoi de logs
while true do
    log("Ping: " .. tostring(os.time()))
    wait(2)
end
'''
    
    print("[+] Injection...")
    requests.post("http://localhost:3111/execute", 
                  json={"script": script, "pids": [pid]},
                  timeout=10)
    print("[+] Logs en temps reel (Ctrl+C pour arreter):\n")
    
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()
        print("\n[+] Arrete")

if __name__ == "__main__":
    main()
