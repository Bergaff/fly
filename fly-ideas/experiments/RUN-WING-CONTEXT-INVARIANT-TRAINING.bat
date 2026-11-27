@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Two flies - context invariant right_x training

echo Серия 63: контрольная и контекст-инвариантная модели right_x.
echo Исходная серия 59 и новый holdout не изменяются.
echo Для начала, продолжения или паузы используйте этот же BAT.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\63_long_wing_context_invariant_training.py" --choose
if errorlevel 1 echo Расчет остановлен. Сохраните сообщение об ошибке. Если новая папка серии уже создана, последняя завершенная партия остается в базе.
pause
