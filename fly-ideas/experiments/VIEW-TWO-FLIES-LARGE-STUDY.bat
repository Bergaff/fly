@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
title Two Flies - inspect study group
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Отдельная среда двух мух не найдена.
  pause
  exit /b 1
)
echo Выберите папку исследования и укажите group_id из trials_summary.csv.
echo Данные группы будут скопированы в новую папку без изменения базы.
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\44_two_flies_large_study.py" --export
if errorlevel 1 echo Группу не удалось открыть. См. сообщение выше.
pause
