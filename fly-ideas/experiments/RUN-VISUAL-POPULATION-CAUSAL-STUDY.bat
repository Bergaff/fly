@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=4
set OPENBLAS_NUM_THREADS=4
set MKL_NUM_THREADS=4
title Series 71 - visual population causal study

echo Серия 71: какие T4/T5 популяции нужны для отложенного повтора.
echo 1 - записать preregistration и условия лезий ^(без расчета^)
echo 2 - получить активность pretrained FlyVis из готового retinal movie NPY
echo 3 - создать кандидаты FlyVis - FlyWire для ручной научной проверки
echo 4 - проверить утвержденный mapping и разблокировать план лезий
set /p MODE=Выберите 1-4: 
if "%MODE%"=="2" goto flyvis
if "%MODE%"=="3" goto mapping
if "%MODE%"=="4" goto validate
if not exist "workspace\.venv-two-flies\Scripts\python.exe" goto nobrain
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\71_visual_population_causal_study.py" --stage protocol
goto done

:flyvis
if not exist "workspace\.venv-flyvis\Scripts\python.exe" (
 echo Сначала в Fly Ideas откройте Мозг - Данные и окружение - Зрение и физическое тело.
 echo Нажмите установить всё для зрения и тела.
 goto done
)
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms;$d=New-Object System.Windows.Forms.OpenFileDialog;$d.Title='Retinal movie NPY: eyes x frames x hexals';$d.Filter='NumPy (*.npy)|*.npy';if($d.ShowDialog() -eq 'OK'){$d.FileName}"`) do set "MOVIE=%%F"
if not defined MOVIE goto done
"workspace\.venv-flyvis\Scripts\python.exe" "experiments\templates\71_visual_population_causal_study.py" --stage flyvis --movie "%MOVIE%"
goto done

:mapping
if not exist "workspace\.venv-two-flies\Scripts\python.exe" goto nobrain
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms;$d=New-Object System.Windows.Forms.OpenFileDialog;$d.Title='flyvis_activity.csv';$d.Filter='CSV (*.csv)|*.csv';if($d.ShowDialog() -eq 'OK'){$d.FileName}"`) do set "ACTIVITY=%%F"
if not defined ACTIVITY goto done
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms;$d=New-Object System.Windows.Forms.OpenFileDialog;$d.Title='Таблица нейронов FlyWire v630';$d.Filter='CSV (*.csv)|*.csv';if($d.ShowDialog() -eq 'OK'){$d.FileName}"`) do set "NEURONS=%%F"
if not defined NEURONS goto done
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\71_visual_population_causal_study.py" --stage mapping --activity "%ACTIVITY%" --neurons "%NEURONS%"
goto done

:validate
if not exist "workspace\.venv-two-flies\Scripts\python.exe" goto nobrain
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms;$d=New-Object System.Windows.Forms.OpenFileDialog;$d.Title='Утвержденный mapping_review.json';$d.Filter='JSON (*.json)|*.json';if($d.ShowDialog() -eq 'OK'){$d.FileName}"`) do set "MAPPING=%%F"
if not defined MAPPING goto done
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\71_visual_population_causal_study.py" --stage validate --mapping "%MAPPING%"
goto done

:nobrain
echo Не найдена основная среда. Сначала откройте Fly Ideas и установите окружение через Данные и окружение.
:done
if errorlevel 1 echo Этап остановлен научным gate. Смотрите summary.json в папке запуска.
pause
