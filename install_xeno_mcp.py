#!/usr/bin/env python3
"""
XenoBridge MCP Installer & Launcher
Crée un dossier d'installation, ouvre l'explorateur, télécharge les prérequis,
et lance le serveur MCP automatiquement.
"""

import os
import sys
import json
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path
import time

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

APP_NAME = "XenoBridgeMCP"
XENO_DOWNLOAD_URL = "https://xeno.now/download"
GITHUB_RELEASES_URL = "https://github.com/zenith/xenobridge/releases/latest"

# Dossier d'installation dans AppData/Local
INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_NAME

# Fichiers requis pour fonctionner
REQUIRED_FILES = {
    "Xeno.dll": "DLL Xeno pour l'injection Roblox",
    "XenoBridge.exe": "Bridge C# launcher",
    "XenoBridge.dll": "Bridge C# runtime",
    "XenoBridge.runtimeconfig.json": "Bridge C# config",
}

# Fichier MCP à installer (version Claude)
MCP_SCRIPT_NAME = "xeno_mcp_bridge-claude-version.py"

# Configuration GitHub
GITHUB_REPO = "mbleskine-droid/xenobridge"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"

# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def print_header(text):
    """Affiche un header stylisé"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def print_step(step_num, text):
    """Affiche une étape"""
    print(f"[{step_num}/5] {text}")

def open_explorer(path):
    """Ouvre l'explorateur Windows à un chemin donné"""
    if os.path.isdir(path):
        subprocess.Popen(f'explorer "{path}"')
        return True
    return False

def open_browser(url):
    """Ouvre l'URL dans le navigateur par défaut"""
    import webbrowser
    webbrowser.open(url)
    print(f"🌐 Navigateur ouvert: {url}")

def download_file(url, dest_path):
    """Télécharge un fichier depuis une URL"""
    try:
        print(f"⬇️  Téléchargement: {url}")
        urllib.request.urlretrieve(url, dest_path)
        print(f"✅ Sauvegardé: {dest_path}")
        return True
    except Exception as e:
        print(f"❌ Erreur téléchargement: {e}")
        return False

def check_required_files():
    """Vérifie si tous les fichiers requis sont présents"""
    missing = []
    for filename, description in REQUIRED_FILES.items():
        filepath = INSTALL_DIR / filename
        if not filepath.exists():
            missing.append((filename, description))
    return missing

def create_mcp_config():
    """Crée le fichier de configuration MCP pour Windsurf (version Claude)"""
    config = {
        "mcpServers": {
            "xeno-bridge-claude": {
                "command": sys.executable,
                "args": [str(INSTALL_DIR / MCP_SCRIPT_NAME)],
                "disabled": False
            }
        }
    }
    return config

def install_python_dependencies():
    """Installe les dépendances Python nécessaires"""
    deps = ["fastmcp", "requests", "psutil", "pyperclip"]
    print("📦 Installation des dépendances Python...")
    for dep in deps:
        try:
            __import__(dep.replace("-", "_"))
            print(f"  ✅ {dep} déjà installé")
        except ImportError:
            print(f"  ⬇️  Installation de {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", dep])
            print(f"  ✅ {dep} installé")

# ═══════════════════════════════════════════════════════════════════════════════
# ÉTAPES D'INSTALLATION
# ═══════════════════════════════════════════════════════════════════════════════

def step1_create_directory():
    """Étape 1: Créer le dossier d'installation"""
    print_step(1, "Création du dossier d'installation")
    
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Dossier créé: {INSTALL_DIR}")
    
    # Créer sous-dossiers
    (INSTALL_DIR / "logs").mkdir(exist_ok=True)
    (INSTALL_DIR / "temp").mkdir(exist_ok=True)
    
    return True

