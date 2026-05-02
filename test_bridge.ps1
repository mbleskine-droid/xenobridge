# Test script pour XenoBridge
# Lance ce script apres avoir demarre XenoBridge.exe

$BRIDGE_URL = "http://localhost:3111"

Write-Host "🧪 Test XenoBridge" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Health check
Write-Host "Test 1: Health Check" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BRIDGE_URL/health" -Method GET -TimeoutSec 5
    Write-Host "✅ Statut: $($response.status)" -ForegroundColor Green
    Write-Host "   Version: $($response.version)" -ForegroundColor Gray
    Write-Host "   Initialisé: $($response.initialized)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Erreur: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   Verifiez que XenoBridge.exe tourne" -ForegroundColor Gray
    exit 1
}

Write-Host ""

# Test 2: Get version
Write-Host "Test 2: Version Xeno" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BRIDGE_URL/version" -Method GET -TimeoutSec 5
    Write-Host "✅ Version: $($response.version)" -ForegroundColor Green
} catch {
    Write-Host "❌ Erreur: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 3: Get clients (liste vide si pas encore attaché)
Write-Host "Test 3: Liste des clients" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BRIDGE_URL/clients" -Method GET -TimeoutSec 5
    $clients = $response.clients
    
    if ($clients.Count -eq 0) {
        Write-Host "⚠️  Aucun client connecté (normal si Roblox n'est pas demarre)" -ForegroundColor Yellow
    } else {
        Write-Host "✅ $($clients.Count) client(s) trouvé(s):" -ForegroundColor Green
        foreach ($client in $clients) {
            $state = switch ($client.state) {
                0 { "🔴 Deconnecte" }
                1 { "🟡 En attente" }
                2 { "🔵 Attache" }
                3 { "🟢 Pret" }
                default { "⚪ Inconnu" }
            }
            Write-Host "   PID $($client.pid): $($client.name) - $state" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "❌ Erreur: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 4: Attach (ne marche que si Roblox tourne)
Write-Host "Test 4: Attachement" -ForegroundColor Yellow
Write-Host "   Cherche RobloxPlayerBeta.exe..." -ForegroundColor Gray

$roblox = Get-Process -Name "RobloxPlayerBeta" -ErrorAction SilentlyContinue
if ($roblox) {
    Write-Host "   ✅ Roblox trouvé (PID: $($roblox.Id))" -ForegroundColor Green
    Write-Host "   Tentative d'attachement..." -ForegroundColor Gray
    
    try {
        $response = Invoke-RestMethod -Uri "$BRIDGE_URL/attach" -Method POST -TimeoutSec 10
        Write-Host "✅ $($response.message)" -ForegroundColor Green
        Write-Host "   Attendez 5-10 secondes et relancez le test pour voir les clients" -ForegroundColor Yellow
    } catch {
        Write-Host "❌ Erreur: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "   ⚠️  Roblox non trouvé. Demarrez Roblox d'abord." -ForegroundColor Yellow
    Write-Host "   Test ignore." -ForegroundColor Gray
}

Write-Host ""

# Test 5: Execute (test simple)
Write-Host "Test 5: Execution de script" -ForegroundColor Yellow
Write-Host "   Ce test necessite un client attaché" -ForegroundColor Gray

$clients = Invoke-RestMethod -Uri "$BRIDGE_URL/clients" -Method GET -TimeoutSec 5
$readyClients = $clients.clients | Where-Object { $_.state -eq 3 }

if ($readyClients.Count -gt 0) {
    $pids = $readyClients | ForEach-Object { $_.pid }
    $body = @{
        script = "print('Test XenoBridge OK!')"
        pids = $pids
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$BRIDGE_URL/execute" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 5
        Write-Host "✅ Script execute sur PIDs: $($pids -join ', ')" -ForegroundColor Green
    } catch {
        Write-Host "❌ Erreur: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "   ⚠️  Aucun client pret (state=3). Attachez d'abord." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==================" -ForegroundColor Cyan
Write-Host "Tests termines !" -ForegroundColor Cyan
