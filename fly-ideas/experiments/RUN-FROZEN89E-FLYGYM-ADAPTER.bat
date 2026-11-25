@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PYW=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "PY=%CD%\workspace\.venv-flygym\Scripts\python.exe"
set "SCRIPT=%CD%\experiments\templates\101_frozen89e_flygym_adapter.py"
if not exist "%PYW%" if not exist "%PY%" (
  >"experiments\ОШИБКА-FLYGYM-ADAPTER.txt" echo Не найден Python среды FlyGym. Установите FlyGym через интерфейс Fly Ideas.
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('Не найдено готовое окружение FlyGym. Откройте Fly Ideas: Мозг - Данные и окружение - установить только FlyGym.','Series101')" >nul 2>&1
  start "" "%CD%\START.bat"
  exit /b 2
)
if not exist "%SCRIPT%" (
  >"experiments\ОШИБКА-FLYGYM-ADAPTER.txt" echo Не найден runner Series101. Обновите проект.
  exit /b 3
)
if exist "%PYW%" (
  start "Series101 frozen89E FlyGym" "%PYW%" "%SCRIPT%" --gui
) else (
  start "Series101 frozen89E FlyGym" /b "%PY%" "%SCRIPT%" --gui
)
