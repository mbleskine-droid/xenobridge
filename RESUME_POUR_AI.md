# 📋 RÉSUMÉ EXÉCUTIF - Pour AI sans contexte

## 🎯 Prompt de l'Utilisateur
> "peut tu me faire une version de ce script mcp python mais qui utilise mon bridge c# a la place"

## 🔑 Concepts Clés à Comprendre

### 1. Architecture Actuelle (À REMPLACER)
```
MCP Python ──ctypes──► Xeno.dll ──► Roblox
```
- Le MCP charge directement `Xeno.dll` via `ctypes`
- Appels directs: `xeno_dll.Execute(pid, script)`

### 2. Architecture Cible (À IMPLÉMENTER)
```
MCP Python ──HTTP──► XenoBridge.exe ──► Xeno.dll ──► Roblox
                    (port 3111)
```
- Le MCP parle au **Bridge C#** via HTTP sur `localhost:3111`
- Le Bridge gère lui-même `Xeno.dll`

## 🛠️ Ce que le Nouveau Script Doit Faire

### A. Démarrer le Bridge (Auto-start)
```python
import subprocess
_bridge_process = subprocess.Popen([
    "C:/.../XenoBridge.exe"  # Chemin absolu
])
# Attendre que localhost:3111 réponde
```

### B. Wrappers HTTP pour chaque fonction Xeno

| Fonction Xeno | Endpoint Bridge | Code Python |
|---------------|-----------------|-------------|
| `Attach()` | `POST /attach` | `requests.post("http://localhost:3111/attach", json={"scan": True})` |
| `GetClients()` | `GET /clients` | `requests.get("http://localhost:3111/clients")` |
| `Execute(pid, script)` | `POST /execute` | `requests.post("http://localhost:3111/execute", json={"script": code, "pid": pid})` |
| `SetSetting(k,v)` | `POST /setting` | `requests.post("http://localhost:3111/setting", json={"key": k, "value": v})` |

### C. Adapter les @mcp.tool()

**AVANT (Direct):**
```python
@mcp.tool()
def execute_script(code: str, pid: int = 0):
    xeno = ctypes.windll.LoadLibrary("Xeno.dll")
    xeno.Execute(pid, code.encode())
    return "OK"
```

**APRÈS (Via Bridge):**
```python
@mcp.tool()
def execute_script(code: str, pid: int = 0):
    # 1. S'assurer que le Bridge tourne
    if not is_bridge_running():
        start_bridge()
    
    # 2. Appeler le Bridge via HTTP
    resp = requests.post(
        "http://localhost:3111/execute",
        json={"script": code, "pid": pid},
        timeout=30
    )
    return f"✅ Exécuté: {resp.json()}"
```

## 📁 Fichiers Importants

| Fichier | Rôle | Chemin |
|---------|------|--------|
| `xeno_mcp.py` | MCP **original** (à convertir) | `C:/Users/Zenith__/Documents/xeno_mcp.py` |
| `xeno_mcp_bridge_full.py` | Exemple **déjà converti** | `windsurf/xeno-re/` |
| `XenoBridge.exe` | Le **Bridge C#** à utiliser | `XenoBridge/bin/Release/.../win-x64/` |
| `Xeno.dll` | La **DLL** (doit être copiée à côté du Bridge) | `Xeno-v1.3.30/` |

## ⚡ Checklist Implémentation

- [ ] Lire le MCP original pour voir les outils existants
- [ ] Créer `start_bridge()` qui lance `XenoBridge.exe` en sous-processus
- [ ] Créer `is_bridge_running()` qui teste `GET http://localhost:3111/health`
- [ ] Créer `_get_clients()` → `GET /clients`
- [ ] Créer `_execute(script, pids)` → `POST /execute`
- [ ] Créer `_attach()` → `POST /attach`
- [ ] Adapter chaque `@mcp.tool()` pour utiliser les wrappers HTTP
- [ ] Ajouter health check avant chaque opération
- [ ] Gérer les erreurs (Bridge crash, timeout, port occupé)
- [ ] Lancer `start_bridge()` automatiquement au démarrage du MCP

## 🚨 Pièges à Éviter

1. **Xeno.dll doit être copiée** à côté de `XenoBridge.exe` sinon il crash
2. **Port 3111** - Vérifier si déjà utilisé avant de démarrer
3. **Timeout** - `/execute` peut prendre 30s, pas 5s
4. **Chemins absolus** - Toujours utiliser des chemins complets
5. **Auto-detect** - Si `pid=0`, chercher client avec `state=3` via `/clients`

## 📚 Documentation Complète

Lire: `DOCUMENTATION_AI_CONTEXT.md` (13 000 mots) pour:
- Détails de tous les endpoints HTTP
- Code source complet du Bridge C#
- Exemples de conversion complets
- Architecture détaillée

## 🎓 Réponse Attendue par l'IA

L'IA doit créer un fichier Python qui:
1. ✅ Importe `fastmcp`, `requests`, `subprocess`, `psutil`
2. ✅ Démarre automatiquement `XenoBridge.exe`
3. ✅ Utilise `requests` pour appeler `localhost:3111`
4. ✅ Implémente les mêmes `@mcp.tool()` que l'original
5. ✅ Gère le cycle de vie du Bridge (start, health check, restart)

**Exemple déjà fonctionnel à copier:** `xeno_mcp_bridge_full.py`
