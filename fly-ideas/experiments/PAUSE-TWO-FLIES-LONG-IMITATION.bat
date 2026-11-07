@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
title Two Flies - long imitation
echo Пауза после сохранения текущей партии
echo Старые серии и модель не изменяются; нужна среда двух мух.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\49_two_flies_long_imitation.py" --pause
if errorlevel 1 echo Операция остановлена. Сохраните сообщение об ошибке.
pause
