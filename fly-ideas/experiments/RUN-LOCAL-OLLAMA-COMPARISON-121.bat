@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PYW=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "PY=%CD%\workspace\.venv-flygym\Scripts\python.exe"
set "SCRIPT=%CD%\experiments\templates\121_local_ollama_narrow_benchmark.py"
set "ERR=%CD%\experiments\ОШИБКА-OLLAMA-COMPARISON-121.txt"
if not exist "%PY%" ( >"%ERR%" echo Не найден Python среды FlyGym.& start "" "%ERR%"& start "" "%CD%\START.bat"& exit /b 2 )
if not exist "%SCRIPT%" ( >"%ERR%" echo Не найден runner Series121. Обновите проект.& start "" "%ERR%"& exit /b 3 )
"%PY%" -c "import csv, hashlib, json, numpy, tkinter, urllib.request" >nul 2>&1
if errorlevel 1 ( >"%ERR%" echo Python не прошёл import preflight.& start "" "%ERR%"& exit /b 4 )
if exist "%PYW%" ( start "Series121 local Ollama comparison" "%PYW%" "%SCRIPT%" --gui ) else ( start "Series121 local Ollama comparison" /b "%PY%" "%SCRIPT%" --gui )
