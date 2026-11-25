@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PY=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "SCRIPT=%CD%\experiments\templates\100_flygym_two_body_preflight.py"
if not exist "%PY%" (
  >"experiments\ОШИБКА-FLYGYM-ПРЕДПРОВЕРКА.txt" echo FlyGym ещё не установлен. Откройте Fly Ideas: Мозг - Данные и окружение - Зрение и физическое тело - установить только FlyGym.
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('FlyGym ещё не установлен. Сейчас откроется Fly Ideas. Перейдите: Мозг - Данные и окружение - Зрение и физическое тело - установить только FlyGym. После установки снова запустите этот BAT.','FlyGym: нужна установка')" >nul 2>&1
  start "" "%CD%\START.bat"
  exit /b 2
)
if not exist "%SCRIPT%" (
  >"experiments\ОШИБКА-FLYGYM-ПРЕДПРОВЕРКА.txt" echo Не найден runner: %SCRIPT%
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('Не найден runner Series100. Обновите проект.','FlyGym: ошибка')" >nul 2>&1
  exit /b 3
)
start "FlyGym two-body preflight" "%PY%" "%SCRIPT%" --gui
