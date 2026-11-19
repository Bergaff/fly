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
rem Disable the legacy replace hook; the launcher handles progress and CSV safely.
set "FLY_LONG_STUDY_IO_RETRY=0"
echo Временные блокировки прогресса и CSV обрабатываются без перезапуска приложения.
echo Нажмите любую клавишу для продолжения или закройте окно для отмены.
pause >nul
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\44_two_flies_safe_launcher.py" --choose
if errorlevel 1 (
  echo Расчёт остановлен. Готовые группы сохранены в базе.
  echo Сообщите текст ошибки, не удаляйте папку исследования.
  pause
  exit /b 1
)
echo Окно можно закрыть.
pause
