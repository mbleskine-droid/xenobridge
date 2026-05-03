"""
xeno_mcp_bridge.py — Xeno Executor MCP Server (XenoBridge C# Edition)

Install:  pip install fastmcp requests psutil pyperclip
Run:      python xeno_mcp_bridge.py

Requires: XenoBridge.exe running (or set BRIDGE_EXE_PATH below)
Bridge API: http://localhost:3111
"""

# Fix Unicode encoding on Windows
import sys
import io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import json
import os
import subprocess
import time
import uuid
import requests
import psutil
from fastmcp import FastMCP

# ─── Configuration ────────────────────────────────────────────────────────────

BRIDGE_URL     = "http://localhost:3111"

# Auto-detect bridge path (same directory as this script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_EXE_PATH = os.path.join(SCRIPT_DIR, "XenoBridge.exe")
# Fallback to common install locations if not found
if not os.path.exists(BRIDGE_EXE_PATH):
    fallback_paths = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "XenoBridgeMCP", "XenoBridge.exe"),
        os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "XenoBridgeMCP", "XenoBridge.exe"),
    ]
    for path in fallback_paths:
        if os.path.exists(path):
            BRIDGE_EXE_PATH = path
            break

TIMEOUT        = 10
EXEC_TIMEOUT   = 30

mcp = FastMCP("Xeno Bridge Executor")

_bridge_process = None

# ─── Bridge Lifecycle ─────────────────────────────────────────────────────────

