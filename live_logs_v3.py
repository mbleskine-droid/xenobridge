#!/usr/bin/env python3
"""
Live logs Roblox V3 - Utilise writefile pour ecrire dans un fichier
et Python lit ce fichier en temps reel
"""
import subprocess
import time
import requests
import sys
import os
import threading
from datetime import datetime

LOG_FILE = os.path.expandvars("%TEMP%\\roblox_live_logs.txt")
MONITORING = True
LAST_SIZE = 0

def timestamp():
    return datetime.now().strftime("%H:%M:%S")

def tail_file():
    """Lit le fichier de log en temps reel (comme 'tail -f')"""
    global LAST_SIZE, MONITORING
    
    print(f"[+] Monitoring fichier: {LOG_FILE}")
    print("[+] Attente des logs...\n")
    print("=" * 70)
    
    while MONITORING:
        try:
            if os.path.exists(LOG_FILE):
                current_size = os.path.getsize(LOG_FILE)
                
                if current_size > LAST_SIZE:
                    with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(LAST_SIZE)
                        new_lines = f.read()
                    
                    # Afficher les nouvelles lignes
                    for line in new_lines.split('\n'):
                        if line.strip():
                            print(f"[{timestamp()}] [RBX] {line}")
                            sys.stdout.flush()
                    
                    LAST_SIZE = current_size
            else:
                # Creer le fichier s'il n'existe pas
                with open(LOG_FILE, 'w') as f:
                    f.write("")
                
        except Exception as e:
            pass
            
        time.sleep(0.2)

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

def inject_script_with_writefile(pid):
    """Injecte un script qui ecrit dans un fichier"""
    print("[+] Attachement...")
    try:
        requests.post("http://localhost:3111/attach", timeout=5)
    except:
        pass
    
    print("[+] Injection script avec writefile...")
    
    # Nettoyer le fichier avant
    try:
        with open(LOG_FILE, 'w') as f:
            f.write("")
    except:
        pass
    
    script = f'''
-- Utiliser writefile pour ecrire dans un fichier
if writefile then
    local logFile = "{LOG_FILE.replace('\\', '\\\\')}"
    
    local function log(msg)
        local current = ""
        pcall(function()
            -- Lire le contenu actuel
            if isfile and isfile(logFile) then
                current = readfile(logFile) or ""
            end
        end)
        
        -- Ajouter le nouveau message
        current = current .. "[" .. os.date("%H:%M:%S") .. "] " .. msg .. "\\n"
        
        -- Ecrire
        pcall(function()
            writefile(logFile, current)
        end)
    end
    
    log("=== HELLO WORLD FROM MCP ===")
    log("Injection reussie via writefile!")
    log("Timestamp: " .. tostring(os.time()))
    log("Ceci est un test de log en temps reel")
    log("=============================")
    
    -- Envoi de plusieurs messages
    for i = 1, 10 do
        log("Message #" .. tostring(i) .. " - " .. tostring(os.time()))
        wait(0.3)
    end
    
    log("=== FIN DU TEST ===")
else
    print("writefile non disponible")
end
'''
    
    try:
        r = requests.post("http://localhost:3111/execute", 
                         json={"script": script, "pids": [pid]},
                         timeout=10)
        result = r.json()
        
        if r.status_code == 200:
            print(f"[OK] Script injecte! Status: {r.status_code}\n")
            return True
        else:
            print(f"[!] Erreur: {result}")
            return False
            
    except Exception as e:
        print(f"[!] Erreur injection: {e}")
        return False

def main():
    global MONITORING
    
    print("=" * 70)
    print("LIVE LOGS ROBLOX V3 - WRITEFILE + TAIL")
    print("=" * 70)
    print(f"\nFichier de log: {LOG_FILE}")
    print()
    
    # Demarrer le monitoring en arriere-plan
    monitor_thread = threading.Thread(target=tail_file, daemon=True)
    monitor_thread.start()
    
    # Demarrer XenoBridge
    start_xenobridge()
    
    # Obtenir le PID
    pid = get_roblox_pid()
    if not pid:
        print("\n[!] Aucun Roblox detecte!")
        MONITORING = False
        sys.exit(1)
    
    # Injecter
    success = inject_script_with_writefile(pid)
    
    if success:
        print("[+] Les logs vont s'afficher ci-dessus...")
        print("[+] Appuyez sur Ctrl+C pour arreter\n")
        
        try:
            # Maintenir le script actif
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[!] Arret...")
            MONITORING = False
            time.sleep(1)
            print("[OK] Termine")
    else:
        print("\n[!] Injection echouee")
        MONITORING = False

if __name__ == "__main__":
    main()
