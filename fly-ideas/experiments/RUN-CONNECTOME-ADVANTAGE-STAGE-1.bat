@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Этап 1 - преимущество 96-unit архитектуры

echo Этап 1: artificial96-unit benchmark.
echo Реальные нейроны и FlyWire ID на этом этапе не используются.
echo Результат и ошибки автоматически сохраняются в копируемые TXT-файлы.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Среда не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\91_connectome_advantage_stage1.py" --choose
if errorlevel 1 echo Этап 1 остановлен. Открылся копируемый TXT-отчет об ошибке.
pause