def _is_bridge_running() -> bool:
    try:
        r = requests.get(f"{BRIDGE_URL}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def _wait_for_bridge(max_wait: float = 10.0) -> bool:
    start = time.time()
    while time.time() - start < max_wait:
        if _is_bridge_running():
            return True
        time.sleep(0.5)
    return False


def _start_bridge() -> str:
    global _bridge_process
    if _is_bridge_running():
        return "already_running"

    if not os.path.exists(BRIDGE_EXE_PATH):
        return f"exe_not_found:{BRIDGE_EXE_PATH}"

    try:
        _bridge_process = subprocess.Popen(
            [BRIDGE_EXE_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if _wait_for_bridge(max_wait=12.0):
            return "started"
        return "timeout"
    except Exception as e:
        return f"error:{e}"


def _stop_bridge():
    global _bridge_process
    if _bridge_process:
        try:
            _bridge_process.terminate()
            _bridge_process.wait(timeout=5)
        except Exception:
            pass
        _bridge_process = None


def _ensure_bridge():
    if not _is_bridge_running():
        result = _start_bridge()
        if result not in ("started", "already_running"):
            raise RuntimeError(f"Bridge could not start: {result}")


# ─── Bridge HTTP Helpers ──────────────────────────────────────────────────────

def _get_clients() -> list:
    r = requests.get(f"{BRIDGE_URL}/clients", timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return data.get("clients", [])


def _get_ready_pid(pid: int | None) -> int:
    clients = _get_clients()
    if not clients:
        raise RuntimeError("No clients connected.")
    if pid:
        return pid
    # Prefer state=3 (ready), fallback to first client
    ready = [c for c in clients if c.get("state", 0) == 3]
    target = ready[0] if ready else clients[0]
    return target["pid"]


def _execute(pid: int, script: str) -> bool:
    r = requests.post(
        f"{BRIDGE_URL}/execute",
        json={"script": script, "pid": pid},
        timeout=EXEC_TIMEOUT,
    )
    return r.status_code == 200 and r.json().get("success", False)


def _attach():
    requests.post(f"{BRIDGE_URL}/attach", json={"scan": True}, timeout=TIMEOUT)


def _set_setting(key: str, value):
    requests.post(
        f"{BRIDGE_URL}/setting",
        json={"key": key, "value": str(value)},
        timeout=TIMEOUT,
    )


# ─── Clipboard + File Helpers (unchanged from original) ──────────────────────

def _get_clipboard():
    try:
        import pyperclip
        return pyperclip.paste()
    except Exception:
        return None


def _unique_file() -> str:
    uid = uuid.uuid4().hex[:14]
    return f"mcp_out/{uid}.txt"


def _unique_marker() -> str:
    return f"[MCP_{uuid.uuid4().hex[:8]}]"


def _unique_callback_id() -> str:
    return uuid.uuid4().hex[:16]


# ─── HTTP Callback Helpers (v2 — replaces clipboard) ────────────────────────────

def _lua_http_callback(callback_id: str) -> str:
    """Return Lua snippet that POSTs result back to the bridge."""
    return f'''
local __CB_ID__ = "{callback_id}"
local __CB_URL__ = "http://localhost:3111/result/" .. __CB_ID__
local __CB_SENT__ = false
local function sendResult(text)
    if __CB_SENT__ then return end
    __CB_SENT__ = true
    local ok, hs = pcall(function() return game:GetService("HttpService") end)
    if not ok or not hs then
        -- fallback: try to write to file if HttpService unavailable
        if writefile then pcall(writefile, "mcp_out/" .. __CB_ID__ .. ".txt", tostring(text)) end
        return
    end
    local body = hs:JSONEncode({{content = tostring(text)}})
    local opts = {{
        Url = __CB_URL__,
        Method = "POST",
        Headers = {{["Content-Type"] = "application/json"}},
        Body = body
    }}
    if request then
        pcall(request, opts)
    elseif http_request then
        pcall(http_request, opts)
    elseif syn and syn.request then
        pcall(syn.request, opts)
    end
end
'''


def _get_result_http(callback_id: str, timeout: float = 8.0, poll_interval: float = 0.3) -> str | None:
    """Poll the bridge for a result posted via HTTP callback."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{BRIDGE_URL}/result/{callback_id}", timeout=3)
            if r.status_code == 200:
                data = r.json()
                if data.get("found"):
                    return data.get("content", "")
        except Exception:
            pass
        time.sleep(poll_interval)
    return None


def _execute_with_callback(pid: int, lua_code: str, exec_timeout: float = 30.0, poll_timeout: float = 8.0) -> str | None:
    """
    Execute Lua via XenoBridge and retrieve the result via HTTP callback.
    Returns the result string, or None if the callback failed/timed out.
    """
    callback_id = _unique_callback_id()

    # Prefix: ensure out dir exists + inject HTTP callback helper
    prefix = _ensure_outdir_lua() + _lua_http_callback(callback_id)

    # Wrap user code so that any return value or error is sent back
    wrapped = prefix + f"""
local __ok, __res = pcall(function()
{lua_code}
end)
if __ok then
    sendResult(tostring(__res))
else
    sendResult("[LUA_ERROR] " .. tostring(__res))
end
"""
    ok = _execute(pid, wrapped)
    if not ok:
        return None

    # Poll bridge for the result
    return _get_result_http(callback_id, timeout=poll_timeout)


def _execute_and_read_v2(pid: int, lua_code: str, wait: float = 2.0) -> str:
    """
    Attempt HTTP callback first, then fall back to the legacy file+clipboard method.
    """
    # ── Try HTTP callback (fast, reliable, no clipboard races) ──
    result = _execute_with_callback(pid, lua_code, poll_timeout=8.0)
    if result is not None:
        return result

    # ── Fallback: legacy file+clipboard ──
    return _execute_and_read_legacy(pid, lua_code, wait=wait)


def _execute_and_read_legacy(pid: int, lua_code: str, wait: float = 2.0) -> str:
    """Original file + clipboard implementation (kept as fallback)."""
    outfile = _unique_file()
    marker  = _unique_marker()

    prefix   = _ensure_outdir_lua() + _write_result_lua(outfile)
    full_lua = prefix + "\n" + lua_code

    ok = _execute(pid, full_lua)
    if not ok:
        return f"❌ Execution failed on PID {pid}."

    time.sleep(wait)

    read_lua = (
        f'local __MARKER__  = "{marker}"\n'
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

    result = None
    for attempt in range(4):
        time.sleep(0.9 if attempt == 0 else 0.6)
        result = _get_clipboard()
        if result and result.startswith(marker):
            return result[len(marker):].strip()

    return (
        f"⚠️ Clipboard validation failed after 4 retries.\n"
        f"Expected marker: {marker}\n"
        f"Got: {(result or '(empty)')[:120]}\n\n"
        "Try running one tool at a time, or increase wait time."
    )


def _execute_and_capture_smart(pid: int, lua_code: str, wait: float = 2.0) -> str:
    """
    Smart execution with fallback chain: HTTP callback → File+Clipboard.
    Wraps user code to capture print output and return value, then returns
    the captured result via the best available transport.
    """
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
sendResult(__final)
"""
    result = _execute_with_callback(pid, wrapped, poll_timeout=8.0)
    if result is not None:
        return result

    # Fallback to legacy
    return _execute_and_read_legacy(pid, wrapped, wait=wait)


# ─── Path Resolver Lua ────────────────────────────────────────────────────────

def _resolver_lua() -> str:
    return r"""
local function resolvePath(pathStr)
    if pathStr == nil or pathStr == "" then return nil, "empty path" end
    if pathStr == "game"      then return game, nil end
    if pathStr == "_G"        then return _G, nil end
    if pathStr == "workspace" then return workspace, nil end
    if pathStr == "script"    then return script, nil end
    local parts = {}
    for part in pathStr:gmatch("[^%.]+") do table.insert(parts, part) end
    if #parts == 0 then return nil, "no parts" end
    local current
    local root = parts[1]
    if root == "game"          then current = game
    elseif root == "_G"        then current = _G
    elseif root == "workspace" then current = workspace
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
                local fcOk = pcall(function() fc = current:FindFirstChild(seg) end)
                if fcOk and fc ~= nil then return fc end
            end
            return current[seg]
        end)
        if not ok then return nil, "error at '" .. seg .. "': " .. tostring(child) end
        if child == nil then return nil, "nil at segment '" .. seg .. "'" end
        current = child
    end
    return current, nil
end
"""


def _ensure_outdir_lua() -> str:
    return """
if not isfolder("mcp_out") then pcall(makefolder, "mcp_out") end
"""


def _write_result_lua(outfile: str) -> str:
    return f"""
local __OUTFILE__ = "{outfile}"
local function writeResult(text)
    if writefile then pcall(writefile, __OUTFILE__, tostring(text)) end
end
"""


def _execute_and_read(pid: int, lua_code: str, wait: float = 2.0) -> str:
    """Smart result retrieval — HTTP callback first, file+clipboard fallback."""
    return _execute_and_read_v2(pid, lua_code, wait=wait)


# ─── Bridge Management Tools ──────────────────────────────────────────────────

@mcp.tool()
def bridge_status() -> str:
    """Check XenoBridge status and version."""
    if not _is_bridge_running():
        return "❌ XenoBridge is not running. Use start_bridge() to start it."
    try:
        v = requests.get(f"{BRIDGE_URL}/version", timeout=TIMEOUT).json()
        return f"✅ XenoBridge is UP — Version: {v.get('version', '?')}"
    except Exception as e:
        return f"✅ Bridge is UP but /version failed: {e}"


@mcp.tool()
def start_bridge() -> str:
    """Start XenoBridge.exe if not already running."""
    if _is_bridge_running():
        return "✅ Bridge is already running."
    result = _start_bridge()
    if result == "started":
        return "✅ XenoBridge started successfully."
    if result == "already_running":
        return "✅ Bridge was already running."
    if result.startswith("exe_not_found"):
        return (
            f"❌ XenoBridge.exe not found at:\n{BRIDGE_EXE_PATH}\n\n"
            "Update BRIDGE_EXE_PATH in the script."
        )
    return f"❌ Failed to start bridge: {result}"


@mcp.tool()
def stop_bridge() -> str:
    """Stop the XenoBridge process."""
    _stop_bridge()
    return "✅ Bridge stopped."


@mcp.tool()
def attach_to_roblox() -> str:
    """Force XenoBridge to scan and attach to Roblox clients."""
    try:
        _ensure_bridge()
        _attach()
        time.sleep(2)
        clients = _get_clients()
        ready = [c for c in clients if c.get("state", 0) == 3]
        return (
            f"✅ Attach requested. {len(clients)} client(s) found, "
            f"{len(ready)} ready (state=3)."
        )
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def set_auto_attach(enabled: bool) -> str:
    """Enable or disable auto-attach in XenoBridge."""
    try:
        _ensure_bridge()
        _set_setting("auto_attach", "1" if enabled else "0")
        return f"✅ Auto-attach: {'ON' if enabled else 'OFF'}"
    except Exception as e:
        return f"ERROR: {e}"


# ─── Basic Tools ──────────────────────────────────────────────────────────────

@mcp.tool()
def check_api_status() -> str:
    """Ping the XenoBridge API."""
    return bridge_status()


@mcp.tool()
def list_clients() -> str:
    """List all attached Roblox clients."""
    try:
        _ensure_bridge()
        clients = _get_clients()
        if not clients:
            return "No clients connected."
        state_icons = {0: "🔴", 1: "🟡", 2: "🔵", 3: "🟢"}
        lines = []
        for c in clients:
            icon = state_icons.get(c.get("state", 0), "⚪")
            lines.append(f"{icon} PID {c['pid']} | {c.get('name', '?')} | state={c.get('state', '?')}")
        return "Connected clients:\n" + "\n".join(lines)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def execute_script(lua_code: str, pid: int | None = None) -> str:
    """
    Execute Lua on a client via XenoBridge.

    Args:
        lua_code: Lua source to run.
        pid: Target PID (optional, auto-picks state=3 client).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)
        ok = _execute(target, lua_code)
        return f"✅ Executed on PID {target}." if ok else f"❌ Failed on PID {target}."
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def execute_and_capture(lua_code: str, pid: int | None = None, wait_time: float = 2.0) -> str:
    """
    Execute Lua and capture print output + return value.
    Uses HTTP callback first, falls back to file+clipboard if needed.

    Args:
        lua_code: Lua source to run.
        pid: Target PID (optional).
        wait_time: Seconds to wait (default 2.0).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)
        return _execute_and_capture_smart(target, lua_code, wait=wait_time)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def broadcast_script(lua_code: str) -> str:
    """Execute on ALL connected clients."""
    try:
        _ensure_bridge()
        clients = _get_clients()
        if not clients:
            return "ERROR: No clients connected."
        results = []
        for c in clients:
            ok = _execute(c["pid"], lua_code)
            icon = "✅" if ok else "❌"
            results.append(f"{icon} PID {c['pid']} ({c.get('name', '?')})")
        return "Broadcast:\n" + "\n".join(results)
    except Exception as e:
        return f"ERROR: {e}"


# ─── Game Explorer ────────────────────────────────────────────────────────────

@mcp.tool()
def explore_game_tree(path: str = "game", depth: int = 3, pid: int | None = None) -> str:
    """
    Explore game instance hierarchy.

    Args:
        path: Starting path e.g. "game", "game.Workspace".
        depth: Levels deep (default 3, max 5).
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)
        depth  = min(depth, 5)

        lua = _resolver_lua() + f"""
local root, err = resolvePath("{path}")
if root == nil then writeResult("ERROR: " .. tostring(err)) return end
local function explore(obj, cur, max, indent)
    if cur > max then return "" end
    local out = ""
    local ok2, ch = pcall(function() return obj:GetChildren() end)
    if not ok2 then return out end
    for _, child in ipairs(ch) do
        out = out .. indent .. "|- "
            .. tostring(child.Name) .. " (" .. tostring(child.ClassName) .. ")\\n"
        if cur < max then out = out .. explore(child, cur + 1, max, indent .. "   ") end
    end
    return out
end
local ok2, nm  = pcall(function() return root.Name end)
local ok3, cls = pcall(function() return root.ClassName end)
local out = "=== GAME TREE: {path} (depth={depth}) ===\\n"
out = out .. (ok2 and tostring(nm) or "{path}") .. " ("
          .. (ok3 and tostring(cls) or "?") .. ")\\n"
out = out .. explore(root, 1, {depth}, "")
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=2.5)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def find_instances(class_name: str, parent_path: str = "game", pid: int | None = None) -> str:
    """
    Find all instances of a ClassName.

    Args:
        class_name: e.g. "RemoteEvent", "Part".
        parent_path: Root to search (default "game").
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        lua = _resolver_lua() + f"""
local parent, err = resolvePath("{parent_path}")
if parent == nil then writeResult("ERROR: " .. tostring(err)) return end
local function getPath(obj)
    local p = tostring(obj.Name)
    local c = obj.Parent
    while c and c ~= game do p = tostring(c.Name) .. "." .. p; c = c.Parent end
    return "game." .. p
end
local results = {{}}
local ok2, descs = pcall(function() return parent:GetDescendants() end)
if ok2 then
    for _, obj in ipairs(descs) do
        if obj.ClassName == "{class_name}" then table.insert(results, getPath(obj)) end
    end
end
local out = "=== FIND '{class_name}' in '{parent_path}' ===\\nFound: " .. #results .. "\\n\\n"
for i, p in ipairs(results) do out = out .. i .. ". " .. p .. "\\n" end
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=2.0)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def get_instance_properties(instance_path: str, pid: int | None = None) -> str:
    """
    Get all readable properties of a Roblox Instance.

    Args:
        instance_path: e.g. "game.Workspace.Baseplate".
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        lua = _resolver_lua() + f"""
local inst, err = resolvePath("{instance_path}")
if inst == nil then writeResult("ERROR: " .. tostring(err)) return end
local ok2, cn = pcall(function() return inst.ClassName end)
local out = "=== PROPERTIES: {instance_path} ===\\nClass: " .. (ok2 and tostring(cn) or "?") .. "\\n\\n"
local props = {{
    "Name","Parent","Archivable","Position","Size","CFrame","Orientation",
    "Transparency","Color","Material","CanCollide","Anchored","Velocity",
    "Health","MaxHealth","WalkSpeed","JumpPower","Text","Value","Enabled"
}}
for _, pn in ipairs(props) do
    local pok, pv = pcall(function() return inst[pn] end)
    if pok and pv ~= nil then out = out .. pn .. ": " .. tostring(pv) .. "\\n" end
end
local aok, attrs = pcall(function() return inst:GetAttributes() end)
if aok and attrs and next(attrs) then
    out = out .. "\\n=== ATTRIBUTES ===\\n"
    for k, v in pairs(attrs) do out = out .. tostring(k) .. ": " .. tostring(v) .. "\\n" end
end
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=1.8)
    except Exception as e:
        return f"ERROR: {e}"


