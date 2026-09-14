@echo off
setlocal
title GLaDOS
cd /d "%~dp0"

if not exist ".venv\Scripts\glados.exe" (
    echo GLaDOS is not installed in .venv.
    echo Run: python scripts\install.py
    echo Then: .venv\Scripts\python.exe -m uv pip install -e ".[cpu]" --python .venv\Scripts\python.exe
    echo.
    pause
    exit /b 1
)

set "VIRTUAL_ENV=%CD%\.venv"
set "PATH=%VIRTUAL_ENV%\Scripts;%PATH%"

echo Starting GLaDOS TUI...
.venv\Scripts\glados.exe tui
set "EXITCODE=%ERRORLEVEL%"

echo.
if not "%EXITCODE%"=="0" (
    echo GLaDOS stopped with error %EXITCODE%.
) else (
    echo GLaDOS closed.
)
pause
exit /b %EXITCODE%
