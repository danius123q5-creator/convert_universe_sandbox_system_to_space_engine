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
echo  Для остановки: Ctrl+C или STOP.bat
echo.

python src\us2se_sync.py
pause

