@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title FlyVis and FlyGym setup
echo Установка перенесена в интерфейс Fly Ideas.
echo Откройте: Мозг - Данные и окружение - Зрение и физическое тело.
echo Нажмите: установить всё для зрения и тела.
echo.
echo Сейчас будет запущен Fly Ideas. Этот BAT ничего не скачивает и не меняет Python.
pause
start "" "%CD%\START.bat"
