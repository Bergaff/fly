@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title Two Flies - visual controls
set PYTHONIOENCODING=utf-8
echo Серия из семи условий: взмахи и движущийся посторонний объект.
echo Все результаты сохраняются в новой папке; старые файлы не изменяются.
echo Одна задача на CPU. Если идёт важный расчёт, закройте окно и запустите позже.
echo Сохраните работу в Word перед запуском.
echo.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
echo Нажмите любую клавишу для запуска или закройте окно для отмены.
pause >nul
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\41_two_flies_visual_controls.py"
if errorlevel 1 (
  echo Расчёт не завершён. Проверьте сообщение об ошибке выше.
  echo Папка со статусом running содержит неполные результаты.
  pause
  exit /b 1
)
echo Открывается общая папка результатов. Выберите последнюю папку visual_controls_.
start "" explorer "workspace\runs\ideas\i-observational\visual-controls"
pause
