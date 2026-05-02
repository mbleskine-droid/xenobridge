#!/usr/bin/env python3
"""Test Xeno final - Capture logs en temps réel via rconsoleprint"""
import subprocess
import time
import requests
import sys
import os
import threading
import queue
from datetime import datetime

# Queue pour stocker les logs
logs_queue = queue.Queue()
MONITORING = True

def read_console_output(process):
    """Lit la sortie console de XenoBridge en temps réel"""
    global MONITORING
    
    print("\n[MONITOR] Demarrage lecture console XenoBridge...")
    print("=" * 60)
    
    while MONITORING and process.poll() is None:
        try:
            # Lire stdout
            import select
            # Note: select ne fonctionne pas bien sur Windows avec pipes
            # On utilise une approche simple
            line = process.stdout.readline()
            if line:
                line_str = line.strip()
                logs_queue.put(line_str)
                # Afficher si c'est un log interessant
                if "HELLO" in line_str or "MCP" in line_str or "rconsole" in line_str.lower():
                    print(f"  [XENO] {line_str}")
        except:
            pass
        time.sleep(0.1)

def start_xenobridge_with_capture():
    """Demarre XenoBridge avec capture de la sortie"""
    bridge_path = r"c:\Users\Zenith__\Documents\windsurf\xeno-re\XenoBridge\bin\Release\net8.0-windows\win-x64\XenoBridge.exe"
    
    print("[1] Demarrage XenoBridge avec capture console...")
    
    # Lancer avec capture des flux
    process = subprocess.Popen(
        [bridge_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
    
    # Attendre le demarrage
    time.sleep(3)
    
    # Demarrer le thread de monitoring
    monitor_thread = threading.Thread(target=read_console_output, args=(process,), daemon=True)
    monitor_thread.start()
    
    return process, monitor_thread

def get_roblox_pid():
    """Recupere le PID Roblox"""
    print("\n[2] Recherche processus Roblox...")
    try:
        r = requests.get("http://localhost:3111/clients", timeout=5)
        data = r.json()
        clients = data.get('clients', [])
        
        for c in clients:
            print(f"    - PID {c['pid']}: {c['name']} (State: {c['state']})")
            if c['state'] == 3:
                print(f"    [OK] PID cible: {c['pid']}")
                return c['pid']
    except Exception as e:
        print(f"    [ERREUR] {e}")
    return None

def inject_hello_world(pid):
    """Injecte le script Hello World avec rconsoleprint"""
    print("\n[3] Attachement a Roblox...")
    try:
        r = requests.post("http://localhost:3111/attach", timeout=5)
        print(f"    Status: {r.status_code}")
    except Exception as e:
        print(f"    [ERREUR] {e}")
        return False
    
    print("\n[4] Preparation script Hello World...")
    script = '''
-- Hello World from MCP via XenoBridge
if rconsoleprint then
    rconsoleprint("\\n========================================\\n")
    rconsoleprint("  [HELLO WORLD FROM MCP]\\n")
    rconsoleprint("  Injection via XenoBridge reussie!\\n")
    rconsoleprint("  Timestamp: " .. tostring(os.time()) .. "\\n")
    rconsoleprint("========================================\\n")
    rconsoleprint("  [STATUS] Execution OK\\n")
    rconsoleprint("========================================\\n")
else
    print("[MCP] Hello World - rconsoleprint non disponible")
end

-- Message aussi dans print normal
print("[MCP] Hello World from MCP via print()")
'''
    
    print("    Script Lua:")
    for line in script.strip().split('\n'):
        print(f"      {line}")
    
    print("\n[5] Injection...")
    try:
        r = requests.post("http://localhost:3111/execute", 
                         json={"script": script, "pids": [pid]},
                         timeout=10)
        
        result = r.json()
        print(f"    Status HTTP: {r.status_code}")
        print(f"    Resultat: {result}")
        
        if r.status_code == 200:
            print("\n    [SUCCESS] Script injecte!")
            return True
        else:
            print(f"\n    [ECHEC]")
            return False
            
    except Exception as e:
        print(f"    [ERREUR] {e}")
        return False

def wait_and_check_logs(timeout=10):
    """Attend et verifie les logs"""
    print(f"\n[6] Attente des logs ({timeout}s)...")
    
    start_time = time.time()
    found_hello = False
    
    while time.time() - start_time < timeout:
        # Verifier si on a recu des logs
        while not logs_queue.empty():
            log = logs_queue.get()
            if "HELLO WORLD FROM MCP" in log:
                found_hello = True
                print(f"\n    [OK] [OK] [OK] CAPTURE EN TEMPS REEL: {log}")
        
        if found_hello:
            break
            
        time.sleep(0.5)
    
    return found_hello

def main():
    global MONITORING
    
    print("=" * 70)
    print("TEST XENO - CAPTURE TEMPS REEL VIA RCONSOLEPRINT")
    print("=" * 70)
    
    # Démarrer XenoBridge avec capture
    bridge_process, monitor_thread = start_xenobridge_with_capture()
    
    # Obtenir PID
    pid = get_roblox_pid()
    if not pid:
        print("\n[ERREUR] Aucun processus Roblox!")
        MONITORING = False
        bridge_process.terminate()
        sys.exit(1)
    
    # Injecter
    success = inject_hello_world(pid)
    
    if success:
        # Attendre et capturer
        found = wait_and_check_logs(timeout=10)
        
        print("\n" + "=" * 60)
        print("RESULTAT")
        print("=" * 60)
        
        if found:
            print("  [OK] [OK] [OK] SUCCESS!")
            print("  Le 'Hello World from MCP' a ete capture en temps reel!")
            print("  La methode rconsoleprint fonctionne!")
        else:
            print("  [!] Hello World non capture dans les logs console")
            print("  Mais le script a ete injecte avec succes (HTTP 200)")
            print("\n  Les logs rconsoleprint peuvent etre dans une console separee")
            print("  ou necessitent une configuration specifique de Xeno.")
    
    # Arreter
    MONITORING = False
    time.sleep(1)
    
    print("\n" + "=" * 70)
    print("TEST TERMINE")
    print("=" * 70)
    
    print("\n[XenoBridge]")
    print("  - Le processus tourne toujours")
    print("  - Fermez la fenetre ou faites Ctrl+C pour arreter")
    
    # Option pour arreter
    print("\n[?] Voulez-vous arreter XenoBridge? (o/n): ", end="")
    try:
        response = input().strip().lower()
        if response == 'o':
            print("  Arret de XenoBridge...")
            bridge_process.terminate()
            bridge_process.wait(timeout=5)
            print("  [OK] Arrete")
    except:
        pass

if __name__ == "__main__":
    main()
