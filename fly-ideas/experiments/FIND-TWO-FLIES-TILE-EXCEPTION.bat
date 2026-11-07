@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
title Two Flies - find tile exception
echo Выберите groups.csv в папке завершённого парного анализа.
echo База не используется, новый расчёт не запускается.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Среда двух мух не найдена. Запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\46_find_tile_exception.py"
if errorlevel 1 echo Поиск остановлен. Пришлите текст ошибки.
pause
