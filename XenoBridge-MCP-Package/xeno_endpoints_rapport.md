# Xeno Executor — Endpoints HTTP localhost
## Rapport d'analyse RE (v1_3_30)

**Port :** `localhost:3110`  
**Protocole :** HTTP/1.1 (pas de TLS)  
**Source :** HAR `xeno.onl` + décompilation Ghidra MCP

---

## Endpoints identifiés

### `POST /o` — Execute ✅ CONFIRMÉ (HAR)

Exécute un script Lua sur un ou plusieurs clients Roblox.

**Requête :**
```http
POST http://localhost:3110/o HTTP/1.1
Host: localhost:3110
Content-Type: text/plain
Clients: ["<PID>"]
Origin: https://xeno.onl

<script lua brut>
```

**Réponse :**
```http
HTTP/1.1 200 OK
Content-Length: 0
Access-Control-Allow-Origin: *
```

**Notes :**
- Le header `Clients` est un tableau JSON de PIDs (entiers en string)
- Le body est le script Lua **brut** (pas encodé, pas de JSON wrapping)
- Réponse vide `Content-Length: 0` — pas de retour de valeur
- Execution asynchrone via `_beginthreadex` → `FUN_180168b00`

---

### `GET /g` — GetClients ⚠️ PROBABLE

Retourne la liste des clients Roblox actuellement attachés.

**Requête :**
```http
GET http://localhost:3110/g HTTP/1.1
Host: localhost:3110
Origin: https://xeno.onl
```

**Réponse attendue (JSON) :**
```json
[
  {
    "pid": 2548,
    "...": "..."
  }
]
```

**Notes RE :**
- `GetClients` est référencé dans les tables DATA à `0x1801e3450` et `0x18022f240`
- La fonction construit une collection d'objets avec PID (`+0x1c8`), nom (`+0x180`, `+0x1a8`), PlaceId (`+0x210`), JobId (`+0x1a0`)
- Naming pattern cohérent avec `/g` = **g**et clients (même convention `/o` = **o**pen/execute)

---

### `POST /a` — Attach ⚠️ PROBABLE

Déclenche la détection et l'attachement à un processus Roblox.

**Requête :**
```http
POST http://localhost:3110/a HTTP/1.1
Host: localhost:3110
Content-Type: text/plain
Origin: https://xeno.onl
```

**Notes RE :**
- `Attach` → appelle directement `FUN_180166900(0)`
- `FUN_180166900` scanne les processus nommés `RobloxPlayerBeta.exe` et `eurotrucks2.exe`
- Aucun body requis a priori (l'attach est automatique par scan de processus)

---

### `POST /s` — SetSetting ⚠️ PROBABLE

Modifie un paramètre de la DLL.

**Requête :**
```http
POST http://localhost:3110/s HTTP/1.1
Host: localhost:3110
Content-Type: text/plain
Origin: https://xeno.onl

<setting_id> <value>
```

**Paramètres connus (décompilés depuis `SetSetting`) :**

| `param_1` (setting ID) | `param_2` (value) | Effet |
|------------------------|-------------------|-------|
| `0` | `0` ou `1` | Active/désactive le mode furtif (`DAT_180223cc1`) |
| `1` | `0` | Désactive le Discord RPC (`"RPC was disabled"`) |
| `1` | `1` | Active le Discord RPC (`"RPC is Enabled"`) |

**Notes RE :**
- L'activation du RPC (`param_1=1, param_2=1`) spawn un thread supplémentaire (`FUN_180168bf0`)
- Discord App ID : `1393297926209405000`
- URL interne liée au RPC : `https://xeno.now`
- Secrets hardcodés : `"secretA"`, `"secretB"`

---

### `GET /v` — Version ⚠️ POSSIBLE

Retourne la version de la DLL.

**Requête :**
```http
GET http://localhost:3110/v HTTP/1.1
Host: localhost:3110
Origin: https://xeno.onl
```

**Réponse attendue :**
```
v1_3_30
```

**Notes RE :**
- `Version` → retourne directement la chaîne `s_v1_3_30`
- Référencé dans la table DATA à `0x1801e345c`

---

## Récapitulatif

| Route | Méthode | Export DLL | Statut | Adresse export |
|-------|---------|------------|--------|----------------|
| `/o`  | `POST`  | `Execute`  | ✅ Confirmé HAR | `0x180167bc0` |
| `/g`  | `GET`   | `GetClients` | ⚠️ Probable | `0x180167de0` |
| `/a`  | `POST`  | `Attach`   | ⚠️ Probable | `0x180167b90` |
| `/s`  | `POST`  | `SetSetting` | ⚠️ Probable | `0x180168110` |
| `/v`  | `GET`   | `Version`  | ⚠️ Possible | `0x180167ba0` |

---

## CORS & Sécurité

Le serveur répond avec :
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Clients
```

**Pas d'authentification.** N'importe quelle page web peut appeler ces endpoints si l'utilisateur a Xeno en cours d'exécution. Seule la présence d'un client Roblox actif (PID `STILL_ACTIVE`) est vérifiée par `Execute`.

---

*Rapport partiel — `FUN_18012fc10` (thread serveur HTTP) non décompilable (timeout MCP). À compléter après résultats des tests.*
