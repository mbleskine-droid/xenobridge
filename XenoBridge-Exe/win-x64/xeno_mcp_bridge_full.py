"""
xeno_mcp_bridge_full.py — Xeno MCP avec Bridge intégré

Ce MCP :
1. Lance automatiquement XenoBridge.exe au démarrage
2. Attend que le Bridge soit prêt (health check)
3. Utilise le Bridge (port 3111) au lieu de Xeno natif (port 3110)
4. Gère l'auto-détection des clients (state=3)

Install:  pip install fastmcp requests psutil
Run:      python xeno_mcp_bridge_full.py
"""

import json
import requests
import time
import uuid
import subprocess
import os
import signal
import atexit
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP

# Configuration du Bridge
BRIDGE_URL = "http://localhost:3111"
BRIDGE_PATH = Path("C:/Users/Zenith__/Documents/windsurf/xeno-re/XenoBridge/bin/Release/net8.0-windows/win-x64/XenoBridge.exe")
TIMEOUT = 10

# Variable globale pour le processus Bridge
_bridge_process: Optional[subprocess.Popen] = None

mcp = FastMCP("Xeno Bridge Executor")

# ═══════════════════════════════════════════════════════════════════════════════
# GESTION DU BRIDGE
# ═══════════════════════════════════════════════════════════════════════════════

def find_bridge_executable() -> Path:
    """Trouver l'exécutable XenoBridge.exe"""
    # Chemins possibles
    possible_paths = [
        BRIDGE_PATH,
        Path("XenoBridge/bin/Release/net8.0-windows/win-x64/XenoBridge.exe"),
        Path("XenoBridge/bin/Debug/net8.0-windows/win-x64/XenoBridge.exe"),
        Path("../XenoBridge/bin/Release/net8.0-windows/win-x64/XenoBridge.exe"),
        Path("./XenoBridge.exe"),
    ]
    
    for path in possible_paths:
        if path.exists():
            return path.resolve()
    
    # Chercher dans le répertoire courant et parent
    for root in [Path("."), Path("..")]:
        for pattern in ["**/XenoBridge.exe", "**/win-x64/XenoBridge.exe"]:
            matches = list(root.glob(pattern))
            if matches:
                return matches[0].resolve()
    
    raise FileNotFoundError("XenoBridge.exe non trouvé. Compilez-le d'abord avec 'dotnet build'")

