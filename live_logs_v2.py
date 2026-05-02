#!/usr/bin/env python3
"""
Live logs Roblox - Affichage temps reel dans PowerShell
Methode: HTTP callback pour recevoir les logs directement
"""
import subprocess
import time
import requests
import sys
import os
import threading
import queue
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

LOGS_QUEUE = queue.Queue()
HTTP_PORT = 3115
HTTP_SERVER = None

def timestamp():
    return datetime.now().strftime("%H:%M:%S")

class LogHandler(BaseHTTPRequestHandler):
    """Recoit les logs de Roblox via HTTP POST"""
    
    def log_message(self, format, *args):
        pass  # Pas de logs du serveur HTTP
    
    def do_POST(self):
        if self.path == '/log':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8', errors='ignore')
                
                # Mettre dans la queue
                LOGS_QUEUE.put(post_data)
                
                # Afficher IMMEDIATEMENT dans la console
                lines = post_data.split('\n')
                for line in lines:
                    if line.strip():
                        print(f"[{timestamp()}] [RBX] {line}")
                        sys.stdout.flush()
                
                self.send_response(200)
                self.end_headers()
            except Exception as e:
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_response(404)
            self.end_headers()

def start_http_server():
    """Demarre le serveur HTTP pour recevoir les logs"""
    global HTTP_SERVER
    HTTP_SERVER = HTTPServer(('127.0.0.1', HTTP_PORT), LogHandler)
    print(f"[+] Serveur de logs demarre sur http://127.0.0.1:{HTTP_PORT}")
    
    while True:
        try:
            HTTP_SERVER.handle_request()
        except:
            break

def start_xenobridge():
    """Demarre XenoBridge"""
    bridge_path = r"c:\Users\Zenith__\Documents\windsurf\xeno-re\XenoBridge\bin\Release\net8.0-windows\win-x64\XenoBridge.exe"
    print("[+] Demarrage XenoBridge...")
    subprocess.Popen([bridge_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
    time.sleep(3)
    print("[OK] XenoBridge pret\n")

def get_roblox_pid():
    """Recupere le PID Roblox"""
    try:
        r = requests.get("http://localhost:3111/clients", timeout=5)
        data = r.json()
        clients = data.get('clients', [])
        
        for c in clients:
            print(f"[+] Roblox detecte: PID {c['pid']} ({c['name']}) - State {c['state']}")
            if c['state'] == 3:
                return c['pid']
        
        if clients:
            return clients[0]['pid']
            
    except Exception as e:
        print(f"[!] Erreur detection: {e}")
    return None

def inject_script_with_callback(pid):
    """Injecte un script qui envoie les logs via HTTP"""
    print("[+] Attachement...")
    try:
        requests.post("http://localhost:3111/attach", timeout=5)
    except:
        pass
    
    print("[+] Injection script avec callback HTTP...")
    
    # Script qui envoie les logs via HTTP vers notre serveur local
    script = f'''
local HttpService = game:GetService("HttpService")
local LOG_URL = "http://127.0.0.1:{HTTP_PORT}/log"

local function send(msg)
    pcall(function()
        HttpService:PostAsync(LOG_URL, msg, Enum.HttpContentType.TextPlain)
    end)
end

send("=== HELLO WORLD FROM MCP ===")
send("Injection reussie via HTTP callback!")
send("Timestamp: " .. tostring(os.time()))
send("Ceci est un test de log en temps reel")
send("=============================")

-- Test d'echo
for i = 1, 5 do
    send("Message test #" .. tostring(i))
    wait(0.5)
end

send("=== FIN DU TEST ===")
'''
    
    try:
        r = requests.post("http://localhost:3111/execute", 
                         json={"script": script, "pids": [pid]},
                         timeout=10)
        result = r.json()
        
        if r.status_code == 200:
            print(f"[OK] Script injecte! Status: {r.status_code}")
            return True
        else:
            print(f"[!] Erreur: {result}")
            return False
            
    except Exception as e:
        print(f"[!] Erreur injection: {e}")
        return False

def main():
    print("=" * 70)
    print("LIVE LOGS ROBLOX V2 - HTTP CALLBACK")
    print("=" * 70)
    print("\n[!] AVERTISSEMENT: Cette methode necessite que Roblox")
    print("    puisse faire des requetes HTTP vers localhost")
    print()
    
    # Demarrer le serveur HTTP en arriere-plan
    server_thread = threading.Thread(target=start_http_server, daemon=True)
    server_thread.start()
    time.sleep(1)  # Attendre le demarrage
    
    # Demarrer XenoBridge
    start_xenobridge()
    
    # Obtenir le PID
    pid = get_roblox_pid()
    if not pid:
        print("\n[!] Aucun Roblox detecte!")
        print("    Verifiez que Roblox est ouvert.")
        sys.exit(1)
    
    # Injecter le script
    success = inject_script_with_callback(pid)
    
    if success:
        print("\n[+] Attente des logs... (Appuyez sur Ctrl+C pour arreter)\n")
        print("=" * 70)
        
        try:
            while True:
                # Afficher les logs en attente
                while not LOGS_QUEUE.empty():
                    log = LOGS_QUEUE.get()
                    # Deja affiche dans le handler
                    
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\n[!] Arret...")
            if HTTP_SERVER:
                HTTP_SERVER.shutdown()
            print("[OK] Termine")
    else:
        print("\n[!] Injection echouee")

if __name__ == "__main__":
    main()
