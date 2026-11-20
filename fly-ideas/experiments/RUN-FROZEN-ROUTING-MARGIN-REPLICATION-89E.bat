@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 89E - frozen routing margin replication

echo Серия89E: frozen routing-margin replication без обучения и выбора.
echo Понадобятся завершённые папки result89D и production84Z.
echo Motions873-890,216 visual cases,648 trials.
echo Результат и ошибки автоматически откроются как копируемые файлы.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\89e_frozen_routing_margin_replication.py" --choose
if errorlevel 1 echo Серия89E остановлена. Открылся копируемый TXT-отчет об ошибке.
pause
