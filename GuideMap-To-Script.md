

# `GuideMap-To-Script.md`

# GuideMap-To-Script — Le Manuel Complet de l'Exploit Developer (v2.0)

**Objectif** : Fournir un cadre systématique pour analyser, comprendre et exploiter les faiblesses de n'importe quel jeu Roblox. Ce guide se concentre sur le **flux de travail (workflow)** et la **méthodologie**, de la reconnaissance initiale à l'automatisation avancée.

---

## Partie 1 – La Phase de Reconnaissance : Comprendre le Jeu

Avant d'écrire la moindre ligne de code, vous devez cartographier la surface d'attaque du jeu. Votre objectif est de trouver les points d'interaction entre le client (vous) et le serveur.

### 1.1. L'Approche "Externe" (Analyse sans outils)
La première chose qu'un exploit dev fait est de comprendre le jeu de manière conventionnelle.
- **Objectif** : Jouez normalement et identifiez ce qui a de la valeur (argent, items, kills).
- **Trigger** : Déclenchez l'action de valeur (cliquez sur un bouton "Acheter", ramassez un objet, tirez avec une arme).
- **Hypothèse** : Cette action a *très probablement* déclenché un `RemoteEvent:FireServer()` ou un `RemoteFunction:InvokeServer()`.

### 1.2. L'Approche "Interne" (Le Scan de Remotes)
Maintenant que vous avez une idée de quoi chercher, passez à l'analyse en direct avec votre executor.

**Étape 1 : Le Scan Profond**
Ne vous limitez pas à `ReplicatedStorage`. Les jeux cachent souvent leurs Remotes dans des endroits moins conventionnels. Utilisez ce script de scan universel :

```lua
local servicesToScan = {
    game:GetService("ReplicatedStorage"),
    game:GetService("Workspace"),
    game:GetService("Players"),
    game:GetService("Lighting"),
    game:GetService("StarterGui"),
    game:GetService("StarterPack"),
    game:GetService("StarterPlayer")
}

local discoveredRemotes = {}

for _, service in ipairs(servicesToScan) do
    for _, obj in ipairs(service:GetDescendants()) do
        if obj:IsA("RemoteEvent") or obj:IsA("RemoteFunction") then
            table.insert(discoveredRemotes, {
                Name = obj.Name,
                Class = obj.ClassName,
                Path = obj:GetFullName(),
                Parent = obj.Parent and obj.Parent:GetFullName() or "nil"
            })
        end
    end
end

return discoveredRemotes
```

**Étape 2 : L'Analyse des Noms**
Les jeux, même les plus complexes, ont des conventions de nommage prévisibles. Scannez la liste des Remotes pour :
- **Mots-clés de valeur** : `Money`, `Cash`, `Gold`, `Gem`, `Coin`, `Point`, `Level`, `XP`, `Reward`, `Grant`, `Award`, `Give`.
- **Mots-clés d'action** : `Buy`, `Sell`, `Trade`, `Upgrade`, `Equip`, `Use`, `Activate`, `Hit`, `Damage`, `Kill`, `Fire`, `Shoot`, `Teleport`, `Move`.
- **Mots-clés de localisation** : Les noms de zones du jeu (ex: `LobbyRemotes`, `DungeonEvent`, `BossFightActions`).

### 1.3. Le "Silent Hook" (pour les cas complexes)
Si les noms sont obfusqués ou si vous voulez accéder à des remotes cachées, utilisez `getnilinstances()`. Cette fonction permet de trouver des objets dont la propriété `Parent` est définie sur `nil`, une technique courante pour cacher des objets aux scanners classiques.

```lua
local remotesFromNil = {}
local nilInstances = getnilinstances()
for _, v in pairs(nilInstances) do
    if v:IsA("RemoteEvent") or v:IsA("RemoteFunction") then
        table.insert(remotesFromNil, {Name = v.Name, Class = v.ClassName})
    end
end
return remotesFromNil
```
**[Source : Fil de discussion "Having trouble with exploiters? Unsigned can help!" sur le DevForum Roblox]**

---

## Partie 2 – Le Guide Pratique d'Exploitation

C'est ici que la plupart des "script kiddies" échouent. Ils spamment des `FireServer` au hasard, se font repérer et sont bannis. Un vrai exploit dev suit un processus.

### Étape 1 : Le Scan (Découverte)
Exécutez le script de la Partie 1 pour obtenir une liste de toutes les remotes.

### Étape 2 : La Capture (Compréhension)
C'est l'étape la plus cruciale. **Vous devez capturer à quoi ressemble un appel légitime.**
1.  **Activez votre Remote Spy**. C'est un script qui va intercepter et logger tous les `FireServer` et `InvokeServer` que le jeu lui-même déclenche. Des exemples incluent **SimpleSpy**, **TurtleSpy**, ou l'outil **SaneLittleHelper** qui permet de le faire de manière plus interactive.
2.  **Déclenchez l'action en jeu** (achetez une chose, tirez avec l'arme). Le Remote Spy va afficher le nom de la remote et les arguments exacts.
3.  **Analysez les arguments**.
    *   Repérez l'argument qui correspond à la valeur que vous voulez (ex: le deuxième argument est `100`, c'est sûrement le nombre de pièces).
    *   Repérez l'argument qui pourrait être une clé de sécurité ou un identifiant unique. Modifier cet argument peut ne pas fonctionner ou déclencher l'anti-cheat.
    *   Repérez l'objet `Player`. Le serveur l'utilise souvent pour valider l'appel. Votre script devra l'envoyer aussi (généralement le `LocalPlayer`).

