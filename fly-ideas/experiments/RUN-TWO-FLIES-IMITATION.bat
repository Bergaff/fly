@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
title Two Flies - supervised imitation pilot
echo Проба обучения движению крыльев по изображениям и эталонным углам.
echo Старые исследования не изменяются. Новая папка будет создана автоматически.
echo Вы можете продолжать работать, но время и отзывчивость не гарантируются.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\47_two_flies_imitation_learning.py"
if errorlevel 1 echo Проба остановлена. Сохраните текст ошибки и не используйте папку с INCOMPLETE.txt.
pause