def start_bridge() -> subprocess.Popen:
    """Démarrer le Bridge C# comme sous-processus"""
    global _bridge_process
    
    if _bridge_process is not None and _bridge_process.poll() is None:
        print("ℹ️  Bridge déjà en cours d'exécution")
        return _bridge_process
    
    bridge_exe = find_bridge_executable()
    print(f"🚀 Démarrage du Bridge : {bridge_exe}")
    
    # Lancer le bridge en arrière-plan
    _bridge_process = subprocess.Popen(
        [str(bridge_exe)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(bridge_exe.parent)
    )
    
    # Attendre qu'il soit prêt
    max_retries = 30
    for i in range(max_retries):
        try:
            resp = requests.get(f"{BRIDGE_URL}/health", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Bridge prêt (version {data.get('version', '?')})")
                return _bridge_process
        except:
            pass
        
        # Vérifier si le processus a crashé
        if _bridge_process.poll() is not None:
            stdout, stderr = _bridge_process.communicate()
            print(f"❌ Bridge a crashé (code {_bridge_process.returncode})")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            raise RuntimeError("Le Bridge a crashé au démarrage")
        
        time.sleep(0.5)
        print(f"   Attente... {i+1}/{max_retries}")
    
    raise TimeoutError("Le Bridge ne répond pas après 15 secondes")

def stop_bridge():
    """Arrêter proprement le Bridge"""
    global _bridge_process
    
    if _bridge_process is not None:
        print("\n🛑 Arrêt du Bridge...")
        try:
            _bridge_process.terminate()
            _bridge_process.wait(timeout=5)
        except:
            _bridge_process.kill()
        _bridge_process = None
        print("✅ Bridge arrêté")

def ensure_bridge_running():
    """S'assurer que le Bridge tourne"""
    global _bridge_process
    
    if _bridge_process is None or _bridge_process.poll() is not None:
        print("ℹ️  Redémarrage du Bridge...")
        start_bridge()
    
    # Vérifier qu'il répond
    try:
        requests.get(f"{BRIDGE_URL}/health", timeout=3)
    except:
        print("⚠️  Bridge ne répond pas, redémarrage...")
        stop_bridge()
        start_bridge()

# Enregistrer l'arrêt propre
atexit.register(stop_bridge)

# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _get_clients() -> List[Dict[str, Any]]:
    """Récupérer la liste des clients via le Bridge"""
    ensure_bridge_running()
    
    try:
        resp = requests.get(f"{BRIDGE_URL}/clients", timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data.get("clients", [])
    except Exception as e:
        print(f"[ERROR] _get_clients: {e}")
        return []

def _execute(script: str, pids: List[int]) -> bool:
    """Exécuter un script sur des PIDs via le Bridge"""
    ensure_bridge_running()
    
    try:
        payload = {
            "script": script,
            "pids": pids
        }
        resp = requests.post(
            f"{BRIDGE_URL}/execute",
            json=payload,
            timeout=TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("success", False)
    except Exception as e:
        print(f"[ERROR] _execute: {e}")
        return False

def _attach() -> bool:
    """Forcer l'attachement via le Bridge"""
    ensure_bridge_running()
    
    try:
        resp = requests.post(f"{BRIDGE_URL}/attach", timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data.get("success", False)
    except Exception as e:
        print(f"[ERROR] _attach: {e}")
        return False

def _set_setting(setting: str, value: bool) -> bool:
    """Modifier un paramètre via le Bridge"""
    ensure_bridge_running()
    
    try:
        payload = {
            "setting": setting,
            "value": value
        }
        resp = requests.post(
            f"{BRIDGE_URL}/setting",
            json=payload,
            timeout=TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("success", False)
    except Exception as e:
        print(f"[ERROR] _set_setting: {e}")
        return False

def _get_clipboard():
    """Lire le presse-papiers"""
    try:
        import pyperclip
        return pyperclip.paste()
    except:
        return None

def _unique_file() -> str:
    uid = uuid.uuid4().hex[:14]
    return f"mcp_out/{uid}.txt"

def _unique_marker() -> str:
    return f"[MCP_{uuid.uuid4().hex[:8]}]"

def _ensure_outdir_lua() -> str:
    return """
if not isfolder("mcp_out") then
    pcall(makefolder, "mcp_out")
end
"""

def _write_result_lua(outfile: str) -> str:
    return f"""
local __OUTFILE__ = "{outfile}"
local function writeResult(text)
    if writefile then
        pcall(writefile, __OUTFILE__, tostring(text))
    end
end
"""

def _resolver_lua() -> str:
    return r"""
local function resolvePath(pathStr)
    if pathStr == nil or pathStr == "" then
        return nil, "empty path"
    end
    if pathStr == "game"      then return game, nil end
    if pathStr == "_G"        then return _G, nil end
    if pathStr == "workspace" then return workspace, nil end
    if pathStr == "script"    then return script, nil end

    local parts = {}
    for part in pathStr:gmatch("[^%.]+") do
        table.insert(parts, part)
    end
    if #parts == 0 then return nil, "no parts" end

    local current
    local root = parts[1]
    if root == "game"           then current = game
    elseif root == "_G"         then current = _G
    elseif root == "workspace"  then current = workspace
    else
        if getgenv then current = getgenv()[root] end
        if current == nil then current = _G[root] end
        if current == nil then return nil, "unknown root: " .. root end
    end

    for i = 2, #parts do
        local seg = parts[i]
        local ok, child = pcall(function()
            if type(current) ~= "table" then
                local fc
                local fcOk = pcall(function()
                    fc = current:FindFirstChild(seg)
                end)
                if fcOk and fc ~= nil then return fc end
            end
            return current[seg]
        end)
        if not ok then
            return nil, "error at '" .. seg .. "': " .. tostring(child)
        end
        if child == nil then
            return nil, "nil at segment '" .. seg .. "'"
        end
        current = child
    end
    return current, nil
end
"""

def _execute_and_read(script: str, wait: float = 2.0) -> str:
    """
    Exécute un script et lit le résultat via le Bridge
    """
    clients = _get_clients()
    if not clients:
        return "❌ Aucun client connecté. Utilisez 'attach_to_roblox()' d'abord."
    
    # Prendre le premier client en state=3 (prêt)
    ready_clients = [c for c in clients if c.get("state") == 3]
    if not ready_clients:
        return f"❌ Aucun client prêt (state=3). Clients trouvés: {len(clients)}. Attendez l'attachement complet."
    
    target_pid = ready_clients[0]["pid"]
    
    outfile = _unique_file()
    marker = _unique_marker()
    
    # Construire le script complet
    prefix = _ensure_outdir_lua() + _write_result_lua(outfile)
    full_lua = prefix + "\n" + script
    
    # Exécuter
    if not _execute(full_lua, [target_pid]):
        return f"❌ Échec de l'exécution sur PID {target_pid}"
    
    time.sleep(wait)
    
    # Lire le résultat
    read_lua = (
        f'local __M__ = "{marker}"\n'
        f'local __F__ = "{outfile}"\n'
        'if not readfile then\n'
        '    setclipboard(__M__ .. " [ERROR] readfile not available")\n'
        '    return\n'
        'end\n'
        'local ok2, content = pcall(readfile, __F__)\n'
        'if ok2 and content and content ~= "" then\n'
        '    setclipboard(__M__ .. " " .. content)\n'
        '    pcall(delfile, __F__)\n'
        'else\n'
        '    setclipboard(__M__ .. " [READ_ERROR] " .. tostring(content))\n'
        'end\n'
    )
    
    _execute(read_lua, [target_pid])
    
    # Retry loop
    for attempt in range(4):
        time.sleep(0.9 if attempt == 0 else 0.6)
        result = _get_clipboard()
        if result and result.startswith(marker):
            return result[len(marker):].strip()
    
    return (
        f"⚠️ Validation du presse-papiers échouée après 4 essais.\n"
        f"Marker attendu: {marker}\n"
        f"Obtenu: {(result or '(vide)')[:120]}"
    )

# ═══════════════════════════════════════════════════════════════════════════════
# OUTILS MCP
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def bridge_status() -> str:
    """
    Vérifier le statut du Bridge et de l'environnement
    """
    try:
        ensure_bridge_running()
        
        resp = requests.get(f"{BRIDGE_URL}/health", timeout=TIMEOUT)
        data = resp.json()
        
        status_lines = [
            "🌉 STATUT DU BRIDGE",
            "=" * 40,
            f"✅ Bridge: {data.get('status', '?')}",
            f"📦 Version: {data.get('version', '?')}",
            f"🔧 Initialisé: {data.get('initialized', False)}",
            "",
            "🌐 Endpoints disponibles:",
            "   POST /attach     - Attacher à Roblox",
            "   POST /execute    - Exécuter script Lua",
            "   GET  /clients    - Liste des clients",
            "   POST /setting    - Paramètres (AutoAttach)",
            "   GET  /version    - Version de Xeno.dll",
        ]
        
        return "\n".join(status_lines)
    except Exception as e:
        return f"❌ Erreur: {e}\n\nLe Bridge tourne-t-il ? Essayez de redémarrer le MCP."

@mcp.tool()
def attach_to_roblox() -> str:
    """
    Force l'attachement à Roblox via le Bridge
    """
    ensure_bridge_running()
    
    # Vérifier les clients actuels
    clients_before = _get_clients()
    ready_before = [c for c in clients_before if c.get("state") == 3]
    
    if ready_before:
        return f"✅ Déjà attaché !\n\nClient prêt: PID {ready_before[0]['pid']} ({ready_before[0]['name']})"
    
    # Déclencher l'attachement
    print("🔌 Déclenchement de l'attachement...")
    if _attach():
        time.sleep(2)
        
        # Vérifier le résultat
        clients_after = _get_clients()
        ready_after = [c for c in clients_after if c.get("state") == 3]
        
        if ready_after:
            c = ready_after[0]
            return (
                f"✅ Attachement réussi !\n\n"
                f"🎮 Client: {c['name']}\n"
                f"🔢 PID: {c['pid']}\n"
                f"📦 Version: {c['version']}\n"
                f"🟢 État: {c['state']} (Prêt)"
            )
        else:
            return (
                f"⏳ Attachement en cours...\n\n"
                f"Clients trouvés: {len(clients_after)}\n"
                f"Attendez 5-10 secondes et utilisez 'list_clients()'"
            )
    else:
        return "❌ Échec de l'attachement"

@mcp.tool()
def list_clients() -> str:
    """
    Liste tous les clients Roblox connectés via le Bridge
    """
    ensure_bridge_running()
    
    clients = _get_clients()
    
    if not clients:
        return (
            "⚠️ Aucun client connecté\n\n"
            "🔧 Conseils:\n"
            "   1. Démarrez Roblox\n"
            "   2. Utilisez 'attach_to_roblox()'\n"
            "   3. Attendez 10 secondes\n"
            "   4. Réessayez"
        )
    
    lines = [f"🎮 Clients connectés: {len(clients)}", ""]
    
    for c in clients:
        state_str = {
            0: "🔴 Déconnecté",
            1: "🟡 En attente", 
            2: "🔵 Attaché",
            3: "🟢 Prêt"
        }.get(c.get("state", -1), "⚪ Inconnu")
        
        lines.extend([
            f"PID: {c.get('pid')}",
            f"  👤 Nom: {c.get('name', 'N/A')}",
            f"  📦 Version: {c.get('version', 'N/A')}",
            f"  📊 État: {c.get('state')} - {state_str}",
            ""
        ])
    
    ready_count = len([c for c in clients if c.get("state") == 3])
    if ready_count > 0:
        lines.append(f"✅ Prêts à exécuter: {ready_count} client(s)")
    
    return "\n".join(lines)

@mcp.tool()
def execute_script(lua_code: str, pids: str = "auto") -> str:
    """
    Exécute un script Lua sur les clients spécifiés
    
    Args:
        lua_code: Code Lua à exécuter
        pids: PIDs des clients (ex: "1234,5678" ou "auto" pour auto-détection)
    """
    ensure_bridge_running()
    
    # Déterminer les PIDs
    target_pids: List[int] = []
    
    if pids == "auto":
        # Laisser le Bridge auto-détecter
        target_pids = []
    else:
        try:
            target_pids = [int(p.strip()) for p in pids.split(",")]
        except ValueError:
            return "❌ Format de PIDs invalide. Utilisez: '1234,5678' ou 'auto'"
    
    # Exécuter
    success = _execute(lua_code, target_pids)
    
    if success:
        if target_pids:
            return f"✅ Script exécuté sur PIDs: {target_pids}"
        else:
            return "✅ Script exécuté (auto-détection du Bridge)"
    else:
        return f"❌ Échec de l'exécution"

@mcp.tool()
def execute_and_capture(lua_code: str, wait_time: float = 2.0) -> str:
    """
    Exécute un script Lua et capture le résultat
    
    Args:
        lua_code: Code Lua à exécuter
        wait_time: Temps d'attente pour la capture (défaut 2.0s)
    """
    ensure_bridge_running()
    
    # Wrapper pour capturer print + return
    wrapped = f"""
local __cap = {{}}
local __op  = print
print = function(...)
    local a = {{...}}
    for i, v in ipairs(a) do a[i] = tostring(v) end
    table.insert(__cap, table.concat(a, " "))
    __op(...)
end
local __ok, __res = pcall(function()
{lua_code}
end)
print = __op
local __out = table.concat(__cap, "\\n")
local __final
if __ok then
    __final = "=== OUTPUT ===\\n" .. __out
           .. "\\n\\n=== RESULT ===\\n" .. tostring(__res)
else
    __final = "=== ERROR ===\\n" .. tostring(__res)
           .. "\\n\\n=== CAPTURED ===\\n" .. __out
end
writeResult(__final)
"""
    
    return _execute_and_read(wrapped, wait=wait_time)

@mcp.tool()
def set_auto_attach(enabled: bool) -> str:
    """
    Active/désactive l'AutoAttach (scan automatique des processus Roblox)
    
    Args:
        enabled: true pour activer, false pour désactiver
    """
    ensure_bridge_running()
    
    success = _set_setting("AutoAttach", enabled)
    
    if success:
        status = "activé" if enabled else "désactivé"
        return (
            f"✅ AutoAttach {status}\n\n"
            f"Xeno scannera automatiquement les processus Roblox toutes les 25 secondes."
        )
    else:
        return "❌ Échec de la modification du paramètre"

@mcp.tool()
def print_test() -> str:
    """
    Test simple: envoie 'print(\"Bridge MCP Test OK!\")' au client
    """
    ensure_bridge_running()
    
    clients = _get_clients()
    ready = [c for c in clients if c.get("state") == 3]
    
    if not ready:
        return "❌ Aucun client prêt. Utilisez 'attach_to_roblox()' d'abord."
    
    script = 'print("✅ Bridge MCP Test OK! PID: " .. game.PlaceId)'
    success = _execute(script, [ready[0]["pid"]])
    
    if success:
        return f"✅ Test envoyé au PID {ready[0]['pid']} - vérifiez la console Roblox (F9)"
    else:
        return "❌ Échec du test"

# ═══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Xeno MCP avec Bridge intégré")
    print("=" * 60)
    print("")
    
    try:
        # Démarrer le Bridge automatiquement
        start_bridge()
        print("")
        print("✅ Système prêt ! Démarrage du serveur MCP...")
        print("")
        
        # Lancer le serveur MCP
        mcp.run()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Interruption par l'utilisateur")
        stop_bridge()
    except Exception as e:
        print(f"\n\n❌ Erreur fatale: {e}")
        stop_bridge()
        raise

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION MCP
# ═══════════════════════════════════════════════════════════════════════════════
# Fichier: %APPDATA%\Windsurf\mcp_config.json
# {
#   "mcpServers": {
#     "xeno-bridge": {
#       "command": "python",
#       "args": ["C:/Users/Zenith__/Documents/windsurf/xeno-re/xeno_mcp_bridge_full.py"]
#     }
#   }
# }
