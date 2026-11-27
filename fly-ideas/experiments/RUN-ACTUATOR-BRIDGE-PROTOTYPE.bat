@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 88 - actuator bridge prototype

echo Серия88: bounded actuator bridge с proprioception/contact feedback.
echo 30 новых motions537-566, 16 views, frozen model84Z без обучения.
echo Результат и ошибки автоматически откроются как копируемые файлы.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\88_actuator_bridge_prototype.py" --choose
if errorlevel 1 echo Серия88 остановлена. Открылся копируемый TXT-отчет об ошибке.
pause
