@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 79 - frozen view stress map

echo Серия 79: read-only stress map замороженной модели 78 без обучения.
echo Четыре новых движения 161-164, one-factor sweeps, core/evaluation corners и diagnostics.
echo Replay использует только 72 coefficients и phase после задержки 0,5 с.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\79_frozen_view_stress_map.py" --choose
if errorlevel 1 echo Stress map остановлен. Исходная серия 78 не изменялась.
pause
