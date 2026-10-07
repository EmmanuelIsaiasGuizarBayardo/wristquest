@echo off
rem Demo con el brazalete conectado por puerto serie
set /p PUERTO=Puerto del brazalete (por ejemplo COM3): 
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar_demo.ps1" -Fuente serie -PuertoSerie %PUERTO%
pause
