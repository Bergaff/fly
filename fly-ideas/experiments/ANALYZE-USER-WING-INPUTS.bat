@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
title Two flies - analyze existing visual input
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Не найдена среда предыдущей пробы. Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
echo Проверка готовых результатов, без нового обучения. Старые файлы не изменяются.
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\52_analyze_user_wing_inputs.py" --choose
if errorlevel 1 (
  echo Диагностика остановлена. Пришлите текст сообщения об ошибке.
  pause
  exit /b 1
)
pause
