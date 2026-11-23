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
if not exist "workspace\runs\ideas\i-connectome-advantage\stage-4-frozen-paired-loss" mkdir "workspace\runs\ideas\i-connectome-advantage\stage-4-frozen-paired-loss"
set "RUNLOG=workspace\runs\ideas\i-connectome-advantage\stage-4-frozen-paired-loss\ПОСЛЕДНИЙ-ХОД-STAGE94.log"
start "" /wait "workspace\.venv-two-flies\Scripts\pythonw.exe" "experiments\templates\94_frozen_paired_loss_replication.py" --choose > "%RUNLOG%" 2>&1
