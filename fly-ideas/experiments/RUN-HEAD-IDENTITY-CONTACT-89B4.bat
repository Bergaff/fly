@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 89B4 - head identity and contact

echo Серия89B4: soft action mixture, head contact и oracle diagnostic.
echo Motions711-746,360 visual cases; frozen source84Z.
echo Результат и ошибки автоматически откроются как копируемые файлы.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\89b4_head_identity_contact.py" --choose
if errorlevel 1 echo Серия89B4 остановлена. Открылся копируемый TXT-отчет об ошибке.
pause