# ─── Script Tools ─────────────────────────────────────────────────────────────

@mcp.tool()
def decompile_script(script_path: str, pid: int | None = None) -> str:
    """
    Decompile a LocalScript or ModuleScript.

    Args:
        script_path: e.g. "game.Players.LocalPlayer.PlayerScripts.MyScript".
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        lua = _resolver_lua() + f"""
local scr, err = resolvePath("{script_path}")
if scr == nil then writeResult("ERROR: " .. tostring(err)) return end
local isOk, isScript = pcall(function() return scr:IsA("LuaSourceContainer") end)
if not (isOk and isScript) then
    writeResult("ERROR: not a script, got " .. tostring(scr.ClassName)) return
end
local source = nil
if decompile then local dok, dr = pcall(decompile, scr); if dok then source = dr end
elseif getsrc then local sok, sr = pcall(getsrc, scr); if sok then source = sr end end
local out = "=== DECOMPILE: " .. scr.Name .. " (" .. scr.ClassName .. ") ===\\n\\n"
out = out .. (source or "ERROR: no decompiler (tried decompile, getsrc)")
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=3.5)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def find_all_scripts(script_type: str = "all", parent_path: str = "game", pid: int | None = None) -> str:
    """
    Find all Lua scripts in the game.

    Args:
        script_type: "LocalScript", "Script", "ModuleScript", or "all".
        parent_path: Root to search (default "game").
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        lua = _resolver_lua() + f"""
local parent, err = resolvePath("{parent_path}")
if parent == nil then writeResult("ERROR: " .. tostring(err)) return end
local function getPath(obj)
    local p = tostring(obj.Name)
    local c = obj.Parent
    while c and c ~= game do p = tostring(c.Name) .. "." .. p; c = c.Parent end
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
        for i, p in ipairs(paths) do out = out .. "  " .. i .. ". " .. p .. "\\n" end
    end
end
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=2.5)
    except Exception as e:
        return f"ERROR: {e}"


# ─── Remote Spy ───────────────────────────────────────────────────────────────

