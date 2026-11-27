@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 82D - distal observability diagnostic

echo Серия 82D: диагностика видимости distal-сегментов и level/edge признаков.
echo Это короткая диагностика, а не серия 83 и не восьмичасовой расчет.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\82d_distal_observability_diagnostic.py" --choose
if errorlevel 1 echo Диагностика остановлена.
pause
