@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
title Two Flies - pause large study
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Отдельная среда двух мух не найдена.
  pause
  exit /b 1
)
echo Выберите папку текущего исследования large_two_flies_...
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\44_two_flies_large_study.py" --stop
if errorlevel 1 echo Не удалось запросить остановку. См. сообщение выше.
pause
