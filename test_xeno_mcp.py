#!/usr/bin/env python3
"""
Test XenoBridge avec injection dans le processus en cours
et verification du "hello world from mcp"
"""

import subprocess
import time
import requests
import json
import sys
import os
import psutil

def start_xenobridge():
    """Demarre XenoBridge et retourne le processus"""
    bridge_path = r"c:\Users\Zenith__\Documents\windsurf\xeno-re\XenoBridge\bin\Release\net8.0-windows\win-x64\XenoBridge.exe"
    
    print("[+] Demarrage de XenoBridge...")
    print(f"    Executable: {bridge_path}")
    
    # Demarrer avec redirection des flux pour capturer la sortie
    process = subprocess.Popen(
        [bridge_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Attendre que le serveur demarre
    time.sleep(2)
    
    return process

def test_health():
    """Teste le endpoint health"""
    try:
        response = requests.get("http://localhost:3111/health", timeout=5)
        print(f"[OK] Health check: {response.status_code}")
        print(f"     Reponse: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"[ERREUR] Health check echoue: {e}")
        return None

def test_version():
    """Teste le endpoint version"""
    try:
        response = requests.get("http://localhost:3111/version", timeout=5)
        print(f"[OK] Version: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"[ERREUR] Version check echoue: {e}")
        return None

def test_attach():
    """Teste l'attachement a Roblox"""
    try:
        print("\n[+] Test d'attachement...")
        response = requests.post("http://localhost:3111/attach", timeout=10)
        print(f"     Status: {response.status_code}")
        print(f"     Reponse: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"[ERREUR] Attach echoue: {e}")
        return None

def test_clients():
    """Recupere la liste des clients Roblox"""
    try:
        print("\n[+] Recuperation des clients...")
        response = requests.get("http://localhost:3111/clients", timeout=5)
        data = response.json()
        print(f"     Status: {response.status_code}")
        print(f"     Clients trouves: {len(data.get('clients', []))}")
        for client in data.get('clients', []):
            print(f"        - PID {client['pid']}: {client['name']} (State: {client['state']})")
        return data
    except Exception as e:
        print(f"[ERREUR] Get clients echoue: {e}")
        return None

def test_execute_hello_world():
    """Execute un script 'hello world from mcp'"""
    try:
        print("\n[+] Execution du script 'hello world from mcp'...")
        
        # Script Lua pour Roblox
        script = '''
-- Hello World from MCP
print("=== HELLO WORLD FROM MCP ===")
print("[OK] Injection reussie via MCP!")
print("[INFO] Timestamp: " .. tostring(os.time()))
print("[INFO] Process PID detecte par Xeno")
print("=== END HELLO WORLD ===")
        '''
        
        payload = {
            "script": script,
            "pids": []  # Laisser XenoBridge auto-detecter
        }
        
        response = requests.post(
            "http://localhost:3111/execute",
            json=payload,
            timeout=10
        )
        
        print(f"     Status: {response.status_code}")
        print(f"     Reponse: {json.dumps(response.json(), indent=2)}")
        return response.json()
    except Exception as e:
        print(f"[ERREUR] Execute echoue: {e}")
        return None

def get_console_output(process, timeout=5):
    """Recupere la sortie console de XenoBridge"""
    print("\n[+] Recuperation de la sortie console...")
    
    # Lire la sortie disponible
    output_lines = []
    
    print(f"     Processus XenoBridge:")
    print(f"        - PID: {process.pid}")
    print(f"        - Statut: {'En cours' if process.poll() is None else 'Termine'}")
    print(f"        - Return code: {process.poll()}")
    
    return output_lines

def main():
    print("=" * 60)
    print("TEST XENO BRIDGE - INJECTION ET HELLO WORLD")
    print("=" * 60)
    
    # Verifier si Roblox est en cours d'execution
    roblox_processes = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'roblox' in proc.info['name'].lower():
                roblox_processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    print(f"\n[*] Processus Roblox trouves: {len(roblox_processes)}")
    for p in roblox_processes:
        print(f"    - PID {p['pid']}: {p['name']}")
    
    # Demarrer XenoBridge
    bridge_process = start_xenobridge()
    
    try:
        # Tests API
        print("\n" + "=" * 60)
        print("TESTS API")
        print("=" * 60)
        
        health = test_health()
        version = test_version()
        
        # Test attach
        attach_result = test_attach()
        
        # Test clients
        clients = test_clients()
        
        # Test execution (seulement si des clients sont trouves)
        if clients and len(clients.get('clients', [])) > 0:
            ready_clients = [c for c in clients['clients'] if c['state'] == 3]
            if ready_clients:
                execute_result = test_execute_hello_world()
            else:
                print("\n[!] Aucun client en state=3 (pret). Execution ignoree.")
                print("    Roblox doit etre attache et pret.")
        else:
            print("\n[!] Aucun client Roblox trouve. Execution ignoree.")
            print("    Demarrez Roblox et reessayez.")
        
        # Recuperer la sortie console
        console_output = get_console_output(bridge_process)
        
        print("\n" + "=" * 60)
        print("RESUME")
        print("=" * 60)
        print(f"[OK] Health: {'OK' if health else 'ECHEC'}")
        print(f"[OK] Version: {version.get('version', 'N/A') if version else 'ECHEC'}")
        print(f"[OK] Attach: {'OK' if attach_result else 'ECHEC'}")
        print(f"[OK] Clients: {len(clients.get('clients', [])) if clients else 0} trouves")
        
        if not roblox_processes:
            print("\n[!] NOTE: Aucun processus Roblox detecte!")
            print("    Pour un test complet, demarrez Roblox d'abord.")
        
        print("\n[OK] Test termine. Appuyez sur Ctrl+C pour arreter XenoBridge.")
        
        # Attendre l'interruption
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n[!] Arret demande par l'utilisateur...")
    finally:
        # Nettoyer
        if bridge_process.poll() is None:
            print("[+] Arret de XenoBridge...")
            bridge_process.terminate()
            bridge_process.wait(timeout=5)
        
        print("[OK] Termine!")

if __name__ == "__main__":
    main()
