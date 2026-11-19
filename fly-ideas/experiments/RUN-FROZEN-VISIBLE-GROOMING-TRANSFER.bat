@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 76 - frozen visible grooming transfer

echo Серия 76: frozen transfer модели 75 без дообучения.
echo Автоматические holdout 101-110: matched, FOV, camera shift, body shift, mask и temporal shuffle.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\76_frozen_visible_grooming_transfer.py" --choose
if errorlevel 1 echo Frozen transfer остановлен. Исходная серия 75 не изменялась.
pause
