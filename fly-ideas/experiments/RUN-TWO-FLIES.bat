@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title Two Flies - observation
echo Небольшая кинематическая сцена с упрощённой нейросетью, не FlyWire.
echo Если сейчас идёт важный расчёт, закройте это окно и запустите позже.
echo.
echo Нажмите любую клавишу для запуска или закройте окно для отмены.
pause >nul
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\38_two_flies_observation.py" --output "workspace\runs\ideas\i-observational\two-flies"
if errorlevel 1 (
  echo Расчёт завершился с ошибкой. Неполная папка имеет status running в metadata.json.
  pause
  exit /b 1
)
echo Результаты: workspace\runs\ideas\i-observational\two-flies
echo Открывается папка с результатами.
start "" explorer "workspace\runs\ideas\i-observational\two-flies"
pause
