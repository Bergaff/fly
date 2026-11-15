@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 81 - raw plus gated canonical multiscale prototype

echo Серия 81: короткий raw-vs-gated-multiscale prototype.
echo Raw признаки всегда сохраняются; canonical eye отключается при border touch.
echo Это не восьмичасовой расчет и не научный long-run результат.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\81_multiscale_gated_view_prototype.py" --choose
if errorlevel 1 echo Prototype остановлен.
pause
