#!/usr/bin/env python3
"""Affiche les logs Roblox en temps reel dans la console - Ne s'arrete jamais"""
import subprocess
import time
import requests
import sys
import os
import threading
import queue
from datetime import datetime

logs_queue = queue.Queue()
MONITORING = True

def read_console_output(process):
    """Lit la sortie XenoBridge et affiche les logs interessants"""
    print("\n[+] Monitoring logs Roblox en temps reel...")
    print("=" * 70)
    print("Appuyez sur Ctrl+C pour arreter")
    print("=" * 70 + "\n")
    
    while MONITORING and process.poll() is None:
        try:
            line = process.stdout.readline()
            if line:
                line_str = line.strip()
                logs_queue.put(line_str)
                
                # Afficher seulement les logs RConsole (de Roblox)
                if "[RConsole]" in line_str:
                    # Extraire le message apres [trace] ou [info]
                    parts = line_str.split("[peigneetoile15]:")
                    if len(parts) > 1:
                        msg = parts[1].strip()
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] [RBX] {msg}")
                    else:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] {line_str}")
                        
        except:
            pass
        time.sleep(0.05)

def start_xenobridge():
    """Demarre XenoBridge"""
    bridge_path = r"c:\Users\Zenith__\Documents\windsurf\xeno-re\XenoBridge\bin\Release\net8.0-windows\win-x64\XenoBridge.exe"
    
    print("[+] Demarrage XenoBridge...")
    process = subprocess.Popen(
        [bridge_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    time.sleep(3)
    print("[OK] XenoBridge pret\n")
    return process

def get_roblox_pid():
    """Recupere le PID Roblox"""
    try:
        r = requests.get("http://localhost:3111/clients", timeout=5)
        data = r.json()
        clients = data.get('clients', [])
        
        for c in clients:
            if c['state'] == 3:
                print(f"[+] Roblox detecte: PID {c['pid']} ({c['name']})")
                return c['pid']
    except Exception as e:
        print(f"[!] Erreur: {e}")
    return None

def inject_hello_world(pid):
    """Injecte le script Hello World"""
    print("[+] Attachement a Roblox...")
    try:
        requests.post("http://localhost:3111/attach", timeout=5)
    except:
        pass
    
    print("[+] Injection script Hello World...")
    script = '''
if rconsoleprint then
    rconsoleprint("\n=== HELLO WORLD FROM MCP ===\n")
    rconsoleprint("Injection reussie!\n")
    rconsoleprint("Timestamp: " .. tostring(os.time()) .. "\n")
    rconsoleprint("============================\n")
end
'''
    
    try:
        r = requests.post("http://localhost:3111/execute", 
                         json={"script": script, "pids": [pid]},
                         timeout=10)
        if r.status_code == 200:
            print("[OK] Script injecte!\n")
            return True
    except Exception as e:
        print(f"[!] Erreur injection: {e}")
    return False

def main():
    global MONITORING
    
    print("=" * 70)
    print("LIVE LOGS ROBLOX - AFFICHAGE TEMPS REEL")
    print("=" * 70)
    
    # Demarrer XenoBridge
    bridge_process = start_xenobridge()
    
    # Demarrer le monitoring
    monitor_thread = threading.Thread(target=read_console_output, args=(bridge_process,), daemon=True)
    monitor_thread.start()
    
    # Obtenir PID et injecter
    pid = get_roblox_pid()
    if pid:
        inject_hello_world(pid)
    else:
        print("[!] Aucun Roblox detecte")
        print("    Attente de logs...")
    
    # Boucle infinie d'affichage
    try:
        while True:
            # Verifier si XenoBridge est toujours actif
            if bridge_process.poll() is not None:
                print("\n[!] XenoBridge s'est arrete")
                break
                
            # Afficher les logs en attente
            while not logs_queue.empty():
                log = logs_queue.get()
                # Deja affiche dans le thread, mais on peut traiter ici si besoin
                
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n[!] Arret demande (Ctrl+C)")
        MONITORING = False
        bridge_process.terminate()
        print("[OK] Termine")

if __name__ == "__main__":
    main()
