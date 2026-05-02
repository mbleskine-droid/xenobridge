#!/usr/bin/env python3
"""Test Xeno avec récupération de logs en temps réel - Fonctionne sans UI"""
import subprocess
import time
import requests
import sys
import os
import threading
from datetime import datetime

# Fichier log temporaire pour Roblox
LOG_FILE = os.path.expandvars("%TEMP%\\xeno_mcp_test.log")
STOP_MONITORING = False

def clear_log():
    """Vide le fichier log"""
    try:
        with open(LOG_FILE, 'w') as f:
            f.write(f"=== Log démarré à {datetime.now()} ===\n")
    except:
        pass

def read_log():
    """Lit le contenu du fichier log"""
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        return ""
    except Exception as e:
        return f"[Erreur lecture log: {e}]"

def monitor_log_realtime():
    """Monitor le fichier log en temps réel et affiche les nouvelles lignes"""
    global STOP_MONITORING
    last_size = 0
    
    print("\n[MONITOR] Démarrage du monitoring temps réel...")
    print("=" * 60)
    
    while not STOP_MONITORING:
        try:
            if os.path.exists(LOG_FILE):
                current_size = os.path.getsize(LOG_FILE)
                
                if current_size > last_size:
                    with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(last_size)
                        new_content = f.read()
                        
                    if new_content.strip():
                        for line in new_content.strip().split('\n'):
                            if line.strip():
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                print(f"  [{timestamp}] {line}")
                    
                    last_size = current_size
                    
        except Exception as e:
            pass
            
        time.sleep(0.5)
    
    print("=" * 60)
    print("[MONITOR] Arrêt du monitoring")

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
    global STOP_MONITORING
    
    print("\n[3] Attachement à Roblox...")
    try:
        r = requests.post("http://localhost:3111/attach", timeout=5)
        print(f"    Status: {r.status_code}")
    except Exception as e:
        print(f"    [ERREUR] {e}")
        return False
    
    # Script Lua qui écrit dans un fichier + print dans console
    print("\n[4] Préparation du script de test...")
    script = f'''
-- Script de test MCP avec logging vers fichier
local logFile = "{LOG_FILE.replace('\\', '\\\\')}"

local function log(msg)
    -- Écrire dans fichier
    local f = io.open(logFile, "a")
    if f then
        f:write("[" .. os.date("%H:%M:%S") .. "] " .. msg .. "\\n")
        f:close()
    end
    -- Aussi print pour la console Roblox (si visible)
    print(msg)
end

log("========================================")
log("  HELLO WORLD FROM MCP!")
log("  Test d'injection XenoBridge")
log("  Timestamp: " .. tostring(os.time()))
log("  PID: " .. tostring(game.PlaceId))
log("========================================")
log("  [OK] Injection réussie!")
log("  [INFO] Ce message est écrit dans le fichier log")
log("  [INFO] et peut être lu même sans UI Roblox")
log("========================================")
'''
    
    print("    Script prêt")
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
    global STOP_MONITORING
    
    print("=" * 70)
    print("TEST XENO - LOGS EN TEMPS RÉEL (FONCTIONNE SANS UI)")
    print("=" * 70)
    
    # Nettoyer le log précédent
    clear_log()
    
    # Démarrer XenoBridge
    start_xenobridge()
    
    # Obtenir le PID Roblox
    pid = get_roblox_pid()
    if not pid:
        print("\n[ERREUR] Aucun processus Roblox trouvé!")
        print("    Démarrez Roblox d'abord.")
        sys.exit(1)
    
    # Démarrer le monitoring en arrière-plan AVANT l'injection
    monitor_thread = threading.Thread(target=monitor_log_realtime, daemon=True)
    monitor_thread.start()
    
    # Attendre un peu que le monitoring démarre
    time.sleep(1)
    
    # Attacher et injecter
    success = attach_and_inject(pid)
    
    if success:
        print("\n[6] Attente des logs (5 secondes)...")
        time.sleep(5)
        
        print("\n[7] Vérification finale du fichier log...")
        log_content = read_log()
        
        if "HELLO WORLD FROM MCP" in log_content:
            print("    [✓] Hello World confirmé dans les logs!")
        else:
            print("    [!] Hello World non trouvé dans les logs")
            print("    Contenu du log:")
            print("-" * 40)
            print(log_content if log_content else "(fichier vide)")
            print("-" * 40)
    
    # Arrêter le monitoring
    STOP_MONITORING = True
    monitor_thread.join(timeout=2)
    
    print("\n" + "=" * 70)
    print("TEST TERMINÉ")
    print("=" * 70)
    print(f"\nFichier log: {LOG_FILE}")
    print("\nXenoBridge tourne encore dans sa console.")
    print("Fermez la fenêtre XenoBridge pour arrêter.")
    
    # Afficher le contenu final du log
    print("\n--- CONTENU FINAL DU LOG ---")
    final_log = read_log()
    print(final_log if final_log else "(vide)")
    print("--- FIN DU LOG ---")

if __name__ == "__main__":
    main()
