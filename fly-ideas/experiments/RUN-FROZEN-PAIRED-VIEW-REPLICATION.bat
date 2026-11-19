@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 84W - frozen replication model84V

echo Серия84W: read-only replication frozen model84V.
echo Обучения, tuning и изменения weights нет.
echo Выберите завершенную папку paired_view_distal_... серии84V.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\84w_frozen_paired_view_replication.py" --choose
if errorlevel 1 echo Репликация остановлена. Source84V не изменялась.
pause
