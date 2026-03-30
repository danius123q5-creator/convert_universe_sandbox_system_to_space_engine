@echo off
title US2SE Bridge - STOP
color 0c
cd /d "%~dp0"

echo  ╔══════════════════════════════════════╗
echo  ║        US2SE Bridge — стоп           ║
echo  ║  ! ЗАПУСК ОТ ИМЕНИ АДМИНИСТРАТОРА !  ║
echo  ╚══════════════════════════════════════╝
echo.

:: ── Синхронизатор ─────────────────────────────────────────────────────────
echo  [1/3] Останавливаю синхронизатор...
wmic process where "CommandLine like '%%us2se_sync.py%%'" delete >nul 2>&1
taskkill /FI "WINDOWTITLE eq US2SE Bridge*" /F >nul 2>&1
echo        OK

:: ── SpaceEngine ───────────────────────────────────────────────────────────
echo  [2/3] Закрываю SpaceEngine...
taskkill /IM "SpaceEngine.exe" /F >nul 2>&1
echo        OK

:: ── Universe Sandbox ──────────────────────────────────────────────────────
echo  [3/3] Закрываю Universe Sandbox...
taskkill /FI "IMAGENAME eq Universe Sandbox x64.exe" /F >nul 2>&1
taskkill /FI "IMAGENAME eq Universe Sandbox.exe"     /F >nul 2>&1
powershell -Command "Get-Process | Where-Object { $_.Name -match 'Universe' } | Stop-Process -Force" >nul 2>&1
echo        OK

echo.
echo  Все процессы завершены.
echo.
pause
