# XenoBridge

Bridge C# qui charge Xeno.dll et expose toutes ses fonctionnalités via HTTP local.

## 🎯 Ce que ça fait

Imite le vrai Xeno.exe mais sans interface visuelle :
- ✅ Charge **Xeno.dll** 
- ✅ Appelle `Initialize()` pour démarrer le serveur HTTP interne (port 3110)
- ✅ Expose les fonctions via HTTP sur **port 3111**

## 🚀 Endpoints disponibles

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `POST /attach` | POST | Attacher à Roblox (appelle `Attach()`) |
| `POST /execute` | POST | Exécuter script Lua sur des PIDs |
| `GET /clients` | GET | Liste des clients Roblox attachés |
| `POST /setting` | POST | Modifier paramètre (AutoAttach, DiscordRPC) |
| `GET /version` | GET | Version de Xeno.dll |
| `GET /health` | GET | Statut du bridge |

## 📦 Prérequis

1. **.NET 8.0 SDK** : [Télécharger ici](https://dotnet.microsoft.com/download/dotnet/8.0)
2. **Xeno.dll** : Placer dans le même dossier ou `Xeno-v1.3.30/Xeno.dll`

## 🔨 Compilation

```powershell
cd "C:\Users\Zenith__\Documents\windsurf\xeno-re\XenoBridge"
dotnet build -c Release
```

L'exécutable sera dans : `bin/Release/net8.0-windows/win-x64/XenoBridge.exe`

## ▶️ Exécution

```powershell
.\bin\Release\net8.0-windows\win-x64\XenoBridge.exe
```

Ou en un seul fichier portable :
```powershell
dotnet publish -c Release -r win-x64 --self-contained false
.\bin\Release\net8.0-windows\win-x64\publish\XenoBridge.exe
```

## 🧪 Test rapide

```powershell
# Vérifier que le bridge tourne
Invoke-RestMethod -Uri "http://localhost:3111/health"

# Attacher à Roblox
Invoke-RestMethod -Uri "http://localhost:3111/attach" -Method POST

# Voir les clients
Invoke-RestMethod -Uri "http://localhost:3111/clients"

# Exécuter un script
$body = @{ script = "print('Hello from Bridge')"; pids = @(1234) } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:3111/execute" -Method POST -Body $body -ContentType "application/json"
```

## 🔌 Intégration MCP

Modifier `xeno_mcp.py` pour utiliser le bridge :

```python
BASE_URL = "http://localhost:3111"  # Au lieu de 3110

@mcp.tool()
def attach_to_roblox() -> str:
    """Force l'attachement à Roblox"""
    r = requests.post(f"{BASE_URL}/attach")
    return r.json()["message"]
```

## ⚠️ Limitations

Même problème que le vrai Xeno : si Xeno.dll n'est pas injectée dans Roblox, `Attach()` ne peut pas fonctionner. Le bridge doit être lancé **depuis un processus qui a accès à Roblox**, ou Roblox doit être démarré **après** le bridge pour que l'auto-scan de Xeno fonctionne.

## 🐛 Debug

Si ça ne marche pas :
1. Vérifier que `Xeno.dll` est trouvée (message au démarrage)
2. Vérifier que `Initialize()` réussit (pas d'exception)
3. Tester avec Roblox démarré
