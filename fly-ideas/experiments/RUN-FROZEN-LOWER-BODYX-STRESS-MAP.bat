@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 84 - frozen lower body X stress map

echo Серия 84: read-only stress map замороженной модели 83 без обучения.
echo Новые движения 281-286, 72 geometry cells и отдельное воспроизведение failed probes серии 83.
echo Replay использует только 72 coefficients и phase после задержки 0,5 с.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\84_frozen_lower_bodyx_stress_map.py" --choose
if errorlevel 1 echo Stress map остановлен. Исходная серия 83 не изменялась.
pause
