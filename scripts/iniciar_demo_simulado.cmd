@echo off
rem Demo con el paciente simulado (sEMG real de GRABMyo)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar_demo.ps1" -Fuente simulada
pause
