--[[
    WordHelper v5.1.2 — Voxxar
    Full-featured word assistant for Word Bomb / BombParty on Roblox
    
    v5.1.2 Changelog:
    - Added Last Letter gamemode auto-detection
    - Fixed enemy word detection tracking
    - Added in-game refresh loop for help/pity feature
    - Fixed help button with multiple chat method fallbacks
    - Added enemyUsedWords tracking
]]

---------------------------------------------------------------------
-- 1. SERVICES
---------------------------------------------------------------------
local Players            = game:GetService("Players")
local VirtualInputManager= game:GetService("VirtualInputManager")
local UserInputService   = game:GetService("UserInputService")
local StarterGui         = game:GetService("StarterGui")
local HttpService        = game:GetService("HttpService")
local SoundService       = game:GetService("SoundService")
local RunService         = game:GetService("RunService")
local TweenService       = game:GetService("TweenService")
local LocalizationService= game:GetService("LocalizationService")
local ReplicatedStorage  = game:GetService("ReplicatedStorage")
local TextChatService    = game:GetService("TextChatService")

---------------------------------------------------------------------
-- 2. CONSTANTS & IDENTIFIERS
---------------------------------------------------------------------
local SCRIPT_TAG   = "WordHelper_v6"
local DICT_URL_TXT = "https://raw.githubusercontent.com/mbleskine-droid/english-word-freq-list-370k/refs/heads/main/wordlist_by_frequency(2).txt"
local CACHE_DICT   = "VoxxarDict_v6.json"
local CACHE_FREQ   = "VoxxarFreq_v6.json"

---------------------------------------------------------------------
-- 3. CONFIG
---------------------------------------------------------------------
local CONFIG = {
    typingSpeed         = 0.082,
    minLength           = 3,
    maxLength           = 20,
    maxWordsDisplay     = 50,
    batchLoadSize       = 30,
    animBaseDelay       = 0.02,
    animStepDelay       = 0.015,
    animMaxTweens       = 10,
    toastDuration       = 3,
    abilityNotifDuration= 5,
    typoChance          = 0.08,
    fullAutoDelay       = 0.3,
    urgentTimeThreshold = 5,
    urgentTypingSpeed   = 0.03,
    ghostMode           = false,
    heartbeatInterval   = 6,
    matchAutoReset      = true,
    hoverEffects        = true,
    glowEnabled         = true,
    headerReactive      = true,
    smoothScroll        = true,
    retryDelay          = 0.4,
    retryBackspaceSpeed = 0.02,
    retryStableChecks   = 5,
    retryMaxAttempts    = 10,
}

---------------------------------------------------------------------
-- 4. MODES
---------------------------------------------------------------------
local MODES = {
    {name="Normal",  icon="✨", color=Color3.fromRGB(0,200,255),  borderColor=Color3.fromRGB(0,150,200)},
    {name="Survie",  icon="🛡️", color=Color3.fromRGB(0,255,100),  borderColor=Color3.fromRGB(0,200,80)},
    {name="Tourney", icon="🏆", color=Color3.fromRGB(255,215,0),  borderColor=Color3.fromRGB(200,170,0)},
    {name="Killer",  icon="😈", color=Color3.fromRGB(255,50,50),  borderColor=Color3.fromRGB(200,0,0)},
}

---------------------------------------------------------------------
-- 5. ABILITIES
---------------------------------------------------------------------
local ABILITIES = {
    ["rbxassetid://70404159886323"]  = "Basic (+7s)",
    ["rbxassetid://77947144563808"]  = "Double Down",
    ["rbxassetid://111640862224873"] = "Locked In",
    ["rbxassetid://71365791407896"]  = "Troublemaker",
    ["rbxassetid://100760582742903"] = "Unpredictable",
    ["rbxassetid://138231081470699"] = "Intimidator (INV!)",
    ["rbxassetid://122829515490379"] = "Upside Down",
    ["rbxassetid://110096646895213"] = "Quick (7s)",
    ["rbxassetid://132867524799724"] = "Stealer (-2)",
    ["rbxassetid://113157540479371"] = "Healer",
    ["rbxassetid://116928527478457"] = "Deleter",
    ["rbxassetid://122604365048451"] = "Blocker",
    ["rbxassetid://79885722591265"]  = "Skipper",
    ["rbxassetid://136192299714095"] = "Reverse",
    ["rbxassetid://82917746442219"]  = "Finisher (KILL)",
    ["rbxassetid://73563783252518"]  = "Mimic",
}

---------------------------------------------------------------------
-- 6. KEYBOARD LAYOUTS
---------------------------------------------------------------------
local LAYOUTS = {
    QWERTY = {
        rows = {
            {"Q","W","E","R","T","Y","U","I","O","P"},
            {"A","S","D","F","G","H","J","K","L"},
            {"Z","X","C","V","B","N","M"},
        },
        map = {},
    },
    AZERTY = {
        rows = {
            {"A","Z","E","R","T","Y","U","I","O","P"},
            {"Q","S","D","F","G","H","J","K","L","M"},
            {"W","X","C","V","B","N"},
        },
        map = {
            A = Enum.KeyCode.Q,
            Z = Enum.KeyCode.W,
            Q = Enum.KeyCode.A,
            M = Enum.KeyCode.Semicolon,
            W = Enum.KeyCode.Z,
        },
    },
    QWERTZ = {
        rows = {
            {"Q","W","E","R","T","Z","U","I","O","P"},
            {"A","S","D","F","G","H","J","K","L"},
            {"Y","X","C","V","B","N","M"},
        },
        map = {
            Z = Enum.KeyCode.Y,
            Y = Enum.KeyCode.Z,
        },
    },
}

---------------------------------------------------------------------
-- 7. KILLER SCORING CONSTANTS
---------------------------------------------------------------------
local DEST_SUFFIXES = {"zy","xy","ky","wy","py","fy","my","ny","ty","ry"}
local RARE_BIGRAMS  = {"zz","qq","xx","zx","xz","qx","jx","vx","wx","zw","zk","qz","jz","fq"}
local RARE_LETTERS  = {z=8, x=8, q=10, j=5, k=3, v=2, w=2}

---------------------------------------------------------------------
-- 8. COMMON WORDS (excluded from dictionary)
---------------------------------------------------------------------
local commonWords = {}
for _, w in ipairs({"the","and","a","an","is","it","to","of","in","for","on","with","as","at","by","or"}) do
    commonWords[w] = true
end

---------------------------------------------------------------------
-- 9. STATE VARIABLES
---------------------------------------------------------------------
local connections      = {}
local isUnloaded       = false
local uiVisible        = true
local currentModeIndex = 1
local curLayout        = "QWERTY"
local nearbyKeys       = {}
local allWords         = {}
local wordFreq         = {}
local autoMode         = 0        -- 0=OFF, 1=SEMI, 2=FULL
local destroyerOn      = false
local usedWords        = {}
local enemyUsedWords   = {}       -- Track words used by enemies
local currentGamemode  = ""       -- Detected gamemode from DisplayMatch
local topWords         = {}
local displayedCount   = 0
local byPrefix         = {}
local byFirstChar      = {}
local dictLoaded       = false
local autoTypeLock     = false
local fullAutoLock     = false
local retryBlacklist   = {}
local cachedWord       = ""
local cachedWordDirty  = true
local lastChildHash    = 0
local cachedBombTime   = nil
local abilityOn        = true
local labelPool        = {}
local activeLabels     = {}
local destructiveWords = {}
local ksCache          = {}
local sortScoreCache   = {}
-- Snapshot-based UsedWords tracking state
local prevSnapshotWord = ""    -- the word detected at time T-1
local prevTurnPlayer   = nil   -- the player whose turn it was at T-1
local pendingWord      = nil   -- word currently being typed (candidate for usedWords)
local lastEnemyWord    = ""    -- last word detected from enemy
local cachedPromptLen  = 0     -- prompt length captured at turn start (before typing)
local sessionStats     = {startTime = os.clock(), wordsTyped = 0, totalChars = 0}
local letterConns      = {}
local clickConns       = {}
local heartbeatCounter = 0
local lastHeartbeatWord= ""
local refreshThread    = nil   -- Pour éviter les boucles qui s'accumulent
local isDisplaying     = false -- Empêche displayWords de s'exécuter en parallèle
local lastDisplayedPrompt = "" -- Cache du dernier prompt affiché
local settOpen         = false
local matchActive      = false
local glowPulseRunning = true
local dragging         = false
local dragStart        = nil
local startPos         = nil
local toastVis         = false
local toastThread      = nil
local sf               = 0.85
local updateDebounce   = nil   -- Debounce pour ChildAdded/ChildRemoved

-- SinkBox state — gère le blocage des frappes humaines
local _botTyping       = false   -- TRUE uniquement pendant typeWord()

-- GAMEMODE DETECTION
local function detectGamemode()
    local ok, result = pcall(function()
        local displayMatch = playerGui:FindFirstChild("DisplayMatch")
        if not displayMatch then return nil end
        local frame = displayMatch:FindFirstChild("Frame")
        if not frame then return nil end
        local matches = frame:FindFirstChild("Matches")
        if not matches then return nil end
        local match1 = matches:FindFirstChild("1")
        if not match1 then return nil end
        local title = match1:FindFirstChild("Title")
        if not title or not title:IsA("TextLabel") then return nil end
        return title.Text
    end)
    if ok and result then
        local gamemode = string.match(result, "Gamemode:%s*(.+)")
        if gamemode then
            currentGamemode = gamemode
            return gamemode
        end
    end
    return currentGamemode
end

-- AUTO-PLAY FOR LAST LETTER
local function shouldAutoPlay()
    local gamemode = detectGamemode()
    return gamemode == "Last Letter" and autoMode == 2
end

---------------------------------------------------------------------
-- 10. FILE SYSTEM ACCESS CHECK
---------------------------------------------------------------------
local hasFSAccess = false
do
    local ok, _ = pcall(function()
        return isfile and readfile and writefile
    end)
    if ok and isfile and readfile and writefile then
        hasFSAccess = true
    end
end

---------------------------------------------------------------------
-- 11. PLAYER REFERENCES
---------------------------------------------------------------------
local player    = Players.LocalPlayer
local playerGui = player:WaitForChild("PlayerGui")

---------------------------------------------------------------------
-- 12. ANTI-DUPLICATE
---------------------------------------------------------------------
do
    -- Destroy old main GUI
    local old = playerGui:FindFirstChild(SCRIPT_TAG)
    if old then old:Destroy() end
    
    -- Destroy old input sink (VoxxarInputSink)
    local oldSink = playerGui:FindFirstChild("VoxxarInputSink")
    while oldSink do
        oldSink:Destroy()
        oldSink = playerGui:FindFirstChild("VoxxarInputSink")
    end
    
    -- Destroy old loading screen
    local oldLoading = playerGui:FindFirstChild("WordHelper_Loading")
    if oldLoading then oldLoading:Destroy() end
end

---------------------------------------------------------------------
-- 13. LOADING SCREEN
---------------------------------------------------------------------
local loadingScreen = Instance.new("ScreenGui")
loadingScreen.Name = "WordHelper_Loading"
loadingScreen.DisplayOrder = 10000
loadingScreen.IgnoreGuiInset = true
loadingScreen.ResetOnSpawn = false
loadingScreen.Parent = playerGui

local loadBg = Instance.new("Frame")
loadBg.Size = UDim2.new(1, 0, 1, 0)
loadBg.BackgroundColor3 = Color3.fromRGB(10, 10, 15)
loadBg.BorderSizePixel = 0
loadBg.ZIndex = 10000
loadBg.Parent = loadingScreen

local loadTitle = Instance.new("TextLabel")
loadTitle.Size = UDim2.new(1, 0, 0, 50)
loadTitle.Position = UDim2.new(0, 0, 0.35, 0)
loadTitle.BackgroundTransparency = 1
loadTitle.Text = "⚡ VOXXAR v5.1.2"
loadTitle.TextColor3 = Color3.fromRGB(0, 200, 255)
loadTitle.TextSize = 36
loadTitle.Font = Enum.Font.GothamBold
loadTitle.ZIndex = 10001
loadTitle.Parent = loadBg

local loadStatus = Instance.new("TextLabel")
loadStatus.Size = UDim2.new(1, 0, 0, 30)
loadStatus.Position = UDim2.new(0, 0, 0.45, 0)
loadStatus.BackgroundTransparency = 1
loadStatus.Text = "Initializing..."
loadStatus.TextColor3 = Color3.fromRGB(180, 180, 190)
loadStatus.TextSize = 18
loadStatus.Font = Enum.Font.Gotham
loadStatus.ZIndex = 10001
loadStatus.Parent = loadBg

