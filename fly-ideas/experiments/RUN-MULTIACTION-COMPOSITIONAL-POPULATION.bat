@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 86 - multi-action compositional population

echo Серия86: три действия, action identity и compositional holdout.
echo Frozen model84Z не обучается и не изменяется.
echo Calibration471-479; blocking identity480-491; composition492-497.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\86_multiaction_compositional_population.py" --choose
if errorlevel 1 echo Серия86 остановлена. Открылся копируемый TXT-отчет об ошибке.
pause
