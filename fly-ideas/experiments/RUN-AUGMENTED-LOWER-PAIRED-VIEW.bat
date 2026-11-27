@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 84Y - augmented lower paired view

echo Серия84Y: 4096 новых движений x 5 ракурсов = 20480 candidates.
echo Четыре ракурса84V сохранены; добавлен один lower-X ракурс.
echo В интерфейсе выберите 2, 4, 6 workers или МАКСИМУМ.
echo МАКСИМУМ использует все логические процессоры без резерва для других программ.
echo Повторный запуск позволяет продолжить с тем же закрепленным режимом или запросить паузу.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\84y_augmented_lower_paired_view.py" --choose
if errorlevel 1 echo Серия остановлена. Последняя committed партия сохранена; source84V не изменялась.
pause
