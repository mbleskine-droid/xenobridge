"""
Xeno MCP utilisant XenoBridge (C#) au lieu du serveur HTTP natif (port 3110)
Ce MCP expose TOUTES les fonctionnalités : Attach, Execute, Clients, Settings
"""

import json
import requests
import psutil
import time
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

# Configuration
BRIDGE_URL = "http://localhost:3111"
NATIVE_URL = "http://localhost:3110"
TIMEOUT = 10

# Créer l'instance MCP
mcp = FastMCP("xeno-bridge")

class XenoBridgeClient:
    """Client pour communiquer avec XenoBridge"""
    
    def __init__(self, base_url: str = BRIDGE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
    
    def health_check(self) -> Dict[str, Any]:
        """Vérifier que le bridge est actif"""
        try:
            resp = self.session.get(f"{self.base_url}/health", timeout=TIMEOUT)
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def attach(self) -> bool:
        """Déclencher l'attachement à Roblox"""
        try:
            resp = self.session.post(f"{self.base_url}/attach", timeout=TIMEOUT)
            data = resp.json()
            return data.get("success", False)
        except Exception as e:
            print(f"[ERROR] Attach failed: {e}")
            return False
    
    def get_clients(self) -> List[Dict[str, Any]]:
        """Récupérer la liste des clients"""
        try:
            resp = self.session.get(f"{self.base_url}/clients", timeout=TIMEOUT)
            data = resp.json()
            return data.get("clients", [])
        except Exception as e:
            print(f"[ERROR] GetClients failed: {e}")
            return []
    
    def execute(self, script: str, pids: List[int]) -> bool:
        """Exécuter un script sur des PIDs"""
        try:
            payload = {
                "script": script,
                "pids": pids
            }
            resp = self.session.post(
                f"{self.base_url}/execute",
                json=payload,
                timeout=TIMEOUT
            )
            data = resp.json()
            return data.get("success", False)
        except Exception as e:
            print(f"[ERROR] Execute failed: {e}")
            return False
    
    def set_setting(self, setting: str, value: bool) -> bool:
        """Modifier un paramètre (AutoAttach, DiscordRPC)"""
        try:
            payload = {
                "setting": setting,
                "value": value
            }
            resp = self.session.post(
                f"{self.base_url}/setting",
                json=payload,
                timeout=TIMEOUT
            )
            data = resp.json()
            return data.get("success", False)
        except Exception as e:
            print(f"[ERROR] SetSetting failed: {e}")
            return False

# Instance globale du client
xeno = XenoBridgeClient()

# =============================================================================
# OUTILS MCP
# =============================================================================

@mcp.tool()
def bridge_status() -> str:
    """
    Vérifier le statut de XenoBridge
    """
    health = xeno.health_check()
    
    if health.get("status") == "ok":
        return f"""✅ XenoBridge actif
Version: {health.get('version', 'unknown')}
Initialisé: {health.get('initialized', False)}"""
    else:
        return f"❌ XenoBridge inaccessible\nErreur: {health.get('error', 'unknown')}"

@mcp.tool()
def attach_to_roblox() -> str:
    """
    Force l'attachement à Roblox via XenoBridge
    """
    # D'abord chercher Roblox
    roblox_pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] and 'Roblox' in proc.info['name']:
            roblox_pids.append(proc.info['pid'])
    
    if not roblox_pids:
        return "❌ Aucun processus Roblox trouvé. Démarrez Roblox d'abord."
    
    # Déclencher l'attachement
    success = xeno.attach()
    
    if success:
        return f"✅ Attachement déclenché\nRoblox PIDs trouvés: {roblox_pids}\nAttendez 5-10 secondes puis vérifiez les clients."
    else:
        return "❌ Échec de l'attachement"

@mcp.tool()
def list_clients_bridge() -> str:
    """
    Liste les clients Roblox via XenoBridge (avec Attach/Execute/Settings)
    """
    clients = xeno.get_clients()
    
    if not clients:
        return "⚠️ Aucun client connecté\n\nConseils:\n1. Démarrez Roblox\n2. Utilisez 'attach_to_roblox()'\n3. Attendez 10 secondes\n4. Réessayez"
    
    result = [f"🎮 Clients connectés: {len(clients)}"]
    result.append("")
    
    for client in clients:
        state_str = {
            0: "🔴 Déconnecté",
            1: "🟡 En attente",
            2: "🔵 Attaché",
            3: "🟢 Prêt"
        }.get(client.get('state', -1), "⚪ Inconnu")
        
        result.append(f"PID: {client.get('pid')}")
        result.append(f"  Nom: {client.get('name', 'N/A')}")
        result.append(f"  Version: {client.get('version', 'N/A')}")
        result.append(f"  État: {state_str}")
        result.append("")
    
    return "\n".join(result)

