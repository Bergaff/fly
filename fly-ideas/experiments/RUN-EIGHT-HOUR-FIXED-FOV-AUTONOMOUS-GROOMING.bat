@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 83 - fixed FOV35 autonomous grooming

echo Серия 83: ровно 8 часов fixed-FOV35 edge обучения двух мух.
echo После обучения frozen model проверяется на движениях 261-270 x 16 geometry corners.
echo Primary включает все шесть осей, controls, body X 4,18 и autonomous replay после задержки 0,5 с.
echo Этот BAT начинает, продолжает и ставит расчет на паузу.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\83_eight_hour_fixed_fov_autonomous_grooming.py" --choose
if errorlevel 1 echo Расчет остановлен. Если папка серии создана, последняя завершенная партия сохранена.
pause
