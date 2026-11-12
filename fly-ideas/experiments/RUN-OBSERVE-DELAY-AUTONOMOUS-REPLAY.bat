@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Two flies - observe delay autonomous replay

echo Серия 66: наблюдение - внутреннее состояние - задержка - автономный replay.
echo Для начала, продолжения или паузы используйте этот же BAT.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\66_long_observe_delay_autonomous_replay.py" --choose
if errorlevel 1 echo Расчет остановлен. Если папка серии создана, последняя завершенная партия остается в базе.
pause
