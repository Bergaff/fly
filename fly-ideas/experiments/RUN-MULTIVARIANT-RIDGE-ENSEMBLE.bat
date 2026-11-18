@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 84Z - multivariant ridge ensemble

echo Серия84Z: 4096 новых движений x 4 balanced84V ракурса = 16384 candidates.
echo Обучаются четыре ridge-варианта и два frozen84V ensemble-варианта.
echo Выбор выполняется только на motions421-430; final motions431-440 остаются изолированными.
echo В интерфейсе выберите 2, 4, 6 workers или МАКСИМУМ.
echo МАКСИМУМ использует все логические процессоры без резерва для других программ.
echo Повторный запуск продолжает тот же закрепленный режим или запрашивает паузу.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\84z_multivariant_ridge_ensemble.py" --choose
if errorlevel 1 echo Серия остановлена. Последняя committed партия сохранена; source84V не изменялась.
pause