@mcp.tool()
def list_all_remotes(pid: int | None = None) -> str:
    """List all RemoteEvents and RemoteFunctions."""
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        lua = """
local function getPath(obj)
    local p = tostring(obj.Name)
    local c = obj.Parent
    while c and c ~= game do p = tostring(c.Name) .. "." .. p; c = c.Parent end
    return "game." .. p
end
local evts, funcs = {}, {}
for _, obj in ipairs(game:GetDescendants()) do
    if obj:IsA("RemoteEvent") then table.insert(evts, getPath(obj))
    elseif obj:IsA("RemoteFunction") then table.insert(funcs, getPath(obj)) end
end
local out = "=== REMOTE CATALOG ===\\n\\nRemoteEvents (" .. #evts .. "):\\n"
for i, p in ipairs(evts) do out = out .. "  " .. i .. ". " .. p .. "\\n" end
out = out .. "\\nRemoteFunctions (" .. #funcs .. "):\\n"
for i, p in ipairs(funcs) do out = out .. "  " .. i .. ". " .. p .. "\\n" end
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=2.5)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def spy_remotes(duration: int = 30, filter_type: str = "all", pid: int | None = None) -> str:
    """
    Spy on remote calls for N seconds. Read results with read_file() after.

    Args:
        duration: How long to spy (default 30s).
        filter_type: "RemoteEvent", "RemoteFunction", or "all".
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target  = _get_ready_pid(pid)
        outfile = _unique_file()

        setup = _ensure_outdir_lua()
        lua = setup + f"""
local calls = {{}}
local t0 = tick()
local function getPath(obj)
    local p = tostring(obj.Name)
    local c = obj.Parent
    while c and c ~= game do p = tostring(c.Name) .. "." .. p; c = c.Parent end
    return "game." .. p
end
local function argStr(...)
    local args = {{...}}
    local ss = {{}}
    for i, a in ipairs(args) do
        if i > 5 then table.insert(ss, "...") break end
        local t = type(a)
        if t == "string" then table.insert(ss, '"' .. a:sub(1, 40) .. '"')
        elseif t == "number" or t == "boolean" then table.insert(ss, tostring(a))
        elseif t == "table" then table.insert(ss, "table[" .. #a .. "]")
        else table.insert(ss, t) end
    end
    return table.concat(ss, ", ")
end
if hookmetamethod then
    local old
    old = hookmetamethod(game, "__namecall", function(self, ...)
        local m  = getnamecallmethod()
        local ft = "{filter_type}"
        if (ft == "all" or ft == "RemoteEvent") and self:IsA("RemoteEvent") and m == "FireServer" then
            table.insert(calls, {{path=getPath(self), method=m, args=argStr(...), t=tick()-t0}})
        end
        if (ft == "all" or ft == "RemoteFunction") and self:IsA("RemoteFunction") and m == "InvokeServer" then
            table.insert(calls, {{path=getPath(self), method=m, args=argStr(...), t=tick()-t0}})
        end
        return old(self, ...)
    end)
end
task.wait({duration})
local out = "=== REMOTE SPY ({duration}s) ===\\nCaptured: " .. #calls .. "\\n\\n"
for _, c in ipairs(calls) do
    out = out .. string.format("[%.2fs] %s:%s(%s)\\n", c.t, c.path, c.method, c.args)
end
if writefile then pcall(writefile, "{outfile}", out) end
"""
        _execute(target, lua)
        return (
            f"✅ Remote spy running on PID {target} for {duration}s.\n"
            f"📄 Output: {outfile}\n"
            f"⏳ Call  read_file('{outfile}')  after {duration}s."
        )
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def spy_http_requests(duration: int = 30, pid: int | None = None) -> str:
    """
    Spy on HTTP requests for N seconds. Read results with read_file() after.

    Args:
        duration: How long to spy (default 30s).
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target  = _get_ready_pid(pid)
        outfile = _unique_file()

        setup = _ensure_outdir_lua()
        lua = setup + f"""
local reqs = {{}}
local t0 = tick()
local HS = game:GetService("HttpService")
local function cap(method, url, body)
    body = body or ""
    if #body > 80 then body = body:sub(1, 80) .. "..." end
    table.insert(reqs, {{method=method, url=url, body=body, t=tick()-t0}})
end
local oldReq = HS.RequestAsync
HS.RequestAsync = function(self, opts)
    cap(opts.Method or "GET", opts.Url or "?", opts.Body)
    return oldReq(self, opts)
end
local oldGet = HS.GetAsync
HS.GetAsync = function(self, url, ...)
    cap("GET", url, "")
    return oldGet(self, url, ...)
end
local oldPost = HS.PostAsync
HS.PostAsync = function(self, url, data, ...)
    cap("POST", url, data)
    return oldPost(self, url, data, ...)
end
if request then
    local oldR = request
    request = function(opts)
        cap(opts.Method or "GET", opts.Url or "?", opts.Body)
        return oldR(opts)
    end
end
task.wait({duration})
local out = "=== HTTP SPY ({duration}s) ===\\nCaptured: " .. #reqs .. "\\n\\n"
for _, r in ipairs(reqs) do
    out = out .. string.format("[%.2fs] %s %s\\n  Body: %s\\n\\n", r.t, r.method, r.url, r.body)
end
if writefile then pcall(writefile, "{outfile}", out) end
"""
        _execute(target, lua)
        return (
            f"✅ HTTP spy running on PID {target} for {duration}s.\n"
            f"📄 Output: {outfile}\n"
            f"⏳ Call  read_file('{outfile}')  after {duration}s."
        )
    except Exception as e:
        return f"ERROR: {e}"


# ─── Debugger ─────────────────────────────────────────────────────────────────

@mcp.tool()
def get_stack_trace(pid: int | None = None) -> str:
    """Get current Lua call stack."""
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

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
            level, tostring(info.name or "?"),
            tostring(info.source or "?"), tostring(info.currentline or "?"))
    end
else
    out = out .. "debug.getinfo not available\\n"
end
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=1.5)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def debug_function(function_path: str, pid: int | None = None) -> str:
    """
    Inspect a function: source, params, constants, upvalues.

    Args:
        function_path: e.g. "string.format", "require".
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        lua = _resolver_lua() + f"""
local fn, err = resolvePath("{function_path}")
if fn == nil or type(fn) ~= "function" then
    writeResult("ERROR: not a valid function: " .. tostring(err)) return
end
local out = "=== FUNCTION DEBUG: {function_path} ===\\n\\n"
if debug and debug.getinfo then
    local ok2, i = pcall(debug.getinfo, fn)
    if ok2 and i then
        out = out .. "Source:      " .. tostring(i.source or "?") .. "\\n"
        out = out .. "LineDefined: " .. tostring(i.linedefined or "?") .. "\\n"
        out = out .. "Params:      " .. tostring(i.nparams or "?") .. "\\n"
        out = out .. "Upvalues:    " .. tostring(i.nups or "?") .. "\\n\\n"
    end
end
if debug and debug.getconstants then
    local ok3, consts = pcall(debug.getconstants, fn)
    if ok3 and consts then
        out = out .. "=== CONSTANTS (" .. #consts .. ") ===\\n"
        for i2, c in ipairs(consts) do
            if i2 > 60 then out = out .. "  ...\\n" break end
            out = out .. "  " .. i2 .. ". " .. tostring(c) .. " (" .. type(c) .. ")\\n"
        end
        out = out .. "\\n"
    end
end
if debug and debug.getupvalues then
    local ok4, uvs = pcall(debug.getupvalues, fn)
    if ok4 and uvs then
        out = out .. "=== UPVALUES ===\\n"
        local n = 0
        for name, val in pairs(uvs) do
            n = n + 1
            if n > 30 then out = out .. "  ...\\n" break end
            out = out .. "  " .. tostring(name) .. " = " .. tostring(val) .. " (" .. type(val) .. ")\\n"
        end
    end
end
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=1.8)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def trace_function_calls(function_names: str, duration: int = 10, pid: int | None = None) -> str:
    """
    Hook functions and log every call for N seconds.

    Args:
        function_names: Comma-separated e.g. "require,loadstring".
        duration: Seconds to trace (default 10).
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target  = _get_ready_pid(pid)
        outfile = _unique_file()

        funcs = [f.strip() for f in function_names.split(",")]
        hook_blocks = ""
        for i, fn in enumerate(funcs):
            hook_blocks += f"""
do
    local _ok{i}, _orig{i} = pcall(function() return resolvePath("{fn}") end)
    if _ok{i} and _orig{i} and type(_orig{i}) == "function" then
        local _o{i} = _orig{i}
        local _n{i} = function(...)
            local ss = {{}}
            for j, v in ipairs({{...}}) do
                if j > 5 then ss[j] = "..." break end
                ss[j] = tostring(v):sub(1, 50)
            end
            table.insert(__calls, {{fn="{fn}", args=table.concat(ss, ", "), t=tick()-__t0}})
            return _o{i}(...)
        end
        pcall(hookfunction, _o{i}, _n{i})
    end
end
"""
        setup = _ensure_outdir_lua()
        lua = setup + _resolver_lua() + f"""
local __calls = {{}}
local __t0    = tick()
{hook_blocks}
task.wait({duration})
local out = "=== CALL TRACE ({duration}s): {function_names} ===\\nCaptured: " .. #__calls .. "\\n\\n"
for _, c in ipairs(__calls) do
    out = out .. string.format("[%.2fs] %s(%s)\\n", c.t, c.fn, c.args)
end
if writefile then pcall(writefile, "{outfile}", out) end
"""
        _execute(target, lua)
        return (
            f"✅ Tracing [{function_names}] on PID {target} for {duration}s.\n"
            f"📄 Output: {outfile}\n"
            f"⏳ Call  read_file('{outfile}')  after {duration}s."
        )
    except Exception as e:
        return f"ERROR: {e}"


