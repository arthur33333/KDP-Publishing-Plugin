@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python est introuvable. Installez Python 3.11 ou plus recent.
  pause
  exit /b 1
)
start "" http://127.0.0.1:8765
py studio\server.py
pause
