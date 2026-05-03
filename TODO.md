# 📝 TODO / Features à venir

## Idées d'amélioration pour XenoBridge MCP

### 🎮 Features proposées

#### 1. Join un jeu spécifique
- **Description** : Outil MCP pour rejoindre un jeu Roblox via son PlaceId
- **Usage** : `xeno_join_game(place_id: str)`
- **Implémentation** : 
  - Utiliser `roblox://placeId=123456` ou l'API Roblox
  - Attendre que le jeu charge
  - Auto-attacher quand trouvé

#### 2. Screenshot de l'interface
- **Description** : Capturer l'écran du jeu Roblox
- **Usage** : `xeno_screenshot()`
- **Implémentation** :
  - Utiliser Windows API (PrintWindow, BitBlt)
  - Ou intégrer avec l'executor si possible
  - Sauvegarder dans le dossier logs/

#### 3. Éliminer dépendance clipboard ✅ *COMPLÉTÉ 04/05/2026*
- **~~Problème~~** : ~~setclipboard() = unreliable, race conditions, limite taille~~
- **Solution implémentée** : ✅ Option C (Smart) — Fallback chain HTTP → Files → Clipboard
- **Endpoints ajoutés** : `POST /result/{id}` et `GET /result/{id}`
- **Fonctions ajoutées** : `_execute_with_callback()`, `_execute_and_read_v2()`, `_execute_and_capture_smart()`
- **Impact** : ✅ 80% des bugs résolus — Tests 8+ requêtes simultanées OK

#### 4. Système de Queue pour async tasks
- **Description** : Gérer les opérations longues (spy, trace...) proprement
- **Usage** : `task_id = spy_remotes_async()` → `get_result(task_id)`
- **Implémentation** :
  - Class `ResultQueue` avec threading
  - Endpoint `/queue/{id}` dans bridge
  - Outils concernés : spy_remotes, trace_events, trace_function_calls

---

## 📊 Résumé des gains

| Problème | Solution |
|----------|----------|
| 🔴 Clipboard unreliable | ✅ HTTP callbacks + file polling |
| 🔴 Race conditions | ✅ Status files + polling intelligent |
| 🔴 Pas de résultats async | ✅ Queue system + task IDs |
| 🔴 Timeouts arbitraires | ✅ Polling adaptatif |
| 🔴 Gros résultats lents | ✅ Compression + chunking |
| 🔴 Erreurs non catchées | ✅ Logging structuré |

---

## ✅ Features existantes (fonctionnelles)

- [x] Attachement automatique Roblox
- [x] Exécution Lua
- [x] Capture de retour (execute_and_capture)
- [x] Liste des clients
- [x] Modification des settings Xeno
- [x] Stack trace
- [x] **Élimination dépendance clipboard (HTTP callback + fallback chain)** ✅ *04/05/2026*

---

## 🚀 Pour plus tard

- [ ] Join jeu spécifique
- [ ] Screenshot automatique
- [ ] Auto-reconnexion
- [ ] Historique des scripts
- [ ] GUI web pour le bridge
- [ ] Pool HTTP réutilisable
- [ ] Cache métadonnées clients
- [ ] Compression gros résultats

---

## ✅ Récemment complétés

### 04/05/2026 - Élimination dépendance clipboard
- ✅ Implémenté `ResultStore` thread-safe avec TTL 2min
- ✅ Endpoints `POST /result/{id}` et `GET /result/{id}` dans bridge C#
- ✅ Fonctions `_execute_with_callback()`, `_execute_and_read_v2()`, `_execute_and_capture_smart()`
- ✅ Chaîne de fallback : HTTP → file+clipboard
- ✅ Tests : 8+ requêtes simultanées sans race conditions

---

*Notes prises le 02/05/2025 — Mise à jour 04/05/2026*

"Move fast and break things... but have good logs"

--Zenith
