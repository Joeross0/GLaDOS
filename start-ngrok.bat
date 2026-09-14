@echo off
setlocal
title GLaDOS ngrok
cd /d "%~dp0"

where ngrok >nul 2>&1
if errorlevel 1 (
    echo ngrok is not on PATH.
    echo Install it, then run: ngrok config add-authtoken YOUR_TOKEN
    echo.
    pause
    exit /b 1
)

echo Starting GLaDOS in another window...
start "GLaDOS" cmd /k "%~dp0start.bat"

echo Waiting for the portal on port 9119...
timeout /t 8 /nobreak >nul

echo.
echo Opening an HTTPS tunnel to http://127.0.0.1:9119
echo Paste the https://....ngrok-free.app URL into the Vercel portal as the Core URL.
echo PIN is 9119
echo.
ngrok http 9119 --log=stdout
set "EXITCODE=%ERRORLEVEL%"

echo.
if not "%EXITCODE%"=="0" (
    echo ngrok exited with error %EXITCODE%.
    echo If it asked for an authtoken: ngrok config add-authtoken YOUR_TOKEN
)
pause
exit /b %EXITCODE%
