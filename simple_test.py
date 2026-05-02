#!/usr/bin/env python3
"""Test simple de XenoBridge"""
import subprocess
import time
import requests
import sys

# Démarrer XenoBridge en arrière-plan
print("[1] Démarrage XenoBridge...")
bridge_path = r"c:\Users\Zenith__\Documents\windsurf\xeno-re\XenoBridge\bin\Release\net8.0-windows\win-x64\XenoBridge.exe"

# Lancer sans bloquer
subprocess.Popen([bridge_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
time.sleep(3)  # Attendre le démarrage

# Test health
print("\n[2] Test Health...")
try:
    r = requests.get("http://localhost:3111/health", timeout=5)
    print(f"    Status: {r.status_code}")
    print(f"    Data: {r.json()}")
except Exception as e:
    print(f"    ERREUR: {e}")

# Test version
print("\n[3] Test Version...")
try:
    r = requests.get("http://localhost:3111/version", timeout=5)
    print(f"    Status: {r.status_code}")
    print(f"    Data: {r.json()}")
except Exception as e:
    print(f"    ERREUR: {e}")

# Test clients
print("\n[4] Test Clients (liste des process Roblox)...")
try:
    r = requests.get("http://localhost:3111/clients", timeout=5)
    data = r.json()
    print(f"    Status: {r.status_code}")
    print(f"    Nombre de clients: {len(data.get('clients', []))}")
    for c in data.get('clients', []):
        print(f"      - PID {c['pid']}: {c['name']} (State: {c['state']})")
except Exception as e:
    print(f"    ERREUR: {e}")

# Test attach
print("\n[5] Test Attach...")
try:
    r = requests.post("http://localhost:3111/attach", timeout=5)
    print(f"    Status: {r.status_code}")
    print(f"    Data: {r.json()}")
except Exception as e:
    print(f"    ERREUR: {e}")

# Test execute hello world
print("\n[6] Test Execute 'Hello World from MCP'...")
try:
    script = '''
print("=== HELLO WORLD FROM MCP ===")
print("[OK] Injection et execution reussies!")
print("=== END HELLO WORLD ===")
'''
    r = requests.post("http://localhost:3111/execute", 
                     json={"script": script, "pids": []},
                     timeout=10)
    print(f"    Status: {r.status_code}")
    print(f"    Data: {r.json()}")
except Exception as e:
    print(f"    ERREUR: {e}")

print("\n[7] Tests termines!")
print("    XenoBridge tourne encore. Fermez la console manuellement.")
