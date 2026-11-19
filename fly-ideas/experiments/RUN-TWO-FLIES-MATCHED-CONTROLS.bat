@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title Two Flies - matched visual controls
set PYTHONIOENCODING=utf-8
echo Контроли зрительных кадров и спайков 32 искусственных нейронов.
echo Это не обучение, не биологическая проверка зеркальных нейронов.
echo Выберите завершённую папку visual_controls_... с metadata.json.
echo Исходная серия не изменяется. Сначала завершите другие расчёты.
echo.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
echo Нажмите любую клавишу для выбора папки или закройте окно для отмены.
pause >nul
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\43_two_flies_matched_controls.py" --choose
if errorlevel 1 (
  echo Расчёт не завершён. Проверьте сообщение выше.
  echo Папка со статусом running содержит неполные результаты.
  pause
  exit /b 1
)
echo Готово или выбор отменён.
pause
