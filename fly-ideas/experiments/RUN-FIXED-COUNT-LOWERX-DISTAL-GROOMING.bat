@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 84S - fixed-count lower-X distal model

echo Серия 84S: 16 384 committed candidates, не wall-clock budget.
echo QuickEdit отключается и проверяется внутри Python. Случайный щелчок по консоли не должен приостанавливать расчёт.
echo Повторный запуск этого BAT позволяет продолжить серию или запросить паузу.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\84s_fixed_count_lowerx_distal_grooming.py" --choose
if errorlevel 1 echo Серия остановлена. Последняя committed партия сохранена; source84R не изменялась.
pause
