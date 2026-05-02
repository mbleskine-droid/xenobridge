"""
xeno_mcp_v2.py — Xeno Executor MCP Server v7
Améliorations basées sur l'analyse HAR et Ghidra MCP

Install:  pip install fastmcp requests pyperclip
Run:      python xeno_mcp_v2.py
"""

import json
import requests
import time
import uuid
from fastmcp import FastMCP
from typing import Optional, List, Dict, Any

BASE_URL = "http://localhost:3110"
ENDPOINT_EXECUTE = f"{BASE_URL}/o"
TIMEOUT = 5

mcp = FastMCP("Xeno Executor v2")

# ═══════════════════════════════════════════════════════════════════════════════
# CORRECTIONS FONDAMENTALES
# ═══════════════════════════════════════════════════════════════════════════════

def _get_clients_via_options() -> Optional[List[List[Any]]]:
    """
    CORRECTION: Récupère la liste des clients via OPTIONS /o
    
    D'après l'analyse HAR et les tests, le serveur Xeno renvoie la liste
    des clients dans la réponse OPTIONS à /o, pas via GET /g.
    
    Format retourné: [[pid, username, version, state, id], ...]
    Exemple: [[27680,"[i] Loading...","version-...",1,0], ...]
    """
    try:
        resp = requests.options(ENDPOINT_EXECUTE, timeout=TIMEOUT)
        resp.raise_for_status()
        # La réponse OPTIONS contient la liste des clients en JSON
        if resp.text and resp.text.strip():
            try:
                return resp.json()
            except json.JSONDecodeError:
                pass
        return []
    except Exception:
        return None


