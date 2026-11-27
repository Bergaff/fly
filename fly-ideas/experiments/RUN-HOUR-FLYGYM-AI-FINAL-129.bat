@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PYW=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "PY=%CD%\workspace\.venv-flygym\Scripts\python.exe"
set "SCRIPT=%CD%\experiments\templates\129_hour_flygym_ai_final_battery.py"
set "ERR=%CD%\experiments\ОШИБКА-HOUR-FINAL-129.txt"
if not exist "%PY%" ( >"%ERR%" echo Не найден Python среды FlyGym.& start "" "%ERR%"& start "" "%CD%\START.bat"& exit /b 2 )
if not exist "%SCRIPT%" ( >"%ERR%" echo Не найден runner Series129. Обновите проект.& start "" "%ERR%"& exit /b 3 )
"%PY%" -c "import csv, hashlib, json, numpy, tkinter, urllib.request" >nul 2>&1
if errorlevel 1 ( >"%ERR%" echo Python не прошёл import preflight.& start "" "%ERR%"& exit /b 4 )
where ollama >nul 2>&1
if errorlevel 1 ( >"%ERR%" echo Не найдена Ollama. Установите Ollama и qwen2.5:7b.& start "" "%ERR%"& exit /b 5 )
start "Ollama" /min ollama serve
if exist "%PYW%" ( start "Series129 hour FlyGym AI final" "%PYW%" "%SCRIPT%" --gui ) else ( start "Series129 hour FlyGym AI final" /b "%PY%" "%SCRIPT%" --gui )
