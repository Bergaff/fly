@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PYW=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "PY=%CD%\workspace\.venv-flygym\Scripts\python.exe"
set "SCRIPT=%CD%\experiments\templates\120abc_final_digital_product.py"
set "ERR=%CD%\experiments\ОШИБКА-FINAL-DIGITAL-PRODUCT-120ABC.txt"
if not exist "%PY%" ( >"%ERR%" echo Не найден Python среды FlyGym.& start "" "%ERR%"& start "" "%CD%\START.bat"& exit /b 2 )
if not exist "%SCRIPT%" ( >"%ERR%" echo Не найден runner Series120A-B-C. Обновите проект.& start "" "%ERR%"& exit /b 3 )
"%PY%" -c "import csv, hashlib, json, numpy, tkinter" >nul 2>&1
if errorlevel 1 ( >"%ERR%" echo Python не прошёл import preflight numpy/tkinter.& start "" "%ERR%"& exit /b 4 )
if exist "%PYW%" ( start "Series120 A B C final digital product" "%PYW%" "%SCRIPT%" --gui ) else ( start "Series120 A B C final digital product" /b "%PY%" "%SCRIPT%" --gui )
