@echo off
chcp 65001 >nul
echo 🏗️  Compilation XenoBridge

:: Vérifier si dotnet est installé
dotnet --version >nul 2>&1
if errorlevel 1 (
    echo ❌ .NET SDK non trouve !
    echo    Telechargez: https://dotnet.microsoft.com/download/dotnet/8.0
    pause
    exit /b 1
)

echo 📦 Nettoyage...
dotnet clean -c Release >nul 2>&1

echo 🔨 Compilation Release...
dotnet build -c Release

if errorlevel 1 (
    echo ❌ Erreur de compilation
    pause
    exit /b 1
)

echo ✅ Compilation reussie !
echo.
echo 📁 Executable: bin\Release\net8.0-windows\win-x64\XenoBridge.exe
echo.
pause
