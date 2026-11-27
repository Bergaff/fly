@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 84U - frozen replication model84S

echo Серия 84U: read-only replication замороженной model84S.
echo Обучения, продолжения training и настройки параметров нет.
echo Выберите завершенную папку lowerx_distal_fixed_count_... серии84S.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
echo Открывается отдельное окно выбора папки. Если оно не видно, переключитесь на окно "Серия 84U" через Alt+Tab.
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\84u_frozen_lowerx_distal_replication.py" --choose
if errorlevel 1 echo Репликация остановлена. Source84S не изменялась.
pause
