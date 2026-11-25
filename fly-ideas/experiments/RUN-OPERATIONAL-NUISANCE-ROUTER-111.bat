@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PYW=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "PY=%CD%\workspace\.venv-flygym\Scripts\python.exe"
set "SCRIPT=%CD%\experiments\templates\111_operational_nuisance_router.py"
set "ERR=%CD%\experiments\ОШИБКА-NUISANCE-ROUTER-111.txt"
if not exist "%PY%" ( >"%ERR%" echo Не найден Python среды FlyGym. Установите только FlyGym через интерфейс.& start "" "%ERR%"& start "" "%CD%\START.bat"& exit /b 2 )
if not exist "%SCRIPT%" ( >"%ERR%" echo Не найден runner Series111. Обновите проект.& start "" "%ERR%"& exit /b 3 )
"%PY%" -c "import brian2, flygym, numba, llvmlite.binding, numpy; from flygym.vision.retina import Retina; Retina()" >nul 2>&1
if errorlevel 1 ( >"%ERR%" echo Среда не прошла проверку Brian2/FlyGym vision.& start "" "%ERR%"& start "" "%CD%\START.bat"& exit /b 4 )
if exist "%PYW%" ( start "Series111 operational nuisance router" "%PYW%" "%SCRIPT%" --gui ) else ( start "Series111 operational nuisance router" /b "%PY%" "%SCRIPT%" --gui )
