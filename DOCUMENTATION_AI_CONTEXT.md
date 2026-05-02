# 📚 Documentation Complète pour AI - XenoBridge MCP Integration

**Document**: Guide complet pour permettre à une IA sans contexte de créer un MCP Python utilisant XenoBridge C#  
**Version**: 2.0  
**Date**: 2 Mai 2026  
**Auteur**: Zenith__  

---

## 🎯 OBJECTIF DU PROMPT

Quand l'utilisateur demande:
> *"peut tu me faire une version de ce script mcp python mais qui utilise mon bridge c# a la place"*

L'IA doit comprendre qu'il faut:
1. **Analyser le script MCP Python existant** (qui utilise Xeno.dll directement)
2. **Créer une nouvelle version** qui utilise le **XenoBridge C#** via son API HTTP
3. **Gérer le cycle de vie du Bridge** (démarrage, surveillance, arrêt)

---

## 📁 ARCHITECTURE DU SYSTÈME

### Structure des Fichiers

```
xeno-re/
├── Xeno-v1.3.30/                    # Executor Xeno original
│   ├── Xeno.dll                     # DLL principale (injection Lua)
│   └── ...
├── XenoBridge/                      # Bridge C# (NOUVEAU)
│   ├── Program.cs                   # Code source C#
│   ├── bin/Release/.../XenoBridge.exe
│   └── Xeno.dll                     # Copiée ici pour le Bridge
├── xeno_mcp.py                      # MCP ORIGINAL (direct Xeno)
├── xeno_mcp_bridge_full.py          # MCP NOUVEAU (utilise Bridge)
└── mcp_config.json                  # Configuration Windsurf
```

### Composants Clés

| Composant | Technologie | Port | Rôle |
|-----------|-------------|------|------|
| Xeno.dll | C++ DLL | - | Injection Lua dans Roblox |
| XenoBridge.exe | C# (.NET 8) | 3111 | Wrapper HTTP pour Xeno.dll |
| xeno_mcp.py | Python (FastMCP) | MCP stdio | MCP utilisant Xeno.dll directement |
| xeno_mcp_bridge_full.py | Python (FastMCP) | MCP stdio + HTTP 3111 | MCP utilisant le Bridge |

---

## 🔧 COMPOSANT 1: XenoBridge C#

### Description
Le XenoBridge est un **serveur HTTP C#** qui:
- Charge `Xeno.dll` en mémoire
- Expose les fonctions de Xeno via une API REST
- Écoute sur `localhost:3111`

### Endpoints HTTP

| Méthode | Endpoint | Description | Paramètres |
|---------|----------|-------------|------------|
| GET | `/health` | Vérifier si le Bridge fonctionne | - |
| GET | `/version` | Version de Xeno.dll | - |
| GET | `/clients` | Liste des clients Roblox détectés | - |
| POST | `/attach` | Forcer l'attachement à Roblox | `{"scan": true}` |
| POST | `/execute` | Exécuter un script Lua | `{"script": "print('test')", "pid": 1234}` |
| POST | `/setting` | Modifier une configuration | `{"key": "auto_attach", "value": true}` |

### Exemple de Réponses

**GET /clients:**
```json
{
  "success": true,
  "clients": [
    {"pid": 1234, "name": "RobloxPlayer", "state": 3}
  ]
}
```

**POST /execute:**
```json
{
  "success": true,
  "executed": true,
  "pid": 1234
}
```

### État des Clients (state)

| State | Couleur | Signification |
|-------|---------|---------------|
| 0 | 🔴 | Déconnecté |
| 1 | 🟡 | En attente |
| 2 | 🔵 | Attaché |
| 3 | 🟢 | **Prêt à exécuter** |

### Code Source Clé (Program.cs)

```csharp
// Initialisation Xeno.dll
[DllImport("Xeno.dll")] static extern bool Attach();
[DllImport("Xeno.dll")] static extern string GetClients();
[DllImport("Xeno.dll")] static extern bool Execute(int pid, string script);
[DllImport("Xeno.dll")] static extern void SetSetting(string key, string value);

// Serveur HTTP sur port 3111
var listener = new HttpListener();
listener.Prefixes.Add("http://localhost:3111/");
```

