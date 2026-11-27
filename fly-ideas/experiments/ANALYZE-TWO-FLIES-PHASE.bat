@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title Two Flies - phase analysis
set PYTHONIOENCODING=utf-8
echo Анализ фаз и 100 перемешиваний исходных кадров.
echo Выберите папку полного запуска с файлом metadata.json, не папку moving.
echo Исходные данные не перезаписываются. Если идёт важный расчёт, запустите позже.
echo.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
echo Нажмите любую клавишу, чтобы выбрать папку, или закройте окно.
pause >nul
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\40_two_flies_phase_analysis.py" --choose
if errorlevel 1 (
  echo Анализ не завершён. Проверьте сообщение об ошибке выше.
  echo Если папка анализа уже создана, status running означает неполный результат.
  pause
  exit /b 1
)
echo Готово или выбор папки отменён. Окно можно закрыть.
pause
