@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PYW=%CD%\workspace\.venv-flygym\Scripts\pythonw.exe"
set "PY=%CD%\workspace\.venv-flygym\Scripts\python.exe"
set "SCRIPT=%CD%\experiments\templates\102_frozen89e_flygym_replication.py"
if not exist "%PY%" (
  >"experiments\ОШИБКА-FLYGYM-REPLICATION.txt" echo Не найден Python среды FlyGym. Откройте Fly Ideas: Мозг - Данные и окружение - Зрение и физическое тело - установить только FlyGym.
  start "" "%CD%\experiments\ОШИБКА-FLYGYM-REPLICATION.txt"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('Не найдено готовое окружение FlyGym. Сейчас откроется Fly Ideas. Установите только FlyGym, затем снова запустите BAT.','Series102')" >nul 2>&1
  start "" "%CD%\START.bat"
  exit /b 2
)
if not exist "%SCRIPT%" (
  >"experiments\ОШИБКА-FLYGYM-REPLICATION.txt" echo Не найден runner Series102. Обновите проект.
  start "" "%CD%\experiments\ОШИБКА-FLYGYM-REPLICATION.txt"
  exit /b 3
)
"%PY%" -c "import brian2, flygym" >nul 2>&1
if errorlevel 1 (
  >"experiments\ОШИБКА-FLYGYM-REPLICATION.txt" echo Среда FlyGym не прошла проверку Brian2/FlyGym. Откройте Fly Ideas и повторно нажмите установить только FlyGym.
  start "" "%CD%\experiments\ОШИБКА-FLYGYM-REPLICATION.txt"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('Среда не прошла проверку Brian2/FlyGym. Сейчас откроется Fly Ideas. Повторно нажмите установить только FlyGym, затем снова запустите BAT.','Series102')" >nul 2>&1
  start "" "%CD%\START.bat"
  exit /b 4
)
if exist "%PYW%" (
  start "Series102 frozen FlyGym replication" "%PYW%" "%SCRIPT%" --gui
) else (
  start "Series102 frozen FlyGym replication" /b "%PY%" "%SCRIPT%" --gui
)