@mcp.tool()
def execute_on_clients(script: str, pids: str = "auto") -> str:
    """
    Exécute un script Lua sur les clients spécifiés
    
    Args:
        script: Code Lua à exécuter
        pids: PIDs des clients (ex: "1234,5678" ou "auto" pour tous les clients prêts)
    """
    # Récupérer les clients
    clients = xeno.get_clients()
    
    if not clients:
        return "❌ Aucun client disponible. Attachez d'abord avec 'attach_to_roblox()'"
    
    # Déterminer les PIDs cibles
    target_pids = []
    
    if pids == "auto":
        # Prendre tous les clients "Prêt" (state=3)
        for client in clients:
            if client.get('state') == 3:
                target_pids.append(client.get('pid'))
        
        if not target_pids:
            return "❌ Aucun client prêt (state=3). Attendez que l'attachement soit complet."
    else:
        # Parser les PIDs fournis
        try:
            target_pids = [int(p.strip()) for p in pids.split(",")]
        except ValueError:
            return "❌ Format de PIDs invalide. Utilisez: '1234,5678' ou 'auto'"
    
    # Exécuter
    success = xeno.execute(script, target_pids)
    
    if success:
        return f"✅ Script exécuté sur {len(target_pids)} client(s)\nPIDs: {target_pids}\n\nScript:\n{script[:200]}..."
    else:
        return f"❌ Échec de l'exécution sur PIDs: {target_pids}"

@mcp.tool()
def set_auto_attach(enabled: bool) -> str:
    """
    Active/désactive l'AutoAttach (scan automatique des processus Roblox)
    
    Args:
        enabled: true pour activer, false pour désactiver
    """
    success = xeno.set_setting("AutoAttach", enabled)
    
    if success:
        status = "activé" if enabled else "désactivé"
        return f"✅ AutoAttach {status}\n\nXeno scannera automatiquement les processus Roblox toutes les 25 secondes."
    else:
        return "❌ Échec de la modification du paramètre"

@mcp.tool()
def bridge_diagnostics() -> str:
    """
    Diagnostic complet du bridge et de l'environnement Roblox
    """
    lines = ["🔍 DIAGNOSTIC XENOBIRDGE", "=" * 40]
    
    # 1. Statut bridge
    health = xeno.health_check()
    lines.append(f"\n📊 Bridge: {health.get('status', 'unknown')}")
    lines.append(f"   Version: {health.get('version', 'N/A')}")
    lines.append(f"   Initialisé: {health.get('initialized', False)}")
    
    # 2. Processus Roblox
    lines.append("\n🎮 Processus Roblox:")
    roblox_found = False
    for proc in psutil.process_iter(['pid', 'name', 'status']):
        if proc.info['name'] and 'Roblox' in proc.info['name']:
            lines.append(f"   PID {proc.info['pid']}: {proc.info['name']} ({proc.info['status']})")
            roblox_found = True
    
    if not roblox_found:
        lines.append("   ⚠️ Aucun processus Roblox trouvé")
    
    # 3. Clients Xeno
    lines.append("\n🔗 Clients Xeno:")
    clients = xeno.get_clients()
    if clients:
        for c in clients:
            state = {0: "🔴", 1: "🟡", 2: "🔵", 3: "🟢"}.get(c.get('state', -1), "⚪")
            lines.append(f"   {state} PID {c.get('pid')}: {c.get('name')} (v{c.get('version')})")
    else:
        lines.append("   ⚠️ Aucun client connecté")
    
    # 4. Serveurs HTTP
    lines.append("\n🌐 Serveurs HTTP:")
    try:
        r = requests.get(f"{BRIDGE_URL}/health", timeout=2)
        lines.append(f"   ✅ Bridge (3111): OK")
    except:
        lines.append(f"   ❌ Bridge (3111): Inaccessible")
    
    try:
        r = requests.get(f"{NATIVE_URL}/", timeout=2)
        lines.append(f"   ✅ Xeno natif (3110): OK")
    except:
        lines.append(f"   ⚪ Xeno natif (3110): {r.status_code if 'r' in locals() else 'N/A'}")
    
    lines.append("\n" + "=" * 40)
    
    return "\n".join(lines)

# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    print("🚀 Xeno MCP (Bridge Mode)")
    print(f"   Bridge URL: {BRIDGE_URL}")
    print(f"   Native URL: {NATIVE_URL}")
    print()
    
    # Test de connexion
    health = xeno.health_check()
    if health.get("status") == "ok":
        print(f"✅ Connecté à XenoBridge v{health.get('version')}")
    else:
        print("⚠️ XenoBridge inaccessible")
        print("   Lancez: .\\XenoBridge\\bin\\Release\\net8.0-windows\\win-x64\\XenoBridge.exe")
    
    print()
    print("Démarrage du serveur MCP...")
    mcp.run()
