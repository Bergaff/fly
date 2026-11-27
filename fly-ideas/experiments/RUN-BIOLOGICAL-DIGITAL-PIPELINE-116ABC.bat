@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PYW=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "PY=%CD%\workspace\.venv-flygym\Scripts\python.exe"
set "SCRIPT=%CD%\experiments\templates\116abc_biological_digital_pipeline.py"
set "ERR=%CD%\experiments\ОШИБКА-BIOLOGICAL-DIGITAL-116ABC.txt"
if not exist "%PY%" ( >"%ERR%" echo Не найден Python среды FlyGym.& start "" "%ERR%"& start "" "%CD%\START.bat"& exit /b 2 )
where git >nul 2>&1
if errorlevel 1 ( >"%ERR%" echo Не найден Git для exact structural sources.& start "" "%ERR%"& exit /b 3 )
if not exist "%SCRIPT%" ( >"%ERR%" echo Не найден runner Series116A-C. Обновите проект.& start "" "%ERR%"& exit /b 4 )
"%PY%" -c "import csv, hashlib, json, numpy, tkinter" >nul 2>&1
if errorlevel 1 ( >"%ERR%" echo Python не прошёл import preflight numpy/tkinter.& start "" "%ERR%"& exit /b 5 )
if exist "%PYW%" ( start "Series116A-C biological digital pipeline" "%PYW%" "%SCRIPT%" --gui ) else ( start "Series116A-C biological digital pipeline" /b "%PY%" "%SCRIPT%" --gui )
