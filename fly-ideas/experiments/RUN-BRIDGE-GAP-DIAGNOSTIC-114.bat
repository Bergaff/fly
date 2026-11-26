@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PYW=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "PY=%CD%\workspace\.venv-flygym\Scripts\python.exe"
set "SCRIPT=%CD%\experiments\templates\114_bridge_gap_diagnostic.py"
set "ERR=%CD%\experiments\ОШИБКА-BRIDGE-GAP-DIAGNOSTIC-114.txt"
if not exist "%PY%" ( >"%ERR%" echo Не найден Python среды FlyGym. Установите среду через интерфейс.& start "" "%ERR%"& start "" "%CD%\START.bat"& exit /b 2 )
if not exist "%SCRIPT%" ( >"%ERR%" echo Не найден runner Series114. Обновите проект.& start "" "%ERR%"& exit /b 3 )
"%PY%" -c "import csv, hashlib, json, tkinter" >nul 2>&1
if errorlevel 1 ( >"%ERR%" echo Python не прошёл стандартный import preflight.& start "" "%ERR%"& exit /b 4 )
if exist "%PYW%" ( start "Series114 bridge gap diagnostic" "%PYW%" "%SCRIPT%" --gui ) else ( start "Series114 bridge gap diagnostic" /b "%PY%" "%SCRIPT%" --gui )