# ─── Upvalue Tools ────────────────────────────────────────────────────────────

@mcp.tool()
def dump_all_upvalues(function_path: str, recursive: bool = True, max_depth: int = 3, pid: int | None = None) -> str:
    """
    Dump all upvalues of a function recursively.

    Args:
        function_path: e.g. "require".
        recursive: Dump nested function upvalues (default True).
        max_depth: Recursion limit (default 3).
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target  = _get_ready_pid(pid)
        rec_str = "true" if recursive else "false"

        lua = _resolver_lua() + f"""
local fn, err = resolvePath("{function_path}")
if fn == nil or type(fn) ~= "function" then
    writeResult("ERROR: " .. tostring(err)) return
end
if not (debug and debug.getupvalues) then
    writeResult("ERROR: debug.getupvalues not available on this executor") return
end
local visited = {{}}
local lines = {{"=== UPVALUE DUMP: {function_path} ===", "Recursive: {rec_str}  MaxDepth: {max_depth}", ""}}
local function dump(f, depth, prefix)
    if depth > {max_depth} then table.insert(lines, prefix .. "[max depth]") return end
    if visited[f] then table.insert(lines, prefix .. "[circular]") return end
    visited[f] = true
    local ok2, uvs = pcall(debug.getupvalues, f)
    if not ok2 or not uvs or not next(uvs) then
        table.insert(lines, prefix .. "[no upvalues]") return
    end
    for name, val in pairs(uvs) do
        local vt = type(val)
        if vt == "function" then
            table.insert(lines, prefix .. tostring(name) .. " = function()")
            if {rec_str} then dump(val, depth + 1, prefix .. "  ") end
        elseif vt == "table" then
            local n = 0
            for _ in pairs(val) do n = n + 1 end
            table.insert(lines, prefix .. tostring(name) .. " = table[" .. n .. "]")
        elseif vt == "string" then
            table.insert(lines, prefix .. tostring(name) .. ' = "' .. val:sub(1, 80) .. '"')
        else
            table.insert(lines, prefix .. tostring(name) .. " = " .. tostring(val) .. " (" .. vt .. ")")
        end
    end
end
dump(fn, 1, "")
writeResult(table.concat(lines, "\\n"))
"""
        return _execute_and_read(target, lua, wait=2.2)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def search_upvalues(function_path: str, search_term: str, search_type: str = "value", pid: int | None = None) -> str:
    """
    Search upvalues by name or value.

    Args:
        function_path: Dot-path to function.
        search_term: Pattern to find.
        search_type: "name" or "value" (default "value").
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        lua = _resolver_lua() + f"""
local fn, err = resolvePath("{function_path}")
if fn == nil or type(fn) ~= "function" then
    writeResult("ERROR: " .. tostring(err)) return
end
if not (debug and debug.getupvalues) then
    writeResult("ERROR: debug.getupvalues not available") return
end
local ok2, uvs = pcall(debug.getupvalues, fn)
if not ok2 or not uvs then writeResult("ERROR: could not get upvalues") return end
local term = string.lower("{search_term}")
local stype = "{search_type}"
local matches = {{}}
for name, val in pairs(uvs) do
    local hit = false
    if stype == "name" then hit = string.lower(tostring(name)):find(term, 1, true) ~= nil
    else hit = string.lower(tostring(val)):find(term, 1, true) ~= nil end
    if hit then table.insert(matches, {{name=tostring(name), val=tostring(val), vt=type(val)}}) end
end
local out = "=== UPVALUE SEARCH: {function_path} ===\\nTerm: '{search_term}'  Mode: {search_type}\\nFound: " .. #matches .. "\\n\\n"
for i, m in ipairs(matches) do
    out = out .. i .. ". " .. m.name .. " = " .. m.val:sub(1, 100) .. " (" .. m.vt .. ")\\n"
end
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=1.5)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def modify_upvalue(function_path: str, upvalue_name: str, new_value_expr: str, pid: int | None = None) -> str:
    """
    Modify an upvalue at runtime.

    Args:
        function_path: Dot-path to function.
        upvalue_name: Name of upvalue to change.
        new_value_expr: Lua expression e.g. "true", "42", '"hello"'.
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        lua = _resolver_lua() + f"""
local fn, err = resolvePath("{function_path}")
if fn == nil or type(fn) ~= "function" then
    writeResult("ERROR: " .. tostring(err)) return
end
if not (debug and debug.setupvalue) then
    writeResult("ERROR: debug.setupvalue not available") return
end
local evok, newVal = pcall(function() return loadstring("return {new_value_expr}")() end)
if not evok then writeResult("ERROR: invalid value expression") return end
local result = debug.setupvalue(fn, "{upvalue_name}", newVal)
local out = "=== MODIFY UPVALUE ===\\nFunction: {function_path}\\nUpvalue:  {upvalue_name}\\n"
out = out .. "NewValue: " .. tostring(newVal) .. "\\nResult:   " .. (result and "SUCCESS" or "FAILED") .. "\\n"
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=1.3)
    except Exception as e:
        return f"ERROR: {e}"


# ─── Table Inspector ──────────────────────────────────────────────────────────

@mcp.tool()
def inspect_table_deep(table_path: str, max_depth: int = 4, show_metatables: bool = False, pid: int | None = None) -> str:
    """
    Deep recursive inspection of a Lua table.

    Args:
        table_path: Dot-path to table e.g. "_G".
        max_depth: Recursion depth (default 4).
        show_metatables: Show metatables (default False).
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target  = _get_ready_pid(pid)
        show_mt = "true" if show_metatables else "false"

        lua = _resolver_lua() + f"""
local tbl, err = resolvePath("{table_path}")
if tbl == nil then writeResult("ERROR: " .. tostring(err)) return end
if type(tbl) ~= "table" then
    writeResult("ERROR: type='" .. type(tbl) .. "' is not a table.") return
end
local visited = {{}}
local lines = {{"=== DEEP TABLE: {table_path} (depth={max_depth}) ==="}}
local function ins(t, depth, prefix)
    if depth > {max_depth} then table.insert(lines, prefix .. "[max depth]") return end
    if visited[t] then table.insert(lines, prefix .. "[circular]") return end
    visited[t] = true
    local count = 0
    for k, v in pairs(t) do
        count = count + 1
        if count > 150 then table.insert(lines, prefix .. "[...truncated at 150]") break end
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
    if {show_mt} then
        local mt = getmetatable(t)
        if mt and type(mt) == "table" then
            table.insert(lines, prefix .. "[METATABLE] = {{")
            ins(mt, depth + 1, prefix .. "  ")
            table.insert(lines, prefix .. "}}")
        end
    end
end
ins(tbl, 1, "")
writeResult(table.concat(lines, "\\n"))
"""
        return _execute_and_read(target, lua, wait=2.8)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def search_in_table(table_path: str, search_key: str = "", search_value: str = "", pid: int | None = None) -> str:
    """
    Recursively search a Lua table for matching keys or values.

    Args:
        table_path: Dot-path to table e.g. "_G".
        search_key: Key substring to match (optional).
        search_value: Value substring to match (optional).
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        lua = _resolver_lua() + f"""
local tbl, err = resolvePath("{table_path}")
if tbl == nil then writeResult("ERROR: " .. tostring(err)) return end
if type(tbl) ~= "table" then
    writeResult("ERROR: type='" .. type(tbl) .. "' is not a Lua table.") return
