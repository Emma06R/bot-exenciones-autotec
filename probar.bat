@echo off
title Pruebas del bot de exenciones
cd /d "%~dp0"
python -m pip install -r requirements.txt --quiet
python pruebas\pruebas_bot.py
echo.
python pruebas\exploratorio.py
pause
