@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
title Series 80 - canonical view representation prototype

echo Серия 80: короткий raw-vs-image-canonicalized prototype.
echo Это не восьмичасовой расчет и не новый научный результат.
echo Метаданные камеры и тела не передаются canonicalizer.
if not exist "workspace\.venv-two-flies\Scripts\python.exe" (
  echo Основная среда двух мух не найдена. Установите ее через Fly Ideas - Мозг - Данные и окружение.
  pause
  exit /b 1
)
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\80_canonical_view_representation_prototype.py" --choose
if errorlevel 1 echo Prototype остановлен.
pause
