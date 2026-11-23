@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Комплексный Connectome Advantage - около 4 часов

echo Комплексный artificial96 development benchmark примерно на 4 часа.
echo Проверяются ordered actions, few-shot, ракурсы, окклюзия, state noise и lesions.
echo Прогресс сохраняется после каждого replicate.
echo Вывод Python пишется в файл, поэтому клавиатура и консоль не могут остановить расчёт.
echo Повторный запуск этого BAT продолжает незавершённую папку.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Среда не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
if not exist "workspace\runs\ideas\i-connectome-advantage\stage-2-complex-development" mkdir "workspace\runs\ideas\i-connectome-advantage\stage-2-complex-development"
set "RUNLOG=workspace\runs\ideas\i-connectome-advantage\stage-2-complex-development\ПОСЛЕДНИЙ-ХОД-КОМПЛЕКСНЫЙ.log"
echo Подробный ход записывается в: %RUNLOG%
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\92_complex_connectome_advantage.py" --choose > "%RUNLOG%" 2>&1
if errorlevel 1 echo Расчёт остановлен. Открылся копируемый TXT-отчёт об ошибке.
pause
