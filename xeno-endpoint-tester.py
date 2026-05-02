"""
Xeno Executor — HTTP Endpoint Tester
Teste les endpoints locaux sur localhost:3110

Usage:
    python xeno_endpoint_tester.py
    python xeno_endpoint_tester.py --pid 2548
    python xeno_endpoint_tester.py --host localhost --port 3110

Résultats à transmettre pour mise à jour du rapport RE.
"""

import requests
import json
import argparse
import sys
from typing import Optional

BASE_HEADERS = {
    "Origin": "https://xeno.onl",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0",
    "Accept": "*/*",
}

TIMEOUT = 5


def separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def print_result(method: str, url: str, resp: Optional[requests.Response], error: str = None):
    if error:
        print(f"  ❌ ERREUR : {error}")
        return

    status_icon = "✅" if resp.status_code == 200 else ("⚠️" if resp.status_code < 500 else "❌")
    print(f"  {status_icon} {resp.status_code} {resp.reason}")
    print(f"  Headers réponse :")
    for k, v in resp.headers.items():
        print(f"    {k}: {v}")
    if resp.text:
        print(f"  Body ({len(resp.text)} bytes) :")
        body = resp.text[:500]
        print(f"    {body}")
        if len(resp.text) > 500:
            print(f"    ... [{len(resp.text) - 500} bytes supplémentaires]")
    else:
        print(f"  Body : (vide)")


def test_get(base_url: str, path: str, extra_headers: dict = None):
    url = base_url + path
    headers = {**BASE_HEADERS, **(extra_headers or {})}
    print(f"\n  → GET {url}")
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        print_result("GET", url, resp)
        return resp
    except requests.exceptions.ConnectionError:
        print_result("GET", url, None, "Connexion refusée — serveur non démarré ou mauvais port")
    except requests.exceptions.Timeout:
        print_result("GET", url, None, f"Timeout ({TIMEOUT}s)")
    except Exception as e:
        print_result("GET", url, None, str(e))
    return None


def test_post(base_url: str, path: str, body: str, content_type: str = "text/plain",
              extra_headers: dict = None):
    url = base_url + path
    headers = {
        **BASE_HEADERS,
        "Content-Type": content_type,
        "Content-Length": str(len(body.encode())),
        **(extra_headers or {}),
    }
    print(f"\n  → POST {url}")
    print(f"     Body : {repr(body[:80])}")
    if extra_headers:
        for k, v in extra_headers.items():
            print(f"     Header : {k}: {v}")
    try:
        resp = requests.post(url, data=body.encode(), headers=headers, timeout=TIMEOUT)
        print_result("POST", url, resp)
        return resp
    except requests.exceptions.ConnectionError:
        print_result("POST", url, None, "Connexion refusée — serveur non démarré ou mauvais port")
    except requests.exceptions.Timeout:
        print_result("POST", url, None, f"Timeout ({TIMEOUT}s)")
    except Exception as e:
        print_result("POST", url, None, str(e))
    return None


def test_options(base_url: str, path: str):
    url = base_url + path
    print(f"\n  → OPTIONS {url} (CORS preflight)")
    try:
        resp = requests.options(url, headers=BASE_HEADERS, timeout=TIMEOUT)
        print_result("OPTIONS", url, resp)
        return resp
    except Exception as e:
        print_result("OPTIONS", url, None, str(e))
    return None


def main():
    parser = argparse.ArgumentParser(description="Xeno HTTP Endpoint Tester")
    parser.add_argument("--host", default="localhost", help="Hôte (défaut: localhost)")
    parser.add_argument("--port", type=int, default=3110, help="Port (défaut: 3110)")
    parser.add_argument("--pid", type=int, default=None, help="PID du client Roblox (pour /o)")
    parser.add_argument("--script", default='print("XenoTest_RE")',
                        help="Script Lua à envoyer sur /o")
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"
    pid_list = json.dumps([str(args.pid)]) if args.pid else '["0"]'

    print(f"\n🔍 Xeno Endpoint Tester — {base_url}")
    print(f"   PID cible : {args.pid or 'non spécifié (utilise 0)'}")
    print(f"   Script    : {args.script}")

    # ─── /v — Version ────────────────────────────────────────────
    separator("GET /v — Version")
    test_get(base_url, "/v")

    # ─── /g — GetClients ─────────────────────────────────────────
    separator("GET /g — GetClients")
    test_get(base_url, "/g")

    # ─── /o — Execute (confirmé HAR) ─────────────────────────────
    separator("POST /o — Execute (confirmé HAR)")
    if args.pid:
        test_post(base_url, "/o", args.script,
                  extra_headers={"Clients": pid_list})
    else:
        print("  ℹ️  Aucun PID fourni. Test avec PID=0 (devrait échouer proprement).")
        test_post(base_url, "/o", args.script,
                  extra_headers={"Clients": '["0"]'})
        print()
        print("  ℹ️  Test sans header Clients (pour voir le comportement sans header)")
        test_post(base_url, "/o", args.script)

    # ─── /a — Attach ─────────────────────────────────────────────
    separator("POST /a — Attach")
    test_post(base_url, "/a", "")
    print()
    test_get(base_url, "/a")

    # ─── /s — SetSetting ─────────────────────────────────────────
    separator("POST /s — SetSetting (setting 0 = stealth, setting 1 = RPC)")
    # Test setting 0 valeur 0 (désactiver stealth)
    test_post(base_url, "/s", "0 0")
    # Test setting 0 valeur 1 (activer stealth)
    test_post(base_url, "/s", "0 1")
    # Test setting 1 valeur 0 (désactiver RPC)
    test_post(base_url, "/s", "1 0")

    # ─── Routes alternatives ──────────────────────────────────────
    separator("Routes alternatives à tester")

    for route in ["/execute", "/clients", "/attach", "/setting", "/version",
                  "/status", "/ping", "/info", "/roblox", "/"]:
        print(f"\n  → GET {base_url}{route}")
        try:
            resp = requests.get(base_url + route, headers=BASE_HEADERS, timeout=TIMEOUT)
            icon = "✅" if resp.status_code == 200 else f"[{resp.status_code}]"
            body_preview = resp.text[:60].replace('\n', ' ') if resp.text else "(vide)"
            print(f"     {icon} {resp.status_code} | body: {body_preview!r}")
        except requests.exceptions.ConnectionError:
            print(f"     ❌ Connexion refusée")
        except Exception as e:
            print(f"     ❌ {e}")

    # ─── OPTIONS CORS preflight ───────────────────────────────────
    separator("OPTIONS /o — CORS Preflight")
    test_options(base_url, "/o")

    # ─── Résumé ───────────────────────────────────────────────────
    separator("FIN DES TESTS")
    print("""
Transmets les résultats complets pour mise à jour du rapport.
Format utile :
  - Code HTTP de chaque endpoint
  - Body de réponse si non vide
  - Erreur si connexion refusée
""")


if __name__ == "__main__":
    main()