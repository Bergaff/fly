@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PYW=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "PY=%CD%\workspace\.venv-flygym\Scripts\python.exe"
set "SCRIPT=%CD%\experiments\templates\118_four_hour_adaptive_three_direction.py"
set "ERR=%CD%\experiments\ОШИБКА-ADAPTIVE-THREE-DIRECTION-118.txt"
if not exist "%PY%" ( >"%ERR%" echo Не найден Python среды FlyGym.& start "" "%ERR%"& start "" "%CD%\START.bat"& exit /b 2 )
if not exist "%SCRIPT%" ( >"%ERR%" echo Не найден runner Series118. Обновите проект.& start "" "%ERR%"& exit /b 3 )
"%PY%" -c "import csv, hashlib, json, numpy, sqlite3, tkinter" >nul 2>&1
if errorlevel 1 ( >"%ERR%" echo Python не прошёл import preflight numpy/tkinter.& start "" "%ERR%"& exit /b 4 )
if exist "%PYW%" ( start "Series118 adaptive three directions ~4h" "%PYW%" "%SCRIPT%" --gui ) else ( start "Series118 adaptive three directions ~4h" /b "%PY%" "%SCRIPT%" --gui )
