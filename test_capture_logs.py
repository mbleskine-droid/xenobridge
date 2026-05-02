#!/usr/bin/env python3
"""Test Xeno avec capture de logs via HTTP callback"""
import subprocess
import time
import requests
import sys
import os
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# Stockage des logs reçus
received_logs = []
LOG_SERVER_PORT = 3112
STOP_SERVER = False

class LogHandler(BaseHTTPRequestHandler):
    """Handler pour recevoir les logs de Roblox via HTTP"""
    
    def log_message(self, format, *args):
        # Supprimer les logs par défaut du serveur HTTP
        pass
    
    def do_POST(self):
        global received_logs
        
        if self.path == '/log':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            received_logs.append({
                'timestamp': datetime.now().strftime("%H:%M:%S"),
                'message': post_data
            })
            
            # Afficher en temps réel
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] {post_data}")
            
            self.send_response(200)
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

def start_log_server():
    """Démarre le serveur HTTP pour recevoir les logs"""
    global STOP_SERVER
    
    server = HTTPServer(('localhost', LOG_SERVER_PORT), LogHandler)
    print(f"[OK] Serveur de logs démarré sur http://localhost:{LOG_SERVER_PORT}")
    
    while not STOP_SERVER:
        server.handle_request()
    
    server.server_close()

def start_xenobridge():
    """Démarre XenoBridge"""
    bridge_path = r"c:\Users\Zenith__\Documents\windsurf\xeno-re\XenoBridge\bin\Release\net8.0-windows\win-x64\XenoBridge.exe"
    
    print("[1] Démarrage XenoBridge...")
    subprocess.Popen([bridge_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
    time.sleep(3)
    print("    OK - XenoBridge prêt")

def get_roblox_pid():
    """Récupère le PID du processus Roblox"""
    print("\n[2] Recherche du processus Roblox...")
    
    try:
        r = requests.get("http://localhost:3111/clients", timeout=5)
        data = r.json()
        clients = data.get('clients', [])
        
        for c in clients:
            print(f"    - PID {c['pid']}: {c['name']} (State: {c['state']})")
            if c['state'] == 3:
                print(f"    OK - PID cible: {c['pid']}")
                return c['pid']
                
        if clients:
            print(f"    [!] Aucun client en state 3, utilisation du premier PID: {clients[0]['pid']}")
            return clients[0]['pid']
            
    except Exception as e:
        print(f"    [ERREUR] {e}")
        
    return None

def attach_and_inject(pid):
    """Attache et injecte le script de test"""
    
    print("\n[3] Attachement à Roblox...")
    try:
        r = requests.post("http://localhost:3111/attach", timeout=5)
        print(f"    Status: {r.status_code}")
    except Exception as e:
        print(f"    [ERREUR] {e}")
        return False
    
    # Script Lua qui envoie les logs via HTTP POST
    print("\n[4] Préparation du script avec capture HTTP...")
    script = f'''
local HttpService = game:GetService("HttpService")
local LOG_URL = "http://localhost:{LOG_SERVER_PORT}/log"

local function sendLog(msg)
    pcall(function()
        HttpService:PostAsync(LOG_URL, msg, Enum.HttpContentType.TextPlain)
    end)
    print(msg)  -- Aussi print pour console Roblox
end

sendLog("========================================")
sendLog("  HELLO WORLD FROM MCP!")
sendLog("  Test d injection XenoBridge")
sendLog("  Timestamp: " .. tostring(os.time()))
sendLog("  PlaceId: " .. tostring(game.PlaceId))
sendLog("========================================")
sendLog("  [OK] Injection et capture HTTP reussies!")
sendLog("  [INFO] Ce message est capture en temps reel")
sendLog("  [INFO] par le serveur MCP local")
sendLog("========================================")
'''
    
    print("    Script prêt (utilise HttpService)")
    print("\n[5] Injection du script...")
    
    try:
        payload = {
            "script": script,
            "pids": [pid]
        }
        r = requests.post("http://localhost:3111/execute", 
                         json=payload,
                         timeout=10)
        
        result = r.json()
        print(f"    Status HTTP: {r.status_code}")
        print(f"    Résultat: {result}")
        
        if r.status_code == 200:
            print("\n    [SUCCESS] Script injecté!")
            return True
        else:
            print(f"\n    [ECHEC] Erreur: {result}")
            return False
            
    except Exception as e:
        print(f"    [ERREUR] {e}")
        return False

def main():
    global STOP_SERVER, received_logs
    
    print("=" * 70)
    print("TEST XENO - CAPTURE DE LOGS EN TEMPS RÉEL VIA HTTP")
    print("=" * 70)
    print("\nMéthode: Le script Lua envoie les logs via HTTP POST")
    print("         vers un serveur local qui les affiche en temps réel")
    
    # Démarrer le serveur de logs en arrière-plan
    print("\n[0] Démarrage du serveur de capture...")
    log_server_thread = threading.Thread(target=start_log_server, daemon=True)
    log_server_thread.start()
    time.sleep(1)  # Attendre que le serveur démarre
    
    # Démarrer XenoBridge
    start_xenobridge()
    
    # Obtenir le PID Roblox
    pid = get_roblox_pid()
    if not pid:
        print("\n[ERREUR] Aucun processus Roblox trouvé!")
        STOP_SERVER = True
        sys.exit(1)
    
    print("\n[LOGS EN TEMPS RÉEL]")
    print("=" * 60)
    
    # Attacher et injecter
    success = attach_and_inject(pid)
    
    if success:
        print("\n[6] Attente des logs (10 secondes)...")
        print("    Les logs apparaissent ci-dessus en temps réel:\n")
        
        time.sleep(10)
        
        print("\n" + "=" * 60)
        print("[7] Vérification finale...")
        
        # Chercher le Hello World dans les logs reçus
        found = False
        for log_entry in received_logs:
            if "HELLO WORLD FROM MCP" in log_entry['message']:
                found = True
                break
        
        if found:
            print("    [✓✓✓] SUCCESS! Hello World capturé en temps réel!")
        else:
            print("    [!] Hello World non capturé")
            print(f"    Total logs reçus: {len(received_logs)}")
            if received_logs:
                print("    Logs reçus:")
                for log in received_logs:
                    print(f"      - {log['timestamp']}: {log['message'][:50]}...")
    
    # Arrêter le serveur
    STOP_SERVER = True
    try:
        # Envoyer une requête pour débloquer le serveur
        requests.get(f"http://localhost:{LOG_SERVER_PORT}/health", timeout=1)
    except:
        pass
    
    log_server_thread.join(timeout=2)
    
    print("\n" + "=" * 70)
    print("TEST TERMINÉ")
    print("=" * 70)
    print("\nXenoBridge tourne encore dans sa console.")
    print("Fermez la fenêtre XenoBridge pour arrêter.")

if __name__ == "__main__":
    main()
