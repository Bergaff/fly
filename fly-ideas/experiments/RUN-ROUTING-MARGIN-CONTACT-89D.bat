@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 89D - routing margin contact

echo Серия89D: routing-margin identity и robust foreleg contact.
echo Motions837-872,360 visual cases; frozen source84Z.
echo Результат и ошибки автоматически откроются как копируемые файлы.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\89d_routing_margin_contact.py" --choose
if errorlevel 1 echo Серия89D остановлена. Открылся копируемый TXT-отчет об ошибке.
pause
