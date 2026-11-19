@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 85 - shared latent population

echo Серия85: shared observation/execution population prototype.
echo Новые motions451-470, две независимые batteries, 320 cases.
echo Frozen model84Z не обучается и не изменяется.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\85_shared_latent_population.py" --choose
if errorlevel 1 echo Серия85 остановлена. Открылся копируемый TXT-отчет об ошибке.
pause
