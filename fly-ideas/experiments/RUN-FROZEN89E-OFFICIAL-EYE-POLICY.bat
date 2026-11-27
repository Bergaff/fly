@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PYW=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "PY=%CD%\workspace\.venv-flygym\Scripts\python.exe"
set "SCRIPT=%CD%\experiments\templates\104_frozen89e_official_eye_policy.py"
if not exist "%PY%" (
  >"experiments\ОШИБКА-OFFICIAL-EYE-POLICY.txt" echo Не найден Python среды FlyGym. Установите только FlyGym через интерфейс.
  start "" "%CD%\experiments\ОШИБКА-OFFICIAL-EYE-POLICY.txt"
  start "" "%CD%\START.bat"
  exit /b 2
)
if not exist "%SCRIPT%" (
  >"experiments\ОШИБКА-OFFICIAL-EYE-POLICY.txt" echo Не найден runner Series104. Обновите проект.
  start "" "%CD%\experiments\ОШИБКА-OFFICIAL-EYE-POLICY.txt"
  exit /b 3
)
"%PY%" -c "import brian2, flygym, numba, llvmlite.binding; from flygym.vision.retina import Retina; Retina()" >nul 2>&1
if errorlevel 1 (
  >"experiments\ОШИБКА-OFFICIAL-EYE-POLICY.txt" echo Среда не прошла проверку Brian2/FlyGym vision. Повторно нажмите установить только FlyGym.
  start "" "%CD%\experiments\ОШИБКА-OFFICIAL-EYE-POLICY.txt"
  start "" "%CD%\START.bat"
  exit /b 4
)
if exist "%PYW%" (
  start "Series104 frozen89E official eyes" "%PYW%" "%SCRIPT%" --gui
) else (
  start "Series104 frozen89E official eyes" /b "%PY%" "%SCRIPT%" --gui
)
