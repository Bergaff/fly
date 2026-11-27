@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Two flies - full wing context factorial
echo Полный расчет 32 комбинаций контекстных осей для right_x.
echo Модели не переобучаются. Исходная серия не изменяется.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\62_long_wing_context_factorial.py" --choose
if errorlevel 1 echo Расчет остановлен. Сохраните сообщение об ошибке.
pause
