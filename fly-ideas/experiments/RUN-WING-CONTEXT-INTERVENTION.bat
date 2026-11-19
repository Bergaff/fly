@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Two flies - wing context intervention
echo Короткая проверка контекстных осей уже обученных моделей.
echo Исходная серия и модели не изменяются.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\61_long_wing_context_intervention.py" --choose
if errorlevel 1 echo Проверка остановлена. Сохраните сообщение об ошибке.
pause
