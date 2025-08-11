@echo off
echo.
echo ====================================================
echo    Netra AI Platform - Windows Quick Setup
echo ====================================================
echo.
echo This script will set up your complete development
echo environment automatically.
echo.
echo Prerequisites:
echo   - Python 3.9 or higher
echo   - Node.js 18 or higher
echo   - Git
echo.
echo Press any key to start setup, or Ctrl+C to cancel...
pause >NUL

REM Check if Python is installed
python --version >NUL 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

REM Run the installer
echo.
echo Starting installation...
echo.
python install_dev_env.py

if %errorlevel% equ 0 (
    echo.
    echo ====================================================
    echo    Setup Complete!
    echo ====================================================
    echo.
    echo To start the development environment, run:
    echo    start_dev.bat
    echo.
    echo Or manually:
    echo    python dev_launcher.py --dynamic
    echo.
) else (
    echo.
    echo ====================================================
    echo    Setup Failed
    echo ====================================================
    echo.
    echo Please check the error messages above and try again.
    echo For help, see README.md or CLAUDE.md
    echo.
)

pause