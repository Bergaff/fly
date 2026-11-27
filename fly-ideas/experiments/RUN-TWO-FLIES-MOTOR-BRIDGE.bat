@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title Two Flies - motor bridge
set PYTHONIOENCODING=utf-8
echo Технический пилот: программная связь зрительных нейронов с крыльями.
echo Это не обучение имитации. До и во время показа крылья неподвижны по правилу.
echo После показа заранее заданный осциллятор работает на 2 Гц.
echo Выберите папку завершённой серии visual_controls_... с metadata.json.
echo Исходные данные не перезаписываются. Другие расчёты сначала завершите.
echo.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Сначала запустите experiments\SETUP-TWO-FLIES.bat.
  pause
  exit /b 1
)
echo Нажмите любую клавишу для выбора папки или закройте окно для отмены.
pause >nul
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\42_two_flies_motor_bridge.py" --choose
if errorlevel 1 (
  echo Расчёт не завершён. Проверьте сообщение выше.
  echo Папка со статусом running содержит неполные результаты.
  pause
  exit /b 1
)
echo Готово или выбор отменён.
pause
