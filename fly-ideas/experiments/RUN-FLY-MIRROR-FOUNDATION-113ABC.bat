@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PYW=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "PY=%CD%\workspace\.venv-flygym\Scripts\python.exe"
set "SCRIPT=%CD%\experiments\templates\113abc_fly_mirror_foundation.py"
set "ERR=%CD%\experiments\ОШИБКА-FLY-MIRROR-FOUNDATION-113ABC.txt"
if not exist "%PY%" ( >"%ERR%" echo Не найден Python среды FlyGym. Установите среду через интерфейс.& start "" "%ERR%"& start "" "%CD%\START.bat"& exit /b 2 )
where git >nul 2>&1
if errorlevel 1 ( >"%ERR%" echo Не найден Git, необходимый для exact official sources.& start "" "%ERR%"& exit /b 3 )
if not exist "%SCRIPT%" ( >"%ERR%" echo Не найден runner Series113A-C. Обновите проект.& start "" "%ERR%"& exit /b 4 )
"%PY%" -c "import csv, hashlib, json, tkinter" >nul 2>&1
if errorlevel 1 ( >"%ERR%" echo Python не прошёл стандартный import preflight.& start "" "%ERR%"& exit /b 5 )
if exist "%PYW%" ( start "Series113A-C fly mirror foundation" "%PYW%" "%SCRIPT%" --gui ) else ( start "Series113A-C fly mirror foundation" /b "%PY%" "%SCRIPT%" --gui )