def _get_clients_via_get() -> Optional[List[List[Any]]]:
    """Fallback: essaie GET /g si disponible (selon Ghidra c'est probable)."""
    try:
        resp = requests.get(f"{BASE_URL}/g", timeout=TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        return []
    except Exception:
        return None


def _get_clients() -> List[List[Any]]:
    """
    Récupère la liste des clients connectés.
    Essaie d'abord OPTIONS /o (confirmé par HAR), puis GET /g.
    """
    # Premier essai: OPTIONS /o (confirmé par l'analyse)
    clients = _get_clients_via_options()
    if clients is not None:
        return clients
    
    # Fallback: GET /g (si implémenté dans une future version)
    clients = _get_clients_via_get()
    if clients is not None:
        return clients
    
    return []


def _get_server_info() -> Dict[str, Any]:
    """Récupère les informations du serveur Xeno."""
    info = {
        "base_url": BASE_URL,
        "execute_endpoint": ENDPOINT_EXECUTE,
        "status": "unknown",
        "version": None,
        "cors_headers": {},
        "clients": []
    }
    
    try:
        # Test GET /
        r = requests.get(BASE_URL, timeout=TIMEOUT)
        info["status"] = "up" if r.status_code == 200 else f"http_{r.status_code}"
        info["root_response"] = r.text[:100] if r.text else ""
        
        # Test OPTIONS /o pour CORS et clients
        r_opt = requests.options(ENDPOINT_EXECUTE, timeout=TIMEOUT)
        info["cors_headers"] = dict(r_opt.headers)
        if r_opt.text:
            try:
                info["clients"] = r_opt.json()
            except:
                pass
        
        # Test GET /v pour version
        r_ver = requests.get(f"{BASE_URL}/v", timeout=TIMEOUT)
        if r_ver.status_code == 200:
            info["version"] = r_ver.text
            
    except requests.ConnectionError:
        info["status"] = "down"
    except Exception as e:
        info["error"] = str(e)
    
    return info


def _execute(pid: int, script: str) -> bool:
    """
    Exécute un script Lua sur un client Roblox.
    
    Args:
        pid: Process ID du client Roblox
        script: Code Lua à exécuter
    
    Returns:
        True si la requête a réussi (HTTP 200)
    """
    headers = {
        "Content-Type": "text/plain",
        "Clients": json.dumps([str(pid)]),
        "Origin": "https://xeno.onl"  # Requis par CORS
    }
    try:
        r = requests.post(ENDPOINT_EXECUTE, headers=headers, data=script.encode(), timeout=TIMEOUT)
        return r.status_code == 200
    except Exception:
        return False


def _broadcast_execute(script: str, clients: Optional[List[int]] = None) -> Dict[int, bool]:
    """Exécute un script sur plusieurs clients."""
    if clients is None:
        client_list = _get_clients()
        clients = [c[0] for c in client_list if isinstance(c[0], int)]
    
    results = {}
    for pid in clients:
        results[pid] = _execute(pid, script)
        time.sleep(0.1)  # Petit délai entre chaque exécution
    return results


def _get_clipboard() -> Optional[str]:
    """Récupère le contenu du presse-papiers."""
    try:
        import pyperclip
        return pyperclip.paste()
    except Exception:
        return None


def _unique_file() -> str:
    """Génère un nom de fichier unique."""
    uid = uuid.uuid4().hex[:14]
    return f"mcp_out/{uid}.txt"


def _unique_marker() -> str:
    """Génère un marqueur unique pour validation."""
    return f"[MCP_{uuid.uuid4().hex[:8]}]"


# ═══════════════════════════════════════════════════════════════════════════════
# LUA HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _ensure_outdir_lua() -> str:
    """Lua code pour créer le dossier de sortie."""
    return """
if not isfolder("mcp_out") then
    pcall(makefolder, "mcp_out")
end
"""


def _write_result_lua(outfile: str) -> str:
    """Lua code pour écrire un résultat dans un fichier."""
    return f"""
local __OUTFILE__ = "{outfile}"
local function writeResult(text)
    if writefile then
        pcall(writefile, __OUTFILE__, tostring(text))
    end
end
"""


def _resolver_lua() -> str:
    """Lua resolver de chemins Roblox."""
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


def _execute_and_read(pid: int, lua_code: str, wait: float = 2.0) -> str:
    """
    Exécute du code Lua et lit le résultat via clipboard.
    """
    outfile = _unique_file()
    marker = _unique_marker()

    prefix = _ensure_outdir_lua() + _write_result_lua(outfile)
    full_lua = prefix + "\n" + lua_code

    if not _execute(pid, full_lua):
        return f"❌ Execution failed on PID {pid}."

    time.sleep(wait)

    # Script de lecture
    read_lua = (
        f'local __MARKER__ = "{marker}"\n'
        f'local __OUTFILE__ = "{outfile}"\n'
        'if not readfile then\n'
        '    setclipboard(__MARKER__ .. " [ERROR] readfile not available")\n'
        '    return\n'
        'end\n'
        'local ok2, content = pcall(readfile, __OUTFILE__)\n'
        'if ok2 and content and content ~= "" then\n'
        '    setclipboard(__MARKER__ .. " " .. content)\n'
        '    pcall(delfile, __OUTFILE__)\n'
        'else\n'
        '    setclipboard(__MARKER__ .. " [READ_ERROR] " .. tostring(content))\n'
        'end\n'
    )

    _execute(pid, read_lua)

    for attempt in range(4):
        time.sleep(0.9 if attempt == 0 else 0.6)
        result = _get_clipboard()
        if result and result.startswith(marker):
            return result[len(marker):].strip()

    return (
        f"⚠️ Clipboard validation failed after 4 retries.\n"
        f"Expected marker: {marker}\n"
        f"Got: {(result or '(empty)')[:120]}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# OUTILS MCP - DIAGNOSTIC ET INFOS
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def diagnose_server() -> str:
    """
    Diagnostique complet du serveur Xeno.
    Affiche l'état, la version, les clients connectés, et les headers CORS.
    """
    info = _get_server_info()
    
    lines = ["=== XENO SERVER DIAGNOSTIC ===", ""]
    
    # Statut
    status = info.get("status", "unknown")
    icon = "✅" if status == "up" else "❌"
    lines.append(f"{icon} Status: {status}")
    
    # Version
    version = info.get("version")
    if version:
        lines.append(f"📦 Version: {version}")
    
    # Réponse root
    root = info.get("root_response", "")
    if root:
        lines.append(f"🌐 Root: {root}")
    
    # Clients
    clients = info.get("clients", [])
    lines.append(f"");
    lines.append(f"👥 Clients connectés: {len(clients)}")
    for i, c in enumerate(clients):
        if isinstance(c, list) and len(c) >= 2:
            pid = c[0]
            username = c[1] if len(c) > 1 else "unknown"
            version = c[2] if len(c) > 2 else "unknown"
            lines.append(f"  {i+1}. PID {pid} | {username} | {version}")
    
    # CORS Headers
    cors = info.get("cors_headers", {})
    if cors:
        lines.append(f"")
        lines.append("🔒 CORS Headers:")
        for k, v in cors.items():
            if "Access-Control" in k:
                lines.append(f"  {k}: {v}")
    
    # Erreur
    if "error" in info:
        lines.append(f"⚠️ Error: {info['error']}")
    
    return "\n".join(lines)


@mcp.tool()
def list_clients_detailed() -> str:
    """
    Liste détaillée des clients Roblox connectés.
    Format: PID, Username, Version, State, ID
    """
    clients = _get_clients()
    
    if not clients:
        return "❌ Aucun client connecté. Le serveur Xeno est-il démarré ?"
    
    lines = ["=== CLIENTS ROBLOX ===", ""]
    
    for i, c in enumerate(clients):
        if isinstance(c, list):
            pid = c[0] if len(c) > 0 else "?"
            username = c[1] if len(c) > 1 else "?"
            version = c[2] if len(c) > 2 else "?"
            state = c[3] if len(c) > 3 else "?"
            uid = c[4] if len(c) > 4 else "?"
            
            lines.append(f"[{i+1}] PID: {pid}")
            lines.append(f"    User: {username}")
            lines.append(f"    Version: {version}")
            lines.append(f"    State: {state}")
            lines.append(f"    ID: {uid}")
            lines.append("")
    
    return "\n".join(lines)


@mcp.tool()
def list_clients() -> str:
    """Liste rapide des clients (compatible v1)."""
    clients = _get_clients()
    if not clients:
        return "No clients connected."
    lines = []
    for c in clients:
        if isinstance(c, list) and len(c) >= 2:
            lines.append(f"PID {c[0]} | {c[1]} | {c[2] if len(c) > 2 else '?'}")
    return "Connected clients:\n" + "\n".join(lines)


@mcp.tool()
def check_api_status() -> str:
    """Vérifie si l'API Xeno est disponible."""
    info = _get_server_info()
    status = info.get("status", "unknown")
    
    if status == "up":
        clients = info.get("clients", [])
        return f"✅ Xeno API UP | {len(clients)} client(s)"
    elif status == "down":
        return "❌ Xeno API DOWN - Serveur non démarré"
    else:
        return f"⚠️ Xeno API status: {status}"


# ═══════════════════════════════════════════════════════════════════════════════
# OUTILS MCP - EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def execute_script(lua_code: str, pid: int | None = None) -> str:
    """
    Exécute du code Lua sur un client.
    
    Args:
        lua_code: Code Lua à exécuter
        pid: PID cible (auto-sélectionne le premier si non spécifié)
    """
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    target = pid or clients[0][0]
    success = _execute(target, lua_code)
    
    if success:
        return f"✅ Exécuté sur PID {target}"
    else:
        return f"❌ Échec sur PID {target}"


@mcp.tool()
def execute_and_capture(lua_code: str, pid: int | None = None, wait_time: float = 2.0) -> str:
    """
    Exécute du Lua et capture le résultat (print + return).
    
    Args:
        lua_code: Code Lua
        pid: PID cible
        wait_time: Temps d'attente en secondes
    """
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    target = pid or clients[0][0]
    
    lua = f"""
local __cap = {{}}
local __op = print
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
    return _execute_and_read(target, lua, wait=wait_time)


@mcp.tool()
def broadcast_script(lua_code: str, target_pids: str = "") -> str:
    """
    Exécute du Lua sur tous les clients ou une liste spécifique.
    
    Args:
        lua_code: Code Lua
        target_pids: Liste de PIDs séparés par virgule (vide = tous)
    """
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    # Parse les PIDs cibles
    if target_pids.strip():
        try:
            pids = [int(p.strip()) for p in target_pids.split(",")]
        except ValueError:
            return "❌ Format de PIDs invalide. Exemple: 1234,5678"
    else:
        pids = [c[0] for c in clients if isinstance(c, list) and isinstance(c[0], int)]
    
    results = []
    for pid in pids:
        success = _execute(pid, lua_code)
        icon = "✅" if success else "❌"
        # Trouve le nom d'utilisateur
        username = "?"
        for c in clients:
            if isinstance(c, list) and c[0] == pid:
                username = c[1] if len(c) > 1 else "?"
                break
        results.append(f"{icon} PID {pid} ({username})")
    
    return "Broadcast:\n" + "\n".join(results)


# ═══════════════════════════════════════════════════════════════════════════════
# OUTILS MCP - EXPLORATION DU JEU
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def explore_game_tree(path: str = "game", depth: int = 3, pid: int | None = None) -> str:
    """
    Explore l'arbre des instances Roblox.
    
    Args:
        path: Chemin de départ (ex: "game", "game.Workspace")
        depth: Profondeur max (1-5)
        pid: PID cible
    """
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    target = pid or clients[0][0]
    depth = min(max(depth, 1), 5)
    
    lua = _resolver_lua() + f"""
local root, err = resolvePath("{path}")
if root == nil then
    writeResult("ERROR: " .. tostring(err))
    return
end

local function explore(obj, cur, max, indent)
    if cur > max then return "" end
    local out = ""
    local ok2, ch = pcall(function() return obj:GetChildren() end)
    if not ok2 then return out end
    
    for _, child in ipairs(ch) do
        local name_ok, name = pcall(function() return child.Name end)
        local class_ok, class = pcall(function() return child.ClassName end)
        out = out .. indent .. "|- "
            .. (name_ok and tostring(name) or "?")
            .. " (" .. (class_ok and tostring(class) or "?") .. ")\\n"
        if cur < max then
            out = out .. explore(child, cur + 1, max, indent .. "   ")
        end
    end
    return out
end

local ok2, nm = pcall(function() return root.Name end)
local ok3, cls = pcall(function() return root.ClassName end)
local out = "=== GAME TREE: {path} (depth={depth}) ===\\n"
out = out .. (ok2 and tostring(nm) or "{path}") .. " ("
          .. (ok3 and tostring(cls) or "?") .. ")\\n"
out = out .. explore(root, 1, {depth}, "")
writeResult(out)
"""
    return _execute_and_read(target, lua, wait=2.5)


@mcp.tool()
def find_instances(class_name: str, parent_path: str = "game", pid: int | None = None) -> str:
    """
    Trouve toutes les instances d'une ClassName.
    
    Args:
        class_name: Nom de la classe (ex: "RemoteEvent", "Part")
        parent_path: Chemin parent de recherche
        pid: PID cible
    """
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    target = pid or clients[0][0]
    
    lua = _resolver_lua() + f"""
local parent, err = resolvePath("{parent_path}")
if parent == nil then
    writeResult("ERROR: " .. tostring(err))
    return
end

local function getPath(obj)
    local p = tostring(obj.Name)
    local c = obj.Parent
    while c and c ~= game do
        p = tostring(c.Name) .. "." .. p
        c = c.Parent
    end
    return "game." .. p
end

local results = {{}}
local ok2, descs = pcall(function() return parent:GetDescendants() end)
if ok2 then
    for _, obj in ipairs(descs) do
        if obj.ClassName == "{class_name}" then
            table.insert(results, getPath(obj))
        end
    end
end

local out = "=== FIND '{class_name}' in '{parent_path}' ===\\n"
out = out .. "Trouvés: " .. #results .. "\\n\\n"
for i, p in ipairs(results) do
    out = out .. i .. ". " .. p .. "\\n"
end
writeResult(out)
"""
    return _execute_and_read(target, lua, wait=2.0)


@mcp.tool()
def get_instance_properties(instance_path: str, pid: int | None = None) -> str:
    """
    Récupère les propriétés d'une instance Roblox.
    
    Args:
        instance_path: Chemin complet (ex: "game.Workspace.Baseplate")
        pid: PID cible
    """
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    target = pid or clients[0][0]
    
    lua = _resolver_lua() + f"""
local inst, err = resolvePath("{instance_path}")
if inst == nil then
    writeResult("ERROR: " .. tostring(err))
    return
end

local ok2, cn = pcall(function() return inst.ClassName end)
local out = "=== PROPERTIES: {instance_path} ===\\n"
out = out .. "Class: " .. (ok2 and tostring(cn) or "?") .. "\\n\\n"

local props = {{
    "Name","Parent","Archivable",
    "Position","Size","CFrame","Orientation",
    "Transparency","Color","Material","CanCollide","Anchored","Velocity",
    "Health","MaxHealth","WalkSpeed","JumpPower",
    "Text","Value","Enabled"
}}

for _, pn in ipairs(props) do
    local pok, pv = pcall(function() return inst[pn] end)
    if pok and pv ~= nil then
        out = out .. pn .. ": " .. tostring(pv) .. "\\n"
    end
end

local aok, attrs = pcall(function() return inst:GetAttributes() end)
if aok and attrs and next(attrs) then
    out = out .. "\\n=== ATTRIBUTES ===\\n"
    for k, v in pairs(attrs) do
        out = out .. tostring(k) .. ": " .. tostring(v) .. "\\n"
    end
end

writeResult(out)
"""
    return _execute_and_read(target, lua, wait=1.8)


@mcp.tool()
def list_all_remotes(pid: int | None = None) -> str:
    """Liste tous les RemoteEvents et RemoteFunctions."""
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    target = pid or clients[0][0]
    
    lua = """
local function getPath(obj)
    local p = tostring(obj.Name)
    local c = obj.Parent
    while c and c ~= game do
        p = tostring(c.Name) .. "." .. p
        c = c.Parent
    end
    return "game." .. p
end

local evts, funcs = {{}}, {{}}
for _, obj in ipairs(game:GetDescendants()) do
    if obj:IsA("RemoteEvent") then
        table.insert(evts, getPath(obj))
    elseif obj:IsA("RemoteFunction") then
        table.insert(funcs, getPath(obj))
    end
end

local out = "=== REMOTE CATALOG ===\\n\\n"
out = out .. "RemoteEvents (" .. #evts .. "):\\n"
for i, p in ipairs(evts) do
    out = out .. "  " .. i .. ". " .. p .. "\\n"
end
out = out .. "\\nRemoteFunctions (" .. #funcs .. "):\\n"
for i, p in ipairs(funcs) do
    out = out .. "  " .. i .. ". " .. p .. "\\n"
end
writeResult(out)
"""
    return _execute_and_read(target, lua, wait=2.5)


# ═══════════════════════════════════════════════════════════════════════════════
# OUTILS MCP - SCRIPTS
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def decompile_script(script_path: str, pid: int | None = None) -> str:
    """
    Décompile un LocalScript ou ModuleScript.
    
    Args:
        script_path: Chemin du script (ex: "game.Players.LocalPlayer.PlayerScripts.MyScript")
        pid: PID cible
    """
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    target = pid or clients[0][0]
    
    lua = _resolver_lua() + f"""
local scr, err = resolvePath("{script_path}")
if scr == nil then
    writeResult("ERROR: " .. tostring(err))
    return
end

local isOk, isScript = pcall(function() return scr:IsA("LuaSourceContainer") end)
if not (isOk and isScript) then
    writeResult("ERROR: not a script, got " .. tostring(scr.ClassName))
    return
end

local source = nil
if decompile then
    local dok, dr = pcall(decompile, scr)
    if dok then source = dr end
elseif getsrc then
    local sok, sr = pcall(getsrc, scr)
    if sok then source = sr end
end

local out = "=== DECOMPILE: " .. scr.Name
          .. " (" .. scr.ClassName .. ") ===\\n\\n"
out = out .. (source or "ERROR: no decompiler (tried decompile, getsrc)")
writeResult(out)
"""
    return _execute_and_read(target, lua, wait=3.5)


@mcp.tool()
def find_all_scripts(script_type: str = "all", parent_path: str = "game", pid: int | None = None) -> str:
    """
    Trouve tous les scripts Lua.
    
    Args:
        script_type: "LocalScript", "Script", "ModuleScript", ou "all"
        parent_path: Racine de recherche
        pid: PID cible
    """
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    target = pid or clients[0][0]
    
    lua = _resolver_lua() + f"""
local parent, err = resolvePath("{parent_path}")
if parent == nil then
    writeResult("ERROR: " .. tostring(err))
    return
end

local function getPath(obj)
    local p = tostring(obj.Name)
    local c = obj.Parent
    while c and c ~= game do
        p = tostring(c.Name) .. "." .. p
        c = c.Parent
    end
    return "game." .. p
end

local R = {{LocalScript={{}}, Script={{}}, ModuleScript={{}}}}
for _, obj in ipairs(parent:GetDescendants()) do
    if obj:IsA("LuaSourceContainer") then
        local cn = obj.ClassName
        if "{script_type}" == "all" or cn == "{script_type}" then
            if R[cn] then table.insert(R[cn], getPath(obj)) end
        end
    end
end

local out = "=== SCRIPTS ({script_type}) in {parent_path} ===\\n"
for cn, paths in pairs(R) do
    if #paths > 0 then
        out = out .. "\\n" .. cn .. " (" .. #paths .. "):\\n"
        for i, p in ipairs(paths) do
            out = out .. "  " .. i .. ". " .. p .. "\\n"
        end
    end
end
writeResult(out)
"""
    return _execute_and_read(target, lua, wait=2.5)


# ═══════════════════════════════════════════════════════════════════════════════
# OUTILS MCP - REMOTE SPY
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def spy_remotes(duration: int = 30, filter_type: str = "all", pid: int | None = None) -> str:
    """
    Spy sur les appels RemoteEvent/RemoteFunction.
    
    Args:
        duration: Durée en secondes
        filter_type: "RemoteEvent", "RemoteFunction", ou "all"
        pid: PID cible
    """
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    target = pid or clients[0][0]
    outfile = _unique_file()
    
    setup = _ensure_outdir_lua()
    lua = setup + f"""
local calls = {{}}
local t0 = tick()

local function getPath(obj)
    local p = tostring(obj.Name)
    local c = obj.Parent
    while c and c ~= game do
        p = tostring(c.Name) .. "." .. p
        c = c.Parent
    end
    return "game." .. p
end

local function argStr(...)
    local args = {{...}}
    local ss = {{}}
    for i, a in ipairs(args) do
        if i > 5 then table.insert(ss, "...") break end
        local t = type(a)
        if t == "string" then
            table.insert(ss, '"' .. a:sub(1, 40) .. '"')
        elseif t == "number" or t == "boolean" then
            table.insert(ss, tostring(a))
        elseif t == "table" then
            table.insert(ss, "table[" .. #a .. "]")
        else
            table.insert(ss, t)
        end
    end
    return table.concat(ss, ", ")
end

if hookmetamethod then
    local old
    old = hookmetamethod(game, "__namecall", function(self, ...)
        local m = getnamecallmethod()
        local ft = "{filter_type}"
        if (ft == "all" or ft == "RemoteEvent")
            and self:IsA("RemoteEvent") and m == "FireServer" then
            table.insert(calls, {{
                path = getPath(self),
                method = m,
                args = argStr(...),
                t = tick() - t0
            }})
        end
        if (ft == "all" or ft == "RemoteFunction")
            and self:IsA("RemoteFunction") and m == "InvokeServer" then
            table.insert(calls, {{
                path = getPath(self),
                method = m,
                args = argStr(...),
                t = tick() - t0
            }})
        end
        return old(self, ...)
    end)
end

task.wait({duration})

local out = "=== REMOTE SPY ({duration}s) ===\\n"
out = out .. "Captured: " .. #calls .. "\\n\\n"
for _, c in ipairs(calls) do
    out = out .. string.format("[%.2fs] %s:%s(%s)\\n",
        c.t, c.path, c.method, c.args)
end
if writefile then pcall(writefile, "{outfile}", out) end
"""
    _execute(target, lua)
    return (
        f"✅ Remote spy lancé sur PID {target} pendant {duration}s.\n"
        f"📄 Fichier: {outfile}\n"
        f"⏳ Utilise read_file('{outfile}') après {duration}s."
    )


@mcp.tool()
def read_file(filepath: str, pid: int | None = None) -> str:
    """
    Lit un fichier depuis l'espace de travail de l'executor.
    
    Args:
        filepath: Chemin du fichier (ex: "mcp_out/abc123.txt")
        pid: PID cible
    """
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    target = pid or clients[0][0]
    marker = _unique_marker()
    
    lua = (
        f'local __M__ = "{marker}"\n'
        f'local __F__ = "{filepath}"\n'
        'if not readfile then\n'
        '    setclipboard(__M__ .. " [ERROR] readfile not available")\n'
        '    return\n'
        'end\n'
        'local ok2, content = pcall(readfile, __F__)\n'
        'if ok2 and content then\n'
        '    setclipboard(__M__ .. " " .. content)\n'
        'else\n'
        '    setclipboard(__M__ .. " [READ_ERROR] " .. tostring(content))\n'
        'end\n'
    )
    
    ok = _execute(target, lua)
    if not ok:
        return f"❌ Échec de l'exécution sur PID {target}."
    
    for attempt in range(4):
        time.sleep(1.0 if attempt == 0 else 0.6)
        result = _get_clipboard()
        if result and result.startswith(marker):
            return result[len(marker):].strip()
    
    return f"⚠️ Échec de lecture pour '{filepath}'."


# ═══════════════════════════════════════════════════════════════════════════════
# OUTILS MCP - DEBUGGING
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_stack_trace(pid: int | None = None) -> str:
    """Récupère la stack trace Lua actuelle."""
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    target = pid or clients[0][0]
    
    lua = """
local out = "=== STACK TRACE ===\\n\\n"
if debug and debug.traceback then
    local ok2, tb = pcall(debug.traceback, "", 2)
    out = out .. (ok2 and tostring(tb) or "traceback failed") .. "\\n\\n"
else
    out = out .. "debug.traceback not available\\n\\n"
end

out = out .. "=== CALL STACK ===\\n\\n"
if debug and debug.getinfo then
    for level = 1, 25 do
        local ok3, info = pcall(debug.getinfo, level)
        if not ok3 or not info then break end
        out = out .. string.format("  [%d] %s  @  %s:%s\\n",
            level,
            tostring(info.name or "?"),
            tostring(info.source or "?"),
            tostring(info.currentline or "?"))
    end
else
    out = out .. "debug.getinfo not available\\n"
end
writeResult(out)
"""
    return _execute_and_read(target, lua, wait=1.5)


@mcp.tool()
def inspect_environment(pid: int | None = None) -> str:
    """Vérifie les capacités de l'executor."""
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    target = pid or clients[0][0]
    
    lua = """
local caps = {
    {"setclipboard", type(setclipboard) == "function"},
    {"writefile", type(writefile) == "function"},
    {"readfile", type(readfile) == "function"},
    {"delfile", type(delfile) == "function"},
    {"makefolder", type(makefolder) == "function"},
    {"isfolder", type(isfolder) == "function"},
    {"hookfunction", type(hookfunction) == "function"},
    {"hookmetamethod", type(hookmetamethod) == "function"},
    {"newproxy", type(newproxy) == "function"},
    {"getrawmetatable", type(getrawmetatable) == "function"},
    {"getgenv", type(getgenv) == "function"},
    {"getfenv", type(getfenv) == "function"},
    {"loadstring", type(loadstring) == "function"},
    {"decompile", type(decompile) == "function"},
    {"getsrc", type(getsrc) == "function"},
    {"request", type(request) == "function"},
    {"debug.getinfo", debug ~= nil and type(debug.getinfo) == "function"},
    {"debug.getconstants", debug ~= nil and type(debug.getconstants) == "function"},
    {"debug.getupvalues", debug ~= nil and type(debug.getupvalues) == "function"},
    {"debug.setupvalue", debug ~= nil and type(debug.setupvalue) == "function"},
    {"debug.traceback", debug ~= nil and type(debug.traceback) == "function"},
}
local out = "=== EXECUTOR CAPABILITIES ===\\n\\n"
for _, c in ipairs(caps) do
    out = out .. (c[2] and "[YES]" or "[ NO]") .. "  " .. c[1] .. "\\n"
end
writeResult(out)
"""
    return _execute_and_read(target, lua, wait=1.5)


@mcp.tool()
def dump_globals(filter_pattern: str = "", pid: int | None = None) -> str:
    """
    Liste les variables globales.
    
    Args:
        filter_pattern: Filtre optionnel (pattern Lua)
        pid: PID cible
    """
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    target = pid or clients[0][0]
    
    filter_code = f'and k:match("{filter_pattern}")' if filter_pattern else ""
    
    lua = f"""
local sorted = {{}}
for k, v in pairs(getfenv(0)) do
    if type(k) == "string" {filter_code} then
        table.insert(sorted, {{k=k, t=type(v)}})
    end
end
table.sort(sorted, function(a, b) return a.k < b.k end)
local out = "=== GLOBALS (" .. #sorted .. ") ===\\n\\n"
for _, e in ipairs(sorted) do
    out = out .. e.k .. " : " .. e.t .. "\\n"
end
writeResult(out)
"""
    return _execute_and_read(target, lua, wait=1.8)


# ═══════════════════════════════════════════════════════════════════════════════
# OUTILS MCP - TABLE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def inspect_table_deep(table_path: str, max_depth: int = 4, pid: int | None = None) -> str:
    """
    Inspection profonde d'une table Lua.
    
    Args:
        table_path: Chemin de la table (ex: "_G", "game.Players")
        max_depth: Profondeur max (1-5)
        pid: PID cible
    """
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    target = pid or clients[0][0]
    max_depth = min(max(max_depth, 1), 5)
    
    lua = _resolver_lua() + f"""
local tbl, err = resolvePath("{table_path}")
if tbl == nil then
    writeResult("ERROR: " .. tostring(err))
    return
end
if type(tbl) ~= "table" then
    writeResult("ERROR: type='" .. type(tbl) .. "' (not a table)")
    return
end

local visited = {{}}
local lines = {{"=== DEEP TABLE: {table_path} (depth={max_depth}) ==="}}

local function ins(t, depth, prefix)
    if depth > {max_depth} then
        table.insert(lines, prefix .. "[max depth]")
        return
    end
    if visited[t] then
        table.insert(lines, prefix .. "[circular]")
        return
    end
    visited[t] = true
    
    local count = 0
    for k, v in pairs(t) do
        count = count + 1
        if count > 150 then
            table.insert(lines, prefix .. "[...truncated at 150]")
            break
        end
        local ks = type(k) == "string" and k or ("[" .. tostring(k) .. "]")
        local vt = type(v)
        if vt == "table" then
            table.insert(lines, prefix .. ks .. " = {{")
            ins(v, depth + 1, prefix .. "  ")
            table.insert(lines, prefix .. "}}")
        elseif vt == "function" then
            table.insert(lines, prefix .. ks .. " = function()")
        elseif vt == "string" then
            table.insert(lines, prefix .. ks .. ' = "' .. v:sub(1, 60) .. '"')
        else
            table.insert(lines, prefix .. ks .. " = " .. tostring(v) .. " (" .. vt .. ")")
        end
    end
end

ins(tbl, 1, "")
writeResult(table.concat(lines, "\\n"))
"""
    return _execute_and_read(target, lua, wait=2.8)


# ═══════════════════════════════════════════════════════════════════════════════
# OUTILS MCP - HOOKS
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def create_hook(function_path: str, hook_type: str = "before", custom_code: str = "", pid: int | None = None) -> str:
    """
    Installe un hook sur une fonction.
    
    Args:
        function_path: Chemin de la fonction (ex: "require")
        hook_type: "before", "after", ou "replace"
        custom_code: Code Lua à exécuter
        pid: PID cible
    """
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    target = pid or clients[0][0]
    
    lua = _resolver_lua() + f"""
if not hookfunction then
    writeResult("ERROR: hookfunction not available")
    return
end

local orig, err = resolvePath("{function_path}")
if orig == nil or type(orig) ~= "function" then
    writeResult("ERROR: " .. tostring(err))
    return
end

local userCode = [==[{custom_code}]==]
local ht = "{hook_type}"
local newFn

if ht == "before" then
    newFn = function(...)
        if userCode ~= "" then pcall(loadstring(userCode), ...) end
        return orig(...)
    end
elseif ht == "after" then
    newFn = function(...)
        local r = {{orig(...)}}
        if userCode ~= "" then pcall(loadstring(userCode), ...) end
        return table.unpack(r)
    end
elseif ht == "replace" then
    if userCode == "" then
        newFn = function(...) end
    else
        newFn = function(...) return loadstring(userCode)(...) end
    end
else
    writeResult("ERROR: invalid hook_type '" .. ht .. "'")
    return
end

local hok, herr = pcall(hookfunction, orig, newFn)
local reg = getgenv and getgenv() or _G
reg.__mcp_hooks = reg.__mcp_hooks or {{}}
reg.__mcp_hooks["{function_path}"] = {{orig=orig, new=newFn, htype=ht}}

local out = "=== HOOK INSTALLED ===\\n"
out = out .. "Path: {function_path}\\n"
out = out .. "Type: {hook_type}\\n"
out = out .. "Result: " .. (hok and "SUCCESS" or "FAILED: " .. tostring(herr)) .. "\\n"
writeResult(out)
"""
    return _execute_and_read(target, lua, wait=1.5)


@mcp.tool()
def remove_hook(function_path: str, pid: int | None = None) -> str:
    """Supprime un hook et restaure la fonction originale."""
    clients = _get_clients()
    if not clients:
        return "❌ Erreur: Aucun client connecté."
    
    target = pid or clients[0][0]
    
    lua = f"""
local reg = getgenv and getgenv() or _G
local hooks = reg.__mcp_hooks or {{}}
local data = hooks["{function_path}"]
if not data then
    writeResult("ERROR: no hook for '{function_path}'")
    return
end
if hookfunction then
    pcall(hookfunction, data.new, data.orig)
end
hooks["{function_path}"] = nil
writeResult("=== HOOK REMOVED ===\\nPath: {function_path}\\nResult: SUCCESS")
"""
    return _execute_and_read(target, lua, wait=1.2)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    mcp.run()
