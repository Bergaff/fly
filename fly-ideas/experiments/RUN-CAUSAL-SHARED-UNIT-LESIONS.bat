@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 87 - causal shared unit lesions

echo Серия87: causal shared/observation/execution/random lesions.
echo Ranking только calibration498-506; blocking evaluation507-536.
echo Frozen model84Z не обучается и не изменяется.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\87_causal_shared_unit_lesions.py" --choose
if errorlevel 1 echo Серия87 остановлена. Открылся копируемый TXT-отчет об ошибке.
pause