def step2_download_from_github():
    """Étape 2: Télécharger les fichiers depuis GitHub"""
    print_step(2, "Téléchargement des fichiers depuis GitHub")
    
    files_to_download = {
        MCP_SCRIPT_NAME: f"{GITHUB_RAW_URL}/{MCP_SCRIPT_NAME}",
        "XenoBridge.exe": f"{GITHUB_RAW_URL}/XenoBridge.exe",
        "XenoBridge.dll": f"{GITHUB_RAW_URL}/XenoBridge.dll",
        "XenoBridge.runtimeconfig.json": f"{GITHUB_RAW_URL}/XenoBridge.runtimeconfig.json",
    }
    
    for filename, url in files_to_download.items():
        dest = INSTALL_DIR / filename
        
        if not dest.exists():
            print(f"  ⬇️  Téléchargement de {filename}...")
            try:
                urllib.request.urlretrieve(url, dest)
                print(f"  ✅ Téléchargé: {filename}")
            except Exception as e:
                print(f"  ❌ ERREUR: Impossible de télécharger {filename}")
                print(f"     {e}")
                # Fallback: copier localement si disponible
                source = Path(__file__).parent / filename
                if source.exists():
                    print(f"  🔄 Fallback: Copie locale...")
                    shutil.copy2(source, dest)
                    print(f"  ✅ Copié localement: {filename}")
                elif filename == "XenoBridge.exe":
                    print(f"  ⚠️  {filename} non trouvé, sera requis manuellement")
                else:
                    return False
        else:
            print(f"  ✅ {filename} déjà présent")
    
    return True

def step3_open_explorer_and_browser():
    """Étape 3: Ouvrir l'explorateur et le navigateur"""
    print_step(3, "Ouverture de l'explorateur et du navigateur")
    
    # Ouvrir l'explorateur
    print(f"📂 Ouverture de: {INSTALL_DIR}")
    open_explorer(INSTALL_DIR)
    
    # Ouvrir le navigateur
    open_browser(XENO_DOWNLOAD_URL)
    
    return True

def step4_wait_for_user_files():
    """Étape 4: Attendre que l'utilisateur mette les fichiers requis"""
    print_step(4, "Vérification des fichiers requis")
    
    missing = check_required_files()
    
    if missing:
        print("\n⚠️  Fichiers manquants:")
        for filename, description in missing:
            print(f"   - {filename}: {description}")
        
        print(f"\n📋 Instructions:")
        print(f"   1. L'explorateur est ouvert sur: {INSTALL_DIR}")
        print(f"   2. Le navigateur est ouvert sur: {XENO_DOWNLOAD_URL}")
        print(f"   3. Télécharge Xeno.dll depuis le site")
        print(f"   4. Copie Xeno.dll dans le dossier ouvert")
        print(f"\n⏳ Appuie sur ENTRÉE quand c'est fait (ou laisse vide pour continuer sans)...")
        user_input = input().strip()
        
        # Revérifier
        missing = check_required_files()
        if missing:
            print("⚠️  Fichiers toujours manquants!")
            print("   L'installation continue mais le serveur ne fonctionnera pas")
            print("   sans ces fichiers. Relance le script après les avoir ajoutés.")
            print("\n⏳ Appuie sur ENTRÉE pour continuer...")
            input()
    else:
        print("✅ Tous les fichiers requis sont présents!")
    
    return True

def step5_install_and_configure():
    """Étape 5: Installation finale et configuration MCP"""
    print_step(5, "Installation finale et configuration MCP")
    
    # Installer dépendances Python
    install_python_dependencies()
    
    # Créer la config MCP
    config = create_mcp_config()
    config_path = INSTALL_DIR / "mcp_config.json"
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    
    print(f"\n📝 Config MCP créée: {config_path}")
    
    # Afficher les chemins pour config Windsurf
    print("\n" + "="*70)
    print("  CONFIGURATION WINDSURF")
    print("="*70)
    print(f"\nCopie cette configuration dans:")
    print(f"  %APPDATA%\\Windsurf\\mcp_config.json")
    print(f"\nOu exécute:")
    print(f"  copy \"{config_path}\" \"%APPDATA%\\Windsurf\\mcp_config.json\"")
    print("\n" + "-"*70)
    print(json.dumps(config, indent=2))
    print("-"*70)
    
    return True

# ═══════════════════════════════════════════════════════════════════════════════
# MODE SERVEUR (quand tout est installé)
# ═══════════════════════════════════════════════════════════════════════════════