### Étape 3 : Le Rejeu (Test)
Maintenant, vous allez rejouer l'appel capturé avec vos propres arguments, manuellement, pour tester.
```lua
-- Exemple : Rejeu de l'appel capturé "GiveCash" avec un montant modifié
local remote = game:GetService("ReplicatedStorage").Remotes.GiveCash
remote:FireServer(game.Players.LocalPlayer, 999999) -- On modifie le 2eme argument
```
*   **Si ça marche** : Félicitations, vous avez trouvé un filon !
*   **Si vous êtes kické** : Vous avez déclenché l'anti-cheat. Analysez mieux la capture. Il y avait probablement un ticket, un token, ou une clé unique (Argument #1) que vous avez mal copié.
*   **Si rien ne se passe** : L'argument est peut-être vérifié côté serveur (ex: `si montant > gain_max_alors stop`). L'exploit n'est pas possible sur cette seule Remote.

### Étape 4 : L'Automatisation (Déploiement)
Une fois le test réussi, vous pouvez envelopper l'appel dans une boucle en toute confiance.

---

## Partie 3 – La Base de Connaissances (Bibliothèque de Patterns)

Une fois que vous avez compris le flux ci-dessus, vous pouvez l'appliquer à une large gamme de jeux. Voici les patterns d'exploitation les plus courants.

| Objectif           | Type de Remote / Objet | Arguments Typiques                                                                 | Script Exemple                                                                                                                              |
| ------------------ | ---------------------- | ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Auto-Farm**      | RemoteEvent            | `(Player, Number)`                                                                 | `while true do r:FireServer(plr, 1e9) task.wait(0.01) end`                                                                                  |
| **Achat Gratuit**  | RemoteEvent/Function   | `(String, Player)`                                                                 | `r:InvokeServer("Cash", plr)`                                                                                                                |
| **Kill Aura**      | RemoteEvent            | `(Player, Player)`                                                                 | `for i,v in pairs(game.Players:GetPlayers()) do r:FireServer(v) end`                                                                         |
| **God Mode**       | Fonction               | `(Boolean)`                                                                        | `r:FireServer(true)` ou `hookfunction(hum.Health, function() return 9999 end)`                                                                |
| **Fly / Noclip**   | Physique Locale        | `(Vector3)`                                                                        | `local bv = Instance.new("BodyVelocity"); bv.Velocity = Vector3.new(0,50,0); bv.Parent = root`                                               |
| **Silent Aim**     | Fonction (Raycast)     | `(Vector3, Vector3)`                                                               | `hookfunction(Raycast, function(...) local args = {...}; args[3] = targetHead.Position; return oldRay(unpack(args)) end)` |
| **ESP (Wallhack)** | Drawing Library        | N/A                                                                                | Utilisez `Drawing.new("Square")` sur chaque joueur                                                                                          |
| **Server Crasher** | Divers                 | N/A                                                                                | `while true do r:FireServer() end` (à utiliser avec modération)                                                                              |

---

## Partie 4 – Considérations Avancées (Pour aller plus loin)

### 4.1. Anti-Anti-Cheat (Restez sous le radar)
Les jeux avancés mettent en place des défenses. Voici comment les contourner.
-   **Hooking Sécurisé** : Utilisez `newcclosure()` pour votre spy et vos hooks. Cela rend la détection par l'anti-cheat beaucoup plus difficile car cela "nettoie" la trace d'appel.
-   **Contournement des Vérifications Côté Serveur** : Si un "token" de sécurité est requis, votre Remote Spy en capturera un valide lors de l'Étape 2. Vous pouvez soit le réutiliser (s'il est à usage unique, vous aurez un souci), soit essayer de comprendre la logique de génération du token (souvent un hash simple d'une valeur statique).
-   **Soyez Rapide, Pas Vorace** : Ne spammez pas bêtement. Un `task.wait(0.05 + math.random() * 0.1)` entre les appels est souvent plus sûr qu'un `task.wait(0.001)` qui déclenche des détections de fréquence.

### 4.2. Outils d'Analyse Avancés
Ce ne sont pas des scripts de cheat en eux-mêmes, mais des outils de développement qui vous donnent un avantage massif. Les exploiteurs sérieux utilisent des versions "sécurisées" de ces outils (comme le Secure Dex) conçues pour contourner les détections des anti-cheats.
-   **Dark Dex (ou Synaptic X)** : Un explorateur d'objets visuel qui vous permet de naviguer dans toute la hiérarchie du jeu en temps réel pour trouver des remotes.
-   **Remote Spy (ou SimpleSpy)** : Comme expliqué précédemment, il intercepte et loggue tous les appels réseau.
-   **SaveInstance** : Permet d'exporter la carte du jeu pour l'analyser hors-ligne.

---
