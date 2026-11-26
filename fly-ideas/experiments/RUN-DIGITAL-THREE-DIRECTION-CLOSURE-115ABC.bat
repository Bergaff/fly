@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PYW=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "PY=%CD%\workspace\.venv-flygym\Scripts\python.exe"
set "SCRIPT=%CD%\experiments\templates\115abc_digital_three_direction_closure.py"
set "ERR=%CD%\experiments\ОШИБКА-DIGITAL-CLOSURE-115ABC.txt"
if not exist "%PY%" ( >"%ERR%" echo Не найден Python среды FlyGym.& start "" "%ERR%"& start "" "%CD%\START.bat"& exit /b 2 )
where git >nul 2>&1
if errorlevel 1 ( >"%ERR%" echo Не найден Git для exact sources.& start "" "%ERR%"& exit /b 3 )
if not exist "%SCRIPT%" ( >"%ERR%" echo Не найден runner Series115A-C. Обновите проект.& start "" "%ERR%"& exit /b 4 )
"%PY%" -c "import csv, hashlib, json, tkinter" >nul 2>&1
if errorlevel 1 ( >"%ERR%" echo Python не прошёл standard import preflight.& start "" "%ERR%"& exit /b 5 )
if exist "%PYW%" ( start "Series115A-C digital closure" "%PYW%" "%SCRIPT%" --gui ) else ( start "Series115A-C digital closure" /b "%PY%" "%SCRIPT%" --gui )
