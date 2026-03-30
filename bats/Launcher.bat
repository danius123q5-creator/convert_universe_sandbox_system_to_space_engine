@echo off
chcp 65001 >nul
title US2SE Bridge Launcher
cd /d "%~dp0.."
:menu
cls
echo ==============================================
echo       UNIVERSE SANDBOX TO SPACE ENGINE
echo ==============================================
echo.
echo 1. Авто-Настройка (Найти пути)
echo 2. ЗАПУСТИТЬ МОСТ (Старт синхронизации)
echo 3. ОСТАНОВИТЬ МОСТ (Убить фоновые процессы)
echo 4. Выход
echo.
set /p choice="Выберите действие (1-4): "

if "%choice%"=="1" goto setup
if "%choice%"=="2" goto start
if "%choice%"=="3" goto stop
if "%choice%"=="4" exit
goto menu

:setup
cls
echo Запуск авто-настройки...
if exist "src\dist\US2SE_AutoDiscover.exe" (
    "src\dist\US2SE_AutoDiscover.exe"
) else (
    python src\autodiscover.py
)
pause
goto menu

:start
cls
echo Запуск фонового процесса синхронизации...
if exist "src\dist\US2SE_SyncBridge.exe" (
    start "" "src\dist\US2SE_SyncBridge.exe"
) else (
    start "" pythonw src\us2se_sync.py
)
echo Мост успешно запущен в фоновом режиме!
pause
goto menu

:stop
cls
echo Остановка моста...
taskkill /f /im US2SE_SyncBridge.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1
taskkill /f /im python.exe >nul 2>&1
echo Все процессы синхронизации завершены!
pause
goto menu