---

## 🐍 COMPOSANT 2: MCP Python Original (xeno_mcp.py)

### Ce qu'il fait
Ce script MCP utilise **directement** `Xeno.dll` via `ctypes`:

```python
import ctypes

# Chargement direct de la DLL
xeno_dll = ctypes.windll.LoadLibrary("Xeno-v1.3.30/Xeno.dll")

# Appel direct des fonctions
xeno_dll.Attach()
clients = xeno_dll.GetClients()
xeno_dll.Execute(pid, script.encode())
```

### Limitations
- Nécessite que Xeno.dll soit accessible directement
- Gestion manuelle des appels de fonction C
- Pas d'isolation du processus Xeno
- Doit être dans le même processus que la DLL

---

## 🚀 COMPOSANT 3: MCP Python avec Bridge (xeno_mcp_bridge_full.py)

### Ce qu'il fait différemment
Ce script MCP utilise le **Bridge C#** via HTTP:

```python
import requests

# Communication HTTP avec le Bridge
response = requests.post("http://localhost:3111/execute", 
    json={"script": "print('test')", "pid": 1234})
```

### Fonctionnalités Additionnelles

1. **Auto-démarrage du Bridge:**
   ```python
   def start_bridge():
       # Lance XenoBridge.exe en sous-processus
       subprocess.Popen(["XenoBridge.exe"], ...)
       # Attend que le port 3111 réponde
       wait_for_health_check()
   ```

2. **Gestion du cycle de vie:**
   ```python
   def ensure_bridge_running():
       if not is_bridge_alive():
           start_bridge()
   ```

3. **Auto-détection des clients:**
   ```python
   # Si aucun PID fourni, trouve le client avec state=3
   def auto_detect_client():
       clients = requests.get("http://localhost:3111/clients").json()
       ready_client = next(c for c in clients if c["state"] == 3)
       return ready_client["pid"]
   ```

---

## 🔄 FLUX DE DONNÉES

### Ancienne Architecture (Direct)
```
Windsurf → MCP Python → ctypes → Xeno.dll → Roblox
              ↑
         (même processus)
```

### Nouvelle Architecture (Via Bridge)
```
Windsurf → MCP Python → HTTP → XenoBridge.exe → Xeno.dll → Roblox
              ↑                         ↑
         (subprocess)           (HTTP API :3111)
```

### Avantages du Bridge

| Aspect | Direct (Ancien) | Bridge (Nouveau) |
|--------|-----------------|-------------------|
| Isolation | ❌ Même processus | ✅ Processus séparé |
| Stabilité | ❌ Crash = tout arrêt | ✅ Bridge crash = redémarrage |
| API | ❌ ctypes complexe | ✅ HTTP simple |
| Multi-client | ❌ Limité | ✅ Gestion avancée |
| Monitoring | ❌ Difficile | ✅ Health check facile |

---

## 🛠️ EXIGENCES TECHNIQUES

### Dépendances Python

```bash
pip install fastmcp requests psutil pyperclip
```

| Package | Usage |
|---------|-------|
| fastmcp | Framework MCP |
| requests | HTTP client pour Bridge |
| psutil | Gestion des processus |
| pyperclip | Capture sortie via clipboard |

### Dépendances C#

- .NET 8.0 SDK
- Xeno.dll (à copier dans le dossier du Bridge)

### Ports Réseau

| Port | Utilisation |
|------|-------------|
| 3111 | XenoBridge HTTP API |
| MCP stdio | Communication Windsurf-MCP |

---

## 💻 CODE CLÉ À IMPLÉMENTER

### 1. Wrappers HTTP Bridge

```python
import requests

BRIDGE_URL = "http://localhost:3111"

def _get_clients():
    """Liste les clients via Bridge"""
    resp = requests.get(f"{BRIDGE_URL}/clients", timeout=5)
    return resp.json()["clients"]

def _execute(script: str, pids: list):
    """Exécute script via Bridge"""
    for pid in pids:
        requests.post(f"{BRIDGE_URL}/execute", 
            json={"script": script, "pid": pid}, timeout=30)

def _attach():
    """Force l'attachement via Bridge"""
    requests.post(f"{BRIDGE_URL}/attach", 
        json={"scan": True}, timeout=10)

def _set_setting(key: str, value):
    """Modifie paramètre via Bridge"""
    requests.post(f"{BRIDGE_URL}/setting",
        json={"key": key, "value": str(value)}, timeout=5)
```

