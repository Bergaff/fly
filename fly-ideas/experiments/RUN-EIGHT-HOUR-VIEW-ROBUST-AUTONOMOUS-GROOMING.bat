@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 78 - view robust autonomous grooming

echo Серия 78: 8 часов наблюдения двух мух с camera, FOV и body augmentation.
echo После обучения модель автоматически замораживается и проверяется на движениях 141-150.
echo Primary оценивает autonomous replay после задержки 0,5 с на новых view-motion combinations по каждой оси.
echo Этот же BAT начинает, продолжает и ставит расчет на паузу.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\78_eight_hour_view_robust_autonomous_grooming.py" --choose
if errorlevel 1 echo Расчет остановлен. Если папка серии создана, последняя завершенная партия сохранена.
pause