end
local sk = string.lower("{search_key}")
local sv = string.lower("{search_value}")
local visited = {{}}
local matches = {{}}
local function search(t, path)
    if visited[t] then return end
    visited[t] = true
    for k, v in pairs(t) do
        local ks = string.lower(tostring(k))
        local vs = string.lower(tostring(v))
        local kp = path .. "." .. tostring(k)
        local km = (sk == "" or ks:find(sk, 1, true) ~= nil)
        local vm = (sv == "" or vs:find(sv, 1, true) ~= nil)
        if km and vm then
            table.insert(matches, {{path=kp, val=tostring(v):sub(1, 80), vt=type(v)}})
        end
        if type(v) == "table" and #matches < 200 then search(v, kp) end
    end
end
search(tbl, "{table_path}")
local out = "=== TABLE SEARCH: {table_path} ===\\nKey='{search_key}'  Value='{search_value}'\\nFound: " .. #matches .. "\\n\\n"
for i, m in ipairs(matches) do
    if i > 100 then out = out .. "  ...\\n" break end
    out = out .. i .. ". " .. m.path .. " = " .. m.val .. " (" .. m.vt .. ")\\n"
end
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=2.5)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def compare_instances(instance_path1: str, instance_path2: str, pid: int | None = None) -> str:
    """
    Compare properties of two Roblox Instances side-by-side.

    Args:
        instance_path1: e.g. "game.Players.LocalPlayer".
        instance_path2: e.g. "game.Players.OtherPlayer".
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        lua = _resolver_lua() + f"""
local i1, e1 = resolvePath("{instance_path1}")
if i1 == nil then writeResult("ERROR: first path: " .. tostring(e1)) return end
local i2, e2 = resolvePath("{instance_path2}")
if i2 == nil then writeResult("ERROR: second path: " .. tostring(e2)) return end
local props = {{
    "Name","ClassName","Archivable","Position","Size","CFrame","Orientation",
    "Transparency","Color","Material","CanCollide","Anchored",
    "Health","MaxHealth","WalkSpeed","JumpPower","Text","Value","Enabled"
}}
local out = "=== INSTANCE COMPARE ===\\nA: {instance_path1}\\nB: {instance_path2}\\n\\n"
local same, diff = 0, 0
for _, pn in ipairs(props) do
    local aok, av = pcall(function() return i1[pn] end)
    local bok, bv = pcall(function() return i2[pn] end)
    if aok and bok and av ~= nil and bv ~= nil then
        local as = tostring(av)
        local bs = tostring(bv)
        if as == bs then same = same + 1
        else
            diff = diff + 1
            out = out .. "  " .. pn .. ":\\n    A = " .. as:sub(1, 60) .. "\\n    B = " .. bs:sub(1, 60) .. "\\n"
        end
    end
end
out = out .. "\\nSame: " .. same .. "  Different: " .. diff .. "\\n"
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=1.8)
    except Exception as e:
        return f"ERROR: {e}"


# ─── Hook Manager ─────────────────────────────────────────────────────────────

@mcp.tool()
def create_hook(function_path: str, hook_type: str = "before", custom_code: str = "", pid: int | None = None) -> str:
    """
    Install a hook (before / after / replace).

    Args:
        function_path: Dot-path to function e.g. "require".
        hook_type: "before", "after", or "replace".
        custom_code: Lua to run (args available as vararg ...).
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        lua = _resolver_lua() + f"""
if not hookfunction then writeResult("ERROR: hookfunction not available") return end
local orig, err = resolvePath("{function_path}")
if orig == nil or type(orig) ~= "function" then
    writeResult("ERROR: " .. tostring(err)) return
end
local userCode = [==[{custom_code}]==]
local ht = "{hook_type}"
local newFn
if ht == "before" then
    newFn = function(...) if userCode ~= "" then pcall(loadstring(userCode), ...) end return orig(...) end
elseif ht == "after" then
    newFn = function(...) local r = {{orig(...)}} if userCode ~= "" then pcall(loadstring(userCode), ...) end return table.unpack(r) end
elseif ht == "replace" then
    if userCode == "" then newFn = function(...) end
    else newFn = function(...) return loadstring(userCode)(...) end end
else
    writeResult("ERROR: invalid hook_type '" .. ht .. "'") return
