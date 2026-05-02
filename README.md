# 🎮 XenoBridge MCP

**Bridge C# pour Xeno Executor avec serveur MCP Python**

Un bridge HTTP qui expose les fonctionnalités de Xeno.dll (injection Roblox) via une API REST, utilisable par un serveur MCP (Model Context Protocol) pour intégration avec Claude, Windsurf, et autres assistants IA.

---

## 📁 Structure du projet

```
xenobridge/
├── XenoBridge/                     # Projet C# du Bridge
│   ├── Program.cs                  # Code principal
│   ├── XenoBridge.csproj         # Configuration projet
│   └── build.bat                 # Script de compilation
├── xeno_mcp_bridge-claude-version.py  # MCP Python (version Claude)
├── install_xeno_mcp.py              # Script d'installation auto
└── README.md                       # Ce fichier
```

---

## 🚀 Installation rapide

### 1. Télécharge et lance l'installateur

```powershell
curl -o install_xeno_mcp.py https://raw.githubusercontent.com/mbleskine-droid/xenobridge/main/install_xeno_mcp.py
python install_xeno_mcp.py
```

### 2. Mets les fichiers binaires

L'installateur ouvre automatiquement :
- 📂 L'explorateur sur le dossier d'installation
- 🌐 Le navigateur sur `https://xeno.now/download`

**Copie dans le dossier d'installation :**
- `Xeno.dll` (depuis le site officiel)
- `XenoBridge.exe` (optionnel, compilable depuis le projet C#)

### 3. Configure Windsurf/Claude

Ajoute cette configuration à ton `mcp_config.json` :

```json
{
  "mcpServers": {
    "xeno-bridge-claude": {
      "command": "python",
      "args": [
        "C:/Users/TonUser/AppData/Local/XenoBridgeMCP/xeno_mcp_bridge-claude-version.py"
      ],
      "disabled": false
    }
  }
}
```

### 4. Relance le script

```powershell
python install_xeno_mcp.py
```

Le serveur MCP se lance automatiquement en arrière-plan !

---

## 🔧 Compilation manuelle (optionnel)

Si tu veux compiler XenoBridge.exe toi-même :

```powershell
cd XenoBridge
.\build.bat
```

**Prérequis :** .NET 8.0 SDK

---

## 🌐 API du Bridge

Le bridge C# expose ces endpoints sur `http://localhost:3111` :

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/health` | GET | Vérifie si le bridge fonctionne |
| `/version` | GET | Retourne la version de Xeno.dll |
| `/clients` | GET | Liste les clients Roblox détectés |
| `/attach` | POST | Attache à un processus Roblox |
| `/execute` | POST | Exécute du Lua sur un client |
| `/setting` | POST | Change un paramètre Xeno |

---

## 📝 Outils MCP disponibles

Une fois le serveur lancé, ces outils sont disponibles dans Claude/Windsurf :

- **`xeno_attach`** - Attache à un client Roblox
- **`xeno_execute`** - Exécute du code Lua
- **`xeno_get_clients`** - Liste les clients Roblox
- **`xeno_set_setting`** - Modifie les paramètres Xeno
- **`xeno_version`** - Affiche la version

---

## 📦 Dossier d'installation

```
%LOCALAPPDATA%\XenoBridgeMCP\
├── xeno_mcp_bridge-claude-version.py
├── mcp_config.json
├── logs\mcp.log
├── temp\
├── Xeno.dll          ← À télécharger manuellement
└── XenoBridge.exe    ← Optionnel (compilable)
```

---

## ⚠️ Important

- **Xeno.dll** n'est PAS inclus dans ce repo (propriétaire)
- Tu dois la télécharger depuis `https://xeno.now/download`
- Ce projet est uniquement un **bridge technique**

---

## 🔗 Liens

- **Repo GitHub** : https://github.com/mbleskine-droid/xenobridge
- **Xeno Download** : https://xeno.now/download
- **MCP Documentation** : https://modelcontextprotocol.io

---

## 🛠️ Développement

### Dépendances Python
```
fastmcp
requests
psutil
pyperclip
```

### Stack technique
- **C#** (.NET 8.0) - Bridge HTTP natif
- **Python** - Serveur MCP
- **HTTP API** - Communication Bridge ↔ MCP

---

Made with 🎮 by Zenith
