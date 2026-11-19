@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
title Two Flies - frozen model holdout
echo Проверка заранее обученной модели на новых движениях без переобучения.
echo Выберите model.npz в папке вашего завершённого пилота imitation_...
echo Старые исследования и выбранная модель не изменяются.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\48_two_flies_frozen_holdout.py"
if errorlevel 1 echo Проверка остановлена. Сохраните текст ошибки и не используйте папку с INCOMPLETE.txt.
pause
