@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Two flies - frozen rich observer replication

echo Серия 68: независимая репликация замороженной модели серии 67.
echo Нового обучения нет. Нужны пять новых random JSON длительностью 2 с.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\68_frozen_rich_observer_replication.py" --choose
if errorlevel 1 echo Репликация остановлена. Папка с INCOMPLETE.txt не является результатом.
pause
