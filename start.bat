@echo off
setlocal

set "VENV_PY=%~dp0.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo Virtualenv non trovato in .venv\Scripts\python.exe
    echo Crea prima il virtualenv e installa le dipendenze.
    exit /b 1
)

"%VENV_PY%" "%~dp0run.py"
