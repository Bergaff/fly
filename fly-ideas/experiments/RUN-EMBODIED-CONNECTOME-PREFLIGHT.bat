@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
title FlyVis - Shiu - FlyGym preflight
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
echo 1 - проверить три среды и данные
echo 2 - проверить контракты на короткой fixture
set /p MODE=Выберите 1 или 2: 
if "%MODE%"=="2" (
  "workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\70_embodied_connectome_pipeline.py" --preflight --fixture
) else (
  "workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\70_embodied_connectome_pipeline.py" --preflight
)
if errorlevel 1 echo Preflight завершился с ошибкой.
pause
