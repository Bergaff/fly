@echo off
chcp 65001 >nul
title Fly Ideas: сборка EXE
cd /d "%~dp0"

where node >nul 2>nul
if errorlevel 1 (
  echo  [!] Node.js не найден. Установи LTS-версию с https://nodejs.org
  pause
  exit /b 1
)

if not exist node_modules (
  echo  Устанавливаю зависимости...
  call npm install || (pause & exit /b 1)
)

echo.
echo  Собираю портативный Fly-Ideas-0.1.0-win64.exe в папку release\ ...
echo.
call npm run dist
if errorlevel 1 (
  echo.
  echo  [!] Сборка не удалась. Скопируй текст ошибки выше.
  pause
  exit /b 1
)

echo.
echo  Готово! Файл лежит в папке release\
echo.
explorer release
pause
