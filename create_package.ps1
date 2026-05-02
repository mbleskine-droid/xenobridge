# Script pour créer le package XenoBridge MCP
# Lancez ce script pour générer l'archive ZIP complète

param(
    [string]$OutputPath = "XenoBridge-MCP-Package.zip"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Création du package XenoBridge MCP..." -ForegroundColor Cyan
Write-Host "=" * 60

# Vérifier que 7z ou Compress-Archive est disponible
$has7z = Get-Command "7z" -ErrorAction SilentlyContinue
$hasTar = Get-Command "tar" -ErrorAction SilentlyContinue

# Fichiers à inclure
$filesToInclude = @(
    # MCP Python
    "xeno_mcp_bridge_full.py",
    "xeno_mcp_bridge.py",
    
    # Bridge C#
    "XenoBridge/bin/Release/net8.0-windows/win-x64/XenoBridge.exe",
    "XenoBridge/bin/Release/net8.0-windows/win-x64/*.dll",
    "XenoBridge/bin/Release/net8.0-windows/win-x64/*.runtimeconfig.json",
    "XenoBridge/Program.cs",
    "XenoBridge/XenoBridge.csproj",
    "XenoBridge/build.bat",
    
    # Documentation
    "GUIDE_COMPLET_XENO_BRIDGE.md",
    "README_QUICKSTART.txt",
    "mcp_config_updated.json",
    
    # Scripts de test
    "test_bridge.ps1",
    "test_all.ps1",
    "create_package.ps1",
    
    # Xeno DLL (essentiel)
    "Xeno-v1.3.30/Xeno.dll",
    
    # Rapports et analyse
    "rapport_RE_xeno_onl_HTTP.md",
    "xeno_endpoints_rapport.md",
    "xeno-endpoint-test.txt",
    "xeno_endpoint_validator.py"
)

# Créer un dossier temporaire
$tempDir = "temp_package_$([Guid]::NewGuid().ToString().Substring(0,8))"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

Write-Host "📁 Préparation des fichiers..." -ForegroundColor Yellow

foreach ($pattern in $filesToInclude) {
    $resolved = Resolve-Path $pattern -ErrorAction SilentlyContinue
    if ($resolved) {
        foreach ($file in $resolved) {
            # Conserver la structure des dossiers
            $relativePath = $file.Path.Substring((Get-Location).Path.Length + 1)
            $destDir = Join-Path $tempDir (Split-Path $relativePath -Parent)
            
            if ($destDir -and -not (Test-Path $destDir)) {
                New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            }
            
            Copy-Item $file.Path -Destination (Join-Path $tempDir $relativePath) -Force -ErrorAction SilentlyContinue
            Write-Host "  ✅ $relativePath" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⚠️  Non trouvé: $pattern" -ForegroundColor Yellow
    }
}

# Créer un fichier README spécifique au package
$packageReadme = @"
================================================================================
XENO BRIDGE MCP - PACKAGE COMPLET
Version 1.0 - Avril 2026
================================================================================

🚀 CONTENU DU PACKAGE:
----------------------

📁 XenoBridge/                 - Bridge C# compilé (nécessite Xeno.dll)
📄 xeno_mcp_bridge_full.py      - MCP Python avec auto-start
📄 mcp_config_updated.json      - Configuration MCP pour Windsurf
📄 GUIDE_COMPLET_XENO_BRIDGE.md - Guide d'utilisation complet
📄 README_QUICKSTART.txt        - Démarrage rapide
📄 Xeno-v1.3.30/Xeno.dll       - DLL Xeno (essentiel !)

⚡ INSTALLATION RAPIDE:
-----------------------

1. Copier Xeno.dll dans le dossier du Bridge:
   Copy-Item "Xeno-v1.3.30\Xeno.dll" "XenoBridge\bin\Release\net8.0-windows\win-x64\Xeno.dll" -Force

2. Copier la config MCP:
   copy "mcp_config_updated.json" "%APPDATA%\Windsurf\mcp_config.json"

3. Installer dépendances Python:
   pip install fastmcp requests psutil pyperclip

4. Redémarrer Windsurf

🎮 UTILISATION:
---------------

Dans Windsurf, utiliser:
  - bridge_status()      : Voir le statut
  - list_clients()       : Lister les clients Roblox
  - attach_to_roblox()   : Forcer l'attachement
  - execute_script(...)  : Exécuter du Lua
  - print_test()         : Test rapide

📖 DOCUMENTATION:
-----------------
Guide complet: GUIDE_COMPLET_XENO_BRIDGE.md
Démarrage rapide: README_QUICKSTART.txt

================================================================================
"@

$packageReadme | Out-File -FilePath "$tempDir/README_PACKAGE.txt" -Encoding UTF8

# Créer le ZIP
Write-Host ""
Write-Host "📦 Création de l'archive ZIP..." -ForegroundColor Cyan

if ($has7z) {
    # Utiliser 7z si disponible (meilleur compression)
    7z a -tzip -mx5 $OutputPath "$tempDir\*" | Out-Null
} else {
    # Utiliser Compress-Archive (PowerShell natif)
    Compress-Archive -Path "$tempDir\*" -DestinationPath $OutputPath -Force
}

# Nettoyer
Remove-Item -Path $tempDir -Recurse -Force

Write-Host ""
Write-Host "✅ Package créé avec succès !" -ForegroundColor Green
Write-Host "📦 Fichier: $OutputPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "🚀 Prochaines étapes:" -ForegroundColor Yellow
Write-Host "   1. Extraire le ZIP dans: C:\Users\Zenith__\Documents\windsurf\xeno-re\" -ForegroundColor White
Write-Host "   2. Lire README_QUICKSTART.txt" -ForegroundColor White
Write-Host "   3. Suivre les instructions d'installation" -ForegroundColor White
Write-Host ""

# Afficher la taille
if (Test-Path $OutputPath) {
    $size = (Get-Item $OutputPath).Length / 1MB
    Write-Host "📊 Taille: $([math]::Round($size, 2)) Mo" -ForegroundColor Gray
}