local barBg = Instance.new("Frame")
barBg.Size = UDim2.new(0.4, 0, 0, 8)
barBg.Position = UDim2.new(0.3, 0, 0.53, 0)
barBg.BackgroundColor3 = Color3.fromRGB(40, 40, 50)
barBg.BorderSizePixel = 0
barBg.ZIndex = 10001
barBg.Parent = loadBg
Instance.new("UICorner", barBg).CornerRadius = UDim.new(0, 4)

local barFill = Instance.new("Frame")
barFill.Size = UDim2.new(0, 0, 1, 0)
barFill.BackgroundColor3 = Color3.fromRGB(0, 200, 255)
barFill.BorderSizePixel = 0
barFill.ZIndex = 10002
barFill.Parent = barBg
Instance.new("UICorner", barFill).CornerRadius = UDim.new(0, 4)

local function setLoadProgress(pct, msg)
    if loadingScreen.Parent then
        loadStatus.Text = msg or loadStatus.Text
        TweenService:Create(barFill, TweenInfo.new(0.3, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
            Size = UDim2.new(math.clamp(pct, 0, 1), 0, 1, 0)
        }):Play()
    end
end

local function dismissLoading()
    if loadingScreen.Parent then
        TweenService:Create(loadBg, TweenInfo.new(0.5, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
            BackgroundTransparency = 1
        }):Play()
        TweenService:Create(loadTitle, TweenInfo.new(0.4), {TextTransparency = 1}):Play()
        TweenService:Create(loadStatus, TweenInfo.new(0.4), {TextTransparency = 1}):Play()
        TweenService:Create(barBg, TweenInfo.new(0.4), {BackgroundTransparency = 1}):Play()
        TweenService:Create(barFill, TweenInfo.new(0.4), {BackgroundTransparency = 1}):Play()
        task.delay(0.6, function()
            if loadingScreen and loadingScreen.Parent then
                loadingScreen:Destroy()
            end
        end)
    end
end

setLoadProgress(0.05, "Waiting for game UI...")

---------------------------------------------------------------------
-- 14. WAIT FOR GAME ELEMENTS
---------------------------------------------------------------------
local inGameGui = playerGui:WaitForChild("InGame", 30)
if not inGameGui then
    setLoadProgress(1, "❌ InGame GUI not found")
    task.wait(2)
    dismissLoading()
    return
end

local gameFrame = inGameGui:WaitForChild("Frame", 15)
if not gameFrame then
    setLoadProgress(1, "❌ Game Frame not found")
    task.wait(2)
    dismissLoading()
    return
end

local currentWordFrame = gameFrame:WaitForChild("CurrentWord", 15)
local typeLabel        = gameFrame:WaitForChild("Type", 15)

if not currentWordFrame or not typeLabel then
    setLoadProgress(1, "❌ Missing game elements")
    task.wait(2)
    dismissLoading()
    return
end

setLoadProgress(0.15, "Game UI found!")

local rotated = nil
pcall(function()
    rotated = SoundService:WaitForChild("Game", 5)
    if rotated then rotated = rotated:WaitForChild("Rotated", 5) end
end)

---------------------------------------------------------------------
-- 15. UTILITY FUNCTIONS
---------------------------------------------------------------------
local function S(v)
    return math.floor(v * sf)
end

local function track(conn)
    table.insert(connections, conn)
    return conn
end

local function cleanup()
    isUnloaded = true
    _botTyping = false  -- libère le flag au cas où le script est unload pendant un typage
    for _, c in ipairs(connections) do
        if c and c.Connected then
            pcall(function() c:Disconnect() end)
        end
    end
    connections = {}
    local gui = playerGui:FindFirstChild(SCRIPT_TAG)
    if gui then gui:Destroy() end
    if loadingScreen and loadingScreen.Parent then loadingScreen:Destroy() end
    -- Détruire le sinkBox pour rendre le clavier au joueur
    if sinkGui and sinkGui.Parent then sinkGui:Destroy() end
end

local function getCurrentMode()
    return MODES[currentModeIndex]
end

local function fsSave(name, data)
    if hasFSAccess then
        pcall(function() writefile(name, data) end)
    end
end

local function fsLoad(name)
    if hasFSAccess then
        local ok, result = pcall(function()
            if isfile(name) then
                return readfile(name)
            end
            return nil
        end)
        if ok then return result end
    end
    return nil
end

local function recordWord(word)
    sessionStats.wordsTyped = sessionStats.wordsTyped + 1
    sessionStats.totalChars = sessionStats.totalChars + #word
end

local function getBombTime()
    local ok, val = pcall(function()
        return tonumber(gameFrame.Circle.Timer.Seconds.Text)
    end)
    if ok and val then
        cachedBombTime = val
        return val
    end
    return cachedBombTime
end

local function isUrgent()
    local t = cachedBombTime or getBombTime()
    if t and t <= CONFIG.urgentTimeThreshold then
        return true, t
    end
    return false, t
end

local function detectLayout()
    -- Try reading from the game's in-game Settings UI first
    local fromGame = false
    pcall(function()
        local layoutLabel = playerGui
            :WaitForChild("Settings", 5)
            :WaitForChild("Frame", 3)
            :WaitForChild("Settings", 3)
            :WaitForChild("KeyboardLayout", 3)
            :WaitForChild("Layout", 3)
        if layoutLabel and layoutLabel:IsA("TextLabel") then
            local txt = string.upper(layoutLabel.Text)
            if txt == "AZERTY" then
                curLayout = "AZERTY"
                fromGame = true
            elseif txt == "QWERTZ" then
                curLayout = "QWERTZ"
                fromGame = true
            elseif txt == "QWERTY" then
                curLayout = "QWERTY"
                fromGame = true
            end
        end
    end)
    
    -- Fallback to locale detection if game setting not found
    if not fromGame then
        local ok, locale = pcall(function()
            return string.lower(string.sub(LocalizationService.RobloxLocaleId, 1, 2))
        end)
        if ok then
            if locale == "fr" then
                curLayout = "AZERTY"
            elseif locale == "de" or locale == "cs" or locale == "sk" then
                curLayout = "QWERTZ"
            else
                curLayout = "QWERTY"
            end
        else
            curLayout = "QWERTY"
        end
    end
    return curLayout
end

local function getKC(char)
    local layout = LAYOUTS[curLayout]
    if layout and layout.map and layout.map[char] then
        return layout.map[char]
    end
    local ok, kc = pcall(function() return Enum.KeyCode[char] end)
    if ok and kc then return kc end
    return nil
end

local function buildNearby()
    nearbyKeys = {}
    local layout = LAYOUTS[curLayout]
    if not layout then return nearbyKeys end

    local posMap = {}
    for r, row in ipairs(layout.rows) do
        for c, key in ipairs(row) do
            posMap[key] = {r = r, c = c}
        end
    end

    local dirs = {{-1,-1},{-1,0},{-1,1},{0,-1},{0,1},{1,-1},{1,0},{1,1}}
    local revMap = {}
    for r, row in ipairs(layout.rows) do
        for c, key in ipairs(row) do
            revMap[r .. "," .. c] = key
        end
    end

    for key, pos in pairs(posMap) do
        local neighbors = {}
        for _, d in ipairs(dirs) do
            local nr, nc = pos.r + d[1], pos.c + d[2]
            local neighbor = revMap[nr .. "," .. nc]
            if neighbor then
                table.insert(neighbors, neighbor)
            end
        end
        nearbyKeys[key] = neighbors
    end

    return nearbyKeys
end

local function notify(msg)
    pcall(function()
        StarterGui:SetCore("SendNotification", {
            Title = "Voxxar v5.1.2",
            Text = msg,
            Duration = 3,
        })
    end)
end

local function sendChatMessage(msg)
    local ok = pcall(function()
        ReplicatedStorage.DefaultChatSystemChatEvents.SayMessageRequest:FireServer(msg, "All")
    end)
    if not ok then
        pcall(function()
            TextChatService.TextChannels.RBXGeneral:SendAsync(msg)
        end)
    end
end

---------------------------------------------------------------------
-- 16. WORD CACHE & GAME STATE
---------------------------------------------------------------------
local function invalidateWordCache()
    cachedWordDirty = true
    lastChildHash = -1
end

local function getCurrentWord()
    local children = currentWordFrame:GetChildren()
    local count = #children
    if count == lastChildHash and not cachedWordDirty then
        return cachedWord
    end

    local letters = {}
    local maxIdx = 0
    for _, child in ipairs(children) do
        if child:IsA("Frame") and child.Name ~= "Extra" then
            local idx = tonumber(child.Name)
            if idx then
                local tl = child:FindFirstChildWhichIsA("TextLabel")
                if not tl then
                    tl = child:FindFirstChild("Letter")
                end
                if tl and tl:IsA("TextLabel") then
                    letters[idx] = tl.Text
                    if idx > maxIdx then maxIdx = idx end
                end
            end
        end
    end

    local result = {}
    for i = 1, maxIdx do
        table.insert(result, letters[i] or "")
    end

    cachedWord = table.concat(result)
    cachedWordDirty = false
    lastChildHash = count
    return cachedWord
end

local function getCurPlayer()
    local ok, txt = pcall(function() return typeLabel.Text end)
    if ok and txt then
        local name = string.match(txt, "^(.-),")
        return name or txt
    end
    return nil
end

local function isMyTurn()
    return getCurPlayer() == player.Name
end

