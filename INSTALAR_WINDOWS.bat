@echo off
setlocal
cd /d "%~dp0"
echo New Island Outfit Forge - Instalacao
where py >nul 2>&1
if errorlevel 1 goto USE_PYTHON
py -3 -c "import sys; assert sys.version_info >= (3,11), 'Use Python 3.11 ou mais recente (64 bits)'"
if errorlevel 1 goto FAIL
py -3 -m venv .venv
goto INSTALL
:USE_PYTHON
python -c "import sys; assert sys.version_info >= (3,11), 'Use Python 3.11 ou mais recente (64 bits)'"
if errorlevel 1 goto FAIL
python -m venv .venv
:INSTALL
if errorlevel 1 goto FAIL
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto FAIL
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto FAIL
echo.
echo Instalacao concluida. Abra INICIAR_WINDOWS.bat.
exit /b 0
:FAIL
echo.
echo Nao foi possivel instalar. Confira a mensagem acima.
echo Instale Python 3.11 ou mais recente, 64 bits, de python.org.
echo A instalacao das dependencias precisa de internet.
pause
exit /b 1
