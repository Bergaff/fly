@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title Two Flies - separate environment
echo Создание отдельного окружения, существующий Brian2 не меняется.
echo Не запускайте установку во время важного расчёта без необходимости.
set "PYCMD="
py -3.12 -c "import sys" >nul 2>nul
if not errorlevel 1 set "PYCMD=py -3.12"
if not defined PYCMD (
  py -3.11 -c "import sys" >nul 2>nul
  if not errorlevel 1 set "PYCMD=py -3.11"
)
if not defined PYCMD (
  python -c "import sys; assert sys.version_info[:2] in [(3,11),(3,12)]" >nul 2>nul
  if not errorlevel 1 set "PYCMD=python"
)
if not defined PYCMD (
  echo Нужен Python 3.11 или 3.12 для Windows x64: https://www.python.org/downloads/
  pause
  exit /b 1
)
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  %PYCMD% -m venv "workspace\.venv-two-flies"
  if errorlevel 1 goto error
)
"workspace\.venv-two-flies\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] in [(3,11),(3,12)]" || goto error
"workspace\.venv-two-flies\Scripts\python.exe" -m pip install --prefer-binary "numpy==1.26.4" "mujoco==3.3.7" "brian2==2.9.0" "pillow==11.3.0"
if errorlevel 1 goto error
"workspace\.venv-two-flies\Scripts\python.exe" -c "import numpy, mujoco, brian2, PIL; print('Среда готова.')"
if errorlevel 1 goto error
echo Теперь используйте experiments\RUN-TWO-FLIES.bat после завершения текущего расчёта.
pause
exit /b 0
:error
echo Установка не завершена. Проверьте интернет, Python и сообщение об ошибке.
pause
exit /b 1
