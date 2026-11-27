@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 84AA - frozen replication model84Z

echo Серия84AA: read-only replication selected model84Z.
echo Новые motions441-450, 16 corners, 160 final cases.
echo Training и повторный выбор шести variants запрещены.
echo Source84Z и frozen84V/84S/84R не изменяются.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\84aa_frozen_multivariant_replication.py" --choose
if errorlevel 1 echo Replication остановлена. Source84Z не изменялась.
pause
