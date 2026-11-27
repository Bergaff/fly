@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
title Диагностика Stage92

if not exist "workspace\.venv-two-flies\Scripts\pythonw.exe" (
  echo Среда не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
if not exist "workspace\runs\ideas\i-connectome-advantage\stage-2-complex-development" mkdir "workspace\runs\ideas\i-connectome-advantage\stage-2-complex-development"
set "RUNLOG=workspace\runs\ideas\i-connectome-advantage\stage-2-complex-development\ПОСЛЕДНИЙ-ХОД-ДИАГНОСТИКИ.log"
start "" /wait "workspace\.venv-two-flies\Scripts\pythonw.exe" "experiments\templates\93_stage92_paired_diagnostic.py" --gui > "%RUNLOG%" 2>&1
