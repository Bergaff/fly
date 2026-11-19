@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 84R - 8h distal-robust grooming model

echo Серия 84R: новая preregistered spatial-pyramid модель, ровно 8 часов активного обучения.
echo Source83 используется только как frozen comparator. Новые holdouts 301-310 не входят в обучение.
echo Два процесса оставляют компьютер доступным для Word. Повторный запуск этого BAT позволяет продолжить или запросить паузу.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\84r_eight_hour_distal_robust_grooming.py" --choose
if errorlevel 1 echo Серия остановлена. Последняя завершённая партия сохранена; source83 не изменялась.
pause
