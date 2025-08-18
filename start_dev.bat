@echo off
:: Netra AI Platform - Quick Start Development Script (Windows)
:: This script starts both backend and frontend with optimal settings

echo.
echo ===============================================
echo    Netra AI Development Environment
echo ===============================================
echo.

:: Check if virtual environment exists
if not exist venv\ (
    echo ERROR: Virtual environment not found!
    echo Please run: scripts\setup.bat
    echo.
    pause
    exit /b 1
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Start the dev launcher with optimal settings
echo.
echo Starting Backend and Frontend servers...
echo   - Dynamic port allocation (avoids conflicts)
echo   - No backend reload (30-50%% faster)
echo   - Automatic secret loading
echo.

python scripts\dev_launcher.py --dynamic --no-backend-reload --load-secrets

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to start development environment
    echo Please check the error messages above
    echo.
    pause
)