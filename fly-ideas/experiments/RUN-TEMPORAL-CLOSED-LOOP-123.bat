@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PYW=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "PY=%CD%\workspace\.venv-flygym\Scripts\python.exe"
set "SCRIPT=%CD%\experiments\templates\123_temporal_closed_loop_graph_benchmark.py"
set "ERR=%CD%\experiments\ОШИБКА-TEMPORAL-CLOSED-LOOP-123.txt"
if not exist "%PY%" ( >"%ERR%" echo Не найден Python среды FlyGym.& start "" "%ERR%"& start "" "%CD%\START.bat"& exit /b 2 )
if not exist "%SCRIPT%" ( >"%ERR%" echo Не найден runner Series123. Обновите проект.& start "" "%ERR%"& exit /b 3 )
"%PY%" -c "import csv, hashlib, json, numpy, tkinter" >nul 2>&1
if errorlevel 1 ( >"%ERR%" echo Python не прошёл import preflight.& start "" "%ERR%"& exit /b 4 )
if exist "%PYW%" ( start "Series123 temporal closed loop" "%PYW%" "%SCRIPT%" --gui ) else ( start "Series123 temporal closed loop" /b "%PY%" "%SCRIPT%" --gui )
