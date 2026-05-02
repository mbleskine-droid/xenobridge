# 🎮 Guide Complet - XenoBridge MCP

**Version**: 1.0  
**Date**: 27 Avril 2026  
**Auteur**: Zenith__  

---

## 📋 Table des Matières

1. [Prérequis](#1-prérequis)
2. [Installation](#2-installation)
3. [Configuration MCP](#3-configuration-mcp)
4. [Démarrage](#4-démarrage)
5. [Utilisation](#5-utilisation)
6. [Outils MCP Disponibles](#6-outils-mcp-disponibles)
7. [Dépannage](#7-dépannage)
8. [Architecture](#8-architecture)

---

## 1. Prérequis

### Logiciels Requis

| Logiciel | Version | Lien de Téléchargement |
|----------|---------|------------------------|
| Python | 3.10+ | https://www.python.org/downloads/ |
| .NET SDK | 8.0 | https://dotnet.microsoft.com/download/dotnet/8.0 |
| Roblox | Dernière | https://www.roblox.com/download |
| Xeno Executor | v1.3.30 | (Fichiers fournis) |

### Dépendances Python

```powershell
pip install fastmcp requests psutil pyperclip
```

### Fichiers Nécessaires

```
xeno-re/
├── XenoBridge/                 # Projet C# compilé
│   ├── bin/Release/.../XenoBridge.exe
│   └── Xeno.dll               # À COPIER ICI
├── xeno_mcp_bridge_full.py   # MCP Python
└── Xeno-v1.3.30/             # Fichiers Xeno originaux
    └── Xeno.dll
```

---

## 2. Installation

### Étape 1 : Extraire l'Archive

```powershell
# Extraire xeno-bridge-package.zip dans :
C:\Users\Zenith__\Documents\windsurf\xeno-re\
```

### Étape 2 : Copier Xeno.dll

**⚠️ IMPORTANT** : Le Bridge a besoin de `Xeno.dll` dans son dossier !

```powershell
cd "C:\Users\Zenith__\Documents\windsurf\xeno-re"

# Copier Xeno.dll dans le dossier du Bridge
Copy-Item "Xeno-v1.3.30\Xeno.dll" "XenoBridge\bin\Release\net8.0-windows\win-x64\Xeno.dll" -Force
```

### Étape 3 : Vérifier l'Installation

```powershell
# Tester le Bridge seul
.\XenoBridge\bin\Release\net8.0-windows\win-x64\XenoBridge.exe
```

Vous devriez voir :
```
✅ Xeno.dll trouvée
✅ Xeno.dll initialisée
🚀 XenoBridge démarré
   Port: 3111
   Serveur HTTP démarré sur http://localhost:3111
```

**Arrêter avec Ctrl+C**

---

## 3. Configuration MCP

### Étape 1 : Sauvegarder l'Ancienne Config

```powershell
copy "%APPDATA%\Windsurf\mcp_config.json" "%APPDATA%\Windsurf\mcp_config.json.backup"
```

### Étape 2 : Appliquer la Nouvelle Config

**Option A - Automatique** :
```powershell
copy "mcp_config_updated.json" "%APPDATA%\Windsurf\mcp_config.json"
```

**Option B - Manuelle** :
Ouvrir `%APPDATA%\Windsurf\mcp_config.json` et ajouter :

```json
{
  "mcpServers": {
    "xeno-bridge": {
      "args": [
        "C:\\Users\\Zenith__\\Documents\\windsurf\\xeno-re\\xeno_mcp_bridge_full.py"
      ],
      "command": "C:\\Users\\Zenith__\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
      "disabled": false
    }
  }
}
```

### Étape 3 : Redémarrer Windsurf

1. Fermer complètement Windsurf
2. Rouvrir Windsurf
3. Le MCP "xeno-bridge" devrait apparaître dans la liste

---

## 4. Démarrage

### Méthode 1 : Via Windsurf (Recommandé)

Le MCP démarre automatiquement quand vous ouvrez Windsurf.

### Méthode 2 : Manuellement

```powershell
cd "C:\Users\Zenith__\Documents\windsurf\xeno-re"
python xeno_mcp_bridge_full.py
```

### Ce qui se Passe Automatiquement

```
1. 🚀 Démarrage du Bridge (XenoBridge.exe)
2. ⏳ Attente que le Bridge soit prêt (health check)
3. ✅ Bridge prêt (version v1.3.30)
4. 🎯 Démarrage du serveur MCP
5. 🟢 Système prêt !
```

---

## 5. Utilisation

### Workflow Typique

```
1. Démarrer Roblox
2. Attendre que le MCP se connecte
3. Utiliser 'attach_to_roblox()' si nécessaire
4. Exécuter des scripts !
```

### Test Rapide

Dans Windsurf, demandez :
```
Utilise xeno-bridge pour faire un test print
```

Ou utilisez directement :
```python
print_test()
```

---

## 6. Outils MCP Disponibles

### 🔧 Gestion du Bridge

| Outil | Description | Exemple |
|-------|-------------|---------|
| `bridge_status()` | Statut complet | Voir si tout est OK |
| `attach_to_roblox()` | Force l'attachement | Quand Roblox n'est pas détecté |
| `list_clients()` | Liste les clients | Voir PID, noms, états |
| `set_auto_attach(true)` | Active l'auto-scan | Attach automatique |

### 🎮 Exécution de Scripts

| Outil | Description | Paramètres |
|-------|-------------|------------|
| `execute_script(code, pids)` | Exécute Lua | `code="print('test')"`, `pids="auto"` |
| `execute_and_capture(code)` | Exécute + capture | `code="return game.PlaceId"` |
| `print_test()` | Test simple | Aucun |

### 📊 États des Clients

| État | Couleur | Signification |
|------|---------|---------------|
| 0 | 🔴 | Déconnecté |
| 1 | 🟡 | En attente |
| 2 | 🔵 | Attaché |
| 3 | 🟢 | **Prêt à exécuter** |

---

## 7. Dépannage

### Problème : "Xeno.dll non trouvée"

**Solution** :
```powershell
Copy-Item "Xeno-v1.3.30\Xeno.dll" "XenoBridge\bin\Release\net8.0-windows\win-x64\Xeno.dll" -Force
```

### Problème : "Bridge a crashé"

**Vérifications** :
1. Roblox est-il fermé ? → Normal, attendez qu'il soit ouvert
2. Xeno.dll est-elle copiée ? → Voir ci-dessus
3. .NET 8.0 est-il installé ? → `dotnet --version`

### Problème : "Aucun client trouvé"

**Solutions** :
1. Démarrer Roblox AVANT le MCP
2. Utiliser `attach_to_roblox()`
3. Activer l'auto-attach : `set_auto_attach(true)`

### Problème : "Port 3111 déjà utilisé"

**Solution** :
```powershell
# Trouver et tuer le processus
Get-Process | Where-Object {$_.ProcessName -like "*XenoBridge*"} | Stop-Process -Force
```

### Vérifier les Logs

**Bridge** : Affiché dans la console du Bridge  
**MCP** : Affiché dans la console Python

---

## 8. Architecture

```
┌─────────────────┐     ┌───────────────┐     ┌─────────────┐
│   Windsurf      │────▶│  MCP Python   │────▶│   Bridge    │
│  (Claude UI)    │     │(port MCP)     │     │  (port 3111)│
└─────────────────┘     └───────────────┘     └──────┬──────┘
                                                     │
                                              ┌──────▼──────┐
                                              │  Xeno.dll   │
                                              │  (injectée) │
                                              └──────┬──────┘
                                                     │
                                              ┌──────▼──────┐
                                              │   Roblox    │
                                              │  (Lua VM)   │
                                              └─────────────┘
```

### Ports Utilisés

| Port | Service | Description |
|------|---------|-------------|
| 3111 | XenoBridge | HTTP API du Bridge |
| 3110 | Xeno natif | (Non utilisé par le Bridge) |
| MCP | MCP Python | Communication avec Windsurf |

### Flux d'Exécution

```
1. User demande "execute print('hello')"
2. MCP Python reçoit la demande
3. MCP envoie POST /execute au Bridge (localhost:3111)
4. Bridge appelle Xeno.dll::Execute()
5. Xeno.dll injecte le script dans Roblox
6. Roblox exécute le Lua
7. Résultat remonte la chaîne
```

---

## 📁 Structure des Fichiers

```
xeno-bridge-package/
├── XenoBridge/
│   ├── bin/Release/net8.0-windows/win-x64/
│   │   ├── XenoBridge.exe          ← Exécutable principal
│   │   ├── XenoBridge.dll
│   │   └── Xeno.dll                ← À COPIER ICI
│   ├── Program.cs                  ← Source C#
│   ├── XenoBridge.csproj
│   └── build.bat
├── xeno_mcp_bridge_full.py         ← MCP Python
├── mcp_config_updated.json         ← Config MCP
├── test_bridge.ps1                 ← Script de test
├── GUIDE_COMPLET_XENO_BRIDGE.md    ← Ce guide
└── README_QUICKSTART.txt           ← Démarrage rapide
```

---

## 🚀 Commandes Rapides

### Démarrage Rapide (PowerShell)

```powershell
# 1. Aller dans le dossier
cd "C:\Users\Zenith__\Documents\windsurf\xeno-re"

# 2. Vérifier Xeno.dll est présente
Test-Path "XenoBridge\bin\Release\net8.0-windows\win-x64\Xeno.dll"

# 3. Lancer le MCP
python xeno_mcp_bridge_full.py

# 4. (Optionnel) Tester le Bridge seul
.\XenoBridge\bin\Release\net8.0-windows\win-x64\XenoBridge.exe
```

### Tests Rapides (dans Windsurf)

```
bridge_status()
list_clients()
print_test()
execute_script("print('Hello World')")
```

---

## 📞 Support

### En Cas de Problème

1. Vérifier ce guide (section Dépannage)
2. Vérifier les logs dans la console
3. Tester le Bridge seul : `.\XenoBridge\bin\Release\...\XenoBridge.exe`
4. Redémarrer Windsurf

### Fichiers de Log Importants

- Console du MCP Python
- Console du Bridge (XenoBridge.exe)
- Fichier `%APPDATA%\Windsurf\logs\`

---

**FIN DU GUIDE** 🎉

Bonne exploitation Roblox ! 🔥
