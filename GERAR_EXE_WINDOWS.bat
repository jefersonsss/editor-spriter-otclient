@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto BUILD
call INSTALAR_WINDOWS.bat
if errorlevel 1 exit /b 1
:BUILD
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto FAIL
".venv\Scripts\python.exe" -m PyInstaller --noconfirm NewIslandOutfitForge.spec
if errorlevel 1 goto FAIL
echo.
echo Pronto: dist\NewIslandOutfitForge\NewIslandOutfitForge.exe
echo Distribua a pasta NewIslandOutfitForge inteira, incluindo _internal.
pause
exit /b 0
:FAIL
echo Falha ao gerar executavel. Confira a mensagem acima.
pause
exit /b 1