def run_server():
    """Lance le serveur MCP Claude en arrière-plan"""
    print_header("🚀 LANCEMENT DU SERVEUR MCP (VERSION CLAUDE)")
    
    # Vérifier que tout est là
    missing = check_required_files()
    if missing:
        print("❌ Fichiers manquants, impossible de lancer:")
        for f, d in missing:
            print(f"   - {f}")
        print("\nRelance le script pour l'installation.")
        return False
    
    # Vérifier XenoBridge.exe
    bridge_exe = INSTALL_DIR / "XenoBridge.exe"
    if not bridge_exe.exists():
        # Chercher dans les sous-dossiers
        possible_paths = [
            INSTALL_DIR / "XenoBridge" / "bin" / "Release" / "net8.0-windows" / "win-x64" / "XenoBridge.exe",
            INSTALL_DIR / "XenoBridge.exe",
        ]
        for p in possible_paths:
            if p.exists():
                bridge_exe = p
                break
    
    if not bridge_exe.exists():
        print("⚠️  XenoBridge.exe non trouvé!")
        print("   Le MCP essaiera de le trouver automatiquement.")
    else:
        print(f"✅ Bridge trouvé: {bridge_exe}")
    
    # Lancer le serveur MCP (version Claude)
    mcp_script = INSTALL_DIR / MCP_SCRIPT_NAME
    if not mcp_script.exists():
        print(f"❌ Script MCP non trouvé: {mcp_script}")
        return False
    
    print(f"\n🎯 Lancement du serveur MCP...")
    print(f"   Script: {mcp_script}")
    print(f"   Logs: {INSTALL_DIR / 'logs'}")
    
    # Créer le fichier de lancement en arrière-plan
    vbs_script = INSTALL_DIR / "temp" / "launch_mcp.vbs"
    with open(vbs_script, "w") as f:
        f.write(f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c \\"{sys.executable}\\" \\"{mcp_script}\\" > \\"{INSTALL_DIR / 'logs' / 'mcp.log'}\\" 2>&1", 0, False
Set WshShell = Nothing''')
    
    # Lancer
    subprocess.Popen(["wscript", str(vbs_script)], shell=True)
    
    print(f"\n✅ Serveur MCP lancé en arrière-plan!")
    print(f"   Logs: {INSTALL_DIR / 'logs' / 'mcp.log'}")
    print(f"\n📝 Pour voir les logs en temps réel:")
    print(f"   Get-Content '{INSTALL_DIR / 'logs' / 'mcp.log'}' -Wait")
    
    # Ouvrir Windsurf si installé
    windsurf_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Windsurf" / "Windsurf.exe"
    if windsurf_path.exists():
        print(f"\n🚀 Lancement de Windsurf...")
        subprocess.Popen([str(windsurf_path)])
    
    return True

# ═══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Fonction principale"""
    print_header("🎮 XenoBridge MCP CLAUDE - Installateur & Lanceur")
    
    # Vérifier si c'est une réinstallation ou un premier lancement
    if INSTALL_DIR.exists():
        missing = check_required_files()
        if not missing:
            # Tout est installé, lancer directement
            print("✅ Installation détectée et complète!")
            print("🚀 Lancement du serveur...\n")
            return run_server()
    
    # Mode installation
    print("📦 Mode: INSTALLATION\n")
    
    success = True
    success = step1_create_directory() and success
    success = step2_download_from_github() and success
    success = step3_open_explorer_and_browser() and success
    success = step4_wait_for_user_files() and success
    success = step5_install_and_configure() and success
    
    if success:
        print_header("✅ INSTALLATION TERMINÉE")
        print("\n🎉 XenoBridge MCP est prêt!")
        print(f"\n📁 Dossier d'installation: {INSTALL_DIR}")
        print("\n⚡ Prochaines étapes:")
        print("   1. Configure Windsurf avec la config fournie ci-dessus")
        print("   2. Relance ce script pour démarrer le serveur")
        print("\n💡 Relance simplement ce script quand tu veux lancer le serveur!")
    else:
        print_header("❌ INSTALLATION ÉCHOUÉE")
        print("Vérifie les erreurs ci-dessus et réessaie.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
