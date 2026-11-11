@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title Setup FlyVis and FlyGym
echo Установка двух изолированных сред. Существующая среда мозга не изменяется.
echo FlyVis и FlyGym разделены из-за несовместимых версий NumPy и Python.
echo.
where py >nul 2>nul || (echo Не найден Python Launcher py.exe. Установите Python 3.11 и 3.12 с python.org.& pause& exit /b 1)
if not exist "workspace\.venv-flyvis\Scripts\python.exe" py -3.11 -m venv "workspace\.venv-flyvis" || (echo Для FlyVis нужен Python 3.11.& pause& exit /b 1)
"workspace\.venv-flyvis\Scripts\python.exe" -m pip install --upgrade "pip<26"
"workspace\.venv-flyvis\Scripts\python.exe" -m pip install "flyvis==1.2.0" || (echo FlyVis не установлен.& pause& exit /b 1)
if not exist "workspace\.venv-flygym\Scripts\python.exe" py -3.12 -m venv "workspace\.venv-flygym" || (echo Для FlyGym 2 нужен Python 3.12.& pause& exit /b 1)
"workspace\.venv-flygym\Scripts\python.exe" -m pip install --upgrade "pip<26"
"workspace\.venv-flygym\Scripts\python.exe" -m pip install "flygym==2.1.1" || (echo FlyGym не установлен.& pause& exit /b 1)
echo.
echo Среды созданы. Теперь запустите RUN-EMBODIED-CONNECTOME-PREFLIGHT.bat.
pause