end
local hok, herr = pcall(hookfunction, orig, newFn)
local reg = getgenv and getgenv() or _G
reg.__mcp_hooks = reg.__mcp_hooks or {{}}
reg.__mcp_hooks["{function_path}"] = {{orig=orig, new=newFn, htype=ht}}
local out = "=== HOOK INSTALLED ===\\nPath:   {function_path}\\nType:   {hook_type}\\n"
out = out .. "Result: " .. (hok and "SUCCESS" or "FAILED: " .. tostring(herr)) .. "\\n"
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=1.5)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def list_active_hooks(pid: int | None = None) -> str:
    """List all active MCP-managed hooks."""
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        lua = """
local reg   = getgenv and getgenv() or _G
local hooks = reg.__mcp_hooks or {}
local lines = {"=== ACTIVE MCP HOOKS ===", ""}
local n = 0
for path, data in pairs(hooks) do
    n = n + 1
    table.insert(lines, n .. ". " .. tostring(path) .. "  [" .. tostring(data.htype) .. "]")
end
if n == 0 then table.insert(lines, "(no active hooks)") end
table.insert(lines, "\\nTotal: " .. n)
writeResult(table.concat(lines, "\\n"))
"""
        return _execute_and_read(target, lua, wait=1.2)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def remove_hook(function_path: str, pid: int | None = None) -> str:
    """
    Remove a hook and restore the original function.

    Args:
        function_path: Same path used in create_hook.
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        lua = f"""
local reg   = getgenv and getgenv() or _G
local hooks = reg.__mcp_hooks or {{}}
local data  = hooks["{function_path}"]
if not data then writeResult("ERROR: no hook for '{function_path}'") return end
if hookfunction then pcall(hookfunction, data.new, data.orig) end
hooks["{function_path}"] = nil
writeResult("=== HOOK REMOVED ===\\nPath: {function_path}\\nResult: SUCCESS")
"""
        return _execute_and_read(target, lua, wait=1.2)
    except Exception as e:
        return f"ERROR: {e}"


# ─── Proxy ────────────────────────────────────────────────────────────────────

@mcp.tool()
def create_proxy_object(target_path: str, log_access: bool = True, log_modification: bool = True, pid: int | None = None) -> str:
    """
    Wrap a table in a transparent proxy that logs all reads and writes.

    Args:
        target_path: Dot-path to table e.g. "_G".
        log_access: Log reads (default True).
        log_modification: Log writes (default True).
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)
        log_a  = "true" if log_access else "false"
        log_m  = "true" if log_modification else "false"

        lua = _resolver_lua() + f"""
local targetObj, err = resolvePath("{target_path}")
if targetObj == nil then writeResult("ERROR: " .. tostring(err)) return end
local accessLog = {{}}
local modLog    = {{}}
local t0        = tick()
local proxy     = {{}}
setmetatable(proxy, {{
    __index    = function(_, key)
        if {log_a} then table.insert(accessLog, {{key=tostring(key), t=tick()-t0}}) end
        return targetObj[key]
    end,
    __newindex = function(_, key, value)
        if {log_m} then table.insert(modLog, {{key=tostring(key), val=tostring(value), t=tick()-t0}}) end
        targetObj[key] = value
    end,
    __tostring = function() return "MCPProxy[" .. tostring(targetObj) .. "]" end
}})
local reg = getgenv and getgenv() or _G
reg.__mcp_proxies = reg.__mcp_proxies or {{}}
reg.__mcp_proxies["{target_path}"] = {{proxy=proxy, accessLog=accessLog, modLog=modLog}}
local out = "=== PROXY CREATED ===\\nTarget:    {target_path}\\nLogReads:  {log_a}\\nLogWrites: {log_m}\\n\\n"
out = out .. "Stored at __mcp_proxies['{target_path}']\\nCall get_proxy_logs('{target_path}') to view activity."
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=1.5)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def get_proxy_logs(proxy_path: str, log_type: str = "all", pid: int | None = None) -> str:
    """
    Retrieve activity logs from a proxy object.

    Args:
        proxy_path: Same path used in create_proxy_object.
        log_type: "access", "modification", or "all" (default).
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        lua = f"""
local reg     = getgenv and getgenv() or _G
local proxies = reg.__mcp_proxies or {{}}
local data    = proxies["{proxy_path}"]
if not data then
    writeResult("ERROR: no proxy for '{proxy_path}'. Call create_proxy_object first.") return
end
local lt  = "{log_type}"
local out = "=== PROXY LOGS: {proxy_path} ===\\n\\n"
if lt == "all" or lt == "access" then
    out = out .. "=== READ LOG (" .. #data.accessLog .. " events) ===\\n"
    for i, e in ipairs(data.accessLog) do
        if i > 100 then out = out .. "  ...\\n" break end
        out = out .. string.format("  [%.2fs] READ  %s\\n", e.t, e.key)
    end
    out = out .. "\\n"
end
if lt == "all" or lt == "modification" then
    out = out .. "=== WRITE LOG (" .. #data.modLog .. " events) ===\\n"
    for i, e in ipairs(data.modLog) do
        if i > 100 then out = out .. "  ...\\n" break end
        out = out .. string.format("  [%.2fs] WRITE %s = %s\\n", e.t, e.key, e.val)
    end
end
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=1.3)
    except Exception as e:
        return f"ERROR: {e}"


# ─── Event Tracer ─────────────────────────────────────────────────────────────

@mcp.tool()
def trace_events(instance_path: str, event_names: str = "all", duration: int = 30, pid: int | None = None) -> str:
    """
    Listen to events on an instance for N seconds.

    Args:
        instance_path: e.g. "game.Players.LocalPlayer".
        event_names: Comma-separated names or "all".
        duration: Seconds to listen (default 30).
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target  = _get_ready_pid(pid)
        outfile = _unique_file()

        setup = _ensure_outdir_lua()
        lua = setup + _resolver_lua() + f"""
local inst, err = resolvePath("{instance_path}")
if inst == nil then
    if writefile then pcall(writefile, "{outfile}", "ERROR: " .. tostring(err)) end return
end
local evtStr   = "{event_names}"
local evtNames = {{}}
if evtStr == "all" then
    for _, e in ipairs({{"Changed","ChildAdded","ChildRemoved","DescendantAdded","DescendantRemoving","AncestryChanged"}}) do
        table.insert(evtNames, e)
    end
    pcall(function()
        for key, val in pairs(inst) do
            if type(val) == "RBXScriptSignal" then table.insert(evtNames, key) end
        end
    end)
else
    for name in evtStr:gmatch("[^,]+") do table.insert(evtNames, name:match("^%s*(.-)%s*$")) end
end
local log = {{}}
local t0  = tick()
local conns = {{}}
for _, en in ipairs(evtNames) do
    local eok, ev = pcall(function() return inst[en] end)
    if eok and type(ev) == "RBXScriptSignal" then
        local c = ev:Connect(function(...)
            local ss = {{}}
            for i, v in ipairs({{...}}) do if i > 5 then break end ss[i] = tostring(v):sub(1, 40) end
            table.insert(log, {{e=en, args=table.concat(ss, ", "), t=tick()-t0}})
        end)
        table.insert(conns, c)
    end
end
task.wait({duration})
for _, c in ipairs(conns) do pcall(function() c:Disconnect() end) end
local out = "=== EVENT TRACE: {instance_path} ({duration}s) ===\\nHooked: " .. #conns .. "  |  Fired: " .. #log .. "\\n\\n"
for i, e in ipairs(log) do
    if i > 200 then out = out .. "  ...\\n" break end
    out = out .. string.format("[%.2fs] %s(%s)\\n", e.t, e.e, e.args)
end
if writefile then pcall(writefile, "{outfile}", out) end
"""
        _execute(target, lua)
        return (
            f"✅ Event tracing on PID {target} for {duration}s.\n"
            f"📄 Output: {outfile}\n"
            f"⏳ Call  read_file('{outfile}')  after {duration}s."
        )
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def trace_instance_lifecycle(instance_path: str, duration: int = 60, pid: int | None = None) -> str:
    """
    Monitor instance lifecycle for N seconds (children added/removed).

    Args:
        instance_path: Dot-path to parent instance.
        duration: Seconds to monitor (default 60).
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target  = _get_ready_pid(pid)
        outfile = _unique_file()

        setup = _ensure_outdir_lua()
        lua = setup + _resolver_lua() + f"""
local inst, err = resolvePath("{instance_path}")
if inst == nil then
    if writefile then pcall(writefile, "{outfile}", "ERROR: " .. tostring(err)) end return
end
local log = {{}}
local t0  = tick()
local conns = {{}}
local function cap(evType, child)
    table.insert(log, {{e=evType, name=tostring(child.Name), class=tostring(child.ClassName), t=tick()-t0}})
end
table.insert(conns, inst.ChildAdded:Connect(function(c) cap("ChildAdded", c) end))
table.insert(conns, inst.ChildRemoved:Connect(function(c) cap("ChildRemoved", c) end))
table.insert(conns, inst.DescendantAdded:Connect(function(c) cap("DescendantAdded", c) end))
table.insert(conns, inst.DescendantRemoving:Connect(function(c) cap("DescendantRemoving", c) end))
task.wait({duration})
for _, c in ipairs(conns) do pcall(function() c:Disconnect() end) end
local out = "=== LIFECYCLE: {instance_path} ({duration}s) ===\\nTotal events: " .. #log .. "\\n\\n"
for i, e in ipairs(log) do
    if i > 200 then out = out .. "  ...\\n" break end
    out = out .. string.format("[%.2fs] %s: %s (%s)\\n", e.t, e.e, e.name, e.class)
