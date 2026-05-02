"""
xeno_endpoint_validator.py — Validation complète des endpoints Xeno
Basé sur l'analyse HAR et Ghidra MCP

Usage:
    python xeno_endpoint_validator.py
    python xeno_endpoint_validator.py --full
"""

import requests
import json
import argparse
import sys
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

class EndpointStatus(Enum):
    CONFIRMED = "confirmed"      # ✅ Testé et fonctionnel
    PROBABLE = "probable"        # ⚠️ Référencé dans Ghidra mais non confirmé
    UNLIKELY = "unlikely"        # ❌ 404 ou non disponible
    UNKNOWN = "unknown"          # ❓ Pas encore testé

@dataclass
class EndpointResult:
    route: str
    method: str
    expected_from_ghidra: bool
    status_code: Optional[int] = None
    response_body: str = ""
    headers: Dict[str, str] = None
    status: EndpointStatus = EndpointStatus.UNKNOWN
    notes: str = ""
    
    def to_dict(self):
        return {
            "route": self.route,
            "method": self.method,
            "expected_from_ghidra": self.expected_from_ghidra,
            "status_code": self.status_code,
            "response_body": self.response_body[:200] if self.response_body else "",
            "headers": self.headers or {},
            "status": self.status.value,
            "notes": self.notes
        }