### 2. Gestion Sous-Processus Bridge

```python
import subprocess
import psutil

_bridge_process = None

def start_bridge():
    """Démarre XenoBridge.exe"""
    global _bridge_process
    _bridge_process = subprocess.Popen(
        ["XenoBridge.exe"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    # Attendre que le health check réponde
    wait_for_bridge_ready()

def stop_bridge():
    """Arrête le Bridge"""
    if _bridge_process:
        _bridge_process.terminate()
        _bridge_process.wait()

def is_bridge_running():
    """Vérifie si Bridge répond"""
    try:
        requests.get(f"{BRIDGE_URL}/health", timeout=2)
        return True
    except:
        return False
```

### 3. Outils MCP (@mcp.tool())

```python
from fastmcp import FastMCP

mcp = FastMCP("Xeno Bridge Executor")

@mcp.tool()
def bridge_status() -> str:
    """Vérifier le statut du Bridge"""
    if not is_bridge_running():
        return "❌ Bridge arrêté"
    version = requests.get(f"{BRIDGE_URL}/version").json()
    return f"✅ Bridge OK - Version {version['version']}"

@mcp.tool()
def list_clients() -> str:
    """Lister les clients Roblox"""
    clients = _get_clients()
    result = []
    for c in clients:
        emoji = ["🔴", "🟡", "🔵", "🟢"][c["state"]]
        result.append(f"{emoji} PID {c['pid']}: {c['name']} (state={c['state']})")
    return "\n".join(result)

@mcp.tool()
def execute_script(code: str, pids: str = "auto") -> str:
    """
    Exécuter un script Lua dans Roblox
    
    Args:
        code: Code Lua à exécuter
        pids: "auto" ou liste de PIDs (ex: "1234,5678")
    """
    if pids == "auto":
        # Trouver automatiquement le client prêt (state=3)
        clients = _get_clients()
        ready = [c for c in clients if c["state"] == 3]
        if not ready:
            return "❌ Aucun client en state=3 prêt"
        target_pids = [ready[0]["pid"]]
    else:
        target_pids = [int(p.strip()) for p in pids.split(",")]
    
    _execute(code, target_pids)
    return f"✅ Script exécuté sur PID {target_pids}"

@mcp.tool()
def attach_to_roblox() -> str:
    """Forcer l'attachement à Roblox"""
    _attach()
    return "✅ Attachement demandé"

@mcp.tool()
def set_auto_attach(enabled: bool) -> str:
    """Activer/désactiver l'auto-attachement"""
    _set_setting("auto_attach", "1" if enabled else "0")
    return f"✅ Auto-attach: {'ON' if enabled else 'OFF'}"
```

### 4. Point d'Entrée

```python
if __name__ == "__main__":
    # Démarrer le Bridge automatiquement
    if not is_bridge_running():
        start_bridge()
    
    # Lancer le serveur MCP
    mcp.run()
```

---

## 📋 CHECKLIST POUR L'IA

Quand l'utilisateur demande la version Bridge, l'IA doit:

- [ ] **Lire le script MCP original** pour comprendre les outils MCP existants
- [ ] **Identifier les appels directs à Xeno.dll** (ctypes, CDLL, etc.)
- [ ] **Créer des wrappers HTTP** vers `localhost:3111` pour chaque fonction
- [ ] **Ajouter la gestion du sous-processus** (start_bridge, stop_bridge)
- [ ] **Implémenter le health check** avant chaque appel
- [ ] **Garder les mêmes @mcp.tool()** mais adapter le corps des fonctions
- [ ] **Ajouter l'auto-démarrage** du Bridge au lancement du MCP
- [ ] **Gérer les erreurs** (Bridge non démarré, timeout, etc.)
- [ ] **Conserver les fonctionnalités** (capture output, auto-detect PID, etc.)

---

## ⚠️ PIÈGES COURANTS À ÉVITER

