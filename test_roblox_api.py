#!/usr/bin/env python3
"""Test Xeno avec différentes méthodes de capture de logs"""
import subprocess
import time
import requests
import sys
import os
import threading
import queue
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# Queue pour les logs
log_queue = queue.Queue()
LOG_SERVER_PORT = 3113
STOP_SERVER = False

class LogHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def do_POST(self):
        if self.path == '/log':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            log_queue.put(post_data)
            print(f"  [LOG] {post_data}")
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

def start_log_server():
    global STOP_SERVER
    server = HTTPServer(('localhost', LOG_SERVER_PORT), LogHandler)
    while not STOP_SERVER:
        try:
            server.handle_request()
        except:
            pass
    server.server_close()

def start_xenobridge():
    bridge_path = r"c:\Users\Zenith__\Documents\windsurf\xeno-re\XenoBridge\bin\Release\net8.0-windows\win-x64\XenoBridge.exe"
    print("[1] Demarrage XenoBridge...")
    subprocess.Popen([bridge_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
    time.sleep(3)
    print("    OK")

def get_roblox_pid():
    print("\n[2] Recherche processus Roblox...")
    try:
        r = requests.get("http://localhost:3111/clients", timeout=5)
        data = r.json()
        clients = data.get('clients', [])
        
        for c in clients:
            print(f"    - PID {c['pid']}: {c['name']} (State: {c['state']})")
            if c['state'] == 3:
                print(f"    OK - PID: {c['pid']}")
                return c['pid']
    except Exception as e:
        print(f"    ERREUR: {e}")
    return None

def test_with_rconsole():
    """Test avec rconsoleprint (fonction exécuteur)"""
    pid = get_roblox_pid()
    if not pid:
        print("[!] Aucun processus trouve")
        return False
    
    print("\n[3] Attachement...")
    try:
        requests.post("http://localhost:3111/attach", timeout=5)
    except:
        pass
    
    print("\n[4] Test avec rconsoleprint...")
    script = '''
if rconsoleprint then
    rconsoleprint("========================================\\n")
    rconsoleprint("  HELLO WORLD FROM MCP!\\n")
    rconsoleprint("  (via rconsoleprint)\\n")
    rconsoleprint("========================================\\n")
else
    print("rconsoleprint non disponible")
end
'''
    
    try:
        r = requests.post("http://localhost:3111/execute", 
                         json={"script": script, "pids": [pid]},
                         timeout=10)
        print(f"    Status: {r.status_code}")
        print(f"    Result: {r.json()}")
        return r.status_code == 200
    except Exception as e:
        print(f"    ERREUR: {e}")
        return False

def test_with_writefile():
    """Test avec writefile (fonction exécuteur fichier)"""
    pid = get_roblox_pid()
    if not pid:
        return False
    
    print("\n[5] Test avec writefile...")
    log_path = os.path.expandvars("%TEMP%\\xeno_test_rbx.log")
    
    script = f'''
if writefile then
    local content = "========================================\\n"
    content = content .. "  HELLO WORLD FROM MCP!\\n"
    content = content .. "  (via writefile)\\n"
    content = content .. "  Timestamp: " .. tostring(os.time()) .. "\\n"
    content = content .. "========================================\\n"
    
    writefile("{log_path.replace('\\', '\\\\')}", content)
    print("Fichier ecrit: {log_path.replace('\\', '\\\\')}")
else
    print("writefile non disponible")
end
'''
    
    try:
        r = requests.post("http://localhost:3111/execute", 
                         json={"script": script, "pids": [pid]},
                         timeout=10)
        print(f"    Status: {r.status_code}")
        print(f"    Result: {r.json()}")
        
        time.sleep(2)
        
        # Lire le fichier
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                content = f.read()
            print(f"\n    Contenu fichier:")
            print("    " + "-" * 40)
            for line in content.split('\n'):
                print(f"    {line}")
            print("    " + "-" * 40)
            return "HELLO WORLD" in content
        else:
            print(f"    [!] Fichier non cree: {log_path}")
            return False
            
    except Exception as e:
        print(f"    ERREUR: {e}")
        return False

def test_with_request_async():
    """Test avec request async (moins restrictif)"""
    pid = get_roblox_pid()
    if not pid:
        return False
    
    print("\n[6] Test avec RequestAsync...")
    
    # Démarrer le serveur de logs
    global STOP_SERVER
    STOP_SERVER = False
    server_thread = threading.Thread(target=start_log_server, daemon=True)
    server_thread.start()
    time.sleep(1)
    
    script = f'''
local HttpService = game:GetService("HttpService")

-- Essayer RequestAsync (moins restrictif que PostAsync)
local success, result = pcall(function()
    local response = HttpService:RequestAsync({{
        Url = "http://localhost:{LOG_SERVER_PORT}/log",
        Method = "POST",
        Body = "HELLO WORLD FROM MCP (via RequestAsync)",
        Headers = {{
            ["Content-Type"] = "text/plain"
        }}
    }})
    return response
end)

if success then
    print("RequestAsync OK")
else
    print("RequestAsync ERREUR: " .. tostring(result))
end

-- Fallback sur print
print("=== HELLO WORLD FROM MCP ===")
print("Test en cours...")
'''
    
    try:
        r = requests.post("http://localhost:3111/execute", 
                         json={"script": script, "pids": [pid]},
                         timeout=10)
        print(f"    Status: {r.status_code}")
        
        time.sleep(5)
        
        STOP_SERVER = True
        try:
            requests.get(f"http://localhost:{LOG_SERVER_PORT}/health", timeout=1)
        except:
            pass
        
        # Vérifier les logs reçus
        logs_received = []
        while not log_queue.empty():
            logs_received.append(log_queue.get())
        
        if logs_received:
            print(f"    [OK] Logs recus: {len(logs_received)}")
            for log in logs_received:
                print(f"      - {log}")
            return True
        else:
            print("    [!] Aucun log recu")
            return False
            
    except Exception as e:
        print(f"    ERREUR: {e}")
        return False

def main():
    print("=" * 70)
    print("TEST XENO - MULTI-METHODES DE CAPTURE DE LOGS")
    print("=" * 70)
    
    start_xenobridge()
    
    print("\n" + "=" * 70)
    print("TESTS")
    print("=" * 70)
    
    # Test 1: rconsoleprint
    result1 = test_with_rconsole()
    time.sleep(2)
    
    # Test 2: writefile
    result2 = test_with_writefile()
    time.sleep(2)
    
    # Test 3: RequestAsync
    result3 = test_with_request_async()
    
    print("\n" + "=" * 70)
    print("RESULTATS")
    print("=" * 70)
    print(f"  rconsoleprint: {'OK' if result1 else 'ECHEC'}")
    print(f"  writefile:     {'OK' if result2 else 'ECHEC'}")
    print(f"  RequestAsync:  {'OK' if result3 else 'ECHEC'}")
    
    if result1 or result2 or result3:
        print("\n  [SUCCESS] Au moins une methode fonctionne!")
    else:
        print("\n  [!] Aucune methode n'a fonctionne")
        print("      Le script s'execute mais les logs ne sont pas captures")
    
    print("\n" + "=" * 70)
    print("XenoBridge tourne encore. Fermez sa console pour arreter.")

if __name__ == "__main__":
    main()
