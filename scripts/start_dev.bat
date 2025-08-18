@echo off
echo Starting Netra AI Development Environment...
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start services in new windows
echo Starting Backend Server...
start "Netra Backend" cmd /k "python scripts\dev_launcher.py --dynamic --no-backend-reload"

echo.
echo Development environment is starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to stop all services...
pause >NUL

REM Kill processes
taskkill /FI "WindowTitle eq Netra Backend" /T /F
echo Services stopped.
