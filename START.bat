@echo off
title US2SE Bridge - Converter
color 0e
cd /d "%~dp0"

echo  ╔══════════════════════════════════════╗
echo  ║        US2SE Bridge — старт          ║
echo  ║  ! ЗАПУСК ОТ ИМЕНИ АДМИНИСТРАТОРА !  ║
echo  ╚══════════════════════════════════════╝
echo.

:: ── Читаем пути из config.ini ──────────────────────────────────────────────
for /f "usebackq tokens=1,* delims== " %%A in (`findstr /i "us2_exe" config.ini`) do set US2_EXE=%%B
for /f "usebackq tokens=1,* delims== " %%A in (`findstr /i "se_exe"  config.ini`) do set SE_EXE=%%B

:: ── Запускаем Universe Sandbox ─────────────────────────────────────────────
if exist "%US2_EXE%" (
    echo  [1/3] Запуск Universe Sandbox...
    start "" "%US2_EXE%"
) else (
    echo  [!]   Universe Sandbox не найден: %US2_EXE%
    echo        Проверь us2_exe в config.ini
)

:: ── Небольшая пауза, чтобы US2 начал инициализацию ────────────────────────
timeout /t 3 /nobreak >nul

:: ── Запускаем SpaceEngine ──────────────────────────────────────────────────
if exist "%SE_EXE%" (
    echo  [2/3] Запуск SpaceEngine...
    start "" "%SE_EXE%"
) else (
    echo  [!]   SpaceEngine не найден: %SE_EXE%
    echo        Проверь se_exe в config.ini
)

:: ── Небольшая пауза перед стартом синка ───────────────────────────────────
timeout /t 3 /nobreak >nul

:: ── Запускаем синхронизатор ────────────────────────────────────────────────
echo  [3/3] Запуск синхронизатора...
echo.
echo  Пути читаются из config.ini
echo  Остановка: Ctrl+C (закроет также SE и US) или STOP.bat
echo.

python src\us2se_sync.py

:: ── После остановки синка закрываем SE и US ────────────────────────────────
echo.
echo  ╔══════════════════════════════════════╗
echo  ║        US2SE Bridge — стоп           ║
echo  ╚══════════════════════════════════════╝
echo.

echo  [1/2] Закрываю SpaceEngine...
taskkill /IM "SpaceEngine.exe" /F >nul 2>&1
echo        OK

echo  [2/2] Закрываю Universe Sandbox...
taskkill /FI "IMAGENAME eq Universe Sandbox x64.exe" /F >nul 2>&1
taskkill /FI "IMAGENAME eq Universe Sandbox.exe"     /F >nul 2>&1
powershell -Command "Get-Process | Where-Object { $_.Name -match 'Universe' } | Stop-Process -Force" >nul 2>&1
echo        OK

echo.
echo  Все процессы завершены.
echo.
pause

