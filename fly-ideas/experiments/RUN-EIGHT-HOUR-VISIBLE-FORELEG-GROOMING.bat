@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 75 - eight hours foreleg grooming observation

echo Серия 75: ровно 8 часов обучения наблюдению за передними лапами с обязательной проверкой RGB.
echo Четыре семейства: piecewise 5/9 точек, harmonic, chirp.
echo Движения 101-110 закрепляются до обучения. Прежние файлы не изменяются.
echo Этот же BAT начинает, продолжает и ставит расчет на паузу.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\75_eight_hour_visible_foreleg_grooming.py" --choose
if errorlevel 1 echo Расчет остановлен. Если папка серии создана, последняя завершенная партия сохранена.
pause
