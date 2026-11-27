@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
if not exist "workspace\.venv-two-flies\Scripts\pythonw.exe" (
  echo Среда не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
if not exist "workspace\runs\ideas\i-connectome-advantage\stage-5-strong-controls-development" mkdir "workspace\runs\ideas\i-connectome-advantage\stage-5-strong-controls-development"
set "RUNLOG=workspace\runs\ideas\i-connectome-advantage\stage-5-strong-controls-development\ПОСЛЕДНИЙ-ХОД-STAGE95.log"
start "" /wait "workspace\.venv-two-flies\Scripts\pythonw.exe" "experiments\templates\95_strong_controls_development.py" --choose > "%RUNLOG%" 2>&1
