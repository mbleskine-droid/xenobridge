#!/usr/bin/env python3
"""Test Hello World from MCP avec XenoBridge"""
import subprocess
import time
import requests
import sys

# Démarrer XenoBridge en arrière-plan
print("=" * 60)
print("TEST INJECTION XENO - HELLO WORLD FROM MCP")
print("=" * 60)

print("\n[1] Demarrage XenoBridge...")
bridge_path = r"c:\Users\Zenith__\Documents\windsurf\xeno-re\XenoBridge\bin\Release\net8.0-windows\win-x64\XenoBridge.exe"
subprocess.Popen([bridge_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
time.sleep(3)

# Test clients pour obtenir le PID
print("\n[2] Recuperation des clients Roblox...")
try:
    r = requests.get("http://localhost:3111/clients", timeout=5)
    data = r.json()
    clients = data.get('clients', [])
    print(f"    Clients trouves: {len(clients)}")
    
    target_pid = None
    for c in clients:
        print(f"      - PID {c['pid']}: {c['name']} (State: {c['state']})")
        if c['state'] == 3:  # Ready state
            target_pid = c['pid']
            
    if not target_pid:
        print("    [!] Aucun client en state 3 trouve!")
        sys.exit(1)
        
    print(f"    [OK] PID cible: {target_pid}")
except Exception as e:
    print(f"    [ERREUR] {e}")
    sys.exit(1)

# Test attach
print("\n[3] Attachement a Roblox...")
try:
    r = requests.post("http://localhost:3111/attach", timeout=5)
    print(f"    Status: {r.status_code}")
    print(f"    Resultat: {r.json()}")
except Exception as e:
    print(f"    [ERREUR] {e}")

# Test execute hello world avec PID explicite
print("\n[4] Execution du script 'Hello World from MCP'...")
print("    Script Lua:")
script = '''
print("========================================")
print("  HELLO WORLD FROM MCP!")
print("  Injection via XenoBridge reussie!")
print("  Timestamp: " .. tostring(os.time()))
print("========================================")
'''
for line in script.strip().split('\n'):
    print(f"      {line}")

try:
    payload = {
        "script": script,
        "pids": [target_pid]  # PID explicite
    }
    r = requests.post("http://localhost:3111/execute", 
                     json=payload,
                     timeout=10)
    print(f"\n    Status HTTP: {r.status_code}")
    print(f"    Reponse: {r.json()}")
    
    if r.status_code == 200:
        print("\n    [SUCCESS] Script envoye a Roblox!")
        print("    Verifiez la console Roblox/F9 pour voir le 'Hello World'")
    else:
        print(f"\n    [ECHEC] Erreur {r.status_code}")
        
except Exception as e:
    print(f"    [ERREUR] {e}")

print("\n" + "=" * 60)
print("TEST TERMINE")
print("=" * 60)
print("\nXenoBridge tourne encore dans sa console.")
print("Fermez la fenetre console XenoBridge pour l'arreter.")
