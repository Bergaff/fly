@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 84X - lower-weighted paired view, 4 workers

echo Серия84X: 4096 новых движений x 4 ракурса = 16384 candidates.
echo На каждое движение: 3 lower-X и 1 upper-X view.
echo Используются 4 workers и batch4 для более быстрого расчета.
echo Model84V/84S/84R остаются frozen comparators.
echo Повторный запуск позволяет продолжить или запросить паузу.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\84x_lower_weighted_paired_view.py" --choose
if errorlevel 1 echo Серия остановлена. Последняя committed batch4 сохранена; source84V не изменялась.
pause