end
if writefile then pcall(writefile, "{outfile}", out) end
"""
        _execute(target, lua)
        return (
            f"✅ Lifecycle on PID {target} for {duration}s.\n"
            f"📄 Output: {outfile}\n"
            f"⏳ Call  read_file('{outfile}')  after {duration}s."
        )
    except Exception as e:
        return f"ERROR: {e}"


# ─── Deobfuscation ────────────────────────────────────────────────────────────

@mcp.tool()
def extract_strings(script_code: str, min_length: int = 3, wait_time: float = 2.5, pid: int | None = None) -> str:
    """
    Hook string.char to capture decoded constants from obfuscated Lua.

    Args:
        script_code: Obfuscated Lua source.
        min_length: Minimum length to capture (default 3).
        wait_time: Seconds to wait (default 2.5).
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        lua = f"""
local __strings = {{}}
local __seen    = {{}}
local __oldChar = string.char
string.char = function(...)
    local r = __oldChar(...)
    if #r >= {min_length} and not __seen[r] and r:match("[a-zA-Z0-9]") then
        __seen[r] = true
        table.insert(__strings, r)
    end
    return r
end
pcall(function() loadstring([==[{script_code}]==])() end)
string.char = __oldChar
local out = "=== EXTRACTED STRINGS (" .. #__strings .. ") ===\\n\\n"
for i, s in ipairs(__strings) do out = out .. i .. ". " .. s .. "\\n" end
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=wait_time)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def dump_globals(filter_pattern: str = "", pid: int | None = None) -> str:
    """
    List all global variables, optionally filtered.

    Args:
        filter_pattern: Lua pattern to filter names (optional).
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        filter_code = f'and k:match("{filter_pattern}")' if filter_pattern else ""
        lua = f"""
local sorted = {{}}
for k, v in pairs(getfenv(0)) do
    if type(k) == "string" {filter_code} then table.insert(sorted, {{k=k, t=type(v)}}) end
end
table.sort(sorted, function(a, b) return a.k < b.k end)
local out = "=== GLOBALS (" .. #sorted .. ") ===\\n\\n"
for _, e in ipairs(sorted) do out = out .. e.k .. " : " .. e.t .. "\\n" end
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=1.8)
    except Exception as e:
        return f"ERROR: {e}"


# ─── File System ──────────────────────────────────────────────────────────────

@mcp.tool()
def read_file(filepath: str, pid: int | None = None) -> str:
    """
    Read any file from the executor workspace.
    Uses HTTP callback first, falls back to clipboard.

    Args:
        filepath: e.g. "mcp_out/abc123.txt" or "capture.txt".
        pid: Target PID (optional).
    """
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        callback_id = _unique_callback_id()
        lua = _lua_http_callback(callback_id) + f'''
local __F__ = "{filepath}"
if not readfile then
    sendResult("[ERROR] readfile not available")
    return
end
local ok2, content = pcall(readfile, __F__)
if ok2 and content then
    sendResult(content)
else
    sendResult("[READ_ERROR] " .. tostring(content))
end
'''
        ok = _execute(target, lua)
        if not ok:
            return f"❌ Execution failed on PID {target}."

        result = _get_result_http(callback_id, timeout=6.0)
        if result is not None:
            return result

        # Fallback: legacy clipboard
        marker = _unique_marker()
        lua_fallback = (
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
        _execute(target, lua_fallback)
        for attempt in range(4):
            time.sleep(1.0 if attempt == 0 else 0.6)
            result = _get_clipboard()
            if result and result.startswith(marker):
                return result[len(marker):].strip()

        return f"⚠️ read_file: failed to retrieve '{filepath}' via HTTP and clipboard."
    except Exception as e:
        return f"ERROR: {e}"


# ─── Utilities ────────────────────────────────────────────────────────────────

@mcp.tool()
def test_capture(pid: int | None = None) -> str:
    """End-to-end test of the capture pipeline."""
    return execute_and_capture(
        'print("LINE_1")\nprint("LINE_2")\nreturn "CAPTURE_OK"',
        pid,
        wait_time=1.8,
    )


@mcp.tool()
def inspect_environment(pid: int | None = None) -> str:
    """Check which executor capabilities are available."""
    try:
        _ensure_bridge()
        target = _get_ready_pid(pid)

        lua = """
local caps = {
    {"setclipboard",       type(setclipboard) == "function"},
    {"writefile",          type(writefile) == "function"},
    {"readfile",           type(readfile) == "function"},
    {"delfile",            type(delfile) == "function"},
    {"makefolder",         type(makefolder) == "function"},
    {"isfolder",           type(isfolder) == "function"},
    {"hookfunction",       type(hookfunction) == "function"},
    {"hookmetamethod",     type(hookmetamethod) == "function"},
    {"newproxy",           type(newproxy) == "function"},
    {"getrawmetatable",    type(getrawmetatable) == "function"},
    {"getgenv",            type(getgenv) == "function"},
    {"getfenv",            type(getfenv) == "function"},
    {"loadstring",         type(loadstring) == "function"},
    {"decompile",          type(decompile) == "function"},
    {"getsrc",             type(getsrc) == "function"},
    {"request",            type(request) == "function"},
    {"debug.getinfo",      debug ~= nil and type(debug.getinfo) == "function"},
    {"debug.getconstants", debug ~= nil and type(debug.getconstants) == "function"},
    {"debug.getupvalues",  debug ~= nil and type(debug.getupvalues) == "function"},
    {"debug.setupvalue",   debug ~= nil and type(debug.setupvalue) == "function"},
    {"debug.traceback",    debug ~= nil and type(debug.traceback) == "function"},
}
local out = "=== EXECUTOR CAPABILITIES ===\\n\\n"
for _, c in ipairs(caps) do
    out = out .. (c[2] and "[YES]" or "[ NO]") .. "  " .. c[1] .. "\\n"
end
writeResult(out)
"""
        return _execute_and_read(target, lua, wait=1.5)
    except Exception as e:
        return f"ERROR: {e}"


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("[MCP] Checking XenoBridge...")
    if not _is_bridge_running():
        print("[MCP] Bridge not running, starting...")
        result = _start_bridge()
        if result in ("started", "already_running"):
            print("[MCP] ✅ Bridge started.")
        else:
            print(f"[MCP] ⚠️  Bridge could not start ({result}).")
            print(f"[MCP]    Update BRIDGE_EXE_PATH in the script and try again.")
            print(f"[MCP]    Current path: {BRIDGE_EXE_PATH}")
    else:
        print("[MCP] ✅ Bridge already running.")

    mcp.run()

# ─── Windsurf Config ──────────────────────────────────────────────────────────
# %APPDATA%\Windsurf\mcp_config.json  (or .codeium/windsurf/mcp_config.json)
# {
#   "mcpServers": {
#     "xeno-bridge": {
#       "command": "python",
#       "args": ["C:/ABSOLUTE/PATH/xeno_mcp_bridge.py"]
#     }
#   }
# }
