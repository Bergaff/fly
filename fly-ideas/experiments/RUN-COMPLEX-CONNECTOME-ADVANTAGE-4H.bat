@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Комплексный Connectome Advantage - около 4 часов

echo Комплексный artificial96 development benchmark примерно на 4 часа.
echo Проверяются ordered actions, few-shot, ракурсы, окклюзия, state noise и lesions.
echo QuickEdit отключается; прогресс сохраняется после каждого replicate.
echo Повторный запуск этого BAT продолжает незавершённую папку.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Среда не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\92_complex_connectome_advantage.py" --choose
if errorlevel 1 echo Расчёт остановлен. Открылся копируемый TXT-отчёт об ошибке.
pause
