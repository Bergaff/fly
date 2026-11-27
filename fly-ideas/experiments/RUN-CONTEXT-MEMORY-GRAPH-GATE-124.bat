@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PYW=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "PY=%CD%\workspace\.venv-flygym\Scripts\python.exe"
set "SCRIPT=%CD%\experiments\templates\124_context_memory_graph_gate.py"
set "ERR=%CD%\experiments\ОШИБКА-CONTEXT-MEMORY-124.txt"
if not exist "%PY%" ( >"%ERR%" echo Не найден Python среды FlyGym.& start "" "%ERR%"& start "" "%CD%\START.bat"& exit /b 2 )
if not exist "%SCRIPT%" ( >"%ERR%" echo Не найден runner Series124. Обновите проект.& start "" "%ERR%"& exit /b 3 )
"%PY%" -c "import hashlib, importlib.util, json, numpy, tkinter" >nul 2>&1
if errorlevel 1 ( >"%ERR%" echo Python не прошёл import preflight.& start "" "%ERR%"& exit /b 4 )
if exist "%PYW%" ( start "Series124 context memory gate" "%PYW%" "%SCRIPT%" --gui ) else ( start "Series124 context memory gate" /b "%PY%" "%SCRIPT%" --gui )
