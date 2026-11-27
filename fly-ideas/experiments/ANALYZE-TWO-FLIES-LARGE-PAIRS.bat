@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
title Two Flies - paired analysis
echo Парный анализ сохранённых групп и времён спайков.
echo Закройте большой расчёт перед анализом. База будет открыта только для чтения.
echo Проверка и чтение большой базы могут занять значительное время.
echo Результаты будут сохранены в новой папке внутри выбранного исследования.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\45_two_flies_paired_analysis.py"
if errorlevel 1 echo Анализ остановлен. Сообщите текст ошибки, не удаляйте базу.
pause
