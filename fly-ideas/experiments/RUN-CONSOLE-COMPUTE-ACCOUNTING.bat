@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 84T - console and compute accounting

echo Серия 84T: fixed-count технический расчёт 128 candidates.
echo QuickEdit отключается внутри Python: щелчок мышью по окну не должен ставить расчёт на скрытую паузу.
echo Отдельно записываются coordinator wall time и worker CPU time. Научная модель не обучается.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\84t_console_compute_accounting.py" --choose
if errorlevel 1 echo Диагностика остановлена.
pause
