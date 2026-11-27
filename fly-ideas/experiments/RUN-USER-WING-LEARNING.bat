@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
title Two flies - user trajectory learning
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
echo Короткая проба: от 2 траекторий для обучения и отдельные для проверки.
echo Закреплённые скрипты и прежние результаты не изменяются.
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\51_two_flies_user_trajectory_learning.py" --choose
if errorlevel 1 echo Расчёт остановлен. Сохраните сообщение об ошибке.
pause
