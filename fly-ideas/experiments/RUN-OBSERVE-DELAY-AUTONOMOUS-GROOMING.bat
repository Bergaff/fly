@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 77 - observe delay autonomous grooming

echo Серия 77: наблюдение - внутреннее состояние - задержка 0,5 с - автономный replay.
echo Frozen модель 75 не переобучается. Во время replay RGB, teacher и prediction buffer недоступны.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\77_observe_delay_autonomous_grooming.py" --choose
if errorlevel 1 echo Автономная проверка остановлена. Исходная серия 75 не изменялась.
pause
