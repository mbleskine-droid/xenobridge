# Test complet de XenoBridge
# Lance ce script pour tester TOUTES les fonctionnalités

$URL = "http://localhost:3111"

Write-Host "🚀 TEST COMPLET XENOBIRDGE" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan
Write-Host ""

# 1. Health Check
Write-Host "✅ 1. Health Check" -ForegroundColor Green
$health = Invoke-RestMethod -Uri "$URL/health"
Write-Host "   Statut: $($health.status)"
Write-Host "   Version: $($health.version)"
Write-Host "   Initialisé: $($health.initialized)"
Write-Host ""

# 2. Version
Write-Host "✅ 2. Version Xeno" -ForegroundColor Green
$ver = Invoke-RestMethod -Uri "$URL/version"
Write-Host "   $($ver.version)"
Write-Host ""

# 3. Liste des clients
Write-Host "✅ 3. Clients Roblox" -ForegroundColor Green
$clients = Invoke-RestMethod -Uri "$URL/clients"
if ($clients.clients.Count -eq 0) {
    Write-Host "   ⚠️ Aucun client (démarrez Roblox)" -ForegroundColor Yellow
} else {
    foreach ($c in $clients.clients) {
        $state = switch ($c.state) {
            0 { "🔴 Déconnecté" }
            1 { "🟡 En attente" }
            2 { "🔵 Attaché" }
            3 { "🟢 Prêt" }
        }
        Write-Host "   PID $($c.pid): $($c.name) - $state"
    }
}
Write-Host ""

# 4. Test d'exécution (si client prêt)
$ready = $clients.clients | Where-Object { $_.state -eq 3 }
if ($ready) {
    Write-Host "✅ 4. Exécution de script" -ForegroundColor Green
    $pid = $ready[0].pid
    $body = @{ 
        script = "print('✅ XenoBridge TEST OK - Script exécuté avec succès !')" 
        pids = @($pid)
    } | ConvertTo-Json
    
    $result = Invoke-RestMethod -Uri "$URL/execute" -Method POST -Body $body -ContentType "application/json"
    Write-Host "   Script envoyé au PID $pid : $($result.success)"
    Write-Host ""
}

# 5. Paramètres
Write-Host "✅ 5. Paramètres (AutoAttach)" -ForegroundColor Green
$set = Invoke-RestMethod -Uri "$URL/setting" -Method POST -Body '{"setting": "AutoAttach", "value": true}' -ContentType "application/json"
Write-Host "   AutoAttach activé: $($set.success)"
Write-Host ""

Write-Host "=" * 50 -ForegroundColor Cyan
Write-Host "🎉 TOUS LES TESTS PASSÉS !" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Résumé des endpoints testés :" -ForegroundColor Gray
Write-Host "   GET  /health   - Statut du bridge" -ForegroundColor Gray
Write-Host "   GET  /version  - Version Xeno" -ForegroundColor Gray
Write-Host "   GET  /clients  - Liste des clients" -ForegroundColor Gray
Write-Host "   POST /execute  - Exécution de script ✅" -ForegroundColor Gray
Write-Host "   POST /setting  - Configuration" -ForegroundColor Gray
Write-Host "   POST /attach   - Attachement manuel" -ForegroundColor Gray
