@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 89 - closed loop embodied validation

echo Серия89: новые motions, views, initial poses, disturbance и controls.
echo 432 visual cases, 1296 embodied trials; frozen model84Z без обучения.
echo Результат и ошибки автоматически откроются как копируемые файлы.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\89_closed_loop_embodied_validation.py" --choose
if errorlevel 1 echo Серия89 остановлена. Открылся копируемый TXT-отчет об ошибке.
pause
