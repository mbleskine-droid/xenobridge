================================================================================
  XENO BRIDGE MCP - DÉMARRAGE RAPIDE
================================================================================

PRÉREQUIS:
----------
1. Python 3.10+ installé
2. .NET 8.0 SDK installé
3. Roblox installé
4. Xeno.dll présente (fournie dans Xeno-v1.3.30/)

INSTALLATION RAPIDE:
--------------------
1. Extraire cette archive dans:
   C:\Users\Zenith__\Documents\windsurf\xeno-re\

2. Copier Xeno.dll (IMPORTANT !):
   cd "C:\Users\Zenith__\Documents\windsurf\xeno-re"
   Copy-Item "Xeno-v1.3.30\Xeno.dll" "XenoBridge\bin\Release\net8.0-windows\win-x64\Xeno.dll" -Force

3. Installer les dépendances Python:
   pip install fastmcp requests psutil pyperclip

4. Configurer MCP dans Windsurf:
   copy "mcp_config_updated.json" "%APPDATA%\Windsurf\mcp_config.json"

5. Redémarrer Windsurf

TEST RAPIDE:
------------
Dans Windsurf, demande:
   "bridge_status()"
   "list_clients()"
   "print_test()"

Ou lancer manuellement:
   python xeno_mcp_bridge_full.py

FICHIERS:
---------
- xeno_mcp_bridge_full.py    : MCP Python principal
- XenoBridge/bin/.../XenoBridge.exe : Bridge C#
- mcp_config_updated.json    : Config MCP
- GUIDE_COMPLET_XENO_BRIDGE.md : Guide complet
- test_bridge.ps1            : Script de test PowerShell

COMMANDES UTILES:
-----------------
# Tester le Bridge seul:
.\XenoBridge\bin\Release\net8.0-windows\win-x64\XenoBridge.exe

# Lister les clients:
Invoke-RestMethod -Uri "http://localhost:3111/clients"

# Exécuter un script:
Invoke-RestMethod -Uri "http://localhost:3111/execute" -Method POST `
    -Body '{"script": "print(\"test\")"}' -ContentType "application/json"

DÉPANNAGE:
----------
- "Xeno.dll non trouvée" → Copier Xeno.dll dans le dossier du Bridge
- "Port déjà utilisé" → Stopper les instances précédentes
- "Aucun client" → Démarrer Roblox puis attach_to_roblox()

LIENS:
------
Guide complet: GUIDE_COMPLET_XENO_BRIDGE.md
Config MCP: %APPDATA%\Windsurf\mcp_config.json

================================================================================
  Bonne exploitation ! 🎮
================================================================================
