@echo off
title GLaDOS
cd /d "%~dp0"

if not exist ".venv\Scripts\glados.exe" (
    echo GLaDOS is not installed in .venv.
    echo Run: python scripts\install.py
    echo Then: .venv\Scripts\python.exe -m uv pip install -e ".[cpu]" --python .venv\Scripts\python.exe
    pause
    exit /b 1
)

set "VIRTUAL_ENV=%CD%\.venv"
set "PATH=%VIRTUAL_ENV%\Scripts;%PATH%"

.venv\Scripts\glados.exe tui
if errorlevel 1 pause
