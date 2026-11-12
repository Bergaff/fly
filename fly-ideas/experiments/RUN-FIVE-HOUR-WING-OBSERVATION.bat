@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 72 - five hours of two-fly observation

echo Серия 72: ровно 5 часов активного обучения наблюдателя второй мухи.
echo Исходные движения и прежняя модель не изменяются.
echo Этот же BAT начинает, продолжает и ставит расчет на паузу.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\72_five_hour_wing_observation.py" --choose
if errorlevel 1 echo Расчет остановлен. Если папка серии уже создана, последняя завершенная партия сохранена.
pause
