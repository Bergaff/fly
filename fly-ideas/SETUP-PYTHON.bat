@echo off
chcp 65001 >nul
title Fly Ideas - Python Setup
cd /d "%~dp0"

set "PYCMD="
python -c "import sys; raise SystemExit(0 if sys.version_info[0]>=3 else 1)" >nul 2>nul
if not errorlevel 1 set "PYCMD=python"

if "%PYCMD%"=="" (
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info[0]>=3 else 1)" >nul 2>nul
  if not errorlevel 1 set "PYCMD=py -3"
)

if "%PYCMD%"=="" (
  echo.
  echo  [!] Python 3 не найден в PATH.
  echo  Скачай Python 3.11 или 3.12 с https://www.python.org/downloads/
  echo  (обязательно отметь галочку Add Python to PATH при установке)
  echo  и запусти этот файл снова.
  echo.
  pause
  exit /b 1
)

echo.
echo  [1/3] Создаю локальное окружение workspace\.venv ...
if not exist "workspace\.venv\Scripts\python.exe" (
  %PYCMD% -m venv "workspace\.venv"
  if errorlevel 1 (
    echo.
    echo  [!] Не удалось создать workspace\.venv. Проверь права на папку и место на диске.
    pause
    exit /b 1
  )
)

set "VENV_PY=workspace\.venv\Scripts\python.exe"

echo.
echo  [2/3] Устанавливаю научные пакеты (numpy, pandas, scipy, matplotlib, pyarrow, brian2)...
"%VENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] <= (3, 12) else 1)" >nul 2>nul
if not errorlevel 1 (
  "%VENV_PY%" -m pip install --prefer-binary "numpy<2" "pyarrow<19" pandas scipy matplotlib brian2==2.9.0 networkx joblib requests tqdm pillow
) else (
  "%VENV_PY%" -m pip install --prefer-binary numpy pyarrow pandas scipy matplotlib brian2 networkx joblib requests tqdm pillow
)

if errorlevel 1 (
  echo.
  echo  [!] pip завершился с ошибкой. Проверь интернет и запусти SETUP-PYTHON.bat ещё раз.
  pause
  exit /b 1
)

echo.
echo  [3/3] Проверяю импорт библиотек...
"%VENV_PY%" -c "import numpy, pandas, scipy, matplotlib, pyarrow; print('OK:', numpy.__version__, pandas.__version__)"
if errorlevel 1 (
  echo.
  echo  [!] Проверка импорта не прошла.
  pause
  exit /b 1
)

echo.
echo  Готово! Fly Ideas автоматически подхватит workspace\.venv\Scripts\python.exe.
echo  Теперь можно запускать расчёты в разделе Мозг.
echo.
pause
