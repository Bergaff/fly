@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PYW=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "PY=%CD%\workspace\.venv-flygym\Scripts\python.exe"
set "SCRIPT=%CD%\experiments\templates\103_flygym_interbody_vision_preflight.py"
if not exist "%PY%" (
  >"experiments\ОШИБКА-FLYGYM-VISION-PREFLIGHT.txt" echo Не найден Python среды FlyGym. Установите только FlyGym через интерфейс Fly Ideas.
  start "" "%CD%\experiments\ОШИБКА-FLYGYM-VISION-PREFLIGHT.txt"
  start "" "%CD%\START.bat"
  exit /b 2
)
if not exist "%SCRIPT%" (
  >"experiments\ОШИБКА-FLYGYM-VISION-PREFLIGHT.txt" echo Не найден runner Series103. Обновите проект.
  start "" "%CD%\experiments\ОШИБКА-FLYGYM-VISION-PREFLIGHT.txt"
  exit /b 3
)
"%PY%" -c "import flygym, PIL, numba, llvmlite.binding; from flygym.vision.retina import Retina; Retina()" >nul 2>&1
if errorlevel 1 (
  >"experiments\ОШИБКА-FLYGYM-VISION-PREFLIGHT.txt" echo Среда не прошла проверку FlyGym vision/Numba/llvmlite. Повторно нажмите установить только FlyGym в интерфейсе: установщик заново восстановит binary dependencies.
  start "" "%CD%\experiments\ОШИБКА-FLYGYM-VISION-PREFLIGHT.txt"
  start "" "%CD%\START.bat"
  exit /b 4
)
if exist "%PYW%" (
  start "Series103 official vision preflight" "%PYW%" "%SCRIPT%" --gui
) else (
  start "Series103 official vision preflight" /b "%PY%" "%SCRIPT%" --gui
)