class XenoValidator:
    """Validateur d'endpoints Xeno basé sur l'analyse RE."""
    
    BASE_URL = "http://localhost:3110"
    TIMEOUT = 5
    
    # Headers de base basés sur le HAR
    BASE_HEADERS = {
        "Origin": "https://xeno.onl",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0",
        "Accept": "*/*",
    }
    
    def __init__(self):
        self.results: List[EndpointResult] = []
        self.server_info: Dict[str, Any] = {}
        
    def _request(self, method: str, path: str, headers: Optional[Dict] = None, 
                 body: Optional[str] = None) -> tuple:
        """Effectue une requête HTTP et retourne (status_code, body, headers, error)."""
        url = f"{self.BASE_URL}{path}"
        req_headers = {**self.BASE_HEADERS, **(headers or {})}
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=req_headers, timeout=self.TIMEOUT)
            elif method == "POST":
                resp = requests.post(url, headers=req_headers, data=body or "", timeout=self.TIMEOUT)
            elif method == "OPTIONS":
                resp = requests.options(url, headers=req_headers, timeout=self.TIMEOUT)
            elif method == "PUT":
                resp = requests.put(url, headers=req_headers, data=body or "", timeout=self.TIMEOUT)
            elif method == "DELETE":
                resp = requests.delete(url, headers=req_headers, timeout=self.TIMEOUT)
            else:
                return None, "", {}, f"Méthode non supportée: {method}"
            
            return resp.status_code, resp.text, dict(resp.headers), None
            
        except requests.ConnectionError:
            return None, "", {}, "Connexion refusée - serveur non démarré"
        except requests.Timeout:
            return None, "", {}, f"Timeout ({self.TIMEOUT}s)"
        except Exception as e:
            return None, "", {}, str(e)
    
    def _add_result(self, route: str, method: str, expected_ghidra: bool,
                    status_code, body: str, headers: Dict, error: Optional[str],
                    notes: str = ""):
        """Ajoute un résultat à la liste."""
        if error:
            status = EndpointStatus.UNLIKELY
            notes = f"{notes} | Erreur: {error}" if notes else f"Erreur: {error}"
        elif status_code == 200:
            status = EndpointStatus.CONFIRMED
        elif status_code == 404:
            status = EndpointStatus.UNLIKELY
        else:
            status = EndpointStatus.PROBABLE if expected_ghidra else EndpointStatus.UNKNOWN
            
        self.results.append(EndpointResult(
            route=route,
            method=method,
            expected_from_ghidra=expected_ghidra,
            status_code=status_code,
            response_body=body,
            headers=headers,
            status=status,
            notes=notes
        ))
    
    def test_root(self):
        """Teste GET / (page d'accueil)."""
        print("\n[TEST] GET / (Root)")
        code, body, headers, error = self._request("GET", "/")
        self._add_result("/", "GET", False, code, body, headers, error, 
                        "Page d'accueil du serveur")
        
        if code == 200:
            print(f"  ✅ {code} | {body[:80]}")
            self.server_info["running"] = True
        else:
            print(f"  ❌ {code or 'ERR'} | {error or body[:50]}")
            self.server_info["running"] = False
    
    def test_execute(self):
        """Teste POST /o (Execute) - CONFIRMÉ par HAR."""
        print("\n[TEST] POST /o (Execute) - CONFIRMÉ HAR")
        
        # Test 1: Sans header Clients (doit échouer avec 400)
        code1, body1, hdrs1, err1 = self._request(
            "POST", "/o", 
            headers={"Content-Type": "text/plain"},
            body='print("Test")'
        )
        self._add_result("/o", "POST", True, code1, body1, hdrs1, err1,
                        "Test sans header Clients")
        
        if code1 == 400:
            print(f"  ✅ Sans Clients header → {code1} (attendu: 400)")
        else:
            print(f"  ⚠️ Sans Clients header → {code1} (attendu: 400)")
        
        # Test 2: Avec header Clients invalide (PID 0)
        code2, body2, hdrs2, err2 = self._request(
            "POST", "/o",
            headers={
                "Content-Type": "text/plain",
                "Clients": '["0"]'
            },
            body='print("Test")'
        )
        self._add_result("/o", "POST (avec Clients)", True, code2, body2, hdrs2, err2,
                        "Test avec header Clients=[\"0\"]")
        
        if code2 == 200:
            print(f"  ✅ Avec Clients header → {code2} (serveur accepte la requête)")
        else:
            print(f"  ⚠️ Avec Clients header → {code2}")
        
        # Test 3: OPTIONS /o (CORS preflight) - Détecté comme source de clients
        print("\n[TEST] OPTIONS /o (CORS Preflight)")
        code3, body3, hdrs3, err3 = self._request("OPTIONS", "/o")
        self._add_result("/o", "OPTIONS", True, code3, body3, hdrs3, err3,
                        "CORS preflight - peut contenir liste clients")
        
        if code3 == 200:
            print(f"  ✅ OPTIONS → {code3}")
            if body3 and body3.strip().startswith("["):
                try:
                    clients = json.loads(body3)
                    print(f"  📊 Clients détectés: {len(clients)}")
                    self.server_info["clients"] = clients
                except:
                    print(f"  📄 Body: {body3[:100]}")
            else:
                print(f"  📄 Body: {body3[:100] if body3 else '(vide)'}")
        else:
            print(f"  ❌ OPTIONS → {code3 or 'ERR'}")
    
    def test_getclients(self):
        """Teste GET /g (GetClients) - Probable selon Ghidra."""
        print("\n[TEST] GET /g (GetClients) - Probable Ghidra")
        code, body, headers, error = self._request("GET", "/g")
        self._add_result("/g", "GET", True, code, body, headers, error,
                        "Export GetClients à 0x180167de0")
        
        if code == 200:
            print(f"  ✅ {code} | GetClients fonctionne!")
            try:
                clients = json.loads(body)
                print(f"  📊 {len(clients)} client(s)")
            except:
                print(f"  📄 {body[:100]}")
        elif code == 404:
            print(f"  ❌ {code} | GetClients non implémenté ou route différente")
        else:
            print(f"  ⚠️ {code} | {body[:50] if body else 'vide'}")
    
    def test_version(self):
        """Teste GET /v (Version) - Possible selon Ghidra."""
        print("\n[TEST] GET /v (Version) - Possible Ghidra")
        code, body, headers, error = self._request("GET", "/v")
        self._add_result("/v", "GET", True, code, body, headers, error,
                        "Export Version à 0x180167ba0")
        
        if code == 200 and body:
            print(f"  ✅ {code} | Version: {body.strip()}")
            self.server_info["version"] = body.strip()
        elif code == 404:
            print(f"  ❌ {code} | Version non exposée via HTTP")
        else:
            print(f"  ⚠️ {code} | {body[:50] if body else 'vide'}")
    
    def test_attach(self):
        """Teste POST /a (Attach) - Probable selon Ghidra."""
        print("\n[TEST] POST /a (Attach) - Probable Ghidra")
        code, body, headers, error = self._request("POST", "/a", body="")
        self._add_result("/a", "POST", True, code, body, headers, error,
                        "Export Attach à 0x180167b90")
        
        if code == 200:
            print(f"  ✅ {code} | Attach accepté")
        elif code == 404:
            print(f"  ❌ {code} | Attach non exposé ou méthode différente")
        else:
            print(f"  ⚠️ {code} | {body[:50] if body else 'vide'}")
        
        # Test aussi GET /a
        code2, body2, headers2, error2 = self._request("GET", "/a")
        self._add_result("/a", "GET", False, code2, body2, headers2, error2,
                        "Test GET (non documenté)")
    
    def test_setsetting(self):
        """Teste POST /s (SetSetting) - Probable selon Ghidra."""
        print("\n[TEST] POST /s (SetSetting) - Probable Ghidra")
        
        # Test setting 0 (stealth) = 0
        code1, body1, hdrs1, err1 = self._request(
            "POST", "/s",
            headers={"Content-Type": "text/plain"},
            body="0 0"
        )
        self._add_result("/s", "POST (stealth off)", True, code1, body1, hdrs1, err1,
                        "Export SetSetting à 0x180168110 | Param: 0 0")
        
        # Test setting 0 (stealth) = 1
        code2, body2, hdrs2, err2 = self._request(
            "POST", "/s",
            headers={"Content-Type": "text/plain"},
            body="0 1"
        )
        self._add_result("/s", "POST (stealth on)", True, code2, body2, hdrs2, err2,
                        "Param: 0 1")
        
        # Test setting 1 (RPC) = 0
        code3, body3, hdrs3, err3 = self._request(
            "POST", "/s",
            headers={"Content-Type": "text/plain"},
            body="1 0"
        )
        self._add_result("/s", "POST (rpc off)", True, code3, body3, hdrs3, err3,
                        "Param: 1 0")
        
        if code1 == 200 or code2 == 200 or code3 == 200:
            print(f"  ✅ SetSetting fonctionne (codes: {code1}, {code2}, {code3})")
        elif code1 == 404:
            print(f"  ❌ 404 | SetSetting non exposé via HTTP")
        else:
            print(f"  ⚠️ Codes: {code1}, {code2}, {code3}")
    
    def test_alternative_routes(self):
        """Teste les routes alternatives (nommées complètes)."""
        print("\n[TEST] Routes alternatives (nommées)")
        
        alternatives = [
            ("/execute", ["GET", "POST"]),
            ("/clients", ["GET"]),
            ("/attach", ["GET", "POST"]),
            ("/setting", ["GET", "POST"]),
            ("/version", ["GET"]),
            ("/status", ["GET"]),
            ("/ping", ["GET"]),
            ("/info", ["GET"]),
        ]
        
        for route, methods in alternatives:
            for method in methods:
                code, body, headers, error = self._request(method, route)
                self._add_result(route, method, False, code, body, headers, error,
                                "Route alternative testée")
                
                status = "✅" if code == 200 else ("❌" if code == 404 else "⚠️")
                print(f"  {status} {method} {route} → {code or 'ERR'}")
    
    def test_cors_headers(self):
        """Analyse les headers CORS."""
        print("\n[TEST] Analyse CORS Headers")
        
        # Test CORS preflight sur plusieurs endpoints
        endpoints = ["/o", "/", "/g", "/v"]
        
        for ep in endpoints:
            code, body, headers, error = self._request("OPTIONS", ep)
            
            cors_headers = {k: v for k, v in headers.items() 
                          if "Access-Control" in k or "CORS" in k}
            
            if cors_headers:
                print(f"  📋 {ep} OPTIONS:")
                for k, v in cors_headers.items():
                    print(f"      {k}: {v}")
    
    def test_with_real_pid(self, pid: Optional[int] = None):
        """Teste l'exécution avec un vrai PID si disponible."""
        print("\n[TEST] Exécution avec PID réel")
        
        # Récupère les clients via OPTIONS
        code, body, headers, error = self._request("OPTIONS", "/o")
        
        if code == 200 and body:
            try:
                clients = json.loads(body)
                if clients and len(clients) > 0:
                    first_client = clients[0]
                    pid = first_client[0] if isinstance(first_client, list) else None
                    username = first_client[1] if isinstance(first_client, list) and len(first_client) > 1 else "?"
                    
                    if pid:
                        print(f"  📊 Client trouvé: PID {pid} ({username})")
                        
                        # Test exécution
                        code2, body2, hdrs2, err2 = self._request(
                            "POST", "/o",
                            headers={
                                "Content-Type": "text/plain",
                                "Clients": json.dumps([str(pid)])
                            },
                            body='print("XenoValidator_Test")'
                        )
                        
                        if code2 == 200:
                            print(f"  ✅ Exécution réussie sur PID {pid}")
                        else:
                            print(f"  ❌ Exécution échouée: {code2}")
                    else:
                        print(f"  ⚠️ Pas de PID valide trouvé")
                else:
                    print(f"  ⚠️ Aucun client connecté")
            except json.JSONDecodeError:
                print(f"  ⚠️ Réponse non-JSON: {body[:100]}")
        else:
            print(f"  ❌ Impossible de récupérer les clients: {code or error}")
    
    def generate_report(self) -> str:
        """Génère un rapport complet."""
        lines = []
        lines.append("=" * 70)
        lines.append("RAPPORT DE VALIDATION XENO ENDPOINTS")
        lines.append("=" * 70)
        lines.append("")
        
        # Résumé
        confirmed = [r for r in self.results if r.status == EndpointStatus.CONFIRMED]
        probable = [r for r in self.results if r.status == EndpointStatus.PROBABLE]
        unlikely = [r for r in self.results if r.status == EndpointStatus.UNLIKELY]
        
        lines.append(f"✅ Confirmés:     {len(confirmed)}")
        lines.append(f"⚠️  Probables:     {len(probable)}")
        lines.append(f"❌ Non disponibles: {len(unlikely)}")
        lines.append("")
        
        # Détails par catégorie
        if confirmed:
            lines.append("-" * 70)
            lines.append("ENDPOINTS CONFIRMÉS (✅)")
            lines.append("-" * 70)
            for r in confirmed:
                lines.append(f"\n{r.method} {r.route}")
                lines.append(f"  Status: {r.status_code}")
                if r.response_body:
                    lines.append(f"  Body: {r.response_body[:100]}")
                if r.notes:
                    lines.append(f"  Notes: {r.notes}")
        
        if probable:
            lines.append("")
            lines.append("-" * 70)
            lines.append("ENDPOINTS PROBABLES (⚠️)")
            lines.append("-" * 70)
            for r in probable:
                lines.append(f"\n{r.method} {r.route}")
                lines.append(f"  Status: {r.status_code}")
                if r.notes:
                    lines.append(f"  Notes: {r.notes}")
        
        if unlikely:
            lines.append("")
            lines.append("-" * 70)
            lines.append("ENDPOINTS NON DISPONIBLES (❌)")
            lines.append("-" * 70)
            for r in unlikely:
                lines.append(f"\n{r.method} {r.route}")
                lines.append(f"  Status: {r.status_code or 'ERR'}")
                if r.notes:
                    lines.append(f"  Notes: {r.notes}")
        
        # Infos serveur
        lines.append("")
        lines.append("-" * 70)
        lines.append("INFORMATIONS SERVEUR")
        lines.append("-" * 70)
        for k, v in self.server_info.items():
            if k == "clients":
                lines.append(f"  {k}: {len(v)} client(s)")
            else:
                lines.append(f"  {k}: {v}")
        
        lines.append("")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def save_json_report(self, filename: str = "xeno_validation_report.json"):
        """Sauvegarde le rapport en JSON."""
        report = {
            "server_info": self.server_info,
            "results": [asdict(r) for r in self.results],
            "summary": {
                "confirmed": len([r for r in self.results if r.status == EndpointStatus.CONFIRMED]),
                "probable": len([r for r in self.results if r.status == EndpointStatus.PROBABLE]),
                "unlikely": len([r for r in self.results if r.status == EndpointStatus.UNLIKELY]),
                "unknown": len([r for r in self.results if r.status == EndpointStatus.UNKNOWN]),
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Rapport JSON sauvegardé: {filename}")
    
    def run_all_tests(self, full: bool = False):
        """Exécute tous les tests."""
        print("=" * 70)
        print("VALIDATION DES ENDPOINTS XENO")
        print("Basé sur l'analyse HAR et Ghidra MCP")
        print("=" * 70)
        
        self.test_root()
        
        if not self.server_info.get("running"):
            print("\n❌ Le serveur Xeno ne semble pas démarré. Arrêt des tests.")
            return
        
        self.test_execute()
        self.test_getclients()
        self.test_version()
        self.test_attach()
        self.test_setsetting()
        self.test_cors_headers()
        self.test_with_real_pid()
        
        if full:
            self.test_alternative_routes()
        
        # Génère et affiche le rapport
        report = self.generate_report()
        print(report)
        
        # Sauvegarde
        self.save_json_report()


def main():
    parser = argparse.ArgumentParser(description="Validateur d'endpoints Xeno")
    parser.add_argument("--full", action="store_true", 
                       help="Teste aussi les routes alternatives")
    parser.add_argument("--json-only", action="store_true",
                       help="N'affiche que le JSON de sortie")
    args = parser.parse_args()
    
    validator = XenoValidator()
    validator.run_all_tests(full=args.full)


if __name__ == "__main__":
    main()
