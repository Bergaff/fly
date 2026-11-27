@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PYW=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "PY=%CD%\workspace\.venv-flygym\Scripts\python.exe"
set "SCRIPT=%CD%\experiments\templates\105d_action_aware_temporal_tournament.py"
set "ERR=%CD%\experiments\ОШИБКА-ACTION-AWARE-105D.txt"
if not exist "%PY%" (
  >"%ERR%" echo Не найден Python среды FlyGym. Установите только FlyGym через интерфейс.
  start "" "%ERR%"
  start "" "%CD%\START.bat"
  exit /b 2
)
if not exist "%SCRIPT%" (
  >"%ERR%" echo Не найден runner Series105D. Обновите проект.
  start "" "%ERR%"
  exit /b 3
)
"%PY%" -c "import brian2, flygym, numba, llvmlite.binding, numpy; from flygym.vision.retina import Retina; Retina()" >nul 2>&1
if errorlevel 1 (
  >"%ERR%" echo Среда не прошла проверку Brian2/FlyGym vision. Повторно нажмите установить только FlyGym.
  start "" "%ERR%"
  start "" "%CD%\START.bat"
  exit /b 4
)
if exist "%PYW%" (
  start "Series105D action-aware temporal tournament" "%PYW%" "%SCRIPT%" --gui
) else (
  start "Series105D action-aware temporal tournament" /b "%PY%" "%SCRIPT%" --gui
)
