@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
title Two flies - wing studio pilot
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
echo Короткая проба 6 осей по выбранной траектории.
echo Исходная траектория и предыдущие исследования не изменяются.
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\50_two_flies_wing_studio_pilot.py" --choose
if errorlevel 1 echo Проба остановлена. Сохраните сообщение об ошибке.
pause
