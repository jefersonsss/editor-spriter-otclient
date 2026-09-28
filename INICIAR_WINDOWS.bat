@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto START
call INSTALAR_WINDOWS.bat
if errorlevel 1 exit /b 1
:START
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
