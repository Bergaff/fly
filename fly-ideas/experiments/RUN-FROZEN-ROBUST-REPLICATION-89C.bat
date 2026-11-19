@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 89C - frozen robust replication

echo Серия89C: frozen replication без обучения и выбора.
echo Понадобятся завершённые папки result89B6 и production84Z.
echo Motions819-836,216 visual cases,648 trials.
echo Результат и ошибки автоматически откроются как копируемые файлы.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\89c_frozen_robust_replication.py" --choose
if errorlevel 1 echo Серия89C остановлена. Открылся копируемый TXT-отчет об ошибке.
pause
