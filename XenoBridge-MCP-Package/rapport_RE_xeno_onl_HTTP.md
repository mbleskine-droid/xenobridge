# Rapport de Rétro-Ingénierie — Xeno Executor DLL
## Analyse des fonctions réseau HTTP / localhost

**Date d'analyse :** 25 avril 2026  
**Source HAR :** `xeno.onl_o_Archive [26-04-25 14-52-17].har`  
**Outil :** Ghidra MCP (analyse statique de la DLL)  
**Plateforme cible :** Windows x64 (PE64 / DLL)

---

## 1. Vue d'ensemble de l'architecture

La DLL Xeno expose **6 exports nommés** qui constituent son API publique. Ces exports sont appelés directement par la page web `https://xeno.onl/executor` via un agent HTTP local.

| Export | Adresse | Rôle |
|--------|---------|------|
| `Initialize` | `0x1801673a0` | Initialisation globale + spawn des threads serveur |
| `Attach` | `0x180167b90` | Attachement à un processus Roblox |
| `Version` | `0x180167ba0` | Retourne la version de la DLL |
| `Execute` | `0x180167bc0` | Exécute un script Lua sur un ou plusieurs clients |
| `GetClients` | `0x180167de0` | Liste les clients Roblox attachés |
| `SetSetting` | `0x180168110` | Modifie un paramètre de configuration |

---

## 2. Analyse du trafic HAR — Le protocole HTTP local

Le fichier HAR capture une requête réelle envoyée par Firefox depuis `https://xeno.onl/executor` vers le serveur local de la DLL.

### Requête capturée

```
POST http://localhost:3110/o  HTTP/1.1
Host: localhost:3110
Origin: https://xeno.onl
Content-Type: text/plain
Clients: ["2548"]
Content-Length: 22

print("Hello, World!")
```

### Réponse du serveur local

```
HTTP/1.1 200 OK
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Clients
Keep-Alive: timeout=5, max=100
Content-Length: 0
```

### Décodage du protocole

| Champ | Valeur | Signification |
|-------|--------|---------------|
| Port | `3110` | Port d'écoute fixe du serveur HTTP de la DLL |
| Endpoint | `/o` | Route d'exécution de scripts ("**o**pen execute") |
| Header `Clients` | `["2548"]` | Tableau JSON des PIDs des clients Roblox ciblés |
| Body | Script Lua brut | Code à exécuter (texte plain, non encodé) |
| `serverIPAddress` | `::1` | Loopback IPv6, confirme un serveur local |
| `_securityState` | `insecure` | HTTP pur (pas de TLS sur localhost) |

---

## 3. Analyse statique des fonctions clés

### 3.1 `Initialize` — `0x1801673a0`

C'est le point d'entrée principal de la DLL. Son flux d'exécution :

1. **Appel à `_time64()`** — enregistre l'heure de démarrage dans `DAT_180223d08`
2. **Chargement de `ntdll.dll`** via `LoadLibraryA` et résolution de 6 fonctions NT :
   - `NtUnlockVirtualMemory`
   - `NtLockVirtualMemory`
   - `NtSuspendProcess`
   - `NtResumeProcess`
   - `NtReadVirtualMemory`
   - `NtWriteVirtualMemory`
3. **Initialisation de libcurl** — `curl_global_init(3)` + `curl_share_init()` avec partage des cookies et connexions (options `1` et `3`/`4`), ce qui indique des appels HTTP sortants (probablement vers `xeno.onl` pour la validation de licence)
4. **Chargement de ressources embarquées** via `FindResourceW` (types `0x2000` et `0x2004`, type `0x2002`) — données internes au PE
5. **Spawn de 4 threads de travail** via `_beginthreadex` :
   - Thread 1 → `FUN_1801671e0` : gestionnaire de processus Roblox (détection, killswitch)
   - Thread 2 → `FUN_1800d6210` : gestionnaire du cache (`XENO_CACHE.bin`) + serveur
   - Thread 3 → `FUN_18016a110` : (non décompilé — probablement le serveur HTTP sur 3110)
   - Thread 4 → `FUN_18012fc10` : tâche de fond supplémentaire
