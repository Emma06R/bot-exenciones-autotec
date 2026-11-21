@echo off
title Bot de exenciones AutoTec
cd /d "%~dp0"
if not exist ".env" (
  echo Falta el archivo .env con el token. Lee LEEME_PRIMERO.md, paso 2.
  pause
  exit /b
)
python -m pip install -r requirements.txt --quiet
:inicio
python bot.py
echo El bot se detuvo. Se reinicia en 10 segundos... (cierra esta ventana para apagarlo)
timeout /t 10 >nul
goto inicio
