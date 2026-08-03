@echo off
cd /d "%~dp0"
title Kalite Repo Analyzer

echo.
echo =========================================
echo  Kalite Repo Analyzer
echo =========================================
echo.

where node >nul 2>nul || (echo [HATA] Node.js yok & pause & exit /b 1)
where npm  >nul 2>nul || (echo [HATA] npm yok & pause & exit /b 1)

echo Eski process kapatiliyor...
taskkill /f /im node.exe >nul 2>&1
timeout /t 2 /nobreak >nul

if not exist "node_modules\.bin\next.cmd" (
  echo Bagimliliklar kuruluyor...
  call npm install
  if errorlevel 1 (echo [HATA] & pause & exit /b 1)
)

if not exist "src\app\tailwind-gen.css" (
  echo Tailwind CSS olusturuluyor (ilk kurulum, 1-2 dk)...
  node scripts\build-tailwind.mjs
  if errorlevel 1 (echo [HATA] Tailwind CSS & pause & exit /b 1)
)

echo.
echo Baslatiliyor: http://localhost:3000
echo Kapatmak icin: Ctrl+C
echo.

:: Browser'ı sunucu hazir olunca ac
start /b cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:3000"

npx next dev -p 3000
pause
