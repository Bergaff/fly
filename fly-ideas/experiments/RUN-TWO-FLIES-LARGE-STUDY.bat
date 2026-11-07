@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title Two Flies - large study
set PYTHONIOENCODING=utf-8
echo Большая серия: 12 168 групп, 73 008 условий; две искусственные мухи.
echo Две фоновые задачи, низкий приоритет. Сначала завершите другие расчёты.
echo Это игрушечная модель зрения, не коннектом и не доказательство зеркальных нейронов.
echo Время 4-8 часов ориентировочно и зависит от компьютера.
echo Нужно не менее 12 ГиБ свободного диска перед новым запуском и 4 ГиБ свободной RAM.
echo Для безопасной паузы используйте PAUSE-TWO-FLIES-LARGE-STUDY.bat.
echo После паузы этим же файлом можно продолжить расчёт.
echo.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
rem Local compatibility shim; no changes to the checkpointed research script.
set "FLY_LONG_STUDY_IO_RETRY=1"
set "PYTHONPATH=%CD%\experiments\long-study-compat;%PYTHONPATH%"
"workspace\.venv-two-flies\Scripts\python.exe" -c "import os; assert getattr(os.replace, '_fly_progress_retry', False), 'Progress lock workaround did not load'"
if errorlevel 1 (
  echo Не удалось включить защиту от блокировки progress.json. Расчёт не запущен.
  pause
  exit /b 1
)
echo Нажмите любую клавишу для продолжения или закройте окно для отмены.
pause >nul
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\44_two_flies_large_study.py" --choose
if errorlevel 1 (
  echo Расчёт остановлен. Готовые группы сохранены в базе.
  echo Сообщите текст ошибки, не удаляйте папку исследования.
  pause
  exit /b 1
)
echo Окно можно закрыть.
pause
