@echo off
REM Critical Unified Tests Runner - Windows Batch Script
REM 
REM This script runs the 10 critical unified tests with proper error handling
REM and service management for Windows environments.

echo ================================================================================
echo CRITICAL UNIFIED TESTS RUNNER
echo ================================================================================
echo.

REM Change to project root directory
cd /d "%~dp0"

REM Set environment variables
set NETRA_ENV=test
set LOG_LEVEL=INFO
set PYTHONPATH=%CD%

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not available in PATH
    pause
    exit /b 1
)

REM Check if pytest is available
python -m pytest --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: pytest is not available. Please install it with: pip install pytest
    pause
    exit /b 1
)

REM Run the critical tests runner
echo Running 10 critical unified tests...
echo.

python tests\unified\e2e\run_critical_unified_tests.py %*

REM Capture exit code
set TEST_EXIT_CODE=%errorlevel%

echo.
echo ================================================================================
if %TEST_EXIT_CODE% equ 0 (
    echo ALL TESTS PASSED - System ready for production
) else (
    echo TESTS FAILED - Review results and fix issues before deployment
)
echo ================================================================================

REM Pause if running interactively (not from another script)
if /i "%1" neq "--no-pause" pause

exit /b %TEST_EXIT_CODE%