6. Chaque thread est immédiatement détaché (`_Thrd_detach`)

> **Note clé :** La version de la DLL est stockée dans la chaîne `"v1_3_30"` (visible dans le code de `Initialize`) et le port hardcodé est `3110` (valeur `0xC26`).

---

### 3.2 `Execute` — `0x180167bc0`

```c
void Execute(longlong script_ptr, longlong clients_array, ulonglong client_count)
```

**Paramètres :**
- `param_1` (`script_ptr`) : pointeur vers la chaîne du script Lua
- `param_2` (`clients_array`) : tableau d'entiers (PIDs clients)
- `param_3` (`client_count`) : nombre de clients dans le tableau

**Logique interne :**

1. Itère sur chaque PID dans `clients_array`
2. Verrouille un mutex (`DAT_1801e95b0`) pour accéder à la liste des clients attachés
3. Parcourt la liste globale des clients (`DAT_180223ff8` → `DAT_180224000`)
4. Pour chaque client, vérifie que le PID correspond ET que le processus est **toujours en vie** via `GetExitCodeProcess()` (code attendu : `0x103` = `STILL_ACTIVE`)
5. Si le client est valide, alloue un bloc de 0x18 octets contenant `{client_handle, shared_data, script_ptr}` et le passe à un thread d'exécution via `_beginthreadex(FUN_180168b00, ...)`
6. Le thread d'exécution est immédiatement détaché — l'exécution est **asynchrone**

> **Point important :** Il n'y a **aucune validation du contenu du script** dans `Execute`. Le Lua est passé tel quel. La seule vérification est l'état STILL_ACTIVE du processus cible.

---

### 3.3 `GetClients` — `0x180167de0`

```c
undefined8 *GetClients(void)
```

Retourne un objet JSON (sérialisé en C++) contenant la liste des clients Roblox actifs avec pour chaque client :
- Le PID (`0x1c8` → `uVar1` = PID en tant que `uint`)
- Des champs à offsets `+0x180`, `+0x1a8` (probablement nom du jeu / username)
- Un champ entier à `+0x210` (probablement le PlaceId ou JobId)
- Un champ `ulonglong` à `+0x1a0`

La sérialisation utilise un format interne à base d'objets dynamiques (le code construit des paires clé/valeur dans une structure de type `std::vector`).

Le résultat est renvoyé comme pointeur sur une chaîne/objet géré par la DLL. C'est ce que le serveur HTTP renvoie quand la page web interroge la liste des clients disponibles.

---

### 3.4 Thread `FUN_1801671e0` — Gestionnaire de processus

Ce thread tourne **en boucle infinie** et effectue deux rôles :

**Rôle 1 — Anti-démarrage multiple :**
- Appelle `GetCurrentProcessId()` pour obtenir son propre PID
- Appelle `GetModuleFileNameW()` pour obtenir le nom du processus parent
- Énumère tous les processus Windows ayant le même nom (`FUN_180165b40`)
- Pour chaque processus différent du sien, tente `OpenProcess(1, 0, pid)` et si réussi, log un message (`"..."`, offset `0x1801c89c0`) puis **`TerminateProcess(hProcess, 0)`** — il tue les autres instances

**Rôle 2 — Boucle d'attente/signal :**
- Alterne entre deux comportements selon `DAT_180223cc1`
- Appelle `FUN_180166900(1)` ou `FUN_180166900(0)` (probablement une signalisation)
- Calcule un timeout de `25_000_000` unités puis appelle `FUN_18001e3b0` (probablement un `Sleep` ou `WaitForSingleObject`)

---

### 3.5 Thread `FUN_1800d6210` — Cache + Infrastructure

