@echo off
cd /d "%~dp0"
set "GLADOS_COMPLETION_URL=https://c31vfv18xcqk8y-11435.proxy.runpod.net/v1/chat/completions"
set "GLADOS_API_KEY=glados-runpod-secret"
echo Starting GLaDOS TUI against RunPod...
echo Leave the pod terminal on READY.
python -m uv run glados tui
echo.
pause