---------------------------------------------------------------------
-- 17. KILLER SCORING
---------------------------------------------------------------------
local function killerScore(word)
    if ksCache[word] then return ksCache[word] end

    local score = 0
    local wLower = string.lower(word)

    -- suffix check
    for _, suf in ipairs(DEST_SUFFIXES) do
        if string.sub(wLower, -#suf) == suf then
            score = score + 15
            break
        end
    end

    -- rare bigrams
    for _, bg in ipairs(RARE_BIGRAMS) do
        local i = 1
        while true do
            local f = string.find(wLower, bg, i, true)
            if not f then break end
            score = score + 20
            i = f + 1
        end
    end

    -- length bonus
    local len = #wLower
    if len >= 10 then
        score = score + 10
    elseif len >= 7 then
        score = score + 5
    end

    -- rare letters
    for letter, bonus in pairs(RARE_LETTERS) do
        local count = 0
        for ch in string.gmatch(wLower, letter) do
            count = count + 1
        end
        score = score + bonus * count
    end

    -- frequency penalty
    local freq = wordFreq[wLower] or 0
    if freq > 0.7 then
        score = score - 10
    end

    ksCache[word] = score
    return score
end

local function markDestructive()
    destructiveWords = {}
    for _, w in ipairs(allWords) do
        if killerScore(w) >= 15 then
            destructiveWords[w] = true
        end
    end
end

---------------------------------------------------------------------
-- 18. FREQUENCY HELPERS
---------------------------------------------------------------------
local function getFreqLabel(word)
    local f = wordFreq[word] or 0
    if f >= 0.1 then return "★★★"
    elseif f >= 0.01 then return "★★"
    elseif f >= 0.001 then return "★"
    elseif f > 0 then return "·"
    else return "" end
end

local function getFreqColor(word)
    local f = wordFreq[word] or 0
    if f >= 0.1 then return Color3.fromRGB(255, 215, 0)
    elseif f >= 0.01 then return Color3.fromRGB(255, 170, 50)
    elseif f >= 0.001 then return Color3.fromRGB(200, 200, 100)
    elseif f > 0 then return Color3.fromRGB(0, 255, 150)
    else return Color3.fromRGB(150, 150, 150) end
end

---------------------------------------------------------------------
-- 19. DICTIONARY INDEXING
---------------------------------------------------------------------
local function buildPrefix()
    byPrefix = {}
    byFirstChar = {}
    for _, w in ipairs(allWords) do
        if #w >= 2 then
            local pre = string.sub(w, 1, 2)
            if not byPrefix[pre] then byPrefix[pre] = {} end
            table.insert(byPrefix[pre], w)
        end
        local fc = string.sub(w, 1, 1)
        if not byFirstChar[fc] then byFirstChar[fc] = {} end
        table.insert(byFirstChar[fc], w)
    end
end

---------------------------------------------------------------------
-- 20. WORD SEARCH & SORT
---------------------------------------------------------------------
local function findWords(input)
    if not input or input == "" then return {} end
    local prompt = string.lower(input)
    local candidates

    if #prompt >= 2 then
        local pre = string.sub(prompt, 1, 2)
        candidates = byPrefix[pre]
    else
        local fc = string.sub(prompt, 1, 1)
        candidates = byFirstChar[fc]
    end

    if not candidates then return {} end

    local results = {}
    local mode = getCurrentMode()
    local isTourney = (mode.name == "Tourney")

    for _, w in ipairs(candidates) do
        if string.sub(w, 1, #prompt) == prompt and w ~= prompt and not usedWords[w] and not enemyUsedWords[w] then
            local len = #w
            if isTourney then
                local f = wordFreq[w] or 0
                if f >= 0.001 and len >= 3 and len <= 10 and not destructiveWords[w] then
                    table.insert(results, w)
                end
            else
                if len >= CONFIG.minLength and len <= CONFIG.maxLength then
                    table.insert(results, w)
                end
            end
        end
    end

    return results
end

local function sortWords(words)
    if #words == 0 then return end

    sortScoreCache = {}
    for _, w in ipairs(words) do
        sortScoreCache[w] = wordFreq[w] or 0
    end

    local mode = getCurrentMode()
    local isKiller = (mode.name == "Killer") or destroyerOn

    if isKiller then
        table.sort(words, function(a, b)
            local da, db = destructiveWords[a], destructiveWords[b]
            if da and not db then return true end
            if db and not da then return false end
            if da and db then
                local ka, kb = killerScore(a), killerScore(b)
                if math.abs(ka - kb) > 5 then return ka > kb end
            end
            return (sortScoreCache[a] or 0) < (sortScoreCache[b] or 0)
        end)
    else
        table.sort(words, function(a, b)
            return (sortScoreCache[a] or 0) > (sortScoreCache[b] or 0)
        end)
    end

    sortScoreCache = {}
end

---------------------------------------------------------------------
-- 21. DICTIONARY LOADING
---------------------------------------------------------------------
local function loadDictFromTxt()
    local ok, raw = pcall(function()
        return game:HttpGet(DICT_URL_TXT)
    end)
    if not ok or not raw or raw == "" then
        return false, 0, 0
    end

    local wc, fc = 0, 0
    local entries = {}
    local lineNum = 0

    for line in string.gmatch(raw, "[^\r\n]+") do
        lineNum = lineNum + 1
        if line ~= "" and string.sub(line, 1, 1) ~= "#" and not string.match(line, "^=+$") then
            -- Try format: word frequency (e.g., "hello 12345")
            local word, freqStr = string.match(line, "^(%S+)%s+(%S+)$")
            
            if word and freqStr then
                -- Format with frequency
                local freq = tonumber(freqStr)
                word = string.lower(word)
                if freq and #word >= 2 and #word <= 25 and not commonWords[word] then
                    table.insert(entries, {word = word, freq = freq, lineNum = lineNum})
                end
            else
                -- Try format: just word (e.g., "hello")
                local singleWord = string.match(line, "^(%S+)$")
                if singleWord then
                    singleWord = string.lower(singleWord)
                    if #singleWord >= 2 and #singleWord <= 25 and not commonWords[singleWord] then
                        -- Assign descending frequency based on line position (earlier = higher freq)
                        local estimatedFreq = math.max(1, 1000000 - lineNum)
                        table.insert(entries, {word = singleWord, freq = estimatedFreq, lineNum = lineNum})
                    end
                end
            end
        end
    end

    -- Find max frequency for normalization
    local maxFreqVal = 0
    for _, entry in ipairs(entries) do
        if entry.freq > maxFreqVal then
            maxFreqVal = entry.freq
        end
    end

    -- Now normalize and populate
    for _, entry in ipairs(entries) do
        local normFreq = 0
        if maxFreqVal > 0 then
            normFreq = entry.freq / maxFreqVal
        end
        table.insert(allWords, entry.word)
        wordFreq[entry.word] = normFreq
        wc = wc + 1
        if normFreq > 0 then fc = fc + 1 end
    end

    return true, wc, fc
end

local function loadDict()
    notify("Loading dictionary...")
    setLoadProgress(0.2, "Loading dictionary...")

    allWords = {}
    wordFreq = {}

    -- Try to download fresh version FIRST (always get latest)
    setLoadProgress(0.3, "Downloading dictionary...")
    local success, wc, fc = loadDictFromTxt()
    
    if success and wc > 0 then
        setLoadProgress(0.7, string.format("Downloaded %d words!", wc))
        -- Save to cache for backup
        task.spawn(function()
            fsSave(CACHE_DICT, HttpService:JSONEncode(allWords))
            fsSave(CACHE_FREQ, HttpService:JSONEncode(wordFreq))
        end)
    else
        -- Download failed - fallback to cache
        notify("Download failed, trying cache...")
        setLoadProgress(0.4, "Checking cache...")
        
        local cacheOk = false
        local dRaw = fsLoad(CACHE_DICT)
        local fRaw = fsLoad(CACHE_FREQ)
        if dRaw and fRaw then
            local ok1, dData = pcall(function() return HttpService:JSONDecode(dRaw) end)
            local ok2, fData = pcall(function() return HttpService:JSONDecode(fRaw) end)
            if ok1 and ok2 and type(dData) == "table" and #dData > 100 then
                allWords = dData
                wordFreq = fData
                cacheOk = true
                setLoadProgress(0.7, string.format("Loaded %d words from cache", #allWords))
                notify("Using cached dictionary (old version)")
            end
        end
        
        if not cacheOk then
            setLoadProgress(1, "❌ Failed to load dictionary")
            return false
        end
    end

    setLoadProgress(0.8, "Sorting & indexing...")

    -- Sort by frequency desc, then length asc
    table.sort(allWords, function(a, b)
        local fa, fb = wordFreq[a] or 0, wordFreq[b] or 0
        if fa ~= fb then return fa > fb end
        return #a < #b
    end)

    buildPrefix()

    setLoadProgress(0.9, "Building killer index...")
    markDestructive()

    -- gcinfo() renvoie la mémoire utilisée, mais sur Roblox 
    -- le simple fait d'appeler certaines fonctions de gestion 
    -- ou de laisser le moteur gérer est préférable.
    local memUsage = gcinfo() 
    print("Mémoire utilisée après chargement : " .. memUsage .. " KB")
    -- ancien code : "collectgarbage("collect")"

    dictLoaded = true
    setLoadProgress(1, string.format("✅ %d words loaded!", #allWords))
    notify(string.format("Dictionary loaded: %d words", #allWords))
    return true
end

---------------------------------------------------------------------
-- 22. CREATE GUI
---------------------------------------------------------------------
setLoadProgress(0.12, "Building interface...")

local screenGui = Instance.new("ScreenGui")
screenGui.Name = SCRIPT_TAG
screenGui.DisplayOrder = 999
screenGui.ResetOnSpawn = false
screenGui.Parent = playerGui

---------------------------------------------------------------------
-- 22-SINK. SINKBOX — absorbe les frappes humaines via gameProcessed
-- Principe :
--   • La TextBox est focused EN PERMANENCE  → les frappes humaines
--     font gameProcessed = true  → le jeu les ignore.
--   • Pendant typeWord() le bot fait ReleaseFocus → gameProcessed = false
--     → le jeu les détecte normalement.
--    Pendant ce temps le joueur humain n'a aucun focus → ses touches
--    n'ont aucun effet sur la logique du jeu ──
---------------------------------------------------------------------
local sinkGui = Instance.new("ScreenGui")
sinkGui.Name            = "VoxxarInputSink"
sinkGui.DisplayOrder    = 99998          -- juste sous le loading (99999)
sinkGui.ResetOnSpawn    = false
sinkGui.IgnoreGuiInset  = true
sinkGui.Parent          = playerGui

local sinkBox = Instance.new("TextBox")
sinkBox.Size                   = UDim2.new(0, 1, 0, 1)
sinkBox.Position               = UDim2.new(0, -9999, 0, -9999)  -- hors écran
sinkBox.BackgroundTransparency = 1
sinkBox.TextTransparency       = 1
sinkBox.TextColor3             = Color3.new(0, 0, 0)
sinkBox.Text                   = ""
sinkBox.ClearTextOnFocus       = false   -- ne pas vider à chaque focus
sinkBox.MultiLine              = false
sinkBox.Parent                 = sinkGui

-- Reprend le focus dès que perdu, SAUF si le bot tape en ce moment
local function captureFocus()
    task.defer(function()
        if not _botTyping and not isUnloaded and isMyTurn() then
            sinkBox:CaptureFocus()
        end
    end)
end

-- Re-focus automatique si perdu (clic, menu, etc.)
-- Le guard isMyTurn() dans captureFocus empêche tout re-focus hors-tour
sinkBox.FocusLost:Connect(function()
    captureFocus()
end)

-- Vider le buffer en continu pour éviter l'accumulation de caractères
UserInputService.InputBegan:Connect(function()
    if sinkBox.Text ~= "" then
        sinkBox.Text = ""
    end
end)

-- GUI element references (forward declare all we need)
local header, headerStroke, headerGlow, mainTitle
local btnContainer, modeBtn, modeBtnStroke, autoBtn, autoBtnStroke, autoBtnBg
local resultsFrame
local settingsPanel
local toastFrame, toastStroke, toastLabel
local floatingGhost

---------------------------------------------------------------------
-- 22a. HEADER
---------------------------------------------------------------------
header = Instance.new("Frame")
header.Name = "Header"
header.Size = UDim2.new(0, S(500), 0, S(70))
header.Position = UDim2.new(0.5, -S(250), 0, S(10))
header.BackgroundColor3 = Color3.fromRGB(20, 20, 28)
header.BorderSizePixel = 0
header.Active = true
header.Parent = screenGui

Instance.new("UICorner", header).CornerRadius = UDim.new(0, 16)

headerStroke = Instance.new("UIStroke")
headerStroke.Thickness = 2
headerStroke.Color = Color3.fromRGB(40, 40, 50)
headerStroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
headerStroke.Parent = header

-- Glow
headerGlow = Instance.new("ImageLabel")
headerGlow.Name = "Glow"
headerGlow.Image = "rbxassetid://5028857084"
headerGlow.BackgroundTransparency = 1
headerGlow.ImageColor3 = Color3.fromRGB(0, 200, 255)
headerGlow.ImageTransparency = 0.7
headerGlow.ScaleType = Enum.ScaleType.Slice
headerGlow.SliceCenter = Rect.new(24, 24, 276, 276)
headerGlow.SliceScale = 0.12
headerGlow.Size = UDim2.new(1, 40, 1, 40)
headerGlow.Position = UDim2.new(0, -20, 0, -20)
headerGlow.ZIndex = 0
headerGlow.Parent = header

-- Settings button (top-left)
local settBtn = Instance.new("TextButton")
settBtn.Size = UDim2.new(0, S(40), 0, S(40))
settBtn.Position = UDim2.new(0, S(8), 0.5, -S(20))
settBtn.BackgroundTransparency = 1
settBtn.Text = "⚙"
settBtn.TextColor3 = Color3.fromRGB(180, 180, 190)
settBtn.TextSize = S(22)
settBtn.Font = Enum.Font.GothamBold
settBtn.ZIndex = 5
settBtn.Parent = header

-- Main title (center)
mainTitle = Instance.new("TextLabel")
mainTitle.Name = "MainTitle"
mainTitle.Size = UDim2.new(1, -S(100), 1, 0)
mainTitle.Position = UDim2.new(0, S(50), 0, 0)
mainTitle.BackgroundTransparency = 1
mainTitle.Text = "⏳ LOADING..."
mainTitle.TextColor3 = Color3.fromRGB(255, 255, 255)
mainTitle.TextSize = S(20)
mainTitle.Font = Enum.Font.Arcade
mainTitle.TextTruncate = Enum.TextTruncate.AtEnd
mainTitle.ZIndex = 5
mainTitle.Parent = header

-- Unload button (top-right)
local unloadBtn = Instance.new("TextButton")
unloadBtn.Size = UDim2.new(0, S(40), 0, S(40))
unloadBtn.Position = UDim2.new(1, -S(48), 0.5, -S(20))
unloadBtn.BackgroundTransparency = 1
unloadBtn.Text = "✕"
unloadBtn.TextColor3 = Color3.fromRGB(255, 80, 80)
unloadBtn.TextSize = S(22)
unloadBtn.Font = Enum.Font.GothamBold
unloadBtn.ZIndex = 5
unloadBtn.Parent = header

---------------------------------------------------------------------
-- 22b. HOVER EFFECT
---------------------------------------------------------------------
local function addHoverEffect(btn)
    local origSize = btn.Size
    track(btn.MouseEnter:Connect(function()
        if CONFIG.hoverEffects then
            TweenService:Create(btn, TweenInfo.new(0.15, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
                Size = UDim2.new(
                    origSize.X.Scale * 1.08,
                    math.floor(origSize.X.Offset * 1.08),
                    origSize.Y.Scale * 1.08,
                    math.floor(origSize.Y.Offset * 1.08)
                )
            }):Play()
        end
    end))
    track(btn.MouseLeave:Connect(function()
        if CONFIG.hoverEffects then
            TweenService:Create(btn, TweenInfo.new(0.15, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
                Size = origSize
            }):Play()
        end
    end))
end

---------------------------------------------------------------------
-- 22c. BUTTON CONTAINER
---------------------------------------------------------------------
btnContainer = Instance.new("Frame")
btnContainer.Name = "Buttons"
btnContainer.Size = UDim2.new(1, 0, 0, S(43))
btnContainer.Position = UDim2.new(0, 0, 1, S(5))
btnContainer.BackgroundTransparency = 1
btnContainer.Parent = header

local btnLayout = Instance.new("UIListLayout")
btnLayout.FillDirection = Enum.FillDirection.Horizontal
btnLayout.HorizontalAlignment = Enum.HorizontalAlignment.Center
btnLayout.VerticalAlignment = Enum.VerticalAlignment.Center
btnLayout.Padding = UDim.new(0, S(6))
btnLayout.Parent = btnContainer

local function mkSquareBtn(icon, color, borderColor)
    local btn = Instance.new("TextButton")
    btn.Size = UDim2.new(0, S(43), 0, S(43))
    btn.BackgroundColor3 = Color3.fromRGB(25, 25, 30)
    btn.BorderSizePixel = 0
    btn.Text = icon
    btn.TextColor3 = color
    btn.TextSize = S(20)
    btn.Font = Enum.Font.GothamBold
    btn.Parent = btnContainer

    local stroke = Instance.new("UIStroke")
    stroke.Thickness = 2
    stroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
    stroke.Color = borderColor
    stroke.Parent = btn

    Instance.new("UICorner", btn).CornerRadius = UDim.new(0, 8)
    addHoverEffect(btn)
    return btn, stroke
end

-- Reset button
local resetBtn = mkSquareBtn("🔄", Color3.fromRGB(0, 200, 255), Color3.fromRGB(0, 150, 200))

-- Mode button
modeBtn, modeBtnStroke = mkSquareBtn("✨", Color3.fromRGB(0, 200, 255), Color3.fromRGB(0, 150, 200))

-- Ghost button
local ghostBtn = mkSquareBtn("👻", Color3.fromRGB(180, 100, 255), Color3.fromRGB(140, 60, 200))

-- Help button
local helpBtn = mkSquareBtn("🤝", Color3.fromRGB(100, 200, 255), Color3.fromRGB(70, 150, 200))

-- Auto button (wider)
autoBtn = Instance.new("TextButton")
autoBtn.Size = UDim2.new(0, S(120), 0, S(43))
autoBtn.BackgroundColor3 = Color3.fromRGB(25, 25, 30)
autoBtn.BorderSizePixel = 0
autoBtn.Text = "🔴 OFF"
autoBtn.TextColor3 = Color3.fromRGB(255, 80, 80)
autoBtn.TextSize = S(16)
autoBtn.Font = Enum.Font.GothamBold
autoBtn.Parent = btnContainer

autoBtnStroke = Instance.new("UIStroke")
autoBtnStroke.Thickness = 2
autoBtnStroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
autoBtnStroke.Color = Color3.fromRGB(200, 0, 0)
autoBtnStroke.Parent = autoBtn

Instance.new("UICorner", autoBtn).CornerRadius = UDim.new(0, 8)
addHoverEffect(autoBtn)

---------------------------------------------------------------------
-- 22d. RESULTS FRAME (ScrollingFrame)
---------------------------------------------------------------------
resultsFrame = Instance.new("ScrollingFrame")
resultsFrame.Name = "Results"
resultsFrame.Size = UDim2.new(1, 0, 0, S(250))
resultsFrame.Position = UDim2.new(0, 0, 1, S(55))
resultsFrame.BackgroundColor3 = Color3.fromRGB(15, 15, 20)
resultsFrame.BackgroundTransparency = 1
resultsFrame.BorderSizePixel = 0
resultsFrame.ScrollBarThickness = S(5)
resultsFrame.ScrollBarImageColor3 = Color3.fromRGB(0, 200, 255)
resultsFrame.CanvasSize = UDim2.new(0, 0, 0, 0)
resultsFrame.AutomaticCanvasSize = Enum.AutomaticSize.None
resultsFrame.Parent = header

Instance.new("UICorner", resultsFrame).CornerRadius = UDim.new(0, 12)

---------------------------------------------------------------------
-- 22e. TOAST
---------------------------------------------------------------------
toastFrame = Instance.new("Frame")
toastFrame.Name = "Toast"
toastFrame.Size = UDim2.new(0, S(400), 0, S(80))
toastFrame.Position = UDim2.new(0.5, -S(200), 0, -S(100))
toastFrame.BackgroundColor3 = Color3.fromRGB(15, 15, 20)
toastFrame.BackgroundTransparency = 0.1
toastFrame.BorderSizePixel = 0
toastFrame.Visible = false
toastFrame.ZIndex = 50
toastFrame.Parent = screenGui

Instance.new("UICorner", toastFrame).CornerRadius = UDim.new(0, 12)

toastStroke = Instance.new("UIStroke")
toastStroke.Thickness = 3
toastStroke.Color = Color3.fromRGB(0, 200, 255)
toastStroke.Parent = toastFrame

toastLabel = Instance.new("TextLabel")
toastLabel.Size = UDim2.new(1, -20, 1, -10)
toastLabel.Position = UDim2.new(0, 10, 0, 5)
toastLabel.BackgroundTransparency = 1
toastLabel.TextColor3 = Color3.fromRGB(255, 255, 255)
toastLabel.TextSize = S(24)
toastLabel.Font = Enum.Font.Arcade
toastLabel.TextScaled = true
toastLabel.TextStrokeTransparency = 0
toastLabel.TextStrokeColor3 = Color3.fromRGB(0, 0, 0)
toastLabel.ZIndex = 51
toastLabel.Parent = toastFrame

---------------------------------------------------------------------
-- 22f. FLOATING GHOST BUTTON
---------------------------------------------------------------------
floatingGhost = Instance.new("TextButton")
floatingGhost.Name = "FloatingGhost"
floatingGhost.Size = UDim2.new(0, S(45), 0, S(45))
floatingGhost.Position = UDim2.new(1, -S(60), 0, S(10))
floatingGhost.BackgroundColor3 = Color3.fromRGB(25, 25, 35)
floatingGhost.BorderSizePixel = 0
floatingGhost.Text = "👻"
floatingGhost.TextSize = S(22)
floatingGhost.Font = Enum.Font.GothamBold
floatingGhost.Visible = false
floatingGhost.ZIndex = 100
floatingGhost.Parent = screenGui

Instance.new("UICorner", floatingGhost).CornerRadius = UDim.new(0, 10)

local fgStroke = Instance.new("UIStroke")
fgStroke.Thickness = 2
fgStroke.Color = Color3.fromRGB(140, 60, 200)
fgStroke.Parent = floatingGhost

---------------------------------------------------------------------
-- 22g. SETTINGS PANEL
---------------------------------------------------------------------
settingsPanel = Instance.new("Frame")
settingsPanel.Name = "Settings"
settingsPanel.Size = UDim2.new(0, S(300), 0, S(400))
settingsPanel.Position = UDim2.new(1, S(10), 0, 0)
settingsPanel.BackgroundColor3 = Color3.fromRGB(18, 18, 24)
settingsPanel.BorderSizePixel = 0
settingsPanel.Visible = false
settingsPanel.ZIndex = 20
settingsPanel.Parent = header

Instance.new("UICorner", settingsPanel).CornerRadius = UDim.new(0, 12)

local settStroke = Instance.new("UIStroke")
settStroke.Thickness = 2
settStroke.Color = Color3.fromRGB(60, 60, 80)
settStroke.Parent = settingsPanel

local settTitle = Instance.new("TextLabel")
settTitle.Size = UDim2.new(1, -S(40), 0, S(35))
settTitle.Position = UDim2.new(0, S(10), 0, S(5))
settTitle.BackgroundTransparency = 1
settTitle.Text = "⚙ SETTINGS"
settTitle.TextColor3 = Color3.fromRGB(200, 200, 220)
settTitle.TextSize = S(16)
settTitle.Font = Enum.Font.GothamBold
settTitle.TextXAlignment = Enum.TextXAlignment.Left
settTitle.ZIndex = 21
settTitle.Parent = settingsPanel

local settCloseBtn = Instance.new("TextButton")
settCloseBtn.Size = UDim2.new(0, S(30), 0, S(30))
settCloseBtn.Position = UDim2.new(1, -S(35), 0, S(5))
settCloseBtn.BackgroundTransparency = 1
settCloseBtn.Text = "✕"
settCloseBtn.TextColor3 = Color3.fromRGB(255, 80, 80)
settCloseBtn.TextSize = S(18)
settCloseBtn.Font = Enum.Font.GothamBold
settCloseBtn.ZIndex = 21
settCloseBtn.Parent = settingsPanel

local settScroll = Instance.new("ScrollingFrame")
settScroll.Size = UDim2.new(1, -S(16), 1, -S(45))
settScroll.Position = UDim2.new(0, S(8), 0, S(40))
settScroll.BackgroundTransparency = 1
settScroll.BorderSizePixel = 0
settScroll.ScrollBarThickness = S(4)
settScroll.CanvasSize = UDim2.new(0, 0, 0, 0)
settScroll.AutomaticCanvasSize = Enum.AutomaticSize.Y
settScroll.ZIndex = 21
settScroll.Parent = settingsPanel

local settListLayout = Instance.new("UIListLayout")
settListLayout.FillDirection = Enum.FillDirection.Vertical
settListLayout.Padding = UDim.new(0, S(4))
settListLayout.SortOrder = Enum.SortOrder.LayoutOrder
settListLayout.Parent = settScroll

-- Slider factory
local function mkSlider(label, mn, mx, cur, step, order, cb)
    local container = Instance.new("Frame")
    container.Size = UDim2.new(1, 0, 0, S(45))
    container.BackgroundColor3 = Color3.fromRGB(25, 25, 35)
    container.BackgroundTransparency = 0.5
    container.BorderSizePixel = 0
    container.LayoutOrder = order
    container.ZIndex = 22
    container.Parent = settScroll
    Instance.new("UICorner", container).CornerRadius = UDim.new(0, 6)

    local lbl = Instance.new("TextLabel")
    lbl.Size = UDim2.new(0.55, 0, 0, S(18))
    lbl.Position = UDim2.new(0, S(8), 0, S(3))
    lbl.BackgroundTransparency = 1
    lbl.Text = label
    lbl.TextColor3 = Color3.fromRGB(180, 180, 200)
    lbl.TextSize = S(12)
    lbl.Font = Enum.Font.Gotham
    lbl.TextXAlignment = Enum.TextXAlignment.Left
    lbl.ZIndex = 23
    lbl.Parent = container

    local valLbl = Instance.new("TextLabel")
    valLbl.Size = UDim2.new(0.4, 0, 0, S(18))
    valLbl.Position = UDim2.new(0.55, 0, 0, S(3))
    valLbl.BackgroundTransparency = 1
    valLbl.Text = tostring(cur)
    valLbl.TextColor3 = Color3.fromRGB(0, 200, 255)
    valLbl.TextSize = S(12)
    valLbl.Font = Enum.Font.GothamBold
    valLbl.TextXAlignment = Enum.TextXAlignment.Right
    valLbl.ZIndex = 23
    valLbl.Parent = container

    local track2 = Instance.new("Frame")
    track2.Size = UDim2.new(0.9, 0, 0, S(7))
    track2.Position = UDim2.new(0.05, 0, 0, S(28))
    track2.BackgroundColor3 = Color3.fromRGB(40, 40, 55)
    track2.BorderSizePixel = 0
    track2.ZIndex = 23
    track2.Parent = container
    Instance.new("UICorner", track2).CornerRadius = UDim.new(0, 4)

    local pct = math.clamp((cur - mn) / (mx - mn), 0, 1)

    local fill = Instance.new("Frame")
    fill.Size = UDim2.new(pct, 0, 1, 0)
    fill.BackgroundColor3 = Color3.fromRGB(0, 200, 255)
    fill.BorderSizePixel = 0
    fill.ZIndex = 24
    fill.Parent = track2
    Instance.new("UICorner", fill).CornerRadius = UDim.new(0, 4)

    local knob = Instance.new("Frame")
    knob.Size = UDim2.new(0, S(12), 0, S(12))
    knob.Position = UDim2.new(pct, -S(6), 0.5, -S(6))
    knob.BackgroundColor3 = Color3.fromRGB(255, 255, 255)
    knob.BorderSizePixel = 0
    knob.ZIndex = 25
    knob.Parent = track2
    Instance.new("UICorner", knob).CornerRadius = UDim.new(1, 0)

    local sliderDragging = false

    local function updateSlider(inputPos)
        local trackAbsPos = track2.AbsolutePosition.X
        local trackAbsSize = track2.AbsoluteSize.X
        local rel = math.clamp((inputPos - trackAbsPos) / trackAbsSize, 0, 1)
        local raw = mn + rel * (mx - mn)
        local snapped = math.floor(raw / step + 0.5) * step
        snapped = math.clamp(snapped, mn, mx)
        -- Round to avoid float artifacts
        local decimals = 0
        local stepStr = tostring(step)
        local dotPos = string.find(stepStr, "%.")
        if dotPos then decimals = #stepStr - dotPos end
        snapped = tonumber(string.format("%." .. decimals .. "f", snapped))

        local newPct = math.clamp((snapped - mn) / (mx - mn), 0, 1)
        fill.Size = UDim2.new(newPct, 0, 1, 0)
        knob.Position = UDim2.new(newPct, -S(6), 0.5, -S(6))
        valLbl.Text = tostring(snapped)
        cb(snapped)
    end

    track(track2.InputBegan:Connect(function(input)
        if input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch then
            sliderDragging = true
            updateSlider(input.Position.X)
        end
    end))

    track(knob.InputBegan:Connect(function(input)
        if input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch then
            sliderDragging = true
        end
    end))

    track(UserInputService.InputChanged:Connect(function(input)
        if sliderDragging and (input.UserInputType == Enum.UserInputType.MouseMovement or input.UserInputType == Enum.UserInputType.Touch) then
            updateSlider(input.Position.X)
        end
    end))

    track(UserInputService.InputEnded:Connect(function(input)
        if input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch then
            sliderDragging = false
        end
    end))
end

-- Toggle factory
local function mkToggle(label, default, order, cb)
    local container = Instance.new("Frame")
    container.Size = UDim2.new(1, 0, 0, S(35))
    container.BackgroundColor3 = Color3.fromRGB(25, 25, 35)
    container.BackgroundTransparency = 0.5
    container.BorderSizePixel = 0
    container.LayoutOrder = order
    container.ZIndex = 22
    container.Parent = settScroll
    Instance.new("UICorner", container).CornerRadius = UDim.new(0, 6)

    local lbl = Instance.new("TextLabel")
    lbl.Size = UDim2.new(0.7, 0, 1, 0)
    lbl.Position = UDim2.new(0, S(8), 0, 0)
    lbl.BackgroundTransparency = 1
    lbl.Text = label
    lbl.TextColor3 = Color3.fromRGB(180, 180, 200)
    lbl.TextSize = S(12)
    lbl.Font = Enum.Font.Gotham
    lbl.TextXAlignment = Enum.TextXAlignment.Left
    lbl.ZIndex = 23
    lbl.Parent = container

    local state = default
    local btn = Instance.new("TextButton")
    btn.Size = UDim2.new(0, S(50), 0, S(22))
    btn.Position = UDim2.new(1, -S(58), 0.5, -S(11))
    btn.BackgroundColor3 = state and Color3.fromRGB(0, 180, 80) or Color3.fromRGB(180, 40, 40)
    btn.BorderSizePixel = 0
    btn.Text = state and "ON" or "OFF"
    btn.TextColor3 = Color3.fromRGB(255, 255, 255)
    btn.TextSize = S(11)
    btn.Font = Enum.Font.GothamBold
    btn.ZIndex = 23
    btn.Parent = container
    Instance.new("UICorner", btn).CornerRadius = UDim.new(0, 6)

    track(btn.MouseButton1Click:Connect(function()
        state = not state
        btn.Text = state and "ON" or "OFF"
        btn.BackgroundColor3 = state and Color3.fromRGB(0, 180, 80) or Color3.fromRGB(180, 40, 40)
        cb(state)
    end))
end

-- Create settings controls
mkSlider("Typing Speed", 0.03, 0.2, CONFIG.typingSpeed, 0.01, 1, function(v) CONFIG.typingSpeed = v end)
mkSlider("Typo %", 0, 30, math.floor(CONFIG.typoChance * 100), 1, 2, function(v) CONFIG.typoChance = v / 100 end)
mkSlider("Auto Delay", 0.1, 2.0, CONFIG.fullAutoDelay, 0.1, 3, function(v) CONFIG.fullAutoDelay = v end)
mkToggle("Ability Notifs", abilityOn, 4, function(v) abilityOn = v end)
mkToggle("Match Auto-Reset", CONFIG.matchAutoReset, 5, function(v) CONFIG.matchAutoReset = v end)
mkToggle("Hover Effects", CONFIG.hoverEffects, 6, function(v) CONFIG.hoverEffects = v end)
mkToggle("Glow Effect", CONFIG.glowEnabled, 7, function(v) CONFIG.glowEnabled = v; if not v then headerGlow.ImageTransparency = 1 end end)
mkToggle("Reactive Header", CONFIG.headerReactive, 8, function(v) CONFIG.headerReactive = v end)

---------------------------------------------------------------------
-- 23. LABEL POOL
---------------------------------------------------------------------
local function getLabel(parent)
    local l
    if #labelPool > 0 then
        l = table.remove(labelPool)
    else
        l = Instance.new("TextLabel")
        l.BackgroundTransparency = 1
        l.Font = Enum.Font.Arcade
        l.TextStrokeTransparency = 0
        l.TextStrokeColor3 = Color3.fromRGB(0, 0, 0)
    end
    l.TextTransparency = 1
    l.TextStrokeTransparency = 1
    l.Visible = true
    l.Parent = parent
    table.insert(activeLabels, l)
    return l
end

local function recycleLabels()
    for _, l in ipairs(activeLabels) do
        l.Visible = false
        l.Parent = nil
        -- Remove any gradients AND click buttons
        for _, child in ipairs(l:GetChildren()) do
            if child:IsA("UIGradient") or child:IsA("TextButton") then
                child:Destroy()
            end
        end
        table.insert(labelPool, l)
    end
    activeLabels = {}
end

---------------------------------------------------------------------
-- 24. ANIMATION HELPERS
---------------------------------------------------------------------
local function tweenIn(l, d)
    l.TextTransparency = 1
    l.TextStrokeTransparency = 1
    local origPos = l.Position
    l.Position = origPos + UDim2.new(0, 0, 0, 6)
    task.delay(d, function()
        if l and l.Parent then
            TweenService:Create(l, TweenInfo.new(0.18, Enum.EasingStyle.Quart, Enum.EasingDirection.Out), {
                TextTransparency = 0,
                TextStrokeTransparency = 0,
                Position = origPos,
            }):Play()
        end
    end)
end

local function showInstant(l)
    l.TextTransparency = 0
    l.TextStrokeTransparency = 0
end

---------------------------------------------------------------------
-- 25. GRADIENT HELPER
---------------------------------------------------------------------
local function applyGradient(label, word)
    for _, child in ipairs(label:GetChildren()) do
        if child:IsA("UIGradient") then child:Destroy() end
    end

    local mode = getCurrentMode()
    local isKiller = (mode.name == "Killer") or destroyerOn
    local f = wordFreq[word] or 0
    local grad

    if isKiller and destructiveWords[word] then
        grad = Instance.new("UIGradient")
        grad.Color = ColorSequence.new({
            ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 50, 50)),
            ColorSequenceKeypoint.new(1, Color3.fromRGB(180, 50, 255)),
        })
    elseif f >= 0.1 then
        grad = Instance.new("UIGradient")
        grad.Color = ColorSequence.new({
            ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 230, 100)),
            ColorSequenceKeypoint.new(0.5, Color3.fromRGB(255, 200, 50)),
            ColorSequenceKeypoint.new(1, Color3.fromRGB(255, 170, 0)),
        })
    elseif f >= 0.01 then
        grad = Instance.new("UIGradient")
        grad.Color = ColorSequence.new({
            ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 190, 80)),
            ColorSequenceKeypoint.new(1, Color3.fromRGB(255, 150, 30)),
        })
    end

    if grad then
        grad.Parent = label
    end
end

---------------------------------------------------------------------
-- 26. HEADER REACTIVE & GLOW
---------------------------------------------------------------------
local lastReactiveColor = Color3.fromRGB(40, 40, 50)

local function updateHeaderReactive()
    if isUnloaded then return end
    if not CONFIG.headerReactive then
        if headerStroke.Color ~= Color3.fromRGB(40, 40, 50) then
            TweenService:Create(headerStroke, TweenInfo.new(0.3, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
                Color = Color3.fromRGB(40, 40, 50)
            }):Play()
        end
        return
    end

    local targetColor
    local urgent, _ = isUrgent()
    local myTurn = isMyTurn()
    local mode = getCurrentMode()

    if urgent and myTurn then
        -- Flash effect
        if math.floor(os.clock() * 4) % 2 == 0 then
            targetColor = Color3.fromRGB(200, 30, 30)
        else
            targetColor = Color3.fromRGB(80, 15, 15)
        end
    elseif mode.name == "Killer" or destroyerOn then
        targetColor = Color3.fromRGB(150, 20, 20)
    elseif autoMode == 2 then
        targetColor = Color3.fromRGB(20, 150, 20)
    elseif autoMode == 0 then
        targetColor = Color3.fromRGB(50, 50, 55)
    else
        targetColor = mode.borderColor
    end

    if targetColor ~= lastReactiveColor then
        lastReactiveColor = targetColor
        TweenService:Create(headerStroke, TweenInfo.new(0.3, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
            Color = targetColor
        }):Play()
    end
end

-- Glow pulse loop
task.spawn(function()
    while glowPulseRunning and not isUnloaded do
        if CONFIG.glowEnabled and headerGlow and headerGlow.Parent then
            TweenService:Create(headerGlow, TweenInfo.new(1.5, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut), {
                ImageTransparency = 0.5
            }):Play()
            task.wait(1.5)
            if isUnloaded then break end
            TweenService:Create(headerGlow, TweenInfo.new(1.5, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut), {
                ImageTransparency = 0.85
            }):Play()
            task.wait(1.5)
        else
            task.wait(1)
        end
    end
end)

---------------------------------------------------------------------
-- 27. TOAST
---------------------------------------------------------------------
local function showToast(word)
    if not CONFIG.ghostMode or not word or word == "" then return end

    local mode = getCurrentMode()
    local isKiller = (mode.name == "Killer") or destroyerOn
    local txt, col

    if isKiller and destructiveWords[word] then
        local ks = killerScore(word)
        txt = "💀 " .. string.upper(word) .. " [K:" .. ks .. "]"
        col = Color3.fromRGB(0, 255, 80)
    else
        txt = string.upper(word) .. " " .. getFreqLabel(word)
        col = getFreqColor(word)
    end

    toastLabel.Text = txt
    toastLabel.TextColor3 = col
    toastStroke.Color = col
    toastFrame.Visible = true
    toastVis = true

    TweenService:Create(toastFrame, TweenInfo.new(0.3, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {
        Position = UDim2.new(0.5, -S(200), 0, S(15))
    }):Play()

    if toastThread then
        pcall(function() task.cancel(toastThread) end)
    end

    toastThread = task.delay(CONFIG.toastDuration, function()
        if toastVis then
            TweenService:Create(toastFrame, TweenInfo.new(0.25, Enum.EasingStyle.Quad, Enum.EasingDirection.In), {
                Position = UDim2.new(0.5, -S(200), 0, -S(100))
            }):Play()
            task.wait(0.25)
            toastFrame.Visible = false
            toastVis = false
        end
    end)
end

local function hideToast()
    if toastVis then
        if toastThread then
            pcall(function() task.cancel(toastThread) end)
            toastThread = nil
        end
        TweenService:Create(toastFrame, TweenInfo.new(0.2, Enum.EasingStyle.Quad, Enum.EasingDirection.In), {
            Position = UDim2.new(0.5, -S(200), 0, -S(100))
        }):Play()
        task.delay(0.2, function()
            toastFrame.Visible = false
            toastVis = false
        end)
    end
end

---------------------------------------------------------------------
-- 28. GHOST MODE
---------------------------------------------------------------------
local function applyGhost()
    if CONFIG.ghostMode then
        header.Visible = false
        toastFrame.Visible = false
        floatingGhost.Visible = true
    else
        header.Visible = true
        floatingGhost.Visible = false
        hideToast()
    end
end

---------------------------------------------------------------------
-- 29. AUTO BUTTON
---------------------------------------------------------------------
local function updateAutoBtn()
    if autoMode == 0 then
        autoBtn.Text = "🔴 OFF"
        autoBtn.TextColor3 = Color3.fromRGB(255, 80, 80)
        autoBtnStroke.Color = Color3.fromRGB(200, 0, 0)
        autoBtn.BackgroundColor3 = Color3.fromRGB(25, 25, 30)
    elseif autoMode == 1 then
        autoBtn.Text = "🟡 SEMI"
        autoBtn.TextColor3 = Color3.fromRGB(255, 220, 50)
        autoBtnStroke.Color = Color3.fromRGB(200, 170, 0)
        autoBtn.BackgroundColor3 = Color3.fromRGB(25, 25, 30)
    else
        autoBtn.Text = "🟢 FULL"
        autoBtn.TextColor3 = Color3.fromRGB(80, 255, 80)
        autoBtnStroke.Color = Color3.fromRGB(0, 200, 0)
        autoBtn.BackgroundColor3 = Color3.fromRGB(25, 25, 30)
    end
    updateHeaderReactive()
end

---------------------------------------------------------------------
-- 30. MODE APPLICATION
---------------------------------------------------------------------
local function applyMode()
    local mode = getCurrentMode()
    modeBtn.Text = mode.icon
    modeBtn.TextColor3 = mode.color
    modeBtnStroke.Color = mode.borderColor

    if mode.name == "Normal" then
        destroyerOn = false
        CONFIG.typingSpeed = 0.082
        CONFIG.typoChance = 0.08
    elseif mode.name == "Survie" then
        destroyerOn = false
        CONFIG.typingSpeed = 0.03
        CONFIG.typoChance = 0
    elseif mode.name == "Tourney" then
        destroyerOn = false
        CONFIG.typingSpeed = 0.06
        CONFIG.typoChance = 0.05
    elseif mode.name == "Killer" then
        destroyerOn = true
        CONFIG.typingSpeed = 0.082
        CONFIG.typoChance = 0.08
    end

    notify("Mode: " .. mode.icon .. " " .. mode.name)
    updateHeaderReactive()

    if dictLoaded and updateResults then
        updateResults()
    end
end

---------------------------------------------------------------------
-- 31. TYPING SYSTEM
---------------------------------------------------------------------

-- Sends N unconditional backspaces to the game input
local function forceBackspace(count)
    for _ = 1, count do
        VirtualInputManager:SendKeyEvent(true, Enum.KeyCode.Backspace, false, game)
        task.wait(CONFIG.retryBackspaceSpeed)
        VirtualInputManager:SendKeyEvent(false, Enum.KeyCode.Backspace, false, game)
        task.wait(0.08 + math.random() * 0.04)
    end
end

-- Clears all typed text back to the prompt.
-- Uses cachedPromptLen (captured at turn start) to know how many
-- characters the player typed beyond the prompt.
local function clearBackspace()
    -- Read current word length from frames
    invalidateWordCache()
    local curW = getCurrentWord()
    local typed = #curW - cachedPromptLen
    if typed > 0 then
        forceBackspace(typed + 5) -- +5 safety margin
    end
    task.wait(0.25)
end

local function typeWord(word, curInput)
    -- curInput = the prompt string (e.g. "so")
    -- word = the full word to type (e.g. "something")
    -- We only need to type the part AFTER the prompt
    local rem = string.sub(word, #curInput + 1)
    if rem == "" then return true end

    -- ── SinkBox : libère le focus AVANT de taper
    --    → les frappes VirtualInputManager arrivent avec gameProcessed=false
    --    → le jeu les détecte normalement.
    --    Pendant ce temps le joueur humain n'a aucun focus → ses touches
    --    n'ont aucun effet sur la logique du jeu ──
    _botTyping = true
    sinkBox:ReleaseFocus(false)
    task.wait(0.02)  -- laisser le focus se libérer complètement

    -- Click to focus game input
    local vpSize = workspace.CurrentCamera.ViewportSize
    local cx, cy = math.floor(vpSize.X / 2), math.floor(vpSize.Y / 2)
    for _ = 1, 3 do
        VirtualInputManager:SendMouseButtonEvent(cx, cy, 0, true, game, 1)
        VirtualInputManager:SendMouseButtonEvent(cx, cy, 0, false, game, 1)
        task.wait(0.02)
    end

    local urgent, _ = isUrgent()
    local mode = getCurrentMode()
    local speed = CONFIG.typingSpeed
    if urgent or mode.name == "Survie" then
        speed = CONFIG.urgentTypingSpeed
    end
    local typoChance = CONFIG.typoChance
    local remLen = #rem

    for i = 1, remLen do
        if isUnloaded then
            -- Nettoyage de sécurité si le script est déchargé en plein typage
            _botTyping = false
            captureFocus()
            return false
        end
        local ch = string.upper(string.sub(rem, i, i))
        local delay = speed + math.random() * 0.020

        -- Typo simulation
        if typoChance > 0 and not urgent and math.random() < typoChance then
            local neighbors = nearbyKeys[ch]
            if neighbors and #neighbors > 0 then
                local wrongChar = neighbors[math.random(#neighbors)]
                local wrongKC = getKC(wrongChar)
                if wrongKC then
                    VirtualInputManager:SendKeyEvent(true, wrongKC, false, game)
                    task.wait(delay)
                    VirtualInputManager:SendKeyEvent(false, wrongKC, false, game)
                    task.wait(0.1 + math.random() * 0.1)
                    VirtualInputManager:SendKeyEvent(true, Enum.KeyCode.Backspace, false, game)
                    task.wait(0.08 + math.random() * 0.04)
                    VirtualInputManager:SendKeyEvent(false, Enum.KeyCode.Backspace, false, game)
                    task.wait(0.08 + math.random() * 0.04)
                end
            end
        end

        local kc = getKC(ch)
        if kc then
            VirtualInputManager:SendKeyEvent(true, kc, false, game)
            task.wait(delay)
            VirtualInputManager:SendKeyEvent(false, kc, false, game)
        end
    end

    -- Press Enter to submit
    task.wait(0.1)
    VirtualInputManager:SendKeyEvent(true, Enum.KeyCode.Return, false, game)
    task.wait(0.05)
    VirtualInputManager:SendKeyEvent(false, Enum.KeyCode.Return, false, game)

    -- ── SinkBox : reprend le focus → le joueur humain est re-bloqué ──
    _botTyping = false
    captureFocus()

    return true
end

-- Waits up to 1.5s after submitting a word.
-- Returns true if the word was ACCEPTED (turn changed).
-- Returns false if the word was REJECTED (still our turn).
local function waitForWordResult(word)
    for _ = 1, 15 do -- 15 * 0.1s = 1.5s max
        task.wait(0.1)

        -- Turn changed → word was accepted by the game
        if not isMyTurn() then
            return true
        end
    end

    -- 1.5s elapsed, still our turn → rejected
    return false
end

local function autoType(word, curInput)
    if autoTypeLock then return end
    autoTypeLock = true

    -- Track as pending — do NOT add to usedWords yet.
    -- The snapshot system in onTurn() will validate it.
    pendingWord = string.lower(word)

    task.spawn(function()
        local success = typeWord(word, curInput)

        if success then
            -- Wait for game response
            local accepted = waitForWordResult(word)
            if accepted then
                -- Word went through, turn changed. We're done.
                retryBlacklist = {}
                autoTypeLock = false
                return
            end
        end

        -- Word was rejected or typeWord failed → clean up and retry
        if not isMyTurn() then
            retryBlacklist = {}
            autoTypeLock = false
            return
        end

        -- Blacklist the failed word
        retryBlacklist[string.lower(word)] = true

        for attempt = 1, CONFIG.retryMaxAttempts do
            if isUnloaded then break end
            if not isMyTurn() then break end

            -- Force-clear all typed text before retrying (réduit de 30 à 15)
            forceBackspace(15)
            task.wait(0.25)

            if not isMyTurn() then break end

            -- Read fresh prompt
            invalidateWordCache()
            local curPrompt = string.lower(getCurrentWord())
            if curPrompt == "" then break end

            -- Recapture prompt length for the cleared state
            cachedPromptLen = #curPrompt

            local newWords = findWords(curPrompt)
            sortWords(newWords)

            local picked = nil
            for _, w in ipairs(newWords) do
                if not retryBlacklist[w] and not usedWords[w] then
                    picked = w
                    break
                end
            end

            if not picked then break end

            -- Track as pending — snapshot system validates
            pendingWord = picked

            if dictLoaded then updateResults() end

            local s = typeWord(picked, curPrompt)
            if s then
                local accepted = waitForWordResult(picked)
                if accepted then
                    break -- Success → exit retry loop
                end
            end

            retryBlacklist[picked] = true
        end

        retryBlacklist = {}
        autoTypeLock = false
    end)
end

---------------------------------------------------------------------
-- 32. CLEAR CLICKS
---------------------------------------------------------------------
local function clearClicks()
    for _, c in ipairs(clickConns) do
        if c and c.Connected then pcall(function() c:Disconnect() end) end
    end
    clickConns = {}
end

---------------------------------------------------------------------
-- 33. DISPLAY WORDS
---------------------------------------------------------------------
displayWords = function(mx)
    -- Protection contre les appels simultanés - retour immédiat si déjà en cours
    if isDisplaying then return end
    isDisplaying = true
    
    -- S'assurer que le flag est toujours libéré, même en cas d'erreur
    local success, err = pcall(function()
    
    clearClicks()
    recycleLabels()

    -- Remove old MORE button and any leftover UI elements
    local oldMore = resultsFrame:FindFirstChild("MoreBtn")
    if oldMore then oldMore:Destroy() end
    
    -- Clean up any remaining children in resultsFrame (safety cleanup)
    for _, child in ipairs(resultsFrame:GetChildren()) do
        if child:IsA("TextLabel") or child:IsA("TextButton") or child:IsA("Frame") then
            if child.Name ~= "MoreBtn" then
                child:Destroy()
            end
        end
    end

    local maxShow = mx or CONFIG.maxWordsDisplay
    local show = math.min(maxShow, #topWords)
    displayedCount = show

    -- Update title
    if show > 0 then
        local best = topWords[1]
        local mode = getCurrentMode()
        local isKiller = (mode.name == "Killer") or destroyerOn

        if isKiller and destructiveWords[best] then
            local ks = killerScore(best)
            mainTitle.Text = mode.icon .. " 💀 " .. string.upper(best) .. " [K:" .. ks .. "]"
            mainTitle.TextColor3 = Color3.fromRGB(255, 80, 80)
        else
            mainTitle.Text = mode.icon .. " " .. string.upper(best) .. " " .. getFreqLabel(best)
            mainTitle.TextColor3 = getFreqColor(best)
        end
    else
        mainTitle.Text = "NO MATCH"
        mainTitle.TextColor3 = Color3.fromRGB(150, 150, 150)
    end

    local yOff = 0
    local szH = S(28) + 8

    for i = 1, show do
        local w = topWords[i]
        local l = getLabel(resultsFrame)
        l.Size = UDim2.new(1, -S(10), 0, szH)
        l.Position = UDim2.new(0, S(5), 0, yOff)
        l.TextSize = S(14)
        l.TextXAlignment = Enum.TextXAlignment.Center
        l.ZIndex = 5

        local mode = getCurrentMode()
        local isKiller = (mode.name == "Killer") or destroyerOn

        if usedWords[w] then
            l.Text = "✓ " .. string.upper(w)
            l.TextColor3 = Color3.fromRGB(80, 80, 80)
        elseif isKiller and destructiveWords[w] then
            local ks = killerScore(w)
            l.Text = "💀 " .. string.upper(w) .. " [K:" .. ks .. "]"
            l.TextColor3 = Color3.fromRGB(0, 255, 80)
            applyGradient(l, w)
        else
            l.Text = string.upper(w) .. " " .. getFreqLabel(w)
            l.TextColor3 = getFreqColor(w)
            applyGradient(l, w)
        end

        -- Animation
        if i <= CONFIG.animMaxTweens then
            tweenIn(l, CONFIG.animBaseDelay + (i - 1) * CONFIG.animStepDelay)
        else
            showInstant(l)
        end

        -- Click to auto-type (works in OFF and SEMI mode too)
        if not usedWords[w] then
            -- Make label clickable by adding a transparent button on top
            local clickBtn = Instance.new("TextButton")
            clickBtn.Size = UDim2.new(1, 0, 1, 0)
            clickBtn.BackgroundTransparency = 1
            clickBtn.Text = ""
            clickBtn.ZIndex = l.ZIndex + 1
            clickBtn.Parent = l

            local conn = clickBtn.MouseButton1Click:Connect(function()
                if not usedWords[w] then
                    local prompt = string.lower(getCurrentWord())
                    autoType(w, prompt)
                end
            end)
            table.insert(clickConns, conn)
        end

        yOff = yOff + szH + 6
    end

    -- MORE button
    if show < #topWords then
        local moreBtn = Instance.new("TextButton")
        moreBtn.Name = "MoreBtn"
        moreBtn.Size = UDim2.new(1, -S(10), 0, S(30))
        moreBtn.Position = UDim2.new(0, S(5), 0, yOff)
        moreBtn.BackgroundColor3 = Color3.fromRGB(30, 30, 40)
        moreBtn.BackgroundTransparency = 1
        moreBtn.BorderSizePixel = 0
        moreBtn.Text = "▼ MORE (" .. (#topWords - show) .. ")"
        moreBtn.TextColor3 = Color3.fromRGB(0, 200, 255)
        moreBtn.TextSize = S(13)
        moreBtn.Font = Enum.Font.GothamBold
        moreBtn.ZIndex = 5
        moreBtn.Parent = resultsFrame
        Instance.new("UICorner", moreBtn).CornerRadius = UDim.new(0, 8)

        local mc = moreBtn.MouseButton1Click:Connect(function()
            displayWords(show + CONFIG.batchLoadSize)
        end)
        table.insert(clickConns, mc)

        yOff = yOff + S(30) + 6
    end

    -- Update canvas
    local targetCanvas = UDim2.new(0, 0, 0, yOff + 10)
    if CONFIG.smoothScroll then
        TweenService:Create(resultsFrame, TweenInfo.new(0.2, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
            CanvasSize = targetCanvas
        }):Play()
    else
        resultsFrame.CanvasSize = targetCanvas
    end

    -- Scroll to top
    if CONFIG.smoothScroll then
        TweenService:Create(resultsFrame, TweenInfo.new(0.15), {CanvasPosition = Vector2.new(0, 0)}):Play()
    else
        resultsFrame.CanvasPosition = Vector2.new(0, 0)
    end

    end) -- Fin du pcall
    
    -- Libérer le flag d'affichage (toujours exécuté, même en cas d'erreur)
    isDisplaying = false
    
    -- Si erreur, l'afficher
    if not success then
        warn("[Voxxar] displayWords error: " .. tostring(err))
    end
end

---------------------------------------------------------------------
-- 34. UPDATE RESULTS
---------------------------------------------------------------------
updateResults = function(force)
    if not dictLoaded then return end
    if isDisplaying and not force then return end -- Déjà en cours d'affichage

    invalidateWordCache()
    local prompt = string.lower(getCurrentWord())
    
    -- Skip si le prompt n'a pas changé (sauf si force=true)
    if prompt == lastDisplayedPrompt and not force then
        return
    end
    lastDisplayedPrompt = prompt

    if prompt == "" then
        topWords = {}
        displayWords()
        mainTitle.Text = "WAITING..."
        mainTitle.TextColor3 = Color3.fromRGB(150, 150, 150)
        hideToast()
        return
    end

    topWords = findWords(prompt)
    sortWords(topWords)
    displayWords()

    if isMyTurn() and #topWords > 0 then
        showToast(topWords[1])
    end
end

---------------------------------------------------------------------
-- 35. FULL AUTO
---------------------------------------------------------------------
fullAuto = function()
    if isUnloaded or autoMode ~= 2 or not isMyTurn() or fullAutoLock then return end
    fullAutoLock = true

    task.spawn(function()
        invalidateWordCache()
        local prompt = string.lower(getCurrentWord())
        if prompt == "" then
            fullAutoLock = false
            return
        end

        -- For Last Letter mode, we might need different logic
        local gamemode = detectGamemode()
        local isLastLetter = (gamemode == "Last Letter")

        local words = findWords(prompt)
        if #words == 0 then
            fullAutoLock = false
            return
        end

        local chosen
        local urgent, _ = isUrgent()

        if urgent then
            -- Pick shortest word
            chosen = words[1]
            for _, w in ipairs(words) do
                if #w < #chosen then chosen = w end
            end
        elseif isLastLetter then
            -- For Last Letter, prefer words ending with rare letters
            sortWords(words)
            -- Find word that ends with a letter that creates difficult prompts
            for _, w in ipairs(words) do
                if not usedWords[w] and not enemyUsedWords[w] then
                    chosen = w
                    break
                end
            end
            if not chosen then
                chosen = words[1]
            end
        else
            sortWords(words)
            chosen = words[1]
        end

        if chosen then
            showToast(chosen)
            -- Do NOT add to usedWords here.
            -- The snapshot system in onTurn() validates after turn change.
            autoType(chosen, prompt)
        end

        task.wait(0.5)
        fullAutoLock = false
    end)
end

---------------------------------------------------------------------
-- 36. TURN DETECTION
---------------------------------------------------------------------
local function onTurn()
    invalidateWordCache()

    -- Detect gamemode at turn start
    detectGamemode()

    -- ── Snapshot-based UsedWords validation ──
    local currentTurnPlayer = getCurPlayer()
    local currentWord = string.lower(getCurrentWord())

    if prevTurnPlayer ~= nil and currentTurnPlayer ~= prevTurnPlayer then
        -- TURN CHANGED - capture what happened
        
        -- Case 1: It was our turn, now it's not → our word was accepted
        if prevTurnPlayer == player.Name and currentTurnPlayer ~= player.Name then
            if pendingWord and pendingWord ~= "" then
                usedWords[pendingWord] = true
                recordWord(pendingWord)
                print("[Voxxar] ✓ Our word used: " .. pendingWord)
            end
            -- Also capture enemy's word from the display (what they typed)
            if prevSnapshotWord and #prevSnapshotWord >= 3 and prevSnapshotWord ~= pendingWord then
                enemyUsedWords[prevSnapshotWord] = true
                usedWords[prevSnapshotWord] = true
                print("[Voxxar] ✓ Enemy word captured: " .. prevSnapshotWord)
            end
        end
        
        -- Case 2: It was enemy's turn, now it's ours → enemy's word was accepted
        if prevTurnPlayer ~= player.Name and currentTurnPlayer == player.Name then
            -- prevSnapshotWord contains what was displayed when enemy was playing
            if prevSnapshotWord and #prevSnapshotWord >= 3 then
                enemyUsedWords[prevSnapshotWord] = true
                usedWords[prevSnapshotWord] = true
                print("[Voxxar] ✓ Enemy word used: " .. prevSnapshotWord)
            end
        end
        
        pendingWord = nil
    end

    -- Update snapshot state for next comparison
    prevSnapshotWord = currentWord
    prevTurnPlayer = currentTurnPlayer

    -- Force unlock all locks
    autoTypeLock = false
    fullAutoLock = false
    retryBlacklist = {}

    if isMyTurn() then
        task.wait(0.05)
        if not isMyTurn() then return end

        -- Capture prompt length NOW, before any typing happens.
        invalidateWordCache()
        cachedPromptLen = #getCurrentWord()

        -- ── SinkBox ON : c'est notre tour, on bloque le clavier humain ──
        captureFocus()

        updateResults()

        -- ── Refresh loop : met à jour la liste toutes les 0.5s tant que
        --    c'est notre tour (le prompt peut changer en cours de partie) ──
        -- Annuler l'ancienne boucle si elle existe encore
        if refreshThread then
            pcall(function() task.cancel(refreshThread) end)
        end
        refreshThread = task.spawn(function()
            while isMyTurn() and not isUnloaded do
                task.wait(0.5)
                if isMyTurn() and not isUnloaded and not autoTypeLock then
                    -- Vérifier si le prompt a vraiment changé avant de mettre à jour
                    local currentPrompt = string.lower(getCurrentWord())
                    if currentPrompt ~= lastDisplayedPrompt then
                        updateResults()
                    end
                end
            end
            refreshThread = nil
        end)

        -- Auto-play for Last Letter mode
        if shouldAutoPlay() then
            task.delay(CONFIG.fullAutoDelay, function()
                if isMyTurn() and shouldAutoPlay() then
                    fullAuto()
                end
            end)
        elseif autoMode == 2 then
            task.delay(CONFIG.fullAutoDelay, function()
                if isMyTurn() and autoMode == 2 then
                    fullAuto()
                end
            end)
        end
    else
        -- ── SinkBox OFF : ce n'est plus notre tour, on rend le clavier ──
        _botTyping = false
        sinkBox:ReleaseFocus(false)
        hideToast()
    end
end

---------------------------------------------------------------------
-- 37. LETTER WATCHING
---------------------------------------------------------------------
local function watchLetter(child)
    if not child:IsA("Frame") or child.Name == "Extra" then return end

    local tl = child:FindFirstChildWhichIsA("TextLabel")
    if not tl then
        tl = child:FindFirstChild("Letter")
    end
    if not tl or not tl:IsA("TextLabel") then return end

    if letterConns[child] then
        pcall(function() letterConns[child]:Disconnect() end)
    end

    letterConns[child] = track(tl:GetPropertyChangedSignal("Text"):Connect(function()
        invalidateWordCache()
        autoTypeLock = false
        fullAutoLock = false

        if isMyTurn() then
            updateResults()
            if autoMode == 2 then
                task.delay(CONFIG.fullAutoDelay, function()
                    if isMyTurn() and autoMode == 2 then
                        fullAuto()
                    end
                end)
            end
        end
    end))
end

---------------------------------------------------------------------
-- 38. ABILITY WATCHING
---------------------------------------------------------------------
local function watchChar(tp)
    if not abilityOn then return end

    task.spawn(function()
        local char = tp.Character or tp.CharacterAdded:Wait()
        local torso = char:WaitForChild("UpperTorso", 10)
        if not torso then return end

        track(torso.ChildAdded:Connect(function(child)
            if not abilityOn then return end
            if child.Name == "Ability" then
                task.wait(0.1)
                local icon = child:FindFirstChild("Icon")
                if not icon or not icon:IsA("ImageLabel") then
                    for _, desc in ipairs(child:GetDescendants()) do
                        if desc:IsA("ImageLabel") and desc.Name == "Icon" then
                            icon = desc
                            break
                        end
                    end
                end

                if icon and icon:IsA("ImageLabel") then
                    local abilityName = ABILITIES[icon.Image]
                    if abilityName then
                        pcall(function()
                            StarterGui:SetCore("SendNotification", {
                                Title = "⚡ " .. tp.Name,
                                Text = "Ability: " .. abilityName,
                                Duration = CONFIG.abilityNotifDuration,
                            })
                        end)
                    end
                end
            end
        end))
    end)
end

local function initAbilities()
    for _, p in ipairs(Players:GetPlayers()) do
        task.spawn(function()
            watchChar(p)
        end)
        track(p.CharacterAdded:Connect(function()
            watchChar(p)
        end))
    end

    track(Players.PlayerAdded:Connect(function(p)
        task.spawn(function()
            watchChar(p)
        end)
        track(p.CharacterAdded:Connect(function()
            watchChar(p)
        end))
    end))
end

---------------------------------------------------------------------
-- 39. MATCH TRACKER
---------------------------------------------------------------------
local function initMatchTracker()
    -- Watch InGame.Enabled
    pcall(function()
        local lastEnabled = inGameGui.Enabled
        track(inGameGui:GetPropertyChangedSignal("Enabled"):Connect(function()
            local now = inGameGui.Enabled
            if lastEnabled and not now and CONFIG.matchAutoReset then
                usedWords = {}
                prevSnapshotWord = ""
                prevTurnPlayer = nil
                pendingWord = nil
                notify("Match ended — words reset")
                if dictLoaded then updateResults() end
            end
            lastEnabled = now
        end))
    end)

    -- Watch Frame.Visible
    pcall(function()
        local lastVis = gameFrame.Visible
        track(gameFrame:GetPropertyChangedSignal("Visible"):Connect(function()
            local now = gameFrame.Visible
            if lastVis and not now and CONFIG.matchAutoReset then
                usedWords = {}
                prevSnapshotWord = ""
                prevTurnPlayer = nil
                pendingWord = nil
            end
            lastVis = now
        end))
    end)

    -- Watch Choices.Visible
    pcall(function()
        local choices = gameFrame:WaitForChild("Choices", 5)
        if choices then
            track(choices:GetPropertyChangedSignal("Visible"):Connect(function()
                if choices.Visible then
                    usedWords = {}
                    prevSnapshotWord = ""
                    prevTurnPlayer = nil
                    pendingWord = nil
                end
            end))
        end
    end)

    -- Watch Player Position vs Tables
    pcall(function()
        local tablesFolder = workspace:FindFirstChild("Tables")
        if not tablesFolder then return end
        
        local tablesToWatch = {}
        for _, name in ipairs({"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16"}) do
            local tm = tablesFolder:FindFirstChild(name)
            if tm then table.insert(tablesToWatch, tm) end
        end

        local lastCheck = 0
        local checkInterval = 1 
        local leaveTimestamps = {}
        local activeTables = {}

        track(RunService.Heartbeat:Connect(function()
            if not CONFIG.matchAutoReset or isUnloaded then return end
            
            local currentTime = os.clock()
            if currentTime - lastCheck >= checkInterval then
                lastCheck = currentTime
                
                local character = player.Character
                if not character or not character:FindFirstChild("HumanoidRootPart") then return end

                for _, tableModel in ipairs(tablesToWatch) do
                    local tableName = tableModel.Name
                    local hitbox = tableModel:FindFirstChild("Hitbox")
                    
                    if hitbox then
                        local partsTouching = workspace:GetPartsInPart(hitbox)
                        local isTouchingNow = false
                        
                        for _, part in ipairs(partsTouching) do
                            if part:IsDescendantOf(character) then
                                isTouchingNow = true
                                break
                            end
                        end
                        
                        if isTouchingNow then
                            -- Player is in the zone: cancel leave timer
                            leaveTimestamps[tableName] = nil
                            
                            if not activeTables[tableName] then
                                activeTables[tableName] = true
                                local tableID = tonumber(tableName)
                                local mode = (tableID and tableID >= 1 and tableID <= 9) and "Last Letter" or "One by One"
                                print("Voxxar: toucher table " .. tableName .. " | Mode: " .. mode)
                            end
                        else
                            -- Player is NOT in the zone
                            if activeTables[tableName] then
                                if not leaveTimestamps[tableName] then
                                    leaveTimestamps[tableName] = currentTime
                                end
                                
                                -- 5 seconds out = reset
                                if currentTime - leaveTimestamps[tableName] >= 5 then
                                    activeTables[tableName] = false
                                    leaveTimestamps[tableName] = nil
                                    
                                    -- Reset variables
                                    usedWords = {}
                                    prevSnapshotWord = ""
                                    prevTurnPlayer = nil
                                    pendingWord = nil
                                    
                                    notify("Left table " .. tableName .. " — words reset")
                                    if dictLoaded then updateResults() end
                                    print("Voxxar: Sortie confirmée (5s+) de la table " .. tableName .. " : Reset variable")
                                end
                            end
                        end
                    end
                end
            end
        end))
    end)
end

---------------------------------------------------------------------
-- 40. BUTTON CONNECTIONS
---------------------------------------------------------------------

-- Unload
track(unloadBtn.MouseButton1Click:Connect(function()
    cleanup()
end))

-- Settings toggle
track(settBtn.MouseButton1Click:Connect(function()
    settOpen = not settOpen
    settingsPanel.Visible = settOpen
end))

track(settCloseBtn.MouseButton1Click:Connect(function()
    settOpen = false
    settingsPanel.Visible = false
end))

-- Reset
track(resetBtn.MouseButton1Click:Connect(function()
    usedWords = {}
    retryBlacklist = {}
    prevSnapshotWord = ""
    prevTurnPlayer = nil
    pendingWord = nil
    notify("Words reset!")
    if dictLoaded then updateResults() end
end))

-- Mode cycle
track(modeBtn.MouseButton1Click:Connect(function()
    currentModeIndex = (currentModeIndex % #MODES) + 1
    applyMode()
end))

-- Ghost toggle
track(ghostBtn.MouseButton1Click:Connect(function()
    CONFIG.ghostMode = not CONFIG.ghostMode
    applyGhost()
    notify(CONFIG.ghostMode and "Ghost mode ON" or "Ghost mode OFF")
end))

track(floatingGhost.MouseButton1Click:Connect(function()
    CONFIG.ghostMode = false
    applyGhost()
    notify("Ghost mode OFF")
end))

-- Help (send best word to chat)
local helpClickLock = false
track(helpBtn.MouseButton1Click:Connect(function()
    if helpClickLock then return end
    helpClickLock = true

    if #topWords > 0 then
        local wordToSend = topWords[1]
        -- Try multiple chat methods
        local success = false

        -- Method 1: DefaultChatSystemChatEvents
        pcall(function()
            if ReplicatedStorage:FindFirstChild("DefaultChatSystemChatEvents") then
                local sayEvent = ReplicatedStorage.DefaultChatSystemChatEvents:FindFirstChild("SayMessageRequest")
                if sayEvent then
                    sayEvent:FireServer(wordToSend, "All")
                    success = true
                end
            end
        end)

        -- Method 2: TextChatService
        if not success then
            pcall(function()
                if TextChatService then
                    local generalChannel = TextChatService.TextChannels:FindFirstChild("RBXGeneral")
                    if generalChannel then
                        generalChannel:SendAsync(wordToSend)
                        success = true
                    end
                end
            end)
        end

        -- Method 3: Legacy chat
        if not success then
            pcall(function()
                StarterGui:SetCore("ChatMakeSystemMessage", {
                    Text = wordToSend,
                    Color = Color3.fromRGB(0, 200, 255),
                })
            end)
        end

        notify("Sent: " .. wordToSend)
    else
        notify("No words available!")
    end

    task.wait(0.5)
    helpClickLock = false
end))

-- Auto mode cycle
track(autoBtn.MouseButton1Click:Connect(function()
    autoMode = (autoMode + 1) % 3
    updateAutoBtn()
    local labels = {"OFF", "SEMI", "FULL"}
    notify("Auto: " .. labels[autoMode + 1])
end))

---------------------------------------------------------------------
-- 41. DRAG SYSTEM
---------------------------------------------------------------------
track(header.InputBegan:Connect(function(input)
    if input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch then
        dragging = true
        dragStart = input.Position
        startPos = header.Position
    end
end))

track(UserInputService.InputChanged:Connect(function(input)
    if dragging and (input.UserInputType == Enum.UserInputType.MouseMovement or input.UserInputType == Enum.UserInputType.Touch) then
        if dragStart and startPos then
            local delta = input.Position - dragStart
            header.Position = UDim2.new(
                startPos.X.Scale, startPos.X.Offset + delta.X,
                startPos.Y.Scale, startPos.Y.Offset + delta.Y
            )
        end
    end
end))

track(UserInputService.InputEnded:Connect(function(input)
    if input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch then
        dragging = false
    end
end))

---------------------------------------------------------------------
-- 42. KEYBOARD SHORTCUT (F4)
---------------------------------------------------------------------
track(UserInputService.InputBegan:Connect(function(input, processed)
    if processed then return end
    if input.KeyCode == Enum.KeyCode.F4 then
        uiVisible = not uiVisible
        screenGui.Enabled = uiVisible
    end
end))

---------------------------------------------------------------------
-- 43. GAME EVENT CONNECTIONS
---------------------------------------------------------------------

-- TypeLabel change → turn detection
track(typeLabel:GetPropertyChangedSignal("Text"):Connect(function()
    if isUnloaded then return end
    onTurn()
end))

-- Sound-based rotation detection
if rotated then
    for _, soundName in ipairs({"1", "2", "3"}) do
        local sound = rotated:FindFirstChild(soundName)
        if sound and sound:IsA("Sound") then
            track(sound.Played:Connect(function()
                invalidateWordCache()
            end))
        end
    end
end

-- Watch existing letter frames
for _, child in ipairs(currentWordFrame:GetChildren()) do
    watchLetter(child)
end

-- Debounced update helper
local function debouncedUpdate()
    if updateDebounce then
        pcall(function() task.cancel(updateDebounce) end)
    end
    updateDebounce = task.delay(0.1, function()
        updateDebounce = nil
        if not isMyTurn() and dictLoaded then
            local currentPrompt = string.lower(getCurrentWord())
            if currentPrompt and currentPrompt ~= "" and currentPrompt ~= lastHeartbeatWord then
                lastHeartbeatWord = currentPrompt
                updateResults()
            end
        end
    end)
end

-- Watch new/removed letter frames
track(currentWordFrame.ChildAdded:Connect(function(child)
    invalidateWordCache()
    watchLetter(child)
    -- Refresh word list on new letter (for help/pity when not our turn)
    if not isMyTurn() and dictLoaded then
        debouncedUpdate()
    end
end))

track(currentWordFrame.ChildRemoved:Connect(function(child)
    invalidateWordCache()
    if letterConns[child] then
        pcall(function() letterConns[child]:Disconnect() end)
        letterConns[child] = nil
    end
    -- Refresh word list on letter removed (for help/pity when not our turn)
    if not isMyTurn() and dictLoaded then
        debouncedUpdate()
    end
end))

---------------------------------------------------------------------
-- 44. HEARTBEAT LOOP
---------------------------------------------------------------------
track(RunService.Heartbeat:Connect(function()
    if isUnloaded then return end
    heartbeatCounter = heartbeatCounter + 1

    if heartbeatCounter % 3 == 0 then
        getBombTime()
    end

    if heartbeatCounter % 10 == 0 then
        updateHeaderReactive()
    end

    if heartbeatCounter % CONFIG.heartbeatInterval == 0 then
        local w = getCurrentWord()
        if w ~= lastHeartbeatWord then
            lastHeartbeatWord = w
            invalidateWordCache()
        end
    end
end))

---------------------------------------------------------------------
-- 44c. OPTIMIZATIONS
---------------------------------------------------------------------
-- Pre-cache common operations
local cachedFindWords = {}
task.spawn(function()
    while not isUnloaded do
        task.wait(30) -- Clear cache every 30 seconds
        cachedFindWords = {}
    end
end)

-- Optimized word finding with caching
local function findWordsCached(input)
    if not input or input == "" then return {} end
    if cachedFindWords[input] then
        return cachedFindWords[input]
    end
    local results = findWords(input)
    cachedFindWords[input] = results
    return results
end

---------------------------------------------------------------------
-- 45. MAIN INITIALIZATION (async)
---------------------------------------------------------------------
task.spawn(function()
    setLoadProgress(0.1, "Detecting keyboard layout...")
    buildNearby()
    detectLayout()
    notify("Layout: " .. curLayout)

    setLoadProgress(0.15, "Applying default mode...")
    applyMode()
    updateAutoBtn()

    local success = loadDict()

    if success then
        usedWords = {}
        prevSnapshotWord = ""
        prevTurnPlayer = nil
        pendingWord = nil
        initAbilities()
        initMatchTracker()
        applyGhost()

        -- SinkBox démarre INACTIF — sera activé par onTurn() quand nécessaire

        print("═══════════════════════════════════════")
        print("  ⚡ Voxxar WordHelper v5.1.2 loaded!")
        print("  📖 " .. #allWords .. " words")
        print("  ⌨ Layout: " .. curLayout)
        print("  🎮 Mode: " .. getCurrentMode().name)
        print("  🎯 Gamemode: " .. (currentGamemode ~= "" and currentGamemode or "Unknown"))
        print("═══════════════════════════════════════")

        -- Initial results check
        task.wait(0.5)
        if isMyTurn() then
            onTurn()
        end
    end

    task.wait(0.8)
    dismissLoading()
end)