Ce thread gère le fichier `XENO_CACHE.bin` stocké dans `%TEMP%\Xeno\`. Il charge ou crée ce cache binaire contenant :

| Structure | Description |
|-----------|-------------|
| `RBXBytecode` | Bytecode Roblox compilé (hash SHA-256 sur 0x20 octets par entrée) |
| `RBXMFlags` | Flags mémoire Roblox |
| `RBXClientInfo` | Infos par client (PID, offsets, flags, listes de chaînes) |
| PIDs cachés | Liste des PIDs Roblox connus (`"Reattaching to cached client PID: {}"`) |

**Détail notable :** Si aucun cache valide n'est trouvé, la DLL ouvre automatiquement `https://discord.gg/xe-no` via `ShellExecuteW` — comportement d'onboarding.

---

## 4. Flux complet d'une exécution de script

```
[Page web xeno.onl/executor]
         │
         │  POST http://localhost:3110/o
         │  Headers: Clients: ["2548"]
         │  Body: print("Hello, World!")
         ▼
[Serveur HTTP local (port 3110) — Thread 3 de la DLL]
         │
         │  Parse le header "Clients" → tableau de PIDs [2548]
         │  Parse le body → script Lua brut
         │
         ▼
[Export Execute(script_ptr, [2548], 1)]
         │
         │  Lock mutex
         │  Recherche PID 2548 dans la liste des clients attachés
         │  GetExitCodeProcess → vérifie STILL_ACTIVE (0x103)
         │
         ▼
[_beginthreadex → FUN_180168b00]
         │
         │  Exécution asynchrone du script Lua
         │  dans le processus Roblox PID 2548
         │
         ▼
[HTTP Response: 200 OK, Content-Length: 0]
```

---

## 5. Résumé des appels système réseau identifiés

| Fonction | Origine | Usage |
|----------|---------|-------|
| `curl_global_init(3)` | `Initialize` | Init libcurl (HTTP sortant vers xeno.onl) |
| `curl_share_init()` | `Initialize` | Partage de session HTTP entre threads |
| `curl_share_setopt(share, 1, 3/4)` | `Initialize` | Partage des cookies et DNS |
| Serveur HTTP sur `:3110` | Thread 3 | Réception des commandes depuis le navigateur |
| CORS headers `Access-Control-Allow-Origin: *` | Thread 3 | Autorise les requêtes cross-origin depuis `xeno.onl` |
| `ShellExecuteW(L"https://discord.gg/xe-no")` | `FUN_1800d6210` | Ouverture automatique du Discord si pas de cache |

---

## 6. Points de sécurité notables

1. **Pas d'authentification sur le serveur local** — n'importe quelle page web peut POST sur `localhost:3110/o` si le header `Origin` est accepté (mais les réponses CORS ne filtrent pas l'origin : `*`)
2. **Pas de validation du script Lua** dans `Execute` — le code est passé directement au moteur Roblox
3. **Communication HTTP non chiffrée** (`_securityState: insecure`) — le trafic localhost est en clair
4. **Les PIDs sont des `int32`** — pas d'authentification par token ou nonce pour identifier un client
5. **Killswitch actif** — la DLL tue les autres instances du même processus au démarrage

---

## 7. Chaînes littérales significatives identifiées

```
"Failed to load ntdll.dll"
"A symbol was unable to be loaded from ntdll.dll"
"A Xeno resource was unable to load, will abort immediately."
"Xeno directory missing: \"{}\"" 
"Directory \"{}\" was created. Restart Xeno if problem persists"
"Caching file: {}"
"Loaded existing cache: {} RBXClients, {} RBXBytecode, {} RBXMFlags, {} RBXClientInfos"
"Reattaching to cached client PID: {}"
"Failed to read RBXBytecode #{}"
"Failed to read RBXMFlags #{}"
"Failed to read RBXClientInfo #{}"
"No cache file found at {}"
"No valid cache found (Starting new fresh cache)"
"Inviting you to our Official Discord server :D {}"
"Invalid or corrupted cache header (file: {})"
"v1_3_30"
"https://discord.gg/xe-no"
```

---

*Rapport généré le 25 avril 2026 — Analyse statique Ghidra MCP*
