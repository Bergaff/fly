@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set OMP_NUM_THREADS=4
set OPENBLAS_NUM_THREADS=4
set MKL_NUM_THREADS=4
set "FLYVIS_ROOT_DIR=%CD%\workspace\data\flyvis"
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
if not exist "workspace\.venv-two-flies\Scripts\python.exe" goto nobrain
if not exist "workspace\runs\ideas\i-observational\visual-population-causality\latest_prepared.txt" goto prepare69
set /p PREP=<"workspace\runs\ideas\i-observational\visual-population-causality\latest_prepared.txt"
if exist "%PREP%\retinal_sources.json" goto runprepared69
:prepare69
echo Ищу последний полный result серии 69 и готовлю пять движений 51-55...
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\71_visual_population_causal_study.py" --stage prepare
if errorlevel 1 goto choose69
:prepared69
if not exist "workspace\runs\ideas\i-observational\visual-population-causality\latest_prepared.txt" (
 echo Не удалось определить папку подготовленных движений.
 goto done
)
set /p PREP=<"workspace\runs\ideas\i-observational\visual-population-causality\latest_prepared.txt"
:runprepared69
echo Папка подготовленных кадров: %PREP%
echo Запускаю pretrained FlyVis для пяти движений. Это может занять несколько минут.
"workspace\.venv-flyvis\Scripts\python.exe" "experiments\templates\71_visual_population_causal_study.py" --stage batch-flyvis --output "%PREP%" --prepared "%PREP%"
if not errorlevel 1 (
 echo Готово. Активность находится в подпапках flyvis_051 - flyvis_055:
 echo %PREP%
 start "" "%PREP%"
)
goto done

:choose69
echo Автоматический поиск не сработал. Выберите папку запуска серии 69, внутри которой есть input и result.
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms;$d=New-Object System.Windows.Forms.FolderBrowserDialog;$d.Description='Папка запуска серии 69 с input и result';if($d.ShowDialog() -eq 'OK'){$d.SelectedPath}"`) do set "SERIES69=%%F"
if not defined SERIES69 goto done
"workspace\.venv-two-flies\Scripts\python.exe" "experiments\templates\71_visual_population_causal_study.py" --stage prepare --series69 "%SERIES69%"
if errorlevel 1 goto done
goto prepared69

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
