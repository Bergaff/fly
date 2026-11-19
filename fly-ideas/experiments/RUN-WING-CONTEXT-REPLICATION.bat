@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Two flies - five new context holdouts

echo Серия 64: пять новых holdout для замороженных моделей серии 63.
echo Сначала подготовьте пять новых JSON. Выберите их одновременно, удерживая Ctrl.
echo Серия 63 и новые JSON не изменяются.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\64_wing_context_invariant_replication.py" --choose
if errorlevel 1 echo Расчет остановлен. Сохраните сообщение об ошибке.
pause
