@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Two flies - long user wing study
echo Длительное обучение на ваших движениях. Новая серия, продолжение или пауза.
echo Старая модель и исходные JSON не изменяются.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\60_long_wing_folder_selector.py" --choose
if errorlevel 1 echo Операция остановлена. Сохраните сообщение об ошибке.
pause
