# `GuideMap-To-Script.md`

# GuideMap-To-Script — The Complete Exploit Developer's Handbook (v2.0)

**Objective**: Provide a systematic framework for analyzing, understanding, and exploiting the weaknesses of any Roblox game. This guide focuses on the **workflow** and **methodology**, from initial reconnaissance to advanced automation.

---

## Part 1 – The Reconnaissance Phase: Understanding the Game

Before writing a single line of code, you must map the game's attack surface. Your goal is to find the interaction points between the client (you) and the server.

### 1.1. The "External" Approach (Analysis without tools)
The first thing an exploit dev does is understand the game in a conventional way.
- **Objective**: Play normally and identify what has value (money, items, kills).
- **Trigger**: Trigger the valuable action (click a "Buy" button, pick up an item, fire a weapon).
- **Hypothesis**: This action *very likely* fired a `RemoteEvent:FireServer()` or a `RemoteFunction:InvokeServer()`.

### 1.2. The "Internal" Approach (Remote Scanning)
Now that you have an idea of what to look for, move on to live analysis with your executor.

**Step 1: Deep Scan**
Don't limit yourself to `ReplicatedStorage`. Games often hide their Remotes in less conventional places. Use this universal scanning script:

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

**Step 2: Name Analysis**
Games, even the most complex ones, have predictable naming conventions. Scan the list of Remotes for:
- **Value keywords**: `Money`, `Cash`, `Gold`, `Gem`, `Coin`, `Point`, `Level`, `XP`, `Reward`, `Grant`, `Award`, `Give`.
- **Action keywords**: `Buy`, `Sell`, `Trade`, `Upgrade`, `Equip`, `Use`, `Activate`, `Hit`, `Damage`, `Kill`, `Fire`, `Shoot`, `Teleport`, `Move`.
- **Location keywords**: Names of game areas (e.g., `LobbyRemotes`, `DungeonEvent`, `BossFightActions`).

### 1.3. The "Silent Hook" (for complex cases)
If names are obfuscated or you want to access hidden remotes, use `getnilinstances()`. This function finds objects whose `Parent` property is set to `nil`, a common technique to hide objects from standard scanners.

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
**[Source: "Having trouble with exploiters? Unsigned can help!" thread on the Roblox DevForum]**

---

## Part 2 – The Practical Exploitation Guide

This is where most "script kiddies" fail. They spam `FireServer` randomly, get detected, and are banned. A real exploit dev follows a process.

### Step 1: Scan (Discovery)
Run the script from Part 1 to get a list of all remotes.

### Step 2: Capture (Understanding)
This is the most crucial step. **You must capture what a legitimate call looks like.**
1.  **Activate your Remote Spy**. This is a script that will intercept and log all `FireServer` and `InvokeServer` calls that the game itself triggers. Examples include **SimpleSpy**, **TurtleSpy**, or the **SaneLittleHelper** tool which allows you to do this more interactively.
2.  **Trigger the action in-game** (buy something, fire the weapon). The Remote Spy will display the remote's name and the exact arguments.
3.  **Analyze the arguments**.
    *   Identify the argument that corresponds to the value you want (e.g., the second argument is `100`, that's probably the number of coins).
    *   Identify the argument that might be a security key or a unique identifier. Modifying this argument might not work or could trigger the anti-cheat.
    *   Identify the `Player` object. The server often uses it to validate the call. Your script will need to send it too (usually the `LocalPlayer`).

### Step 3: Replay (Test)
Now, you will replay the captured call with your own arguments, manually, to test.
```lua
-- Example: Replay the captured "GiveCash" call with a modified amount
local remote = game:GetService("ReplicatedStorage").Remotes.GiveCash
remote:FireServer(game.Players.LocalPlayer, 999999) -- We modify the 2nd argument
```
*   **If it works**: Congratulations, you've found a goldmine!
*   **If you get kicked**: You triggered the anti-cheat. Analyze the capture better. There was probably a ticket, token, or unique key (Argument #1) that you copied incorrectly.
*   **If nothing happens**: The argument might be verified server-side (e.g., `if amount > max_gain then stop`). The exploit is not possible on this Remote alone.

### Step 4: Automation (Deployment)
Once the test is successful, you can wrap the call in a loop with confidence.

---

## Part 3 – The Knowledge Base (Pattern Library)

Once you understand the flow above, you can apply it to a wide range of games. Here are the most common exploitation patterns.

| Goal               | Remote/Object Type     | Typical Arguments                                                                  | Example Script                                                                                                                              |
| ------------------ | ---------------------- | ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Auto-Farm**      | RemoteEvent            | `(Player, Number)`                                                                 | `while true do r:FireServer(plr, 1e9) task.wait(0.01) end`                                                                                  |
| **Free Purchase**  | RemoteEvent/Function   | `(String, Player)`                                                                 | `r:InvokeServer("Cash", plr)`                                                                                                                |
| **Kill Aura**      | RemoteEvent            | `(Player, Player)`                                                                 | `for i,v in pairs(game.Players:GetPlayers()) do r:FireServer(v) end`                                                                         |
| **God Mode**       | Function               | `(Boolean)`                                                                        | `r:FireServer(true)` or `hookfunction(hum.Health, function() return 9999 end)`                                                                |
| **Fly / Noclip**   | Local Physics          | `(Vector3)`                                                                        | `local bv = Instance.new("BodyVelocity"); bv.Velocity = Vector3.new(0,50,0); bv.Parent = root`                                               |
| **Silent Aim**     | Function (Raycast)     | `(Vector3, Vector3)`                                                               | `hookfunction(Raycast, function(...) local args = {...}; args[3] = targetHead.Position; return oldRay(unpack(args)) end)` |
| **ESP (Wallhack)** | Drawing Library        | N/A                                                                                | Use `Drawing.new("Square")` on each player                                                                                                  |
| **Server Crasher** | Various                | N/A                                                                                | `while true do r:FireServer() end` (use with moderation)                                                                                     |

---

## Part 4 – Advanced Considerations (Going Further)

### 4.1. Anti-Anti-Cheat (Stay Under the Radar)
Advanced games implement defenses. Here's how to bypass them.
-   **Secure Hooking**: Use `newcclosure()` for your spy and your hooks. This makes detection by the anti-cheat much harder because it "cleans" the call stack.
-   **Bypassing Server-Side Checks**: If a security "token" is required, your Remote Spy will capture a valid one during Step 2. You can either reuse it (if it's single-use, you'll have a problem), or try to understand the token generation logic (often a simple hash of a static value).
-   **Be Fast, Not Greedy**: Don't spam mindlessly. A `task.wait(0.05 + math.random() * 0.1)` between calls is often safer than a `task.wait(0.001)` which triggers frequency detections.

### 4.2. Advanced Analysis Tools
These are not cheat scripts themselves, but development tools that give you a massive advantage. Serious exploiters use "secured" versions of these tools (like Secure Dex) designed to bypass anti-cheat detections.
-   **Dark Dex (or Synaptic X)**: A visual object explorer that lets you navigate the entire game hierarchy in real time to find remotes.
-   **Remote Spy (or SimpleSpy)**: As explained earlier, intercepts and logs all network calls.
-   **SaveInstance**: Allows exporting the game map for offline analysis.

---
