@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 82G - scale normalized camera prototype

echo Серия 82G: variable FOV против fixed FOV 35 и tracked-camera diagnostic.
echo Это короткий geometry prototype, не восьмичасовой расчет.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\82g_scale_normalized_camera_prototype.py" --choose
if errorlevel 1 echo Prototype остановлен.
pause
