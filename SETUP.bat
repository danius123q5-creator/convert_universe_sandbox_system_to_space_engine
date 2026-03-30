@echo off
title US2SE Bridge - Авто-установка
color 0b
cd /d "%~dp0"

echo.
echo  ╔═══════════════════════════════════════════╗
echo  ║       US2SE Bridge: АВТО-НАСТРОЙКА         ║
echo  ╚═══════════════════════════════════════════╝
echo.

:: Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [!] ОШИБКА: Python не найден. Пожалуйста, установите Python.
    pause
    exit /b
)

:: Запуск авто-дискавера
python autodiscover.py

echo.
pause