### 1. Chemin XenoBridge.exe
```python
# ❌ Mauvais
"XenoBridge.exe"

# ✅ Bon - Chemin absolu
"C:/Users/.../xeno-re/XenoBridge/bin/Release/net8.0-windows/win-x64/XenoBridge.exe"
```

### 2. Xeno.dll Manquante
```python
# ❌ Le Bridge crashera sans Xeno.dll dans son dossier
# ✅ Il faut copier Xeno.dll à côté de XenoBridge.exe AVANT de démarrer
```

### 3. Port Déjà Utilisé
```python
# ❌ Démarrer 2 fois = erreur port 3111
# ✅ Vérifier si déjà en cours: requests.get("http://localhost:3111/health")
```

### 4. Timeout Trop Court
```python
# ❌ /execute peut prendre plusieurs secondes
# ✅ Mettre timeout=30 pour l'exécution
```

### 5. Encodage Lua
```python
# ❌ Envoyer tel quel
# ✅ Encoder correctement les caractères spéciaux dans le JSON
```

---

## 🔍 EXEMPLE COMPLET: Conversion d'un Outil

### AVANT (Direct Xeno)

```python
@mcp.tool()
def execute_script(code: str, pid: int = 0) -> str:
    import ctypes
    
    xeno = ctypes.windll.LoadLibrary("Xeno-v1.3.30/Xeno.dll")
    xeno.Attach()
    
    if pid == 0:
        # Trouver PID automatiquement
        import json
        clients = json.loads(xeno.GetClients())
        pid = clients[0]["pid"]
    
    xeno.Execute(pid, code.encode())
    return f"Exécuté sur PID {pid}"
```

### APRÈS (Via Bridge)

```python
@mcp.tool()
def execute_script(code: str, pid: int = 0) -> str:
    import requests
    
    # S'assurer que le Bridge tourne
    ensure_bridge_running()
    
    if pid == 0:
        # Obtenir clients via Bridge
        resp = requests.get("http://localhost:3111/clients")
        clients = resp.json()["clients"]
        pid = next(c["pid"] for c in clients if c["state"] == 3)
    
    # Exécuter via Bridge
    requests.post("http://localhost:3111/execute",
        json={"script": code, "pid": pid}, timeout=30)
    
    return f"Exécuté sur PID {pid}"
```

---

## 📎 FICHIERS DE RÉFÉRENCE

| Fichier | Description | Emplacement |
|---------|-------------|-------------|
| xeno_mcp.py | MCP original (direct Xeno) | `Documents/xeno_mcp.py` |
| xeno_mcp_bridge_full.py | MCP avec Bridge | `windsurf/xeno-re/` |
| XenoBridge/Program.cs | Bridge C# source | `windsurf/xeno-re/XenoBridge/` |
| XenoBridge.exe | Bridge compilé | `XenoBridge/bin/Release/.../win-x64/` |
| mcp_config.json | Config Windsurf | `.codeium/windsurf/mcp_config.json` |

---

## 🎓 COMPREHENSION CLÉ POUR L'IA

### La Question Centrale

L'utilisateur veut **découpler** le MCP de Xeno.dll:
- **Avant**: MCP Python ↔ Xeno.dll (couplage fort)
- **Après**: MCP Python ↔ HTTP ↔ XenoBridge C# ↔ Xeno.dll (couplage faible)

### Pourquoi?

1. **Stabilité**: Si Xeno.dll crash, seul le Bridge crash, pas le MCP
2. **Réutilisabilité**: Le Bridge peut être utilisé par d'autres outils
3. **Monitoring**: HTTP permet health checks, logs, métriques
4. **Flexibilité**: Le MCP peut redémarrer le Bridge si besoin

### La Solution Attendue

Un script Python qui:
1. Démarre automatiquement `XenoBridge.exe`
2. Utilise `requests` pour parler au Bridge sur `localhost:3111`
3. Gère les cas d'erreur (Bridge down, timeout, etc.)
4. Garde les mêmes outils MCP que l'original

---

**FIN DE LA DOCUMENTATION**

Cette documentation contient TOUTES les informations nécessaires pour qu'une IA comprenne le contexte et crée correctement la version Bridge du MCP Python.
