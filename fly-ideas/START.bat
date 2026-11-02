@echo off
chcp 65001 >nul
title Fly Ideas
cd /d "%~dp0"

where node >nul 2>nul
if errorlevel 1 (
  echo.
  echo  [!] Node.js не найден. Установи LTS-версию с https://nodejs.org и запусти снова.
  echo.
  pause
  exit /b 1
)

if exist "electron\app-update-start.cjs" (
  node "electron\app-update-start.cjs"
  if errorlevel 1 (
    echo.
    echo  [!] Обновление не применено. Закрой все окна Fly Ideas и проверь сообщение выше.
    pause
    exit /b 1
  )
)

if exist "workspace\.app-updates\npm-pending" (
  echo.
  echo  Обновляю зависимости приложения...
  call npm ci
  if errorlevel 1 (
    echo  [!] Не удалось обновить зависимости. Проверь интернет и запусти снова.
    pause
    exit /b 1
  )
  del "workspace\.app-updates\npm-pending"
)

if not exist node_modules (
  echo.
  echo  Первый запуск: устанавливаю зависимости, это займёт пару минут...
  echo.
  call npm install
  if errorlevel 1 (
    echo.
    echo  [!] npm install завершился с ошибкой. Проверь интернет и запусти снова.
    pause
    exit /b 1
  )
)

echo.
echo  Запускаю Fly Ideas... (закрой это окно, чтобы остановить программу)
echo.
call npm run electron:dev
