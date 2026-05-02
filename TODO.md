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

#### 3. Éliminer dépendance clipboard
- **Description** : Remplacer setclipboard par système plus fiable
- **Options** :
  - **Option A (HTTP)** : Ajouter endpoints `/result/{id}` au bridge C# + utiliser `request()` côté Lua
  - **Option B (Files)** : Polling avec fichiers status (`file.txt` + `file_status.txt`)
  - **Option C (Fallback)** : Essayer HTTP → Files → Clipboard
- **Implémentation** :
  ```python
  def _execute_and_capture_smart(pid, lua_code):
      try: return _http_callback()      # Méthode 1
      except: pass
      try: return _file_polling()       # Méthode 2  
      except: pass
      return _clipboard_legacy()        # Méthode 3
  ```

---

## ✅ Features existantes (fonctionnelles)

- [x] Attachement automatique Roblox
- [x] Exécution Lua
- [x] Capture de retour (execute_and_capture)
- [x] Liste des clients
- [x] Modification des settings Xeno
- [x] Stack trace

---

## 🚀 Pour plus tard

- [ ] Join jeu spécifique
- [ ] Screenshot automatique
- [ ] Auto-reconnexion
- [ ] Historique des scripts
- [ ] GUI web pour le bridge
- [ ] Système de queue pour async tasks (spy, trace...)
- [ ] Pool HTTP réutilisable (meilleure perf)

---

*Notes prises le 02/05/2025*
