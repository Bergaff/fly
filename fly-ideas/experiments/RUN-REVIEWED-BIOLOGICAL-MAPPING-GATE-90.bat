@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
title Series 90 - reviewed biological mapping gate

echo Серия90: заключительный bounded-аудит biological mapping gate.
echo Это не долгий расчёт; workers не применяются.
echo Mapping, DNs и motor gains не подбираются после результата.
echo Итог и любая ошибка автоматически сохраняются и открываются как копируемый TXT.

if exist "workspace\.venv-two-flies\Scripts\python.exe" (
  "workspace\.venv-two-flies\Scripts\python.exe" -u "experiments\templates\90_reviewed_biological_mapping_gate.py" --choose
) else (
  py -3 -u "experiments\templates\90_reviewed_biological_mapping_gate.py" --choose
)
if errorlevel 1 echo Серия90 остановлена. Открылся копируемый TXT-отчёт об ошибке.
pause
