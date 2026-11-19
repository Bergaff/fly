@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 84V - paired-view distal consistency

echo Серия 84V: 4 096 новых движений x 4 связанных ракурса = 16 384 candidates.
echo Model84S и model84R используются только как frozen comparators.
echo Старые motions 321-350 не входят ни в обучение, ни в blocking evaluation.
echo Повторный запуск позволяет продолжить расчёт или запросить паузу.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\84v_paired_view_distal_consistency.py" --choose
if errorlevel 1 echo Серия остановлена. Последняя committed партия сохранена; source84S не изменялась.
pause
